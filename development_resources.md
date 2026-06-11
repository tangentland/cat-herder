# Development Resources

Inventory of available infrastructure and services. Consult this before implementing
features — use what exists rather than creating workarounds.

## Docker Services

| Service | Image | Port (host:container) | Purpose |
|---------|-------|----------------------|---------|
| dev | custom Dockerfile | — | Development container |
| postgres | postgres:16 | 5433:5432 | PostgreSQL database |

## Database

**PostgreSQL 16** available in Docker compose.

| Schema | Tables | Purpose |
|--------|--------|---------|
| public | *(define as migrations are added)* | Application data |

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Yes (for GitHub MCP) | GitHub API access |
| `TAVILY_API_KEY` | Optional | Web search via onmisearch |
| `BRAVE_API_KEY` | Optional | Web search via onmisearch |
| `KAGI_API_KEY` | Optional | Web search via onmisearch |
| `EXA_API_KEY` | Optional | Web search via onmisearch |

## Test Infrastructure

| Tool | Location | Notes |
|------|----------|-------|
| pytest | Docker container | Primary test runner |
| testcontainers | tests/ | Ephemeral PostgreSQL for tests outside Docker |
| ruff | Docker + local | Linter |
| mypy | Docker + local | Type checker |
| black | Docker + local | Formatter |

## Planning & Documentation Infrastructure

| Directory | Purpose |
|-----------|---------|
| `workflow/incomplete_plans/` | Draft plans (design phase, no task specs) |
| `workflow/plans/` | Approved plans with task spec directories |
| `workflow/completed_plans/` | Archived completed plans |
| `docs/architecture/` | Architecture docs, ADRs, explorations |
| `workflow/implementation_summaries/` | Per-task implementation summaries |
| `workflow/review-output/` | Agent review output files |
| `workflow/past_handoffs/` | Archived session handoffs |

---

*Update this file when new services, tables, or infrastructure are added.*
