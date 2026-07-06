---
gmd: "0.1"
id: handoff
title: "Session Handoff for {PROJECT_NAME}"
tags: [handoff, session]
metadata:
  node_type: handoff
---

# Session Handoff for {PROJECT_NAME} {#root}

Date: 2026-06-11

## Completed {#completed}

- Ported the viascope `vs-bsd` runtime-integration auditor into the template as `ch-bsd`
  (the bullshit detector), sanitized of all viascope-specific content.
- New files:
  - `.claude/agents/ch-bsd.md` — sanitized agent. Lint clean (`python3 tools/gmd/lint.py`).
  - `.claude/commands/ch-bsd.md` — `/ch-bsd [commit range]` command (default `HEAD~1..HEAD`).
- Wired into `CLAUDE.md`:
  - Available Agents table — `@ch-bsd` row
  - Useful Commands table — `/ch-bsd` row
  - Session Start — new step 7: read `workflow/bullshit/` (unaddressed BULLSHIT = first priority)
  - Quality Gates / Before Commit — new checklist line for `@ch-bsd`

## Sanitization Applied (vs-bsd → ch-bsd) {#sanitization-applied}

- Kept "bullshit detector" in name/identity per user request.
- Stripped: ADR catalog (0104-0107), M0-M8 decision-surface cheat-sheet, viascope-dev
  container + `/opt/viascope-venv` two-python trap, `src/viascope/`, GraphQL/`ObserverRuntime`/
  `ChannelConfig`/`supervisor.start_channel`/Guide internals, hardcoded domain stats.
- Genericized checks: Observer→"Handler/Observer Registration", Channel→"Worker/Service
  Startup", Guide→"Wiring"; frontend + E2E marked `(if applicable)` with `{Customize}` notes.
- Template conventions: `model: inherit`, `tags: [agent, cat-herder]`, `{project_package}`
  placeholders, `tools/gmd/lint.py`, `docker compose exec dev`, rmx/tldr gated "if available".
- Kept intact (generic, high-value): cheap-fix detection, deferral-comment detection,
  severity/escalation, `workflow/bullshit/` memory layers, leaderboard, GMD finding output.

## Git State {#git-state}

- Not a git repository (this is the claude_template source). No commit made.

## Next Steps {#next-steps}

- Optional: port remaining viascope `vs-*` agents (vs-refactor-expert,
  vs-root-cause-analyzer, vs-gstreamer-validator, etc.) into `ch-*` template agents on demand.
- The `workflow/bullshit/` directory is created on first `/ch-bsd` run; no seed needed.

## Past Sessions {#past-sessions}

| # | Session | Date | Archive |
|---|---------|------|---------|
| 001 | Template bootstrap | 2026-06-11 | workflow/past_handoffs/001-template-bootstrap_2026-06-11.md |

## User Preferences {#user-preferences}

- When porting viascope `vs-*` agents into the template: sanitize all project-specific
  content but preserve the agent's evocative name/identity (e.g. "bullshit detector").
- Caveman communication mode active (full) for this session.

## Hand-Off Notes {#hand-off-notes}

- This is the claude_template source repo itself, not a bootstrapped project — `{PLACEHOLDER}`
  values remain intentionally unexpanded.
- `ch-bsd` is the first non-stock agent added beyond the template's stock `ch-*` set.
