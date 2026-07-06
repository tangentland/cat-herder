---
gmd: "0.1"
id: unified-baseline-merge
title: "Unified Baseline Template Merge — SDD + rmx + cliquedb canon"
tags: [plan, cat-herder, meta]
metadata:
  node_type: plan
  created: 2026-07-06
  status: drafting
---

# Unified Baseline Template Merge {#root}

Evolve `cat-herder` into the unified baseline Claude Code template by folding in the matured
patterns from `cliquedb` (canonical), the `rmx`/refmatrix integration (engine), `viascope`
(historical lineage — ideas only), and grafting GitHub **spec-kit**'s spec-driven development
(SDD) command chain — with an **ADR phase** inserted between clarify and plan.

Sequenced by `workflow/plan-of-plans.md`.

## Source authority {#authority}

- **cliquedb** = canonical (newest; p20-0 guardrails, matured `ch-*` naming, clean rmx wiring).
- **refmatrix** = the `rmx` engine (integration source of truth).
- **viascope** = historical lineage. Harvest proven *ideas* (hook script primitives) only;
  do NOT copy its 16 domain agents or viascope-specifics.
- **spec-kit** (`~/claude_tools/spec-kit`, cloned) = SDD command chain + templates + scripts.

## Locked decisions {#decisions}

- **D1** — ADR phase sits between clarify and plan:
  `constitution → specify → clarify → adr → plan → tasks → analyze → implement`.
  ADR phase = `ch-architect` pre-impl mode: "what architectural clarity can we add to this
  spec?" → writes/updates `docs/architecture/adr/`; `plan.md` must cite the ADRs.
- **D3** — SDD chain named `ch-*`: `ch-constitution ch-specify ch-clarify ch-crucible ch-plan
  ch-tasks ch-analyze ch-implement`. Unifies with existing `ch-review/ch-audit/ch-bsd`.
- **D4** — Fold specs into `workflow/`: `workflow/specs/NNN-feature/{spec,plan,tasks,research,
  data-model,contracts/}`. Single tree. Constitution → `workflow/CONSTITUTION.md`.
  SDD scripts → `scripts/sdd/`. Templates → `workflow/templates/`.
- **D5** — rmx-only memory layer. Remove wolf `.js` hooks from `settings.json`. Hook regime = rmx
  canonical set; `install.sh` wires it. **OpenWolf is DROPPED entirely** (not merely demoted):
  removed from `install.sh`, CLAUDE.md, SETUP.md; `.claude/rules/openwolf.md` deleted. Its one
  valuable duty (bug logging) is replaced natively — see D10.
- **D6** — Ship +3 agents: `ch-alignment`, `ch-implementer`, `gmd-curator`. No domain stubs.
- **D7** — GMD is the DEFAULT format for ALL `docs/` + `workflow/` items, including every
  SDD template and the artifacts they produce (spec/plan/tasks/constitution). Templates carry
  GMD frontmatter + `{#anchor}` on every heading; cross-doc `rel:` edges are added when filled
  (they dangle at lint time in template context). `plan-of-plans.md` lives at `workflow/` root.
- **D8** — Neutral-def + local-overlay pattern. Committed agent defs (`.claude/agents/<a>.md`)
  are PROJECT-NEUTRAL and reusable. Project specifics are pulled in BY INCLUSION via a per-agent
  overlay `.claude/agents/<a>.local.md` the neutral def instructs reading first, plus a shared
  `.claude/PROJECT_PROFILE.md` for facts common to all agents + hooks. Hooks read paths from
  `.claude/hooks/hooks.env`, not hardcoded. **These project-specific files (overlays, profile,
  hooks.env) are COMMITTED once a project is init'd — they are the project's customization, not
  per-user local state.** The baseline template ships them as placeholders + `*.example`
  illustrations; init fills/creates and commits the real ones. Enforcement hooks (Phase 3) =
  curated 3: adr-gate, enforce-test-to-file, enforce-rmx-grep. rmx hook regime ships in committed
  `settings.json`, guarded so a no-rmx clone no-ops.
- **D9** — Idempotent upgrade pathway. `install.sh` (and any re-init) is NON-DESTRUCTIVE to
  project-specific files: it UPGRADES the neutral baseline (agent defs, commands, templates,
  `scripts/sdd/`, `.example` files) in place, but only CREATES project-specific files
  (`.claude/agents/<a>.local.md`, filled `.claude/PROJECT_PROFILE.md`, `.claude/hooks/hooks.env`)
  when ABSENT — never overwrites an existing one. This lets a project pull a newer baseline while
  keeping its customization. Re-running init = safe upgrade. Baseline neutral files are the
  upgradable layer; `*.local.*` + filled profile are the preserved layer.
- **D10** — The `/ch-adr` command is renamed **`/ch-crucible`** (spec put in the crucible → forge
  the architectural decisions as ADRs). And OpenWolf's buglog is replaced by a native
  `workflow/bug_registry.md` (GMD) curated like `test_mock_registry` / `deferral_registry`, with a
  `.claude/rules/bug-registry.md` read-before-fix / log-after-fix rule.
- **D12** — Better rmx STM (short-term/working memory) wiring, split by caller. **Hooks stay CLI**
  (plumbing): PreCompact + Stop now run `rmx focus summarize --promote` (the STM→LTM bridge — was
  missing `--promote`, so working memory died at compaction); SessionStart adds `rmx focus context`
  to surface the working thread on resume. **Agent-initiated STM/memory ops use the `refmatrix` MCP
  tools, not Bash CLI** (structured, no shell-quoting of multi-line reasoning, no permission/rtk
  friction): decisions → `rmx_focus_note` (extended-thinking is redacted from the transcript, so
  this is the only durable path for the WHY); `/ch-specify` sets `rmx_change_subject <NNN-slug>` so
  STM partitions per feature and digests file under it. CLAUDE.md "Write Decisions Immediately"
  extended accordingly. MCP > CLI for the agent; CLI is the hook exception.
- **D11** — Plan lifecycle is a STATUS FIELD, not a file move. All plans live permanently in
  `workflow/plans/`; `metadata.status` (drafting → approved → in-progress → completed) tracks
  stage. Retired `workflow/incomplete_plans/` and `workflow/completed_plans/`; folded `todo.md`
  into `workflow/plan-of-plans.md` (single index+sequence with a Status column). No moving files,
  no relinking on stage change.

## Target flow {#flow}

```
/ch-constitution → workflow/CONSTITUTION.md         (principles; gate re-checked at plan)
/ch-specify      → workflow/specs/NNN-*/spec.md      (what/why, tech-agnostic, P1/P2/P3 stories)
/ch-clarify      → updates spec.md                   (≤5 Q&A, resolve [NEEDS CLARIFICATION])
/ch-crucible          → docs/architecture/adr/NNNN-*.md   (D1 — architectural decisions from spec)
/ch-plan         → specs/NNN-*/{plan,research,data-model,contracts/}  (how; Constitution+ADR check)
/ch-tasks        → specs/NNN-*/tasks.md              ([T###] [P] [US#] + exact paths, checkpoints)
/ch-analyze      → report                            (cross-artifact consistency, pre-implement)
/ch-implement    → source code                       (execute tasks; then /ch-review + @ch-bsd)
```

rel: implements -> [[#decisions]]

## Phase 1 — SDD command chain + templates (additive, non-destructive) {#phase-1}

Deliverables:
1. `.claude/commands/ch-{constitution,specify,clarify,adr,plan,tasks,analyze,implement}.md` —
   8 command files, house frontmatter style (`.claude/commands/ch-review.md` shape), bodies adapted from
   spec-kit `templates/commands/*.md` but: ch-* names, `handoffs:` chain rewired to ch-*,
   scripts pointed at `scripts/sdd/`, ADR step wired in (ch-crucible dispatches `ch-architect`).
2. `workflow/templates/{spec,plan,tasks,constitution,checklist,adr}-template.md` — adapted from
   spec-kit templates; adr-template from refmatrix `docs/templates/adr-template.md` + cliquedb
   ADR format. Add `[P]`/checkpoint markers to tasks-template.
3. `scripts/sdd/{create-new-feature,setup-plan,setup-tasks,check-prerequisites,common}.sh` —
   from spec-kit `scripts/bash/`, retargeted: feature dir = `workflow/specs/NNN-*`,
   template resolution → `workflow/templates/`.
4. `workflow/CONSTITUTION.md` — synthesized from CLAUDE.md tenets + PLAN_GOVERNANCE, constitution
   gate that `ch-plan` re-checks.

Acceptance: each command file lints as valid; scripts run `--dry-run` clean; a smoke run of
`/ch-specify` creates `workflow/specs/001-*/spec.md`.

## Phase 2 — Agents +3 (additive) {#phase-2}

Deliverables: port from cliquedb, sanitized to generic template (strip domain specifics):
- `.claude/agents/ch-alignment.md` — pseudocode/ ground-truth drift detector; reinforces ch-crucible.
- `.claude/agents/ch-implementer.md` — TDD executor (RED→GREEN), authors NO tests; pairs with
  ch-test-engineer.
- `.claude/agents/gmd-curator.md` — GMD docs as rmx-backed graph (already an available type;
  vendor the file into the template).
Update CLAUDE.md agent table + `.claude/commands` cross-refs.

rel: depends-on -> [[#phase-1]]

## Phase 3 — rmx-only hook regime (DESTRUCTIVE — settings.json rewrite) {#phase-3}

Deliverables:
1. Rewrite `.claude/settings.json` — remove wolf `.js` PreToolUse/PostToolUse/Stop/SessionStart
   hooks; install rmx canonical set (refmatrix/cliquedb): SessionStart (flush + `rmx primer` +
   `rmx memory recall --session-start`), UserPromptSubmit (`rmx scan-prompt` + focus + recall),
   PostToolUse Edit/Write (`rmx sync --enqueue-only`) + focus, Stop/SubagentStop (`rmx sync
   --flush-queue`), PreCompact (`rmx focus summarize` + recall). All `RMX_INVOCATION_SOURCE=hook`,
   heavy ones `& disown`.
2. `.claude/hooks/` script library — port high-value enforcement from viascope (validate each is
   still in cliquedb): `enforce-rmx-grep.sh`, `enforce-test-to-file.sh`, `adr-gate.sh`,
   `session-start-adr-summary.sh`, `post-edit-diagnostics.sh`, `enqueue-edit.sh`. Genericize.
3. Wolf: keep `.wolf/hooks/` files on disk but UNWIRED; retain buglog.json duty only. Update
   `.claude/rules/openwolf.md` + `.wolf/OPENWOLF.md` to reflect demotion.
4. `install.sh` — detect rmx; if present run `rmx install-hooks --apply`; if absent, warn +
   leave settings.json rmx hooks as no-ops (rmx commands simply not found — degrade quietly).

Guard: git branch before touching settings.json. Verify hooks parse (`node`/`bash -n`).

rel: depends-on -> [[#phase-2]]

## Phase 4 — workflow/ restructure + governance merge {#phase-4}

Deliverables:
1. Create `workflow/specs/` (with README explaining the per-feature SDD chain vs the meta
   plan-of-plans/governance layer).
2. Merge governance docs from cliquedb: `TDD_GOVERNANCE.md`, `deferral_registry.md`, extend
   `PLAN_GOVERNANCE.md`. Add `workflow/specs/` to `INDEX.md` + doc hierarchy in CLAUDE.md.
3. Add p20-0 guardrail compiler (cliquedb) as OPTIONAL under `.claude/p20-0/` +
   `guardrails/` memory dir; document in SETUP.md; wire SessionStart compile hook (gated on
   presence). **DONE** — self-contained `.claude/p20-0/` (compiler + validate.py RED oracle +
   golden_cases + 3 universal seed guardrails); compile→validate GREEN 12/12, idempotent;
   SessionStart hook gated on `p20-0` dir + rmx. cliquedb DB-lane guardrails dropped as project-specific.
4. Session-state command suite (cliquedb/refmatrix): `.claude/commands/{save-state,recall-state,
   commit-state,detour,return,stash,stash-list,stash-pop}.md` — rmx-backed; document as
   rmx-dependent.

rel: depends-on -> [[#phase-3]]

## Phase 5 — MCP + docs + install reconcile {#phase-5}

Deliverables:
1. `.mcp.json` — add `refmatrix` (`rmx mcp`) + `tldr` servers to the existing 7. Keep all keys
   as `${ENV_VAR}` (scrub any literal secrets — viascope leaked keys, do NOT propagate).
   Update `settings.local.json` enabled set.
2. Per-tool briefings: `.rtk/CLAUDE.md`, `.tldr/config.json`, `.refmatrix/CLAUDE.md`+`PRIMER.md`,
   `.gmd/config.yml` — vendor sanitized copies (cliquedb versions, no project specifics).
3. CLAUDE.md — new "Spec-Driven Development" section documenting the ch-* flow + ADR gate;
   update agent/command tables; update Task Completion Workflow to reference the SDD chain;
   rewrite OpenWolf preamble → demoted.
4. SETUP.md + install.sh — document optional tiers (rmx, tldr, p20-0), placeholder substitution.
5. `.github/workflows/` — vendor generic `ci.yml` skeleton (lint/type/test in Docker) +
   `gmd-lint` check. Mark as template to customize.

rel: depends-on -> [[#phase-4]]

## Out of scope {#oos}

- Copying viascope's 16 domain agents (vs-*), 8+1 domain model, GStreamer/Lance specifics.
- Any runtime state (`.memory.db*`, `.faiss`, catalogs, session DBs, logs).
- Live secrets from any source `.mcp.json`.
- The `specify` CLI itself (we adopt the *pattern*, ch-* named, not the pip tool).

## Execution order {#order}

Phase 1 (additive) → 2 (additive) → 3 (destructive, branch-guarded) → 4 → 5. Each phase = own
branch, `ch-code-reviewer` pass, commit. Full `/ch-review` at Phase 3 and Phase 5 boundaries.
