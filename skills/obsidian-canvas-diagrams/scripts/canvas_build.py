#!/usr/bin/env python3
"""Build an Obsidian JSON Canvas (.canvas) from a compact grid, swimlane or sequence spec, then lint it.

Usage:
  python3 canvas_build.py spec.json out.canvas [--strict]

The spec places nodes on a grid (col/row), so you never compute pixels. The builder sizes rows from the
text, wraps groups around their members, picks edge sides, adds a header (title + legend + nav links) and
reports readability problems (unlabeled arrows, arrows through boxes, crossings, too many boxes...).
Exit code: 0 ok, 1 errors (or warnings with --strict). See references/spec.md for the format.
"""
import json
import math
import re
import sys

PRESET = {"1": "red", "2": "orange", "3": "yellow", "4": "green", "5": "cyan", "6": "purple"}
GROUP_PAD = 30
GROUP_LABEL = 40  # Obsidian draws the group label above the box
MAX_BOXES = 20
MAX_LABEL = 40
# Header words in the reader's language (spec "lang"); "labels" in the spec overrides them.
WORDS = {"en": ("Legend", "Related"), "es": ("Leyenda", "Relacionado"), "ca": ("Llegenda", "Relacionat"),
         "pt": ("Legenda", "Relacionado"), "fr": ("Légende", "Voir aussi"), "it": ("Legenda", "Correlati"),
         "de": ("Legende", "Siehe auch")}


def estimate_height(text, width):
    """Rough rendered height of Obsidian markdown in a text node. Errs on the tall side."""
    chars = max(12, int((width - 48) / 7.8))
    h = 32
    table_cols = 0
    for line in text.split("\n"):
        s = line.strip()
        if not s:
            h += 8
            continue
        m = re.match(r"(#{1,6}) ", s)
        if m:
            size = {1: 46, 2: 36, 3: 30}.get(len(m[1]), 26)
            h += size * math.ceil(len(s) / (chars * (0.6 if len(m[1]) == 1 else 0.8)))
            continue
        if s.startswith("|"):
            cells = [c for c in s.strip("|").split("|")]
            if all(re.fullmatch(r"\s*:?-+:?\s*", c) for c in cells):
                continue
            table_cols = len(cells)
            per = max(4, chars // max(1, table_cols))
            h += 28 * max(math.ceil(len(c.strip()) / per) for c in cells)
            continue
        plain = re.sub(r"[*`]|\[\[|\]\]", "", s)
        h += 23 * math.ceil(len(plain) / chars)
    return int(math.ceil(h / 20.0) * 20)


def swimlane_to_grid(spec):
    """Lanes become full-width groups (one row each); steps flow left to right by order."""
    lanes = spec["lanes"]
    lane_row = {lane["id"]: i for i, lane in enumerate(lanes)}
    nodes, edges = [], list(spec.get("edges", []))
    col = -1
    prev = None
    number = 0
    for step in spec["steps"]:
        branch = step.get("noChain", False)
        n = dict(step)
        n["row"] = lane_row[step["lane"]]
        n["group"] = step["lane"]
        if branch:
            # Side branch (failure path, note): placed where asked, does not advance the main sequence.
            n["col"] = step.get("col", max(col, 0))
        else:
            col = step.get("col", col + 1)
            n["col"] = col
            number += 1
            if spec.get("number", True) and "text" in n:
                n["text"] = f"**{number}.** {n['text']}"
        nodes.append(n)
        if branch:
            continue
        if spec.get("chain", True) and prev:
            edges.append({"from": prev, "to": step["id"], "label": step.get("edgeLabel", "")})
        prev = step["id"]
    groups = [dict(lane, fullWidth=True) for lane in lanes]
    out = dict(spec)
    out.update(layout="grid", nodes=nodes, edges=edges, groups=groups)
    out.setdefault("colWidth", 280)
    out.setdefault("colGap", 120)
    return out


def sequence_to_grid(spec):
    """Participants become columns (lifeline frames); each message is a row with a horizontal arrow."""
    parts = spec["participants"]
    col_of = {p["id"]: i for i, p in enumerate(parts)}
    nodes = [{"id": f"p-{p['id']}", "col": i, "row": 0, "group": p["id"], "color": p.get("color"),
              "text": p.get("text", f"### {p.get('label', p['id'])}")} for i, p in enumerate(parts)]
    edges = list(spec.get("edges", []))
    for n, m in enumerate(spec["messages"], start=1):
        mid = m.get("id", f"m{n}")
        note = m.get("note")
        if m["from"] == m["to"]:  # self call: just a note on the lifeline
            nodes.append({"id": mid, "col": col_of[m["to"]], "row": n, "group": m["to"], "color": m.get("color"),
                          "text": f"**{n}.** {m.get('label', '')}" + (f"\n{note}" if note else "")})
            continue
        # The caller gets a numbered stub; the receiver gets an activation bar, or a box if there is a note.
        stub = {"width": 64, "height": 64, "align": "center", "anchor": True}
        nodes.append(dict(stub, id=f"{mid}-src", col=col_of[m["from"]], row=n, group=m["from"], text=f"**{n}**"))
        tgt = {"id": mid, "col": col_of[m["to"]], "row": n, "group": m["to"], "color": m.get("color")}
        tgt.update({"text": f"**{n}.** {note}"} if note else dict(stub, width=24, text=""))
        nodes.append(tgt)
        label = ("↩ " if m.get("reply") else "") + m.get("label", "")
        edges.append({"from": f"{mid}-src", "to": mid, "label": label, "color": m.get("color")})
    groups = [{"id": p["id"], "label": p.get("lifelineLabel", ""), "color": p.get("color"), "fullHeight": True}
              for p in parts]
    out = dict(spec)
    out.update(layout="grid", nodes=[{k: v for k, v in n.items() if v is not None} for n in nodes],
               edges=[{k: v for k, v in e.items() if v is not None} for e in edges], groups=groups)
    out.setdefault("colWidth", 240)
    out.setdefault("colGap", 200)
    out.setdefault("rowGap", 40)
    out.setdefault("minRowHeight", 60)
    return out


def side_for(a, b, colgap, rowgap):
    ax, ay = a["x"] + a["width"] / 2, a["y"] + a["height"] / 2
    bx, by = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
    h_clear = b["x"] >= a["x"] + a["width"] or a["x"] >= b["x"] + b["width"]
    v_clear = b["y"] >= a["y"] + a["height"] or a["y"] >= b["y"] + b["height"]
    horizontal = h_clear and (not v_clear or abs(bx - ax) / (a["width"] + colgap) >= abs(by - ay) / (a["height"] + rowgap))
    if horizontal:
        return ("right", "left") if bx > ax else ("left", "right")
    return ("bottom", "top") if by > ay else ("top", "bottom")


def anchor(n, side):
    x, y, w, h = n["x"], n["y"], n["width"], n["height"]
    return {"left": (x, y + h / 2), "right": (x + w, y + h / 2), "top": (x + w / 2, y), "bottom": (x + w / 2, y + h)}[side]


def seg_hits_rect(p, q, r, shrink=10):
    x0, y0, x1, y1 = r["x"] + shrink, r["y"] + shrink, r["x"] + r["width"] - shrink, r["y"] + r["height"] - shrink
    for t in [i / 40 for i in range(1, 40)]:
        x, y = p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t
        if x0 < x < x1 and y0 < y < y1:
            return True
    return False


def segs_cross(p1, p2, p3, p4):
    def ccw(a, b, c):
        return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])

    d1, d2, d3, d4 = ccw(p3, p4, p1), ccw(p3, p4, p2), ccw(p1, p2, p3), ccw(p1, p2, p4)
    return (d1 * d2 < 0) and (d3 * d4 < 0)


def build(spec):
    errors, warnings, info = [], [], []
    layout = spec.get("layout", "grid")
    if layout == "swimlane":
        spec = swimlane_to_grid(spec)
    elif layout == "sequence":
        spec = sequence_to_grid(spec)
    cw = spec.get("colWidth", 360)
    cg = spec.get("colGap", 160)
    rg = spec.get("rowGap", 120)
    nodes = spec.get("nodes", [])
    groups = {g["id"]: g for g in spec.get("groups", [])}

    ids = [n["id"] for n in nodes] + list(groups)
    for dup in {i for i in ids if ids.count(i) > 1}:
        errors.append(f"duplicate id '{dup}'")

    for n in nodes:
        n.setdefault("colspan", 1)
        n.setdefault("rowspan", 1)
        if n.get("group") and n["group"] not in groups:
            errors.append(f"node '{n['id']}' references unknown group '{n['group']}'")
        if "text" not in n and "file" not in n and "url" not in n:
            errors.append(f"node '{n['id']}' needs text, file or url")
        if "text" in n and not n.get("anchor") and not re.match(r"\s*(#|\*\*)", n["text"]):
            info.append(f"node '{n['id']}' has no heading/bold name on its first line")

    ncols = max((n["col"] + n["colspan"] for n in nodes), default=1)
    nrows = max((n["row"] + n["rowspan"] for n in nodes), default=1)

    cells = {}
    for n in nodes:
        for c in range(n["col"], n["col"] + n["colspan"]):
            for r in range(n["row"], n["row"] + n["rowspan"]):
                if (c, r) in cells:
                    errors.append(f"nodes '{cells[(c, r)]}' and '{n['id']}' share grid cell col={c} row={r}")
                cells[(c, r)] = n["id"]

    def width_of(n):
        return n.get("width", cw * n["colspan"] + cg * (n["colspan"] - 1))

    row_h = [spec.get("minRowHeight", 100)] * nrows
    for n in nodes:
        est = n.get("height") or (estimate_height(n["text"], width_of(n)) if "text" in n else 80 if "url" in n else 400)
        n["_est"] = est
        if n["rowspan"] == 1:
            row_h[n["row"]] = max(row_h[n["row"]], est)
    for n in nodes:
        if n["rowspan"] > 1:
            span = sum(row_h[n["row"]:n["row"] + n["rowspan"]]) + rg * (n["rowspan"] - 1)
            if n["_est"] > span:
                row_h[n["row"] + n["rowspan"] - 1] += n["_est"] - span

    # header: title (+ nav links) and legend, above the grid
    grid_w = ncols * cw + (ncols - 1) * cg
    out_nodes, out_groups = [], []
    legend_word, related_word = WORDS.get(spec.get("lang", "en"), WORDS["en"])
    legend_word = spec.get("labels", {}).get("legend", legend_word)
    related_word = spec.get("labels", {}).get("related", related_word)
    if "lang" not in spec:
        info.append('no "lang" in spec: header words default to English ("Legend", "Related")')
    header_lines = [f"# {spec['title']}"] if spec.get("title") else []
    if spec.get("description"):
        header_lines.append(spec["description"])
    if spec.get("links"):
        header_lines.append(f"**{related_word}:** " + " · ".join(spec["links"]))
    legend = spec.get("legend", [])
    legend_w = 300 if legend else 0
    title_w = max(400, grid_w - legend_w - (cg if legend else 0))
    header_h = 0
    if header_lines:
        text = "\n\n".join(header_lines)
        header_h = estimate_height(text, title_w)
    title_h = header_h
    legend_h = 32 + 64 * len(legend) if legend else 0
    header_h = max(header_h, legend_h)
    y0 = header_h + rg + GROUP_LABEL if header_h else 0
    if header_lines:
        out_nodes.append({"id": "_title", "type": "text", "x": 0, "y": 0, "width": title_w, "height": title_h,
                          "text": "\n\n".join(header_lines)})
    if legend:
        lx = grid_w - legend_w if grid_w > title_w else title_w + cg
        out_groups.append({"id": "_legend", "type": "group", "x": lx, "y": 0, "width": legend_w,
                           "height": legend_h, "label": legend_word})
        for i, item in enumerate(legend):
            node = {"id": f"_legend{i}", "type": "text", "x": lx + 16, "y": 16 + i * 64, "width": legend_w - 32,
                    "height": 56, "text": item["label"]}
            if item.get("color"):
                node["color"] = item["color"]
            out_nodes.append(node)

    # A group boundary between two stacked rows needs room for both frames' padding and the lower label.
    group_at = {(c, r): n.get("group") for n in nodes
                for c in range(n["col"], n["col"] + n["colspan"]) for r in range(n["row"], n["row"] + n["rowspan"])}
    full_rows = {n["row"]: n["group"] for n in nodes if n.get("group") and groups[n["group"]].get("fullWidth")}
    row_y = [y0]
    for r, h in enumerate(row_h[:-1], start=1):
        boundary = any((c, r - 1) in group_at and (c, r) in group_at and group_at[(c, r - 1)] != group_at[(c, r)]
                       for c in range(ncols))
        if full_rows:  # full-width lanes: every lane change is a boundary, so lanes stay evenly spaced
            boundary = boundary or (full_rows.get(r - 1) != full_rows.get(r))
        row_y.append(row_y[-1] + h + rg + (GROUP_LABEL + GROUP_PAD if boundary else 0))
    for n in nodes:
        x = n["col"] * (cw + cg)
        y = row_y[n["row"]]
        last = n["row"] + n["rowspan"] - 1
        h = row_y[last] + row_h[last] - y
        if spec.get("fitHeight", False) or n.get("height"):
            h = n.get("height", n["_est"])
        if n.get("align") == "center":  # small anchor centred in its cell (sequence messages)
            x += (cw * n["colspan"] + cg * (n["colspan"] - 1) - width_of(n)) / 2
            y += (row_y[last] + row_h[last] - y - h) / 2
        node = {"id": n["id"], "x": int(x), "y": int(y), "width": int(width_of(n)), "height": int(h)}
        if "text" in n:
            node.update(type="text", text=n["text"])
        elif "file" in n:
            node.update(type="file", file=n["file"])
            if n.get("subpath"):
                node["subpath"] = n["subpath"]
        else:
            node.update(type="link", url=n["url"])
        if n.get("color"):
            node["color"] = n["color"]
        node["_group"] = n.get("group")
        node["_anchor"] = n.get("anchor", False)
        out_nodes.append(node)

    by_id = {n["id"]: n for n in out_nodes}
    grid_nodes = [n for n in out_nodes if not n["id"].startswith("_")]
    for gid, g in groups.items():
        members = [n for n in grid_nodes if n["_group"] == gid]
        if not members:
            warnings.append(f"group '{gid}' has no nodes")
            continue
        x0 = 0 if g.get("fullWidth") else min(n["x"] for n in members)
        x1 = grid_w if g.get("fullWidth") else max(n["x"] + n["width"] for n in members)
        y_min = min(n["y"] for n in members)
        y_max = max(n["y"] + n["height"] for n in (grid_nodes if g.get("fullHeight") else members))
        grp = {"id": gid, "type": "group", "x": int(x0 - GROUP_PAD), "y": int(y_min - GROUP_PAD),
               "width": int(x1 - x0 + 2 * GROUP_PAD), "height": int(y_max - y_min + 2 * GROUP_PAD),
               "label": g.get("label", gid)}
        if g.get("color"):
            grp["color"] = g["color"]
        out_groups.append(grp)
    for a in out_groups:
        for b in out_groups:
            if a["id"] < b["id"] and a["id"] != "_legend" and b["id"] != "_legend":
                inter = not (a["x"] + a["width"] <= b["x"] or b["x"] + b["width"] <= a["x"]
                             or a["y"] + a["height"] <= b["y"] or b["y"] + b["height"] <= a["y"])
                if inter:
                    warnings.append(f"groups '{a['id']}' and '{b['id']}' overlap: keep each group's nodes in a "
                                    "contiguous block of cells")

    out_edges, segs = [], []
    for i, e in enumerate(spec.get("edges", [])):
        if e["from"] not in by_id or e["to"] not in by_id:
            errors.append(f"edge {e['from']} -> {e['to']} references an unknown node")
            continue
        a, b = by_id[e["from"]], by_id[e["to"]]
        fs, ts = side_for(a, b, cg, rg)
        fs, ts = e.get("fromSide", fs), e.get("toSide", ts)
        edge = {"id": e.get("id", f"edge-{i}"), "fromNode": a["id"], "fromSide": fs, "toNode": b["id"], "toSide": ts}
        label = e.get("label", "")
        if label:
            edge["label"] = label
            if len(label) > MAX_LABEL:
                warnings.append(f"edge label too long ({len(label)} chars): '{label}' — keep it to a verb phrase")
        else:
            warnings.append(f"edge {a['id']} -> {b['id']} has no label (say what flows or why)")
        if e.get("color"):
            edge["color"] = e["color"]
        if e.get("bidirectional"):
            edge["fromEnd"] = "arrow"
            warnings.append(f"edge {a['id']} <-> {b['id']} is bidirectional: prefer two labeled arrows")
        if e.get("noArrow"):
            edge["toEnd"] = "none"
        p, q = anchor(a, fs), anchor(b, ts)
        for n in grid_nodes:
            if n["id"] not in (a["id"], b["id"]) and seg_hits_rect(p, q, n):
                warnings.append(f"edge {a['id']} -> {b['id']} passes over node '{n['id']}': move one end or "
                                "reorder columns")
        segs.append((edge["id"], p, q, a["id"], b["id"]))
        out_edges.append(edge)

    node_ids = {n["id"] for n in out_nodes + out_groups}
    for dup in sorted({e["id"] for e in out_edges} & node_ids):
        errors.append(f"edge id '{dup}' is also a node id: rename one (ids must be unique across the canvas)")
    edge_ids = [e["id"] for e in out_edges]
    for dup in sorted({i for i in edge_ids if edge_ids.count(i) > 1}):
        errors.append(f"duplicate edge id '{dup}'")

    crossings = 0
    for i in range(len(segs)):
        for j in range(i + 1, len(segs)):
            s, t = segs[i], segs[j]
            if {s[3], s[4]} & {t[3], t[4]}:
                continue
            if segs_cross(s[1], s[2], t[1], t[2]):
                crossings += 1
                warnings.append(f"edges {s[3]}->{s[4]} and {t[3]}->{t[4]} cross")
    boxes = [n for n in grid_nodes if not n["_anchor"]]
    info.append(f"{len(boxes)} boxes, {len(out_edges)} edges, {crossings} crossings")
    if len(boxes) > spec.get("maxBoxes", MAX_BOXES):
        warnings.append(f"{len(boxes)} boxes: split this canvas (one question per canvas)")

    if layout == "swimlane":
        lane_row = {g["id"]: i for i, g in enumerate(spec["groups"])}
        steps = [n for n in nodes if n.get("group") in lane_row]
        for lane, r in lane_row.items():
            k = sum(1 for n in steps if n["group"] == lane)
            if k == 1 and len(steps) >= 5:
                warnings.append(f"lane '{lane}' holds a single step: merge it into a neighbour lane, or turn it "
                                "into a noChain note in the lane that triggers it")
        node_lane = {n["id"]: n["group"] for n in steps}
        for e in spec.get("edges", []):
            a, b = node_lane.get(e["from"]), node_lane.get(e["to"])
            if a and b and abs(lane_row[a] - lane_row[b]) > 1:
                between = [g for g, r in lane_row.items() if min(lane_row[a], lane_row[b]) < r < max(lane_row[a], lane_row[b])]
                warnings.append(f"edge {e['from']} -> {e['to']} jumps over lane(s) {', '.join(between)}: put lanes "
                                "that talk to each other next to each other")
        fill = len(steps) / max(1, len(lane_row) * ncols)
        if len(lane_row) > 2 and fill < 0.25:
            warnings.append(f"swimlane is {int((1 - fill) * 100)}% empty: drop or merge lanes with few steps, or "
                            "use a sequence layout for request/response flows")

    used = {n.get("color") for n in grid_nodes + out_groups + out_edges if n.get("color")}
    legend_colors = {i.get("color") for i in legend}
    missing = used - legend_colors
    if missing and not spec.get("noLegend"):
        warnings.append("colors without a legend entry: " + ", ".join(f"{c} ({PRESET.get(c, c)})" for c in sorted(missing)))
    if not spec.get("title"):
        warnings.append("canvas has no title")

    for n in out_nodes:
        n.pop("_group", None)
        n.pop("_anchor", None)
    canvas = {"nodes": out_groups + out_nodes, "edges": out_edges}
    return canvas, errors, warnings, info


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        print(__doc__)
        sys.exit(2)
    with open(args[0], encoding="utf-8") as f:
        spec = json.load(f)
    canvas, errors, warnings, info = build(spec)
    for m in errors:
        print("ERROR  ", m)
    for m in warnings:
        print("WARN   ", m)
    for m in info:
        print("INFO   ", m)
    if errors:
        sys.exit(1)
    with open(args[1], "w", encoding="utf-8") as f:
        json.dump(canvas, f, ensure_ascii=False, indent="\t")
    print("wrote", args[1])
    if warnings and "--strict" in sys.argv:
        sys.exit(1)


if __name__ == "__main__":
    main()
