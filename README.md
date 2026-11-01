# skills

Personal agent skills by [@ivrusson](https://github.com/ivrusson), usable from Claude Code, Cursor, Codex and OpenCode.

| Skill | What it does |
| --- | --- |
| [`t3-parallel-dispatch`](skills/t3-parallel-dispatch) | Finds what is pending (Linear / roadmap / git), asks you which tasks to run through the agent's native multi-select question tool, then launches parallel T3 Code children on worktrees and keeps run artifacts for debugging. |
| [`dokploy-deploy`](skills/dokploy-deploy) | Ships any app to a self-hosted Dokploy via git or zip-drop: isolates the product, picks HTTP vs HTTPS, matches Dockerfile/context/port, and verifies with curl. |
| [`obsidian-canvas-diagrams`](skills/obsidian-canvas-diagrams) | Draws architecture, flows, API sequences and plans as several linked Obsidian canvases, with a builder, a readability linter and PNG previews (light or dark, matching your Obsidian). A `doctor.py` checks and sets up Obsidian, the Local REST API plugin, its key and the Obsidian MCP in every agent harness. |
| [`skill-creator-multi`](skills/skill-creator-multi) | Fork of Anthropic's `skill-creator` that also installs every new skill for all agent providers. |

## Install

Uses the [skills CLI](https://skills.sh):

```bash
npx skills add ivrusson/skills -g -a claude-code -a cursor -a codex -a opencode
# or a single skill
npx skills add ivrusson/skills -g -s t3-parallel-dispatch
```

Update with `npx skills update`.

## License

MIT for original content (see `LICENSE`). `skills/skill-creator-multi` is derived from
[`anthropics/skills`](https://github.com/anthropics/skills) and stays under Apache-2.0
(see `skills/skill-creator-multi/LICENSE.txt`).
