# Plan Governance

Lifecycle, staleness, and question-forcing rules for plans. Companion to
`workflow/PLANNING_WORKFLOW.md` (the how-to) — this file is the policy.

## Lifecycle Gates

1. **Drafting** (`incomplete_plans/`) — design in flux, no task specs yet.
2. **Approved** (`plans/` + `plans/<plan>-tasks/`) — every task has a written spec
   (deliverables, key functions/classes, acceptance criteria, test plan).
3. **Completed** (`completed_plans/`) — all tasks shipped and verified.

**Complete-Plan Gate:** Do not write production code for a plan until every task in it is
fully specified. If specs are missing, writing them is the first task.

## Staleness

| Age since last update | Action |
|-----------------------|--------|
| 0–14 d | Normal |
| 15–30 d | Verify active work |
| 31–60 d | Re-justify or reclassify |
| 60+ d | Critical — likely abandoned; escalate |

## Question-Forcing

A plan that reaches approval with vague deliverables, missing API signatures, or unclear
integration points is **blocked** — present it to the user before implementation. Ambiguity
is a stop condition, not a thing to resolve mid-code.

## Source-of-Truth Order

1. `workflow/incomplete_plans/plan-of-plans.md` — what's next
2. `workflow/incomplete_plans/todo.md` — all plans indexed
3. `workflow/plans/` — approved plans with task specs
4. `workflow/incomplete_plans/` — draft plans
