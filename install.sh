#!/usr/bin/env bash
#
# install.sh — bootstrap a cat-herder Claude Code project from this template.
#
# Scaffolds the template into a PROJECT_PATH (created if missing; existing files
# are preserved, never clobbered), then installs and wires the optional-but-
# recommended dependencies that make the discovery ladder, token savings, and
# memory features work:
#
#   rmx       — refmatrix: lookup + GMD memory surface          (github.com/tangentland/refmatrix)
#   llm-tldr  — token-efficient code analysis / call graphs     (PyPI)
#   rtk       — Rust Token Killer: shrinks dev-command output    (github.com/rtk-ai/rtk)
#   caveman   — ultra-compressed agent communication mode        (github.com/JuliusBrussee/caveman)
#   openwolf  — token-conscious project brain + buglog            (npm: openwolf)
#   gmd       — Graph Markdown tooling (bundled under tools/gmd)
#
# With no PROJECT_PATH the installer wires the template repo in place. Given a
# path, it scaffolds there and wires that project. Idempotent and safe to re-run.
#
# Usage:
#   ./install.sh                      # wire the template repo in place
#   ./install.sh ../my-project        # scaffold into ../my-project, then wire it
#   ./install.sh ~/code/app --minimal # scaffold, only wire bundled GMD tooling
#   ./install.sh --skip-openwolf --skip-caveman
#   ./install.sh --help
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"   # template source (where this script lives)

# ---- options ---------------------------------------------------------------
SKIP_RMX=0; SKIP_TLDR=0; SKIP_RTK=0; SKIP_CAVEMAN=0; SKIP_OPENWOLF=0; MINIMAL=0
PROJECT_DIR=""
for arg in "$@"; do
  case "$arg" in
    --minimal)        MINIMAL=1 ;;
    --skip-rmx)       SKIP_RMX=1 ;;
    --skip-tldr)      SKIP_TLDR=1 ;;
    --skip-rtk)       SKIP_RTK=1 ;;
    --skip-caveman)   SKIP_CAVEMAN=1 ;;
    --skip-openwolf)  SKIP_OPENWOLF=1 ;;
    -h|--help)
      sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'
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
# ---------------------------------------------------------------------------
scaffold_project() {
  if [ "$PROJECT_ROOT" = "$TEMPLATE_ROOT" ]; then
    say "No project path — wiring the template repo in place ($PROJECT_ROOT)"
    return
  fi
  say "Scaffolding template into $PROJECT_ROOT (existing files preserved)"
  if have rsync; then
    rsync -a --ignore-existing \
      --exclude '.git/' --exclude '.memory.db*' --exclude 'memory.*' --exclude '.memory.*' \
      --exclude '__pycache__/' --exclude '*.pyc' --exclude '.venv/' \
      --exclude 'node_modules/' --exclude '.wolf/' --exclude '.DS_Store' \
      "$TEMPLATE_ROOT"/ "$PROJECT_ROOT"/
    ok "scaffold complete (rsync)"
  else
    # Portable fallback: copy known top-level entries, never clobbering existing.
    local items=(CLAUDE.md SETUP.md handoff.md install.sh .mcp.json .gitignore \
                 .gmd .claude docs workflow tools scripts)
    local it
    for it in "${items[@]}"; do
      [ -e "$TEMPLATE_ROOT/$it" ] || continue
      if [ -e "$PROJECT_ROOT/$it" ]; then ok "kept existing: $it"; continue; fi
      cp -R "$TEMPLATE_ROOT/$it" "$PROJECT_ROOT/$it" && ok "added: $it"
    done
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
# rmx / refmatrix (github.com/tangentland/refmatrix). Python package exposing the
# `rmx` console script. Prefer an isolated install (pipx / uv tool) straight from
# git; fall back to pip --user. Requires Python >= 3.10.
# ---------------------------------------------------------------------------
RMX_GIT="git+https://github.com/tangentland/refmatrix.git"
install_rmx() {
  say "Installing rmx (refmatrix — lookup + GMD memory surface)"
  if have rmx && rmx --version >/dev/null 2>&1; then
    ok "rmx already installed ($(rmx --version 2>/dev/null | head -1))"; WIRED+=("rmx"); return
  fi
  if have pipx; then
    pipx install "$RMX_GIT" && { ok "installed via pipx"; WIRED+=("rmx"); return; }
  elif have uv; then
    uv tool install "refmatrix @ $RMX_GIT" && { ok "installed via uv tool"; WIRED+=("rmx"); return; }
  elif have pip3; then
    pip3 install --user "$RMX_GIT" && { ok "installed via pip3 --user"; WIRED+=("rmx"); return; }
  fi
  warn "Could not install rmx — install pipx or uv, then: pipx install \"$RMX_GIT\""
  warn "  (for semantic recall, add the dense extra: pipx install \"refmatrix[dense] @ $RMX_GIT\")"
  FAILED+=("rmx")
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
# rtk (github.com/rtk-ai/rtk). brew > install script > cargo. Then wire the hook.
# ---------------------------------------------------------------------------
install_rtk() {
  say "Installing rtk (Rust Token Killer)"
  if have rtk; then
    ok "rtk already installed ($(rtk --version 2>/dev/null))"
  elif have brew; then
    brew install rtk && ok "installed via Homebrew"
  elif have curl; then
    curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh \
      && ok "installed via install script"
  elif have cargo; then
    cargo install --git https://github.com/rtk-ai/rtk && ok "installed via cargo"
  else
    warn "No brew/curl/cargo — see https://github.com/rtk-ai/rtk#installation"
    FAILED+=("rtk"); return
  fi
  if have rtk; then
    # Wire the Claude Code auto-rewrite hook (global). Safe to re-run.
    rtk init -g >/dev/null 2>&1 && ok "wired Claude Code hook (rtk init -g)" \
      || warn "run 'rtk init -g' manually to wire the hook"
    WIRED+=("rtk")
  else
    FAILED+=("rtk")
  fi
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
# openwolf (npm: openwolf). Global install, then init .wolf/ in this project.
# ---------------------------------------------------------------------------
install_openwolf() {
  say "Installing openwolf (token-conscious project brain)"
  if ! have npm; then
    warn "npm required — install Node.js, then: npm install -g openwolf"
    FAILED+=("openwolf"); return
  fi
  if have openwolf; then
    ok "openwolf already installed ($(openwolf --version 2>/dev/null))"
  else
    npm install -g openwolf && ok "installed via npm" || { warn "npm install -g openwolf failed"; FAILED+=("openwolf"); return; }
  fi
  # Initialize .wolf/ in this project (creates buglog, anatomy, and wires hooks).
  if [ ! -d ".wolf" ]; then
    openwolf init >/dev/null 2>&1 && ok "initialized .wolf/ (openwolf init)" \
      || warn "run 'openwolf init' in the project root to finish setup"
  else
    ok ".wolf/ already present"
  fi
  WIRED+=("openwolf")
}

# ---- run -------------------------------------------------------------------
say "cat-herder template installer"
say "  template: $TEMPLATE_ROOT"
say "  project:  $PROJECT_ROOT"
scaffold_project
cd "$PROJECT_ROOT"   # all per-project wiring (GMD lint, openwolf init) targets the project
wire_gmd

if [ "$MINIMAL" -eq 1 ]; then
  say "--minimal: skipping external dependencies"
  SKIPPED+=("rmx" "llm-tldr" "rtk" "caveman" "openwolf")
else
  [ "$SKIP_RMX" -eq 1 ]      && SKIPPED+=("rmx")      || install_rmx
  [ "$SKIP_TLDR" -eq 1 ]     && SKIPPED+=("llm-tldr") || install_tldr
  [ "$SKIP_RTK" -eq 1 ]      && SKIPPED+=("rtk")      || install_rtk
  [ "$SKIP_CAVEMAN" -eq 1 ]  && SKIPPED+=("caveman")  || install_caveman
  [ "$SKIP_OPENWOLF" -eq 1 ] && SKIPPED+=("openwolf") || install_openwolf
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
echo "  • Replace template placeholders ({PROJECT_NAME}, {project_package}, …) — see SETUP.md."
[ ${#FAILED[@]} -gt 0 ] && exit 1 || exit 0
