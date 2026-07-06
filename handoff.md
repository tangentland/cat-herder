---
gmd: "0.1"
id: handoff
title: "Session Handoff for {PROJECT_NAME}"
tags: [handoff, session]
metadata:
  node_type: handoff
---

# Session Handoff for {PROJECT_NAME} {#root}

Date: 2026-07-06

## Completed {#completed}

Unified `cat-herder` into the baseline Claude Code template — folded cliquedb (canonical),
refmatrix/rmx (engine), viascope (historical), and grafted spec-kit's SDD flow with an ADR gate.
Committed as `b1b9834` (130 files, +7944/-479). Full decision log D1–D12 in
`workflow/plans/unified-baseline-merge.md`.

- **SDD chain** — 8 `/ch-*` commands `constitution → specify → clarify → crucible → plan → tasks
  → analyze → implement`; `/ch-crucible` is the ADR gate (dispatches `@ch-architect`). Backing
  `scripts/sdd/`, GMD templates, `workflow/CONSTITUTION.md` gate.
- **Agents** — +`ch-alignment`, `ch-implementer`, `gmd-curator`; refreshed `ch-architect`/`ch-bsd`.
  Project-neutral + per-agent `.local.md` overlay + `.claude/PROJECT_PROFILE.md` (committed post-init).
- **rmx-only memory** — `settings.json` swaps wolf→rmx hooks (guarded). STM: `focus summarize
  --promote` at PreCompact/Stop, `focus context` on resume; agent STM ops via `refmatrix` MCP
  tools (`rmx_focus_note`, `rmx_change_subject`, …). Curated enforcement hooks. OpenWolf DROPPED;
  buglog → native `workflow/bug_registry.md`.
- **Workflow** — single status-driven `workflow/plans/` (`metadata.status`, no file moves);
  `plan-of-plans.md` = one index+sequence. Added `specs/`, TDD_GOVERNANCE, deferral+bug registries,
  session-state commands.
- **Docs** — full GMD transition (44 GMD docs, lint clean); instruction docs `CAPITALIZED.md`;
  CODEBASE_INDEX dropped for rmx nav; `.mcp.json` +refmatrix/tldr; CI + gmd-lint workflows.
- **Cross-project** — bus messages to refmatrix + cliquedb re: the `focus summarize --promote` bug
  (they ship the same regime) + MCP-first STM (`proj:refmatrix:bugs`, `:feature`, `proj:cliquedb:hello`).

## Git State {#git-state}

- Branch `unified-baseline-merge`, HEAD `b1b9834`. Working tree clean. **Push pending** (user pushes).
- Not merged to `main`.

## Next Steps {#next-steps}

- Push `unified-baseline-merge` and open/merge to `main` when ready.
- Optional: GMD-ify the one historical `past_handoffs/001` (currently the sole non-GMD warn).
- On any real project: run `./install.sh <path>`, fill `PROJECT_PROFILE.md` + `hooks.env`,
  create `<agent>.local.md` overlays, then `/ch-constitution` → `/ch-specify`.

## Past Sessions {#past-sessions}

| # | Session | Date | Archive |
|---|---------|------|---------|
| 001 | Template bootstrap | 2026-06-11 | workflow/past_handoffs/001-template-bootstrap_2026-06-11.md |
| 002 | ch-bsd port | 2026-06-11 | workflow/past_handoffs/002-ch-bsd-port_2026-06-11.md |

## Hand-Off Notes {#hand-off-notes}

- This is the cat-herder template source itself — `{PLACEHOLDER}` values remain unexpanded.
- Source authority: cliquedb = canonical, refmatrix = rmx engine, viascope = historical only.
- rmx STM subject for this work: `unified-baseline-merge` (promoted digest in durable memory).
