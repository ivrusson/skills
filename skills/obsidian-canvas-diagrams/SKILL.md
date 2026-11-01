---
name: obsidian-canvas-diagrams
description: Draw architecture, flows, API call sequences and plans as Obsidian canvases (.canvas, JSON Canvas) in the user's vault, split into several linked canvases (overview, one per flow, API sequence, functional flowchart, plan board), using diagram readability rules (C4 checklist, Moody's Physics of Notations, crossing minimisation) and a builder + linter + PNG preview. Use whenever the user asks for an Obsidian canvas, a visual or drawn plan, an architecture diagram or map, a flow/sequence/swimlane drawing, a sequence diagram of API calls or service communication, a functional flowchart with decisions, "dibújalo", "hazme un esquema", "plan visual", or wants a plan or design "in Obsidian"; also to check or set up Obsidian, the Local REST API plugin, its API key or the Obsidian MCP in any agent harness — and when a plan is being written and the user has asked for visuals, even if they don't say "canvas".
---

# Obsidian canvas diagrams

Turn an architecture, a set of flows or a plan into **several small, linked canvases** in an Obsidian
vault, each one answering a single question, laid out so they read at a glance.

You don't compute pixels. You write a compact **spec** (boxes on a grid, steps in swimlanes, or messages
between participants). Then:

- `scripts/canvas_build.py` turns the spec into a `.canvas` and lints it: unlabeled arrows, arrows over
  boxes, crossings, missing legend, too many boxes.
- `scripts/canvas_render.py` renders a preview PNG and flags text that overflows its box.

Look at the PNG before you hand anything over: the first draft of a diagram is almost never the good one.

The skill works in any agent harness (Claude Code, Cursor, Codex, OpenCode, Gemini CLI…). It only needs
Python 3. `S` below is this skill's directory, wherever your harness installed it.

## Workflow

### 0. Check the setup (first use on a machine, or when writing fails)

```bash
python3 $S/scripts/doctor.py
```

It checks Obsidian, the vault, the Local REST API plugin and its key, Node, the Obsidian MCP server in
every harness on the machine, and Chrome for previews. It never prints a key. It ends with one of:

- `READY` (MCP): write through the MCP.
- `READY disk mode`: write files to disk, and mention the numbered steps once.
- `BLOCKED` (no Obsidian or no vault): walk the user through the steps it prints.

Its fixes change the user's vault or configs, so ask before running `install-plugin`, `configure` or
`fix-keys`. Never ask the user to paste an API key in the chat. Details and the manual route are in
`references/setup.md`. Skip this step when you already know the setup works.

### 1. Understand the content first

Gather the facts from the code, docs or plan in front of you. A diagram of something you haven't read
is decoration. Note the actors and boundaries, the main request paths, the scenarios worth showing, and
(for plans) phases, tasks and dependencies.

Then list the edges of the behaviour, the part a reader can't guess: **guards and validations, limits and
quotas, permissions, retries and timeouts, failure modes, and open decisions**. Each one goes on a canvas:
as a failure branch, a note under the step that triggers it, or a risk box in the plan. A diagram that only
shows the happy path looks finished and misleads.

### 2. Decide the canvas set

Split by question. Read `references/patterns.md` for the patterns:

| Canvas | Layout | Answers |
|---|---|---|
| Overview | `grid` | What are the parts, where do they run, who talks to whom? |
| One per flow | `swimlane` | What happens, in order, when X? (happy path; failures as branches) |
| API / communication sequence | `sequence` | Who calls whom, with which call, and what comes back? |
| Functional flowchart | `grid` | Which path does the logic take, and on which conditions? |
| Plan board | `grid` | In what order do we build it, and what depends on what? |
| Decision | `grid` | Which option, and why? |

Each canvas should have about 20 boxes at most, one abstraction level, and the same colors and names as
its siblings. With two or more canvases, also write a **hub note** (template in `patterns.md`) and put
`links` in every spec header, so the reader can move between them.

For a plan, the usual set is an overview with the changed parts highlighted, one flow per new or changed
behaviour, and the plan board.

### 3. Write the specs

The format is in `references/spec.md`. Write one JSON file per canvas in a scratch directory (not in the
vault).

- Order columns along the main path, left to right, so most arrows point the same way.
- Give every box a name line (`### Name`) plus 2–4 short lines that say **what happens, on which
  condition or why, and where** (`file.ts` → `function`). "Stores the message" is a label, not a box.
- Give every arrow a 1–5 word label that says what flows (the call, event or message).
- Define the legend first, then use only those colors.
- **Everything the reader sees is in the user's language** (the language of their request): titles,
  file names, the hub note, group and lane labels, the legend, box text and arrow labels. Set `"lang"`
  in the spec (e.g. `"es"`) so the header words follow. Identifiers stay as they are in the code.

The why behind these rules is in `references/diagram-rules.md`. Read it the first time you use this
skill in a session, or when a layout isn't working.

### 4. Build, lint, look, iterate

```bash
S=<this skill's directory>
python3 $S/scripts/canvas_build.py spec.json "Topic — View.canvas"
python3 $S/scripts/canvas_render.py "Topic — View.canvas" preview.html --png preview.png
```

**Light or dark.** The preview defaults to `--theme auto`, which matches what the user sees in Obsidian:
the vault's theme, or the OS appearance when Obsidian follows the system. The script prints which one it
used and why. If the user asks for light or dark ("en modo claro", "dark mode"), pass `--theme light` or
`--theme dark`, and keep that choice for the rest of the session's previews and exports.

The canvas itself needs no change for either theme, as long as you use the preset colors `"1"`–`"6"`:
Obsidian adapts those to its theme. Hex colors don't adapt, so avoid them unless the user asks.

- Fix every `ERROR`. Treat each `WARN` as a design question. "passes over node" and "cross" usually
  mean a box sits in the wrong column. A missing label means you don't know yet what the arrow means.
  Fix the spec, not the generated JSON.
- Fix every `OVERFLOW`: trim the text, give the box a `colspan`, or move detail into a linked note.
- Swimlane warnings about a single-step lane, an arrow jumping over a lane, or a mostly empty canvas
  mean the lanes are wrong: merge thin lanes, reorder lanes so neighbours talk to each other, put notes
  as `noChain` steps in the lane that triggers them, or switch a request/response flow to `sequence`.
- **Open the PNG and look at it.** Check that the eye lands on the title, then on the main path, that
  groups read as units, and that no label covers anything. Iterate until it reads well. Two or three
  rounds are normal.

### 5. Write to the vault

Find the destination. If the user named a folder, use it. Otherwise look for a folder named after the
project, or ask once.

**Preferred: the Obsidian MCP.** Its tools are named like `obsidian_write_note`. Some harnesses add a
prefix, such as `mcp__obsidian__obsidian_write_note`, so match on the suffix:

- `obsidian_list_notes` to find the folder.
- `obsidian_write_note` with `path: "Folder/Topic — View.canvas"`, the canvas JSON as `content`, and
  `overwrite: true` only after you have read the existing file and the user expects it to be replaced.
- `obsidian_open_in_ui` to open the main canvas.

**Fallback: write the file to disk.** Use it if the MCP is missing, rejects the API key, or refuses a
non-markdown file. Obsidian picks up new files immediately.

```bash
python3 $S/scripts/find_vault.py                 # vault paths from Obsidian's registry (* = open)
python3 $S/scripts/find_vault.py --folder Acme   # locate a folder inside the vaults
```

Copy the `.canvas` (and the hub `.md`) there. Don't overwrite an existing file without looking at it
first.

If the MCP rejects the API key (401), run `doctor.py`. It shows which harness config holds a stale key,
and `doctor.py fix-keys` repairs it (ask first). Then the user must reconnect the MCP server in that
harness. Meanwhile, write to disk.

### 6. Show and report

Show the user the PNG previews if your harness can display images. Then list:

- the files written, with their vault paths;
- what each canvas answers;
- any lint warning you consciously kept, and why.

Say that the preview approximates Obsidian's look and is not a screenshot of Obsidian.

## Editing an existing canvas

Keep the spec next to your scratch files and change the spec. Regenerating from the spec beats patching
coordinates by hand.

If the canvas was made by hand, or you've lost the spec, read the `.canvas`. Then either rebuild a spec
from it (the ids, text and edges carry over) or make small JSON edits and run `canvas_render.py` to check.
A hand-tuned layout the user cares about deserves small edits, not a rebuild.

## JSON Canvas essentials (when editing raw files)

- Top level: `{"nodes": [...], "edges": [...]}`. Node order is z-order, so groups come first.
- Node: `id`, `type` (`text|file|link|group`), integer `x`, `y`, `width`, `height`, optional `color`.
  - `text` has markdown, where wikilinks work.
  - `file` has a vault path and an optional `subpath` like `#Heading`.
  - `link` has a `url`.
  - `group` has a `label`.
- Edge: `id`, `fromNode`, `toNode`, optional `fromSide`/`toSide` (`top|right|bottom|left`),
  `fromEnd`/`toEnd` (`none|arrow`, defaults `none`/`arrow`), `label`, `color`.
- Colors: `"1"` red, `"2"` orange, `"3"` yellow, `"4"` green, `"5"` cyan, `"6"` purple, or a hex string (hex does not adapt to light/dark themes).
- Spec: https://jsoncanvas.org/spec/1.0/
