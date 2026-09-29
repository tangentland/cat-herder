---
gmd: "0.1"
id: problem-log
title: "Problem Log — agent-surfaced issues from reviews"
tags: [log, review]
metadata:
  node_type: log
---

# Problem Log {#root}

Issues surfaced by `/ch-review` agents, with their triage outcome. Bugs that were fixed are also
recorded in `workflow/bug_registry.md`; open gaps in the architecture todo list.

rel: related-to -> [[architecture-todo]]

## 2026-09-29 — install-project-tuning review {#install-project-tuning}

Scope `6ecf626..f7159c8`; reports in `workflow/review-output/install-project-tuning-*.md`
(gitignored). Counts: code-reviewer 2H/6M/13L, architect 2H/8M/5L, test-engineer 1H/5M/2L,
gap-master 3H/5M/5L, doc-writer 0H/3M/7L — heavily overlapping.

| Finding (merged) | Severity | Outcome |
|------------------|----------|---------|
| hooks.env shell injection from directory names | High | fixed (bug-002) |
| Docker/venv/tee invented when any compose file exists | High | fixed (bug-004) |
| Re-run contract false: hooks.env never regenerated, detection block stale | High | fixed — digest-owned hooks.env, generator-owned block, `drift:` report |
| "Nothing tuned" reported as tuned by install.sh | High | fixed — exit 3 → skipped |
| Statusline BSD-only date, no jq guard, weekly accounting wrong | High | fixed (bug-003, bug-006) |
| No tests for the new tooling | High | fixed — `.selftest/` (37 cases) + `template-selftest` CI |
| Placeholder check clobbered values containing `{` | Medium | fixed — template-token rule |
| Project-owned `scripts/`/`tools/` invisible; `spectrum/` dropped by substring match | Medium | fixed — template paths, token-anchored regexes |
| JVM commands invented / invalid Maven goals | Medium | fixed |
| `--no-prompt` created a skeleton unasked; `--lang`/`--package` did not recompute layout | Medium | fixed (bug-005 found by the new tests) |
| Scaffold leaked `settings.local.json`; two copy paths diverged | Medium | fixed — `.scaffoldignore` read by both paths, parity test |
| SETUP anchors renumbered (ids moved) | Medium | fixed — semantic anchors + wikilinks |
| "Safe upgrade" claim false | Medium | docs corrected; mechanism deferred (GAP-002) |
| adr-gate class-only / inert for Go, Rust, SQL | Medium | documented; deferred (GAP-001) |
| adr-gate matched absolute path; unquoted glob | Low | fixed |
| Statusline default-on / timezone; `.agents` tracking; ADR | Medium | awaiting user decision (GAP-003/004/005) |
| Doc drift (omnisearch placeholder, overlay "gitignored", help text, lint scope) | Medium/Low | fixed |
