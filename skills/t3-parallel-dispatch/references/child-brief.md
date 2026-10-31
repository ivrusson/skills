# Child brief template

Paste into `delegate_task.task`. Keep it self-contained: children see **no**
parent transcript.

```markdown
# {TASK_ID}: {short title}

## Mission
One paragraph: the user-visible or contract-level outcome.

## Context pointers (read first)
- Repo rules: `AGENTS.md` (and any path-specific agent guide)
- Specs/ADRs: {paths}
- Research notes: {absolute path to /tmp/t3-dispatch/...}
- Tracker: {Linear/issue URL if any}

## Own these paths
- {folder or glob list}

## Out of bounds
- {paths other children own}
- Do not change `{protocol package}` unless this task says so.

## Acceptance
- [ ] {concrete check}
- [ ] `pnpm check` green (or the package filter this repo uses)
- [ ] {PR opened / branch pushed} per merge policy: {policy}

## Implementation notes
Bullets only — no essays. Call out traps from research.

## Report back
End with: what changed, PR URL + head SHA if any, checks status, anything you
could not do, any contract change you need from the human.
```

## Brief quality bar

- **Pointers over paste.** Link docs; do not dump whole ADRs into the brief.
- **Ownership is a wall.** If two selected tasks share a file, do not dispatch
  both until you split ownership or serialize.
- **Language:** briefs in the repo's documentation language (often English).
- **Secrets:** name the env var (`OPENROUTER_API_KEY`); never put the value in
  the brief. Tell the child to use `request_secret` or existing env.
- **Size:** if the brief needs more than ~40 lines of notes, the research file
  was too thin or the slice is too wide — split the task.
