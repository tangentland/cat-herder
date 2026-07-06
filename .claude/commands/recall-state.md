---
name: recall-state
description: Recall state — orient on the prior session before doing anything
argument-hint: [optional focus hint]
allowed-tools: [Bash, Read, Grep, Glob]
model: inherit
enabled: true
---

# Recall State

"Recall state" is a resume directive: load the prior session's handoff and
orient before taking any other action. The mirror of "save state." Do every
step, then WAIT for direction — the orient pass is the whole job.

> Requires `rmx`. Without it, step 1 degrades to reading `handoff.md` directly.

1. **Latest handoff** — read `handoff.md` and recall the promoted STM digest +
   recent memories:
   ```
   rmx memory recall --session-start --k 10 --scope both
   rmx focus context        # the prior session's threads, if STM survived
   ```
2. **Git state** — branch, `git log --oneline -5`, `git status --short`, and
   how far ahead of the trunk (`git rev-list --count origin/main..HEAD`).
3. **Daemon/hub state** — `rmx daemon status` (+ `rmx hub status` if used);
   compare the running version against the latest shipped.
4. **Report the resume point**: branch + HEAD + version, what was last
   accomplished, open loose ends, the concrete next action, and any anomalies
   (dirty tree, unpushed commits, daemon on stale version).
5. **Wait** for direction. Do not start the next action automatically.

$ARGUMENTS
