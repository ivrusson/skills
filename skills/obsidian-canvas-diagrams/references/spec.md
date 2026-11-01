# Spec format for `canvas_build.py`

A spec is a JSON file. You place boxes on a grid; the builder works out pixels, row heights, group frames,
edge sides and the header. Three layouts: `grid` (structure, plans, flowcharts), `swimlane` (flows across
actors) and `sequence` (calls and replies between participants: APIs, services, protocols).

## Common keys

| Key | Meaning |
|---|---|
| `lang` | Language of the reader: `es`, `en`, `ca`, `pt`, `fr`, `it`, `de`. Sets the header words ("Leyenda", "Relacionado"). `labels: {"legend": …, "related": …}` overrides them. |
| `title` | Becomes `# title` in the header node. Name the diagram type and scope: "Acme Shop — containers (production)". |
| `description` | Markdown under the title: scope, source, date, how to read it. |
| `links` | List of wikilinks to sibling canvases or notes, shown as **Related:** in the header. `["[[Acme Shop — Checkout flow.canvas]]"]` |
| `legend` | `[{"color": "2", "label": "API server"}]`. Every color you use must appear here (the linter checks). |
| `colWidth` / `colGap` / `rowGap` | Pixels. Defaults: grid 360/160/120, swimlane 280/120/120. Widen `colGap` if edge labels are long. |
| `maxBoxes` | Linter threshold, default 20. |
| `noLegend` | `true` to silence the legend check (e.g. a single-color canvas). |
| `fitHeight` | `true`: each box keeps its own estimated height instead of stretching to its row. |

Colors: `"1"` red, `"2"` orange, `"3"` yellow, `"4"` green, `"5"` cyan, `"6"` purple (Obsidian presets,
follow the user's light or dark theme), or a hex string (fixed: it does not adapt).

## `grid` layout

```json
{
  "title": "Acme Shop — containers (production)",
  "description": "What runs where and who talks to whom. Source: docs/architecture.md.",
  "links": ["[[Acme Shop — Checkout flow.canvas]]", "[[Acme Shop — Plan Q3.canvas]]"],
  "legend": [{"color": "5", "label": "Web app"}, {"color": "2", "label": "API server"}, {"color": "4", "label": "Payments"}],
  "groups": [
    {"id": "web", "label": "apps/web — Next.js", "color": "5"},
    {"id": "api", "label": "services/api — Node :8080", "color": "2"}
  ],
  "nodes": [
    {"id": "pages", "group": "web", "col": 0, "row": 0, "text": "### Pages\nCatalog · Cart · Checkout · Account"},
    {"id": "client", "group": "web", "col": 0, "row": 1, "text": "### API client\n`useOrders` | `useCart`"},
    {"id": "routes", "group": "api", "col": 1, "row": 0, "rowspan": 2, "text": "### REST routes\n- `POST /orders`\n- `GET /products`"},
    {"id": "spec", "col": 2, "row": 0, "file": "Acme/Notes/Payments.md"}
  ],
  "edges": [
    {"from": "pages", "to": "client", "label": "hooks"},
    {"from": "client", "to": "routes", "label": "HTTPS · JSON"}
  ]
}
```

Node keys: `id`, `col`, `row`, optional `colspan`, `rowspan`, `group`, `color`, and one of `text`
(markdown), `file` (vault path, optional `subpath` like `#Heading`) or `url`. `width`/`height` override
the computed size; use them only when you must.

Edge keys: `from`, `to`, `label`, optional `color`, `fromSide`/`toSide` (`top|right|bottom|left`) to
override the automatic choice, `bidirectional: true` (discouraged), `noArrow: true` (plain line, e.g. for
"belongs to").

Rules the builder relies on:

- One box per cell. Use `colspan`/`rowspan` for big boxes.
- Keep each group's boxes in a contiguous rectangle of cells, otherwise frames overlap (the linter warns).
- Leave an empty column between groups when many edges cross between them, so labels have room.

## `swimlane` layout

Lanes are actors or systems (one row each, a full-width group). Steps run left to right in order; the
builder numbers them and chains them with arrows.

```json
{
  "layout": "swimlane",
  "title": "Acme Shop — Checkout (flow)",
  "description": "From 'Pay' to the confirmation page. Happy path.",
  "links": ["[[Acme Shop — Containers.canvas]]"],
  "legend": [{"color": "5", "label": "Web app"}, {"color": "2", "label": "API server"},
             {"color": "4", "label": "Payment provider"}, {"color": "1", "label": "Failure path"}],
  "lanes": [
    {"id": "web", "label": "Web app", "color": "5"},
    {"id": "api", "label": "API server", "color": "2"},
    {"id": "pay", "label": "Payment provider", "color": "4"}
  ],
  "steps": [
    {"id": "s1", "lane": "web", "text": "Customer clicks Pay"},
    {"id": "s2", "lane": "api", "text": "`orders.create` stores the order, status `pending`", "edgeLabel": "POST /orders"},
    {"id": "s3", "lane": "pay", "text": "Charge authorised", "edgeLabel": "create payment"},
    {"id": "s4", "lane": "pay", "text": "Sends the `payment.succeeded` webhook", "edgeLabel": "async"},
    {"id": "s5", "lane": "api", "text": "Webhook marks the order `paid`", "edgeLabel": "POST /webhooks"},
    {"id": "s6", "lane": "web", "text": "Confirmation page", "edgeLabel": "order status"},
    {"id": "f1", "lane": "api", "col": 2, "noChain": true, "color": "1", "text": "Card declined → order `failed`, retry offered"}
  ],
  "edges": [{"from": "s2", "to": "f1", "label": "charge fails", "color": "1"}]
}
```

Step keys: `id`, `lane`, `text`, optional `edgeLabel` (label of the arrow coming from the previous step),
`col` (force a column; later steps continue after it), `noChain` (a side branch such as a failure path or
a note: no automatic arrow, unnumbered, does not advance the sequence; place it with `col` under its
trigger and connect it with an explicit edge), `color`. Set `"number": false` to drop the step
numbers and `"chain": false` to draw only the edges you list.

## `sequence` layout

Participants are columns with a lifeline frame. Each message is a row with a horizontal, numbered arrow
from caller to receiver, top to bottom in time. Use it when the question is "who calls whom, and what comes
back": API calls, webhooks, auth handshakes, queue and worker hops.

```json
{
  "layout": "sequence",
  "lang": "es",
  "title": "Acme Shop — Pago (secuencia de API)",
  "description": "Quién llama a quién cuando el cliente paga. Camino feliz.",
  "legend": [{"color": "5", "label": "Web"}, {"color": "2", "label": "API"}, {"color": "4", "label": "Pasarela"},
             {"color": "1", "label": "Fallo"}],
  "participants": [
    {"id": "web", "color": "5", "text": "### Web\nNext.js · `useOrders`"},
    {"id": "api", "color": "2", "text": "### API\nNode · `orders.ts`"},
    {"id": "pay", "color": "4", "text": "### Pasarela de pago\nREST · webhooks"}
  ],
  "messages": [
    {"from": "web", "to": "api", "label": "POST /orders", "note": "Valida el carrito y guarda el pedido `pending`"},
    {"from": "api", "to": "pay", "label": "POST /payments · API key"},
    {"from": "pay", "to": "api", "label": "201 Created", "reply": true},
    {"from": "api", "to": "api", "label": "Si la pasarela no responde", "color": "1", "note": "Pedido `failed`; se ofrece reintentar"}
  ]
}
```

Participant keys: `id`, `text` (the header box; defaults to `### label`), `label`, `color`,
`lifelineLabel` (optional label on the frame).

Message keys: `from`, `to`, `label` (the call: method + path, mutation, event name, status code),
optional `note` (what the receiver does; turns its end into a box), `reply: true` (a response, drawn
with ↩), `color` (e.g. red for an error path), `id`. `from == to` is a self step (internal work, a
check, a branch taken): a box on that lifeline, no arrow.

- Put the caller of the first message leftmost, then participants in the order they are first called,
  so most arrows point right and replies point left.
- Write a `note` only where the receiver does something worth knowing (validates, stores, schedules).
  Plain hops stay as thin activation bars.
- Alternatives (`alt`), loops and optional steps: show the main path, then the branch as messages colored
  red or yellow whose label starts with the condition ("si 401", "cada 5 s"). A large alternative gets
  its own canvas.
- Up to ~15 messages per canvas; split at a natural pause (request accepted / streaming).
