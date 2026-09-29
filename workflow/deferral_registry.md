---
gmd: "0.1"
id: deferral_registry
title: "Deferral Registry — deferred production functionality"
tags: [process, deferral, governance]
metadata:
  node_type: registry
---

# Deferral Registry {#root}

Companion to [[test_mock_registry]]. Where the mock registry classifies **test-side mocks**, this
registry tracks **deferred production functionality** — features intentionally not built yet,
shipped as **fail-closed seams** (an honest `feature_not_supported`-style raise), **inert
self-sentinels**, or **scaffolding with no current caller** — each gated on a concrete future
trigger (an Accepted-but-unimplemented ADR, a later phase, or a platform/deployment).

rel: part-of -> [[test_mock_registry]]

A deferral is **legitimate** only if it (a) fails closed or is inert — never a silent wrong
answer — and (b) names a concrete graduation trigger with an owner. A deferral that silently
self-resolves, or has no graduation owner, is a **bug**, not a deferral. `@ch-gap-master` curates
this registry; `@ch-bsd` flags stale deferrals.

## Classification {#classification}

| Classification | Meaning | Behavior now |
|----------------|---------|--------------|
| `fail-closed-seam` | Real seam that raises/refuses on the unbuilt path | Refuses honestly |
| `inert-sentinel` | Placeholder value/branch with no active effect | No effect |
| `scaffold-no-caller` | Structure built ahead of its first caller | Unreachable in prod |

## Registry {#registry}

| Item | Location | Classification | Graduation Trigger | Owner |
|------|----------|----------------|--------------------|-------|
| adr-gate inert for non-class languages | `scripts/tune-project.py` `hooks_env` (`ADR_GATE_FILE_RE='^$'`); `.claude/hooks/adr-gate.sh` | `inert-sentinel` | Per-language declaration regex lands (todo GAP-001); documented in SETUP.md#tune and the profile's detection block | @ch-gap-master |
| Statusline permission mode read from the transcript | `.claude/statusline.sh` (`permissionMode` grep of `transcript_path`) | `inert-sentinel` | Claude Code exposes the permission mode in the statusLine JSON — swap the transcript grep for that field; until then the mode is simply omitted if the format changes | @ch-gap-master |

## Graduation Log {#graduation-log}

| Date | Item | Trigger fired | Notes |
|------|------|---------------|-------|
| — | — | — | — |
