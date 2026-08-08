#!/usr/bin/env python3
"""Deterministic structural linter for hand-written .drawio files
(ccfa-arch-diagram edition, adapted from drawio-skill's validate.py).

Catches the class of mistakes a vision self-check is slow and unreliable at:
dangling edge endpoints, duplicate or reserved ids, broken parent references,
overlapping sibling nodes, container/title-band geometry defects, stacked edge
ports, and (for waypointed edges) routes that cross unrelated vertices or each
other. Runs without launching draw.io - a fast pre-check before export.

  python3 validate.py diagram.drawio
  python3 validate.py diagram.drawio --strict --score

Layout model assumed (this skill writes FLAT files): every cell has
parent="1"; a "container" is an ordinary vertex rect that fully contains other
vertices drawn on top of it. Containment is therefore *not* an overlap
defect - partial overlap (neither rect contains the other) is.

Checks added for this skill's observed failure modes:
  - vertex partially intruding into a container's top title band
    (clipped titles like "GAT Layer 1 …" colliding with member boxes);
  - contained vertex escaping its container's bounds;
  - canvas content wider than ~2200px (thin strokes and small fonts become
    invisible after the --width 2000 preview downscale);
  - two or more edges sharing the same side of the same node with no pinned
    ports or with identical pinned ports ("stacked - run edgeports.py");
  - an edge carrying a text label without labelBackgroundColor (labels float
    over lines/shapes with no backing);
  - an arrow entering a top-titled box's top edge beneath its own title text,
    and routes slicing through other boxes' top titles (containers are exempt
    from the through-vertex check, so their title bands were previously silent).

Edge routing checks (warnings) only apply to edges with explicit waypoints
(<Array as="points">) - the route of an auto-routed edge is computed by
draw.io at render time and not stored in the XML, so checking it would guess.
Endpoints honour exitX/exitY / entryX/entryY when present, else node centre.

Exit status is non-zero when any error (or, with --strict, any warning) is
found, so it can gate the workflow before PNG export.

Usage: python3 validate.py <file.drawio> [--strict] [--score]
"""
import argparse
import math
import sys
import xml.etree.ElementTree as ET

RESERVED = {"0", "1"}
MAX_CONTENT_WIDTH = 2200      # px - wider figures die under preview downscale
TITLE_BAND = 24               # px reserved under a top-titled container
LEGEND_LINE_MAX = 120         # px - legend line samples are short strokes
MIN_MEMBER_MARGIN = 4         # px clearance a member box needs off a container edge
LABEL_PAD = 4                 # px visual padding around a label's text box
A4_LANDSCAPE_W, A4_LANDSCAPE_H = 1122, 794  # px @96dpi - the skill's print target
ASPECT_TOLERANCE = 0.30       # content h/w may deviate up to 30% from page aspect
PAGE_FIT_TOL = 2.0            # px slack when checking content against the page


def rect(cell):
    """Return (x, y, w, h) floats for a cell's geometry, or None if absent/bad."""
    g = cell.find("mxGeometry")
    if g is None:
        return None
    try:
        return (float(g.get("x", "0")), float(g.get("y", "0")),
                float(g.get("width", "nan")), float(g.get("height", "nan")))
    except ValueError:
        return None


def is_text_cell(cell):
    """True for standalone text cells (titles, captions, legend labels)."""
    style = cell.get("style") or ""
    return cell.get("vertex") == "1" and (
        style.startswith("text;") or "text;" in style[:8])


def is_edge_label(cell):
    """True for a draw.io edge label / relative-positioned child vertex."""
    if "edgeLabel" in (cell.get("style") or ""):
        return True
    g = cell.find("mxGeometry")
    return g is not None and g.get("relative") == "1"


def overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def contains(outer, inner):
    """True if rect `outer` fully contains rect `inner` (2px tolerance)."""
    ox, oy, ow, oh = outer
    ix, iy, iw, ih = inner
    return (ix >= ox - 2 and iy >= oy - 2
            and ix + iw <= ox + ow + 2 and iy + ih <= oy + oh + 2)


# --- Style helpers ----------------------------------------------------------

def style_num(style, key):
    """Return float value of ``key=`` in a drawio style string, or None."""
    for part in (style or "").split(";"):
        if part.startswith(key + "="):
            try:
                return float(part.split("=", 1)[1])
            except ValueError:
                return None
    return None


def style_has(style, key):
    return any(p == key or p.startswith(key + "=")
               for p in (style or "").split(";"))


def is_legend_sample(edge):
    """True if a free-standing edge is a legitimate short legend line sample.

    Legend samples are absolute-positioned (both sourcePoint and targetPoint),
    waypoint-free, unlabeled, short strokes. Anything else that reaches here
    (no source/target) is a *dangling* edge: draw.io detaches edges on
    open/save round-trips by dropping source/target and keeping absolute
    points, which is how a previously-connected arrow silently becomes a
    floating line that no longer follows its boxes.
    """
    g = edge.find("mxGeometry")
    if g is None:
        return False
    sp = tp = None
    for p in g.iter("mxPoint"):
        a = p.get("as")
        if a == "sourcePoint":
            try:
                sp = (float(p.get("x")), float(p.get("y")))
            except (TypeError, ValueError):
                return False
        elif a == "targetPoint":
            try:
                tp = (float(p.get("x")), float(p.get("y")))
            except (TypeError, ValueError):
                return False
    if sp is None or tp is None or g.find("Array") is not None:
        return False
    if (edge.get("value") or "").strip():
        return False
    dx, dy = tp[0] - sp[0], tp[1] - sp[1]
    return (dx * dx + dy * dy) ** 0.5 <= LEGEND_LINE_MAX


# --- Edge routing geometry --------------------------------------------------
# Only edges with explicit waypoints have a knowable route; auto-routed edges
# are skipped so these warnings stay free of false positives.

def abs_rect(cell, by_id):
    """Absolute (x, y, w, h) of a vertex, summing parent-container offsets."""
    r = rect(cell)
    if r is None or any(v != v for v in r):
        return None
    x, y, w, h = r
    parent, seen = cell.get("parent"), set()
    while parent and parent in by_id and parent not in seen:
        seen.add(parent)
        p = by_id[parent]
        if p.get("vertex") == "1":
            pr = rect(p)
            if pr and not any(v != v for v in pr):
                x += pr[0]
                y += pr[1]
        parent = p.get("parent")
    return (x, y, w, h)


def endpoint(edge, end, by_id):
    """Absolute (x, y) where ``edge`` meets its source/target vertex."""
    vid = edge.get(end)
    if not vid or vid not in by_id:
        return None
    box = abs_rect(by_id[vid], by_id)
    if box is None:
        return None
    x, y, w, h = box
    style = edge.get("style") or ""
    fx = style_num(style, "exitX" if end == "source" else "entryX")
    fy = style_num(style, "exitY" if end == "source" else "entryY")
    return (x + (fx if fx is not None else 0.5) * w,
            y + (fy if fy is not None else 0.5) * h)


def edge_waypoints(edge):
    """Explicit <Array as="points"> waypoints of an edge as [(x, y), ...]."""
    g = edge.find("mxGeometry")
    if g is None:
        return []
    arr = g.find("Array")
    if arr is None:
        return []
    pts = []
    for pt in arr.findall("mxPoint"):
        px, py = pt.get("x"), pt.get("y")
        if px is not None and py is not None:
            try:
                pts.append((float(px), float(py)))
            except ValueError:
                pass
    return pts


def edge_route(edge, by_id):
    """Absolute polyline for a waypointed edge, or None if auto-routed."""
    waypoints = edge_waypoints(edge)
    if not waypoints:
        return None
    s, t = endpoint(edge, "source", by_id), endpoint(edge, "target", by_id)
    if s is None or t is None:
        return None
    return [s] + waypoints + [t]


def _orient(a, b, c):
    v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return 0 if abs(v) < 1e-9 else (1 if v > 0 else -1)


def segments_cross(p1, p2, p3, p4):
    """True if segments p1p2 and p3p4 properly cross (interior intersection)."""
    o1, o2 = _orient(p1, p2, p3), _orient(p1, p2, p4)
    o3, o4 = _orient(p3, p4, p1), _orient(p3, p4, p2)
    return o1 != o2 and o3 != o4 and 0 not in (o1, o2, o3, o4)


def _point_in_rect(p, box, eps=1e-6):
    x, y, w, h = box
    return x + eps < p[0] < x + w - eps and y + eps < p[1] < y + h - eps


def route_hits_rect(points, box):
    """True if a polyline enters a rectangle's interior or crosses a border."""
    x, y, w, h = box
    corners = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    borders = list(zip(corners, corners[1:] + corners[:1]))
    for a, b in zip(points, points[1:]):
        if _point_in_rect(a, box) or _point_in_rect(b, box):
            return True
        if any(segments_cross(a, b, c, d) for c, d in borders):
            return True
    return False


def routes_cross(pa, pb):
    """True if any segment of polyline pa properly crosses any of pb."""
    for a1, a2 in zip(pa, pa[1:]):
        for b1, b2 in zip(pb, pb[1:]):
            if segments_cross(a1, a2, b1, b2):
                return True
    return False


# --- Page checks ------------------------------------------------------------

def _side_of(edge, end, by_id):
    """Which side (N/S/E/W) of the node this edge end leaves/enters, if
    knowable: from pinned ports first, else from the peer's position."""
    style = edge.get("style") or ""
    px = style_num(style, "exitX" if end == "source" else "entryX")
    py = style_num(style, "exitY" if end == "source" else "entryY")
    if px is not None and py is not None:
        if px == 0:
            return "W", (px, py)
        if px == 1:
            return "E", (px, py)
        if py == 0:
            return "N", (px, py)
        if py == 1:
            return "S", (px, py)
        return None, (px, py)        # pinned interior point - still a slot
    me_id = edge.get(end)
    peer_id = edge.get("target" if end == "source" else "source")
    if me_id not in by_id or peer_id not in by_id:
        return None, None
    me, peer = abs_rect(by_id[me_id], by_id), abs_rect(by_id[peer_id], by_id)
    if not me or not peer:
        return None, None
    mcx, mcy = me[0] + me[2] / 2, me[1] + me[3] / 2
    pcx, pcy = peer[0] + peer[2] / 2, peer[1] + peer[3] / 2
    dx, dy = pcx - mcx, pcy - mcy
    if abs(dx) >= abs(dy):
        return ("E" if dx >= 0 else "W"), None
    return ("S" if dy >= 0 else "N"), None


def _direction_bucket(by_id, node_id, peer_id):
    """Dominant direction (N/S/E/W) from node centre to peer centre."""
    if node_id not in by_id or peer_id not in by_id:
        return None
    me, peer = abs_rect(by_id[node_id], by_id), abs_rect(by_id[peer_id], by_id)
    if not me or not peer:
        return None
    dx = (peer[0] + peer[2] / 2) - (me[0] + me[2] / 2)
    dy = (peer[1] + peer[3] / 2) - (me[1] + me[3] / 2)
    if abs(dx) >= abs(dy):
        return "E" if dx >= 0 else "W"
    return "S" if dy >= 0 else "N"


def port_stacking_warnings(cells, by_id):
    """Warn when 2+ edges share the same side of the same node and will stack:

    - any unpinned ends in the group (floating connections all land on the
      side's centre) -> "run edgeports.py";
    - pinned ends on identical slots whose far endpoints approach from the
      SAME direction (parallel overlap). Edges converging on one slot from
      opposite directions (a fork/merge into an op circle) are intentional
      and not flagged.
    """
    warns = []
    groups = {}
    for e in cells:
        if e.get("edge") != "1":
            continue
        for end in ("source", "target"):
            node = e.get(end)
            if not node:
                continue
            side, slot = _side_of(e, end, by_id)
            if side is None:
                continue
            peer = e.get("target" if end == "source" else "source")
            groups.setdefault((node, side), []).append((e.get("id"), slot, peer))
    for (node, side), ends in sorted(groups.items()):
        if len(ends) < 2:
            continue
        if any(s is None for _, s, _ in ends):
            warns.append(
                f"{len(ends)} edges share node {node!r} side {side} with "
                f"unpinned ports - they stack at one point; run edgeports.py")
            continue
        slots = {}
        for eid, s, peer in ends:
            slots.setdefault(s, []).append(peer)
        for slot, peers in sorted(slots.items()):
            if len(peers) < 2:
                continue
            buckets = [_direction_bucket(by_id, node, p) for p in peers]
            if len(set(buckets)) < len(buckets):
                warns.append(
                    f"edges on node {node!r} side {side} pin identical port "
                    f"{slot} with same-direction peers - lines overlap along "
                    f"their run; re-spread exit/entry slots")
    return warns


def collinear_entry_warnings(cells, by_id):
    """Waypointed edges must approach the target perpendicular to its edge.

    A hand-authored last waypoint that shares the entry axis with the target
    edge - top/bottom entry with the final waypoint at the same y, or left/
    right entry with the same x - makes the arrow run ALONG the box border and
    stop. It still connects in the XML, but renders as "not connected". The
    fix is to keep the last waypoint offset so the final segment drops/enters
    perpendicularly. Auto-routed edges are skipped: draw.io picks a
    perpendicular approach at render time.
    """
    warns = []
    for c in cells:
        if c.get("edge") != "1":
            continue
        wps = edge_waypoints(c)
        if not wps:
            continue
        tid = c.get("target")
        if not tid or tid not in by_id:
            continue
        box = abs_rect(by_id[tid], by_id)
        if not box:
            continue
        x, y, w, h = box
        entry = endpoint(c, "target", by_id)
        if entry is None:
            continue
        ex, ey = entry
        lx, ly = wps[-1]
        if abs(lx - ex) < 0.6 and abs(ly - ey) < 0.6:
            continue  # last waypoint sits exactly on the entry - degenerate
        style = c.get("style") or ""
        exv, eyv = style_num(style, "entryX"), style_num(style, "entryY")
        eid = c.get("id")
        if eyv == 0 and abs(ly - y) < 0.6:
            warns.append(
                f"edge {eid!r} slides along target {tid!r}'s top edge (last "
                f"waypoint collinear with the entry) - arrow reads as "
                f"unconnected; drop the last waypoint to y<{int(y)} so it "
                f"enters vertically")
        elif eyv == 1 and abs(ly - (y + h)) < 0.6:
            warns.append(
                f"edge {eid!r} slides along target {tid!r}'s bottom edge - "
                f"arrow reads as unconnected; lower the last waypoint below "
                f"the box")
        elif exv == 0 and abs(lx - x) < 0.6:
            warns.append(
                f"edge {eid!r} slides along target {tid!r}'s left edge - "
                f"arrow reads as unconnected; move the last waypoint left of "
                f"the box")
        elif exv == 1 and abs(lx - (x + w)) < 0.6:
            warns.append(
                f"edge {eid!r} slides along target {tid!r}'s right edge - "
                f"arrow reads as unconnected; move the last waypoint right of "
                f"the box")
    return warns


def style_value(style, key):
    """Return the raw value of ``key=`` in a style string, or None."""
    for part in (style or "").split(";"):
        if part.startswith(key + "="):
            return part.split("=", 1)[1]
    return None


def label_width(value, style):
    """Estimated rendered width (px) of an edge label at its fontSize.

    Times New Roman: Latin/digit ≈ 0.55em, CJK ≈ 1.0em. Conservative on the
    high side so an over-wide label is flagged rather than silently missed.
    """
    fs = style_num(style, "fontSize") or 10.0
    width = 0.0
    for line in (value or "").split("\n"):
        line_w = sum(0.55 * fs if ord(ch) < 128 else 1.0 * fs for ch in line)
        width = max(width, line_w)
    return width + LABEL_PAD


def label_height(value, style):
    """Estimated rendered height (px) of an edge label.

    Used for vertical edges: the label sits in the vertical gap between two
    stacked boxes, so the extent that matters is height (one line ≈ 1.4em).
    """
    fs = style_num(style, "fontSize") or 10.0
    lines = (value or "").split("\n")
    return len(lines) * fs * 1.4 + LABEL_PAD


def edge_label_point(edge, by_id):
    """Approximate point where an edge label renders: the polyline midpoint."""
    pts = edge_route(edge, by_id)
    if pts is None:
        s, t = endpoint(edge, "source", by_id), endpoint(edge, "target", by_id)
        if s is None or t is None:
            return None
        pts = [s, t]
    segs, total = [], 0.0
    for a, b in zip(pts, pts[1:]):
        length = math.hypot(b[0] - a[0], b[1] - a[1])
        segs.append((a, b, length))
        total += length
    if total <= 0:
        return pts[0]
    half, acc = total / 2.0, 0.0
    for a, b, length in segs:
        if acc + length >= half:
            frac = (half - acc) / length if length > 0 else 0.0
            return (a[0] + (b[0] - a[0]) * frac, a[1] + (b[1] - a[1]) * frac)
        acc += length
    return pts[0]


def label_gap_warnings(cells, by_id):
    """Labeled straight edges must not be wider than the gap they sit in.

    A label is centred on the edge's midpoint, i.e. the middle of the space
    between the two boxes. If the text is wider than that gap it overruns both
    boxes - the classic "text stamped on the boxes" look. Waypointed edges are
    skipped (their labels float in corridors / on empty canvas where width is
    unconstrained); an explicit label offset means the author already moved the
    label somewhere deliberate.
    """
    warns = []
    for c in cells:
        if c.get("edge") != "1":
            continue
        value = (c.get("value") or "").strip()
        if not value:
            continue
        if edge_waypoints(c):
            continue  # label lives in a corridor, not between the two boxes
        g = c.find("mxGeometry")
        if g is not None and any(p.get("as") == "offset"
                                 for p in g.iter("mxPoint")):
            continue  # label deliberately moved elsewhere
        s_id, t_id = c.get("source"), c.get("target")
        if not s_id or not t_id or s_id not in by_id or t_id not in by_id:
            continue
        sb, tb = abs_rect(by_id[s_id], by_id), abs_rect(by_id[t_id], by_id)
        if not sb or not tb:
            continue
        scx, scy = sb[0] + sb[2] / 2, sb[1] + sb[3] / 2
        tcx, tcy = tb[0] + tb[2] / 2, tb[1] + tb[3] / 2
        horizontal = abs(tcx - scx) >= abs(tcy - scy)
        if horizontal:
            # boxes must be roughly side-by-side (y-intervals overlap), else
            # the label is diagonally offset and the x-clearance is not the
            # space it actually floats in.
            if not (sb[1] < tb[1] + tb[3] and tb[1] < sb[1] + sb[3]):
                continue
            gap = abs(tcx - scx) - (sb[2] + tb[2]) / 2
            extent = label_width(value, c.get("style") or "")
            what = "wide"
        else:
            # Stacked boxes: the label sits in the vertical gap, so it stamps
            # the boxes only when taller than the gap (width is irrelevant -
            # nothing sits beside it inside the gap band).
            if not (sb[0] < tb[0] + tb[2] and tb[0] < sb[0] + sb[2]):
                continue
            gap = abs(tcy - scy) - (sb[3] + tb[3]) / 2
            extent = label_height(value, c.get("style") or "")
            what = "tall"
        if extent > gap:
            warns.append(
                f"edge {c.get('id')!r} label is ~{extent:g}px {what} but the "
                f"gap between boxes {s_id!r} and {t_id!r} is only {gap:g}px - "
                f"text will stamp over the boxes; shorten the label or widen "
                f"the gap (or give the label an explicit offset)")
    return warns


def edge_label_rect(edge, by_id):
    """Approximate rendered rect of an edge label, or None if it has none.

    Centre = polyline midpoint + explicit offset point (if any); size from the
    conservative width/height estimators. Used to keep arrows out of other
    arrows' labels.
    """
    value = (edge.get("value") or "").strip()
    if not value:
        return None
    center = edge_label_point(edge, by_id)
    if center is None:
        return None
    g = edge.find("mxGeometry")
    if g is not None:
        for p in g.iter("mxPoint"):
            if p.get("as") == "offset":
                try:
                    ox, oy = float(p.get("x")), float(p.get("y"))
                except (TypeError, ValueError):
                    ox = oy = 0.0
                center = (center[0] + ox, center[1] + oy)
                break
    style = edge.get("style") or ""
    w = label_width(value, style)
    h = label_height(value, style)
    return (center[0] - w / 2, center[1] - h / 2, w, h)


def arrow_through_text_warnings(cells, by_id):
    """No arrow may slice through the middle of a text label.

    draw.io paints edge labels and standalone text cells (titles, captions,
    legend labels) over the canvas. An arrow whose polyline runs through such a
    rect makes the text unreadable - the "字" in "箭头从字中间穿过". Every edge
    with a knowable route is checked against every OTHER edge's label rect and
    every standalone text cell. Auto-routed edges are checked with their straight
    endpoint line only when axis-aligned (the orthogonal path of a diagonal
    cannot be known without rendering); waypointed edges use the stored route.
    """
    warns = []
    text_rects = []
    for c in cells:
        if is_text_cell(c):
            r = abs_rect(c, by_id)
            if r:
                text_rects.append((c.get("id"), r))
    label_rects = {}
    for c in cells:
        if c.get("edge") == "1":
            r = edge_label_rect(c, by_id)
            if r:
                label_rects[c.get("id")] = r
    for c in cells:
        if c.get("edge") != "1":
            continue
        eid = c.get("id")
        pts = edge_route(c, by_id)
        if pts is None:
            s, t = endpoint(c, "source", by_id), endpoint(c, "target", by_id)
            if s is None or t is None:
                continue
            if abs(s[0] - t[0]) > 0.5 and abs(s[1] - t[1]) > 0.5:
                continue  # auto-routed diagonal: real Manhattan path unknowable
            pts = [s, t]
        for other_id, rect_ in label_rects.items():
            if other_id == eid:
                continue
            if route_hits_rect(pts, rect_):
                warns.append(f"edge {eid!r} route passes through the label of "
                             f"edge {other_id!r}")
        for tid, rect_ in text_rects:
            if route_hits_rect(pts, rect_):
                warns.append(f"edge {eid!r} route passes through text cell "
                             f"{tid!r}")
    return warns


def title_rect(cell, by_id):
    """Approximate rect of a box's top title text, or None if not top-titled.

    A box carries a top title when its style says verticalLabelPosition=top
    AND it has a non-empty value. draw.io centres such titles in the top band
    by default; align=left/right moves the text block to that side. This is
    the rect the "no arrow through the title" rule keeps arrows out of.
    """
    style = cell.get("style") or ""
    if "verticalLabelPosition=top" not in style:
        return None
    value = (cell.get("value") or "").strip()
    if not value:
        return None
    r = abs_rect(cell, by_id)
    if r is None:
        return None
    x, y, w, _h = r
    fs = style_num(style, "fontSize") or 12.0
    tw = label_width(value, style)
    th = fs * 1.4 + LABEL_PAD
    align = style_value(style, "align")
    if align == "left":
        cx = x + 4
    elif align == "right":
        cx = x + w - 4 - tw
    else:
        cx = x + w / 2
    return (cx - tw / 2, y, tw, th)


def text_cell_titles(cell, by_id):
    """Title rects carried as separate text cells inside a box's top band.

    This skill's proven panel idiom draws the box with value="" and paints the
    title as a standalone text cell tucked into the box's top edge (see
    examples/framework_bands.drawio). draw.io renders such cells exactly where
    they sit - no floating labels - but their top-edge entries still deserve
    the same "no arrow through the title" clearance as a label-titled box.
    Returns every text cell fully inside ``cell`` and within 28px of its top.
    """
    r = abs_rect(cell, by_id)
    if r is None:
        return []
    bx, by, bw, bh = r
    rects = []
    for c in by_id.values():
        if c is cell or c.get("vertex") != "1" or not is_text_cell(c):
            continue
        cr = abs_rect(c, by_id)
        if cr is None:
            continue
        cx, cy, cw, ch = cr
        if (cx >= bx - 0.5 and cx + cw <= bx + bw + 0.5
                and cy >= by - 0.5 and cy + ch <= by + bh + 0.5
                and cy < by + 28):
            rects.append((cx, cy, cw, ch))
    return rects


def title_clearance_warnings(cells, by_id):
    """No arrow may point into - or slice through - a box's top title text.

    draw.io paints a top-titled container's title in the top band, centred on
    the box. An arrow entering that box's TOP edge with its port under the
    title points straight at the text (the "箭头从图框顶部标题字上穿过" look), and
    an arrow passing by can slice through another box's title band. Two
    checks, using the estimated title-text rect for every top-titled box:

    - an edge entering a top-titled target's TOP edge must land outside the
      title's horizontal span (or the title must be shifted off-centre);
      a value="" box whose title is a separate text cell in the top band gets
      the same clearance (text_cell_titles);
    - a knowable route must not pass through the title text rect of a box it
      does not connect to (containers are exempt from the through-vertex check,
      so their title bands would otherwise pass silently).
    """
    warns = []
    titled = {}
    text_titled = {}
    for c in cells:
        if c.get("vertex") == "1" and not is_edge_label(c):
            tr = title_rect(c, by_id)
            if tr:
                titled[c.get("id")] = tr
            trs = text_cell_titles(c, by_id)
            if trs:
                text_titled[c.get("id")] = trs
    for c in cells:
        if c.get("edge") != "1":
            continue
        eid = c.get("id")
        pts = edge_route(c, by_id)
        if pts is None:
            s, t = endpoint(c, "source", by_id), endpoint(c, "target", by_id)
            if s is None or t is None:
                continue
            if abs(s[0] - t[0]) > 0.5 and abs(s[1] - t[1]) > 0.5:
                continue  # diagonal auto-route: Manhattan path unknowable
            pts = [s, t]
        tid = c.get("target")
        if tid and style_num(c.get("style") or "", "entryY") == 0:
            entry = endpoint(c, "target", by_id)
            if entry is not None:
                trs = ([titled[tid]] if tid in titled else []) \
                    + list(text_titled.get(tid, []))
                for tr in trs:
                    if tr[0] - 0.5 <= entry[0] <= tr[0] + tr[2] + 0.5:
                        warns.append(
                            f"edge {eid!r} enters titled box {tid!r}'s top edge "
                            f"beneath its own title text - the arrow points into "
                            f"the title; shift the title off-centre or move the "
                            f"entry port clear of it")
                        break
        for bid, tr in titled.items():
            if bid in (c.get("source"), c.get("target")):
                continue
            if route_hits_rect(pts, tr):
                warns.append(
                    f"edge {eid!r} route passes through the top title of box "
                    f"{bid!r} - re-route so the arrow clears the title text")
    return warns


def page_fit_warnings(page_w, page_h, cells, by_id):
    """Content must fit the declared paper; aspect is only checked when it
    actually fills the page.

    Every file in this skill ships an explicit mxGraphModel pageWidth/pageHeight.
    The canonical print target is A4 landscape (1122x794 px @96dpi). Content
    inside the page is fine (it leaves a margin), but content must not overflow
    the page. The aspect check (h/w within 30% of the page) applies ONLY to
    page-filling figures (>= 70% of both page dimensions): a compact figure -
    in a real paper a figure is at most 1/3 of a page, so letterbox margins are
    the norm - is free to be any shape. That still catches a landscape figure
    accidentally declared full-page on a portrait page (and vice versa) without
    banning compact corner figures.
    """
    if page_w is None or page_h is None:
        return [f"no pageWidth/pageHeight declared - A4 fit cannot be "
                f"guaranteed; add pageWidth={A4_LANDSCAPE_W:g} "
                f"pageHeight={A4_LANDSCAPE_H:g} (A4 landscape)"]
    try:
        page_w, page_h = float(page_w), float(page_h)
    except (TypeError, ValueError):
        return [f"pageWidth/pageHeight not numeric - A4 fit cannot be guaranteed"]
    xs, ys, xe, ye = [], [], [], []
    for c in cells:
        if c.get("vertex") == "1" and not is_edge_label(c):
            r = abs_rect(c, by_id)
            if r:
                xs.append(r[0]); ys.append(r[1])
                xe.append(r[0] + r[2]); ye.append(r[1] + r[3])
    if not xs:
        return []
    cw, ch = max(xe) - min(xs), max(ye) - min(ys)
    warns = []
    if min(xs) < -PAGE_FIT_TOL or min(ys) < -PAGE_FIT_TOL \
            or max(xe) > page_w + PAGE_FIT_TOL or max(ye) > page_h + PAGE_FIT_TOL:
        warns.append(f"content {cw:g}x{ch:g} overflows the declared page "
                     f"{page_w:g}x{page_h:g} - shrink or shift so the figure "
                     f"sits inside the paper")
    if cw > 0:
        if cw >= 0.7 * page_w and ch >= 0.7 * page_h:
            page_aspect = page_h / page_w
            content_aspect = ch / cw
            dev = abs(content_aspect - page_aspect) / page_aspect
            if dev > ASPECT_TOLERANCE:
                warns.append(
                    f"content aspect {content_aspect:.2f} (h/w) deviates from page "
                    f"aspect {page_aspect:.2f} by {dev * 100:.0f}% "
                    f"(>{ASPECT_TOLERANCE * 100:.0f}%) - a page-filling figure "
                    f"will look like a letterbox banner on {page_w:g}x{page_h:g}; "
                    f"rebalance rows/columns or declare the real page size")
    return warns


def label_bg_warnings(cells, by_id):
    """A label sitting on a tinted panel must carry the panel's fill colour.

    The guide requires every labeled edge to have labelBackgroundColor; on the
    white canvas that background is #FFFFFF. But when the label's midpoint lands
    inside a tinted container, a white label box floats as an abrupt white slab
    on the coloured panel. The label background must then match the container's
    fillColor instead. Labels on the plain canvas (no container under the
    point) and on white containers keep the default #FFFFFF.
    """
    verts = [(c.get("id"), abs_rect(c, by_id), c) for c in cells
             if c.get("vertex") == "1" and not is_edge_label(c)
             and not is_text_cell(c)]
    verts = [(vid, box, c) for vid, box, c in verts if box]
    containers = [(vid, box, c) for vid, box, c in verts
                  if any(v2 != vid and b2 and contains(box, b2) for v2, b2, _ in verts)]
    warns = []
    for c in cells:
        if c.get("edge") != "1":
            continue
        if not (c.get("value") or "").strip():
            continue
        pt = edge_label_point(c, by_id)
        if pt is None:
            continue
        innermost = None  # (container_cell, area) - smallest wins
        for vid, box, cc in containers:
            x, y, w, h = box
            if (x - 0.001 <= pt[0] <= x + w + 0.001
                    and y - 0.001 <= pt[1] <= y + h + 0.001):
                if innermost is None or w * h < innermost[1]:
                    innermost = (cc, w * h)
        if innermost is None:
            continue
        ccell = innermost[0]
        fill = style_value(ccell.get("style") or "", "fillColor")
        if not fill or fill.upper() == "#FFFFFF":
            continue
        lbg = style_value(c.get("style") or "", "labelBackgroundColor")
        if lbg is None:
            continue  # missing bg already flagged by the label-bg rule
        if lbg.upper() != fill.upper():
            warns.append(
                f"edge {c.get('id')!r} label sits on tinted container "
                f"{ccell.get('id')!r} (fill {fill}) but labelBackgroundColor "
                f"is {lbg} - the white slab looks abrupt on the panel; set "
                f"labelBackgroundColor={fill}")
    return warns


def geometry_warnings(cells, ids, parents):
    """Edge-through-vertex and edge-crossing warnings for waypointed edges."""
    warns = []
    routed = []
    for c in cells:
        if c.get("edge") == "1":
            pts = edge_route(c, ids)
            if pts:
                routed.append((c.get("id"), pts,
                               {c.get("source"), c.get("target")}))
    # In this skill's flat layout a "container" is a plain vertex that fully
    # contains other vertices; an edge between two members legitimately runs
    # inside it. Only vertices containing nothing ("leaves") are obstacles.
    allv = [(c.get("id"), abs_rect(c, ids)) for c in cells
            if c.get("vertex") == "1" and not is_edge_label(c)
            and not is_text_cell(c)]
    allv = [(vid, box) for vid, box in allv if box]
    containers = {vid for vid, box in allv
                  if any(v2 != vid and contains(box, b2) for v2, b2 in allv)}
    leaves = [(vid, box) for vid, box in allv if vid not in containers]
    for eid, pts, ends in routed:
        for vid, box in leaves:
            if vid not in ends and route_hits_rect(pts, box):
                warns.append(f"edge {eid!r} routes through vertex {vid!r}")
    for i in range(len(routed)):
        for j in range(i + 1, len(routed)):
            (ia, pa, _), (ib, pb, _) = routed[i], routed[j]
            if routes_cross(pa, pb):
                warns.append(f"edges {ia!r} and {ib!r} cross")
    return warns


def container_warnings(cells):
    """Flat-layout container geometry checks.

    A "container" here is any leaf-or-not vertex rect that fully contains at
    least one other vertex rect. Members must stay inside the container and
    clear of its top title band (when the container uses a top-aligned label).
    """
    warns = []
    verts = [(c.get("id"), rect(c), c) for c in cells
             if c.get("vertex") == "1" and rect(c)
             and not any(v != v for v in rect(c))
             and not is_edge_label(c)]
    boxes = [(vid, r) for vid, r, _ in verts]
    containers = [(vid, r, c) for vid, r, c in verts
                  if any(v2 != vid and contains(r, r2) for v2, r2 in boxes)]
    for cid, cr, ccell in containers:
        cx, cy, cw, ch = cr
        style = ccell.get("style") or ""
        # Title band exists only when the container carries its own top label;
        # full-width members (dark header bars, form 3) legitimately sit there.
        # verticalLabelPosition=top is the semantic marker of a top-titled
        # container (covers both verticalAlign=top and verticalAlign=bottom).
        top_titled = ("verticalLabelPosition=top" in style
                      and bool((ccell.get("value") or "").strip()))
        for vid, vr in boxes:
            if vid == cid:
                continue
            vx, vy, vw, vh = vr
            inside_x = vx >= cx - 2 and vx + vw <= cx + cw + 2
            inside_y = vy >= cy - 2 and vy + vh <= cy + ch + 2
            if inside_x and inside_y:
                # 6px tolerance: legend first rows etc. may sit just under the
                # band; only flag intrusions deep enough to visibly clip text.
                if top_titled and vw < cw - 4 and vy < cy + TITLE_BAND - 6:
                    warns.append(
                        f"vertex {vid!r} intrudes into container {cid!r}'s "
                        f"top title band ({TITLE_BAND}px) - title will clip; "
                        f"move member down or enlarge container")
                # A member must not sit glued to the container's border: it
                # reads as cramped/overlapping even though it is technically
                # inside. Full-width/height members (dark header bars, form 3)
                # legitimately span the container edge - skip those. Text cells
                # (bottom italic titles, legend notes) sit on borders by design.
                if (vw < cw - 4 and vh < ch - 4
                        and not is_text_cell(cells_by_id(cells, vid))):
                    m = MIN_MEMBER_MARGIN
                    touches = []
                    if vx - cx < m:
                        touches.append("left")
                    if (cx + cw) - (vx + vw) < m:
                        touches.append("right")
                    if (cy + ch) - (vy + vh) < m:
                        touches.append("bottom")
                    if not top_titled and vy - cy < m:
                        touches.append("top")
                    if touches:
                        warns.append(
                            f"member {vid!r} touches container {cid!r}'s "
                            f"{'/'.join(touches)} border - leave >= {m:g}px "
                            f"margin so the box does not look glued to the "
                            f"panel edge")
            elif overlap(cr, vr) and not contains(vr, cr):
                # straddles the container border: half in, half out (sub-4px
                # grazes ignored, same as the sibling-overlap check)
                iw = min(cx + cw, vx + vw) - max(cx, vx)
                ih = min(cy + ch, vy + vh) - max(cy, vy)
                if iw > 4 and ih > 4 and not is_text_cell(cells_by_id(cells, vid)):
                    warns.append(
                        f"vertex {vid!r} straddles container {cid!r}'s border "
                        f"- place it fully inside or fully outside")
    return warns


def cells_by_id(cells, cid):
    for c in cells:
        if c.get("id") == cid:
            return c
    return None


def check_page(diagram):
    """Return (errors, warnings) for one <diagram> page."""
    name = diagram.get("name", "?")
    model = diagram.find("mxGraphModel")
    if model is None:
        if (diagram.text or "").strip():
            return [], [f"page {name!r}: compressed, skipped (cannot lint)"]
        return [f"page {name!r}: no <mxGraphModel>"], []
    root = model.find("root")
    cells = []
    for child in (root if root is not None else []):
        if child.tag == "mxCell":
            cells.append(child)
        elif child.tag in ("UserObject", "object"):
            inner = child.find("mxCell")
            if inner is not None:
                inner.set("id", child.get("id", ""))
                cells.append(inner)
    errors, warns = [], []
    ids = {}
    for c in cells:
        cid = c.get("id")
        if cid in ids:
            errors.append(f"duplicate id {cid!r}")
        ids[cid] = c
    parents = {c.get("parent") for c in cells}
    for c in cells:
        cid, parent = c.get("id"), c.get("parent")
        is_v, is_e = c.get("vertex") == "1", c.get("edge") == "1"
        if parent is not None and parent not in ids:
            errors.append(f"cell {cid!r} parent {parent!r} does not exist")
        for end in ("source", "target"):
            ref = c.get(end)
            if ref and ref not in ids:
                errors.append(f"edge {cid!r} {end} {ref!r} does not exist")
        if (is_v or is_e) and cid in RESERVED:
            errors.append(f"cell {cid!r} reuses reserved id 0/1")
        if is_e and not c.get("source") and not c.get("target"):
            # Free-standing edges are ONLY legitimate as short legend line
            # samples. draw.io detaches edges on open/save round-trips
            # (drops source/target, keeps absolute points) - so any other
            # free-standing edge is a broken connection, not a legend.
            if not is_legend_sample(c):
                errors.append(
                    f"edge {cid!r} is detached (no source/target) and not a "
                    f"legend line sample - reconnect it to both endpoints")
        elif is_e and bool(c.get("source")) != bool(c.get("target")):
            warns.append(
                f"edge {cid!r} has only one endpoint connected - dangling; "
                f"reconnect the missing end")
        if is_e and (c.get("value") or "").strip() \
                and not style_has(c.get("style"), "labelBackgroundColor"):
            warns.append(
                f"edge {cid!r} has a label but no labelBackgroundColor - "
                f"text floats over lines; add labelBackgroundColor=#FFFFFF")
        if is_v and not is_edge_label(c):
            r = rect(c)
            if r is None or any(v != v for v in r):
                errors.append(f"vertex {cid!r} has missing/invalid geometry")
            else:
                x, y, w, h = r
                if w <= 0 or h <= 0:
                    warns.append(f"vertex {cid!r} non-positive size {w:g}x{h:g}")
                if x < 0 or y < 0:
                    warns.append(f"vertex {cid!r} negative position ({x:g},{y:g})")
    # Sibling overlap: partial overlap only - in this skill's flat layout a
    # container legitimately contains its members, and text cells legitimately
    # sit on container borders (bottom italic titles, dark header bars).
    # Sub-4px grazes (rounding, op circles straddling a border) are ignored.
    boxes = [(c.get("id"), rect(c)) for c in cells
             if c.get("vertex") == "1" and rect(c)
             and not any(v != v for v in rect(c))
             and not is_edge_label(c) and not is_text_cell(c)]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            (ia, ra), (ib, rb) = boxes[i], boxes[j]
            if not overlap(ra, rb) or contains(ra, rb) or contains(rb, ra):
                continue
            iw = min(ra[0] + ra[2], rb[0] + rb[2]) - max(ra[0], rb[0])
            ih = min(ra[1] + ra[3], rb[1] + rb[3]) - max(ra[1], rb[1])
            if iw > 4 and ih > 4:
                warns.append(f"vertices {ia!r} and {ib!r} overlap "
                             f"({iw:g}x{ih:g}px)")
    warns += container_warnings(cells)
    warns += geometry_warnings(cells, ids, parents)
    warns += port_stacking_warnings(cells, ids)
    warns += collinear_entry_warnings(cells, ids)
    warns += label_gap_warnings(cells, ids)
    warns += label_bg_warnings(cells, ids)
    warns += arrow_through_text_warnings(cells, ids)
    warns += title_clearance_warnings(cells, ids)
    warns += page_fit_warnings(model.get("pageWidth"), model.get("pageHeight"),
                               cells, ids)
    # Content width cap: beyond ~2200px the --width 2000 preview downscale
    # makes 1.2px strokes and 10-12px fonts illegible.
    max_x = 0.0
    for c in cells:
        r = abs_rect(c, ids) if c.get("vertex") == "1" else None
        if r:
            max_x = max(max_x, r[0] + r[2])
    if max_x > MAX_CONTENT_WIDTH:
        warns.append(
            f"content is {max_x:g}px wide (>{MAX_CONTENT_WIDTH}) - preview "
            f"downscale will make strokes/fonts illegible; shrink column "
            f"gaps, switch direction, or split into (a)(b) panels")
    return errors, warns


def main():
    ap = argparse.ArgumentParser(
        description="Lint a hand-written .drawio file for structural errors.")
    ap.add_argument("file")
    ap.add_argument("--strict", action="store_true",
                    help="treat warnings as failure too")
    ap.add_argument("--score", action="store_true",
                    help="also print a readability score (lower is better) - "
                         "useful for comparing layout variants of the same graph")
    args = ap.parse_args()
    try:
        tree = ET.parse(args.file)
    except (ET.ParseError, OSError) as exc:
        sys.exit(f"error: cannot parse {args.file}: {exc}")
    pages = tree.getroot().findall("diagram") or [tree.getroot()]
    errors, warns = [], []
    for page in pages:
        e, w = check_page(page)
        errors += e
        warns += w
    for w in warns:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    print(f"{len(errors)} error(s), {len(warns)} warning(s)")
    if args.score:
        through = sum(1 for w in warns if "routes through" in w)
        cross = sum(1 for w in warns if " cross" in w)
        olap = sum(1 for w in warns if " overlap" in w)
        stack = sum(1 for w in warns if "stack" in w or "ports" in w)
        print(f"score: {20 * through + 10 * cross + 5 * olap + 3 * stack} "
              f"({through} through-vertex, {cross} crossings, {olap} overlaps, "
              f"{stack} port-stack)")
    if errors or (args.strict and warns):
        sys.exit(1)


if __name__ == "__main__":
    main()
