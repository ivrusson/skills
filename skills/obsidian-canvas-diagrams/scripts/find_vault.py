#!/usr/bin/env python3
"""List Obsidian vaults from Obsidian's own registry, optionally locating a folder inside them.

Usage:
  python3 find_vault.py                 # all vaults (the open one is marked)
  python3 find_vault.py --folder Acme   # folders named like 'Acme' (case-insensitive) in every vault

Only needed when writing .canvas files straight to disk (the REST API MCP is down or refuses the file).
"""
import json
import os
import sys

REGISTRIES = [
    "~/Library/Application Support/obsidian/obsidian.json",  # macOS
    "~/.config/obsidian/obsidian.json",  # Linux
    "~/.var/app/md.obsidian.Obsidian/config/obsidian/obsidian.json",  # Linux flatpak
    os.path.join(os.environ.get("APPDATA", ""), "obsidian", "obsidian.json"),  # Windows
]


def vaults():
    for reg in REGISTRIES:
        path = os.path.expanduser(reg)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return [(v["path"], bool(v.get("open"))) for v in data.get("vaults", {}).values()]
    return []


def main():
    found = vaults()
    if not found:
        print("No Obsidian registry found. Search manually: find ~ -maxdepth 6 -type d -name .obsidian")
        sys.exit(1)
    if "--folder" in sys.argv:
        name = sys.argv[sys.argv.index("--folder") + 1].lower()
        for root, _ in found:
            for dirpath, dirnames, _ in os.walk(root):
                dirnames[:] = [d for d in dirnames if not d.startswith(".")]
                if os.path.basename(dirpath).lower() == name:
                    print(f"{dirpath}\t(vault: {root})")
        return
    for root, is_open in found:
        print(("* " if is_open else "  ") + root)


if __name__ == "__main__":
    main()
