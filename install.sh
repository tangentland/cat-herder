#!/usr/bin/env bash
#
# install.sh — bootstrap a cat-herder Claude Code project from this template.
#
# Scaffolds the template into a PROJECT_PATH (created if missing; existing files
# are preserved, never clobbered), tunes it to the project, then installs and wires the optional-but-
# recommended dependencies that make the discovery ladder, token savings, and
# memory features work:
#
#   rmx       — refmatrix: primary memory layer + GMD surface    (github.com/tangentland/refmatrix)
#   llm-tldr  — token-efficient code analysis / call graphs     (PyPI)
#   caveman   — ultra-compressed agent communication mode        (github.com/JuliusBrussee/caveman)
#   gmd       — Graph Markdown tooling (bundled under tools/gmd)
#
# TUNING TO THE PROJECT IS PART OF INSTALL. After scaffolding, scripts/tune-project.py inspects
# the target: for an EXISTING codebase it detects languages, per-language directory layout
# (src/test/ui/migration roots, monorepo workspaces), frameworks, database and the stack's
# test/lint/type-check/format commands; for a FROM-SCRATCH project (no code, no manifests) it
# PROMPTS for name, languages, package, frameworks, database, UI dir and target OS, and can
# create the conventional directory skeleton. Results land in .claude/PROJECT_PROFILE.md
# (placeholder fields only) and a tuned .claude/hooks/hooks.env. The agent finishes the rest
# on first run (docs/ONBOARDING.md). Pass the tuning flags below to answer without prompts.
#
# Re-running is SAFE but NOT AN UPGRADE: scaffolding only ADDS template files the project lacks
# and never overwrites an existing file, so project files (.claude/agents/*.local.md, a filled
# PROJECT_PROFILE.md, hooks.env) are never clobbered — and, equally, newer versions of baseline
# files (agent defs, scripts/tune-project.py, …) are not pulled into an existing project. To take
# a baseline update, copy the specific files over from the template deliberately.
#
# With no PROJECT_PATH the installer wires the template repo in place. Given a
# path, it scaffolds there and wires that project. Idempotent and safe to re-run.
#
# Usage:
#   ./install.sh                      # wire the template repo in place
#   ./install.sh ../my-project        # scaffold into ../my-project, tune, then wire it
#   ./install.sh ~/code/app --minimal # scaffold, only wire bundled GMD + SDD tooling
#   ./install.sh ../new-app --lang=python,ts --name="New App" --db=postgres --no-prompt
#   ./install.sh --tune               # in place, but this clone IS a new project: tune it
#   ./install.sh --skip-caveman
#   ./install.sh --help
#
# Dependency flags:
#   --minimal  --skip-rmx  --skip-tldr  --skip-caveman
#
# Tuning flags (forwarded to scripts/tune-project.py):
#   --no-tune  --no-prompt  --tune  --skeleton|--no-skeleton
#   --name=  --description=  --lang=  --package=  --db=  --ui=  --os=
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"   # template source (where this script lives)

# ---- options ---------------------------------------------------------------
SKIP_RMX=0; SKIP_TLDR=0; SKIP_CAVEMAN=0; MINIMAL=0
TUNE=auto; TUNE_ARGS=()
PROJECT_DIR=""
for arg in "$@"; do
  case "$arg" in
    --minimal)        MINIMAL=1 ;;
    --skip-rmx)       SKIP_RMX=1 ;;
    --skip-tldr)      SKIP_TLDR=1 ;;
    --skip-caveman)   SKIP_CAVEMAN=1 ;;
    --skip-rtk)       echo "note: --skip-rtk is deprecated (rtk is no longer installed); ignoring" >&2 ;;
    --tune)           TUNE=1 ;;
    --no-tune)        TUNE=0 ;;
    --no-prompt|--skeleton|--no-skeleton) TUNE_ARGS+=("$arg") ;;
    --name=*|--description=*|--lang=*|--package=*|--db=*|--ui=*|--os=*) TUNE_ARGS+=("$arg") ;;
    -h|--help)
      sed -n '2,/^set -euo/p' "$0" | sed '$d' | sed 's/^# \{0,1\}//'
      exit 0 ;;
    --*) echo "unknown option: $arg (try --help)" >&2; exit 2 ;;
    *)
      [ -n "$PROJECT_DIR" ] && { echo "multiple project paths given: '$PROJECT_DIR' and '$arg'" >&2; exit 2; }
      PROJECT_DIR="$arg" ;;
  esac
done

# ---- resolve template vs project root --------------------------------------
TEMPLATE_ROOT="$ROOT"
if [ -n "$PROJECT_DIR" ]; then
  mkdir -p "$PROJECT_DIR"
  PROJECT_ROOT="$(cd "$PROJECT_DIR" && pwd)"
else
  PROJECT_ROOT="$TEMPLATE_ROOT"
fi

# ---- output helpers --------------------------------------------------------
say()  { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m  ok\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m  !!\033[0m %s\n' "$*" >&2; }
have() { command -v "$1" >/dev/null 2>&1; }

WIRED=(); SKIPPED=(); FAILED=()

# ---------------------------------------------------------------------------
# Scaffold the template into PROJECT_ROOT. Existing files are preserved
# (never overwritten) so this is safe on a partially-populated project.
# Skips the template's own VCS + runtime state.
#
# RUNTIME STATE IS NEVER COPIED. .scaffoldignore (the single source for the exclusion
# list, with the reason for each entry) is read by BOTH copy paths below. Most importantly
# .refmatrix/ — the rmx catalog — would seed the target's index with the TEMPLATE's content, so
# rmx context/query/memory would answer about cat-herder, not the project. The target builds
# its own catalog on first rmx sync/ingest; .tldr, .agents/.augment are rebuilt likewise.
# ---------------------------------------------------------------------------
scaffold_project() {
  if [ "$PROJECT_ROOT" = "$TEMPLATE_ROOT" ]; then
    say "No project path — wiring the template repo in place ($PROJECT_ROOT)"
    return
  fi
  say "Scaffolding template into $PROJECT_ROOT (existing files preserved)"
  local ignore="$TEMPLATE_ROOT/.scaffoldignore"
  [ -f "$ignore" ] || { warn ".scaffoldignore missing from the template — refusing to scaffold"; exit 1; }
  if have rsync; then
    rsync -a --ignore-existing --exclude-from="$ignore" "$TEMPLATE_ROOT"/ "$PROJECT_ROOT"/
    ok "scaffold complete (rsync)"
  elif have python3; then
    # Same semantics as rsync --ignore-existing --exclude-from, file by file.
    python3 - "$TEMPLATE_ROOT" "$PROJECT_ROOT" "$ignore" <<'PY'
import fnmatch, os, shutil, sys
src, dst, ignore = sys.argv[1:4]
pats = [l.strip() for l in open(ignore) if l.strip() and not l.lstrip().startswith("#")]
def excluded(rel, is_dir):
    for p in pats:
        dir_only, p = p.endswith("/"), p.rstrip("/")
        if dir_only and not is_dir:
            continue
        if p.startswith("/"):
            if rel == p[1:]:
                return True
        elif fnmatch.fnmatch(os.path.basename(rel), p):
            return True
    return False
for dirpath, dirs, files in os.walk(src):
    base = os.path.relpath(dirpath, src)
    base = "" if base == "." else base
    dirs[:] = [d for d in dirs if not excluded(os.path.join(base, d), True)]
    os.makedirs(os.path.join(dst, base), exist_ok=True)
    for f in files:
        rel = os.path.join(base, f)
        if not excluded(rel, False) and not os.path.lexists(os.path.join(dst, rel)):
            shutil.copy2(os.path.join(src, rel), os.path.join(dst, rel), follow_symlinks=False)
PY
    ok "scaffold complete (python fallback)"
  else
    warn "need rsync or python3 to scaffold"; exit 1
  fi
}

# ---------------------------------------------------------------------------
# GMD — bundled. Just make the tooling executable and smoke-test the linter.
# ---------------------------------------------------------------------------
wire_gmd() {
  say "Wiring bundled GMD tooling (tools/gmd/)"
  if ! have python3; then
    warn "python3 not found — GMD lint will not run. Install Python 3, then re-run."
    FAILED+=("gmd"); return
  fi
  chmod +x tools/gmd/gmd tools/gmd/lint-memory.sh scripts/lint-gmd.sh 2>/dev/null || true
  if python3 tools/gmd/lint.py docs/gmd/PRIMER.md >/dev/null 2>&1; then
    ok "GMD linter works — try: ./scripts/lint-gmd.sh"
    WIRED+=("gmd")
  else
    warn "GMD linter smoke-test failed."
    FAILED+=("gmd")
  fi
}

# ---------------------------------------------------------------------------
# SDD chain + hooks. Make scripts executable and seed project-specific config from
# the shipped *.example files — ONLY when absent, so a re-run upgrades the neutral
# baseline without clobbering a project's customization (see D9 in the merge plan).
# ---------------------------------------------------------------------------
wire_sdd() {
  say "Wiring SDD scripts + enforcement hooks (scripts/sdd/, .claude/hooks/)"
  chmod +x scripts/sdd/*.sh .claude/hooks/*.sh .claude/statusline.sh 2>/dev/null || true
  # Seed hooks.env from the example only if the project has not created one.
  if [ ! -f ".claude/hooks/hooks.env" ] && [ -f ".claude/hooks/hooks.env.example" ]; then
    cp ".claude/hooks/hooks.env.example" ".claude/hooks/hooks.env" && ok "seeded .claude/hooks/hooks.env (edit for this project)"
  else
    ok ".claude/hooks/hooks.env preserved (or no example present)"
  fi
  if scripts/sdd/create-new-feature.sh --help >/dev/null 2>&1; then
    ok "SDD scripts ready — start a feature with /ch-specify"
    WIRED+=("sdd")
  else
    warn "SDD scripts present but --help smoke-test failed."
    FAILED+=("sdd")
  fi
}

# ---------------------------------------------------------------------------
# Tune the scaffold to the project: detect (existing code) or prompt (from scratch).
# Skipped when wiring the template repo itself in place, unless --tune says this
# checkout is a real project. Never clobbers project-authored values.
# ---------------------------------------------------------------------------
tune_project() {
  if [ "$TUNE" = "0" ]; then SKIPPED+=("tune"); return; fi
  if [ "$TUNE" = "auto" ] && [ "$PROJECT_ROOT" = "$TEMPLATE_ROOT" ]; then
    say "Wiring the template itself — skipping project tuning (use --tune if this clone is your project)"
    SKIPPED+=("tune"); return
  fi
  say "Tuning to the project (languages, layout, commands) — scripts/tune-project.py"
  if ! have python3; then
    warn "python3 not found — cannot tune. Install Python 3, then: python3 scripts/tune-project.py"
    FAILED+=("tune"); return
  fi
  local rc=0
  python3 scripts/tune-project.py --root . ${TUNE_ARGS[@]+"${TUNE_ARGS[@]}"} || rc=$?
  case "$rc" in
    0) ok "tuned .claude/PROJECT_PROFILE.md + .claude/hooks/hooks.env — review both"
       WIRED+=("tune") ;;
    3) warn "nothing tuned (from-scratch project, no terminal) — re-run: python3 scripts/tune-project.py"
       SKIPPED+=("tune") ;;
    *) warn "tuning failed (exit $rc) — re-run: python3 scripts/tune-project.py"
       FAILED+=("tune") ;;
  esac
}

# ---------------------------------------------------------------------------
# rmx / refmatrix (github.com/tangentland/refmatrix). Python package exposing the
# `rmx` console script. Prefer an isolated install (pipx / uv tool) straight from
# git; fall back to pip --user. Requires Python >= 3.10.
# ---------------------------------------------------------------------------
RMX_GIT="git+https://github.com/tangentland/refmatrix.git"
install_rmx() {
  say "Installing rmx (refmatrix — lookup + GMD memory surface)"
  if have rmx && rmx --version >/dev/null 2>&1; then
    ok "rmx already installed ($(rmx --version 2>/dev/null | head -1))"; WIRED+=("rmx"); wire_rmx_hooks; return
  fi
  if have pipx; then
    pipx install "$RMX_GIT" && { ok "installed via pipx"; WIRED+=("rmx"); wire_rmx_hooks; return; }
  elif have uv; then
    uv tool install "refmatrix @ $RMX_GIT" && { ok "installed via uv tool"; WIRED+=("rmx"); wire_rmx_hooks; return; }
  elif have pip3; then
    pip3 install --user "$RMX_GIT" && { ok "installed via pip3 --user"; WIRED+=("rmx"); wire_rmx_hooks; return; }
  fi
  warn "Could not install rmx — install pipx or uv, then: pipx install \"$RMX_GIT\""
  warn "  (for semantic recall, add the dense extra: pipx install \"refmatrix[dense] @ $RMX_GIT\")"
  FAILED+=("rmx")
}

# Wire rmx's git hooks (post-commit/merge/checkout → rmx sync). The Claude Code hooks are
# already committed in .claude/settings.json (guarded), so this only installs git-side hooks.
wire_rmx_hooks() {
  have rmx || return
  if rmx install-hooks --apply >/dev/null 2>&1; then
    ok "wired rmx git hooks (rmx install-hooks --apply)"
  else
    warn "run 'rmx install-hooks --apply' in the project to wire git-side sync hooks"
  fi
}

# ---------------------------------------------------------------------------
# llm-tldr (PyPI). Prefer an isolated install (pipx / uv tool); fall back to pip.
# ---------------------------------------------------------------------------
install_tldr() {
  say "Installing llm-tldr (token-efficient code analysis)"
  if have tldr && tldr --version >/dev/null 2>&1; then
    ok "tldr already installed ($(tldr --version 2>/dev/null | head -1))"; WIRED+=("llm-tldr"); return
  fi
  if have pipx; then
    pipx install llm-tldr && { ok "installed via pipx"; WIRED+=("llm-tldr"); return; }
  elif have uv; then
    uv tool install llm-tldr && { ok "installed via uv tool"; WIRED+=("llm-tldr"); return; }
  elif have pip3; then
    pip3 install --user llm-tldr && { ok "installed via pip3 --user"; WIRED+=("llm-tldr"); return; }
  fi
  warn "Could not install llm-tldr — install pipx or uv, then: pipx install llm-tldr"
  FAILED+=("llm-tldr")
}

# ---------------------------------------------------------------------------
# caveman (github.com/JuliusBrussee/caveman). One-line installer wires the agent.
# ---------------------------------------------------------------------------
install_caveman() {
  say "Installing caveman (compressed communication mode)"
  if ! have curl; then
    warn "curl required — see https://github.com/JuliusBrussee/caveman#install"
    FAILED+=("caveman"); return
  fi
  if curl -fsSL https://raw.githubusercontent.com/JuliusBrussee/caveman/main/install.sh | bash; then
    ok "caveman installed + wired"; WIRED+=("caveman")
  else
    warn "caveman install failed — see https://github.com/JuliusBrussee/caveman#install"
    FAILED+=("caveman")
  fi
}

# ---------------------------------------------------------------------------
# ---- run -------------------------------------------------------------------
say "cat-herder template installer"
say "  template: $TEMPLATE_ROOT"
say "  project:  $PROJECT_ROOT"
scaffold_project
cd "$PROJECT_ROOT"   # all per-project wiring (GMD lint, SDD scripts) targets the project
wire_gmd
wire_sdd
tune_project

if [ "$MINIMAL" -eq 1 ]; then
  say "--minimal: skipping external dependencies"
  SKIPPED+=("rmx" "llm-tldr" "caveman")
else
  [ "$SKIP_RMX" -eq 1 ]      && SKIPPED+=("rmx")      || install_rmx
  [ "$SKIP_TLDR" -eq 1 ]     && SKIPPED+=("llm-tldr") || install_tldr
  [ "$SKIP_CAVEMAN" -eq 1 ]  && SKIPPED+=("caveman")  || install_caveman
fi

# ---- summary ---------------------------------------------------------------
echo
say "Summary"
ok    "project: $PROJECT_ROOT"
[ ${#WIRED[@]}   -gt 0 ] && ok    "wired:   ${WIRED[*]}"
[ ${#SKIPPED[@]} -gt 0 ] && say   "skipped: ${SKIPPED[*]}"
[ ${#FAILED[@]}  -gt 0 ] && warn  "failed:  ${FAILED[*]} (see notes above)"
echo
echo "Notes:"
echo "  • Project scaffolded at: $PROJECT_ROOT (existing files were preserved)."
echo "  • rmx (refmatrix) needs Python >= 3.10 and git. For semantic recall add the dense"
echo "    extra: pipx install \"refmatrix[dense] @ $RMX_GIT\"  — verify with: rmx --version"
echo "  • Some integrations wire Claude Code hooks — restart Claude Code to load them."
echo "  • Tuning is part of install: review .claude/PROJECT_PROFILE.md (detected/prompted values),"
echo "    then finish in Claude Code — docs/ONBOARDING.md expands the remaining placeholders"
echo "    ({PROJECT_NAME}, {project_package}, …) and adapts CLAUDE.md + Docker to the stack."
echo "    Re-tune any time: python3 scripts/tune-project.py"
[ ${#FAILED[@]} -gt 0 ] && exit 1 || exit 0
