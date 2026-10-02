---
gmd: "0.1"
id: cat-herder/architecture-todo
title: "Architecture Gap Tracking"
tags: [architecture, todo, gaps]
---

# Architecture Gap Tracking {#root}

Authoritative architecture gap surface, curated by @ch-gap-master. Every entry carries a
status, a concrete blocker (if Deferred), and source/decision references.

## Status Vocabulary {#status}

| Status | Meaning |
|--------|---------|
| Deferred | Blocked by a named, concrete dependency |
| Resolveable | Can be addressed now with existing infrastructure |
| Planned | Task defined, scheduled in a plan |
| Integrated | Shipped and verified in source |

## Open Gaps {#open-gaps}

| ID | Status | Description | Dependencies | Source Ref | Decision Ref |
|----|--------|-------------|--------------|------------|--------------|
| GAP-001 | Resolveable | adr-gate matches `class X` only, so the tuner sets `ADR_GATE_FILE_RE='^$'` (gate inert) for Go/Rust/Elixir/SQL and misses interface/struct/trait/record declarations | per-language declaration regex in hooks.env + tuner | `.claude/hooks/adr-gate.sh`; `scripts/tune-project.py` `hooks_env` | review: install-project-tuning phase 1/3 |
| GAP-002 | Resolveable | Re-running install.sh is not a baseline upgrade: `rsync --ignore-existing` never refreshes existing files, so projects keep old agent defs / tuner / hooks | manifest of template-owned paths safe to refresh | `install.sh` `scaffold_project` | review: install-project-tuning architect M6 |
| GAP-003 | Integrated | Statusline ships default-on via project `settings.json` (overrides an adopter's personal status line); reset zone defaults to America/Los_Angeles (`CH_STATUS_WEEK_TZ`). **Decided 2026-09-29: on by default**; opt-out documented in SETUP.md | — | `.claude/settings.json`; `.claude/statusline.sh` | review: gap-master M-3, architect M7 |
| GAP-004 | Integrated | `.agents/`, `.augment/`, `skills-lock.json` are tracked in the template although excluded from scaffolds. **Decided 2026-09-29: keep tracked, documented as vendored** (`.scaffoldignore`, SETUP.md#scaffold) | — | `.scaffoldignore`; `.gitignore` | review: gap-master M-5, architect M4 |
| GAP-005 | Integrated | No ADR records project-fact ownership (PROFILE authoritative, hooks.env derived + digest-owned, detection block generator-owned, evidence-only commands, re-run vs upgrade) | Recorded in [[adr-0001-project-fact-ownership-and-install-time-tuning]] (Accepted 2026-09-29) | `scripts/tune-project.py`; `SETUP.md#tune` | review: architect ADR recommendation |
| GAP-007 | Resolveable | hooks.env is derived from detection, not from PROJECT_PROFILE: correcting the profile's `Source root` while leaving hooks.env untouched means the next re-run rewrites `SRC_DIR` from detection, contradicting "PROFILE is authoritative" | `tune-project.py --sync-hooks` (derive hooks.env from profile fields) | `scripts/tune-project.py` `hooks_env` | ADR-0001 negative consequence / alternative 5 |
| GAP-006 | Resolveable | A target that already has a `.gitignore` never receives the `.refmatrix/` ignore line (scaffold does not merge files) | — | `install.sh`; `.gitignore` | review: test-engineer observation |

rel: depends-on -> [[architecture-index]]
