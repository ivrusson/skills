# Model & harness economy

Pick the **cheapest child that can finish without a retry tax**. A failed cheap
run that needs a frontier retry often costs more than starting one tier up.

Always resolve names from **this turn's** `orchestrator_capabilities`. The
tables below use **roles**, not frozen model ids — map role → best available
model on an enabled provider (`canRunChildTask: true`).

## Role → tier

| Role / work shape | Tier | Effort / options | Typical mapping (when present) |
| --- | --- | --- | --- |
| Mechanical UI, tokens, copy, screenshots, renames | **fast** | fastMode on / low effort | Cursor Composer 2.5; Claude Haiku; OpenCode Beam Free / Flash / Haiku |
| Feature slice with clear acceptance, tests | **mid** | medium effort | Cursor Auto / Grok Build-class; Claude Sonnet; OpenCode mid models |
| Protocol, authz, agent runtime, migrations, gnarly bugs | **strong** | medium–high | Claude Sonnet/Opus; Cursor Claude Opus; OpenCode strong coding models |
| Research / codebase grep / doc gather only | **fast** | lowest | Any cheap tool-using model; `role: research`, often `isolation: shared` |
| Review / PR critique | **mid–strong** | medium | Prefer a **different** provider than the author when cross-provider children exist |
| Coordinator (this skill) | **strong** | keep current session model | Do not downgrade yourself mid-dispatch |

If a tier is missing on all enabled providers, step **one** tier up — not straight
to max.

## Harness pick

When several providers can run children, choose by fit:

| Prefer | When |
| --- | --- |
| Same provider as parent | Least surprise; shared auth/MCP habits |
| Cross-provider child | Review diversity, or parent provider rate-limited |
| OpenCode cheap models | High-volume mechanical / research waves |
| Claude / Cursor strong | Agent protocol, Convex authz, ADR-quality writing |

Never assign a disabled provider. Never invent a model id absent from the catalog.

## Cost levers (use them)

1. **Sharper briefs > bigger models.** A mid model with file paths and acceptance
   beats Opus fishing in the monorepo.
2. **One research pass** shared by many implementers.
3. **Frontier-only dispatch** so blocked work does not burn tokens waiting.
4. **Folder ownership** from `AGENTS.md` so children do not fight and redo.
5. **Mock/default paths** for AI apps: children must not call paid LLMs in tests
   unless the task explicitly says so.
6. Cap parallel strong-tier children (e.g. ≤2–3); fill the rest with fast/mid.

## Anti-patterns

- Same strong model on every child “just in case”
- Research inside each implementer instead of shared notes
- `isolation: shared` for two editors on one package
- `mode: wait` on a fan-out (serializes the wave for no reason)
- Max/ultrathink effort on CSS padding
