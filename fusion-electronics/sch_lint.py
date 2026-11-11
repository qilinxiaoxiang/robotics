"""Generic acceptance checks for an EAGLE .sch that will be uploaded to Fusion Electronics.

Each check encodes a failure seen on a real import (2026-11-11, 18-021 Logic Display Shield):
  format    library <atts>/<att_values>/<att_sets> blocks: Fusion says "has errors and cannot be opened"
  format    groups must be <groups><schematic_group> at schematic level; inside a sheet's <plain>
            Fusion drops them silently
  display   Fusion smashes instances on import; without explicit NAME/VALUE <attribute> children
            no designators or values show
  display   layer 93 (Pins) visible draws pin-direction circles on every pin
  geometry  every pinref must sit on a wire end of its own segment; no two nets may touch
  layout    group frames (Fusion encloses pins, wires, labels and smashed text) must not overlap,
            and no label or NAME/VALUE text may collide with another
It checks the file only. Run it on your generated file and on Fusion's own export of the uploaded
design (fusion.sh image/run + exportManager) for the real acceptance.

Usage: python3 sch_lint.py FILE.sch      (exit 1 on any failure)
Library: from sch_lint import lint; fails, ctx = lint(path)   # ctx["got"] = {(part, pin): net}
"""
import sys
import xml.etree.ElementTree as ET

FORBIDDEN_TAGS = ("atts", "att_values", "att_sets")
FRAME_GAP = 5.08        # mm between frame models sideways; twice that vertically (title row)
TEXT_CLEAR = 0.5        # mm between any two texts


def text_w(s, size):
    """EAGLE vector font, conservative: about 0.9 x size per character."""
    return len(s) * size * 0.9


LABEL_REACH = 2.54      # a label's anchor must lie this close to a wire of its own segment


def _dist(p, w):
    (x1, y1), (x2, y2) = w
    dx, dy = x2 - x1, y2 - y1
    t = 0 if dx == dy == 0 else max(0, min(1, ((p[0] - x1) * dx + (p[1] - y1) * dy) / (dx * dx + dy * dy)))
    return ((p[0] - x1 - t * dx) ** 2 + (p[1] - y1 - t * dy) ** 2) ** 0.5


def _components(ws):
    """Connected pieces among wires; wires join at shared ends or an end on another wire."""
    parent = list(range(len(ws)))
    def f(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for i, a in enumerate(ws):
        for j, b in enumerate(ws[:i]):
            if any(_dist(e, b) < 1e-3 for e in a) or any(_dist(e, a) < 1e-3 for e in b):
                parent[f(i)] = f(j)
    return len({f(i) for i in range(len(ws))})


def _rot(p, r):
    x, y = p
    return {0: (x, y), 90: (-y, x), 180: (-x, -y), 270: (y, -x)}[r]


def lint(path):
    root = ET.parse(path).getroot()
    sch = root.find(".//schematic")
    fail = []

    bad = sorted({e.tag for e in root.iter() if e.tag in FORBIDDEN_TAGS})
    if bad:
        fail.append(f"format: Fusion rejects these library tags inside a schematic: {bad}")
    declared = {g.get("name") for g in sch.findall("groups/schematic_group")}
    misplaced = [g.get("name") for g in sch.iter("schematic_group") if g.get("name") not in declared
                 or g not in list(sch.findall("groups/schematic_group"))]
    if misplaced:
        fail.append(f"format: schematic_group outside schematic-level <groups> (Fusion drops it): {misplaced}")
    used = {r for e in sch.iter() for r in (e.get("grouprefs") or "").split()}
    if used - declared:
        fail.append(f"format: grouprefs name undeclared groups: {sorted(used - declared)}")
    layers = {L.get("number"): L for L in root.iter("layer")}
    if layers and ("93" not in layers or layers["93"].get("visible") != "no"):
        fail.append("display: layer 93 (Pins) is missing or visible; pin-direction circles will show")

    sym_pins, gate_sym = {}, {}
    for L in sch.iter("library"):
        for s in L.iter("symbol"):
            sym_pins[(L.get("name"), s.get("name"))] = {
                p.get("name"): (float(p.get("x")), float(p.get("y"))) for p in s.iter("pin")}
        for ds in L.iter("deviceset"):
            g = ds.find("gates/gate")
            gate_sym[(L.get("name"), ds.get("name"))] = g.get("symbol")
    parts = {p.get("name"): p for p in sch.iter("part")}

    pinpos = {}
    orphans = [i.get("part") for i in sch.iter("instance") if i.get("part") not in parts]
    if orphans:
        fail.append(f"format: instances refer to parts that do not exist: {orphans}")
        return fail, {"root": root, "sch": sch, "parts": parts, "pinpos": {}, "got": {}, "groups": set(), "frames": {}}
    for i in sch.iter("instance"):
        p = parts[i.get("part")]
        pins = sym_pins[(p.get("library"), gate_sym[(p.get("library"), p.get("deviceset"))])]
        rs = i.get("rot") or "R0"
        mirror, r = "M" in rs, int(rs.lstrip("SMR"))
        for n, (px, py) in pins.items():
            dx, dy = _rot((-px if mirror else px, py), r)   # EAGLE mirrors about the y axis, then rotates
            pinpos[(i.get("part"), n)] = (round(float(i.get("x")) + dx, 4), round(float(i.get("y")) + dy, 4))

    got, endpoints, all_wires = {}, {}, []
    for net in sch.iter("net"):
        name = net.get("name")
        for seg in net.iter("segment"):
            ends, segw = set(), []
            for w in seg.iter("wire"):
                a = (round(float(w.get("x1")), 4), round(float(w.get("y1")), 4))
                b = (round(float(w.get("x2")), 4), round(float(w.get("y2")), 4))
                ends |= {a, b}
                segw.append((a, b))
                all_wires.append((name, a, b))
                for e in (a, b):
                    endpoints.setdefault(e, set()).add(name)
            for pr in seg.iter("pinref"):
                k = (pr.get("part"), pr.get("pin"))
                got[k] = name
                if pinpos.get(k) not in ends:
                    fail.append(f"geometry: {k} at {pinpos.get(k)} not on a wire end of net {name}")
            if segw and _components(segw) > 1:
                fail.append(f"geometry: a segment of net {name} is split into {_components(segw)} disjoint pieces")
            for lb in seg.iter("label"):
                lx, ly = float(lb.get("x")), float(lb.get("y"))
                d, (a, b) = min((_dist((lx, ly), w), w) for w in segw) if segw else (1e9, ((0, 0), (0, 0)))
                if d > LABEL_REACH:
                    fail.append(f"geometry: label {name} at ({lx}, {ly}) is {d:.1f} mm from its own wires")
                horiz = abs(a[1] - b[1]) < 1e-6
                rot = (lb.get("rot") or "R0").lstrip("SM")
                if (rot in ("R0", "R180")) != horiz:
                    fail.append(f"display: label {name} rotated {rot} on a {'horizontal' if horiz else 'vertical'} wire")
    for e, ns in endpoints.items():
        if len(ns) > 1:
            fail.append(f"geometry: nets {sorted(ns)} touch at {e}")
    for e, ns in endpoints.items():          # a wire end on the middle of another net's wire looks shorted
        for name, a, b in all_wires:
            if name not in ns and e not in (a, b) and _dist(e, (a, b)) < 1e-3:
                fail.append(f"geometry: net {sorted(ns)} ends on the middle of a {name} wire at {e}")

    for i in sch.iter("instance"):
        names = {a.get("name") for a in i.iter("attribute")}
        supply = parts[i.get("part")].get("library", "").lower().startswith(("power", "supply"))
        need = {"VALUE"} if supply else {"NAME", "VALUE"}
        if not need <= names:   # Fusion smashes every instance on import; without these nothing shows
            fail.append(f"display: instance {i.get('part')} lacks {sorted(need - names)} attributes")
    groups = {g.get("name") for g in sch.iter("schematic_group")}
    if groups:
        ungrouped = [i.get("part") for i in sch.iter("instance") if not i.get("grouprefs")]
        if ungrouped:
            fail.append(f"layout: instances without group: {ungrouped}")

    # layout: frame models and text boxes
    frames, texts = {}, []

    def grow(g, x0, y0, x1, y1):
        if g:
            b = frames.setdefault(g, [x0, y0, x1, y1])
            b[:] = [min(b[0], x0), min(b[1], y0), max(b[2], x1), max(b[3], y1)]

    def grow_text(g, s, x, y, sz, rot, what=None):
        w = text_w(s, sz)
        box = (x - w, y - sz, x, y) if rot == "R180" else (x, y, x + w, y + sz)
        grow(g, *box)
        if what:
            texts.append((what, box))

    inst_group = {i.get("part"): i.get("grouprefs") for i in sch.iter("instance")}
    for (part, _), (x, y) in pinpos.items():
        grow(inst_group.get(part), x, y, x, y)
    for w in sch.iter("wire"):
        if w.get("layer") == "91":
            xs, ys = (float(w.get("x1")), float(w.get("x2"))), (float(w.get("y1")), float(w.get("y2")))
            grow(w.get("grouprefs"), min(xs), min(ys), max(xs), max(ys))
    values = {p.get("name"): p.get("value") or p.get("deviceset") for p in sch.iter("part")}
    for i in sch.iter("instance"):
        for a in i.iter("attribute"):
            if a.get("x") is not None and a.get("display") != "off":
                s = i.get("part") if a.get("name") == "NAME" else values.get(i.get("part"), "")
                grow_text(i.get("grouprefs"), s, float(a.get("x")), float(a.get("y")),
                          float(a.get("size", 1.778)), a.get("rot"), f"{i.get('part')} {a.get('name')} '{s}'")
    for net in sch.iter("net"):
        for lb in net.iter("label"):
            grow_text(lb.get("grouprefs"), net.get("name"), float(lb.get("x")), float(lb.get("y")),
                      float(lb.get("size")), lb.get("rot"), f"label '{net.get('name')}'")
    plain = sch.find(".//sheet/plain")
    for t in (plain.iter("text") if plain is not None else []):
        grow_text(t.get("grouprefs"), t.text or "", float(t.get("x")), float(t.get("y")),
                  float(t.get("size")), t.get("rot"), f"text '{(t.text or '')[:20]}'")
    names = sorted(frames)
    for n, a in enumerate(names):
        for b in names[n + 1:]:
            A, B = frames[a], frames[b]
            if (A[0] < B[2] + FRAME_GAP and B[0] < A[2] + FRAME_GAP
                    and A[1] < B[3] + 2 * FRAME_GAP and B[1] < A[3] + 2 * FRAME_GAP):
                fail.append(f"layout: group frames {a} and {b} overlap or touch")
    c = TEXT_CLEAR
    for n, (wa, A) in enumerate(texts):
        for wb, B in texts[n + 1:]:
            if A[0] < B[2] + c and B[0] < A[2] + c and A[1] < B[3] + c and B[1] < A[3] + c:
                fail.append(f"layout: text collides: {wa} and {wb}")

    return fail, {"root": root, "sch": sch, "parts": parts, "pinpos": pinpos, "got": got,
                  "groups": groups, "frames": frames}


if __name__ == "__main__":
    fails, ctx = lint(sys.argv[1])
    print(f"{len(ctx['got'])} pin connections, {len(ctx['groups'])} groups")
    print("\n".join(fails) if fails else "PASS: format, display, geometry, layout")
    sys.exit(1 if fails else 0)
