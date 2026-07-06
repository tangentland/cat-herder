---
gmd: "0.1"
id: constitution
title: "Project Constitution — governing principles (SDD gate)"
tags: [constitution, governance, sdd]
metadata:
  node_type: constitution
  version: "1.0.0"
  ratified: 2026-07-06
---

# Project Constitution {#root}

The governing principles every feature must honor. `/ch-plan` re-checks this file as a **gate**
before and after design; `/ch-analyze` verifies artifacts comply. Violations must be justified in
the plan's Complexity Tracking table or the design changes. Amend deliberately — bump `version`
and note the change in [[#amendments]].

> This is the baseline template's constitution. Replace/extend the project-specific principles
> below when you bootstrap a real project (`/ch-constitution`). The **non-negotiables** are the
> template's spine and should survive.

## Non-negotiable principles {#non-negotiable}

### I. Concrete production code {#concrete}

All `src/` code is fully concrete — no stubs, mocks, simulated behavior, fake implementations, or
placeholder logic. Every function/class/module does real work or does not exist yet. Mocks live
ONLY in test code, classified in `workflow/test_mock_registry.md`. Internal-subsystem mocks must
graduate when the real subsystem exists.

### II. No workarounds {#no-workarounds}

A missing dependency (table, service, config) is not worked around. Define the gap, propose the
real solution, ask before proceeding. Consult `workflow/development_resources.md` first.

### III. Reason from tenets {#from-tenets}

Every design proposal reasons FROM the architecture's tenets, not around them. Before a new
mechanism, verify an existing architectural primitive doesn't already solve it. No parallel
infrastructure when an existing conceptual alignment covers the concern. Architectural decisions
are captured as ADRs (`/ch-crucible`) between spec-clarify and plan; `plan.md` must cite them.

### IV. Tests are real and complete {#tests-real}

Tests run in the project's canonical environment (Docker where applicable) — ALL of them, never
skipped to dodge a broken environment. New auth-protected endpoints get a real-auth test; new
UI-facing response shapes get a contract test. Test tiers and mock governance per
`workflow/test_mock_registry.md`.

### V. GMD is the documentation substrate {#gmd}

All `docs/` and `workflow/` items are Graph Markdown: frontmatter (`gmd: "0.1"` + `id` + `title` +
`tags`), a `{#anchor}` on every heading, and typed `rel:` edges for citations. Validate with
`python3 tools/gmd/lint.py <path>` — zero errors — before commit.

### VI. Spec-driven flow {#sdd}

Non-trivial features follow the chain: `/ch-constitution → /ch-specify → /ch-clarify → /ch-crucible →
/ch-plan → /ch-tasks → /ch-analyze → /ch-implement`. Spec defines *what/why* (tech-agnostic);
ADRs capture architectural decisions; plan defines *how* and honors this constitution + the ADRs;
implementation is verified post-hoc by `/ch-review` + `@ch-bsd`.

## Project-specific principles {#project}

<!-- Add via /ch-constitution. Examples: performance budgets, security posture, data-handling
     rules, domain invariants, dependency policy. Each gets a stable {#anchor}. -->

### [PRINCIPLE_NAME] {#project-1}

[Description of a project-specific governing principle and its rationale.]

## Governance {#governance}

- **Gate authority:** `/ch-plan` MUST evaluate every principle here before Phase 0 and re-evaluate
  after Phase 1 design. `/ch-analyze` cross-checks spec/plan/tasks against it.
- **Deviation:** any violation is recorded in the plan's Complexity Tracking with justification,
  or the design is changed to comply. Unjustified violations block `/ch-implement`.
- **Precedence:** the non-negotiables ([[#non-negotiable]]) outrank project-specific principles on
  conflict.

## Amendments {#amendments}

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-07-06 | Initial baseline constitution (template). |
