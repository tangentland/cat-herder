---
gmd: "0.1"
id: SETUP
title: "cat-herder — Project Bootstrap with Claude Code"
tags: [instructions, setup]
metadata:
  node_type: instructions
---

# cat-herder — Project Bootstrap with Claude Code {#root}

**cat-herder** is a structured Claude Code template: a workflow, an agent/command suite, GMD
documentation tooling, and an installer that wires the token-saving dependencies. Follow these
steps to initialize a new project from it.

## Step 1: Scaffold a New Project {#scaffold}

`./install.sh PROJECT_PATH` scaffolds the template into the target directory (created if it
doesn't exist; **existing files are preserved, never overwritten**), **tunes it to the project**
(see [Step 2](#tune)), then installs and wires the recommended tooling (rmx, llm-tldr, caveman)
and the bundled GMD linter. It is idempotent and each dependency is optional:

```bash
./install.sh ../my-project          # scaffold into ../my-project, tune, then wire it
./install.sh ~/code/app --minimal   # scaffold + tune, only wire the bundled GMD/SDD tooling
./install.sh ../new-app --lang=go,ts --name="New App" --db=postgres --no-prompt
./install.sh                        # no path → wire the template repo in place (no tuning)
./install.sh --tune                 # in place, but this clone IS your project → tune it
./install.sh --help                 # full usage + flags
```

Flags: `--minimal`, `--skip-rmx`, `--skip-tldr`, `--skip-caveman`, plus the tuning flags
`--tune`, `--no-tune`, `--no-prompt`, `--skeleton`/`--no-skeleton`, `--name=`, `--description=`,
`--lang=`, `--package=`, `--db=`, `--ui=`, `--os=`.

> Scaffolding excludes the template's own `.git/`, memory state, and caches. The new project is
> not a git repo — run `git init` there yourself when ready.

> **Runtime state is never copied into the target — do not copy it by hand either.** These
> directories describe the *template repo*, not the baseline. The authoritative list (read by
> both of the installer's copy paths, with the reason for each entry) is `.scaffoldignore`:
>
> | Dir | What it is | Why excluded | How the target gets its own |
> |-----|------------|--------------|------------------------------|
> | `.refmatrix/` | rmx catalog (DuckDB), STM, queues, locks, logs | Copying cat-herder's catalog **seeds the target's index with the template's content** — `rmx context`/`query`/`memory` would answer about cat-herder, not the project | rmx builds a fresh catalog on first sync/ingest in the target |
> | `.tldr/` | llm-tldr index cache | Indexes the template's code | `tldr warm .` in the target |
> | `.agents/`, `.augment/` (+ `skills-lock.json`) | caveman skills **vendored** in the template — tracked on purpose, pinned by `skills-lock.json`, for the template's own sessions | A stale copy would shadow the version the installer writes | `install.sh` runs the caveman installer in the target, which writes and pins the project's own copies (commit them there too) |
> | `.memory.db*`, `memory.*`, `.wolf/`, `.rtk/`, `.claude/cam_local/` | other tool state | Template-specific | Created by the tools at runtime |
> | `.claude/settings.local.json`, `.claude/scheduled_tasks.lock` | per-user / per-session Claude Code state | Belongs to whoever runs the template | Each user's own Claude Code |
>
> If a target already received any of these (an older installer, or a manual `cp -R`), delete
> them from the target and let the tools rebuild — for `.refmatrix/`, stop the rmx daemon first.

> **Re-running is safe, but it is not an upgrade.** Scaffolding only *adds* files the project
> lacks and never overwrites one — so project edits survive, and equally, newer versions of
> baseline files (agent definitions, `scripts/tune-project.py`, hooks) are *not* pulled into an
> existing project. Copy a specific baseline file over deliberately when you want its update.

Then `cd PROJECT_PATH` to continue.

> **rmx** ([refmatrix](https://github.com/tangentland/refmatrix)) is the lookup + GMD-memory
> surface referenced in CLAUDE.md. It is a Python package (needs Python ≥ 3.10 and git) exposing
> the `rmx` CLI; the installer pulls it from git via pipx/uv/pip. For semantic recall, add the
> dense extra: `pipx install "refmatrix[dense] @ git+https://github.com/tangentland/refmatrix.git"`.

After install, **restart Claude Code** so the caveman/rmx hooks load.

## Step 2: Tune to the Project (part of install) {#tune}

The template is Python/Docker-flavoured by default; a project is rarely exactly that. **Tuning
the scaffold to the project's real languages and layout is part of installing it, not an
optional follow-up.** `install.sh` runs `scripts/tune-project.py` automatically after scaffolding;
re-run it by hand whenever the codebase grows a new language or top-level directory.

**Existing codebase — detection.** The tuner reads the project, it does not assume a layout:

| Detects | From |
|---------|------|
| Languages (primary first; minor traces reported but not tuned for) | manifests (`pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `pom.xml`, `*.csproj`, `Gemfile`, `composer.json`, `mix.exs`, …) + a source-file census that skips deps, build output and virtualenvs |
| Source roots | the language's conventional layout (`src/<pkg>/`, `cmd/`+`internal/`, `src/main/java/`, `lib/`, `Sources/`, …) **plus** any non-conventional top-level dir that holds source (e.g. `routes/ lib/ providers/`, or `schema/ queries/ functions/` in a SQL-first repo) |
| Tests / UI / migrations | `tests/ test/ spec/ __tests__/ e2e/` and language conventions; `ui/ frontend/ web/ client/` (or static `public/`); `alembic/ migrations/ prisma/ db/migrate/ …` |
| Monorepo | pnpm/npm workspaces, `lerna`/`nx`/`turbo`, `go.work`, Cargo/uv workspaces → `packages/ apps/ services/ crates/ …` become roots |
| Frameworks, storage, Docker | manifest dependencies, compose services, `Dockerfile` |
| Test / lint / type / format commands | **evidence only** — tool config files, declared dependencies, `package.json` scripts, `Makefile` targets. A command with no evidence is written as "none detected", never invented. Commands are wrapped in `docker compose exec dev` only when the compose file defines a `dev` service (see Known limits). |

Supported languages: Python, TypeScript, JavaScript, Go, Rust, Java, Kotlin, C#, Ruby, PHP,
Elixir, Swift, Dart, C/C++, and SQL (schema/function/query repos).

**From-scratch project — prompts.** With no code and no manifests there is nothing to detect,
so the tuner **asks**: project name, one-liner, language(s), package/module name, frameworks,
database, UI directory, target OS. It then proposes the conventional layout for those languages,
records the stack's idiomatic commands marked *proposed*, and offers to create the empty
directory skeleton. Without a terminal (CI, piped install) pass the answers as flags
(`--lang=… --name=… --package=… --db=… --ui=…`); otherwise nothing is guessed.

**What it writes** (never clobbering project-authored values):

- `.claude/PROJECT_PROFILE.md` — fills only fields still holding a `{…}` placeholder or a
  template default, and keeps a generator-owned `Install detection` evidence section (refreshed
  on every run). Filled fields are project-owned and never rewritten; on re-run the tuner prints
  `drift:` lines where detection now disagrees with them (e.g. a new language or source root).
- `.claude/hooks/hooks.env` — `SRC_DIR` (one or more roots), `CORPUS_PATHS`, `CORPUS_EXTS`,
  `ADR_GATE_FILE_RE` for the detected languages. Regenerated on every run while it is still the
  example or exactly what the tuner last wrote (a digest in its first line records that); edit
  any value and it becomes project-owned. Paths with shell-unsafe characters are left out and
  reported, since hooks source this file.

`--dry-run` prints the detection and the `hooks.env` it would write, changing nothing. Exit
status: `0` tuned, `3` nothing tuned (from scratch, no terminal, no flags), `2` bad arguments.

**Known limits.** The ADR gate matches `class X` declarations only, so for Go, Rust, Elixir and
SQL projects it is inert (`ADR_GATE_FILE_RE='^$'`, noted in the detection section). Commands are
wrapped in `docker compose exec dev` only when the compose file defines a `dev` service, with the
`/test-output` tee only when that mount is declared.

**What it leaves for the agent** ([ONBOARDING](docs/ONBOARDING.md)): confirming every detected
value, expanding the placeholders in `CLAUDE.md`/`.mcp.json`/workflow docs ([Step 3](#placeholders)), rewriting
`CLAUDE.md`'s Development Commands and [Docker setup](#docker) for the real stack, the domain
sections of the profile (primitives, glossary, constraints), agent overlays and the constitution.

## Step 3: Find and Replace Placeholders {#placeholders}

Search for these placeholders and replace them with your project values:

| Placeholder | Replace With | Example |
|-------------|-------------|---------|
| `{PROJECT_NAME}` | Your project name | `MyApp` |
| `{project_package}` | Package / module name | `myapp` |
| `{project_db}` | Database name | `myapp` |
| `{pkg}` | Short package name (for commands) | `myapp` |
| `{DATE}` | Current date | `2026-02-22` |
| `{PATH_TO_OMNISEARCH}` | mcp-omnisearch checkout path (see [Step 5](#mcp-paths)) | `~/src/mcp-omnisearch` |

Files containing placeholders:
- `CLAUDE.md` — main Claude instructions
- `.mcp.json` — MCP server config (database URI)
- `handoff.md` — session handoff
- `workflow/QUICK_REFERENCE.md` — quick lookup
- `workflow/PATTERNS.md` — code patterns
- `.claude/agents/*.md` and `.claude/commands/*.md` — `{project_package}` / `{PROJECT_NAME}` in examples
- `.claude/PROJECT_PROFILE.md` — domain sections (primitives, glossary, constraints); stack fields are
  filled by [Step 2](#tune)

Quick scan for anything left:

```bash
grep -rn '{PROJECT_NAME}\|{project_package}\|{project_db}\|{pkg}' . --include='*.md' --include='*.json'
```

## Step 4: Set Up Environment Variables {#env-vars}

These environment variables are referenced by `.mcp.json`:

**Required:**
```bash
export GITHUB_PERSONAL_ACCESS_TOKEN="ghp_..."
```

**Optional (for web search via onmisearch):**
```bash
export TAVILY_API_KEY="tvly-..."
export BRAVE_API_KEY="BSA..."
export KAGI_API_KEY="..."
export EXA_API_KEY="..."
export JINA_AI_API_KEY="..."
export FIRECRAWL_API_KEY="..."
export PERPLEXITY_API_KEY="..."
```

**Tip:** Add these to your shell profile (`~/.zshrc` or `~/.bashrc`) or use a `.env` file
with direnv.

## Step 5: Update .mcp.json Paths {#mcp-paths}

The `onmisearch` server in `.mcp.json` ships with a `{PATH_TO_OMNISEARCH}` placeholder. Replace it
with your mcp-omnisearch checkout path:

```json
"command": "node",
"args": ["/path/to/your/.claude/plugins/repos/mcp-omnisearch/dist/index.js"]
```

If you don't have onmisearch installed, remove that server block entirely.

## Step 6: Initialize Claude Code Memory {#memory}

On your first Claude Code session, Claude will:
1. Read `handoff.md` for initial context
2. Use `rmx context <symbol>` / `rmx grep` for code navigation
3. Begin recording durable learnings as GMD memory files

Memory is authored as GMD files (see `docs/gmd/PRIMER.md`) and indexed for semantic recall via
**rmx** ([refmatrix](https://github.com/tangentland/refmatrix)) — `rmx memory recall` / `rmx memory
search`, backed by `rmx memory sync-disk`. If rmx is not installed, memory files are still written
and linted; only the retrieval layer is unavailable, so the workflow degrades gracefully.

## Step 7: Create Planning & Tracking Directories {#planning-dirs}

The project uses a **status-tracked plan lifecycle**. All plans live permanently in
`workflow/plans/`; a plan never moves between directories — its stage is recorded ONLY by the
`metadata.status` field in its GMD frontmatter: `drafting` → `approved` → `in-progress` →
`completed`.

```bash
# All plans live here permanently; stage = metadata.status frontmatter
mkdir -p workflow/plans

# Architecture documentation
mkdir -p docs/architecture/explorations
mkdir -p docs/architecture/adr

# Implementation tracking
mkdir -p workflow/implementation_summaries
mkdir -p workflow/review-output
mkdir -p workflow/past_handoffs

# Templates (already provided)
# workflow/templates/ — task-spec, proposed-plan, exploration, handoff-session
```

Create the meta index file:

**`workflow/plan-of-plans.md`** — the single plan index + sequenced execution order (with a
Status column). This is the source of truth for what to implement next; each plan's Status
mirrors its `metadata.status` frontmatter:
```markdown
# Plan of Plans

Index and sequenced execution order for all implementation plans. This is the source of truth
for what to implement next. Every plan lives in `workflow/plans/`; the Status column mirrors the
plan's `metadata.status` frontmatter (`drafting` → `approved` → `in-progress` → `completed`).

| # | Plan | Status | Tasks | Notes |
|---|------|--------|-------|-------|
| 1 | {first plan name} | drafting | — | — |
```

## Step 8: Set Up Docker (REQUIRED) {#docker}

All development and testing runs in Docker. The example below is for a **Python** project; for
another stack keep the same shape (a `dev` service, `/workspace` mount, `/test-output` volume)
and swap the base image and dependency step for the one the tuned profile names — e.g.
`node:22` + `npm ci`, `golang:1.23` + `go mod download`, `rust:1` + `cargo fetch`,
`eclipse-temurin:21` + `./gradlew dependencies`, `postgres:16` + `pg_regress` for a SQL-first
repo. If the project deliberately runs outside Docker (e.g. SQL executed against a remote
database), say so in `CLAUDE.md` instead of following this step. Create a `docker-compose.yml`:

```yaml
services:
  dev:
    build:
      context: .
      dockerfile: docker/Dockerfile.dev
    volumes:
      - .:/workspace
      - test-output:/test-output
    working_dir: /workspace
    depends_on:
      - postgres

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: {project_package}
      POSTGRES_PASSWORD: {project_package}_dev
      POSTGRES_DB: {project_package}
    ports:
      - "5433:5432"

volumes:
  test-output:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ./docker/test-output
```

Create `docker/entrypoint.sh` to manage the container venv:

```bash
#!/bin/bash
VENV_PATH="/opt/{project_package}-venv"
if [ ! -d "$VENV_PATH" ]; then
    python3 -m venv "$VENV_PATH"
fi
source "$VENV_PATH/bin/activate"
pip install -e ".[dev]"
exec "$@"
```

Create the test output directory:
```bash
mkdir -p docker/test-output
```

**Important:** The container venv lives at `/opt/{project_package}-venv`, NOT at
`/workspace/.venv`. The entrypoint manages all dependency installation. Never run
`uv` or `pip install` manually — add deps to `pyproject.toml` and restart the container.

## Step 9: First Session {#first-session}

If placeholders remain, the agent first runs [ONBOARDING](docs/ONBOARDING.md). Then Start Claude
Code and it will:
1. Read the handoff and indexes
2. Read `workflow/plan-of-plans.md` for what to implement next
3. Check `docs/architecture/todo.md` for known gaps
4. Be ready to implement with full context awareness

Tell Claude what your project does and what to build first. It will follow the
Task Completion Workflow defined in CLAUDE.md automatically.

## Template Files {#template-files}

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Main Claude Code instructions — development workflow, quality gates, agents |
| `install.sh` | Scaffolds, tunes to the project, installs + wires the tooling (rmx, llm-tldr, caveman, GMD) |
| `scripts/tune-project.py` | Detects (or prompts for) languages, layout, commands → PROFILE + hooks.env |
| `docs/` | **Knowledge** — `architecture/` (README, INDEX, todo, adr/, concepts/, explorations/, tech-stack/), `guides/`, `reference/`, `specs/`, `design/`, `gmd/` |
| `workflow/` | **Process** — plans, governance, templates, audits, summaries (see `workflow/INDEX.md`) |
| `workflow/PLANNING_WORKFLOW.md` | Full planning, exploration, and plan approval workflow |
| `workflow/PLAN_GOVERNANCE.md` | Plan lifecycle, staleness, question-forcing |
| `workflow/templates/` | Document templates (task-spec, proposed-plan, exploration, handoff) |
| `workflow/test_mock_registry.md` | Mock governance registry |
| `docs/ONBOARDING.md` | Agent first-run onboarding (runs when placeholders remain) |
| `docs/gmd/` | GMD primer + conformance spec (Graph Markdown authoring) |
| `tools/gmd/` | Bundled GMD tooling — `gmd lint\|init\|slice`, `lint.py` |
| `scripts/lint-gmd.sh` | Lint `CLAUDE.md` + `docs/` as a GMD graph |
| `.gmd/config.yml` | Project-local GMD lint config |
| `.claude/agents/` | Agent suite — `ch-architect`, `ch-code-reviewer`, `ch-security-auditor`, `ch-test-engineer`, `ch-doc-writer`, `ch-gap-master`, `ch-bsd`, `ch-performance-tuner`, `ch-work-summary`, `general-purpose` |
| `.claude/commands/` | Commands — `/ch-review`, `/ch-audit`, `/ch-bsd`, `/ch-test-gen`, `/ch-handoff` |
| `.claude/statusline.sh` | Status line, **on by default** (wired as `statusLine` in the project's `.claude/settings.json`, which takes precedence over a user-level status line; delete that key to opt out) — project, model + permission mode, context %, tokens, weekly counters. Needs `jq`; BSD or GNU `date`; weekly state in `~/.claude/.weekly_state` (reset Sunday 10:00 in `$CH_STATUS_WEEK_TZ`, default America/Los_Angeles), per-session state in `~/.claude/.statusline/`. The permission mode is read from the session transcript (not in the status JSON) |
| `.scaffoldignore` | Paths `install.sh` never copies into a target (runtime state, per-user files, template self-tests) |
| `.claude/rules/` | Always-on rules (e.g. `bug-registry.md`) |
| `.mcp.json` | MCP server configuration — GitHub, Docker, search, PostgreSQL, diagrams |
| `.gitignore` | Git ignore rules — venv, cache, test output, memory state, IDE files |
| `handoff.md` | Session handoff template — context between conversations |
| `workflow/QUICK_REFERENCE.md` | Fast lookup — commands, conventions, checklist |
| `workflow/PATTERNS.md` | Copy-paste code patterns — testing, async, FastAPI |
| `workflow/development_resources.md` | Infrastructure inventory — Docker, database, environment |
| `SETUP.md` | This file — bootstrap instructions |
