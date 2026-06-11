# Planning & Exploration Workflow

This document contains the full planning workflow, exploration workflow, and plan approval
gate. Referenced from CLAUDE.md.

## Write Decisions Immediately (CRITICAL)

**Architectural discussions and decisions MUST be written to files as they happen — not
deferred to task completion or session end.** Context compaction can erase unwritten
discussion at any time.

**Rules:**
- When an architectural decision is reached in conversation, **immediately** write it to the
  relevant architecture doc, ADR draft, or `docs/architecture/explorations/` file
- When discussing trade-offs between approaches, write a brief summary to a file **before**
  continuing to the next topic
- Do NOT accumulate decisions in conversation context expecting to write them later

**What to capture immediately:**
- Technology choices (write to `docs/architecture/todo.md` or create ADR draft)
- Design decisions (write to relevant architecture doc)
- Rejected alternatives and why (write to ADR or exploration doc)
- User preferences and directives (write to `handoff.md` User Preferences section)

**Pattern:** Discussion → Decision → Write to file → Continue discussion

## Three-Stage Plan Lifecycle

Plans move through three stages with corresponding directory locations:

| Stage | Location | Meaning |
|-------|----------|---------|
| **Drafting** | `workflow/incomplete_plans/<plan-name>.md` | Design in progress, no task specs yet |
| **Approved** | `workflow/plans/<plan-name>.md` + `workflow/plans/<plan>-tasks/` | Task specs written, ready to implement |
| **Completed** | `workflow/completed_plans/<plan-name>.md` | Implementation done, archived |

**Meta-tracking files** (always in `workflow/incomplete_plans/`):
- `plan-of-plans.md` — sequenced execution order (source of truth for what comes next)
- `todo.md` — all plans indexed with status

## Exploration Workflow

Explorations are **research documents** that investigate a design space before decisions are
made. They precede proposals in the pipeline:

```
Exploration (research) → Proposed Plan (decisions) → ADR (if architectural) → Task Specs (implementation)
```

Not every change needs an exploration — straightforward tasks go directly to proposed plans
or implementation. Use an exploration when:

- The design space is unclear or has multiple valid approaches
- Research is needed before options can be evaluated
- The topic is large enough to warrant structured analysis before deciding
- The user explicitly asks to explore a topic

### Creating an Exploration

1. **Create the file** at `docs/architecture/explorations/<topic>.md`
2. **Write findings incrementally** as research proceeds — same compaction-safety rules apply

### Exploration Lifecycle

| Status | Meaning |
|--------|---------|
| `In Progress` | Research ongoing, findings being written |
| `Research Complete` | Analysis done, not yet transitioned to proposal |
| `Transitioned to Proposal` | Transition Summary written, proposed plan created |
| `Promoted to ADR-NNNN` | Decisions made, captured in an ADR |

Explorations are **never deleted** — they serve as the research record for why decisions
were made.

### Transitioning from Exploration to Proposal

When research is sufficient to frame decisions, create an explicit **Transition Summary**
in the exploration document before creating the proposed plan.

**Steps:**

1. Write the Transition Summary in the exploration file (What Survived, What Was Eliminated,
   Key Constraints, Open Questions, What Is NOT Moving Forward)
2. Update the exploration status to `Transitioned to Proposal`
3. Create the proposed plan at `workflow/incomplete_plans/<topic>.md`
4. Update `workflow/incomplete_plans/todo.md` with the exploration → proposal link
5. Follow the Planning Mode Workflow below

## Planning Mode Workflow (CRITICAL)

**All proposed plans MUST be written to disk BEFORE presenting questions to the user.**

### Before Asking Questions

1. **Write the proposed plan to disk** at `workflow/incomplete_plans/<topic>.md`
   - Include: context, options considered, proposed approach, open questions
   - Each open question gets its own numbered section with options
   - Mark all questions as `**Status: OPEN**`

2. **Append a reference** to `handoff.md`:
   ```
   **Active Proposed Plan:** [<topic>](workflow/incomplete_plans/<topic>.md) — <n> open questions
   ```

3. **Then** present the plan and questions to the user

### When the User Answers a Question

After **each individual answer** from the user:

1. **Update the proposed plan file** — change question status from OPEN to RESOLVED,
   record the decision and rationale
2. **Continue** to the next question or topic

**Pattern:** Ask question → User answers → Write answer to plan file → Continue

### When the User Explores a Tangent

1. **Write exploration notes** to the proposed plan file (add a `### Discussion` subsection)
2. **Do NOT wait** for the tangent to resolve before writing — write incrementally

### When All Questions Are Resolved

1. Update plan file status to `Accepted` (or `Revised` if approach changed)
2. Update `handoff.md` reference from "Active" to "Completed"
3. Update `workflow/incomplete_plans/todo.md` with the completed plan entry
4. **Immediately create ALL task spec files** (see Plan Approval Gate below)
5. Move plan to `workflow/plans/<plan-name>.md` with task specs in `workflow/plans/<plan>-tasks/`
6. Then proceed to implementation

## Plan Approval Gate (CRITICAL)

**After a plan is approved, ALL task spec files MUST be created BEFORE any implementation
begins.**

### Workflow: Plan Approved → Tasks Created → Implementation

1. **Create ALL task spec files** for the plan immediately after approval:
   - Location: `workflow/plans/<plan>-tasks/task-N.M-description.md`
   - Use the task spec template (see `workflow/templates/task-spec.md`)
   - Reference specific decisions from the proposed plan discussion
   - Capture dependencies between tasks

2. **Move the plan** from `workflow/incomplete_plans/` to `workflow/plans/`:
   - Plan file: `workflow/plans/<plan-name>.md`
   - Task specs: `workflow/plans/<plan>-tasks/`
   - Verify task count matches

3. **Update tracking files**:
   - `workflow/incomplete_plans/todo.md` — mark plan as "Approved → workflow/plans/"
   - `workflow/incomplete_plans/plan-of-plans.md` — update status
   - `handoff.md` — note that task specs are ready for implementation

4. **Gate**: Do NOT start implementing Task N.1 until all task specs exist on disk

### Why This Matters

Task specs serve as **self-contained implementation briefs**. When a new session starts
Task N.3, the task spec file contains everything needed — requirements, architecture
references, decisions, files to touch — without needing to reconstruct planning context.

## Templates

All templates are in `workflow/templates/`:

| Template | Purpose |
|----------|---------|
| [task-spec.md](templates/task-spec.md) | Individual task specification |
| [proposed-plan.md](templates/proposed-plan.md) | Proposed plan with open questions |
| [exploration.md](templates/exploration.md) | Design space research document |
| [handoff-session.md](templates/handoff-session.md) | Session handoff format |
