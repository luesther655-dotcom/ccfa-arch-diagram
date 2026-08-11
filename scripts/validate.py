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
  python3 validate.py unet.drawio --recipe symmetric_u   # + archetype invariants
  python3 validate.py ddpm.drawio --acyclic              # + flow-cycle check (opt-in)

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
    from the through-vertex check, so their title bands were previously silent);
  - waypointed arrows that are not straight when they could be (a collinear
    redundant waypoint; aligned endpoints with an unblocked straight connector
    yet routed with waypoints);
  - uneven or excessive spacing between boxes in a lane/column (a stray hole, a
    cramped pair, or a lane spread into islands of whitespace);
  - a waypointed arrow whose own route folds back and crosses itself (a
    self-intersecting loop knot - the "arrow loops back on itself" look);
  - the directed flow graph (arrows as source->target edges) containing a
    cycle - an accidental backward connection closing a loop. Opt-in via
    --acyclic: multi-agent collaboration, RL/evolution loops and feedback
    edges legitimately cycle, so this invariant is only true for feedforward
    pipelines.

Edge routing checks (warnings) use explicit waypoints (<Array as="points">)
when present; waypoint-free orthogonal edges get an expected Manhattan
Z-route through the pinned exit/entry points (auto_ortho_route), an
approximation of draw.io's render-time routing that catches the common
"edge slices a sibling box" defect. Diagonal auto-routed edges are skipped -
their route cannot be guessed. Endpoints honour exitX/exitY / entryX/entryY
when present, else node centre.

Exit status is non-zero when any error (or, with --strict, any warning) is
found, so it can gate the workflow before PNG export.

Usage: python3 validate.py <file.drawio> [--strict] [--score]
"""
import argparse
import json
import math
import os
import re
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

# Semantic / intent invariants (the "needs 目检" classes). Each promotes a rule
# from the guide into a deterministic check, so a rendered PNG is not needed to
# spot the defect class it covers.
THROUGH_EPS = 0.6             # px - treat two points as coincident below this
CORRIDOR_CENTER_TOL = 10      # px - U-bottleneck may deviate from corridor centre
CORRIDOR_BELOW_SLACK = 4      # px - bottleneck centre must hang below the arms
MIRROR_TOL = 8                # px - mirrored arm members must be level within this
SKIP_HORIZONTAL_TOL = 4       # px - a skip edge's two ends share a height within this
TEXT_FIT_SLACK = 3            # px - estimated text block may exceed the box by this

# Straightness / spacing quality invariants (the "needs 目检" feel rules). These
# turn the guide's "arrows straight unless they must dodge" and "boxes tightly
# and uniformly spaced" preferences into deterministic warnings.
ALIGN_EPS = 1.0              # px - endpoints within this of the same x/y = aligned
COLLINEAR_EPS = 0.5          # px^2 - cross product below this = redundant waypoint
GAP_RATIO_HI = 2.0           # interior gap >= this x the lane median -> a stray hole
GAP_ABS_FLOOR = 40           # px - interior stray gap must also exceed the median by this
GAP_RATIO_BOUNDARY = 5.0     # first/last gap of a lane needs this ratio - track seams live on the edges
GAP_ABS_BOUNDARY = 150       # px - boundary stray gap must also clear this
LANE_FILL_MIN = 0.3          # lane boxes must fill at least this of the lane span
MIN_SPACING_PX = 34          # smaller boxes (op circles, legend swatches) don't participate
MIN_LANE_BOXES = 3           # lanes with fewer boxes than this are not judged


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


def self_intersection_warnings(cells, by_id):
    """A waypointed arrow's own route must not fold back and cross itself.

    Hand-authored waypoints can double back and slice through an earlier
    segment of the same edge - the arrow reads as a loop knot even though both
    endpoints are correctly connected. Only waypointed edges are checked: auto-
    routed edges get their route from draw.io at render time and cannot fold
    back. Proper interior crossings only; a route that merely grazes its own
    corner (shared endpoint / collinear touch) is not a defect.
    """
    warns = []
    for c in cells:
        if c.get("edge") != "1":
            continue
        eid = c.get("id")
        pts = edge_route(c, by_id)
        if not pts or len(pts) < 4:
            continue
        crossing = None
        for i in range(len(pts) - 1):
            for j in range(i + 2, len(pts) - 1):
                if segments_cross(pts[i], pts[i + 1], pts[j], pts[j + 1]):
                    crossing = (i, j)
                    break
            if crossing:
                break
        if crossing:
            warns.append(
                f"edge {eid!r} route self-intersects (segments {crossing[0]} "
                f"and {crossing[1]} cross) - the arrow loops back through its "
                f"own line; drop the folding waypoints")
    return warns


def flow_cycle_warnings(cells, by_id):
    """The directed flow graph (arrow source -> target) must be acyclic.

    A cycle means an arrow chain closes a loop back onto itself
    (a -> b -> c -> a) - in an architecture figure that reads as an accidental
    backward connection, not a real data flow. Deliberate feedback / iterative
    edges (drawn dashed along the outer corridor per the style guide) are the
    intentional exception: if the model truly loops, keep the edge and accept
    the warning (or annotate the cycle as a design feature). DFS with three
    colours over vertex cells only, so a dangling edge can never fabricate a
    cycle.
    """
    verts = [c.get("id") for c in cells if c.get("vertex") == "1"]
    adj = {vid: [] for vid in verts}
    for c in cells:
        if c.get("edge") != "1":
            continue
        s, t = c.get("source"), c.get("target")
        if s in adj and t in adj:
            adj[s].append(t)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {vid: WHITE for vid in verts}
    stack, cycles = [], []

    def dfs(u):
        color[u] = GRAY
        stack.append(u)
        for w in adj.get(u, []):
            if color[w] == GRAY:
                cycles.append(stack[stack.index(w):] + [w])
            elif color[w] == WHITE:
                dfs(w)
        stack.pop()
        color[u] = BLACK

    for v in verts:
        if color[v] == WHITE:
            dfs(v)
    return [
        f"directed cycle in flow graph: {' -> '.join(cyc)} - the arrows close "
        f"a loop; reverse or drop the backward edge (unless this is a "
        f"deliberate feedback/iterative connection)"
        for cyc in cycles
    ]


def style_value(style, key):
    """Return the raw value of ``key=`` in a style string, or None."""
    for part in (style or "").split(";"):
        if part.startswith(key + "="):
            return part.split("=", 1)[1]
    return None


# --- Semantic / intent invariants ------------------------------------------
# The checks below are the "would otherwise need 目检" classes: an arrow that
# stabs through its own target to a far-side port reads as "not connected"; an
# op circle whose outgoing arrow leaves the wrong side flips the operation's
# meaning; text wider/taller than its chip stamps over the neighbours; and a
# symmetric-U figure with an off-centre bottleneck or unlevel arms reads sloppy
# even though every overlap/routing check passes. Each is derived purely from
# geometry, so the rendered PNG is not the only truth.


def through_target_violations(cells, by_id):
    """Waypointed edges whose first/last segment runs through their own node.

    A hand-authored route that approaches a node from one side but pins the
    port on the OPPOSITE side makes the final (or initial) segment cross the
    node's interior and stop on the far edge. It still connects in the XML but
    renders as "the arrow ran past and is not attached" - the class of defect
    seen on the U-Net bottleneck edge. Returns structured violations for
    validate (warn text) and fix_layout (auto-fix). Auto-routed edges are
    skipped: draw.io never routes a through-the-target line itself.

    Returns a list of dicts: {edge, node, end, bad_side, box} where bad_side
    is the pinned port side that is wrong (the fix is the opposite side).
    """
    violations = []
    for c in cells:
        if c.get("edge") != "1":
            continue
        wps = edge_waypoints(c)
        if not wps:
            continue
        style = c.get("style") or ""
        eid = c.get("id")
        # target end: last waypoint -> entry point
        tid = c.get("target")
        if tid and tid in by_id:
            box = abs_rect(by_id[tid], by_id)
            entry = endpoint(c, "target", by_id)
            if box and entry:
                ex, ey = entry
                lx, ly = wps[-1]
                exv, eyv = style_num(style, "entryX"), style_num(style, "entryY")
                if eyv is not None and eyv in (0, 1) and abs(lx - ex) < THROUGH_EPS:
                    if eyv == 1 and ly < ey - THROUGH_EPS:
                        violations.append(
                            {"edge": eid, "node": tid, "end": "target",
                             "bad_side": "S", "box": box})
                    elif eyv == 0 and ly > ey + THROUGH_EPS:
                        violations.append(
                            {"edge": eid, "node": tid, "end": "target",
                             "bad_side": "N", "box": box})
                if exv is not None and exv in (0, 1) and abs(ly - ey) < THROUGH_EPS:
                    if exv == 1 and lx < ex - THROUGH_EPS:
                        violations.append(
                            {"edge": eid, "node": tid, "end": "target",
                             "bad_side": "E", "box": box})
                    elif exv == 0 and lx > ex + THROUGH_EPS:
                        violations.append(
                            {"edge": eid, "node": tid, "end": "target",
                             "bad_side": "W", "box": box})
        # source end: exit point -> first waypoint
        sid = c.get("source")
        if sid and sid in by_id:
            box = abs_rect(by_id[sid], by_id)
            exit_ = endpoint(c, "source", by_id)
            if box and exit_:
                ex, ey = exit_
                fx, fy = wps[0]
                exv, eyv = style_num(style, "exitX"), style_num(style, "exitY")
                if eyv is not None and eyv in (0, 1) and abs(fx - ex) < THROUGH_EPS:
                    if eyv == 1 and fy < ey - THROUGH_EPS:
                        violations.append(
                            {"edge": eid, "node": sid, "end": "source",
                             "bad_side": "S", "box": box})
                    elif eyv == 0 and fy > ey + THROUGH_EPS:
                        violations.append(
                            {"edge": eid, "node": sid, "end": "source",
                             "bad_side": "N", "box": box})
                if exv is not None and exv in (0, 1) and abs(fy - ey) < THROUGH_EPS:
                    if exv == 1 and fx < ex - THROUGH_EPS:
                        violations.append(
                            {"edge": eid, "node": sid, "end": "source",
                             "bad_side": "E", "box": box})
                    elif exv == 0 and fx > ex + THROUGH_EPS:
                        violations.append(
                            {"edge": eid, "node": sid, "end": "source",
                             "bad_side": "W", "box": box})
    return violations


def final_segment_through_target_warnings(cells, by_id):
    """Format through_target_violations for the warning list."""
    warns = []
    fixes = {"source": "exit", "target": "entry"}
    for v in through_target_violations(cells, by_id):
        eid, nid, end, side = v["edge"], v["node"], v["end"], v["bad_side"]
        peer = "target" if end == "source" else "source"
        approach = {"E": "left", "W": "right", "N": "above", "S": "below"}[side]
        entered = {"E": "RIGHT", "W": "LEFT", "N": "TOP", "S": "BOTTOM"}[side]
        if end == "target":
            warns.append(
                f"edge {eid!r} approaches {nid!r} from the {approach} but "
                f"pins its {entered} side - the line runs through the node and "
                f"the arrow reads as unconnected; flip entry{side} to the "
                f"opposite side (or move the last waypoint clear of the box)")
        else:
            warns.append(
                f"edge {eid!r} exits {nid!r}'s {entered} side but immediately "
                f"turns {approach}ward through it - route the edge out the "
                f"other way (or move the first waypoint clear of the box)")
    return warns


def op_direction_violations(cells, by_id):
    """Op circles (ellipse with a down/up glyph) whose outgoing arrow leaves
    the wrong side. Returns structured {circle, edge, expected, actual}."""
    violations = []
    for c in cells:
        if c.get("vertex") != "1" or is_edge_label(c):
            continue
        style = c.get("style") or ""
        if not style_has(style, "ellipse"):
            continue
        value = (c.get("value") or "").strip()
        expected = None
        if "↓" in value:      # ↓ - down-sampling: output exits the bottom
            expected = "S"
        elif "↑" in value:    # ↑ - up-sampling: output exits the top
            expected = "N"
        if expected is None:
            continue
        cid = c.get("id")
        out = None
        for e in cells:
            if e.get("edge") == "1" and e.get("source") == cid:
                out = e
                break
        if out is None:
            continue  # legend glyph / lone symbol - no route to mis-orient
        actual, _ = _side_of(out, "source", by_id)
        # The glyph only encodes flow DIRECTION when the chain runs vertically:
        # on a horizontal chain (prototype A pipeline) an up-sample op's ↑ is an
        # OPERATION tag and its output legitimately leaves the side (E/W) toward
        # the next block. Only judge vertical out-edges, where a mismatch really
        # reads as an arrow pointing the wrong way.
        if actual in ("N", "S") and actual != expected:
            violations.append(
                {"circle": cid, "edge": out.get("id"),
                 "expected": expected, "actual": actual})
    return violations


def op_circle_direction_warnings(cells, by_id):
    """Format op_direction_violations for the warning list."""
    warns = []
    labels = {"N": "up-conv", "S": "down-sample"}
    for v in op_direction_violations(cells, by_id):
        warns.append(
            f"op circle {v['circle']!r} is a {labels[v['expected']]} but its "
            f"outgoing edge {v['edge']!r} leaves the {v['actual']} side - the "
            f"arrow reads backwards; flip the exit port to {v['expected']} "
            f"(or correct the symbol)")
    return warns


def vertex_label_fit_warnings(cells):
    """Text must fit inside its chip (the guide's "box ≈ text + 8-12px" rule).

    A non-wrapping box whose widest line is wider than the box, or a wrapping
    box taller than the box once its lines wrap to the available width, lets
    the label stamp over the neighbouring figure - a 目检-only catch until now.
    The estimators are deliberately not exact (Latin/digit ≈ 0.55em, CJK ≈
    1.0em, line ≈ 1.25em matching draw.io's HTML line spacing), and the trigger
    is proportional (25% taller than the box) so only CLEAR overflow fires -
    a label a couple of px over the box centre is harmless.
    """
    warns = []
    for c in cells:
        if c.get("vertex") != "1" or is_edge_label(c) or is_text_cell(c):
            continue
        value = (c.get("value") or "").strip()
        if not value:
            continue
        text = value.replace("<br>", "\n").replace("&#10;", "\n").strip()
        r = rect(c)
        if r is None or any(v != v for v in r) or r[2] <= 0 or r[3] <= 0:
            continue
        style = c.get("style") or ""
        cid = c.get("id")
        fs = style_num(style, "fontSize") or 10.0
        spacing = style_num(style, "spacing") or 0.0
        if style_has(style, "whiteSpace=wrap"):
            avail_w = max(4.0, r[2] - 2 * spacing - 2)
            lines = 0
            for raw in text.split("\n"):
                cur = ""
                for word in raw.split(" "):
                    trial = (cur + " " + word).strip()
                    if label_width(trial, style) <= avail_w or not cur:
                        cur = trial
                    else:
                        lines += 1
                        cur = word
                lines += 1
            need_h = lines * fs * 1.25 + 2 * spacing
            if need_h > r[3] * 1.25 + TEXT_FIT_SLACK:
                warns.append(
                    f"label of box {cid!r} needs ~{need_h:g}px height once "
                    f"wrapped ({lines} lines) but the box is only {r[3]:g}px "
                    f"tall - text overflows; shorten the label or grow the box")
        else:
            widest = label_width(text, style)
            avail_w = r[2] - 2 * spacing - 2
            if widest > avail_w + TEXT_FIT_SLACK:
                warns.append(
                    f"label of box {cid!r} is ~{widest:g}px wide but the box "
                    f"is {r[2]:g}px - text escapes the chip; widen the box or "
                    f"add whiteSpace=wrap")
    return warns


def load_recipe(name, script_dir):
    """Load a per-figure archetype recipe (recipes/<name>.json)."""
    if name.endswith(".json"):
        path = name
    else:
        path = os.path.join(script_dir, "recipes", name + ".json")
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        sys.exit(f"error: cannot load recipe {name!r} ({path}): {exc}")


def recipe_violations(cells, by_id, recipe):
    """Archetype invariants re-derived from geometry.

    A recipe is a tiny JSON that names which cells play which roles in a figure
    archetype. It turns the guide's layout rules ("Bottleneck 置中", "臂成员
    y 镜像", "跳跃线水平", density floors) into checks, so an off-centre
    bottleneck is caught before anyone opens draw.io. Returns structured
    violations; the centering kind carries a ready-made fix (new_x).
    """
    name = recipe.get("name", "?")
    tag = f"[{name}]"
    violations = []

    def r(id_):
        cell = by_id.get(id_)
        return abs_rect(cell, by_id) if cell is not None else None

    arms = recipe.get("arms")
    corr = recipe.get("corridor", {})
    centered = corr.get("centered")
    tol = corr.get("tol_px", CORRIDOR_CENTER_TOL)
    if arms and centered:
        ar = [a for a in (r(x) for x in arms) if a]
        # The corridor sits between the arms, leftmost arm to rightmost arm
        # (sorted by centre-x so the recipe need not state left/right order).
        ar = sorted(ar, key=lambda a: a[0] + a[2] / 2)
        if ar:
            left = ar[0][0] + ar[0][2]   # right edge of the left arm
            right = ar[-1][0]            # left edge of the right arm
            if left < right:
                center = (left + right) / 2
                br = r(centered)
                if br:
                    cxc = br[0] + br[2] / 2
                    if abs(cxc - center) > tol:
                        new_x = center - br[2] / 2
                        violations.append({
                            "kind": "centering",
                            "id": centered,
                            "fix": {"id": centered, "new_x": new_x},
                            "detail": (f"{tag} corridor element {centered!r} is "
                                       f"off-centre: centre {cxc:g}px vs corridor "
                                       f"centre {center:g}px, {abs(cxc - center):g}px "
                                       f"off - shift x to {new_x:g}")})
                    bottom = max(a[1] + a[3] for a in ar)
                    if br[1] + br[3] / 2 < bottom - CORRIDOR_BELOW_SLACK:
                        violations.append({
                            "kind": "bottleneck_below",
                            "id": centered,
                            "detail": (f"{tag} corridor element {centered!r} "
                                       f"sits above the arms' bottom ({bottom:g}px) "
                                       f"- the U-bottleneck should hang in the "
                                       f"lower corridor")})
    for a, b in recipe.get("mirror_pairs", []):
        ra, rb = r(a), r(b)
        if ra and rb:
            ya = ra[1] + ra[3] / 2
            yb = rb[1] + rb[3] / 2
            if abs(ya - yb) > recipe.get("mirror_tol_px", MIRROR_TOL):
                violations.append({
                    "kind": "mirror",
                    "id": a,
                    "detail": (f"{tag} mirror pair {a!r}/{b!r} are not level: "
                               f"centre-y {ya:g} vs {yb:g} - the two arms should "
                               f"mirror vertically")})
    for eid in recipe.get("horizontal_edges", []):
        edge = by_id.get(eid)
        if edge is None or edge.get("edge") != "1":
            continue
        s, t = edge.get("source"), edge.get("target")
        rs, rt = r(s), r(t)
        if rs and rt:
            sy = rs[1] + rs[3] / 2
            ty = rt[1] + rt[3] / 2
            if abs(sy - ty) > recipe.get("horizontal_tol_px", SKIP_HORIZONTAL_TOL):
                violations.append({
                    "kind": "skip_horizontal",
                    "id": eid,
                    "detail": (f"{tag} skip edge {eid!r} is not horizontal: "
                               f"source centre-y {sy:g} vs target centre-y "
                               f"{ty:g} - a skip connection should run level")})
    if "min_components" in recipe or "min_edges" in recipe:
        comps = sum(1 for c in cells
                    if c.get("vertex") == "1" and not is_edge_label(c)
                    and not is_text_cell(c))
        edges = sum(1 for c in cells
                    if c.get("edge") == "1" and c.get("source") and c.get("target"))
        mc = recipe.get("min_components")
        me = recipe.get("min_edges")
        if mc and comps < mc:
            violations.append({
                "kind": "density_component",
                "id": None,
                "detail": (f"{tag} sparse: {comps} components < {mc} - walk the "
                           f"Step 0 checklist and fill in missing blocks")})
        if me and edges < me:
            violations.append({
                "kind": "density_edge",
                "id": None,
                "detail": (f"{tag} sparse: {edges} edges < {me} - wire up the "
                           f"sub-modules and add feature/tensor labels")})
    return violations


def recipe_warnings(cells, by_id, recipe):
    """Format recipe_violations for the warning list."""
    return [v["detail"] for v in recipe_violations(cells, by_id, recipe)]


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


def blend_over_white(fill, opacity):
    """Visible colour of ``fill`` rendered at ``opacity``% over a white page.

    Containers use semi-transparent fills (``fillOpacity=35`` etc.), so the
    colour a label actually sits on is fill blended with white, not the raw
    fillColor. A label slab set to the raw fill reads as a dark block on the
    translucent panel. ``opacity`` None/100 returns ``fill`` unchanged.
    """
    if not fill or len(fill) != 7 or fill[0] != "#":
        return None
    try:
        r, g, b = int(fill[1:3], 16), int(fill[3:5], 16), int(fill[5:7], 16)
    except ValueError:
        return None
    a = 1.0 if opacity is None else max(0.0, min(1.0, float(opacity) / 100.0))
    return "#%02X%02X%02X" % (int(r * a + 255 * (1 - a)),
                              int(g * a + 255 * (1 - a)),
                              int(b * a + 255 * (1 - a)))


def label_bg_warnings(cells, by_id):
    """A label sitting on a tinted panel must carry the panel's fill colour.

    The guide requires every labeled edge to have labelBackgroundColor; on the
    white canvas that background is #FFFFFF. But when the label's midpoint lands
    inside a tinted container, a white label box floats as an abrupt white slab
    on the coloured panel. The label background must then match the container's
    *visible* colour. Containers are semi-transparent (``fillOpacity``), so the
    visible colour is ``blend_over_white(fillColor, fillOpacity)`` — not the raw
    fillColor, which is darker than what renders. Labels on the plain canvas
    (no container under the point) and on white containers keep the default
    #FFFFFF.
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
        # Semi-transparent containers: the label must match the blended colour
        # actually rendered, not the raw fill (which looks like a dark slab).
        op = style_num(ccell.get("style") or "", "fillOpacity")
        visible = blend_over_white(fill, op) or fill.upper()
        lbg = style_value(c.get("style") or "", "labelBackgroundColor")
        if lbg is None:
            continue  # missing bg already flagged by the label-bg rule
        if lbg.upper() != visible:
            hint = (f"container {ccell.get('id')!r} renders fill {fill} at "
                    f"{op:g}% over white = {visible}" if op else
                    f"container {ccell.get('id')!r} fill {visible}")
            warns.append(
                f"edge {c.get('id')!r} label sits on tinted container "
                f"{ccell.get('id')!r} (fill {fill}) but labelBackgroundColor "
                f"is {lbg} - the slab looks darker than the translucent panel; "
                f"set labelBackgroundColor={visible} ({hint})")
    return warns


def auto_ortho_route(edge, by_id):
    """Expected Manhattan route draw.io computes for a waypoint-free
    orthogonal edge: a Z-shape through the mid-X (horizontal-dominant) or
    mid-Y (vertical-dominant) of the two pinned endpoints. This is an
    approximation of the render-time route - good enough to catch the common
    "edge slices a sibling box" defect, not a promise of the exact bends.
    Returns None for non-orthogonal styles or missing endpoints.
    """
    style = edge.get("style") or ""
    if style_value(style, "edgeStyle") != "orthogonalEdgeStyle":
        return None
    s = endpoint(edge, "source", by_id)
    t = endpoint(edge, "target", by_id)
    if s is None or t is None:
        return None
    sx, sy = s
    tx, ty = t
    if abs(tx - sx) >= abs(ty - sy):      # horizontal-dominant: Z via mid-X
        mx = (sx + tx) / 2.0
        return [s, (mx, sy), (mx, ty), t]
    my = (sy + ty) / 2.0                  # vertical-dominant: Z via mid-Y
    return [s, (sx, my), (tx, my), t]


def geometry_warnings(cells, ids, parents):
    """Edge-through-vertex and edge-crossing warnings.

    Waypointed edges use their stored route; waypoint-free orthogonal edges
    get an *expected* Manhattan Z-route (auto_ortho_route), so the through-
    vertex check covers the whole diagram, not just explicitly-routed edges.
    Edge-crossing is still judged only between waypointed edges - auto-routes
    are an approximation, and pairwise crossings of approximations would be
    noisy.
    """
    warns = []
    routed = []   # (eid, pts, ends) for waypointed edges
    auto = []     # (eid, pts, ends) for waypoint-free orthogonal edges
    for c in cells:
        if c.get("edge") != "1":
            continue
        pts = edge_route(c, ids)
        if pts:
            routed.append((c.get("id"), pts,
                           {c.get("source"), c.get("target")}))
            continue
        ar = auto_ortho_route(c, ids)
        if ar:
            auto.append((c.get("id"), ar,
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
    # Sibling membership: a leaf inside the same container as the edge's source
    # or target is a "sibling member" - an auto-routed edge slicing one is the
    # "wire through sub-box" defect, and needs a different (actionable) message.
    mem_of = {}
    for vid, box in allv:
        for cid, cbox in allv:
            if vid != cid and contains(cbox, box):
                mem_of.setdefault(vid, set()).add(cid)
    for eid, pts, ends in routed + auto:
        sib = set()
        for end in ends:
            sib |= mem_of.get(end, set())
        for vid, box in leaves:
            if vid in ends or not route_hits_rect(pts, box):
                continue
            if mem_of.get(vid, set()) & sib:
                warns.append(
                    f"edge {eid!r} auto-routed across sibling member {vid!r} "
                    f"(shares a container with an endpoint) - add a waypoint "
                    f"or change exit/entry side to route around it")
            else:
                warns.append(f"edge {eid!r} routes through vertex {vid!r}")
    for i in range(len(routed)):
        for j in range(i + 1, len(routed)):
            (ia, pa, _), (ib, pb, _) = routed[i], routed[j]
            if routes_cross(pa, pb):
                warns.append(f"edges {ia!r} and {ib!r} cross")
    return warns


def median(values):
    """Median of a small float list (0.0 for an empty list)."""
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def _cluster_bands(boxes, axis):
    """Group (id, rect) boxes into lanes/columns by overlapping extents.

    ``axis`` is the dimension along which boxes must overlap to sit in the same
    row ("y" -> a horizontal lane; "x" -> a vertical column). Boxes whose
    intervals on that axis overlap (or touch) cluster together; each cluster is
    ordered by that axis' start.
    """
    i = 1 if axis == "y" else 0      # interval start index within the rect
    span = 3 if axis == "y" else 2   # interval length index within the rect
    ordered = sorted(boxes, key=lambda b: b[1][i])
    clusters, cur, hi = [], [], None
    for vid, r in ordered:
        lo = r[i]
        if cur and lo <= hi + 0.5:
            cur.append((vid, r))
            hi = max(hi, lo + r[span])
        else:
            if cur:
                clusters.append(cur)
            cur, hi = [(vid, r)], lo + r[span]
    if cur:
        clusters.append(cur)
    return clusters


def _judge_gaps(warns, boxes, gaps, extent_axis, occup, containers):
    """Emit spacing warnings for one lane/column.

    ``boxes`` is the cluster sorted along the lane direction and ``gaps`` the
    aligned list of gaps between consecutive boxes. ``occup`` lists every non-
    text box in the figure (tiny op circles included) so a gap can be tested
    for genuine whitespace, and ``containers`` supplies the skip set. Three
    rules:

    - a gap is uneven only when nothing occupies the rectangle it opens between
      its two boxes: an op circle or skip symbol living in that column strip
      makes it a working corridor (a U-shape funnel, a residual shortcut), not
      stray whitespace;
    - a gap >= GAP_RATIO_HI x the lane's median (and GAP_ABS_FLOOR px more) is
      then a stray hole. The first/last gap of a lane needs a stricter ratio
      (GAP_RATIO_BOUNDARY x, GAP_ABS_BOUNDARY px): track seams and branch
      separations naturally land on the lane's edges, so only an extreme gap
      there is worth flagging;
    - the lane is "sparse" when its boxes fill less than LANE_FILL_MIN of the
      lane's own span along that axis (excess whitespace) - pull them together.
      Normalising by the span lets a U-shaped corridor pass: the big boxes
      around it still fill the span.

    The too-small direction is deliberately not checked: a small gap beside an
    intentional corridor is normal, and the overlap/straddle/touch checks
    already own "two boxes crammed".
    """
    pairs = [(a, b, g) for (a, b, g) in zip(boxes, boxes[1:], gaps) if g >= 0]
    if len(pairs) < 2:
        return
    med = median([g for _, _, g in pairs])
    if med <= 0:
        return
    n = len(pairs)
    for idx, ((aid, ar), (bid, br), g) in enumerate(pairs):
        if idx == 0 or idx == n - 1:
            if g < GAP_RATIO_BOUNDARY * med or g < med + GAP_ABS_BOUNDARY:
                continue
        elif g < GAP_RATIO_HI * med or g < med + GAP_ABS_FLOOR:
            continue
        if gap_is_corridor(aid, ar, bid, br, extent_axis, occup, containers):
            continue
        warns.append(
            f"gap between boxes {aid!r} and {bid!r} is {g:g}px, "
            f"{g / med:.1f}x the lane median {med:g}px - uneven spacing / "
            f"stray whitespace; move {bid!r} closer (or space the rest to "
            f"match)")
    i = 0 if extent_axis == "width" else 1
    span_i = 2 if extent_axis == "width" else 3
    lo = min(b[1][i] for b in boxes)
    hi = max(b[1][i] + b[1][span_i] for b in boxes)
    span = hi - lo
    if span > 0:
        filled = sum(b[1][span_i] for b in boxes)
        if filled / span < LANE_FILL_MIN:
            warns.append(
                f"lane around {boxes[0][0]!r} is sparse: its {len(boxes)} "
                f"boxes fill only {filled / span * 100:.0f}% of the "
                f"{span:g}px span - excessive whitespace; pull the boxes "
                f"together")


def gap_is_corridor(aid, a, bid, b, extent_axis, occup, containers):
    """True when the rectangle a gap opens between two lane boxes holds a box.

    The rectangle spans the two boxes along the lane axis (a's trailing edge to
    b's leading edge) and the union of their intervals on the other axis. Any
    non-text box whose centre lands inside it is an occupant: a skip/sum
    circle, a funnel target, a hanging label - the gap is a working corridor,
    not stray whitespace. The two endpoint boxes and the containers that hold
    them are excluded: a container's own interior is not an obstacle.
    """
    if extent_axis == "width":     # a horizontal lane: hole along x, band along y
        hx0, hx1 = a[0] + a[2], b[0]
        hy0, hy1 = min(a[1], b[1]), max(a[1] + a[3], b[1] + b[3])
    else:                          # a vertical column: hole along y, band along x
        hx0, hx1 = min(a[0], b[0]), max(a[0] + a[2], b[0] + b[2])
        hy0, hy1 = a[1] + a[3], b[1]
    skip = {aid, bid}
    for oid, ob in occup:
        if oid in containers:
            if contains(ob, a):
                skip.add(oid)
            if contains(ob, b):
                skip.add(oid)
    for oid, ob in occup:
        if oid in skip:
            continue
        cx = ob[0] + ob[2] / 2.0
        cy = ob[1] + ob[3] / 2.0
        if hx0 < cx < hx1 and hy0 < cy < hy1:
            return True
    return False


def straightness_warnings(cells, ids):
    """Two "arrow straightness" rules.

    The guide's routing discipline wants arrows straight unless they must dodge
    a box or a label (换端口侧 first, waypoints only as a last resort). These
    checks turn that preference into deterministic warnings:

    1. A waypoint sitting exactly on the line between its two neighbours bends
       nothing - it is redundant, and deleting it leaves the route unchanged.
       Hand-authored waypoints on the 10px grid make these exact collisions
       common enough to check.
    2. An orthogonal edge whose endpoints are axis-aligned - or any edge whose
       straight connector is clear - carries waypoints that are pure detour.
       The straight line counts as "clear" only when it slices no box, text
       cell, edge label or box title, so a genuine obstacle (the case the
       guide's 绕行 rule permits) never triggers. Crossing another edge is
       deliberately ignored: line crossings are often unavoidable and are not
       the defect this rule targets.
    """
    warns = []
    allv, text_rects, title_rects = [], [], []
    for c in cells:
        if c.get("vertex") != "1" or is_edge_label(c):
            continue
        box = abs_rect(c, ids)
        if box is None:
            continue
        if is_text_cell(c):
            text_rects.append(box)
        else:
            allv.append((c.get("id"), box))
            tr = title_rect(c, ids)
            if tr:
                title_rects.append(tr)
    box_of = dict(allv)
    label_rects = {}
    for c in cells:
        if c.get("edge") == "1":
            r = edge_label_rect(c, ids)
            if r:
                label_rects[c.get("id")] = r

    def skip_set(end_id):
        """endpoint's own box plus every container holding it."""
        skip = {end_id}
        if end_id in box_of:
            for cid, cbox in allv:
                if cid != end_id and contains(cbox, box_of[end_id]):
                    skip.add(cid)
        return skip

    for c in cells:
        if c.get("edge") != "1":
            continue
        eid = c.get("id")
        wps = edge_waypoints(c)
        if not wps:
            continue
        s, t = endpoint(c, "source", ids), endpoint(c, "target", ids)
        if s is None or t is None:
            continue
        pts = [s] + wps + [t]
        # rule 1: a waypoint that bends nothing
        for i in range(1, len(pts) - 1):
            ax, ay = pts[i - 1]
            bx, by = pts[i]
            cx, cy = pts[i + 1]
            cross = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
            if abs(cross) <= COLLINEAR_EPS:
                warns.append(
                    f"edge {eid!r} waypoint at ({bx:g},{by:g}) is collinear "
                    f"with its two neighbours - it bends nothing; delete it "
                    f"and the route is unchanged")
        # rule 2: straight connector is clear, yet the edge detours
        if (s[0] - t[0]) ** 2 + (s[1] - t[1]) ** 2 < 1.0:
            continue  # zero-length connector - nothing to straighten
        style = c.get("style") or ""
        ortho = style_value(style, "edgeStyle") == "orthogonalEdgeStyle"
        if ortho and not (abs(s[0] - t[0]) <= ALIGN_EPS or
                          abs(s[1] - t[1]) <= ALIGN_EPS):
            continue  # misaligned orthogonal edge genuinely needs bends
        src, tgt = c.get("source"), c.get("target")
        skip = skip_set(src) | skip_set(tgt)
        blocked = any(route_hits_rect([s, t], box)
                      for vid, box in allv if vid not in skip)
        if not blocked:
            blocked = any(route_hits_rect([s, t], box) for box in text_rects)
        if not blocked:
            blocked = any(route_hits_rect([s, t], box) for box in title_rects)
        if not blocked:
            blocked = any(route_hits_rect([s, t], box)
                          for bid, box in label_rects.items() if bid != eid)
        if not blocked:
            warns.append(
                f"edge {eid!r} could be a straight connector between its two "
                f"boxes but routes through {len(wps)} waypoint(s) - no box or "
                f"label blocks the straight line; delete the waypoints")
    return warns


# --- Port / routing quality checks (the "four generation defects") ----------
# The guide's edge discipline forbids four classes that a rendered PNG used to
# be the only way to catch: arrows that wrap around their target (打环), arrows
# forced into a bend when a clear straight connector exists (多余弯曲), port
# pins that the cube perimeter silently re-projects, and formula text that is
# not bold. All four are derived purely from geometry + style, so validate can
# flag them without draw.io. Each is verified against draw.io's real router.

PORT_TOL = 2.0          # px - exit point may graze the entry face within this
CUBE_SCRAMBLED_DIRS = ("south",)  # directions whose cube perimeter re-projects ports


def _pinned_side(style, prefix):
    """Return 'N'/'S'/'E'/'W' if the port (exit/entry) is pinned to a boundary
    on exactly one axis, else None. A corner pin (both axes on the boundary)
    is ambiguous -> None, and a mid-face pin ((0.5, 0.5)) is not a side."""
    px, py = style_num(style, prefix + "X"), style_num(style, prefix + "Y")
    on_x = px in (0.0, 1.0)
    on_y = py in (0.0, 1.0)
    if on_x and not on_y:
        return "W" if px == 0.0 else "E"
    if on_y and not on_x:
        return "N" if py == 0.0 else "S"
    return None


def cube_port_violations(cells, by_id):
    """Structured port-pins-on-scrambled-cube findings (one dict per edge end).

    draw.io computes a cube's exit/entry point with `cubePerimeter`, not the
    bounding-box rule the guide teaches. Verified against draw.io 31: a cube
    with `direction=south` renders exitX=1;exitY=0.5 at the BOTTOM centre and
    exitX=0.5;exitY=1 at the LEFT centre - so the "right mid" pin lands
    somewhere else entirely and the auto-router wraps the edge. `direction=north`
    (the default) honours the pins, and unpinned edges auto-pick a sane side.
    """
    finds = []
    for c in cells:
        if c.get("edge") != "1":
            continue
        style = c.get("style") or ""
        eid = c.get("id")
        for end, prefix in (("source", "exit"), ("target", "entry")):
            vid = c.get(end)
            if not vid or vid not in by_id:
                continue
            vs = by_id[vid].get("style") or ""
            if (style_value(vs, "shape") == "cube"
                    and style_value(vs, "direction") in CUBE_SCRAMBLED_DIRS
                    and _pinned_side(style, prefix) is not None):
                finds.append({"edge": eid, "vertex": vid, "end": end})
    return finds


def cube_port_warnings(cells, by_id):
    warns = []
    for v in cube_port_violations(cells, by_id):
        warns.append(
            f"edge {v['edge']!r} pins its "
            f"{'exit' if v['end'] == 'source' else 'entry'} on cube "
            f"{v['vertex']!r} (shape=cube;direction=south) - the cube perimeter "
            f"re-projects ports ((1,0.5) renders at the bottom, (0.5,1) at the "
            f"left) so the route wraps; use direction=north (drop the direction "
            f"style) or a plain rounded rectangle, or unpin the port")
    return warns


def port_facing_violations(cells, by_id):
    """Structured wrap-around findings: exit not "in front of" the entry side.

    Adjacent/opposite exit-entry combos whose exit is not "in front of" the
    entry side - draw.io must wrap around the target to reach it, producing the
    打环 loop or a degenerate slide along the entry edge. Verified against
    draw.io's orthogonal router: entry LEFT needs the exit point left of the
    entry, entry TOP needs it above, etc. Opposite-side combos pass
    automatically (exit right + entry left with a left->right flow is the
    canonical straight case). Only fully-pinned, waypoint-free edges are judged
    - hand-routed edges are the author's own shape, and draw.io auto-picks a
    sane side when a port is unpinned."""
    finds = []
    for c in cells:
        if c.get("edge") != "1":
            continue
        style = c.get("style") or ""
        if style_value(style, "edgeStyle") != "orthogonalEdgeStyle":
            continue
        if edge_waypoints(c):
            continue
        in_side = _pinned_side(style, "entry")
        out_side = _pinned_side(style, "exit")
        if in_side is None or out_side is None:
            continue
        if c.get("source") == c.get("target"):
            continue  # intentional self-loop
        s = endpoint(c, "source", by_id)
        t = endpoint(c, "target", by_id)
        if s is None or t is None:
            continue
        eid = c.get("id")
        reason = None
        if in_side == "W" and s[0] > t[0] + PORT_TOL:
            reason = "its source exits to the right of the entry - draw.io " \
                     "wraps around the target (arrow loop)"
        elif in_side == "E" and s[0] < t[0] - PORT_TOL:
            reason = "its source exits to the left of the entry - draw.io " \
                     "wraps around the target (arrow loop)"
        elif in_side == "N" and s[1] > t[1] + PORT_TOL:
            reason = "its source exits below the entry - draw.io wraps around " \
                     "the target (arrow loop)"
        elif in_side == "S" and s[1] < t[1] - PORT_TOL:
            reason = "its source exits above the entry - draw.io wraps around " \
                     "the target (arrow loop)"
        if reason:
            finds.append({
                "edge": eid, "target": c.get("target"), "in_side": in_side,
                "s": s, "t": t, "reason": reason})
    return finds


def port_facing_warnings(cells, by_id):
    warns = []
    for v in port_facing_violations(cells, by_id):
        face = {"W": "left", "E": "right", "N": "top", "S": "bottom"}[v["in_side"]]
        warns.append(
            f"edge {v['edge']!r} enters {v['target']!r} on the {face} side "
            f"but {v['reason']}; flip the entry side to face the source (or "
            f"pick exit/entry sides that point at each other)")
    return warns


def port_alignment_violations(cells, by_id):
    """Structured S-bend findings: opposite-side ports misaligned when a
    straight connector between the two boxes is geometrically possible and
    unobstructed. The router renders an S-bend; aligning the ports makes it a
    single straight line. Pairs whose boxes do not overlap on the straight axis
    genuinely need the bend. Each finding carries the shared coordinate (ymid /
    xmid) and the two box rects so a fixer can re-slot the ports."""
    finds = []
    allv, text_rects, title_rects = [], [], []
    for c in cells:
        if c.get("vertex") != "1" or is_edge_label(c):
            continue
        box = abs_rect(c, by_id)
        if box is None:
            continue
        if is_text_cell(c):
            text_rects.append(box)
        else:
            allv.append((c.get("id"), box))
            tr = title_rect(c, by_id)
            if tr:
                title_rects.append(tr)
    label_rects = {c.get("id"): edge_label_rect(c, by_id)
                   for c in cells
                   if c.get("edge") == "1" and edge_label_rect(c, by_id)}

    def clear_segment(p1, p2, skip):
        for vid, box in allv:
            if vid in skip:
                continue
            if route_hits_rect([p1, p2], box):
                return False
        for box in text_rects + title_rects:
            if route_hits_rect([p1, p2], box):
                return False
        for bid, box in label_rects.items():
            if route_hits_rect([p1, p2], box):
                return False
        return True

    for c in cells:
        if c.get("edge") != "1":
            continue
        style = c.get("style") or ""
        if style_value(style, "edgeStyle") != "orthogonalEdgeStyle":
            continue
        if edge_waypoints(c):
            continue
        in_side = _pinned_side(style, "entry")
        out_side = _pinned_side(style, "exit")
        if (in_side, out_side) not in (("W", "E"), ("E", "W"),
                                       ("N", "S"), ("S", "N")):
            continue  # only opposite-side pairs can be a single straight line
        s = endpoint(c, "source", by_id)
        t = endpoint(c, "target", by_id)
        if s is None or t is None:
            continue
        src_box, tgt_box = by_id.get(c.get("source")), by_id.get(c.get("target"))
        if src_box is None or tgt_box is None:
            continue
        eid = c.get("id")
        skip = {c.get("source"), c.get("target")}
        if in_side in ("W", "E"):                       # horizontal pair
            if abs(s[1] - t[1]) <= ALIGN_EPS:
                continue                                # already straight
            sr = abs_rect(src_box, by_id)
            tr = abs_rect(tgt_box, by_id)
            if sr is None or tr is None:
                continue
            lo = max(sr[1], tr[1])
            hi = min(sr[1] + sr[3], tr[1] + tr[3])
            if lo > hi:
                continue                                # no shared height
            ymid = (lo + hi) / 2.0
            if not clear_segment((s[0], ymid), (t[0], ymid), skip):
                continue                                # something blocks it
            finds.append({"edge": eid, "source": c.get("source"),
                          "target": c.get("target"), "axis": "H",
                          "shared": ymid, "src_rect": sr, "tgt_rect": tr,
                          "src": s, "tgt": t})
        else:                                           # vertical pair
            if abs(s[0] - t[0]) <= ALIGN_EPS:
                continue
            sr = abs_rect(src_box, by_id)
            tr = abs_rect(tgt_box, by_id)
            if sr is None or tr is None:
                continue
            lo = max(sr[0], tr[0])
            hi = min(sr[0] + sr[2], tr[0] + tr[2])
            if lo > hi:
                continue
            xmid = (lo + hi) / 2.0
            if not clear_segment((xmid, s[1]), (xmid, t[1]), skip):
                continue
            finds.append({"edge": eid, "source": c.get("source"),
                          "target": c.get("target"), "axis": "V",
                          "shared": xmid, "src_rect": sr, "tgt_rect": tr,
                          "src": s, "tgt": t})
    return finds


def port_alignment_warnings(cells, by_id):
    warns = []
    for v in port_alignment_violations(cells, by_id):
        if v["axis"] == "H":
            warns.append(
                f"edge {v['edge']!r} could be a straight horizontal connector "
                f"between {v['source']!r} and {v['target']!r} (their boxes "
                f"overlap vertically and nothing blocks a straight line) but "
                f"exitY={v['src'][1]:g} != entryY={v['tgt'][1]:g} forces an "
                f"S-bend; align the two ports to a shared height")
        else:
            warns.append(
                f"edge {v['edge']!r} could be a straight vertical connector "
                f"between {v['source']!r} and {v['target']!r} (their boxes "
                f"overlap horizontally and nothing blocks a straight line) but "
                f"exitX={v['src'][0]:g} != entryX={v['tgt'][0]:g} forces an "
                f"S-bend; align the two ports to a shared height")
    return warns


# Formula cells must be bold (fontStyle=1) - the guide's math/annotation rule.
# Signals are deliberately conservative so module titles and captions that only
# happen to contain '·' or '−' are not flagged: a cell counts as a formula when
# it carries a sub/superscript, a Greek letter, a dedicated math operator
# (√ ℒ ‖ ∑ ∫ ⊗ ⊕ − × ² ³ ≈ ∈ ≠ ← → ↑ ↓ ↔ ± ∪ ∩ ′ ~), or an underscore that is
# embedded in math context (a bare 'x_0' is a label; '|B_mis| < K_mis' is a
# formula). Code/file names like 'fix_layout.py' or 'M_opt' are NOT formulas -
# an underscore alone never fires. Only shape / note boxes are judged -
# standalone text cells (panel titles, captions, annotations) are labels.
_FORMULA_SUB = re.compile(r"[⁰-₟₀-₟]")
_FORMULA_GREEK = re.compile(r"[Ͱ-Ͽἀ-῿]")
_FORMULA_OPS = re.compile(
    r"[√ℒ‖∑∫⊗⊕−×²³"
    r"≈∈≠←↑→↓↔±∪∩′]|~")
_FORMULA_UNDER = re.compile(r"_")
_FORMULA_UNDER_CTX = re.compile(r"[≤≥<>=|{}]")


def _is_formula_value(value):
    if not value:
        return False
    v = value.replace("<br>", " ").replace("&amp;", "&")
    if _FORMULA_SUB.search(v) or _FORMULA_GREEK.search(v) or _FORMULA_OPS.search(v):
        return True
    # Underscore alone (file names, module ids) is not a formula; it counts only
    # when surrounded by comparison/brace/set punctuation that marks an equation.
    return bool(_FORMULA_UNDER.search(v) and _FORMULA_UNDER_CTX.search(v))


def formula_bold_violations(cells):
    """Shape/note boxes carrying math that are not bold (missing fontStyle=1)."""
    finds = []
    for c in cells:
        if c.get("vertex") != "1" or is_edge_label(c) or is_text_cell(c):
            continue
        value = c.get("value") or ""
        if not _is_formula_value(value):
            continue
        style = c.get("style") or ""
        bold = style_num(style, "fontStyle") is not None and \
            int(style_num(style, "fontStyle")) & 1
        if not bold:
            finds.append({"id": c.get("id"), "value": value})
    return finds


def formula_bold_warnings(cells):
    warns = []
    for v in formula_bold_violations(cells):
        warns.append(
            f"formula cell {v['id']!r} ({v['value'][:24]!r}) is not bold - "
            f"formulas must carry fontStyle=1; add it to the style")
    return warns


def spacing_warnings(cells, ids):
    """Two "space utilisation" rules.

    Boxes inside a lane/column must be spaced roughly uniformly - no stray hole
    in the row - and the lane must not be spread so thin that its boxes are
    islands in whitespace. The check is containment-aware (flat files draw
    containers as background rects, so nesting is found geometrically): members
    are judged against the other members of the same container, the container
    itself takes part in the root-level lanes. Legend material is ignored
    entirely - a container whose non-text members are all tiny swatches is
    dropped along with its members, and any box smaller than MIN_SPACING_PX in
    both dimensions (op circles, legend swatches) never participates - so a
    legend column or bottom bar never skews the gaps of the real figure. The
    "two boxes crammed together" direction is left to the overlap/straddle/
    touch checks: a small gap next to an intentional corridor is normal in a
    U-shaped figure and would be flagged wrongly here. Lanes with fewer than
    MIN_LANE_BOXES boxes are skipped - a lone pair has nothing to be uniform
    against.
    """
    warns = []
    allv = []
    for c in cells:
        if c.get("vertex") != "1" or is_edge_label(c) or is_text_cell(c):
            continue
        box = abs_rect(c, ids)
        if box is None:
            continue
        allv.append((c.get("id"), box))
    containers = {vid for vid, box in allv
                  if any(v2 != vid and contains(box, b2) for v2, b2 in allv)}
    # a legend container holds nothing but tiny swatches (plus text cells)
    legend = set()
    for cid, cbox in allv:
        if cid not in containers:
            continue
        members = [(vid, box) for vid, box in allv
                   if vid != cid and vid not in containers
                   and contains(cbox, box)]
        if (members
                and all(m[1][2] <= MIN_SPACING_PX and m[1][3] <= MIN_SPACING_PX
                        for m in members)):
            legend.add(cid)
    groups = {}    # container id (or None for root) -> [(id, rect)]
    occup = []     # every non-text box incl. small op circles, minus legends
    for vid, box in allv:
        if vid in legend:
            continue
        if vid in containers:
            groups.setdefault(None, []).append((vid, box))
            occup.append((vid, box))
            continue
        holders = [cid for cid, cbox in allv
                   if cid in containers and contains(cbox, box)]
        holder = holders[0] if holders else None
        if holder in legend:
            continue
        groups.setdefault(holder, []).append((vid, box))
        occup.append((vid, box))
    for group in groups.values():
        group = [b for b in group
                 if b[1][2] > MIN_SPACING_PX or b[1][3] > MIN_SPACING_PX]
        if len(group) < MIN_LANE_BOXES:
            continue
        for axis, dir_i, extent in (
                ("y", 0, "width"),    # a lane: overlap y, sort/gap along x
                ("x", 1, "height")):  # a column: overlap x, sort/gap along y
            for cluster in _cluster_bands(group, axis):
                if len(cluster) < MIN_LANE_BOXES:
                    continue
                cluster = sorted(cluster, key=lambda b: b[1][dir_i])
                gaps = [b2[1][dir_i] - (b1[1][dir_i] + b1[1][dir_i + 2])
                        for b1, b2 in zip(cluster, cluster[1:])]
                _judge_gaps(warns, cluster, gaps, extent, occup, containers)
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


def check_page(diagram, recipe=None, acyclic=False):
    """Return (errors, warnings) for one <diagram> page.

    ``recipe`` is an optional per-figure archetype spec (see load_recipe) that
    adds the semantic invariant checks (corridor centring, arm mirroring,
    horizontal skips, density) on top of the generic structural lints.
    ``acyclic`` opts into the directed-flow-graph cycle check - off by default
    because multi-agent / RL / feedback figures legitimately cycle.
    """
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
    warns += straightness_warnings(cells, ids)
    warns += cube_port_warnings(cells, ids)
    warns += port_facing_warnings(cells, ids)
    warns += port_alignment_warnings(cells, ids)
    warns += formula_bold_warnings(cells)
    warns += spacing_warnings(cells, ids)
    warns += port_stacking_warnings(cells, ids)
    warns += collinear_entry_warnings(cells, ids)
    warns += self_intersection_warnings(cells, ids)
    if acyclic:
        warns += flow_cycle_warnings(cells, ids)
    warns += label_gap_warnings(cells, ids)
    warns += label_bg_warnings(cells, ids)
    warns += arrow_through_text_warnings(cells, ids)
    warns += title_clearance_warnings(cells, ids)
    warns += page_fit_warnings(model.get("pageWidth"), model.get("pageHeight"),
                               cells, ids)
    warns += final_segment_through_target_warnings(cells, ids)
    warns += op_circle_direction_warnings(cells, ids)
    warns += vertex_label_fit_warnings(cells)
    if recipe is not None:
        warns += recipe_warnings(cells, ids, recipe)
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
    # Diagrams carry Greek/math unicode in cell values; on Windows the console
    # default codepage (gbk) cannot encode them and print() would crash the
    # whole lint. Reconfigure stdout to UTF-8 so warnings stay readable.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(
        description="Lint a hand-written .drawio file for structural errors.")
    ap.add_argument("file")
    ap.add_argument("--strict", action="store_true",
                    help="treat warnings as failure too")
    ap.add_argument("--score", action="store_true",
                    help="also print a readability score (lower is better) - "
                         "useful for comparing layout variants of the same graph")
    ap.add_argument("--recipe", metavar="NAME",
                    help="apply archetype invariants from recipes/NAME.json "
                         "(corridor centring, arm mirroring, horizontal skips, "
                         "density floors)")
    ap.add_argument("--acyclic", action="store_true",
                    help="flag directed cycles in the flow graph as warnings - "
                         "opt-in because multi-agent / feedback / iterative "
                         "figures legitimately loop; enable for acyclic "
                         "feedforward pipelines")
    args = ap.parse_args()
    try:
        tree = ET.parse(args.file)
    except (ET.ParseError, OSError) as exc:
        sys.exit(f"error: cannot parse {args.file}: {exc}")
    recipe = None
    if args.recipe:
        recipe = load_recipe(args.recipe,
                             os.path.dirname(os.path.abspath(__file__)))
    pages = tree.getroot().findall("diagram") or [tree.getroot()]
    errors, warns = [], []
    for page in pages:
        e, w = check_page(page, recipe, args.acyclic)
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


DEMO_XML = """<mxfile><diagram><mxGraphModel><root>
  <mxCell id="0"/><mxCell id="1" parent="0"/>
  <mxCell id="a1" vertex="1" parent="1"><mxGeometry x="0" y="0" width="120" height="40" as="geometry"/></mxCell>
  <mxCell id="a2" vertex="1" parent="1"><mxGeometry x="160" y="0" width="120" height="40" as="geometry"/></mxCell>
  <mxCell id="a3" vertex="1" parent="1"><mxGeometry x="320" y="0" width="120" height="40" as="geometry"/></mxCell>
  <mxCell id="a4" vertex="1" parent="1"><mxGeometry x="920" y="0" width="120" height="40" as="geometry"/></mxCell>
  <mxCell id="a5" vertex="1" parent="1"><mxGeometry x="1080" y="0" width="120" height="40" as="geometry"/></mxCell>
  <mxCell id="b1" vertex="1" parent="1"><mxGeometry x="0" y="80" width="120" height="40" as="geometry"/></mxCell>
  <mxCell id="b2" vertex="1" parent="1"><mxGeometry x="160" y="80" width="120" height="40" as="geometry"/></mxCell>
  <mxCell id="b3" vertex="1" parent="1"><mxGeometry x="320" y="80" width="120" height="40" as="geometry"/></mxCell>
  <mxCell id="b4" vertex="1" parent="1"><mxGeometry x="480" y="80" width="120" height="40" as="geometry"/></mxCell>
  <mxCell id="c1" vertex="1" parent="1"><mxGeometry x="0" y="160" width="120" height="40" as="geometry"/></mxCell>
  <mxCell id="c2" vertex="1" parent="1"><mxGeometry x="160" y="160" width="120" height="40" as="geometry"/></mxCell>
  <mxCell id="c3" vertex="1" parent="1"><mxGeometry x="320" y="160" width="120" height="40" as="geometry"/></mxCell>
  <mxCell id="d1" vertex="1" parent="1"><mxGeometry x="0" y="240" width="120" height="40" as="geometry"/></mxCell>
  <mxCell id="d2" vertex="1" parent="1"><mxGeometry x="160" y="240" width="120" height="40" as="geometry"/></mxCell>
  <mxCell id="d3" vertex="1" parent="1"><mxGeometry x="320" y="240" width="120" height="40" as="geometry"/></mxCell>
  <mxCell id="d4" vertex="1" parent="1"><mxGeometry x="620" y="240" width="120" height="40" as="geometry"/></mxCell>
  <mxCell id="e_collinear" edge="1" parent="1" source="a1" target="a2">
    <mxGeometry relative="1" as="geometry"><Array as="points">
      <mxPoint x="140" y="20"/></Array></mxGeometry></mxCell>
  <mxCell id="e_detour" edge="1" parent="1" source="b1" target="b2">
    <mxGeometry relative="1" as="geometry"><Array as="points">
      <mxPoint x="140" y="60"/><mxPoint x="140" y="100"/></Array></mxGeometry></mxCell>
  <mxCell id="e_skip" edge="1" parent="1" source="c1" target="c3">
    <mxGeometry relative="1" as="geometry"><Array as="points">
      <mxPoint x="60" y="140"/><mxPoint x="380" y="140"/></Array></mxGeometry></mxCell>
  <mxCell id="e_loop" edge="1" parent="1" source="a4" target="a5">
    <mxGeometry relative="1" as="geometry"><Array as="points">
      <mxPoint x="1000" y="40"/><mxPoint x="1000" y="100"/><mxPoint x="1060" y="100"/>
      <mxPoint x="1060" y="70"/><mxPoint x="940" y="70"/><mxPoint x="940" y="40"/>
      <mxPoint x="1140" y="40"/></Array></mxGeometry></mxCell>
  <mxCell id="e_back" edge="1" parent="1" source="a2" target="a1"/>
</root></mxGraphModel></diagram></mxfile>"""


def demo():
    """Self-check for the straightness + spacing warnings (validate --demo).

    Builds a figure with (a) an edge carrying a collinear waypoint, (b) an edge
    whose aligned endpoints have an unblocked straight connector yet route with
    a detour, (c) a skip edge that genuinely needs its waypoints (c2 blocks the
    straight line), (d) a lane with one stray 480px hole in the MIDDLE of an
    otherwise uniform 40px row, and (e) a lane whose only stray gap is the LAST
    one - a 180px track seam on the lane edge, which must stay silent, (f) an
    edge whose route folds back and self-intersects (a4->a5 loop knot), and
    (g) a 2-edge directed cycle (a1 -> a2 -> a1). Asserts (a) (b) (d) (f) (g)
    warn, (c) (e) stay silent.
    """
    root = ET.fromstring(DEMO_XML)
    model = next(root.iter("mxGraphModel"))
    cells = list(model.iter("mxCell"))
    ids = {c.get("id"): c for c in cells if c.get("id")}

    sw = straightness_warnings(cells, ids)
    assert any("'e_collinear'" in w and "collinear" in w for w in sw), sw
    assert any("'e_detour'" in w and "straight connector" in w for w in sw), sw
    assert not any("'e_detour'" in w and "collinear" in w for w in sw), sw
    assert not any("'e_skip'" in w for w in sw), sw

    pw = spacing_warnings(cells, ids)
    assert any("'a3'" in w and "uneven spacing" in w for w in pw), pw
    assert not any("'b1'" in w or "'b2'" in w or "'b3'" in w or "'b4'" in w
                   for w in pw), pw
    assert not any("'d1'" in w or "'d2'" in w or "'d3'" in w or "'d4'" in w
                   for w in pw), pw

    si = self_intersection_warnings(cells, ids)
    assert any("'e_loop'" in w and "self-intersect" in w for w in si), si
    assert not any("'e_skip'" in w for w in si), si

    fc = flow_cycle_warnings(cells, ids)
    assert any("directed cycle" in w and "a1" in w and "a2" in w for w in fc), fc
    assert not any("d1" in w for w in fc), fc
    print("ok")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        main()

