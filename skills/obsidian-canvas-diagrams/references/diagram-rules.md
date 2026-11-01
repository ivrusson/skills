# Diagram rules: looks and ergonomics

Distilled from four sources that agree with each other more than they differ:

- **C4 model review checklist** (Simon Brown, https://c4model.com/diagrams/checklist): every diagram can be
  read without its author.
- **Physics of Notations** (D. Moody, IEEE TSE 35(6), 2009): nine principles for cognitively effective
  visual notations.
- **Graph-drawing aesthetics studies** (H. Purchase et al., 1996–2012): which layout properties really
  change how fast and how well people read a graph.
- **Gestalt grouping** (proximity, similarity, enclosure, connectedness): what the eye groups before it
  reads anything.

Use the checklist at the end before handing a canvas over.

## 1. One canvas, one question

A diagram answers one question for one audience: "what runs where?", "what happens when a message is
sent?", "in what order do we build this?". Mixing structure, behaviour and schedule on one canvas is the
most common reason a diagram stops being readable.

- **Manageable complexity (Moody):** past ~15–20 boxes, split the canvas. Link the pieces by hand: a
  "Related" line in each header, plus a hub note.
- **One abstraction level per canvas (C4):** don't put a database table next to "Mobile app". Zoom levels
  belong on separate canvases: context → containers → components → code or flow.
- **Cognitive integration (Moody):** when you split, make navigation explicit. Each canvas links to its
  parent and siblings, and the overview links down to each detail canvas.

## 2. Say what everything is

From the C4 checklist, adapted to canvases:

- The **title** names the diagram type and its scope: "Acme Shop — checkout (sequence, happy path)".
- Every **box** has a name on its first line (heading or bold), then its type or technology, then one or
  two lines on what it does. No box that is only a name.
- Every **arrow has a label** saying what flows or why ("POST /turn", "writes deltas", "schedules"). Avoid
  "uses" and "talks to", which say nothing. Put the protocol in the label when it matters.
- The **label reads in the arrow's direction**: an arrow from A to B labeled "calls" means A calls B.
- **Acronyms** are spelled out once, or are well known to the audience.
- A **legend** explains every color, every line style and any size difference you rely on. If a color
  means nothing, don't use it.

## 3. Encode meaning on purpose

- **Semiotic clarity (Moody):** one visual variable per concept. If orange means "API server", orange means
  only the API server on this canvas and on its siblings. Reuse the same color mapping across a set of canvases.
- **Perceptual discriminability:** categories must be told apart at a glance. Use at most ~5 colors, and
  never color as the only cue: pair it with a group label or a word ("⚠️ failure", "NEW").
- **Graphic economy:** few symbol types. Canvas gives you boxes, groups, arrows and colors; that's enough.
- **Dual coding:** text plus visuals beat either alone. Emoji or a short tag in group labels (📱, 🗄️,
  🤖) helps you scan quickly. Don't use them as decoration on every box.
- **Semantic transparency:** use conventions the reader already knows. Red is failure or risk. Green is
  done or healthy. Dashed or grey means planned. Containment means "is part of". Left-to-right means
  "then".
- For plans, **status colors** are a natural legend: green done, yellow in progress, grey/none to do, red
  blocked, purple/cyan new vs changed.

## 4. Layout

Purchase's experiments rank the aesthetics:

1. **Edge crossings matter most.** Minimise them, and above all keep the path the reader must follow free
   of crossings. Reorder columns before anything else; the builder reports crossings.
2. **Fewer bends, shorter edges.** Put tightly coupled boxes next to each other. A long arrow across the
   canvas is a sign the boxes are in the wrong place.
3. **Grid alignment helps.** Align boxes on a grid, with equal widths in a column and equal heights in a
   row. That's why the builder works in cells.
4. **One dominant direction.** Flows read left to right (or top to bottom) and keep that direction; arrows
   going back against the flow should be the exception (a reply, a retry) and visibly so.

Gestalt on top of that:

- **Enclosure:** a group frame is the strongest grouping cue. Use groups for deployment or ownership
  boundaries (app, backend, agent server; or a phase in a plan). Don't nest more than one level.
- **Proximity:** related boxes sit close together; unrelated clusters get clear space between them. Leave
  more gap between groups than inside them.
- **Similarity:** boxes of the same kind look the same (size, color).
- **Connectedness:** an arrow beats proximity. Don't draw arrows you don't mean.

Canvas specifics:

- Obsidian centres the edge label on the curve, and you cannot move it. Keep labels short (≤ 4–5 words)
  and edges reasonably long, or the label covers the arrow.
- Arrows into or out of a group frame are allowed, but an arrow between two specific boxes is clearer.
- Avoid double-headed arrows (C4): readers can't tell request from response. Use two labeled arrows, or
  one arrow from the initiator.
- Text nodes scroll when they overflow, which hides content. Size boxes to their text (the builder
  estimates, the renderer checks).

## 5. Readability of the text in boxes

- Lead with the name, then 2–6 short lines. A box that needs a page is a note: link to it with a `file`
  node instead.
- Use `code` for identifiers, **bold** for the one thing to remember, and lists rather than prose.
- Say what happens, on which condition or why, and where in the code: "Saves the order and schedules
  `payments.capture` (`orders.ts`)" beats "Save".
- Everything the reader sees is in the user's language: titles, file names, labels, legend. Identifiers
  stay as they are in the code.

## Checklist before handing over

- [ ] Title states type and scope; the header says how to read the canvas and links to siblings.
- [ ] ≤ ~20 boxes, one abstraction level, one question.
- [ ] Every box has a name and says what it is or does.
- [ ] Every arrow has a short label that reads in its direction; no double-headed arrows.
- [ ] Every color and line style is in the legend; meaning doesn't rely on color alone.
- [ ] No arrow passes over a box; crossings minimised (builder report).
- [ ] No text overflow (renderer report), and you looked at the PNG.
- [ ] Guards, limits, failures and open decisions are on a canvas, not only the happy path.
- [ ] Titles, file names and labels are in the user's language.
