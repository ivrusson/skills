---
name: t3-parallel-dispatch
description: >-
  Find what is pending (Linear/roadmap/git), work out the next frontier, ask
  the human which tasks to run through the harness's native question tool
  (multi-select), then plan economically and launch parallel T3 children on
  worktrees, persisting run artifacts for debugging. Use when the user asks
  what is pending, next steps, "qué falta", "lanza agentes", parallel
  worktrees, dispatch/swarm, or wants to pick tasks before fan-out — even if
  they do not name this skill.
---

# T3 parallel dispatch

You are the **coordinator**. Children do the work. Loop:

**pending → analyze → ask → research → brief → dispatch → supervise**,
persisting every stage under a run directory
([references/run-artifacts.md](references/run-artifacts.md)).

Works on **every T3 Code provider** that can run children. Refresh the catalog
each run; never assume fixed model ids.

## Dive in, then ask

The human invoked you to get moving, not to read a report. So:

- Do steps 0–2 **silently** (tool calls and files, no chat narration).
- Your first and only message before the question is **≤ 5 lines**: what is
  pending, what the frontier is, what you recommend. Detail lives in
  `pending.md` / `analysis.md` and in the option descriptions of the question.
- Then **call the ask tool in that same turn** (step 3).
- **Never** print task lists with `- [ ]` / `[ ]` / `☐` in the chat. They cannot
  be ticked and the human will rightly see that as the skill not working.
  Tables, `analysis.md` dumps and full plans in the bubble are the same failure.

## Tools (always refresh)

1. `orchestrator_capabilities` — who can run children, models, `maxBatchThreads`.
2. Tracker / repo sources for pending work (Linear MCP or API, `gh`, roadmap,
   `git status` / open PRs) — step 1.
3. **The ask tool** — step 3 and [references/ask-ui.md](references/ask-ui.md).
   Its name differs per provider; load it if it is deferred.
4. `delegate_task` with `isolation: "worktree"` for repo-editing children.
5. `task_status` / completion wakes — no sleep polls.
6. Dispatch contract: [references/harness.md](references/harness.md).

## Steps

### 0. Open a run directory (silent)

Create `~/.agents/t3-dispatch-runs/<project-slug>/<timestamp>-<short-id>/` and
write `meta.json` (git HEAD, thread id if known). Do not announce it yet; the
path goes in the last line of your summary (step 2).

**Done when:** the path exists.

### 1. Discover what is pending

Do **not** require the human to paste issue ids. Pull the backlog yourself:

| Source (use what exists) | Pull |
| --- | --- |
| Linear project / milestone in progress | Todo / In Progress / Backlog issues; blockers; parent epics |
| `docs/roadmap*.md`, ADRs | Stated “pending” / open gates |
| git / GitHub | Open PRs, branch vs `main`, failing checks if cheap |
| Conversation | Explicit “also do X” from the human |

Write `pending.md`: compact table of id, title, state, milestone, blockedBy,
folderHint (from issue body / AGENTS ownership).

Each candidate row:

| Field | Why |
| --- | --- |
| `id` | Option key (`ACME-40`, …) |
| `title` | One scan line |
| `state` | Todo / In Progress / … |
| `blockedBy` | Other ids |
| `folderHint` | Owned paths |
| `role` | `implementation` \| `research` \| `review` \| `design` \| `test` \| `general` |
| `whyNow` | One line: why it is (or is not) on the frontier |

**Done when:** `pending.md` lists the live backlog without inventing issues.

### 2. Analyze next steps

Write `analysis.md` **before** asking:

- Frontier = unblocked + actionable now
- Recommended wave (usually the frontier; call out must-sequence pairs)
- Ownership clashes if those ran in parallel
- Suggested model tiers (see [references/model-economy.md](references/model-economy.md))
- What you would **not** start yet (and why)

Then say the ≤ 5-line summary in the human's language (“pendiente: …;
frontier: …; recomiendo …; plan en `<run-dir>`”) and go straight to step 3.
Analysis alone is not consent to launch.

**Done when:** `analysis.md` exists and the summary is sent.

### 3. Ask (human gate) — native question tool required

1. Find the ask tool for this provider — table in
   [references/ask-ui.md](references/ask-ui.md). If it is not in your tool
   list, **try to load it** (e.g. `ToolSearch select:AskUserQuestion`) before
   concluding it is absent.
2. Call it **in the same turn** as the summary. Task ids are a **multi-select**.
   Put `blockedBy` / `folderHint` / `whyNow` in each option's description, not
   in chat. Ask wave policy and merge policy in the same call.
3. Respect the tool's limits (e.g. `AskUserQuestion` takes 2–4 options per
   question and ≤ 4 questions). More than 4 candidates: split by
   frontier/milestone across several questions, or offer presets
   (“Recomendado”, “Todo el frontier”) and let “Other” take custom ids. Never
   drop to markdown because the list “doesn't fit”.
4. If no ask tool exists anywhere: say which names you tried, offer a
   **numbered** list, ask the human to reply with ids, and stop. Never fake
   checkboxes. Do not silently fall back.

Stop until answers land. Save `selection.json` (include `askTool`). Echo
selection in one line.

**Done when:** you actually invoked an ask tool (or recorded the documented
fallback), `selected[]` is non-empty, and both policies are recorded.

### 4. Research → briefs → model pick

Cheap research (often one `role: research` child, `isolation: shared`) into
`research/<id>.md`. Then write `briefs/<id>.md` from
[references/child-brief.md](references/child-brief.md).

Economy: coordinator stays strong; children are where you save. Fast for UI /
mechanical; strong for protocol / agent runtime / ADR. Cap parallel strong
children. No overlapping folder owners in the same wave.

**Done when:** each selected frontier task has research + brief files and a
chosen `target` (provider/model/options).

### 5. Dispatch in one turn

For each frontier selected task, `delegate_task` in the **same** assistant turn:

- `isolation: "worktree"` for editors
- `mode: "async"`
- `task` = brief body (self-contained; absolute paths into this run dir)
- `clientRequestId` = `{runShortId}:{taskId}`

Append `dispatch.json` + a `status.jsonl` `dispatched` line. Tell the human, in
a few lines: task → model → that you will wake on completion → run-dir path.

**Done when:** every frontier call returned a `taskId`.

### 6. Supervise + keep the log warm

On each wake: `task_status`, append `status.jsonl`, unlock newly ready work,
dispatch the next frontier. One narrow retry on failure, else escalate.

When the wave settles, write `summary.md` (task → PR/result → follow-ups) and
point at the run dir for debugging.

## Hard edges

- Overlapping owners → serialize or split; never two editors on one package.
- No fake launches if `canRunChildTask` is false — offer serial fallback
  ([references/harness.md](references/harness.md)).
- Honor project rules (`AGENTS.md`, ADRs, “no paid AI in tests”, etc.).
- Never put secret values in artifacts; env var **names** are fine.

## Example things the human might say

- “¿Qué hay pendiente? Analiza el siguiente paso, pregúntame, planifica,
  lanza en worktrees y guarda el plan para debug.”
- “t3-parallel-dispatch — mira Linear Acme v0.2.0 y propón el frontier.”
- “Qué falta del epic OpenRouter/créditos y lanza lo que elija.”
