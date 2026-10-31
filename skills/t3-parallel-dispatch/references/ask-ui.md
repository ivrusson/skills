# Ask tool for the task picker

The human picks tasks with the harness's **native question tool**, not a list
in the chat bubble. Markdown `- [ ]` lists are never an acceptable substitute:
they render as plain text and cannot be ticked.

## Why this exists

Past runs wrote good analysis and then printed a `- [ ]` list. Causes worth
remembering:

- The skill said “checkboxes”, so the model produced checkbox markdown instead
  of calling a tool.
- `AskUserQuestion` allows only 2–4 options per question; with 6 candidates the
  model gave up on the tool and fell back to markdown.
- The tool was deferred / not in the visible list and was assumed absent.

## Which tool, per provider

| Provider | Tool | Multi-select | Limits to design around |
| --- | --- | --- | --- |
| Claude Code / Claude Agent | `AskUserQuestion` | `multiSelect: true` | 1–4 questions, 2–4 options each, `header` ≤ 12 chars, “Other” added automatically |
| Cursor | `AskQuestion` (static tool, call by name) | `allow_multiple: true` | ≤ ~12 options is fine |
| Any (MCP) | `ask_user` | per its schema | read the live schema first |
| Fallback | `muelle_ask` presets (single choice) | no | see below |

Codex / OpenCode / others: look in your own tool list for a question/ask tool
and read its schema before calling. Do not guess field names.

## Discovery (every run, before the picker)

1. Look at **your own tool list** for the names above.
2. Not there? It may be **deferred**: load it (Claude Code:
   `ToolSearch` with `select:AskUserQuestion`; Cursor:
   `GetDynamicTools` with `pattern: "AskQuestion|AskUserQuestion|ask_user"`).
3. If a name is listed anywhere, **call it once** before concluding it is
   absent. T3 tools may load late.
4. Cursor's `AskQuestion` is a **static** tool. Do not call it through
   `CallDynamicTool({ namespace:"cursor", … })`.

Record in `selection.json` → `askTool`: the tool name used, or
`"numbered_list"` / `"muelle_presets"` with `askToolMissing: [...]`.

## Shapes

### Claude `AskUserQuestion`

Budget the 4 question slots: tasks (1–2) + wave policy + merge policy.
Put `blockedBy` / `folderHint` / `whyNow` in each option's `description`;
recommended option first with “(Recommended)” in the label.

```json
{
  "questions": [
    {
      "header": "Tareas",
      "question": "¿Qué tareas lanzo en esta ola?",
      "multiSelect": true,
      "options": [
        { "label": "ACME-38 ADR créditos (Recommended)", "description": "agent/ · sin bloqueos · decide el contrato que usan ACME-39/41" },
        { "label": "ACME-17 Wordmark SVG (Recommended)", "description": "apps/web/ · sin bloqueos · tier rápido" },
        { "label": "ACME-40 OpenRouter runtime", "description": "agent/ · choca con ACME-38 en agent/ → serializar" }
      ]
    },
    {
      "header": "Ola",
      "question": "Política de ola",
      "multiSelect": false,
      "options": [
        { "label": "Solo frontier (Recommended)", "description": "Lanza solo lo desbloqueado" },
        { "label": "Frontier + cola blocked", "description": "Deja las bloqueadas en cola hasta que se desbloqueen" }
      ]
    },
    {
      "header": "Merge",
      "question": "Política de merge",
      "multiSelect": false,
      "options": [
        { "label": "Un PR por hijo (Recommended)", "description": "Cada hijo abre su PR" },
        { "label": "Solo ramas", "description": "Integras tú después" }
      ]
    }
  ]
}
```

More than 4 candidates:

- Split the frontier across two `multiSelect` questions (by milestone or by
  folder owner), leaving 2 slots for the policies; or
- Make options presets — “Recomendado: ACME-38 + ACME-17”, “Todo el frontier”,
  “Solo investigación” — and let “Other” take explicit ids.

### Cursor `AskQuestion`

```json
{
  "title": "Acme v0.2.0 — qué lanzo",
  "questions": [
    {
      "id": "tasks",
      "prompt": "Selecciona tareas para esta ola (recomendadas marcadas en el label).",
      "allow_multiple": true,
      "options": [
        { "id": "ACME-38", "label": "ACME-38 — ADR OpenRouter/créditos (recomendado)" },
        { "id": "ACME-17", "label": "ACME-17 — Wordmark SVG (recomendado)" },
        { "id": "ACME-39", "label": "ACME-39 — (blocked by ACME-38) Convex plans" }
      ]
    },
    {
      "id": "wave_policy",
      "prompt": "Política de ola",
      "allow_multiple": false,
      "options": [
        { "id": "frontier_only", "label": "Solo frontier (default)" },
        { "id": "include_blocked_queue", "label": "Incluir blocked (solo cola)" }
      ]
    },
    {
      "id": "merge_policy",
      "prompt": "Política de merge",
      "allow_multiple": false,
      "options": [
        { "id": "one_pr_per_child", "label": "Un PR por hijo (default)" },
        { "id": "branches_only", "label": "Solo ramas; integrar luego" }
      ]
    }
  ]
}
```

- One option `id` per task id.
- Blocked tasks: omit, or include with `(blocked by X)` only if you will not
  dispatch them until unblocked.

### MCP `ask_user` (e.g. xlens)

Use when that namespace is the product surface for the thread. Map answers back
to task ids in `selection.json`.

## When no multi-select ask tool exists

1. **`muelle_ask` presets** (single choice): `recommended`, `all_frontier`,
   `custom` (human replies with ids in chat), plus an epic-slice preset if
   useful. Policies in a follow-up ask.
2. **Numbered list in chat** — only if (1) is also unavailable or the human
   chose `custom`. Say which tool names you tried, ask them to reply with the
   numbers/ids, and stop. Use `1.` `2.` — not `- [ ]`.

Never present a list as if it were the ask UI. Never skip asking and invent a
selection.

## After answers

Echo one line: `Selected: ACME-38 ACME-17 · wave=frontier_only · merge=one_pr_per_child`.
Write `selection.json`. Then research/briefs — not before.
