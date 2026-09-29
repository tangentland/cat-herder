#!/bin/bash
# Claude Code status line — project, model + mode, context, tokens, weekly sessions/compactions.
#
# Shipped by the cat-herder template and wired via .claude/settings.json ("statusLine").
# Reads the status JSON on stdin (context window, workspace dir) and prints a single line:
#
#   <project> | <model> <mode>[ fast] | Ctx:<pct>% | Tok:<n> | Wk:<n> | Win:<sessions> Cmp:<compactions>
#
# The project name (first field) is the basename of the workspace/project dir, so every
# terminal running Claude Code shows which project it is — CC's auto tab-title is not
# configurable, so this status line is the reliable persistent project indicator.
#
# Model comes from the status JSON (.model.display_name). The permission mode (default, plan,
# accept, auto, bypass, dontAsk) is NOT in the status JSON, so it is read from the most recent
# "permissionMode" entry in the session transcript (.transcript_path); omitted if not found.
#
# Requires jq (without it only the project name is shown). Works with BSD (macOS) and GNU date.
#
# Weekly counters (tokens, sessions, compactions) persist in $HOME/.claude/.weekly_state and
# reset weekly at Sunday 10:00 in $CH_STATUS_WEEK_TZ (default America/Los_Angeles). Per-session
# values live in $HOME/.claude/.statusline/<session_id>, so concurrent sessions don't collide.
# "Wk" accumulates context growth (never a session's running total twice).

input=$(cat)

if ! command -v jq >/dev/null 2>&1; then
  echo "${PWD##*/}"
  exit 0
fi

jqr() { echo "$input" | jq -r "$1" 2>/dev/null; }
int() { case "$1" in ''|*[!0-9]*) echo 0 ;; *) echo "$1" ;; esac; }

pct=$(int "$(jqr '.context_window.used_percentage // 0' | cut -d. -f1)")
in_tok=$(int "$(jqr '.context_window.total_input_tokens // 0')")
out_tok=$(int "$(jqr '.context_window.total_output_tokens // 0')")
session=$(jqr '.session_id // empty' | tr -cd 'A-Za-z0-9_-')
session=${session:-default}

# Project name (first field): basename of the project/workspace dir.
proj=$(jqr '.workspace.project_dir // .workspace.current_dir // .cwd // empty')
proj=$(basename "$proj" 2>/dev/null)
if [ -n "$proj" ] && [ "$proj" != "." ] && [ "$proj" != "/" ]; then
  proj_prefix="$proj | "
else
  proj_prefix=""
fi

# Model + permission mode (second field).
model=$(jqr '.model.display_name // .model.id // empty')
transcript=$(jqr '.transcript_path // empty')
mode=""
if [ -n "$transcript" ] && [ -f "$transcript" ]; then
  # Bounded tail: the mode is logged on every prompt, so the latest entry is near the end.
  mode=$(tail -c 4000000 "$transcript" 2>/dev/null \
    | grep -o '"permissionMode":"[A-Za-z]*"' | tail -1 | cut -d'"' -f4)
fi
case "$mode" in
  acceptEdits)       mode="accept" ;;
  bypassPermissions) mode="bypass" ;;
esac
[ "$(jqr '.fast_mode // false')" = "true" ] && mode="${mode:+$mode }fast"
model_field="${model}${model:+${mode:+ }}${mode}"
if [ -z "$model" ] && [ -n "$mode" ]; then model_field="$mode"; fi
[ -n "$model_field" ] && proj_prefix="${proj_prefix}${model_field} | "

# Token formatting (K/M)
fmt_tok() {
  local t=$1
  if [ "$t" -ge 1000000 ]; then
    echo "$((t / 1000000)).$((t % 1000000 / 100000))M"
  elif [ "$t" -ge 1000 ]; then
    echo "$((t / 1000))K"
  else
    echo "$t"
  fi
}

total_tok=$((in_tok + out_tok))
tok_str=$(fmt_tok "$total_tok")

# --- Weekly reset key: most recent Sunday 10:00 in the configured zone (BSD or GNU date) ---
WEEK_TZ="${CH_STATUS_WEEK_TZ:-America/Los_Angeles}"
now_epoch=$(date +%s)
# Seconds are parsed explicitly: BSD `date -j -f` fills unparsed fields from the clock, which
# would make the key drift every render and reset the weekly counters.
sun_10am=$(TZ=$WEEK_TZ date -j -f "%Y%m%d%H%M%S" \
  "$(TZ=$WEEK_TZ date -v-sun -v10H -v0M -v0S +%Y%m%d%H%M%S 2>/dev/null)" +%s 2>/dev/null)
if [ -z "$sun_10am" ]; then  # GNU date
  sun_10am=$(TZ=$WEEK_TZ date -d "$(TZ=$WEEK_TZ date +%F) -$(TZ=$WEEK_TZ date +%w) days 10:00" \
    +%s 2>/dev/null)
fi
sun_10am=$(int "$sun_10am")
if [ "$sun_10am" -gt "$now_epoch" ]; then
  sun_10am=$((sun_10am - 604800))
fi
WEEK_KEY="$sun_10am"

# --- State: weekly totals (shared) + per-session last values ---
STATE_DIR="$HOME/.claude"
STATE_FILE="$STATE_DIR/.weekly_state"
SESSION_DIR="$STATE_DIR/.statusline"
SESSION_FILE="$SESSION_DIR/$session"
mkdir -p "$SESSION_DIR" 2>/dev/null

wk_tok=0; wk_sessions=0; wk_compactions=0
if [ -f "$STATE_FILE" ] && [ "$(sed -n '1p' "$STATE_FILE" 2>/dev/null)" = "$WEEK_KEY" ]; then
  wk_tok=$(int "$(sed -n '2p' "$STATE_FILE" 2>/dev/null)")
  wk_sessions=$(int "$(sed -n '3p' "$STATE_FILE" 2>/dev/null)")
  wk_compactions=$(int "$(sed -n '4p' "$STATE_FILE" 2>/dev/null)")
fi

if [ -f "$SESSION_FILE" ]; then
  last_pct=$(int "$(sed -n '1p' "$SESSION_FILE" 2>/dev/null)")
  last_tok=$(int "$(sed -n '2p' "$SESSION_FILE" 2>/dev/null)")
  # Compaction: context % dropped sharply within the same session.
  if [ $((last_pct - pct)) -gt 15 ]; then
    wk_compactions=$((wk_compactions + 1))
  fi
  delta=$((total_tok - last_tok))
  [ "$delta" -lt 0 ] && delta=0
else
  # First render of this session (skip the empty {} renders before the first API response).
  if [ "$session" != "default" ]; then
    wk_sessions=$((wk_sessions + 1))
    find "$SESSION_DIR" -type f -mtime +14 -delete 2>/dev/null
  fi
  delta=$total_tok
fi
wk_tok=$((wk_tok + delta))

# Atomic writes: concurrent sessions render at the same time.
write_atomic() {
  local dest=$1 tmp
  tmp=$(mktemp "$dest.XXXXXX" 2>/dev/null) || return 0
  cat > "$tmp" && mv -f "$tmp" "$dest" 2>/dev/null || rm -f "$tmp"
}
printf '%s\n%s\n' "$pct" "$total_tok" | write_atomic "$SESSION_FILE"
printf '%s\n%s\n%s\n%s\n' "$WEEK_KEY" "$wk_tok" "$wk_sessions" "$wk_compactions" \
  | write_atomic "$STATE_FILE"

weekly_str=$(fmt_tok "$wk_tok")

# --- Token burn rate warning ---
# High session tokens = context bloat risk, likely heading toward compaction
tok_warn=""
if [ "$total_tok" -ge 800000 ]; then
  tok_warn=" !! BURN"
elif [ "$total_tok" -ge 500000 ]; then
  tok_warn=" ! BURN"
fi

stats="Wk:$weekly_str | Win:$wk_sessions Cmp:$wk_compactions"

# --- Output ---
if [ "$pct" = "0" ]; then
  echo "${proj_prefix}Ctx:-- | Tok:$tok_str$tok_warn | $stats"
elif [ "$pct" -ge 85 ]; then
  echo "${proj_prefix}!! CTX ${pct}% HANDOFF !! | Tok:$tok_str$tok_warn | $stats"
elif [ "$pct" -ge 70 ]; then
  echo "${proj_prefix}! Ctx:${pct}% save | Tok:$tok_str$tok_warn | $stats"
else
  echo "${proj_prefix}Ctx:${pct}% | Tok:$tok_str$tok_warn | $stats"
fi
