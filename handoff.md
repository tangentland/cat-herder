---
gmd: "0.1"
id: handoff
title: "Session Handoff for {PROJECT_NAME}"
tags: [handoff, session]
metadata:
  node_type: handoff
---

# Session Handoff for {PROJECT_NAME} {#root}

Date: 2026-09-29

## Completed {#completed}

**Stack-aware install tuning** — `install.sh` now tunes the scaffold to the target project
(`workflow/implementation_summaries/install-project-tuning.md`).

- **`scripts/tune-project.py`** — detects languages (15 incl. SQL), conventional *and*
  non-conventional source roots, tests/UI/migrations, monorepos, frameworks, storage, Docker, and
  **evidence-only** commands; prompts for from-scratch projects. Fills only placeholder fields of
  `PROJECT_PROFILE.md` (+ generator-owned `Install detection` block), writes a digest-owned
  `hooks.env`, reports `drift:` on tuned profiles. Exit `3` = nothing tuned.
- **`install.sh`** — tuning step + flags; `.scaffoldignore` = single runtime-state exclusion list
  (rsync + Python fallback); in-place template runs skip tuning unless `--tune`; rtk dropped.
- **Statusline** — `.claude/statusline.sh` shows model + permission mode; portable (BSD/GNU date,
  jq guard), per-session accounting.
- **`/ch-review` run** — 5 agents, 0 Critical; all High + most Medium fixed on
  `install-tuning-review-fixes`. Triage: `docs/problem_log.md`. Bugs 002–006 in
  `workflow/bug_registry.md`.
- **Tests** — `.selftest/` (37 cases, stdlib, no mocks; passes on Python 3.9/3.10/3.14) + CI
  `template-selftest.yml` (Ubuntu 3.10/3.13, macOS).
- Verified against sibling repos read-only (`--dry-run`): portal, atldb, cliquet, atlapi.

## Git State {#git-state}

- `main` at the merge of `install-tuning-review-fixes` (branch kept; earlier
  `install-project-tuning` merged as `f7159c8`). Not pushed.

## Next Steps {#next-steps}

- Decisions recorded 2026-09-29: statusline on by default (GAP-003); caveman dirs stay tracked
  as vendored (GAP-004); ADR-0001 written for install-time tuning (GAP-005).
- Resolveable gaps: GAP-001 per-language adr-gate declarations; GAP-002 baseline upgrade path;
  GAP-006 `.refmatrix/` ignore for targets with an existing `.gitignore`; GAP-007 derive
  hooks.env from the profile (`--sync-hooks`) so PROFILE is truly authoritative.
- atlapi has no cat-herder install yet (user to decide); portal's own instance handles portal.

## Past Sessions {#past-sessions}

| # | Session | Date | Archive |
|---|---------|------|---------|
| 001 | Template bootstrap | 2026-06-11 | workflow/past_handoffs/001-template-bootstrap_2026-06-11.md |
| 002 | ch-bsd port | 2026-06-11 | workflow/past_handoffs/002-ch-bsd-port_2026-06-11.md |
| 003 | Unified baseline merge | 2026-07-06 | workflow/past_handoffs/003-unified-baseline-merge_2026-07-06.md |

## User Preferences {#user-preferences}

- Installs must be tuned to the target's real structure; never invent commands or layout.
- Template runtime state (`.refmatrix`, `.tldr`, `.agents`, `.augment`) must never be copied.
- Sibling repos (portal, atldb, cliquet, atlapi) are references; portal's own Claude instance
  installs cat-herder there.

## Hand-Off Notes {#hand-off-notes}

- This is the cat-herder template source itself — `{PLACEHOLDER}` values remain unexpanded.
- Run `.selftest/run.sh` after touching the tuner, install.sh, hooks or statusline.
- Review reports: `workflow/review-output/install-project-tuning-*.md` (gitignored, local only).
