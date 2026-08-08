#!/usr/bin/env python3
"""Re-spread duplicated pinned edge ports in a .drawio file, byte-exact.

Companion to validate.py's "pin identical port ... same-direction peers"
warning: for every (node, side) group whose pinned slots contain duplicates,
reassign ALL ends in the group to even slots (i+1)/(k+1), ordered by the far
endpoint's position along the side axis (so edges keep their relative order
and do not cross). Ends in groups without duplicates are left untouched.

Edits are byte-exact string replacements inside each affected mxCell tag, so
CRLF line endings, tab indentation, and attribute order elsewhere in the file
are preserved (hand-authored files in this repo use CRLF+tab).

Usage:
    python3 respread_ports.py diagram.drawio            # in place
    python3 respread_ports.py diagram.drawio --dry-run  # report only
"""
import argparse
import importlib.util
import os
import re
import sys
import xml.etree.ElementTree as ET

_spec = importlib.util.spec_from_file_location(
    "validate", os.path.join(os.path.dirname(os.path.abspath(__file__)), "validate.py"))
validate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(validate)


def groups_with_dupes(cells, by_id):
    """{(node, side): [(edge_id, end, peer_id), ...]} for groups whose pinned
    slots contain duplicates (all ends must be pinned - unpinned groups are
    edgeports.py's job)."""
    groups = {}
    for e in cells:
        if e.get("edge") != "1":
            continue
        for end in ("source", "target"):
            node = e.get(end)
            if not node:
                continue
            side, slot = validate._side_of(e, end, by_id)
            if side is None or slot is None:
                continue
            peer = e.get("target" if end == "source" else "source")
            groups.setdefault((node, side), []).append((e.get("id"), end, slot, peer))
    out = {}
    for key, ends in groups.items():
        if len(ends) < 2:
            continue
        slots = [s for _, _, s, _ in ends]
        if len(set(slots)) < len(slots):
            out[key] = ends
    return out


def respread(cells, by_id):
    """{(edge_id, end): (px, py)} new port assignments for duplicated groups."""
    plan = {}
    for (node, side), ends in groups_with_dupes(cells, by_id).items():
        along_x = side in ("N", "S")     # slot fills X; fixed Y = 0/1
        fixed = 0.0 if side in ("N", "W") else 1.0

        def peer_pos(peer_id):
            r = validate.abs_rect(by_id[peer_id], by_id) if peer_id in by_id else None
            if not r:
                return 0.0
            c = (r[0] + r[2] / 2, r[1] + r[3] / 2)
            return c[0] if along_x else c[1]

        ends = sorted(ends, key=lambda t: (peer_pos(t[3]), t[0]))
        k = len(ends)
        for i, (eid, end, _, _) in enumerate(ends):
            slot = (i + 1) / float(k + 1)
            plan[(eid, end)] = (slot, fixed) if along_x else (fixed, slot)
    return plan


def apply_byte_exact(text, plan):
    """Rewrite the port attributes inside each planned edge's mxCell tag."""
    for (eid, end), (px, py) in plan.items():
        m = re.search(r'<mxCell\b[^>]*\bid="%s"[^>]*>' % re.escape(eid), text)
        if not m:
            print(f"warning: cell {eid!r} tag not found, skipped", file=sys.stderr)
            continue
        tag = m.group(0)
        prefix = "exit" if end == "source" else "entry"
        new = re.sub(r'%sX=[0-9.]+' % prefix, f"{prefix}X={px:.3f}", tag)
        new = re.sub(r'%sY=[0-9.]+' % prefix, f"{prefix}Y={py:.3f}", new)
        if new == tag:
            print(f"warning: cell {eid!r} has no {prefix}X/Y attrs, skipped",
                  file=sys.stderr)
            continue
        text = text.replace(tag, new, 1)
    return text


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tree = ET.parse(args.file)
    total = 0
    plans = []
    for model in tree.getroot().iter("mxGraphModel"):
        cells = list(model.iter("mxCell"))
        by_id = {c.get("id"): c for c in cells if c.get("id")}
        plan = respread(cells, by_id)
        plans.append(plan)
        total += len(plan)
    if args.dry_run:
        for plan in plans:
            for (eid, end), (px, py) in sorted(plan.items()):
                print(f"{eid}: {end} -> ({px:.3f}, {py:.3f})")
        print(f"{total} edge end(s) would be re-spread in {args.file}")
        return
    with open(args.file, encoding="utf-8", newline="") as f:
        text = f.read()
    for plan in plans:
        text = apply_byte_exact(text, plan)
    with open(args.file, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print(f"{total} edge end(s) re-spread -> {args.file}")


if __name__ == "__main__":
    main()
