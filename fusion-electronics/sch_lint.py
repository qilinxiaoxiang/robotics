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
    if sch.find("groups/schematic_group") is None and any(e.get("grouprefs") for e in sch.iter()):
        fail.append("format: grouprefs used but no <groups><schematic_group> at schematic level; Fusion drops them")
    for L in root.iter("layer"):
        if L.get("number") == "93" and L.get("visible") != "no":
            fail.append("display: layer 93 (Pins) is visible; pin-direction circles will show")

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
    for i in sch.iter("instance"):
        p = parts[i.get("part")]
        pins = sym_pins[(p.get("library"), gate_sym[(p.get("library"), p.get("deviceset"))])]
        r = int((i.get("rot") or "R0").lstrip("MR"))
        for n, xy in pins.items():
            dx, dy = _rot(xy, r)
            pinpos[(i.get("part"), n)] = (round(float(i.get("x")) + dx, 3), round(float(i.get("y")) + dy, 3))

    got, endpoints = {}, {}
    for net in sch.iter("net"):
        for seg in net.iter("segment"):
            ends = set()
            for w in seg.iter("wire"):
                a = (round(float(w.get("x1")), 3), round(float(w.get("y1")), 3))
                b = (round(float(w.get("x2")), 3), round(float(w.get("y2")), 3))
                ends |= {a, b}
                for e in (a, b):
                    endpoints.setdefault(e, set()).add(net.get("name"))
            for pr in seg.iter("pinref"):
                k = (pr.get("part"), pr.get("pin"))
                got[k] = net.get("name")
                if pinpos.get(k) not in ends:
                    fail.append(f"geometry: {k} at {pinpos.get(k)} not on a wire end of net {net.get('name')}")
    for e, ns in endpoints.items():
        if len(ns) > 1:
            fail.append(f"geometry: nets {sorted(ns)} touch at {e}")

    for i in sch.iter("instance"):
        names = {a.get("name") for a in i.iter("attribute")}
        supply = parts[i.get("part")].get("library", "").lower().startswith(("power", "supply"))
        need = {"VALUE"} if supply else {"NAME", "VALUE"}
        if i.get("smashed") == "yes" and not need <= names:
            fail.append(f"display: smashed instance {i.get('part')} lacks {sorted(need - names)} attributes")
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
    for t in sch.iter("text"):
        if t.get("grouprefs"):
            grow_text(t.get("grouprefs"), t.text or "", float(t.get("x")), float(t.get("y")),
                      float(t.get("size")), t.get("rot"))
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
