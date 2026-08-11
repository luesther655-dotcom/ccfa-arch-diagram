#!/usr/bin/env python3
"""Deterministically fix the layout defects that validate.py's semantic
invariants detect (ccfa-arch-diagram edition).

validate.py grew a class of *intent* checks - an arrow stabbing through its own
node to a far-side port, an op circle whose outgoing arrow leaves the wrong
side, and a corridor element off-centre in a symmetric-U figure - that were
previously only catchable by looking at a rendered PNG. Each is mechanical to
correct, so this tool closes the loop: detect -> auto-fix -> re-check until
stable, the way edgeports.py closes the port-stacking loop.

What is auto-fixed:
  - off-centre corridor element (recipe)   : re-centre x on the corridor
  - through-the-node edge (generic)        : flip the entry/exit port to the
                                             side the route actually approaches,
                                             and pull the adjacent waypoint clear
  - op circle wrong exit side (generic)    : repoint the exit port to the side
                                             the glyph promises (up-conv -> N,
                                             down-sample -> S)
  - wrap-around edge (generic)             : flip the entry side to the face
                                             that actually points at the source,
                                             killing the 打环 loop detour
  - misaligned straight pair (generic)     : slot both ports to the shared
                                             height/width so the router emits a
                                             single straight connector
  - formula not bold (generic)             : set fontStyle=1 on math cells
  - port pinned on a scrambled cube        : drop direction=south (back to the
    (generic)                              north default) so cubePerimeter
                                             honours the pins

What is only reported (needs a human hand, or is outside this pass's remit):
  mirror misalignment, non-horizontal skips, density floors, and any residual
  route defects - run validate again after fixing to confirm.

Idempotent: fixes only fire while a violation exists, so a second run is a
no-op. Dry-run by default; pass --apply to write.

Usage:
    python3 fix_layout.py unet.drawio --recipe symmetric_u          # dry-run
    python3 fix_layout.py unet.drawio --recipe symmetric_u --apply  # write in place
    python3 fix_layout.py unet.drawio --apply -o fixed.drawio
"""

import argparse
import importlib.util
import json
import os
import sys
import xml.etree.ElementTree as ET

_spec = importlib.util.spec_from_file_location(
    "validate", os.path.join(os.path.dirname(os.path.abspath(__file__)), "validate.py"))
validate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate)

OPPOSITE = {"N": "S", "S": "N", "E": "W", "W": "E"}
PORT_CLEARANCE = 16       # px an auto-nudged waypoint keeps clear of the box
MAX_PASSES = 4            # detect -> fix loop cap (each pass is deterministic)


def set_port(style, end, px, py):
    """Return style with this end's port keys set, other keys preserved."""
    prefix = "exit" if end == "source" else "entry"
    drop = {prefix + "X", prefix + "Y", prefix + "Dx", prefix + "Dy"}
    parts = [p for p in (style or "").split(";")
             if p and p.split("=", 1)[0] not in drop]
    parts += [f"{prefix}X={px:g}", f"{prefix}Y={py:g}",
              f"{prefix}Dx=0", f"{prefix}Dy=0"]
    return ";".join(parts) + ";"


def _style_drop(style, key):
    """Return style with every token whose key == ``key`` removed."""
    parts = [p for p in (style or "").split(";")
             if p and p.split("=", 1)[0] != key]
    return ";".join(parts) + ";"


def _style_set_num(style, key, value):
    """Return style with numeric token ``key=value`` set (replacing any old)."""
    parts = [p for p in (style or "").split(";")
             if p and p.split("=", 1)[0] != key]
    parts.append(f"{key}={value:g}")
    return ";".join(parts) + ";"


def _facing_side(s, box):
    """The target side whose outward normal points toward exit point ``s``.

    Prefer the side on the axis where ``s`` lies in front of the box (left of
    the left face, above the top face, ...); fall back to the dominant axis of
    the displacement from the box centre for diagonal approaches."""
    x, y, w, h = box
    left, right, top, bot = x, x + w, y, y + h
    if s[0] < left and top - 1 <= s[1] <= bot + 1:
        return "W"
    if s[0] > right and top - 1 <= s[1] <= bot + 1:
        return "E"
    if s[1] < top and left - 1 <= s[0] <= right + 1:
        return "N"
    if s[1] > bot and left - 1 <= s[0] <= right + 1:
        return "S"
    dx = s[0] - (x + w / 2.0)
    dy = s[1] - (y + h / 2.0)
    if abs(dx) >= abs(dy):
        return "W" if dx < 0 else "E"
    return "N" if dy < 0 else "S"


def _side_port(style, side):
    """(px, py) pins for an entry port on ``side``, preserving the current
    cross-axis fraction so the arrow keeps its vertical/horizontal slot."""
    if side == "W":
        return 0.0, (validate.style_num(style, "entryY") or 0.5)
    if side == "E":
        return 1.0, (validate.style_num(style, "entryY") or 0.5)
    if side == "N":
        return (validate.style_num(style, "entryX") or 0.5), 0.0
    return (validate.style_num(style, "entryX") or 0.5), 1.0


def _move_point(point, side, box):
    """Set an mxPoint clear of ``box`` on ``side``; returns a human hint."""
    x, y, w, h = box
    if side == "W":
        point.set("x", f"{x - PORT_CLEARANCE:g}")
        return f"waypoint to x={x - PORT_CLEARANCE:g}"
    if side == "E":
        point.set("x", f"{x + w + PORT_CLEARANCE:g}")
        return f"waypoint to x={x + w + PORT_CLEARANCE:g}"
    if side == "N":
        point.set("y", f"{y - PORT_CLEARANCE:g}")
        return f"waypoint to y={y - PORT_CLEARANCE:g}"
    point.set("y", f"{y + h + PORT_CLEARANCE:g}")
    return f"waypoint to y={y + h + PORT_CLEARANCE:g}"


def _waypoint(edge, end):
    """The mxPoint adjacent to ``end`` (last for target, first for source)."""
    arr = edge.find("mxGeometry/Array")
    if arr is None:
        return None
    pts = arr.findall("mxPoint")
    if not pts:
        return None
    return pts[-1] if end == "target" else pts[0]


def apply_pass(cells, ids, recipe):
    """Apply every currently-detectable fix. Returns (applied, blocked) where
    applied is a list of human-readable fix descriptions and blocked lists the
    violations that need a hand (mirror/skip/density/bottleneck-height)."""
    applied, blocked = [], []

    # --- corridor centering (recipe) --------------------------------------
    if recipe is None:
        recipe = {}
    for v in validate.recipe_violations(cells, ids, recipe):
        if v["kind"] == "centering":
            cell = ids.get(v["fix"]["id"])
            if cell is not None:
                g = cell.find("mxGeometry")
                old = g.get("x")
                g.set("x", f"{v['fix']['new_x']:g}")
                applied.append(f"centred {v['fix']['id']!r}: x {old} -> "
                               f"{g.get('x')}")
        else:
            blocked.append(v["detail"])

    # --- port pinned on a scrambled cube (generic) --------------------------
    # cubePerimeter re-projects ports when direction=south; reverting to the
    # north default makes the pins land where the guide's rule says they do.
    fixed_cubes = set()
    for v in validate.cube_port_violations(cells, ids):
        cube = ids.get(v["vertex"])
        if cube is None or v["vertex"] in fixed_cubes:
            continue
        style = cube.get("style") or ""
        newstyle = _style_drop(style, "direction")
        cube.set("style", newstyle)
        fixed_cubes.add(v["vertex"])
        applied.append(
            f"cube {v['vertex']!r} dropped 'direction=south' (reverted to "
            f"north) so cubePerimeter stops re-projecting pinned ports")

    # --- through-the-node edge ends ----------------------------------------
    for v in validate.through_target_violations(cells, ids):
        edge = ids.get(v["edge"])
        if edge is None:
            continue
        bad = v["bad_side"]
        fix_side = OPPOSITE[bad]
        style = edge.get("style") or ""
        end = v["end"]
        if end == "target":
            cur_x = validate.style_num(style, "entryX")
            cur_y = validate.style_num(style, "entryY")
            if bad in ("E", "W"):
                edge.set("style", set_port(style, "target",
                                           (0.0 if bad == "E" else 1.0),
                                           cur_y if cur_y is not None else 0.5))
            else:
                edge.set("style", set_port(style, "target",
                                           cur_x if cur_x is not None else 0.5,
                                           (1.0 if bad == "N" else 0.0)))
        else:
            cur_x = validate.style_num(style, "exitX")
            cur_y = validate.style_num(style, "exitY")
            if bad in ("E", "W"):
                edge.set("style", set_port(style, "source",
                                           (0.0 if bad == "E" else 1.0),
                                           cur_y if cur_y is not None else 0.5))
            else:
                edge.set("style", set_port(style, "source",
                                           cur_x if cur_x is not None else 0.5,
                                           (1.0 if bad == "N" else 0.0)))
        hint = ""
        wp = _waypoint(edge, end)
        if wp is not None:
            hint = ", " + _move_point(wp, fix_side, v["box"])
        applied.append(f"edge {v['edge']!r} {end} side {bad} -> {fix_side}"
                       f"{hint} (was running through {v['node']!r})")

    # --- op circle output direction -----------------------------------------
    for v in validate.op_direction_violations(cells, ids):
        edge = ids.get(v["edge"])
        if edge is None:
            continue
        style = edge.get("style") or ""
        expected = v["expected"]
        px, py = (0.5, 0.0) if expected == "N" else (0.5, 1.0)
        edge.set("style", set_port(style, "source", px, py))
        applied.append(f"op circle {v['circle']!r} out-edge {v['edge']!r} "
                       f"exit port -> {expected}")

    # --- wrap-around edge (generic): entry faces the source ------------------
    # Entry on a side whose normal points away from the source makes draw.io
    # orbit the whole target (打环). Repoint the entry to the face the source
    # actually stands in front of, keeping the cross-axis slot.
    for v in validate.port_facing_violations(cells, ids):
        edge = ids.get(v["edge"])
        tbox = validate.abs_rect(ids.get(v["target"]), ids) if v["target"] in ids else None
        if edge is None or tbox is None:
            continue
        style = edge.get("style") or ""
        side = _facing_side(v["s"], tbox)
        if side == v["in_side"]:
            continue  # geometry shifted; nothing to do this pass
        px, py = _side_port(style, side)
        edge.set("style", set_port(style, "target", px, py))
        applied.append(f"edge {v['edge']!r} entry {v['in_side']} -> {side} "
                       f"(was wrapping around {v['target']!r} because the "
                       f"entry face pointed away from the source)")

    # --- misaligned straight pair (generic): slot ports to shared axis -------
    for v in validate.port_alignment_violations(cells, ids):
        edge = ids.get(v["edge"])
        if edge is None:
            continue
        style = edge.get("style") or ""
        if v["axis"] == "H":
            ex = validate.style_num(style, "exitX")
            nx = validate.style_num(style, "entryX")
            if ex is None or nx is None:
                continue
            _, _, _, sh = v["src_rect"]
            _, _, _, th = v["tgt_rect"]
            ey = (v["shared"] - v["src_rect"][1]) / sh
            ny = (v["shared"] - v["tgt_rect"][1]) / th
            style = set_port(style, "source", ex, ey)
            style = set_port(style, "target", nx, ny)
            edge.set("style", style)
            applied.append(
                f"edge {v['edge']!r} ports aligned to shared y="
                f"{v['shared']:g} (straight connector between {v['source']!r} "
                f"and {v['target']!r})")
        else:
            ex = validate.style_num(style, "exitX")
            nx = validate.style_num(style, "entryX")
            if ex is None or nx is None:
                continue
            _, sw, _, _ = v["src_rect"]
            _, tw, _, _ = v["tgt_rect"]
            ey = validate.style_num(style, "exitY")
            ny = validate.style_num(style, "entryY")
            if ey is None or ny is None:
                continue
            ex = (v["shared"] - v["src_rect"][0]) / sw
            nx = (v["shared"] - v["tgt_rect"][0]) / tw
            style = set_port(style, "source", ex, ey)
            style = set_port(style, "target", nx, ny)
            edge.set("style", style)
            applied.append(
                f"edge {v['edge']!r} ports aligned to shared x="
                f"{v['shared']:g} (straight connector between {v['source']!r} "
                f"and {v['target']!r})")

    # --- formula not bold (generic): fontStyle bit 1 -------------------------
    for v in validate.formula_bold_violations(cells):
        cell = ids.get(v["id"])
        if cell is None:
            continue
        style = cell.get("style") or ""
        fs = int(validate.style_num(style, "fontStyle") or 0)
        if fs & 1:
            continue  # became bold earlier in this run
        cell.set("style", _style_set_num(style, "fontStyle", fs | 1))
        applied.append(f"formula cell {v['id']!r} fontStyle {fs} -> {fs | 1} "
                       f"(bold)")

    return applied, blocked


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", help="input .drawio")
    ap.add_argument("--recipe", metavar="NAME",
                    help="archetype recipe (enables corridor-centring fixes)")
    ap.add_argument("--apply", action="store_true",
                    help="write the fixes (default: dry-run, print only)")
    ap.add_argument("-o", "--output", help="output path (default: edit in place)")
    args = ap.parse_args()

    try:
        tree = ET.parse(args.file)
    except ET.ParseError as exc:
        sys.exit(f"error: {args.file} is not parseable XML ({exc}). "
                 "Compressed .drawio files must be saved uncompressed first.")

    recipe = None
    if args.recipe:
        recipe = validate.load_recipe(
            args.recipe, os.path.dirname(os.path.abspath(__file__)))

    all_applied, all_blocked = [], []
    for _ in range(MAX_PASSES):
        model = next(tree.getroot().iter("mxGraphModel"), None)
        if model is None:
            break
        cells = list(model.iter("mxCell"))
        ids = {c.get("id"): c for c in cells if c.get("id")}
        applied, blocked = apply_pass(cells, ids, recipe)
        all_applied += applied
        all_blocked += blocked
        if not applied:
            break

    for line in all_applied:
        print(f"fix: {line}")
    for line in dict.fromkeys(all_blocked):
        print(f"needs hand: {line}")
    if not all_applied and not all_blocked:
        print("no layout defects found")

    if not args.apply:
        if all_applied:
            print(f"{len(all_applied)} fix(es) proposed - rerun with --apply to "
                  f"write")
        return

    out = args.output or args.file
    tree.write(out, encoding="utf-8", xml_declaration=False)
    print(f"wrote {out} ({len(all_applied)} fix(es) applied)")


DEMO_RECIPE = {
    "name": "demo_u",
    "arms": ["enc", "dec"],
    "corridor": {"centered": "bot", "tol_px": 10},
    "mirror_pairs": [],
    "horizontal_edges": [],
}

DEMO_XML = """<mxfile><diagram><mxGraphModel><root>
  <mxCell id="0"/><mxCell id="1" parent="0"/>
  <mxCell id="enc" vertex="1" parent="1">
    <mxGeometry x="100" y="80" width="200" height="300" as="geometry"/></mxCell>
  <mxCell id="dec" vertex="1" parent="1">
    <mxGeometry x="480" y="80" width="200" height="300" as="geometry"/></mxCell>
  <mxCell id="bot" vertex="1" parent="1">
    <mxGeometry x="380" y="420" width="90" height="40" as="geometry"/></mxCell>
  <mxCell id="up" value="↑" style="ellipse;fillColor=#FFFFFF;strokeColor=#5F6368;"
         vertex="1" parent="1">
    <mxGeometry x="545" y="330" width="30" height="30" as="geometry"/></mxCell>
  <mxCell id="up_out" value="" style="edgeStyle=orthogonalEdgeStyle;exitX=0.5;exitY=1;"
         edge="1" parent="1" source="up" target="dec">
    <mxGeometry relative="1" as="geometry"/></mxCell>
  <mxCell id="stab" value=""
         style="edgeStyle=orthogonalEdgeStyle;exitX=0.5;exitY=1;entryX=1;entryY=0.5;"
         edge="1" parent="1" source="bot" target="up">
    <mxGeometry relative="1" as="geometry"><Array as="points">
      <mxPoint x="460" y="345"/></Array>
    </mxGeometry></mxCell>
</root></mxGraphModel></diagram></mxfile>"""


def demo():
    """Self-check: one pass fixes all three defect classes and leaves no
    residual intent violation (corridor re-centring, op-circle exit port, and
    the stab-through-the-node entry)."""
    root = ET.fromstring(DEMO_XML)
    model = next(root.iter("mxGraphModel"))
    cells = list(model.iter("mxCell"))
    ids = {c.get("id"): c for c in cells if c.get("id")}
    recipe = DEMO_RECIPE
    applied, blocked = apply_pass(cells, ids, recipe)

    # off-centre bottleneck (centre 425 vs corridor 390) re-centred
    assert not [a for a in applied if "centred 'bot'" in a] \
        is False, applied
    assert any("centred 'bot'" in a for a in applied), applied
    assert ids["bot"].find("mxGeometry").get("x") == "345"
    # up-conv circle whose out edge exited S repointed to N
    assert any("exit port -> N" in a for a in applied), applied
    assert "exitY=0" in (ids["up_out"].get("style") or "")
    # stabbing entry (E side, approached from the left) flipped to W, waypoint
    # pulled clear of the circle
    assert any("E -> W" in a for a in applied), applied
    assert "entryX=0" in (ids["stab"].get("style") or "")
    last = ids["stab"].find("mxGeometry/Array").findall("mxPoint")[-1]
    assert last.get("x") == "529", last.get("x")

    # residual intent violations are gone
    assert not validate.through_target_violations(cells, ids), \
        validate.through_target_violations(cells, ids)
    assert not validate.op_direction_violations(cells, ids), \
        validate.op_direction_violations(cells, ids)
    assert not [v for v in validate.recipe_violations(cells, ids, recipe)
                if v["kind"] == "centering"], \
        validate.recipe_violations(cells, ids, recipe)
    print("ok")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        main()
