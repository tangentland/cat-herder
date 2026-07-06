---
name: detour
description: Soft branch detour — bookmark focus to chase a related tangent, then return
argument-hint: [tangent label]
allowed-tools: [Bash]
model: inherit
enabled: true
---

# Detour

I'm about to chase something related but not on-task — a **soft branch detour**.
No git branch, no stash; just a focus return-point I can rewind to.

> Requires `rmx`. Without it, there is no focus state to bookmark — this is a
> no-op; just note the tangent manually.

Run:

```
rmx focus detour "$ARGUMENTS"
```

This bookmarks the current focus + log line. Now I'll go chase the tangent — it
keeps recording and will show as its own cluster in `rmx focus topics`, so the
detour is captured, not lost. When done, `/return` snaps focus back to here.

Confirm the return-point (label + L-line), then proceed with the tangent.
