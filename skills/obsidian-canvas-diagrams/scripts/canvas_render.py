#!/usr/bin/env python3
"""Render a .canvas to a standalone HTML page (and a PNG via headless Chrome) to *look* at it before
handing it over, and report text nodes whose content overflows their box.

Usage:
  python3 canvas_render.py in.canvas out.html [--png out.png] [--theme auto|light|dark]

--theme auto (default) matches what the user sees: the vault's Obsidian theme (.obsidian/appearance.json;
"moonstone" = light, "obsidian" = dark), and when Obsidian follows the system, the OS appearance.
Use light/dark when the user asks for one. --light is kept as an alias of --theme light.

The look approximates Obsidian's canvas (preset colors, groups, bezier edges, labels). It is a preview,
not a pixel-exact copy. Overflow detection needs Chrome/Chromium/Brave/Edge; without one, only HTML is written.
"""
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

COL = {"1": "#e5484d", "2": "#f76b15", "3": "#e2b203", "4": "#30a46c", "5": "#0ea5b7", "6": "#8e4ec6"}
NEUTRAL = "#8b8d98"


def color(c):
    if not c:
        return None
    return COL.get(c, c if c.startswith("#") else None)


def inline(s):
    s = html.escape(s, quote=False)
    codes = []
    s = re.sub(r"`([^`]+)`", lambda m: codes.append(m[1]) or f"\x00{len(codes) - 1}\x00", s)
    s = re.sub(r"\[\[([^\]|]+)\|([^\]]+)\]\]", r'<a class="wl">\2</a>', s)
    s = re.sub(r"\[\[([^\]]+)\]\]", lambda m: f'<a class="wl">{re.sub(r"[.]canvas$|[.]md$", "", m[1])}</a>', s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a class="wl">\1</a>', s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*([^*]+)\*(?!\w)", r"<i>\1</i>", s)
    s = re.sub(r"==(.+?)==", r"<mark>\1</mark>", s)
    return re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{codes[int(m[1])]}</code>", s)


def md(text):
    out, lines, i = [], text.split("\n"), 0
    while i < len(lines):
        line = lines[i].rstrip()
        s = line.strip()
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [x.strip() for x in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-+:?", x) for x in cells):
                    rows.append(cells)
                i += 1
            body = "".join(
                "<tr>" + "".join(f"<{'th' if r == 0 else 'td'}>{inline(x)}</{'th' if r == 0 else 'td'}>" for x in row) + "</tr>"
                for r, row in enumerate(rows))
            out.append(f"<table>{body}</table>")
            continue
        if s.startswith("```"):
            i += 1
            block = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                block.append(html.escape(lines[i]))
                i += 1
            out.append("<pre>" + "\n".join(block) + "</pre>")
            i += 1
            continue
        m = re.match(r"(#{1,6}) (.*)", s)
        if m:
            out.append(f"<h{len(m[1])}>{inline(m[2])}</h{len(m[1])}>")
        elif re.match(r"(- |\* |\d+\. |- \[[ x]\] )", s):
            tag = "ol" if re.match(r"\d+\. ", s) else "ul"
            items = []
            while i < len(lines) and re.match(r"\s*(- |\* |\d+\. )", lines[i]):
                item = re.sub(r"^\s*(- |\* |\d+\. )", "", lines[i])
                item = item.replace("[ ] ", "☐ ").replace("[x] ", "☑ ")
                items.append(item)
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
            continue
        elif s.startswith("> "):
            out.append(f"<blockquote>{inline(s[2:])}</blockquote>")
        elif s in ("---", "***"):
            out.append("<hr>")
        elif s:
            out.append(f"<p>{inline(s)}</p>")
        i += 1
    return "\n".join(out)


def render(canvas, light=False):
    ns = canvas.get("nodes", [])
    if not ns:
        raise SystemExit("canvas has no nodes")
    pad = 80
    minx = min(n["x"] for n in ns) - pad
    miny = min(n["y"] for n in ns) - pad
    W = max(n["x"] + n["width"] for n in ns) - minx + pad
    H = max(n["y"] + n["height"] for n in ns) - miny + pad
    by_id = {n["id"]: n for n in ns}
    parts = []
    for n in ns:  # file order = z-order
        c = color(n.get("color")) or NEUTRAL
        style = f"left:{n['x'] - minx}px;top:{n['y'] - miny}px;width:{n['width']}px;height:{n['height']}px;--c:{c}"
        nid = html.escape(n["id"], quote=True)
        if n["type"] == "group":
            parts.append(f'<div class="group" style="{style}"><div class="glabel">{inline(n.get("label", ""))}</div></div>')
            continue
        cls = "node colored" if n.get("color") else "node"
        if n["type"] == "text":
            body = md(n.get("text", ""))
        elif n["type"] == "file":
            body = f'<div class="file">📄 {html.escape(n["file"])}{html.escape(n.get("subpath", ""))}</div>'
        else:
            body = f'<div class="file">🔗 {html.escape(n.get("url", ""))}</div>'
        parts.append(f'<div class="{cls}" data-id="{nid}" style="{style}">{body}</div>')

    def pt(n, side):
        x, y, w, h = n["x"] - minx, n["y"] - miny, n["width"], n["height"]
        return {"left": (x, y + h / 2, -1, 0), "right": (x + w, y + h / 2, 1, 0),
                "top": (x + w / 2, y, 0, -1), "bottom": (x + w / 2, y + h, 0, 1)}[side]

    def auto_side(a, b):
        dx = (b["x"] + b["width"] / 2) - (a["x"] + a["width"] / 2)
        dy = (b["y"] + b["height"] / 2) - (a["y"] + a["height"] / 2)
        if abs(dx) >= abs(dy):
            return ("right", "left") if dx > 0 else ("left", "right")
        return ("bottom", "top") if dy > 0 else ("top", "bottom")

    svg = []
    for e in canvas.get("edges", []):
        a, b = by_id.get(e["fromNode"]), by_id.get(e["toNode"])
        if not a or not b:
            continue
        fs, ts = auto_side(a, b)
        p, q = pt(a, e.get("fromSide", fs)), pt(b, e.get("toSide", ts))
        d = max(60, min(200, (abs(p[0] - q[0]) + abs(p[1] - q[1])) / 3))
        c = color(e.get("color")) or "#6b6e7b"
        start = ' marker-start="url(#arr)"' if e.get("fromEnd") == "arrow" else ""
        end = "" if e.get("toEnd") == "none" else ' marker-end="url(#arr)"'
        path = f"M{p[0]},{p[1]} C{p[0] + p[2] * d},{p[1] + p[3] * d} {q[0] + q[2] * d},{q[1] + q[3] * d} {q[0]},{q[1]}"
        svg.append(f'<path class="edge" d="{path}" stroke="{c}"{start}{end}/>')
        if e.get("label"):
            mx = (p[0] + q[0]) / 2 + (p[2] + q[2]) * d * 0.375
            my = (p[1] + q[1]) / 2 + (p[3] + q[3]) * d * 0.375
            svg.append(f'<foreignObject x="{mx - 160}" y="{my - 14}" width="320" height="40"><div class="elabel">'
                       f'<span>{inline(e["label"])}</span></div></foreignObject>')

    bg, fg, card, border, codebg = (("#f6f6f4", "#2e2e2e", "#ffffff", "#d6d6d6", "#eeeeec") if light
                                     else ("#1e1e22", "#dcddde", "#26272c", "#44464f", "#38393f"))
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Canvas preview</title><style>
body{{margin:0;background:{bg};font:15px/1.45 -apple-system,BlinkMacSystemFont,"Inter","Segoe UI",sans-serif;color:{fg}}}
.board{{position:relative;width:{W}px;height:{H}px;background-image:radial-gradient({border} 1px,transparent 1px);background-size:24px 24px}}
.group{{position:absolute;box-sizing:border-box;border:2px solid var(--c);border-radius:14px;background:color-mix(in srgb,var(--c) 8%,transparent)}}
.glabel{{position:absolute;top:-32px;left:4px;font-weight:700;font-size:19px;color:var(--c);white-space:nowrap}}
.node{{position:absolute;box-sizing:border-box;padding:12px 16px;border:2px solid {border};border-radius:10px;background:{card};overflow:hidden}}
.node.colored{{border-color:var(--c);background:color-mix(in srgb,var(--c) 13%,{card})}}
.node.overflow{{outline:4px dashed #ff3b30;outline-offset:3px}}
h1{{font-size:32px;margin:0 0 10px;line-height:1.2}} h2{{font-size:23px;margin:0 0 8px}} h3{{font-size:18px;margin:0 0 6px}} h4,h5,h6{{font-size:16px;margin:0 0 4px}}
p{{margin:0 0 6px}} ul,ol{{margin:0 0 6px;padding-left:22px}} li{{margin:1px 0}} hr{{border:0;border-top:1px solid {border}}}
blockquote{{margin:0 0 6px;padding-left:10px;border-left:3px solid {border};opacity:.85}}
code{{font:13px ui-monospace,Menlo,monospace;background:{codebg};color:#e8875b;padding:1px 4px;border-radius:4px}}
pre{{font:13px ui-monospace,Menlo,monospace;background:{codebg};padding:8px;border-radius:6px;white-space:pre-wrap}}
table{{border-collapse:collapse;margin:4px 0 8px;font-size:14px}} th,td{{border:1px solid {border};padding:3px 7px;text-align:left;vertical-align:top}}
a.wl{{color:#a88bfa;text-decoration:underline}} mark{{background:#e2b20366;color:inherit}}
.file{{font-weight:600;opacity:.9}}
svg{{position:absolute;inset:0;overflow:visible;pointer-events:none}} .edge{{fill:none;stroke-width:2.5}}
.elabel{{display:flex;justify-content:center}} .elabel span{{background:{bg};border:1px solid {border};border-radius:6px;padding:2px 8px;font-size:13px;white-space:nowrap}}
</style></head><body><div class="board">{''.join(parts)}
<svg width="{W}" height="{H}"><defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#a3a5b0" stroke="none"/></marker></defs>{''.join(svg)}</svg>
</div><pre id="report" style="display:none"></pre><script>
const over=[...document.querySelectorAll('.node')].filter(n=>n.scrollHeight>n.clientHeight+4||n.scrollWidth>n.clientWidth+4)
  .map(n=>{{n.classList.add('overflow');return {{id:n.dataset.id,need:n.scrollHeight,have:n.clientHeight}}}});
document.getElementById('report').textContent=JSON.stringify(over);
</script></body></html>""", W, H


def find_chrome():
    cands = ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
             "/Applications/Chromium.app/Contents/MacOS/Chromium",
             "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
             "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"]
    for c in cands:
        if os.path.exists(c):
            return c
    for name in ["google-chrome", "chromium", "chromium-browser", "brave-browser", "microsoft-edge", "chrome"]:
        p = shutil.which(name)
        if p:
            return p
    return None


def _vault_of(path):
    d = os.path.dirname(os.path.abspath(path))
    while d != os.path.dirname(d):
        if os.path.isdir(os.path.join(d, ".obsidian")):
            return d
        d = os.path.dirname(d)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from find_vault import vaults
        vs = vaults()
        return next((p for p, is_open in vs if is_open), vs[0][0] if vs else None)
    except Exception:
        return None


def _system_theme():
    try:
        if sys.platform == "darwin":
            r = subprocess.run(["defaults", "read", "-g", "AppleInterfaceStyle"], capture_output=True, text=True)
            return "dark" if "Dark" in r.stdout else "light"
        if sys.platform.startswith("win"):
            import winreg
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                               r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
            return "light" if winreg.QueryValueEx(k, "AppsUseLightTheme")[0] else "dark"
        r = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                           capture_output=True, text=True)
        return "dark" if "dark" in r.stdout else "light"
    except Exception:
        return "dark"


def resolve_theme(choice, canvas_path):
    """Return (light?, reason)."""
    if choice in ("light", "dark"):
        return choice == "light", "requested"
    vault = _vault_of(canvas_path)
    theme = None
    if vault:
        try:
            theme = json.load(open(os.path.join(vault, ".obsidian", "appearance.json"), encoding="utf-8")).get("theme")
        except (OSError, ValueError):
            pass
    if theme == "moonstone":
        return True, "Obsidian theme of the vault"
    if theme == "obsidian":
        return False, "Obsidian theme of the vault"
    system = _system_theme()
    return system == "light", "Obsidian follows the system" if vault else "system appearance (no vault found)"


def main():
    args = sys.argv[1:]
    png = None
    if "--png" in args:
        i = args.index("--png")
        png = os.path.abspath(args[i + 1])
        del args[i:i + 2]
    theme = "light" if "--light" in args else "auto"
    if "--theme" in args:
        i = args.index("--theme")
        theme = args[i + 1]
        del args[i:i + 2]
    args = [a for a in args if not a.startswith("--")]
    if len(args) != 2 or theme not in ("auto", "light", "dark"):
        print(__doc__)
        sys.exit(2)
    light, why = resolve_theme(theme, args[0])
    print(f"THEME   {'light' if light else 'dark'} ({why})")
    with open(args[0], encoding="utf-8") as f:
        canvas = json.load(f)
    doc, W, H = render(canvas, light)
    out = os.path.abspath(args[1])
    with open(out, "w", encoding="utf-8") as f:
        f.write(doc)
    print("wrote", out, f"({int(W)}x{int(H)})")
    chrome = find_chrome()
    if not chrome:
        print("NOTE    no Chrome/Chromium found: skipped overflow check and PNG")
        return
    with tempfile.TemporaryDirectory() as profile:
        base = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={profile}",
                "--force-device-scale-factor=1", f"--window-size={int(W)},{int(H)}"]
        dom = subprocess.run(base + ["--virtual-time-budget=2000", "--dump-dom", "file://" + out],
                             capture_output=True, text=True, timeout=120).stdout
        m = re.search(r'<pre id="report"[^>]*>(.*?)</pre>', dom, re.S)
        over = json.loads(html.unescape(m[1])) if m and m[1].strip() else []
        for o in over:
            print(f"OVERFLOW node '{o['id']}' needs ~{o['need']}px, has {o['have']}px (raise its row height or trim text)")
        if not over:
            print("OK      no text overflow")
        if png:
            subprocess.run(base + [f"--screenshot={png}", "file://" + out], capture_output=True, timeout=120)
            print("wrote", png if os.path.exists(png) else "(PNG failed)")


if __name__ == "__main__":
    main()
