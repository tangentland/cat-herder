# Codebase Index

Navigation index for `{PROJECT_NAME}` source. Update this as the code grows — it is the
first stop on the discovery ladder (`rmx context` → `tldr` → this index → raw grep).

## Layout

| Path | Contents |
|------|----------|
| `src/{project_package}/` | Production source (fully concrete — no mocks) |
| `tests/` | Test suite (mocks only for external deps; see `workflow/test_mock_registry.md`) |
| `ui/` | Frontend (if applicable) |
| `docker/` | Container build + entrypoint |

## Key Modules

| Module | Responsibility | Entry point |
|--------|----------------|-------------|
| _add as code lands_ | — | — |

## Entry Points

| Surface | File | Notes |
|---------|------|-------|
| App startup | `src/{project_package}/...` | — |
| API routes | — | — |
| Background workers | — | — |

## Conventions

- Line length 100 (Black). Strict mypy. See `workflow/QUICK_REFERENCE.md` for patterns.
