#!/usr/bin/env python3
"""Generate the head USB board schematic (EAGLE 9.7.0 .sch for Fusion Electronics) from netlist.py.

Style: every part is a box symbol with its real pin numbers and names; every connected pin gets a short wire stub
with a net label, so a net is read by name, not by tracing lines. Parts are packed into titled groups.
Stage 1 has symbols only (no packages); footprints are added before layout.

Run: python3 gen_sch.py OUT.sch    (then sch_lint.py and check_netlist.py)
"""
import math
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import netlist as NL

G = 2.54
PITCH = 2 * G            # pin pitch on a box, leaves room for a label above each stub
PINLEN = G               # EAGLE "short" pin
LABEL = 1.778            # label text size
LABEL_DY = 1.016         # label baseline above its wire
CHAR = 0.9               # vector font cell width per unit of size (conservative)
GROUP_GAP = 6 * G
LIB = "duck_head_usb"


def r4(v):
    return round(v + 0.0, 4)


def fmt(v):
    s = f"{v:.4f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def text_w(s, size):
    return len(s) * size * CHAR


def stub_len(net):
    return G * math.ceil((text_w(net, LABEL) + 2 * 1.27) / G)


class Kind:
    """One symbol: pins split left and right in netlist order."""

    def __init__(self, name, pins):
        self.name = name
        self.pins = pins                              # [(number, pin name, side)]
        self.left = [p for p in pins if p[2] == "L"]
        self.right = [p for p in pins if p[2] == "R"]
        rows = max(len(self.left), len(self.right), 1)
        wl = max([text_w(self.pname(p), 1.524) for p in self.left] or [0])
        wr = max([text_w(self.pname(p), 1.524) for p in self.right] or [0])
        self.w = G * math.ceil((wl + wr + 3 * G) / G)
        self.h = PITCH * rows
        self.pos = {}
        for side, x, plist in (("L", -PINLEN, self.left), ("R", self.w + PINLEN, self.right)):
            for i, p in enumerate(plist):
                self.pos[self.pname(p)] = (r4(x), r4(self.h - PITCH / 2 - i * PITCH), side)

    @staticmethod
    def pname(p):
        return f"{p[0]}_{p[1]}" if p[0] is not None else p[1]

    def symbol(self):
        s = ET.Element("symbol", name=self.name)
        for (x1, y1, x2, y2) in ((0, 0, self.w, 0), (self.w, 0, self.w, self.h), (self.w, self.h, 0, self.h), (0, self.h, 0, 0)):
            ET.SubElement(s, "wire", x1=fmt(x1), y1=fmt(y1), x2=fmt(x2), y2=fmt(y2), width="0.254", layer="94")
        ET.SubElement(s, "text", x="0", y=fmt(self.h + 3.2), size="1.778", layer="95").text = ">NAME"
        ET.SubElement(s, "text", x="0", y=fmt(self.h + 0.8), size="1.778", layer="96").text = ">VALUE"
        for p in self.pins:
            x, y, side = self.pos[self.pname(p)]
            a = {"name": self.pname(p), "x": fmt(x), "y": fmt(y), "visible": "pin", "length": "short"}
            if side == "R":
                a["rot"] = "R180"
            ET.SubElement(s, "pin", a)
        return s


def build():
    kinds = {k: Kind(k, pins) for k, pins in NL.KINDS.items()}
    parts, wires, labels, groups = [], [], [], {}
    for gname, members in NL.GROUPS.items():
        # lay the group's parts out in a row, bottom aligned; group origin (0, 0), packed later
        # big parts in a row; small parts (two rows of pins or fewer) stacked in columns to their right
        x = 0.0
        items = []
        slots = []
        for ref, kind, value, conn in members:
            k = kinds[kind]
            lw = max([stub_len(conn[k.pname(p)]) for p in k.left if conn.get(k.pname(p))] or [0])
            rw = max([stub_len(conn[k.pname(p)]) for p in k.right if conn.get(k.pname(p))] or [0])
            unknown = set(conn) - set(k.pos)
            missing = set(k.pos) - set(conn)
            if unknown or missing:
                raise SystemExit(f"{ref}: pins not in {kind}: {sorted(unknown)}; pins without an entry: {sorted(missing)}")
            textw = max(text_w(value, 1.778), text_w(ref, 1.778))
            slots.append((ref, kind, value, conn, k, lw, max(k.w + PINLEN + rw, textw)))
        big = [s for s in slots if s[4].h > 2 * PITCH]
        small = [s for s in slots if s[4].h <= 2 * PITCH]
        tall = max([s[4].h for s in big] or [0])
        for ref, kind, value, conn, k, lw, body in big:
            px = x + lw + PINLEN
            items.append((ref, kind, value, conn, px, 0.0))
            x = px + body + 4 * G
        limit = max(tall, 6 * PITCH)
        step = lambda k: G * math.ceil((k.h + 9.0) / G)
        col, colh, colw_l, colw_b = [], 0.0, 0.0, 0.0
        top = tall

        def flush():
            nonlocal x, col, colh, colw_l, colw_b, top
            yy = 0.0
            for ref, kind, value, conn, k, lw, body in col:
                items.append((ref, kind, value, conn, x + colw_l + PINLEN, yy))
                yy += step(k)
            top = max(top, yy - 3.0)
            x += colw_l + PINLEN + colw_b + 4 * G
            col, colh, colw_l, colw_b = [], 0.0, 0.0, 0.0

        for s in small:
            if col and colh + step(s[4]) > limit + 6:
                flush()
            col.append(s)
            colh += step(s[4])
            colw_l, colw_b = max(colw_l, s[5]), max(colw_b, s[6])
        if col:
            flush()
        groups[gname] = {"items": items, "w": x - 4 * G, "h": top + 6.0}
    # pack groups in rows
    y = 0.0
    placed = {}
    for row in NL.ROWS:
        rowh = max(groups[g]["h"] for g in row)
        y -= rowh + GROUP_GAP + 4 * G
        x = 0.0
        for g in row:
            placed[g] = (r4(G * round(x / G)), r4(G * round(y / G)))
            x += groups[g]["w"] + GROUP_GAP + 2 * G
    for gname, grp in groups.items():
        gx, gy = placed[gname]
        for ref, kind, value, conn, px, py in grp["items"]:
            k = kinds[kind]
            ox, oy = r4(G * round((gx + px) / G)), r4(G * round((gy + py) / G))
            parts.append((ref, kind, value, ox, oy, gname, k))
            for pn, (x, y_, side) in k.pos.items():
                net = conn[pn]
                if not net:
                    continue
                p = (r4(ox + x), r4(oy + y_))
                L = stub_len(net)
                q = (r4(p[0] - L), p[1]) if side == "L" else (r4(p[0] + L), p[1])
                wires.append((net, ref, pn, p, q, gname))
                lx = min(p[0], q[0])
                labels.append((net, ref, pn, r4(lx + 1.27), r4(p[1] + LABEL_DY), gname))
    return kinds, parts, wires, labels


LAYERS = [(1, "Top", 4), (16, "Bottom", 1), (17, "Pads", 2), (18, "Vias", 2), (19, "Unrouted", 6), (20, "Dimension", 24),
          (21, "tPlace", 7), (22, "bPlace", 7), (23, "tOrigins", 15), (25, "tNames", 7), (27, "tValues", 7),
          (29, "tStop", 7), (31, "tCream", 7), (35, "tGlue", 7), (39, "tKeepout", 4), (41, "tRestrict", 4),
          (44, "Drills", 7), (45, "Holes", 7), (46, "Milling", 3), (47, "Measures", 7), (48, "Document", 7),
          (49, "Reference", 7), (51, "tDocu", 7), (88, "SimResults", 9), (89, "SimProbes", 9), (90, "Modules", 5),
          (91, "Nets", 2), (92, "Busses", 1), (93, "Pins", 2), (94, "Symbols", 4), (95, "Names", 7), (96, "Values", 7),
          (97, "Info", 7), (98, "Guide", 6), (99, "SpiceOrder", 5)]


def write(out):
    kinds, parts, wires, labels = build()
    eagle = ET.Element("eagle", version="9.7.0")
    drawing = ET.SubElement(eagle, "drawing")
    ET.SubElement(ET.SubElement(drawing, "settings"), "setting", alwaysvectorfont="no")
    ET.SubElement(drawing, "grid", distance="0.1", unitdist="inch", unit="inch", style="lines", multiple="1",
                  display="no", altdistance="0.01", altunitdist="inch", altunit="inch")
    layers = ET.SubElement(drawing, "layers")
    for num, name, col in LAYERS:
        ET.SubElement(layers, "layer", number=str(num), name=name, color=str(col), fill="1",
                      visible="no" if num == 93 else "yes", active="yes")
    sch = ET.SubElement(drawing, "schematic", xreflabel="%F%N/%S.%C%R", xrefpart="/%S.%C%R")
    lib = ET.SubElement(ET.SubElement(sch, "libraries"), "library", name=LIB)
    ET.SubElement(lib, "packages")
    syms = ET.SubElement(lib, "symbols")
    dss = ET.SubElement(lib, "devicesets")
    used = sorted({p[1] for p in parts})
    for kn in used:
        syms.append(kinds[kn].symbol())
        ds = ET.SubElement(dss, "deviceset", name=kn, prefix=NL.PREFIX.get(kn, "U"), uservalue="yes")
        ET.SubElement(ET.SubElement(ds, "gates"), "gate", name="G$1", symbol=kn, x="0", y="0")
        dev = ET.SubElement(ET.SubElement(ds, "devices"), "device", name="")
        ET.SubElement(ET.SubElement(dev, "technologies"), "technology", name="")
    ET.SubElement(sch, "attributes")
    ET.SubElement(sch, "variantdefs")
    ET.SubElement(ET.SubElement(sch, "classes"), "class", number="0", name="default", width="0", drill="0")
    grp_el = ET.SubElement(sch, "groups")
    for g in NL.GROUPS:
        ET.SubElement(grp_el, "schematic_group", name=g, titleSize="2.54", titleFont="vector", showAnnotations="yes", layer="97")
    pe = ET.SubElement(sch, "parts")
    for ref, kind, value, *_ in parts:
        ET.SubElement(pe, "part", name=ref, library=LIB, deviceset=kind, device="", value=value)
    sheet = ET.SubElement(ET.SubElement(sch, "sheets"), "sheet")
    plain = ET.SubElement(sheet, "plain")
    top = max(p[4] + p[6].h for p in parts)
    ET.SubElement(plain, "text", x="0", y=fmt(G * math.ceil((top + 16) / G)), size="3.81", layer="97").text = NL.TITLE
    inst = ET.SubElement(sheet, "instances")
    for ref, kind, value, ox, oy, gname, k in parts:
        ie = ET.SubElement(inst, "instance", part=ref, gate="G$1", x=fmt(ox), y=fmt(oy), smashed="yes", grouprefs=gname)
        ET.SubElement(ie, "attribute", name="NAME", x=fmt(ox), y=fmt(oy + k.h + 3.2), size="1.778", layer="95")
        ET.SubElement(ie, "attribute", name="VALUE", x=fmt(ox), y=fmt(oy + k.h + 0.8), size="1.778", layer="96")
    ET.SubElement(sheet, "busses")
    nets = ET.SubElement(sheet, "nets")
    by_net = {}
    for w in wires:
        by_net.setdefault(w[0], []).append(w)
    lab = {(l[1], l[2]): l for l in labels}
    for net in sorted(by_net):
        n = ET.SubElement(nets, "net", name=net, **{"class": "0"})
        for _, ref, pn, p, q, gname in by_net[net]:
            se = ET.SubElement(n, "segment")
            ET.SubElement(se, "pinref", part=ref, gate="G$1", pin=pn)
            ET.SubElement(se, "wire", x1=fmt(p[0]), y1=fmt(p[1]), x2=fmt(q[0]), y2=fmt(q[1]), width="0.1524",
                          layer="91", grouprefs=gname)
            l = lab[(ref, pn)]
            ET.SubElement(se, "label", x=fmt(l[3]), y=fmt(l[4]), size=fmt(LABEL), layer="95", grouprefs=gname)
    tree = ET.ElementTree(eagle)
    ET.indent(tree)
    with open(out, "wb") as f:
        f.write(b'<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE eagle SYSTEM "eagle.dtd">\n')
        tree.write(f, encoding="utf-8")
    return len(parts), len(by_net)


if __name__ == "__main__":
    n, m = write(sys.argv[1])
    print(f"wrote {sys.argv[1]}: {n} parts, {m} nets")
