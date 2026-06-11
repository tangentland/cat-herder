# Workflow Index

Map of the `workflow/` process tree. `docs/` holds knowledge (architecture, guides,
reference); `workflow/` holds process (plans, governance, templates, audits, summaries).

## Planning

| Path | Purpose |
|------|---------|
| `incomplete_plans/plan-of-plans.md` | Sequenced execution order (source of truth) |
| `incomplete_plans/todo.md` | All plans, indexed |
| `incomplete_plans/` | Draft plans (no task specs yet) |
| `plans/` | Approved plans + `<plan>-tasks/` spec dirs |
| `completed_plans/` | Archived completed plans |
| `PLANNING_WORKFLOW.md` | How to plan, explore, and gate approval |
| `PLAN_GOVERNANCE.md` | Lifecycle, staleness, question-forcing |

## Reference

| Path | Purpose |
|------|---------|
| `QUICK_REFERENCE.md` | Fast pattern/command lookup |
| `PATTERNS.md` | Copy-paste code patterns |
| `TECH_STACK_DECISIONS.md` | Approved libraries + rationale |
| `development_resources.md` | Available infrastructure inventory |
| `test_mock_registry.md` | Mock governance registry |
| `templates/` | Document templates (task-spec, proposed-plan, exploration, handoff) |

## Audit & Output

| Path | Purpose |
|------|---------|
| `bullshit/` | @ch-bsd runtime-integration audit memory (INDEX, IMPRESSIONS, findings) |
| `implementation_summaries/` | Per-task implementation summaries |
| `session-summaries/` | Per-session summaries |
| `review-output/` | Agent review reports (gitignored — runtime) |
| `functional-tests/` | Functional/E2E test inventory |
| `validation/` | Validation artifacts |
| `change_sets/` | Grouped change records |
| `past_handoffs/` | Archived session handoffs |
