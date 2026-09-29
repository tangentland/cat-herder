---
gmd: "0.1"
id: adr-0001-project-fact-ownership-and-install-time-tuning
title: "ADR-0001: Project-fact ownership and install-time tuning"
tags: [adr, architecture, install, tuning, project-profile]
metadata:
  node_type: adr
  status: Accepted        # Proposed → Accepted (ratified) → Superseded (retired)
  date: 2026-09-29
  governs: [ProjectProfile, HooksEnv, TuneProject, InstallDetection, Scaffoldignore]
---

# ADR-0001: Project-fact ownership and install-time tuning {#root}

This ADR records decisions that have already shipped, on `main` at `73404d8`. There is no feature
spec, so it is derived from the implementation and its review. The implementation summary
(`workflow/implementation_summaries/install-project-tuning.md`) and the review triage are the
evidence.

rel: realizes -> [[SETUP#tune]]
rel: realizes -> [[SETUP#scaffold]]
rel: related-to -> [[ONBOARDING#sequence]]
rel: derives-from -> [[problem-log#install-project-tuning]]
rel: depends-on -> [[claude#no-workarounds]]
rel: depends-on -> [[claude#architectural-principles]]

## Context {#context}

The template's project-neutral agents, commands and hooks get project facts by reference. They
never hardcode them. Two files carry those facts:

- `.claude/PROJECT_PROFILE.md` is prose for agents: identity, stack, layout, commands and corpus.
- `.claude/hooks/hooks.env` is shell variables that every enforcement hook sources: `SRC_DIR`,
  `CORPUS_PATHS`, `CORPUS_EXTS` and `ADR_GATE_FILE_RE`.

The template ships these with Python/Docker defaults. Install used to leave all adaptation to the
agent. `scripts/tune-project.py` now detects the target's languages, layout and commands (or asks
for them, for a from-scratch project) and writes both files at install time.

Once a machine and a person can both write the same facts, ownership has to be explicit. The
first review of the tuner found three failures, all caused by ownership being unstated:

- **Re-runs did nothing.** hooks.env counted as "project-edited" the moment the tuner first wrote
  it, and the detection section never refreshed.
- **Invented facts.** Commands were wrapped in `docker compose exec dev … | tee /test-output`
  with `/opt/<pkg>-venv` whenever *any* compose file existed. This contradicted the rule that
  commands come from evidence only (bug-004).
- **No single source.** PROFILE and hooks.env were two fact stores with nothing tying them
  together.

The review also found the runtime-state exclusion list defined five or six times across
`install.sh` and the docs. Two copy paths had drifted apart, and `settings.local.json` leaked into
targets.

The forces here pull in different directions:

- Detection is useful, but it is heuristic. A scratch directory can look like a source root.
- A person's correction must never be overwritten by a later run.
- Re-running must stay useful as the codebase grows.
- The installer runs in CI and in piped installs, where there is no one to answer a prompt.
- The Constitution's *No workarounds* and *Reason from tenets* principles (mirrored in CLAUDE.md)
  forbid guessing past missing evidence and forbid parallel copies of the same fact.

## Decision {#decision}

`PROJECT_PROFILE.md` is the authoritative store of project facts. Every other place that holds a
project fact is either derived and owned by the generator, or owned by the project. Ownership
passes from the generator to the project, never back. The generator writes only what it can
prove from evidence or from the user's own answers.

### D1. The profile is authoritative {#d1-profile-authoritative}

- `PROJECT_PROFILE.md` is the fact store that agents read.
- When the profile and a derived artifact disagree, the profile wins. The derived artifact is
  what gets corrected.

### D2. Profile fields: the tuner fills placeholders only {#d2-fill-placeholders-only}

- The tuner writes a field only while it still holds the template's value (`untouched()`):
  - a `{…}` placeholder,
  - a template token (`{PROJECT_NAME}`, `{project_package}`, `{project_db}`),
  - an elided `…` example, or
  - a shipped default listed in `PRISTINE`.
- A field is not treated as a placeholder merely because it contains braces. `ruff check
  {src,tests}` is a project value.
- A filled field belongs to the project and is never rewritten.
- Once identity and stack are filled, the profile counts as *tuned*. On re-run the tuner fills
  any remaining placeholders and prints `drift:` lines where detection now disagrees (for example
  a new language or source root). It does not apply those changes.

### D3. The `Install detection` block belongs to the generator {#d3-detection-block}

- The block between `<!-- tune-project:begin … -->` and `<!-- tune-project:end -->` is evidence,
  not facts. It records the mode, file counts, manifests, minor languages, skipped unsafe paths,
  Docker services and ADR-gate status.
- Every non-dry run replaces it completely. Edits made inside it are lost.
- A hand-tuned profile that never had the block does not get one added.

### D4. hooks.env is derived and owned by digest {#d4-hooks-env-digest}

- The generator owns `hooks.env` while it is one of these:
  - absent,
  - identical in its assignment lines to `hooks.env.example`, or
  - carrying a first-line `# tune-project:generated sha256=<16 hex>` digest that still matches
    its assignment lines. Comments and blank lines do not count toward ownership.
- While the generator owns it, every run regenerates it.
- Once any value is edited, the file belongs to the project and is preserved. The run prints the
  values it would have written, so the difference is visible.
- Only paths that match `SAFE_PATH_RE` reach the file, and values are single-quoted. Every hook
  sources this file, so this is a security boundary (bug-002), not a formatting choice.
- `hooks.env` is never scaffolded from the template (`.scaffoldignore`). Each target gets its own.

### D5. Commands come from evidence only {#d5-evidence-only}

- A test, lint, type-check or format command is recorded only when there is evidence for it: a
  tool config file, a declared dependency, a `package.json` script, or a `Makefile` target. JVM
  commands also need a build tool.
- With no evidence, the field reads `— (none detected — do not invent one)`.
- Docker wrapping has to be proven piece by piece:
  - `docker compose exec dev bash -c "…"` only when the compose file defines a `dev` service,
  - `| tee /test-output/<log>.log` only when that mount is declared, and
  - `/opt/<pkg>-venv` only when the Docker files reference it. From-scratch projects are the one
    exception, where it is explicitly marked *proposed*.
- If none of that is proven, commands are recorded as host commands, and the profile's Docker
  sentence says why (for example "compose has no `dev` service").

### D6. From-scratch projects: prompt, never guess {#d6-from-scratch}

- With no code and no manifests, the tuner asks for the details: name, one-liner, languages,
  package, frameworks, database, UI directory and OS. It uses stdin or `/dev/tty`.
- The answers produce a conventional layout. Commands are marked *proposed*. An empty skeleton is
  created only if the user opts in.
- With no terminal and no `--lang`, the tuner changes nothing and exits `3`. `install.sh` records
  that as *skipped*, not *tuned*.
- Flags (`--lang= --name= --package= --db= --ui= --os=`) are the non-interactive way to supply
  the answers, and they go through detection so the layout is recomputed.

### D7. The installer is mechanical; the agent applies judgement {#d7-mechanical-vs-judgement}

- `install.sh` together with the tuner does only what can be checked mechanically:
  - scaffold,
  - detect,
  - fill placeholder fields,
  - write the derived artifact, and
  - wire the tooling.
- It does **not** expand placeholders in `CLAUDE.md` or `.mcp.json`, rewrite CLAUDE.md's
  Development Commands or Docker rule, write domain sections (primitives, glossary, constraints),
  create overlays, or set the constitution.
- Those steps need judgement, so they belong to agent onboarding ([[ONBOARDING#sequence]]).
  Onboarding also treats detection as a starting point and confirms every value with the user.

### D8. One manifest for scaffold exclusions {#d8-scaffoldignore}

- `.scaffoldignore` is the only list of paths never copied from the template into a target:
  - runtime state (`.refmatrix/`, `.tldr/`, `.agents/`, `.augment/`, `skills-lock.json`, …),
  - per-user state (`.claude/settings.local.json`),
  - template-only outputs (`.selftest/`, `workflow/review-output/`, …), and
  - the derived `hooks.env`.
- The rsync path (`--exclude-from`) and the no-rsync Python fallback both read this file, and a
  test checks that they behave the same.
- If the file is missing, `install.sh` refuses to scaffold. It does not fall back to a built-in
  list.
- Documentation describes the manifest and gives the reason for each entry. It does not keep a
  second copy of the list.

### D9. Re-running is safe but is not an upgrade {#d9-rerun-not-upgrade}

- Scaffolding is `--ignore-existing`: it adds missing files and never overwrites existing ones.
- Re-running `install.sh` or the tuner is therefore safe. Project edits survive, and the
  generator-owned outputs (D3, D4) are refreshed.
- For the same reason it is **not** a baseline upgrade. Newer agent definitions, hooks, or the
  tuner itself are not pulled into an existing project. Adopters copy a baseline file over
  deliberately.
- The refresh mechanism, a manifest of template-owned paths that are safe to overwrite, is left
  open as GAP-002.

rel: depends-on -> [[architecture-todo#open-gaps]]

The ownership model as data:

```
ProjectFactOwnership:
    ProjectProfile.field           -> generator while untouched(); project once filled (one-way)
    ProjectProfile.InstallDetection -> generator, always (replaced wholesale per run)
    HooksEnv                       -> generator while absent | == example | digest matches;
                                      project once any assignment is edited (one-way)
    Scaffoldignore                 -> template (single exclusion manifest; both copy paths)

TuneProject.run(root, flags) -> exit
    exit 0  tuned (or tuned profile refreshed: placeholders, detection block, drift report)
    exit 2  bad arguments
    exit 3  from scratch, no tty, no --lang: nothing written

TuneProject.command(kind) -> string
    evidence(kind) is empty           -> "— (none detected — do not invent one)"
    greenfield                        -> "`cmd` (proposed)"
    compose.services contains "dev"   -> docker compose exec dev bash -c "cmd[ | tee /test-output/..]"
                                         (tee only if /test-output mount declared)
    otherwise                         -> host "cmd"
```

## Consequences {#consequences}

- **Positive:**
  - A person's correction is never overwritten.
  - Re-running is useful again. hooks.env and the detection block follow the codebase while the
    generator owns them, and `drift:` lines show when the project's own values have gone stale.
  - No recorded command is made up. A missing command shows up as a gap for onboarding to
    resolve, which is the *No workarounds* principle applied to install.
  - CI and piped installs do nothing rather than guess, and they report that they skipped.
  - Only one exclusion list can drift, and the parity test covers it.
- **Negative:**
  - Once a person edits hooks.env, it no longer follows the codebase. They have to
    reconcile it by hand, guided by the values the tuner prints.
  - A generator-owned hooks.env is regenerated **from detection, not from the profile**. If an
    agent corrects the profile's `Source root` without touching hooks.env, the next re-run
    rewrites `SRC_DIR` from detection. The derived artifact then disagrees with the authoritative
    store, and only the digest rule makes that recoverable. The fix recommended in review is not
    built yet: a `--sync-hooks` mode that derives hooks.env from the profile's layout and corpus
    fields. Onboarding step 4 covers the gap with a manual check.
  - Filled profile fields are never refreshed. A profile tuned before a new language arrived stays
    wrong until someone acts on the `drift:` line.
  - Adopters stay on the baseline version they scaffolded (GAP-002).
- **Neutral:**
  - The tuner keeps a separate `TEMPLATE_PATHS` set: template-owned paths that the source census
    skips. It serves a different purpose from `.scaffoldignore`: *do not read these as project
    code*, as opposed to *do not copy these*. It should converge with the upgrade manifest that
    GAP-002 will need, so that three lists of template-owned paths do not appear.
  - The ADR gate's language coverage is out of scope here. The gate matches `class X` only, so
    the tuner sets `ADR_GATE_FILE_RE='^$'` for Go, Rust, Elixir and SQL. The gate is inert for
    those languages, and D3 requires the detection block to say so. Per-language coverage is
    tracked as GAP-001 and needs its own decision.

What plans must honor:

- Any new generated artifact carries an ownership marker that follows D4 or D3.
- Any new command source follows D5.
- Any new runtime-state directory goes into `.scaffoldignore` and nowhere else.
- No installer step takes on judgement work that belongs to onboarding.

Follow-ups this ADR enables:

- a template-refresh/upgrade ADR (GAP-002),
- an ADR-gate language-coverage ADR (GAP-001), and
- the profile-to-hooks.env sync described above.

rel: motivates -> [[architecture-todo#open-gaps]]

## Alternatives considered {#alternatives}

1. **hooks.env as the source of truth, with the profile generated from it.** Rejected. hooks.env
   holds only the facts that hooks need. Agents need identity, stack, commands and domain prose
   as well, and a shell file cannot hold those. It would also put agent-facing facts in a
   gitignored, sourced file.
2. **Fully generated profile and hooks.env, regenerated on every run (no project ownership).**
   This is the simplest to reason about, and the files would never go stale. Rejected because
   detection is heuristic. Every correction onboarding makes (a scratch directory taken for a
   source root, a minor language) would be undone by the next run, so people would stop running
   the tuner.
3. **Write once, never regenerate (the pre-review behaviour).** This is maximally safe for edits.
   Rejected because re-running became a no-op in practice, while the docs said re-running
   refreshes.
4. **Ownership by mtime or a "do not edit" header instead of a content digest.** An mtime is
   meaningless after git checkout, and a header can be ignored. The digest detects actual value
   edits and ignores comment-only changes. Its cost is that any edit, however small, gives the
   whole file to the project, and ownership never returns to the generator unless the file is
   deleted. That is accepted as simple and predictable.
5. **Generate hooks.env from the profile (`--sync-hooks`) now.** This is architecturally cleaner
   and is the preferred end state (see Consequences). Deferred, not rejected. It requires parsing
   project-authored Markdown fields reliably, and hand-tuned profiles rename fields
   (`Language:` for `Language(s):`), so the parser needs its own contract.
6. **Docker-wrap whenever a compose file exists (the original behaviour).** This matches CLAUDE.md's
   Docker-only convention. Rejected because it recorded commands that cannot run (a compose file
   with only an `api` service). A template convention recorded as a project fact breaks D5.
7. **Guess a stack when a from-scratch install has no terminal.** Everything would come out
   "tuned". Rejected: it is exactly the invented fact D5 forbids. Exit `3` plus a clear re-run
   hint is honest.
8. **Have the installer expand CLAUDE.md placeholders and rewrite its commands too.** Fewer
   onboarding steps, but CLAUDE.md prose mentions the placeholders literally, and rewriting its
   Docker rule is a judgement call. Rejected under D7.
9. **Hardcode exclusions in `install.sh` (the original five or six copies).** Rejected: the
   copies had already drifted, which is how `settings.local.json` leaked into targets.
10. **Make re-install an upgrade by overwriting baseline files.** This would clobber adopters'
    edits to agent definitions and hooks. It needs a template-owned-path manifest and a
    conflict policy, and was deferred as GAP-002 rather than done unsafely.

## References {#references}

- Setup, Step 1 (scaffold): [[SETUP#scaffold]]. Setup, Step 2 (tune): [[SETUP#tune]].
- Agent onboarding: [[ONBOARDING#sequence]].
- Review triage: [[problem-log#install-project-tuning]].
- Open gaps GAP-001 (ADR-gate language coverage), GAP-002 (baseline upgrade) and GAP-005 (this
  ADR): [[architecture-todo#open-gaps]].
- Bugs fixed on the way (in `workflow/bug_registry.md`):
  - bug-002: hooks.env shell injection, which is the reason for the D4 safe-path rule.
  - bug-004: invented Docker, venv and tee, which is the reason for D5.
- Implementation: `scripts/tune-project.py` (`untouched`, `profile_is_tuned`, `drift`,
  `fill_profile`, `env_regenerable`, `hooks_env`, `fmt_cmd`, `TEMPLATE_PATHS`), `install.sh`
  (`scaffold_project`, `tune_project`), `.scaffoldignore`, `.claude/hooks/hooks.env.example`,
  `.claude/PROJECT_PROFILE.md`.
- Implementation summary: `workflow/implementation_summaries/install-project-tuning.md`.
- Constitution principles II (*No workarounds*) and III (*Reason from tenets*):
  `workflow/CONSTITUTION.md`.
- Related ADRs: none (this is the first ADR).

rel: related-to -> [[architecture-index#adr]]
