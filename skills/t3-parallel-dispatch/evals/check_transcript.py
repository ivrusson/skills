#!/usr/bin/env python3 -I
"""Grade a run transcript (any text/JSONL dump) for the ask-gate behavior.

Usage: check_transcript.py <transcript-file>
Fails if the picker was never called as a tool, or if a markdown checkbox
list was printed. Format-agnostic: greps tool-call names and the text.
"""
import re, sys

text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
ask_call = re.search(r'"(?:name|tool_?[nN]ame)"\s*:\s*"(?:AskUserQuestion|AskQuestion|ask_user|muelle_ask)"', text)
checkbox = re.findall(r'^\s*(?:[-*]\s*)?(?:\[ \]|\[x\]|☐|☑)\s+\S+', text, re.M)

checks = {
    "ask tool actually called": bool(ask_call),
    "no markdown checkbox list": not checkbox,
}
for k, ok in checks.items():
    print(("PASS " if ok else "FAIL ") + k)
if checkbox:
    print("  e.g.:", checkbox[0].strip())
sys.exit(0 if all(checks.values()) else 1)
