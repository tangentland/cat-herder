---
gmd: "0.1"
id: project-profile
title: "Project Profile — shared project specifics for neutral agents & hooks"
tags: [config, project-profile]
metadata:
  node_type: project-profile
---

# Project Profile {#root}

Single source of **project-specific facts** that the baseline template's project-neutral agent
definitions, commands, and hooks pull in by reference. Fill the placeholders when you bootstrap a
project. Agents read the sections relevant to their task; they never hardcode these facts.

> **How inclusion works.** Committed agent defs (`.claude/agents/<name>.md`) stay neutral. Each may
> have an optional overlay `.claude/agents/<name>.local.md` (gitignored) for role-specific project
> detail. This file holds the facts common to *all* agents + hooks. CLAUDE.md `@`-imports it so it
> is ambient context. See `.claude/agents/<name>.local.md.example` for the overlay shape.

## Identity {#identity}

- **Name:** {PROJECT_NAME}
- **One-liner:** {one-line description}
- **Package / module:** {project_package}

## Stack {#stack}

- **Language(s):** {e.g. Python 3.14, TypeScript}
- **Frameworks:** {e.g. FastAPI, React}
- **Storage:** {e.g. PostgreSQL, Lance}
- **Key libraries:** {…}
- **Target OS:** {e.g. Ubuntu 24.04}

## Directory layout {#layout}

- **Source root:** `src/{project_package}/`
- **Tests:** `tests/`
- **UI (if any):** `ui/`
- **Migrations/schema:** {e.g. `alembic/`, `sql/`, or `—`}
- **ADRs:** `docs/architecture/adr/`
- **Pseudocode ground truth (if used):** {`pseudocode/` or `—`}

## Commands {#commands}

All commands run in Docker (see CLAUDE.md). The venv is at `/opt/{project_package}-venv`.

- **Test:** `docker compose exec dev bash -c "/opt/{project_package}-venv/bin/python -m pytest -v 2>&1 | tee /test-output/pytest.log"`
- **Lint:** `… ruff check . 2>&1 | tee /test-output/ruff.log`
- **Type check:** `… mypy src/{project_package} 2>&1 | tee /test-output/mypy.log`
- **Format check:** `… black --check . --line-length 100 …`
- **UI tests (if any):** {`cd ui && npx vitest run`, `npm run test:e2e`}

## Discovery corpus {#corpus}

Paths the discovery-ladder hook treats as the indexed corpus (grep here → use `rmx` instead).
Mirror these into `.claude/hooks/hooks.env` (`CORPUS_PATHS`, `SRC_DIR`, `ADR_DIR`).

- **Corpus roots:** `src docs workflow tests {ui/src}`
- **Source extensions:** `.py .ts .tsx .js .md .sh .json .yaml .toml`

## Architectural primitives {#primitives}

<!-- The core concepts/abstractions of this system that every agent should reason from.
     e.g. "Channel", "DPath", "Zone". One line each. Reason FROM these (Constitution III). -->

- {PrimaryConcept} — {one-line role}
- {OtherConcept} — {one-line role}

## Domain glossary {#glossary}

<!-- Project-specific terms an agent would otherwise misread. -->

- **{Term}** — {definition}

## Project constraints {#constraints}

<!-- Non-negotiables beyond the constitution's baseline: perf budgets, security posture,
     data-handling rules, dependency policy. -->

- {constraint}
