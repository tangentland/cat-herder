# Plan of Plans — Sequenced Execution Order

**Source of truth for what to implement next.** Lists every plan in dependency order with
its current stage. @ch-gap-master keeps this current.

## Execution Sequence

| # | Plan | Stage | Location | Depends On |
|---|------|-------|----------|------------|
| 1 | _first plan_ | drafting | `workflow/incomplete_plans/` | — |

## Stage Lifecycle

```
drafting (incomplete_plans/)  →  approved (plans/ + plans/<plan>-tasks/)  →  completed (completed_plans/)
```

## Notes

- A plan is **approved** only when every task in it has a written spec under
  `workflow/plans/<plan>-tasks/`.
- See `workflow/incomplete_plans/todo.md` for the full indexed plan list.
- See `workflow/PLAN_GOVERNANCE.md` for staleness rules and the question-forcing gate.
