# Setup: Obsidian, Local REST API and the MCP server (once per person, per machine)

The skill can work in two modes:

| Mode | Needs | What you get |
|---|---|---|
| **Disk** | Obsidian and a vault | Canvases written as files into the vault folder. Obsidian picks them up live. |
| **MCP** | The above + the Local REST API plugin + the Obsidian MCP server in your agent harness | Writes through Obsidian's API and can open the canvas in Obsidian. |

Previews (PNG) also need Chrome or Chromium. Without them the skill still builds and lints the canvases.

## One command: the doctor

```bash
python3 <skill>/scripts/doctor.py                  # checklist + numbered next steps (read-only)
python3 <skill>/scripts/doctor.py install-plugin   # download Local REST API into the open vault
python3 <skill>/scripts/doctor.py configure        # add the Obsidian MCP server to every detected harness
python3 <skill>/scripts/doctor.py configure cursor codex   # …or only to these
python3 <skill>/scripts/doctor.py fix-keys         # repair stale API keys in harness configs
```

The checklist covers:
- Obsidian installed;
- a vault, and which one is open;
- the plugin installed, enabled, answering, and accepting its own key;
- Node/npx (to run the MCP server);
- every harness on the machine: is the server configured, and does its key work;
- Chrome for previews.

It ends with `READY` (MCP), `READY disk mode` or `BLOCKED`, and the steps to take. Exit code: 0, 1 or 2.

Harnesses it knows:

| Harness | Config file |
|---|---|
| Claude Code | `~/.claude.json` |
| Claude Desktop | `claude_desktop_config.json` |
| Cursor | `~/.cursor/mcp.json` |
| Codex | `~/.codex/config.toml` (TOML) |
| OpenCode | `~/.config/opencode/opencode.json` |
| Gemini CLI | `~/.gemini/settings.json` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |

It also checks the project-level `.mcp.json`, `.cursor/mcp.json` and `.vscode/mcp.json`. Each harness has its
own format, and the doctor writes the right one.

Rules the doctor follows, and the agent too:

- **Never prints a key.** Never ask the user to paste one in the chat: the doctor reads it from the
  plugin's settings.
- **Backs up before changing a file** (`<file>.bak-obsidian`).
- `install-plugin`, `configure` and `fix-keys` change the user's vault or harness configs: the agent asks
  the user before running them.
- After `configure` or `fix-keys`, each harness must **restart or reconnect its MCP server** (Claude Code:
  `/mcp`; the others: restart the app or session). Clients read the config only at startup.

## Step by step (what the doctor automates)

1. **Obsidian.** Install it from https://obsidian.md/download (macOS: `brew install --cask obsidian`).
   Create or open a vault.
2. **Local REST API plugin.** In Obsidian: Settings → Community plugins → turn off Restricted mode →
   Browse → "Local REST API" → Install → Enable. Or run `doctor.py install-plugin`, then restart Obsidian.
   The plugin generates its API key on the first start.
   - Optional: in the plugin settings, enable the non-encrypted HTTP server (port 27123) to avoid the
     self-signed certificate.
3. **Node.js** (for `npx obsidian-mcp-server`): https://nodejs.org.
4. **MCP server in each harness:** `doctor.py configure`. The entry it writes, in the JSON harnesses:

   ```json
   "obsidian": {
     "command": "/absolute/path/to/npx",
     "args": ["-y", "obsidian-mcp-server"],
     "env": {
       "OBSIDIAN_API_KEY": "<from the plugin>",
       "OBSIDIAN_BASE_URL": "http://127.0.0.1:27123",
       "MCP_TRANSPORT_TYPE": "stdio"
     }
   }
   ```

   It uses an absolute `npx` path because desktop apps don't inherit the shell's `PATH`.

## The thing that breaks: the API key

- The key belongs to **each vault**: `<vault>/.obsidian/plugins/obsidian-local-rest-api/data.json`
  (`apiKey`).
- Each harness keeps its **own copy** in its MCP config. Nothing keeps the copies in sync.
- A copy goes stale when:
  - the key is regenerated in the plugin settings;
  - the plugin is reinstalled;
  - another vault becomes the open one;
  - someone copies an MCP config from a colleague.

  Everyone has a different key: never share configs with the key inside.
- **Symptom:** the MCP answers "rejected the API key" (401) while the plugin itself works.
  `doctor.py` shows which harness holds the stale key, and `fix-keys` repairs it.
- **Only the open vault answers.** The plugin listens on one port (HTTPS 27124, optional HTTP 27123), so
  the MCP talks to whichever vault Obsidian has open.
