#!/usr/bin/env python3
"""Check and set up everything this skill needs: Obsidian, a vault, the Local REST API plugin, the API key
and the Obsidian MCP server in every agent harness installed on this machine. Never prints a key.

Usage:
  python3 doctor.py                          # checklist + what to do next (read-only)
  python3 doctor.py install-plugin [--vault PATH]
                                             # download Local REST API from its GitHub releases into the vault
  python3 doctor.py configure [HARNESS ...]  # add the Obsidian MCP server to these harnesses (default: all
                                             # detected ones that lack it), with the plugin's key
  python3 doctor.py fix-keys                 # copy the plugin's key into every harness config whose key fails

Harnesses: claude-code, claude-desktop, cursor, codex, opencode, gemini, windsurf.
Every change backs the file up first (<file>.bak-obsidian). Restart or reconnect the MCP server afterwards.
Exit code of the checklist: 0 MCP ready, 1 works by writing files to disk only, 2 blocked (no Obsidian/vault).
"""
import glob
import json
import os
import platform
import re
import shutil
import ssl
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from find_vault import vaults  # noqa: E402

PLUGIN_ID = "obsidian-local-rest-api"
PLUGIN_REPO = "coddingtonbear/obsidian-local-rest-api"
MCP_PACKAGE = "obsidian-mcp-server"
KEY_RE = re.compile(r"OBSIDIAN\w*KEY", re.I)
URL_RE = re.compile(r"OBSIDIAN\w*(URL|HOST)", re.I)
SYSTEM = platform.system()
APPDATA = os.environ.get("APPDATA", "")


def _desktop_config():
    if SYSTEM == "Darwin":
        return "~/Library/Application Support/Claude/claude_desktop_config.json"
    if SYSTEM == "Windows":
        return os.path.join(APPDATA, "Claude", "claude_desktop_config.json")
    return "~/.config/Claude/claude_desktop_config.json"


# name -> (config file, format, key holding the servers). The harness counts as installed if the file's
# directory exists.
HARNESSES = {
    "claude-code": ("~/.claude.json", "json", "mcpServers"),
    "claude-desktop": (_desktop_config(), "json", "mcpServers"),
    "cursor": ("~/.cursor/mcp.json", "json", "mcpServers"),
    "codex": ("~/.codex/config.toml", "toml", "mcp_servers"),
    "opencode": ("~/.config/opencode/opencode.json", "json", "mcp"),
    "gemini": ("~/.gemini/settings.json", "json", "mcpServers"),
    "windsurf": ("~/.codeium/windsurf/mcp_config.json", "json", "mcpServers"),
}
PROJECT_CONFIGS = ["./.mcp.json", "./.cursor/mcp.json", "./.vscode/mcp.json"]


def say(tag, msg):
    print(f"{tag:<6} {msg}")


# ---------------------------------------------------------------- Obsidian, vault, plugin

def obsidian_installed():
    candidates = {
        "Darwin": ["/Applications/Obsidian.app", "~/Applications/Obsidian.app"],
        "Windows": [os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Obsidian", "Obsidian.exe")],
    }.get(SYSTEM, ["/var/lib/flatpak/app/md.obsidian.Obsidian", "~/.local/share/flatpak/app/md.obsidian.Obsidian",
                   "/snap/bin/obsidian", "~/Applications/Obsidian.AppImage"])
    return any(os.path.exists(os.path.expanduser(c)) for c in candidates) or bool(shutil.which("obsidian"))


def plugin_state(vault):
    base = os.path.join(vault, ".obsidian")
    folder = os.path.join(base, "plugins", PLUGIN_ID)
    try:
        enabled = PLUGIN_ID in json.load(open(os.path.join(base, "community-plugins.json"), encoding="utf-8"))
    except (OSError, ValueError):
        enabled = False
    data = {}
    try:
        data = json.load(open(os.path.join(folder, "data.json"), encoding="utf-8"))
    except (OSError, ValueError):
        pass
    bases = [f"https://127.0.0.1:{data.get('port', 27124)}"]
    if data.get("enableInsecureServer"):
        bases.insert(0, f"http://127.0.0.1:{data.get('insecurePort', 27123)}")
    return {"installed": os.path.isfile(os.path.join(folder, "main.js")), "enabled": enabled,
            "key": data.get("apiKey"), "bases": bases}


def probe(base, key=None):
    """(reachable, authenticated) for the plugin at base."""
    req = urllib.request.Request(base.rstrip("/") + "/", headers={"Authorization": f"Bearer {key}"} if key else {})
    try:
        with urllib.request.urlopen(req, timeout=3, context=ssl._create_unverified_context()) as r:
            return True, bool(json.load(r).get("authenticated"))
    except Exception:
        return False, False


def open_vault():
    vs = vaults()
    return next((p for p, is_open in vs if is_open), vs[0][0] if vs else None), vs


def live_plugin(vault):
    """Plugin state plus the first base URL where its own key works, or None."""
    st = plugin_state(vault)
    st["live"] = next((b for b in st["bases"] if st["key"] and probe(b, st["key"])[1]), None)
    st["listening"] = any(probe(b)[0] for b in st["bases"])
    return st


# ---------------------------------------------------------------- harness configs

def _load_json(f):
    try:
        return json.loads(re.sub(r"^\s*//.*$", "", open(f, encoding="utf-8").read(), flags=re.M))
    except (OSError, ValueError):
        return None


def _find_entries(obj, path=()):
    if isinstance(obj, dict):
        if any(KEY_RE.fullmatch(str(k)) for k in obj):
            yield path, obj
        for k, v in obj.items():
            yield from _find_entries(v, path + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _find_entries(v, path + (i,))


def configured_keys(f):
    """Yield (location, key, base_url, setter) for each OBSIDIAN_*KEY in a config file."""
    if f.endswith(".toml"):
        text = open(f, encoding="utf-8").read()
        url = re.search(r'OBSIDIAN\w*(?:URL|HOST)\s*=\s*"([^"]*)"', text, re.I)
        for m in re.finditer(r'^(\s*(\w*OBSIDIAN\w*KEY)\s*=\s*")([^"]*)(")', text, re.M | re.I):
            def set_toml(new, old=m.group(0), pre=m.group(1), post=m.group(4)):
                t = open(f, encoding="utf-8").read()
                open(f, "w", encoding="utf-8").write(t.replace(old, pre + new + post, 1))
            yield m.group(2), m.group(3), url.group(1) if url else None, set_toml
        return
    data = _load_json(f)
    for loc, env in _find_entries(data) if data is not None else []:
        k = next(k for k in env if KEY_RE.fullmatch(str(k)))
        url = next((v for kk, v in env.items() if URL_RE.fullmatch(str(kk))), None)

        def set_json(new, loc=loc, k=k):
            d = _load_json(f)
            node = d
            for part in loc:
                node = node[part]
            node[k] = new
            json.dump(d, open(f, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
        yield "/".join(map(str, loc)) + "/" + k, env[k], url, set_json


def harness_status():
    """name -> {"file", "installed", "entries": [(loc, key, url, setter)]}"""
    out = {}
    for name, (path, _, _) in HARNESSES.items():
        f = os.path.expanduser(path)
        installed = os.path.isdir(os.path.dirname(f)) and (os.path.exists(f) or name not in ("claude-code",))
        entries = list(configured_keys(f)) if os.path.isfile(f) else []
        out[name] = {"file": f, "installed": installed, "entries": entries}
    return out


def server_env(plugin):
    base = plugin["live"] or plugin["bases"][0]
    env = {"OBSIDIAN_API_KEY": plugin["key"], "OBSIDIAN_BASE_URL": base, "MCP_TRANSPORT_TYPE": "stdio"}
    if base.startswith("https"):
        env["OBSIDIAN_VERIFY_SSL"] = "false"  # the plugin uses a self-signed certificate
    return env


def add_server(name, plugin):
    path, fmt, servers_key = HARNESSES[name]
    f = os.path.expanduser(path)
    npx = shutil.which("npx") or "npx"  # absolute path: GUI apps don't inherit the shell PATH
    env = server_env(plugin)
    os.makedirs(os.path.dirname(f), exist_ok=True)
    if os.path.exists(f):
        shutil.copy(f, f + ".bak-obsidian")
    if fmt == "toml":
        lines = [f"\n[{servers_key}.obsidian]", f'command = "{npx}"', f'args = ["-y", "{MCP_PACKAGE}"]',
                 f"\n[{servers_key}.obsidian.env]"] + [f'{k} = "{v}"' for k, v in env.items()]
        with open(f, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        return f
    data = _load_json(f) if os.path.exists(f) else {}
    if data is None:
        raise SystemExit(f"cannot parse {f}; add the server by hand (references/setup.md)")
    if name == "opencode":
        entry = {"type": "local", "command": [npx, "-y", MCP_PACKAGE], "environment": env, "enabled": True}
    else:
        entry = {"command": npx, "args": ["-y", MCP_PACKAGE], "env": env}
        if name == "claude-code":
            entry = {"type": "stdio", **entry}
    data.setdefault(servers_key, {})["obsidian"] = entry
    json.dump(data, open(f, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    return f


# ---------------------------------------------------------------- commands

def checklist():
    nxt = []
    level = 0  # 0 MCP ready, 1 disk only, 2 blocked

    if obsidian_installed():
        say("OK", "Obsidian is installed")
    else:
        say("FAIL", "Obsidian is not installed")
        nxt.append("Install Obsidian: https://obsidian.md/download"
                   + (" (or: brew install --cask obsidian)" if SYSTEM == "Darwin" and shutil.which("brew") else ""))
    vault, all_vaults = open_vault()
    if not vault:
        say("FAIL", "no vault registered in Obsidian")
        nxt.append("Open Obsidian and create or open a vault (any folder works).")
        level = 2
        return finish(level, nxt)
    say("OK", f"{len(all_vaults)} vault(s); using {'open' if dict(all_vaults).get(vault) else 'closed'} vault: {vault}")

    st = live_plugin(vault)
    if not st["installed"]:
        say("FAIL", "Local REST API plugin is not installed in this vault")
        nxt.append("Ask the user, then: python3 doctor.py install-plugin   (or Obsidian → Settings → Community "
                   "plugins → Browse → 'Local REST API' → Install → Enable)")
    elif not st["enabled"]:
        say("FAIL", "Local REST API plugin is installed but not enabled")
        nxt.append("Obsidian → Settings → Community plugins: turn off Restricted mode if asked, enable 'Local REST API'.")
    elif not st["listening"]:
        say("FAIL", "the plugin is enabled but not answering (is Obsidian open on this vault?)")
        nxt.append("Open Obsidian on this vault; the plugin only runs while the vault is open.")
    elif not st["live"]:
        say("FAIL", "the plugin answers but rejects its own stored key (key regenerated since Obsidian started?)")
        nxt.append("Restart Obsidian, then rerun the doctor.")
    else:
        say("OK", f"Local REST API answers at {st['live']} and its key works")

    if shutil.which("npx"):
        say("OK", "Node.js/npx found (runs the Obsidian MCP server)")
    else:
        say("FAIL", "npx not found: the Obsidian MCP server needs Node.js")
        nxt.append("Install Node.js LTS: https://nodejs.org")

    ready = 0
    for name, h in harness_status().items():
        if not h["installed"]:
            continue
        if not h["entries"]:
            say("TODO", f"{name}: no Obsidian MCP server in {h['file']}")
            if st["live"]:
                nxt.append(f"Ask the user, then: python3 doctor.py configure {name}")
            continue
        for loc, key, url, _ in h["entries"]:
            reachable, works = probe(url or (st["live"] or st["bases"][0]), key)
            if works:
                ready += 1
                say("OK", f"{name}: MCP key works ({h['file']})")
            else:
                say("FAIL", f"{name}: MCP key {'rejected' if reachable else 'untested (plugin not reachable)'} "
                            f"({h['file']} [{loc}])")
                if reachable:
                    nxt.append("Ask the user, then: python3 doctor.py fix-keys")
    for f in PROJECT_CONFIGS:
        if os.path.isfile(f):
            for loc, key, url, _ in configured_keys(f):
                ok = probe(url or (st["live"] or st["bases"][0]), key)[1]
                say("OK" if ok else "FAIL", f"project config {f}: MCP key {'works' if ok else 'fails'}")

    try:
        from canvas_render import find_chrome
        say("OK" if find_chrome() else "WARN", "Chrome/Chromium for PNG previews" + ("" if find_chrome() else
            " not found: previews are skipped (install Chrome or Chromium)"))
    except Exception:
        pass

    if not obsidian_installed() and not all_vaults:
        level = 2
    elif not (st["live"] and ready):
        level = 1
    return finish(level, sorted(set(nxt), key=nxt.index))


def finish(level, nxt):
    mode = ["READY  writes through the Obsidian MCP (and can fall back to disk)",
            "READY  disk mode: canvases are written as files into the vault; the MCP path is not set up",
            "BLOCKED  no Obsidian vault to write to"][level]
    print("\n" + mode)
    if nxt:
        print("NEXT:")
        for i, n in enumerate(dict.fromkeys(nxt), 1):
            print(f"  {i}. {n}")
        print("Then restart or reconnect the MCP server in each harness (Claude Code: /mcp) and rerun the doctor.")
    sys.exit(level)


def install_plugin(vault):
    plugins = os.path.join(vault, ".obsidian", "plugins", PLUGIN_ID)
    req = urllib.request.Request(f"https://api.github.com/repos/{PLUGIN_REPO}/releases/latest",
                                 headers={"Accept": "application/vnd.github+json"})
    release = json.load(urllib.request.urlopen(req, timeout=20))
    assets = {a["name"]: a["browser_download_url"] for a in release.get("assets", [])}
    if "main.js" not in assets or "manifest.json" not in assets:
        raise SystemExit("the latest release has no main.js/manifest.json; install from Obsidian instead")
    os.makedirs(plugins, exist_ok=True)
    for name in ("main.js", "manifest.json", "styles.css"):
        if name in assets:
            with urllib.request.urlopen(assets[name], timeout=60) as r, open(os.path.join(plugins, name), "wb") as fh:
                fh.write(r.read())
    cp = os.path.join(vault, ".obsidian", "community-plugins.json")
    enabled = json.load(open(cp, encoding="utf-8")) if os.path.exists(cp) else []
    if PLUGIN_ID not in enabled:
        if os.path.exists(cp):
            shutil.copy(cp, cp + ".bak-obsidian")
        json.dump(enabled + [PLUGIN_ID], open(cp, "w", encoding="utf-8"), indent=2)
    say("DONE", f"Local REST API {release.get('tag_name', '')} installed and enabled in {vault}")
    print("Now restart Obsidian (it generates the API key on first start). If Obsidian asks, turn off Restricted "
          "mode in Settings → Community plugins. Then: python3 doctor.py configure")


def configure(names):
    vault, _ = open_vault()
    st = live_plugin(vault) if vault else None
    if not st or not st["live"]:
        raise SystemExit("the Local REST API plugin is not answering with its key; run the checklist first")
    status = harness_status()
    targets = names or [n for n, h in status.items() if h["installed"] and not h["entries"]]
    if not targets:
        print("nothing to configure: every detected harness already has an Obsidian MCP entry (try fix-keys)")
    for n in targets:
        if n not in HARNESSES:
            raise SystemExit(f"unknown harness '{n}'; known: {', '.join(HARNESSES)}")
        if status[n]["entries"]:
            say("SKIP", f"{n} already has an Obsidian MCP entry; use fix-keys if its key fails")
            continue
        f = add_server(n, st)
        say("DONE", f"{n}: Obsidian MCP server added to {f} (backup: .bak-obsidian if the file existed)")
    print("Restart or reconnect the MCP server in those harnesses (Claude Code: /mcp).")


def fix_keys():
    vault, _ = open_vault()
    st = live_plugin(vault) if vault else None
    if not st or not st["live"]:
        raise SystemExit("the Local REST API plugin is not answering with its key; run the checklist first")
    files = [h["file"] for h in harness_status().values() if h["entries"]]
    files += [f for f in PROJECT_CONFIGS if os.path.isfile(f)]
    fixed = 0
    for f in files:
        for loc, key, url, setter in configured_keys(f):
            if probe(url or st["live"], key)[1]:
                continue
            shutil.copy(f, f + ".bak-obsidian")
            setter(st["key"])
            fixed += 1
            say("FIXED", f"{f} [{loc}] now holds the plugin's key (backup: {f}.bak-obsidian)")
    print("all keys already work" if not fixed else "Restart or reconnect the MCP server in those harnesses.")


def main():
    args = sys.argv[1:]
    cmd = args[0] if args and not args[0].startswith("-") else "check"
    if cmd == "check":
        checklist()
    elif cmd == "install-plugin":
        vault = args[args.index("--vault") + 1] if "--vault" in args else open_vault()[0]
        if not vault:
            raise SystemExit("no vault found; open or create one in Obsidian first")
        install_plugin(vault)
    elif cmd == "configure":
        configure([a for a in args[1:] if not a.startswith("-")])
    elif cmd == "fix-keys":
        fix_keys()
    else:
        print(__doc__)
        sys.exit(2)


if __name__ == "__main__":
    main()
