# Quick Reference

## Docker Commands (ALL commands in Docker — never on host)

```bash
docker compose up -d                                                                                     # Start
docker compose exec dev bash -c "/opt/{pkg}-venv/bin/python -m pytest -v 2>&1 | tee /test-output/pytest.log"  # Test
docker compose exec dev bash -c "/opt/{pkg}-venv/bin/python -m ruff check . 2>&1 | tee /test-output/ruff.log" # Lint
docker compose exec dev bash -c "/opt/{pkg}-venv/bin/python -m mypy src/{pkg} 2>&1 | tee /test-output/mypy.log" # Types
```

## Reading Test Output (from host)

```bash
tail -20 docker/test-output/pytest.log    # Summary
cat docker/test-output/pytest.log          # Full
```

## Git Workflow

```bash
git checkout -b task-X.Y-description main    # New branch per task
git checkout main && git merge --no-ff task-X.Y-description  # Merge when complete
```

## Quality Gates (Before Commit)

1. Implementation summary written to `workflow/implementation_summaries/<task-name>.md`
2. Tests pass in Docker — ALL tests including system-dependent tests
3. `ruff check .` clean
4. `mypy` clean (strict mode)
5. Code review (@ch-code-reviewer + @ch-architect) — no Critical/High
6. Test review (@ch-test-engineer) — adequate coverage
7. Gap audit (@ch-gap-master) — todo.md current, mocks graduated, no workarounds
8. Docs review (@ch-doc-writer) — indexes updated, docs/ suite current
9. Real-auth test exists for new auth-protected endpoints
10. Contract test exists for new UI-facing response shapes
11. Cleanup phase completed after implementation chunk (if applicable)

## Key Conventions

- Line length: 100 characters (Black)
- Strict type hints (mypy strict)
- No mocks in `src/` — only in `tests/`
- No placeholders, stubs, or `NotImplementedError` in production code
- All API keys via `${ENV_VAR}` — never hardcode secrets
- Write decisions to files immediately — never defer to session end
- New prose docs are GMD — lint with `./scripts/lint-gmd.sh` (zero errors before commit)

## Lookup Priority

| Need | Consult First | Then |
|------|---------------|------|
| Prior work | `handoff.md` + `workflow/past_handoffs/` | Indexes |
| Code structure | `docs/CODEBASE_INDEX.md` | Source files |
| Architecture | `docs/architecture/ARCHITECTURE_INDEX.md` | Architecture docs |
| Patterns | `workflow/QUICK_REFERENCE.md` | `workflow/PATTERNS.md` |
| Symbol / call graph | `rmx context <symbol>` → `tldr` | `rmx grep` → raw grep |
| GMD authoring | `docs/gmd/PRIMER.md` | `docs/gmd/SPEC.md` |
| Gaps | `docs/architecture/todo.md` | — |
| Design research | `docs/architecture/explorations/` | Exploration docs |
| Active plans | `workflow/incomplete_plans/plan-of-plans.md` | `workflow/incomplete_plans/todo.md` |
| Approved task specs | `workflow/plans/<plan>-tasks/` | Plan file in `workflow/plans/` |

## Session Start Checklist

1. Read `handoff.md`
2. Read `workflow/incomplete_plans/plan-of-plans.md` for what to implement next
3. Read `docs/architecture/ARCHITECTURE_INDEX.md`
4. Read `docs/architecture/README.md` for architecture overview
5. Verify git state matches handoff
6. Check `docs/architecture/todo.md`
7. If implementing: read active plan from `workflow/plans/` or `workflow/incomplete_plans/`

## Planning Pipeline (Three-Stage Lifecycle)

```
Exploration (research) → Proposed Plan (decisions) → ADR (if architectural) → Task Specs → Implementation
```

**Stage 1 — Drafting:** `workflow/incomplete_plans/<plan-name>.md`
**Stage 2 — Approved:** `workflow/plans/<plan-name>.md` + `workflow/plans/<plan>-tasks/`
**Stage 3 — Completed:** `workflow/completed_plans/<plan-name>.md`

- Write proposed plans to `workflow/incomplete_plans/` BEFORE presenting questions
- After plan approval: create ALL task spec files in `workflow/plans/<plan>-tasks/` before implementing any task
- `workflow/incomplete_plans/plan-of-plans.md` is the source of truth for execution order
