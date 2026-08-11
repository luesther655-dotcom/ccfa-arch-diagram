#!/usr/bin/env python3
"""Exact-geometry verification of a rendered draw.io SVG vs the .drawio topology.

validate.py lints the .drawio XML without rendering, approximating auto-routed
edges with a Manhattan Z-route (and skipping diagonal auto-routes entirely).
This script reads the *actual* rendered SVG exported by draw.io and re-checks
the defect classes against the real drawn paths - the "render truth" a vision
self-check would provide, but deterministic, so it works even when the model
cannot read images (a language model skips 目检 but still gets this gate).

Checks (ported from the user's svginspect.py; dead code dropped):
  1. an edge line passing THROUGH a box that is not its own source/target,
  2. an edge line passing through a text label / note / caption,
  3. two edge lines properly crossing in open space,
  4. a single edge's own route self-intersecting (a loop back on itself),
  5. (opt-in --acyclic) the directed flow graph containing a cycle,
  + connectivity INFO: each edge's drawn line touches both endpoint boxes.

The SVG must come from draw.io desktop export - it carries data-cell-id
attributes that map rendered shapes back to mxCell ids (present by default,
no -e needed). Exit status is non-zero when any FINDING (or, with --strict,
any INFO) is found, so it can gate the workflow after PNG/SVG export.

Usage:
  python3 scripts/svgcheck.py <name>.drawio <name>.svg
  python3 scripts/svgcheck.py <name>.drawio <name>.svg --acyclic
  python3 scripts/svgcheck.py <name>.drawio <name>.svg --strict
"""
import argparse
import html
import math
import re
import sys
import xml.etree.ElementTree as ET

SVG = "{http://www.w3.org/2000/svg}"


# ---------- affine transforms (translate / rotate / scale / matrix) ----------
def mat_apply(m, p):
    a, b, c, d, e, f = m
    x, y = p
    return (a * x + c * y + e, b * x + d * y + f)


def mat_mul(m2, m1):
    """Apply m1 then m2 (m2 composed over m1)."""
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (a2 * a1 + c2 * b1, b2 * a1 + d2 * b1,
            a2 * c1 + c2 * d1, b2 * c1 + d2 * d1,
            a2 * e1 + c2 * f1 + e2, b2 * e1 + d2 * f1 + f2)


def parse_transform(tr):
    if not tr:
        return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    m = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for cmd in re.findall(r"([a-zA-Z]+)\(([^)]*)\)", tr):
        k, args = cmd[0], [float(v) for v in cmd[1].replace(",", " ").split()]
        if k == "translate":
            m = mat_mul((1, 0, 0, 1, args[0], args[1] if len(args) > 1 else 0), m)
        elif k == "rotate":
            ang, cx, cy = math.radians(args[0]), (args[1] if len(args) > 1 else 0), (args[2] if len(args) > 2 else 0)
            ca, sa = math.cos(ang), math.sin(ang)
            m = mat_mul((ca, sa, -sa, ca, cx - ca * cx + sa * cy, cy - sa * cx - ca * cy), m)
        elif k == "scale":
            m = mat_mul((args[0], 0, 0, args[1] if len(args) > 1 else args[0], 0, 0), m)
        elif k == "matrix":
            m = mat_mul(tuple(args), m)
    return m


# ---------- path 'd' parsing ----------
def path_points(d, m):
    """Sample a path's 'd' into a transformed point list."""
    toks = re.findall(r"[MLHVZQCASmlhvzqcas]|-?\d*\.?\d+(?:e[-+]?\d+)?", d)
    pts = []
    i = 0
    cur = None
    def num():
        nonlocal i
        v = float(toks[i]); i += 1; return v
    def add(x, y):
        nonlocal cur
        cur = (x, y)
        pts.append(mat_apply(m, (x, y)))
    while i < len(toks):
        cmd = toks[i]; i += 1
        if cmd in "Mm":
            x, y = num(), num(); add(x, y)
            while i < len(toks) and re.match(r"-?\d", toks[i]):
                x, y = num(), num(); add(x, y)
        elif cmd in "Ll":
            x, y = num(), num(); add(x, y)
            while i < len(toks) and re.match(r"-?\d", toks[i]):
                x, y = num(), num(); add(x, y)
        elif cmd in "Hh":
            x = num(); add(x, cur[1])
        elif cmd in "Vv":
            y = num(); add(cur[0], y)
        elif cmd in "Zz":
            pass
        elif cmd in "Qq":
            # approximate quadratic: emit midpoint + endpoint
            cx, cy = num(), num()
            x, y = num(), num()
            mx, my = (cur[0] + 2 * cx) / 3, (cur[1] + 2 * cy) / 3
            add(mx, my)
            add(x, y)
        elif cmd in "Cc":
            cx1, cy1, cx2, cy2, x, y = num(), num(), num(), num(), num(), num()
            for t in (0.33, 0.66):
                bx = (1 - t) ** 3 * cur[0] + 3 * (1 - t) ** 2 * t * cx1 + 3 * (1 - t) * t ** 2 * cx2 + t ** 3 * x
                by = (1 - t) ** 3 * cur[1] + 3 * (1 - t) ** 2 * t * cy1 + 3 * (1 - t) * t ** 2 * cy2 + t ** 3 * y
                add(bx, by)
            add(x, y)
        else:
            break
    return pts


def poly_bbox(pts):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def rect_bbox(rect, m):
    x, y, w, h = float(rect.get("x", 0)), float(rect.get("y", 0)), float(rect.get("width", 0)), float(rect.get("height", 0))
    pts = [mat_apply(m, p) for p in ((x, y), (x + w, y), (x, y + h), (x + w, y + h))]
    return poly_bbox(pts)


def ellipse_bbox(el, m):
    cx, cy, rx, ry = float(el.get("cx", 0)), float(el.get("cy", 0)), float(el.get("rx", 0)), float(el.get("ry", 0))
    pts = [mat_apply(m, p) for p in ((cx - rx, cy - ry), (cx + rx, cy - ry), (cx - rx, cy + ry), (cx + rx, cy + ry))]
    return poly_bbox(pts)


# ---------- geometry predicates ----------
def orient(a, b, c):
    v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return 0 if abs(v) < 1e-9 else (1 if v > 0 else -1)


def seg_cross(p1, p2, p3, p4):
    """STRICT proper crossing: touching/collinear endpoints (any orient == 0)
    does not count, so routes that merely start/end on a shape's boundary are
    not treated as crossing into it."""
    o1, o2 = orient(p1, p2, p3), orient(p1, p2, p4)
    o3, o4 = orient(p3, p4, p1), orient(p3, p4, p2)
    return (o1 != o2 and o3 != o4 and o1 != 0 and o2 != 0 and o3 != 0 and o4 != 0)


def point_in_rect(p, r, inset=0.0):
    x, y, w, h = r
    return x + inset <= p[0] <= x + w - inset and y + inset <= p[1] <= y + h - inset


def seg_through_rect(p1, p2, r, inset=0.0):
    """Segment enters rect interior by >inset."""
    x, y, w, h = r
    if point_in_rect(p1, r, inset) or point_in_rect(p2, r, inset):
        return True
    corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    edges = list(zip(corners, corners[1:] + corners[:1]))
    return any(seg_cross(p1, p2, a, b) for a, b in edges)


def poly_through_rect(pts, r, inset=0.0):
    return any(seg_through_rect(a, b, r, inset) for a, b in zip(pts, pts[1:]))


def is_container(bb, all_boxes):
    """True if bb fully contains another box (a panel/legend). Edges are
    expected to run inside panels, so containers are exempt from through-checks."""
    x, y, w, h = bb
    for ob in all_boxes:
        if ob is bb:
            continue
        ox, oy, ow, oh = ob
        if ow * oh >= 0.9 * (w * h):
            continue
        if x < ox and y < oy and x + w > ox + ow and y + h > oy + oh:
            return True
    return False


# ---------- load topology from .drawio ----------
def _plain(v):
    v = html.unescape(v or "")
    return re.sub(r"<[^>]+>", "", v).strip()


def load_topology(drawio_path):
    t = ET.parse(drawio_path)
    root = t.getroot().find("diagram").find("mxGraphModel").find("root")
    vertices, edges = {}, {}
    for cell in root.findall("mxCell"):
        cid = cell.get("id")
        if not cid or cid in ("0", "1"):
            continue
        if cell.get("edge") == "1":
            edges[cid] = {"source": cell.get("source"), "target": cell.get("target"),
                          "value": _plain(cell.get("value"))}
        elif cell.get("vertex") == "1":
            style = cell.get("style") or ""
            is_text = style.startswith("text;") or "text;" in style[:8]
            vertices[cid] = {"text": is_text, "value": _plain(cell.get("value"))}
    return vertices, edges


# ---------- extract per-cell geometry from SVG ----------
def collect_svg(svg_path):
    """Return cellid -> {boxes:[bbox], lines:[pts], labels:[...]} from the SVG.

    Fails loudly when the SVG carries no data-cell-id: that mapping is what
    turns raw shapes back into mxCell ids, and without it every check would
    silently no-op. draw.io desktop SVG export includes it by default.
    """
    t = ET.parse(svg_path)
    root = t.getroot()
    cells = {}  # cellid -> {boxes:[bbox], lines:[pts], labels:[(cx,cy,text,fs,...)]}
    found_ids = [False]
    def ensure(cid):
        return cells.setdefault(cid, {"boxes": [], "lines": [], "labels": []})
    def walk(el, m, owner):
        for child in el:
            nm = m
            tr = child.get("transform")
            if tr:
                nm = mat_mul(parse_transform(tr), m)
            cid = child.get("data-cell-id")
            if cid:
                found_ids[0] = True
                owner = cid
            tag = child.tag.split("}")[-1]
            if tag == "rect":
                fill = (child.get("fill") or "").lower()
                if fill not in ("none", "") and owner:
                    ensure(owner)["boxes"].append(rect_bbox(child, nm))
            elif tag == "ellipse":
                if owner:
                    ensure(owner)["boxes"].append(ellipse_bbox(child, nm))
            elif tag == "path":
                fill = (child.get("fill") or "").lower()
                pts = path_points(child.get("d", ""), nm)
                if fill not in ("none", ""):
                    if len(pts) >= 5 and owner:
                        ensure(owner)["boxes"].append(poly_bbox(pts))
                else:
                    if len(pts) >= 2 and owner:
                        ensure(owner)["lines"].append(pts)
            elif tag == "div":
                style = child.get("style", "")
                ml = re.search(r"margin-left:\s*([-\d.]+)px", style)
                pt = re.search(r"padding-top:\s*([-\d.]+)px", style)
                dw = re.search(r"width:\s*([\d.]+)px", style)
                jc = re.search(r"justify-content:\s*(?:(unsafe|safe)\s+)?([a-z-]+)", style)
                if ml and pt and owner:
                    text, fs = _harvest(child)
                    ensure(owner)["labels"].append((float(ml.group(1)), float(pt.group(1)), text, fs,
                                                     float(dw.group(1)) if dw else 0.0,
                                                     "left" if jc and jc.group(2) in ("left", "flex-start") else "center"))
            walk(child, nm, owner)
    walk(root, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), None)
    if not found_ids[0]:
        sys.exit("error: SVG carries no data-cell-id - re-export from draw.io "
                 "desktop (plain -f svg is fine); without it shapes cannot be "
                 "mapped back to cells and every check would no-op")
    return cells


def _harvest(el):
    text_parts, fs = [], None
    for desc in el.iter():
        tag = desc.tag.split("}")[-1]
        if tag == "div":
            st = desc.get("style", "")
            mfs = re.search(r"font-size:\s*([\d.]+)px", st)
            if mfs:
                fs = float(mfs.group(1))
        elif tag == "br":
            text_parts.append("\n")
        else:
            if desc.text:
                text_parts.append(desc.text)
            if desc.tail:
                text_parts.append(desc.tail)
    return "".join(text_parts).strip(), fs


# ---------- checks ----------
def _text_size(text, fs):
    if not fs:
        fs = 11.0
    w = 0.0
    for line in text.split("\n"):
        lw = sum(0.55 * fs if ord(ch) < 128 else 1.0 * fs for ch in line)
        w = max(w, lw)
    lines = text.count("\n") + 1
    return w, lines * fs * 1.4 + 4


def _label_rect(ml, pt, dw, text, fs, align="center"):
    """Rendered text rect. draw.io's label div sits at (margin-left,
    padding-top) with the text justified per `align`; the glyphs themselves are
    ~text-estimated wide, not the full div width."""
    w, h = _text_size(text, fs)
    if align == "left":
        return (ml, pt - h / 2, w, h)
    cx = ml + (dw / 2 if dw else 0)
    return (cx - w / 2, pt - h / 2, w, h)


def check(drawio, svg, acyclic):
    vertices, edges = load_topology(drawio)
    cells = collect_svg(svg)

    findings, infos = [], []

    # --- map edge cell -> its drawn line (first stroke-only path with >=3 pts) ---
    edge_lines = {}
    for eid, e in edges.items():
        cell = cells.get(eid, {})
        lines = [pts for pts in cell.get("lines", []) if len(pts) >= 2]
        if lines:
            # longest stroke path is the connector line
            edge_lines[eid] = max(lines, key=lambda p: poly_bbox(p)[2] + poly_bbox(p)[3])

    # --- 1. edge through a box that is not its endpoint ---
    all_boxes = [bb for v in cells.values() for bb in v.get("boxes", [])]
    for eid, pts in edge_lines.items():
        s, t = edges[eid]["source"], edges[eid]["target"]
        for vid, v in vertices.items():
            if v["text"] or vid in (s, t):
                continue
            for bb in cells.get(vid, {}).get("boxes", []):
                if is_container(bb, all_boxes):
                    continue  # edges run inside panels/legends legitimately
                if poly_through_rect(pts, bb, inset=1.5):
                    findings.append(f"FINDING  edge {eid} line passes through vertex {vid} box {tuple(round(x) for x in bb)}")
        # through its OWN endpoints? draw.io clips at boundary; flag only deep cuts
        for vid in (s, t):
            if vid is None:
                continue
            for bb in cells.get(vid, {}).get("boxes", []):
                if poly_through_rect(pts, bb, inset=6.0):
                    findings.append(f"FINDING  edge {eid} line cuts {6}px inside its own {vid} box - arrow looks detached")

    # --- 2. edge through text (labels, notes, titles, captions) ---
    text_rects = []  # (cellid, rect, text)
    for cid, cell in cells.items():
        full = (vertices.get(cid) or {}).get("value") or (edges.get(cid) or {}).get("value") or ""
        for (cx, cy, text, fs, dw, align) in cell.get("labels", []):
            t = full or text
            text_rects.append((cid, _label_rect(cx, cy, dw, t, fs, align), t))
    for eid, pts in edge_lines.items():
        for (cid, tr, text) in text_rects:
            if cid == eid:
                continue
            if poly_through_rect(pts, tr, inset=1.0):
                findings.append(f"FINDING  edge {eid} line passes through text of cell {cid}: '{text[:28]}'")

    # --- 3. edge-edge proper crossings in open space ---
    el = [(eid, pts) for eid, pts in edge_lines.items()]
    for i in range(len(el)):
        for j in range(i + 1, len(el)):
            (ea, pa), (eb, pb) = el[i], el[j]
            for (p1, p2) in zip(pa, pa[1:]):
                for (q1, q2) in zip(pb, pb[1:]):
                    if seg_cross(p1, p2, q1, q2):
                        findings.append(f"FINDING  edges {ea} and {eb} cross at ({ (p1[0]+p2[0])/2:.0f},{(p1[1]+p2[1])/2:.0f})")

    # --- 4. self-intersection (route loops back on itself) ---
    for eid, pts in edge_lines.items():
        for i in range(len(pts) - 1):
            for j in range(i + 2, len(pts) - 1):
                if seg_cross(pts[i], pts[i + 1], pts[j], pts[j + 1]):
                    findings.append(f"FINDING  edge {eid} self-intersects (loop) between seg {i} and {j}")

    # --- 5. (opt-in) directed cycles in the flow graph ---
    if acyclic:
        adj = {v: [] for v in vertices}
        for eid, e in edges.items():
            if e["source"] and e["target"]:
                adj.setdefault(e["source"], []).append(e["target"])
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {v: WHITE for v in vertices}
        stack, cycles = [], []
        def dfs(u):
            color[u] = GRAY
            stack.append(u)
            for w in adj.get(u, []):
                if w not in color:
                    continue
                if color[w] == GRAY:
                    idx = stack.index(w)
                    cycles.append(stack[idx:] + [w])
                elif color[w] == WHITE:
                    dfs(w)
            stack.pop()
            color[u] = BLACK
        for v in vertices:
            if color[v] == WHITE:
                dfs(v)
        if cycles:
            for cyc in cycles:
                findings.append(f"FINDING  directed cycle in flow graph: {' -> '.join(cyc)}")
        else:
            infos.append("INFO  no directed cycle in the flow graph (acyclic)")

    # --- connectivity sanity: each edge's line touches both endpoint boxes ---
    for eid, pts in edge_lines.items():
        s, t = edges[eid]["source"], edges[eid]["target"]
        for end, vid in (("source", s), ("target", t)):
            if vid is None:
                continue
            boxes = cells.get(vid, {}).get("boxes", [])
            if not boxes:
                continue
            # endpoint of the line should sit on/near one of the endpoint boxes;
            # draw.io clips the line ~8px short of the shape at arrow heads
            p = pts[0] if end == "source" else pts[-1]
            near = any(point_in_rect(p, bb, inset=-12) for bb in boxes)
            if not near:
                infos.append(f"INFO  edge {eid} {end} endpoint ({p[0]:.0f},{p[1]:.0f}) not near box {vid}")

    return findings, infos, edge_lines


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Windows GBK console
    except Exception:
        pass
    ap = argparse.ArgumentParser(
        description="Verify a rendered draw.io SVG against the .drawio topology "
                    "using exact drawn paths (render truth without vision).")
    ap.add_argument("drawio", help="source .drawio file")
    ap.add_argument("svg", help="rendered SVG exported by draw.io desktop "
                                "(carries data-cell-id)")
    ap.add_argument("--acyclic", action="store_true",
                    help="also flag directed cycles in the flow graph - opt-in "
                         "because multi-agent / feedback / iterative figures "
                         "legitimately loop; enable for acyclic feedforward "
                         "pipelines")
    ap.add_argument("--strict", action="store_true",
                    help="treat INFO (e.g. endpoint-not-near-box) as failure too")
    args = ap.parse_args()

    findings, infos, edge_lines = check(args.drawio, args.svg, args.acyclic)
    for line in infos:
        print(line)
    for line in findings:
        print(line)
    print(f"\n=== summary: {len(findings)} findings, {len(infos)} info, "
          f"{len(edge_lines)} edges checked ===")
    if findings or (args.strict and infos):
        sys.exit(1)


if __name__ == "__main__":
    main()
