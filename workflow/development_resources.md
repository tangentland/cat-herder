---
gmd: "0.1"
id: development_resources
title: "Development Resources"
tags: [reference]
metadata:
  node_type: doc
---

# Development Resources {#root}

Inventory of available infrastructure and services. Consult this before implementing
features — use what exists rather than creating workarounds.

## Docker Services {#docker-services}

| Service | Image | Port (host:container) | Purpose |
|---------|-------|----------------------|---------|
| dev | custom Dockerfile | — | Development container |
| postgres | postgres:16 | 5433:5432 | PostgreSQL database |

## Database {#database}

**PostgreSQL 16** available in Docker compose.

| Schema | Tables | Purpose |
|--------|--------|---------|
| public | *(define as migrations are added)* | Application data |

## Environment Variables {#environment-variables}

| Variable | Required | Purpose |
|----------|----------|---------|
| `GITHUB_PERSONAL_ACCESS_TOKEN` | Yes (for GitHub MCP) | GitHub API access |
| `TAVILY_API_KEY` | Optional | Web search via onmisearch |
| `BRAVE_API_KEY` | Optional | Web search via onmisearch |
| `KAGI_API_KEY` | Optional | Web search via onmisearch |
| `EXA_API_KEY` | Optional | Web search via onmisearch |

## Test Infrastructure {#test-infrastructure}

| Tool | Location | Notes |
|------|----------|-------|
| pytest | Docker container | Primary test runner |
| testcontainers | tests/ | Ephemeral PostgreSQL for tests outside Docker |
| ruff | Docker + local | Linter |
| mypy | Docker + local | Type checker |
| black | Docker + local | Formatter |

## Planning & Documentation Infrastructure {#planning-documentation-infrastructure}

| Directory | Purpose |
|-----------|---------|
| `workflow/plan-of-plans.md` | Plan index + sequenced execution order (Status column) |
| `workflow/plans/` | All plans, permanently + `<plan>-tasks/` spec dirs; stage = `metadata.status` (`drafting` → `approved` → `in-progress` → `completed`) |
| `docs/architecture/` | Architecture docs, ADRs, explorations |
| `workflow/implementation_summaries/` | Per-task implementation summaries |
| `workflow/review-output/` | Agent review output files |
| `workflow/past_handoffs/` | Archived session handoffs |

---

*Update this file when new services, tables, or infrastructure are added.*
