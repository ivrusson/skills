# Canvas patterns

Pick the patterns that answer the questions the user has. A typical visual plan uses three or four of them,
linked by a hub note.

## Overview (structure): `grid`

Question: what are the parts, where do they run, who talks to whom?

- Groups = deployment or ownership boundaries (app, backend, external services). Columns follow the main
  request path from left to right: client → backend → workers → external.
- 8–16 boxes. Each box: name, technology, 1–3 lines of responsibility.
- Edges only for the main dependencies, labeled with what flows.
- For a change plan, the legend gains a change status: e.g. `"4"` green = new, `"3"` yellow = changed,
  `"1"` red = removed. Unchanged boxes stay uncolored, so the change jumps out.

## Flow (behaviour): `swimlane`

Question: what happens, in what order, when X?

- One canvas per scenario: happy path first. Put failure branches as `noChain` steps under their
  trigger, colored red, or give them their own canvas if there are several.
- Lanes = the actors from the overview, using the same colors and the same names. Only actors that do
  something: a lane with one step is a note in disguise; rules and notes go as `noChain` steps in the
  lane that triggers them, not in a lane of their own.
- Order lanes so that the lanes that hand work to each other are neighbours; an arrow should never jump
  over a lane.
- 5–12 steps. A step's text says what happens there; the arrow label says what crosses the boundary
  (call, event, message).
- If a flow needs more than ~12 steps, split it at a natural pause ("dispatch" / "streaming").

## API or communication sequence: `sequence`

Question: who calls whom, with which call, and what comes back?

- One canvas per interaction (send a message, log in, webhook received). Participants = the same systems
  as the overview, with the same names and colors.
- Arrow labels are the real interface: `POST /orders`, `orders.create`, `201`, `event: payment.succeeded`. The
  protocol or auth goes in the label when it matters (`· Bearer`, `· SSE`).
- Replies are explicit (`reply: true`). Async hand-offs (scheduler, queue) are a message to the
  scheduler or queue, not a hidden jump.
- Failure answers (401, timeout, 5xx) as red messages after the call that fails, labeled with the
  condition. More than two of them → a separate "errors" canvas.

## Functional flowchart (logic): `grid`

Question: which path does the logic take, and on which conditions?

- One main column, top to bottom: start → steps → decisions → end. Side columns to the right for the
  "no" or exception branches, which rejoin the main column or end.
- Decision box: `### ◆ ¿Condition?` plus what is checked and where (`file.ts`). Its outgoing arrows are
  labeled with the answer (`sí` / `no`, `válido` / `inválido`, `≤ cuota`). Every decision has at least two
  labeled exits.
- Start and end: one line each (`### ▶ Inicio: …`, `### ■ Fin: …`), colored in the legend.
- Steps say what is done and with which data. Keep to one function or use case per canvas (~15 boxes).

## Plan board (schedule): `grid`

Question: in what order do we build it, and what depends on what?

- Columns = phases or milestones (each a group: "Phase 1 — contracts"). Rows = workstreams, if any;
  otherwise stack tasks in the column.
- Task box: `### TASK-ID Short title`, then owner/folder, acceptance in one line, and a link to the issue.
- Edges = hard dependencies only ("needs"), always pointing forward in time. An arrow pointing backwards
  means the phases are wrong.
- Status colors in the legend (green done, yellow in progress, red blocked, none = to do).
- Keep risks and open questions in one red-bordered box per phase rather than scattering them.

## Decision or comparison: `grid`

Question: which option and why?

- One column per option, the same rows in each column (cost, risk, effort, fit), and a conclusion box
  spanning the bottom row (`colspan`). There are usually no edges.

## Hub note (markdown, not a canvas)

When you produce two or more canvases, also write a note that ties them together:

```markdown
# <Topic> — diagrams

<One paragraph: what this set covers, source of truth, date.>

| Canvas | Question it answers |
|---|---|
| [[<Topic> — Overview.canvas]] | What are the parts and how do they connect? |
| [[<Topic> — <Scenario> flow.canvas]] | What happens when …? |
| [[<Topic> — Plan.canvas]] | In what order do we build it? |

Color legend shared by all canvases: …
```

Name files `<Topic> — <View>.canvas` so they sort together in the vault.
