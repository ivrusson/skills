# Harness: ask + dispatch (all T3 providers)

Refresh `orchestrator_capabilities` every run. Providers and models change;
disabled instances (`canRunChildTask: false`) are not candidates.

## Ask gate (mandatory)

Full discovery, schemas, limits and fallbacks: [ask-ui.md](ask-ui.md).

**Invariant:** after `analysis.md`, the next human-facing action is an **ask
tool call** in the same turn as a ≤ 5-line summary — never a markdown
`- [ ]` list.

Priority:

1. **Native question tool** with multi-select over task ids + wave/merge
   policy: `AskUserQuestion` (Claude), `AskQuestion` (Cursor). Load it first if
   it is deferred.
2. Other MCP **`ask_user`** when that is the thread's product surface.
3. **`muelle_ask` presets** when (1)–(2) are missing.
4. **Numbered list** only after stating which ask tools were missing; then
   stop and wait.

Do not invent a selection. Echo parsed selection before research.

## Language

Match the human's language for picker labels and confirmations. Keep child
briefs, commit messages, and Linear text in the **project's doc language**
(often English per `AGENTS.md`).

## `delegate_task` contract (t3-code)

| Field | Guidance |
| --- | --- |
| `task` | Full brief; no reliance on parent chat |
| `title` | ≤60 chars; includes issue id when any |
| `role` | Maps to economy tier in `model-economy.md` |
| `isolation` | `worktree` for repo edits / PRs; `shared` for read-only research |
| `mode` | `async` for fan-out; `wait` only when the next sentence needs the result |
| `target.providerInstanceId` | Must have `canRunChildTask: true` |
| `target.model` | From that provider's catalog this turn |
| `target.options` | Effort/fastMode/variant only if listed for that model |
| `runtimeMode` | Inherit unless the human asked for a supervised child |
| `clientRequestId` | `{runId}:{taskId}` so retries do not double-dispatch |

Batch: one assistant turn → many `delegate_task` calls, up to `maxBatchThreads`
(often 20). Prefer fewer, sharper children over a flood of tiny ones.

## Providers that cannot run children

If the only live provider has `canRunChildTask: false`, say so and stop — or
offer to continue as a **serial coordinator** in this thread (no worktree
fan-out). Do not pretend parallel dispatch happened.

## Worktrees

`isolation: "worktree"` prepares a checkout from the parent commit; uncommitted
parent edits stay out. Tell children:

- branch naming: `agent/{task-id-slug}` or the repo's convention
- run project checks before finishing
- open a PR when the human's merge policy is `one PR per child`
- never watch PRs from a child thread

## Completion

Use completion notifications + `task_status`. No `sleep` polls, no `gh --watch`
loops. Parent may `link_pull_request` / `watch_pull_request` on its own thread
after the child reports a PR URL.
