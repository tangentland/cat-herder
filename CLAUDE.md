---
gmd: "0.1"
id: claude
title: "CLAUDE.md — project operating instructions"
tags: [instructions, cat-herder]
metadata:
  node_type: instructions
---

# Memory & context layer {#memory-context-layer}

@.claude/PROJECT_PROFILE.md

**`rmx` (refmatrix) is the primary memory, context, and navigation layer.** Its hooks (wired in
`.claude/settings.json`) own session recall, focus, sync, and prompt-scan. Prefer `rmx context`,
`rmx query`, `rmx grep`, and `rmx memory` over raw grep/read for corpus discovery.


# CLAUDE.md {#root}

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> Bootstrapped from the **cat-herder** Claude Code template. Replace the placeholders below
> (`{PROJECT_NAME}`, `{project_package}`, `{project_db}`) with your project's values — see SETUP.md.

## Project Overview {#project-overview}

**{PROJECT_NAME}** — {one-line description of the project}.

- **Stack**: {language}, {framework}, {database}, {key libraries}
- **Target OS**: {e.g., Ubuntu 24.04}
- **Python version**: {e.g., 3.14}

## Development Commands (Docker Only) {#development-commands}

**ALL commands run in Docker containers** — never on the host OS. The host may lack system
dependencies, the correct Python ABI, or required native libraries. Do not use `uv run`,
local venv, or any host-native Python commands.

### Container Python Environment (CRITICAL) {#container-python-env}

The dev container's Python venv lives at **`/opt/{project_package}-venv`** — NOT at
`/workspace/.venv`. The entrypoint script (`docker/entrypoint.sh`) creates and manages
this venv automatically, including installing any system-dependent Python bindings that
require special build steps.

**Hard rules:**

- **NEVER use `/workspace/.venv`** — this path does not exist in the container and must
  never be created or referenced.
- **NEVER run `uv` outside the container** — no `uv sync`, `uv pip install`, `uv run`, or
  any other `uv` command on the host. If a package is missing, add it to `pyproject.toml`
  and restart the container (`docker compose restart dev`).
- **NEVER run `pip install` or `uv pip install` manually inside the container** — the
  entrypoint manages all dependency installation.
- **`docker compose exec` does NOT inherit the entrypoint's PATH**, so you must use the full
  venv Python path: `/opt/{project_package}-venv/bin/python`.

**All commands tee output to `/test-output/`** (host: `docker/test-output/`).

```bash
# Start services
docker compose up -d

# Run all tests (tee to log)
docker compose exec dev bash -c "/opt/{project_package}-venv/bin/python -m pytest -v 2>&1 | tee /test-output/pytest.log"

# Quality gates (tee to logs)
docker compose exec dev bash -c "/opt/{project_package}-venv/bin/python -m ruff check . 2>&1 | tee /test-output/ruff.log"
docker compose exec dev bash -c "/opt/{project_package}-venv/bin/python -m mypy src/{project_package} 2>&1 | tee /test-output/mypy.log"
docker compose exec dev bash -c "/opt/{project_package}-venv/bin/python -m black --check . --line-length 100 2>&1 | tee /test-output/black.log"

# Interactive shell
docker compose exec dev bash
```

### System-Dependent Tests (CRITICAL — NEVER SKIP) {#system-dependent-tests}

**ALL tests must run.** NEVER use `--ignore` to skip tests that depend on system libraries
or services available in the container. If these tests fail with import errors, the
container's Python environment is broken. Fix it:

1. **Restart the container**: `docker compose restart dev`
2. If that fails, **rebuild**: `docker compose build dev && docker compose up -d`

**NEVER work around import errors by skipping tests.**

**Reading results from host**: `tail -20 docker/test-output/pytest.log`

### Functional UI Tests (if applicable) {#functional-ui-tests}

{Remove this section if not using a frontend, or customize for your test tiers.}

The frontend uses two tiers of functional tests beyond unit tests:

**Tier 1 — Vitest Browser Mode** (component integration tests):
- Runs real components in Chromium via `@vitest/browser-playwright`
- Config: `ui/vite.config.ts` — `test.projects` defines `unit` (jsdom) and `browser` (chromium)
- File naming: `*.browser.test.tsx` (browser mode), `*.test.tsx` (jsdom unit)
- Run: `cd ui && npx vitest run --project browser`

**Tier 2 — Playwright E2E** (full-stack end-to-end tests):
- Runs against the full app (Vite dev server + backend in Docker)
- Config: `ui/playwright.config.ts`
- Run: `cd ui && npm run test:e2e`
- Tests live in `ui/e2e/` (spec files: `*.spec.ts`)

**Rules:**
- New canvas/spatial components MUST have Vitest Browser Mode tests
- New user workflows MUST have Playwright E2E tests
- E2E tests authenticate via dev-mode fallback (no mock auth)

## Development Guidelines {#development-guidelines}

- Line length: 100 characters (Black formatting)
- Strict type hints (mypy strict mode)
- Comprehensive audit logging for all data access
- Rate limiting and retry logic for external APIs

### Architectural Principles {#architectural-principles}

{Customize this section for your project's design tenets. Delete if not applicable.}

All design proposals must reason FROM the project's architectural tenets, not around them.
Before proposing any new mechanism, validate: does an existing architectural primitive
already solve this? If yes, use it. Never introduce parallel infrastructure when an
existing conceptual alignment already covers the concern.

**Source:** {link to your architecture principles document}

### No Mocks in Production Code (CRITICAL) {#no-mocks}

All production code (`src/`) must be **fully concrete** — no stubs, mocks, simulated
behavior, fake implementations, or placeholder logic. Every function, class, and module
must do real work or not exist yet.

**Mocks are permitted ONLY in test code** (`tests/`) for external services and dependencies.

### Mock Governance (Test Code) {#mock-governance}

Mocks in test code follow a classification system tracked in
[`workflow/test_mock_registry.md`](workflow/test_mock_registry.md):

| Classification | Meaning | Allowed? |
|----------------|---------|----------|
| `external` | External library, platform API, third-party service | Permanent |
| `internal-active` | Internal subsystem with existing implementation | **Must graduate** |
| `internal-pending` | Internal subsystem not yet built | Temporary |

**Rules:**
- New mocks of external dependencies → add to registry as `external`
- New mocks of internal subsystems → add to registry; graduate when implementation exists
- New auth endpoints → must have a real-auth test (no dependency overrides)
- New API endpoints → must have a contract test if UI-facing
- `pytest -m scenario` runs workflow tests; `pytest -m contract` runs shape tests

### No Workarounds (CRITICAL) {#no-workarounds}

When you encounter a missing dependency (database table, service, config), do NOT work around
it. Define the gap, propose the real solution, and ask before proceeding.
Consult `workflow/development_resources.md` for available infrastructure.

## Git Workflow {#git-workflow}

Create a feature branch per task. Merge to main when complete. Never delete branches.

```bash
git checkout -b task-X.Y-description main
# ... work ...
git checkout main && git merge --no-ff task-X.Y-description
```

## Permissions {#permissions}

**YOU ARE ALLOWED TO EXECUTE ALL COMMANDS WITHIN THE PROJECT DIRECTORY STRUCTURE**
   *FOLLOWING THESE RULES*
     - DO NOT share sensitive information or credentials
     - NEVER COMMIT to the 'release' branch
     - DO NOT CONFIDENCE PROMPT FOR PERMISSIONS
     - NEVER EXECUTE THE COMMAND 'rm -rf *'
     - YOU ARE ALLOWED TO MAKE CHANGES WITHOUT ASKING WITHIN THE PROJECT

## MCP Servers {#mcp-servers}

Configured in `.mcp.json`. All API keys use `${ENV_VAR}` references — never hardcode secrets.
The enabled set lives in `.claude/settings.local.json`.

| Server | Transport | Purpose |
|--------|-----------|---------|
| context7 | npx | Live library documentation lookup |
| github | npx | GitHub API (issues, PRs, actions) |
| mcp-mermaid | npx | Mermaid diagram generation |
| docker | uvx | Docker container management |
| playwright | npx | Browser automation / E2E driving |
| postgres | docker | Read-restricted PostgreSQL access |
| onmisearch | node | Web search aggregator (optional — see SETUP.md) |

## Discovery & Tooling {#discovery-tooling}

This template wires a set of token-saving and memory tools. Run `./install.sh` once to install
and wire them (see SETUP.md). All are optional — the workflow degrades gracefully if one is absent.

| Tool | Purpose | Notes |
|------|---------|-------|
| **rmx** | Lookup + learning surface — `rmx context/query/grep`, GMD memory | [refmatrix](https://github.com/tangentland/refmatrix) — Python pkg (≥3.10), exposes `rmx` CLI; installed by `./install.sh` |
| **llm-tldr** (`tldr`) | Token-efficient code analysis, call graphs | `tldr context <symbol>`, `tldr warm .` |
| **caveman** | Ultra-compressed agent communication mode | Provides `/commit`, `/caveman*` |

**Action guardrails (optional).** `.claude/p20-0/` compiles `guardrail`-type memories in
`.claude/p20-0/guardrails/` into native `autoMode.{hard_deny,soft_deny,allow,environment}` arrays
(`compile_guardrails.py`, re-run each SessionStart, validated by the `validate.py` RED oracle over
`golden_cases.jsonl`). Add a guardrail = drop a new GMD memory with a fenced `guardrail:` block
(`tier` + `rule`) in that dir and recompile — no new code (self-hardening). Ships 3 universal
guardrails (off-machine externalize, uncommitted-revert → `hard_deny`; read-only recon → `allow`).
Requires `rmx`; rules are inert unless the session runs in `auto` permission-mode.

**Discovery ladder** (use indexes before raw search): `rmx context <symbol>` → `tldr` call-graph →
`rmx grep` → raw `grep`/`Glob`. Also consult
`docs/architecture/ARCHITECTURE_INDEX.md`, and `workflow/plan-of-plans.md`.

## Graph Markdown (GMD) {#graph-markdown}

Persistent prose docs in this project are authored as **GMD** (Graph Markdown) — Markdown plus
stable anchors, wikilinks, and typed `rel:` edges. Treat GMD docs as a graph, not prose: follow
wikilinks instead of grepping, and read `rel:` lines as typed edges.

- **Primer:** [`docs/gmd/PRIMER.md`](docs/gmd/PRIMER.md) — **Spec:** [`docs/gmd/SPEC.md`](docs/gmd/SPEC.md)
- **Tooling:** bundled under `tools/gmd/` (`gmd lint|init|slice`).
- **When required:** ADRs, concept docs, design tenets, plan/task specs, memory files, and any
  markdown other docs will reference. Each needs frontmatter (`gmd: "0.1"` + unique `id` + `title`
  + `tags`), a `{#anchor}` on every heading, and `rel:` edges for citations.
- **Validate before commit:** `./scripts/lint-gmd.sh` (or `python3 tools/gmd/lint.py <path>`) — zero errors.

## Context Management (CRITICAL) {#context-management}

### Write Decisions Immediately {#write-decisions}

**Architectural discussions and decisions MUST be written to files as they happen.**
Context compaction can erase unwritten discussion at any time.

**Pattern:** Discussion → Decision → Write to file → Continue discussion

**Also capture the WHY to rmx short-term memory (STM).** Extended-thinking blocks are redacted
from the transcript, so a decision's rationale is otherwise lost at session end. Record it with
the **`refmatrix` MCP tool `rmx_focus_note`** (prefer the MCP tool over `Bash rmx focus note` —
structured, no shell-quoting of multi-line reasoning, no permission friction). STM graduates
to durable memory automatically at PreCompact/Stop (`focus summarize --promote`) and on
`/save-state`. Reach STM/memory through the MCP tools — `rmx_focus_note`, `rmx_change_subject`,
`rmx_context`, `memory_add`/`memory_search`/`memory_recall` — not raw CLI, whenever the agent
itself is the caller (hooks are the CLI exception; they are plumbing).

### Planning, Exploration & Templates {#planning-exploration-templates}

**Full planning workflow, exploration workflow, plan approval gate, and all templates
are in [`workflow/PLANNING_WORKFLOW.md`](workflow/PLANNING_WORKFLOW.md).**

Templates are in `workflow/templates/` (task-spec, proposed-plan, exploration, handoff-session).

**Key rule:** Write proposed plans to disk BEFORE presenting questions to the user.

### Navigation & Lookup {#navigation-lookup}

| Need | Consult First | Then |
|------|---------------|------|
| Prior work | `handoff.md` + `workflow/past_handoffs/` | Indexes |
| Quick patterns/commands | `workflow/QUICK_REFERENCE.md` | Full docs |
| Code structure | `rmx context <symbol>` / `rmx grep` | Source files |
| Architecture topics | `docs/architecture/ARCHITECTURE_INDEX.md` | Architecture docs |
| Implementation gaps | `docs/architecture/todo.md` | - |
| Active plans | `workflow/plan-of-plans.md` (index + sequence + Status) | `workflow/plans/` |
| Approved task specs | `workflow/plans/<plan>-tasks/` | Plan file in `workflow/plans/` (`status: approved`) |

**Never explore blindly** — search indexes first.

## First-Time Onboarding {#first-time-onboarding}

**Before the first Session Start in a fresh clone, check whether this project has been onboarded.**
It is an uninitialized template if literal placeholders remain — quick check:
`grep -rl "{PROJECT_NAME}\|{project_package}" CLAUDE.md .mcp.json .claude/PROJECT_PROFILE.md`.
If it matches, do NOT start normal work: surface it to the user, then follow
[`docs/ONBOARDING.md`](docs/ONBOARDING.md) (install.sh detects/prompts for the stack + layout →
confirm PROJECT_PROFILE → expand placeholders → adapt CLAUDE.md commands/Docker to the stack →
create `<agent>.local.md` overlays → `/ch-constitution` → commit). Run it once;
after that, this section is a no-op and you proceed to Session Start.

## Session Start {#session-start}

1. **Read handoff.md** for context from previous session
2. **Read `workflow/plan-of-plans.md`** for what to implement next
3. **Read docs/architecture/ARCHITECTURE_INDEX.md** for architecture navigation
4. **Read docs/architecture/README.md** to understand the architecture
5. **Verify git state** matches handoff (branch, tag)
6. **Check docs/architecture/todo.md** for known gaps and priorities
7. **Read `workflow/bullshit/`** (if present) — `last_run.log` for the latest verdict, then INDEX.md/IMPRESSIONS.md. Any unaddressed BULLSHIT finding is first priority before new work
8. **If implementation phase**: Read the active plan from `workflow/plans/` — a plan's stage is its `metadata.status` frontmatter field (`drafting` → `approved` → `in-progress` → `completed`)

## Agent and Skill Workflow {#agent-skill-workflow}

### Available Agents {#available-agents}

| Agent | When to Use |
|-------|-------------|
| **@ch-architect** | Architecture decisions, design reviews, ADR creation/validation; dispatched by `/ch-crucible` |
| **@ch-alignment** | Owns `pseudocode/` ground truth; adversarially detects drift (pseudocode ↔ ADRs ↔ code). Reinforces `/ch-crucible` |
| **@ch-implementer** | TDD executor — writes `src/` code to turn RED tests GREEN; authors NO tests (pairs with @ch-test-engineer) |
| **@ch-code-reviewer** | Code changes, PR reviews, systematic quality analysis |
| **@ch-security-auditor** | Security-sensitive code, auth flows, before deployment |
| **@ch-test-engineer** | Test strategy, coverage gaps, test architecture |
| **@ch-doc-writer** | Documentation suite creation/maintenance, index accuracy, cross-references |
| **@ch-gap-master** | Gap/mock curation, deferral challenges, workaround elimination, action enforcement |
| **@ch-bsd** | Bullshit detector — runtime-integration audit at plan/commit completion. Proves committed code actually executes in production paths; finds dead code, stubs, unwired components, cheap fixes, stale deferrals. Cross-run memory in `workflow/bullshit/` |
| **@ch-performance-tuner** | Performance issues, hot path optimization, profiling |
| **@ch-work-summary** | Pre-implementation alignment — holistic work summaries covering intent, assumptions, constraints, UI flow, backend linkages, system effects. Two modes: `describe-work-report` (non-interactive) and `discuss-work-description` (interactive) |
| **@gmd-curator** | Owns GMD docs as a live rmx-backed knowledge graph; bootstraps docs, maintains linkages, surfaces contradictions |
| **general-purpose** | Multi-step research, code search, and subagent implementation work |

> Agent definitions are **project-neutral**. Project specifics come from an optional per-agent
> overlay `.claude/agents/<name>.local.md` (read first when present) + the shared
> `.claude/PROJECT_PROFILE.md`. See `.claude/agents/ch-architect.local.md.example`.

> UI design quality is handled by the `frontend-design` skill (invoke `/frontend-design`) rather than a dedicated agent — drop or add agents in `.claude/agents/` to fit your project.

### Useful Commands {#useful-commands}

**Spec-Driven Development (SDD) chain** — see [Spec-Driven Development](#spec-driven-development):

| Command | Purpose |
|---------|---------|
| `/ch-constitution` | Create/update `workflow/CONSTITUTION.md` (governing principles) |
| `/ch-specify` | New feature spec (what/why) → `workflow/specs/NNN-slug/spec.md` |
| `/ch-clarify` | Resolve spec ambiguity via ≤5 targeted questions |
| `/ch-crucible` | Extract architectural decisions → `docs/architecture/adr/` (between clarify & plan) |
| `/ch-plan` | Technical plan + design artifacts; honors constitution + cites ADRs |
| `/ch-tasks` | Dependency-ordered `tasks.md` with `[P]`/checkpoint markers |
| `/ch-analyze` | Cross-artifact consistency check (pre-implement) |
| `/ch-implement` | Execute tasks, then `/ch-review` + `@ch-bsd` |

**Review, audit & session state:**

| Command | Purpose |
|---------|---------|
| `/ch-review` | Four-phase multi-agent code review |
| `/ch-audit` | Full security audit |
| `/ch-bsd` | Runtime-integration audit (bullshit detector) over a commit range |
| `/ch-test-gen` | Generate tests following the project's test tiers |
| `/ch-handoff` | Create a session handoff document |
| `/commit` | Consistent commit messages (provided by the caveman plugin) |
| `/save-state` · `/recall-state` · `/commit-state` | Session handoff / orient / mid-session checkpoint (rmx-backed) |
| `/detour` · `/return` · `/stash` · `/stash-list` · `/stash-pop` | Focus-state task switching (rmx-backed) |

## Spec-Driven Development {#spec-driven-development}

The baseline ships a spec-driven development (SDD) command chain (grafted from GitHub spec-kit,
`ch-*`-named, with an ADR phase inserted). For a **non-trivial feature**, drive it through the
chain rather than jumping straight to code:

```
/ch-constitution  ── governing principles (workflow/CONSTITUTION.md); the gate /ch-plan re-checks
      │
/ch-specify       ── what/why, tech-agnostic  → workflow/specs/NNN-slug/spec.md
      │
/ch-clarify       ── ≤5 targeted questions; resolve [NEEDS CLARIFICATION]
      │
/ch-crucible      ── "what architectural clarity can we add to this spec?"  ← ADR gate
      │              @ch-architect → docs/architecture/adr/NNNN-*.md (plan must cite these)
/ch-plan          ── how; Constitution Check + cites ADRs → plan.md, research, data-model, contracts/
      │
/ch-tasks         ── dependency-ordered tasks.md ([T###] [P] [US#], checkpoints)
      │
/ch-analyze       ── cross-artifact consistency (spec ↔ ADR ↔ plan ↔ tasks ↔ constitution)
      │
/ch-implement     ── execute tasks → then /ch-review (4-phase) + @ch-bsd (runtime audit)
```

- **Artifacts** live under `workflow/specs/NNN-slug/` (see `workflow/specs/README.md`); ADRs are
  cross-feature and live in `docs/architecture/adr/`. All are GMD.
- The **constitution** (`workflow/CONSTITUTION.md`) is a gate `/ch-plan` evaluates before and
  after design; `/ch-analyze` verifies compliance.
- **Backing scripts** are in `scripts/sdd/` (feature-dir numbering, branch creation, prereq checks).
- This complements the `workflow/` planning system: `plan-of-plans.md` sequences work across
  features; the SDD chain produces each feature's spec→implement lineage. For trivial changes with
  an existing task spec, skip the chain and follow the Task Completion Workflow directly.

## Task Completion Workflow {#task-completion-workflow}

**IMPORTANT** Operate in Continuous Implementation Mode:

1. **Identify next task** — check handoff.md or `workflow/plan-of-plans.md`, read the task spec file
2. **Gap check** — identify missing infrastructure before writing code
3. **Implement** — fully concrete production code (no mocks in `src/`)
4. **Write tests** — mocks only for external dependencies
5. **Verify** — all tests pass in Docker, linting clean, type checking clean (tee to logs)
6. **Four-phase agent review** — run `/ch-review` (see `.claude/commands/ch-review.md` for full workflow)
   - Critical/High: address before proceeding. Medium: address or document rationale.
   - Log agent issues to `docs/problem_log.md`
7. **Update documentation** — `docs/architecture/ARCHITECTURE_INDEX.md`
8. **Save implementation summary** to `workflow/implementation_summaries/<task-name>.md` **(MANDATORY — include in commit)**
9. **Update handoff.md** (see Handoff Rotation below)
10. **Commit and tag** — DO NOT delete feature branches

### Implementation Plan Breadcrumb (MANDATORY) {#implementation-plan-breadcrumb}

Output a 5-line breadcrumb block showing the current task's position in the active
implementation plan. Format each line as `<plan_name (phase/grouping)>:task_name`.

```
Prior plan: workflow/plans/phase-1-core-infrastructure.md (status: completed)
Active plan: workflow/plans/phase-2-api-layer.md (status: in-progress)
Next plan: workflow/plans/phase-3-frontend.md (status: approved)

  [completed] Phase 1 (Core): Database Schema
  [completed] Phase 1 (Core): Service Layer
> [active]    Phase 2 (API): REST Endpoints                              <-- current
  [pending]   Phase 2 (API): Auth Middleware
  [pending]   Phase 3 (Frontend): Component Library
```

**When to output:**
1. **At task start** — after identifying and reading the task spec (step 1)
2. **Before phased reviews** — just prior to launching the four-phase agent review (step 6)
3. **Before final commit** — just before the commit command (step 10)

**Rules:**
- Show three plan document links above the task lines:
  - **Prior plan**: the completed plan that preceded the active one (or `(none)` if first)
  - **Active plan**: the detailed plan file currently being executed
  - **Next plan**: the plan that follows after the active one completes (or `(none)` if last)
- Lines 1-2: previous 2 completed tasks (or fewer if at plan start)
- Line 3: current active task (prefixed with `>` marker)
- Lines 4-5: next 2 pending tasks (or fewer if near plan end)
- Plan names from `workflow/plan-of-plans.md` (the execution sequence)
- Use the phase/grouping from the plan's dependency graph
- All three plans live in `workflow/plans/` and do NOT move — the parenthetical `status:` shows
  each plan's `metadata.status` stage rather than a directory location

### Implementation Plans Must Be Pre-Written (CRITICAL) {#plans-pre-written}

**NEVER create implementation plans on-the-fly during a coding session.** Plans created
ad-hoc during implementation are lost when the context window compacts.

**Required workflow (status-tracked lifecycle — plans never move):**
1. All plans live permanently in `workflow/plans/`. A plan's stage is tracked ONLY by its
   `metadata.status` frontmatter field: `drafting` → `approved` → `in-progress` → `completed`.
2. New plans are written to `workflow/plans/<plan-name>.md` with `status: drafting` during design
3. When task specs are written and approved, set the plan's `status: approved` (in place)
4. Each plan is indexed in `workflow/plan-of-plans.md` (the single index, with a Status column)
5. `workflow/plan-of-plans.md` maintains the sequenced execution order
6. When a plan completes, set its `status: completed` — the file stays in `workflow/plans/`
7. The meta plan-of-plans is the source of truth for what comes next

### Do NOT Enter Plan Mode for Pre-Written Tasks (CRITICAL) {#no-plan-mode-prewritten}

**If a task spec already exists in `workflow/plans/`, do NOT use EnterPlanMode.**
The task spec IS the plan. Instead:

1. **Read the task spec** — it has deliverables, implementation notes, acceptance criteria
2. **Quick exploration** (Read, Grep, Explore agent) — understand APIs you'll integrate with
3. **Implement directly** — follow the Task Completion Workflow

**EnterPlanMode is ONLY for:**
- Brand-new work with no existing task spec
- User-requested architectural explorations
- Ambiguous requirements that need structured design discussion

**Plan document locations (status-tracked lifecycle — one permanent home):**
- **Meta index + sequence:** `workflow/plan-of-plans.md`
- **All plans:** `workflow/plans/<plan-name>.md` — plans never move; the `metadata.status`
  frontmatter field records the stage:
  - `drafting` — no task specs yet
  - `approved` — task specs written under `workflow/plans/<plan>-tasks/`, ready to implement
  - `in-progress` — implementation underway
  - `completed` — shipped and verified (file stays put)

### Complete Plan Gate (CRITICAL) {#complete-plan-gate}

**Before implementing the FIRST task of any multi-task plan, verify:**

1. **All individual task specs exist** — every task in the plan has a written spec with:
   - Description and deliverables
   - Key classes/functions to create or modify
   - Acceptance criteria
   - Test plan
2. **Execution sequence is defined** — dependencies between tasks are documented
3. **User review** — if any task spec lacks implementation details (vague deliverables,
   missing API signatures, unclear integration points), present the plan to the user
   for review before starting implementation

**If any task specs are missing or incomplete, writing them is the first task.**
Do not start coding until every task in the plan is fully specified.

### Plan Mode Output Is NOT Implementation Approval (CRITICAL) {#plan-mode-not-approval}

**When a session continues from a plan mode output or context compaction, the FIRST action
is ALWAYS verifying task specs exist — NEVER jumping to implementation.**

Plan mode produces a **proposed** plan. That plan must go through:
1. **Decomposition** — break into individual task spec files in `workflow/plans/<plan>-tasks/`
2. **User review** — present task specs for approval
3. **Only then** — begin implementation per the Task Completion Workflow

**Hard checkpoint:** Before writing ANY production code (`src/` or `ui/src/`) for a new plan,
verify individual task spec files exist in `workflow/plans/<plan>-tasks/`. If they
don't exist, writing them IS the first task. This applies regardless of what a context
continuation summary says — summaries may lose the distinction between "proposed" and
"approved."

### Phase/Milestone Performance Review {#phase-performance-review}

At the end of **phase blocks, milestones, or major implementation arcs** (not individual
tasks), run @ch-performance-tuner for a full performance review:

- Profile hot paths introduced or modified during the phase
- Benchmark throughput, latency, and resource usage
- Identify regressions from baseline (if established)
- Save output to `workflow/review-output/<phase-or-milestone>-performance.md`
- Critical findings: address before starting the next phase

**Triggers**: Completing a phase, shipping a milestone, or any work touching hot paths
(pipelines, storage, query paths, API response times).

### Cleanup Phase (MANDATORY) {#cleanup-phase}

At the end of each **implementation chunk** (a grouped set of tasks from one plan), execute
a cleanup phase before starting the next plan in the execution sequence.

#### Cleanup Phase Workflow {#cleanup-phase-workflow}

1. **Create cleanup plan** — Run a planning session that produces a cleanup plan at
   `workflow/plans/<chunk-name>-cleanup.md` (`status: drafting`) covering:
   - **docs/architecture/todo.md triage**: Identify items whose status can change from
     `Resolveable` → `Integrated` based on work just completed. Implement fixes for items
     that are now addressable.
   - **Mock registry graduation**: Review `workflow/test_mock_registry.md` for entries classified
     `internal-active` or `internal-pending` that can now be graduated to concrete
     implementations (the real subsystem exists). Convert mock-based tests to use real code.
   - **Technical debt**: Address any deferred Medium findings from agent reviews during
     the chunk.

2. **Execute cleanup tasks** — Implement each item as a mini-task (branch, implement,
   test, commit). Individual tasks do NOT require the full four-phase review — a single
   @ch-code-reviewer pass suffices.

3. **Update tracking** — After cleanup:
   - Update `docs/architecture/todo.md` statuses
   - Update `workflow/test_mock_registry.md` classifications
   - Set the cleanup plan's `status: completed` (it stays in `workflow/plans/`)

#### Triggers {#cleanup-triggers}

A cleanup phase is required after completing:
- Any plan from `workflow/plan-of-plans.md`
- Any group of 3+ related tasks from the same plan

#### Scope Control {#cleanup-scope-control}

Cleanup phases are **bounded**: only address items directly related to the just-completed
implementation chunk. Do not scope-creep into unrelated todo.md items. Target: 1-4 cleanup
tasks per phase, each completable in a single session.

## Quality Gates {#quality-gates}

### Before Commit (ALL required) {#before-commit}
- [ ] Implementation summary written to `workflow/implementation_summaries/<task-name>.md`
- [ ] Code is fully concrete (no mocks in `src/`)
- [ ] Tests pass in Docker — ALL tests including system-dependent tests
- [ ] Lint clean (ruff) and type check clean (mypy)
- [ ] @ch-code-reviewer + @ch-architect: Critical/High addressed
- [ ] @ch-test-engineer: Coverage adequate
- [ ] @ch-gap-master: `docs/architecture/todo.md` current, mock registry updated, no workarounds in src/
- [ ] @ch-bsd: no unaddressed BULLSHIT findings in `workflow/bullshit/` (code wired to production paths, no cheap fixes, no stale deferrals)
- [ ] @ch-doc-writer: Indexes accurate, handoff updated, docs/ suite current
- [ ] Real-auth test exists for new auth-protected endpoints
- [ ] Contract test exists for new UI-facing response shapes
- [ ] Cleanup phase completed after implementation chunk (if applicable)

## Handoff Rotation {#handoff-rotation}

**`handoff.md` keeps only the latest session.** Previous sessions archived in `workflow/past_handoffs/`.

**Format:** See `workflow/templates/handoff-session.md`

**Workflow:** Archive current session to `workflow/past_handoffs/<seq>-<desc>_<date>.md` → update Past
Sessions table → replace Latest Session → update header.

**Archive naming:** `<seq#>` zero-padded (001, 002...), `<desc>` kebab-case from session header.

## Planning & Task Documentation {#planning-task-docs}

### Document Hierarchy {#document-hierarchy}

```
workflow/                       <- PROCESS: planning, governance, audits, summaries
├── plan-of-plans.md            <- META INDEX + SEQUENCE: all plans, Status column, execution order (source of truth)
├── plans/                      <- ALL plans live here permanently; stage = metadata.status
│   │                              (drafting → approved → in-progress → completed)
│   ├── <plan-name>.md          <- A plan at any status (frontmatter records the stage)
│   └── <plan>-tasks/           <- Task spec directories (present once status: approved)
│       └── task-X.Y-description.md
├── specs/                      <- SDD: per-feature spec→plan→tasks chain (NNN-slug/); see specs/README.md
├── constitution.md             <- Governing principles; the SDD gate /ch-plan re-checks
├── implementation_summaries/   <- Per-task implementation summaries
├── session-summaries/          <- Per-session summaries
├── bullshit/                   <- @ch-bsd audit memory (INDEX, IMPRESSIONS, findings)
├── functional-tests/           <- Functional / E2E test inventory
├── review-output/              <- Agent review reports (gitignored — runtime)
├── templates/                  <- Document templates (spec, plan, tasks, adr, constitution, …)
├── INDEX.md                    <- Map of the workflow/ tree
├── PLANNING_WORKFLOW.md        <- How to plan, explore, gate approval
├── PLAN_GOVERNANCE.md          <- Lifecycle, staleness, question-forcing
├── TDD_GOVERNANCE.md           <- RED-first, mutation-gated test contract
├── QUICK_REFERENCE.md          <- Fast pattern lookup
├── PATTERNS.md                 <- Copy-paste code patterns
├── TECH_STACK_DECISIONS.md     <- Approved libraries and rationale
├── development_resources.md    <- Available infrastructure inventory
├── test_mock_registry.md       <- Mock governance registry
├── deferral_registry.md        <- Deferred production functionality registry
└── bug_registry.md             <- Known bugs, root causes, and fixes

docs/                           <- KNOWLEDGE: architecture, guides, reference, specs
├── gmd/                        <- Graph Markdown primer + spec
├── guides/  reference/  specs/  design/  archive/
└── architecture/               <- System architecture docs, ADRs, explorations
    ├── README.md               <- Architecture overview
    ├── ARCHITECTURE_INDEX.md   <- Architecture navigation
    ├── todo.md                 <- Tracked gaps
    ├── adr/                    <- Architecture Decision Records
    ├── concepts/               <- Stable domain concepts
    ├── explorations/           <- Design space research
    └── tech-stack/             <- Per-technology rationale
```

### Source of Truth {#source-of-truth}

1. `workflow/plan-of-plans.md` — index + sequenced execution order (Status column); what to implement next
2. `workflow/plans/` — all plans, permanently; each plan's `metadata.status` records its stage
   (`drafting` → `approved` → `in-progress` → `completed`)
3. `workflow/plans/<plan>-tasks/` — task specs for a plan (present once `status: approved`)

## Architecture Documentation {#architecture-documentation}

See `docs/architecture/` for detailed system design. Key docs: README.md,
ARCHITECTURE_INDEX.md, todo.md, adr/.

## Key Files {#key-files}

| File | Purpose | Update When |
|------|---------|-------------|
| `handoff.md` | Session context | Every session |
| `workflow/plan-of-plans.md` | Plan index + sequenced execution order (Status column) | Plan status changes/added |
| `workflow/plans/` | All plans (stage = `metadata.status`) + `<plan>-tasks/` specs | Plan status changes/added |
| `workflow/QUICK_REFERENCE.md` | Fast pattern lookup | New conventions |
| `docs/architecture/ARCHITECTURE_INDEX.md` | Architecture navigation | Architecture changes |
| `docs/architecture/todo.md` | Tracked gaps | Gap addressed/discovered |
| `workflow/PLANNING_WORKFLOW.md` | Full planning/exploration workflow | Workflow changes |
| `workflow/PLAN_GOVERNANCE.md` | Plan lifecycle, staleness, question forcing | Governance changes |
| `workflow/templates/` | All document templates | Template changes |

## When to Pause Mid-Task {#when-to-pause}

Only pause if: blocking dependency, ambiguous requirements, user requests, or critical decision.
**Do not ask** "Should I proceed?" — follow the Task Completion Workflow.
