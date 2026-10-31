# Run artifacts (debug later)

Every dispatch run writes a **run directory** the human can reopen after the
thread is gone. Prefer a stable machine path outside the git repo:

```text
~/.agents/t3-dispatch-runs/<project-slug>/<YYYYMMDD-HHMMSS>-<short-id>/
```

Fallbacks if home is awkward: `/tmp/t3-dispatch-runs/<same>`. Never commit these
into the project unless the human asks.

`<project-slug>` = repo folder name or Linear project key (`acme`, `JUR`, …).
`<short-id>` = 4–6 chars from the thread/run so collisions are rare.

## Layout (write as you go)

```text
<run-dir>/
  meta.json           # started_at, threadId, project, git HEAD, policies
  pending.md          # what was pending when you looked
  analysis.md         # frontier, blockers, recommended next wave
  selection.json      # human answers (selected ids) + policies + askTool
  research/           # notes per task id (absolute paths in briefs)
    ACME-39.md
  briefs/             # exact delegate_task.task text per child
    ACME-39.md
  dispatch.json       # taskId, provider, model, isolation, clientRequestId
  status.jsonl        # append-only: wake events, PR URLs, failures
  summary.md          # final table when the wave ends
```

## `meta.json` (minimum)

```json
{
  "skill": "t3-parallel-dispatch",
  "startedAt": "ISO-8601",
  "projectSlug": "acme",
  "gitHead": "sha",
  "threadId": "…",
  "wavePolicy": "frontier_only",
  "mergePolicy": "one_pr_per_child"
}
```

## `dispatch.json` (minimum)

```json
{
  "children": [
    {
      "taskKey": "ACME-39",
      "title": "…",
      "delegateTaskId": "node:delegated-task:…",
      "providerInstanceId": "cursor",
      "model": "composer-2.5",
      "role": "implementation",
      "isolation": "worktree",
      "briefPath": "briefs/ACME-39.md",
      "researchPath": "research/ACME-39.md"
    }
  ]
}
```

## `status.jsonl`

One JSON object per line when something happens:

```json
{"at":"ISO","event":"dispatched","taskKey":"ACME-39","delegateTaskId":"…"}
{"at":"ISO","event":"completed","taskKey":"ACME-39","summary":"…","pr":null}
{"at":"ISO","event":"failed","taskKey":"ACME-40","summary":"…"}
```

## Coordinator duties

1. Create `<run-dir>` **before** the ask, silently; tell the human the path once, in the summary line.
2. Update artifacts after each step (pending → analysis → selection → research →
   briefs → dispatch → status). Do not wait until the end.
3. Point every child brief at absolute paths under this run dir.
4. On the final summary message, repeat the run-dir path so debugging is one click.

## Debugging a past run

Read `analysis.md` + `selection.json` + `briefs/` + `status.jsonl`. That is
enough to see why a child got a bad brief or why a wave stalled — without the
parent transcript.
