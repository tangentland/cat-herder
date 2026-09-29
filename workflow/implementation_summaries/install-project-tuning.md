---
gmd: "0.1"
id: impl-install-project-tuning
title: "Implementation Summary — stack-aware install tuning + statusline model/mode"
tags: [implementation-summary, install, tooling]
metadata:
  node_type: implementation-summary
  date: 2026-09-29
  commits: [755a914, d253c10, f7159c8]
  branch: install-project-tuning
  review_fix_branch: install-tuning-review-fixes
---

# Implementation Summary — stack-aware install tuning {#root}

rel: amends -> [[SETUP#tune]]
rel: amends -> [[ONBOARDING#sequence]]

## Intent {#intent}

The installer scaffolded a Python/Docker-flavoured baseline into any project and left all
adaptation to the agent. Goal: make install **sensitive to the target's structure** (languages,
per-language layouts, commands), state that tuning is part of install, and **prompt** for the
details when the project is from scratch.

## What changed {#changes}

- **`scripts/tune-project.py` (new)** — run by `install.sh` after scaffolding; re-runnable.
  - *Existing codebase:* detects 15 languages (incl. SQL) from manifests + a source census that
    skips deps, build output, virtualenvs (`pyvenv.cfg`), `*.egg-info`, and template tooling.
    Minor-language traces (< 3 files or < 5 % of source) are reported, not tuned for.
  - *Layout:* conventional per-language roots (`src/<pkg>`, `cmd`+`internal`, `src/main/java`, …)
    **plus** any non-conventional top-level dir holding source; tests/UI (incl. static `public/`)/
    migrations; monorepo workspaces.
  - *Commands:* evidence-gated — config files, declared deps, `package.json` scripts, `Makefile`
    targets. No evidence → "none detected — do not invent one". Docker-wrapped only when a compose
    file exists.
  - *From scratch:* prompts (tty or `/dev/tty`) for name, one-liner, languages, package,
    frameworks, DB, UI dir, target OS; proposes layout; commands marked *proposed*; optional
    `.gitkeep` skeleton. No tty and no `--lang` → tunes nothing (no guessing).
  - *Writes:* only `{…}`/template-default fields of `.claude/PROJECT_PROFILE.md` + an
    `Install detection` evidence section (between HTML-comment markers, replaced per run);
    `.claude/hooks/hooks.env` when absent or byte-identical to the example. A filled profile is
    treated as project-owned and never rewritten.
- **`install.sh`** — `tune_project` step; flags `--tune`, `--no-tune`, `--no-prompt`,
  `--skeleton`/`--no-skeleton`, `--name= --description= --lang= --package= --db= --ui= --os=`.
  In-place template runs skip tuning unless `--tune`. Rsync excludes runtime state:
  `.refmatrix/` (would seed the target's rmx index with the template's content), `.tldr/`,
  `.agents/`, `.augment/`, `skills-lock.json`, `.rtk/`, `.claude/cam_local/`. `rtk` dependency
  dropped.
- **`.claude/hooks/adr-gate.sh`** — `SRC_DIR` may list several space-separated roots.
- **`.claude/statusline.sh`** (new, wired in `settings.json`) — `<project> | <model> <mode>[ fast]
  | Ctx | Tok | Wk | Win/Cmp`. Mode read from last `"permissionMode"` in `transcript_path`
  (not present in the status JSON).
- **Docs** — `SETUP.md` Step 2 "Tune to the Project" (steps renumbered 3–9), runtime-state table
  in Step 1, stack-aware Docker step; `docs/ONBOARDING.md` steps 1–4 (confirm detection, adapt
  `CLAUDE.md` commands/Docker to the stack); `CLAUDE.md` onboarding pointer; `.gitignore`
  `.refmatrix/`.

## Review fixes (`/ch-review`) {#review-fixes}

Five-agent review (0 Critical; High findings overlapped) — triage in [[problem-log#install-project-tuning]]:

- **Security:** directory names were written unescaped into the sourced `hooks.env` (command
  injection). Paths now pass `SAFE_PATH_RE`, values are single-quoted, skeleton confined to root.
- **Evidence-only, for real:** Docker wrapping requires a `dev` compose service (tee only with a
  `/test-output` mount; venv only when Docker files show it); JVM commands need a build tool and
  use valid Maven goals.
- **Re-run contract:** `hooks.env` carries a `# tune-project:generated sha256=` digest and is
  regenerated while unchanged; the detection block is generator-owned; placeholder fields fill on
  every run; tuned profiles get `drift:` lines. Exit `3` = nothing tuned (install.sh → skipped).
- **Detection:** template-owned *paths* skipped (project `scripts/`/`tools/` count),
  token-anchored test/sample regexes, `--lang`/`--package` recompute layout, greenfield judged
  before overrides, `--db` normalised, non-object `package.json` tolerated.
- **Scaffold:** `.scaffoldignore` is the single exclusion list for rsync and a Python fallback
  (parity-tested); per-user `.claude/settings.local.json` no longer leaks; `--skip-rtk` accepted.
- **adr-gate:** root-relative matching, `set -f`.
- **Statusline:** `jq` guard, BSD+GNU date, week-key drift bug, per-session state by
  `session_id`, growth-based weekly tokens, atomic writes, `CH_STATUS_WEEK_TZ`.
- **Tests:** `.selftest/test_template_tooling.py` — 37 cases (tuner, install, adr-gate,
  statusline), stdlib only; CI `template-selftest` on Ubuntu 3.10/3.13 + macOS.

## Verification {#verification}

- `.selftest/run.sh`: 37/37 on Python 3.9, 3.10 and 3.14 (macOS).
- `ruff check` (E,F,W,B, line length 100) clean on the tuner and tests; `./scripts/lint-gmd.sh`
  clean; `bash -n` on all shell scripts.

Initial manual verification:

- Fixtures in the session scratchpad: Python src-layout, TS monorepo (npm workspaces + compose),
  Go, SQL greenfield, interactive greenfield via `script` pty, non-tty greenfield (no-op).
- Read-only `--dry-run` against sibling repos: `portal` (JS + SQL, non-conventional roots,
  `public/` UI, npm scripts), `atldb` (SQL-first, already tuned → untouched), `cliquet`
  (hand-tuned design-only profile → recognised as tuned), `atlapi` (venv dirs excluded).
- End-to-end `./install.sh <scratch> --minimal --no-prompt`: tuned, and no runtime-state dirs
  copied. In-place run skips tuning.
- `./scripts/lint-gmd.sh` clean; `bash -n` on shell scripts; statusline sample-JSON outputs.

## Known limitations {#limitations}

- `adr-gate` matches `class X` only → inert (`^$`) for Go/Rust/Elixir/SQL (todo GAP-001).
- Statusline mode depends on the transcript's `permissionMode` entries (deferral registry).
- Re-running install is not a baseline upgrade (todo GAP-002).
- The tuner deliberately does not expand `CLAUDE.md`/`.mcp.json` placeholders — prose there
  mentions them literally; the agent does it during onboarding.
- Awaiting decisions: statusline default-on (GAP-003), `.agents`/`.augment` tracking (GAP-004),
  ADR for install-time tuning (GAP-005).
