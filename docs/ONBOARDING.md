---
gmd: "0.1"
id: ONBOARDING
title: "Agent Onboarding — first run in a template-bootstrapped project"
tags: [instructions, onboarding]
metadata:
  node_type: instructions
---

# Agent Onboarding {#root}

What **you (the agent)** do the first time you land in a project scaffolded from the cat-herder
template. This is the human-facing `SETUP.md` steps, driven by the agent. Run it ONCE, then never
again — subsequent sessions follow the normal `CLAUDE.md` Session Start.

## Detect an uninitialized template {#detect}

You are in a fresh, un-onboarded clone if ANY of these hold:

- `CLAUDE.md`, `.mcp.json`, or `.claude/PROJECT_PROFILE.md` still contain literal placeholders:
  `{PROJECT_NAME}`, `{project_package}`, `{project_db}`, `{PATH_TO_OMNISEARCH}`.
- `.claude/PROJECT_PROFILE.md` still has its `{…}` placeholder values.
- No `.claude/agents/*.local.md` overlays exist and `.claude/hooks/hooks.env` is absent.

Quick check: `grep -rl "{PROJECT_NAME}\|{project_package}" CLAUDE.md .mcp.json .claude/PROJECT_PROFILE.md`.
If it matches, run this onboarding. If nothing matches, the project is initialized — skip to
[normal work](#after).

**If you detect an uninitialized template, surface it to the user before mutating anything** — ask
for the project's name, package/module, stack, and DB (or confirm you should infer them from the
existing code). Then proceed.

## Onboarding sequence {#sequence}

Tuning to the project's actual languages and layout is part of the install, not an afterthought:
the template ships Python/Docker defaults, and every step below replaces a default with a fact.

1. **Install, tune, wire** — `./install.sh <path>` to scaffold elsewhere, or `./install.sh --tune`
   when this clone *is* the project (plain `./install.sh` in place treats the checkout as the
   template and skips tuning). It runs `scripts/tune-project.py`, which **detects** languages,
   source/test/UI/migration roots (conventional *and* non-conventional), monorepo workspaces,
   frameworks, storage, Docker, and evidence-backed commands — or, for a **from-scratch** project,
   **prompts** for them. It fills placeholder fields in `.claude/PROJECT_PROFILE.md` (plus an
   `Install detection` evidence section) and writes a tuned `.claude/hooks/hooks.env`. Then it wires
   GMD + SDD scripts and installs rmx/tldr/caveman when available. Re-runnable as a safe upgrade;
   project-authored values are never overwritten. See `SETUP.md` Step 2.
   *If the install ran without a terminal on a from-scratch project, nothing was tuned* — ask the
   user the stack questions and run `python3 scripts/tune-project.py --lang=… --name=… …`.
   **Never copy the template's runtime-state dirs** (`.refmatrix/`, `.tldr/`, `.agents/`,
   `.augment/`) into the project, even when installing by hand: cat-herder's `.refmatrix/`
   catalog would seed the project's rmx index with the template's content, so every
   `rmx context`/`query`/`memory` answer would describe cat-herder. If they are already present
   in the project from an older install, confirm with the user, delete them, and let rmx /
   tldr / the caveman installer rebuild them for this project (`SETUP.md` Step 1).
2. **Confirm + complete the project profile** — read `.claude/PROJECT_PROFILE.md` and its
   `Install detection` section with the user. Correct anything detection got wrong (it is a
   starting point: e.g. a scratch dir picked up as a source root, a minor language). Fill what
   detection cannot know: key libraries, target OS, architectural primitives, glossary,
   constraints. A command recorded as "none detected" means none exists — do not invent one; ask.
3. **Expand placeholders** — replace `{PROJECT_NAME}` / `{project_package}` / `{project_db}` /
   `{PATH_TO_OMNISEARCH}` across `CLAUDE.md`, `.mcp.json`, `handoff.md`, and the workflow docs
   (`SETUP.md` Step 3 lists them). Never leave a literal `{…}` placeholder in a live project.
4. **Adapt `CLAUDE.md` to the stack** — its Development Commands, container-venv rules, and quality
   gates are written for Python in Docker. Rewrite them from the profile's §commands for the real
   language(s) (e.g. `go test ./...`, `npm test`, `cargo clippy`), drop Python-only rules
   (`/opt/<pkg>-venv`, `uv`) from non-Python projects, and if the project does not run in Docker
   say so rather than keeping the Docker-only rule. Check `hooks.env` against the profile's
   layout (`SRC_DIR` may list several roots).
5. **Create per-agent overlays as needed** — copy `.claude/agents/<name>.local.md.example` →
   `.claude/agents/<name>.local.md` and fill project-specific guidance for the roles that need it
   (at minimum `ch-architect`, `ch-test-engineer`). Overlays are committed (they're this project's
   customization); the neutral committed `<name>.md` stays untouched.
6. **Set the constitution** — run `/ch-constitution` to record this project's governing principles
   under `## Project-specific principles` in `workflow/CONSTITUTION.md` (the non-negotiables ship
   filled; add domain rules, perf budgets, security posture, dependency policy).
7. **Optional — project guardrails** — add `.claude/p20-0/guardrails/<name>.md` (GMD, a fenced
   `guardrail:` block with `tier` + `rule`) for any project-specific action policy, then recompile
   (`python3 .claude/p20-0/compile_guardrails.py`). Requires rmx.
8. **Load hooks + verify** — restart Claude Code so `.claude/settings.json` hooks load; confirm
   `rmx --version` (memory layer) and that `./scripts/lint-gmd.sh` is clean.
9. **Commit the initialized state** — one commit: filled `PROJECT_PROFILE.md`, expanded CLAUDE.md /
   `.mcp.json`, `hooks.env`, `<name>.local.md` overlays, and the `/ch-constitution` output.

## After onboarding {#after}

The project is initialized. Follow `CLAUDE.md` Session Start, then drive real work through the
spec-driven-development chain — `/ch-specify` a first feature →
`/ch-clarify → /ch-crucible → /ch-plan → /ch-tasks → /ch-analyze → /ch-implement`. Capture
decisions to STM via the `refmatrix` MCP tool `rmx_focus_note` as you go.
