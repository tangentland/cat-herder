# Test Mock Registry

Mock governance for `{PROJECT_NAME}`. Every mock in `tests/` is classified here. Production
code (`src/`) contains **no mocks** — see CLAUDE.md "No Mocks in Production Code".

## Classification

| Classification | Meaning | Allowed? |
|----------------|---------|----------|
| `external` | External library, platform API, third-party service | Permanent |
| `internal-active` | Internal subsystem with existing implementation | **Must graduate** |
| `internal-pending` | Internal subsystem not yet built | Temporary |

## Registry

| Mock | Target | Classification | Test File(s) | Graduation Plan |
|------|--------|----------------|--------------|-----------------|
| _none yet_ | — | — | — | — |

## Graduation Log

| Date | Mock | From → To | Notes |
|------|------|-----------|-------|
| — | — | — | — |
