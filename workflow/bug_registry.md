---
gmd: "0.1"
id: bug_registry
title: "Bug Registry — known bugs, root causes, and fixes"
tags: [process, bugs, governance]
metadata:
  node_type: registry
---

# Bug Registry {#root}

Curated log of bugs encountered and fixed — sibling to the mock and deferral registries. Where
[[test_mock_registry]] classifies test-side mocks and [[deferral_registry]] tracks deferred
functionality, this registry captures **bugs**: what broke, why, and the fix — so the same mistake
is not re-derived across sessions. Managed the same way (curated, classified, GMD-linted);
`@ch-gap-master` keeps it current, `@ch-bsd` mines it for recurring cheap-fix patterns.

rel: part-of -> [[test_mock_registry]]

## When to log {#when}

The threshold is LOW — when in doubt, log it. Log an entry whenever:

- The user reports an error, bug, or problem ("doesn't work", "broken", "shows wrong X").
- A test, build, lint, or type check fails, or a runtime/import/type/syntax error occurs.
- You fix something that was broken, or change error-handling / validation logic.
- You edit the same file more than twice to get one thing right (a signal it was a bug).

**Before fixing:** search this registry first — the fix may already be known. If `rmx` is present,
`rmx memory search "<symptom>"` also surfaces past occurrences.

## Status {#status}

| Status | Meaning |
|--------|---------|
| `open` | Reproduced, not yet fixed |
| `fixed` | Fix landed + verified |
| `recurring` | Seen again after a prior fix — needs a durable/root fix |

## Registry {#registry}

| ID | Symptom / error | File(s) | Root cause | Fix | Tags | Status | Seen |
|----|-----------------|---------|------------|-----|------|--------|------|
| bug-001 | `gmd init gmd-agents` silently skips every agent: `skip <path>: no template for 'ch-doc-writer'` | `tools/gmd/init.py` | `AGENT_TEMPLATES` was keyed by the pre-rename `vs-*` agent names, but the template's agents are named `ch-*`, so the frontmatter-`name` lookup never matched | Renamed the three keys and their `TEXT_VS_*` constants to `ch-doc-writer` / `ch-alignment` / `ch-bsd` | gmd, tooling, agent-rename, stale-vendor | fixed | 1 |

<!--
Entry conventions:
- ID: bug-NNN, zero-padded, monotonic.
- Symptom: the exact error string or user complaint (quote errors verbatim).
- Root cause: WHY it broke, not just where.
- Fix: what changed to resolve it (file:function or the concrete edit).
- Tags: kebab keywords for search (e.g. auth, off-by-one, import, migration).
- Seen: occurrence count; bump + flip Status to `recurring` if it reappears.
-->
