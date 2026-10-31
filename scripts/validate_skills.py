#!/usr/bin/env python3 -I
"""Check every skills/<name>/SKILL.md: frontmatter exists, `name` matches the
directory, and `description` is non-empty. Stdlib only."""
import re, sys
from pathlib import Path

errors = []
skills = sorted(Path("skills").glob("*/SKILL.md"))
if not skills:
    errors.append("no skills found under skills/*/SKILL.md")

for path in skills:
    folder = path.parent.name
    m = re.match(r"---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S)
    if not m:
        errors.append(f"{path}: missing frontmatter")
        continue
    front = m.group(1)
    name = re.search(r"^name:\s*(\S+)\s*$", front, re.M)
    desc = re.search(r"^description:[ \t]*(.*)$", front, re.M)
    if not name or name.group(1) != folder:
        errors.append(f"{path}: name must equal directory '{folder}'")
    if not desc:
        errors.append(f"{path}: missing description")
    else:
        rest = front[desc.end():].lstrip("\n")
        inline = desc.group(1).strip()
        folded = inline in (">", ">-", "|", "|-") and re.match(r"[ \t]+\S", rest)
        if not inline or (inline in (">", ">-", "|", "|-") and not folded):
            errors.append(f"{path}: empty description")

for e in errors:
    print("FAIL", e)
print(f"checked {len(skills)} skill(s)" + ("" if not errors else f", {len(errors)} error(s)"))
sys.exit(1 if errors else 0)
