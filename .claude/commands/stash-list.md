---
name: stash-list
description: List stashed work — focus task stack + paired git stashes
allowed-tools: [Bash]
model: inherit
enabled: true
---

# Stash List

Show everything I've stashed so I can pick one to resume (possibly out of
order):

> Requires `rmx` for the focus task stack. Without it, only `git stash list`
> is shown.

```
rmx task list
git stash list
```

`rmx task list` is the focus stash stack (1-based, top = most recent). The git
stashes carry a matching `rmx-stash: <desc>` message. Pair them by description
and present a short numbered list so I can choose which to `/stash-pop`.
