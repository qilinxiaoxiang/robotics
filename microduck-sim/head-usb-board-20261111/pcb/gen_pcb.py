#!/usr/bin/env python3
"""Build the head USB board as a KiCad PCB from sch/netlist.py (the same netlist the schematic is generated from).

Runs with KiCad's own Python on the Mac mini (see run.sh). Stages:
  place   footprints from KiCad's standard library, placed from PLACE below, nets from netlist.py, outline, planes -> board.kicad_pcb + board.dsn
  finish  import the autorouter's board.ses, fill zones -> board.kicad_pcb
Board frame (mm): x right, y down, seen from the robot's rear (the face the Dupont plugs enter). The top band
y < BAND is the only place a straight-back plug clears the head parts (../space-check.json), so all 2.54 mm
headers sit there; chips sit below it.
"""
import sys
from pathlib import Path

import pcbnew

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "sch"))
import netlist as NL  # noqa: E402

FPLIB = Path(pcbnew.__file__).resolve()
for parent in FPLIB.parents:
    if (parent / "SharedSupport" / "footprints").is_dir():
        FPLIB = parent / "SharedSupport" / "footprints"
        break

W, H, BAND = 30.0, 30.0, 13.5
MM = pcbnew.FromMM

# kind -> (library, footprint)
FOOT = {
    "RP2040": ("Package_DFN_QFN", "QFN-56-1EP_7x7mm_P0.4mm_EP3.2x3.2mm"),
    "CH334F": ("Package_DFN_QFN", "QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm"),
    "MAX98357A": ("Package_DFN_QFN", "TQFN-16-1EP_3x3mm_P0.5mm_EP1.23x1.23mm"),
    "W25Q16JV": ("Package_SON", "Winbond_USON-8-1EP_3x2mm_P0.5mm_EP0.2x1.6mm"),
    "AP2112K-3.3": ("Package_TO_SOT_SMD", "SOT-23-5"),
    "XTAL": ("Crystal", "Crystal_SMD_3225-4Pin_3.2x2.5mm"),
    "LED": ("LED_SMD", "LED_0603_1608Metric"),
    "FB": ("Inductor_SMD", "L_0603_1608Metric"),
    "TP": ("TestPoint", "TestPoint_Pad_D1.0mm"),
    "R": ("Resistor_SMD", "R_0402_1005Metric"),
    "C": ("Capacitor_SMD", "C_0402_1005Metric"),
}
BIG_C = {"10uF": "C_0603_1608Metric", "22uF": "C_0805_2012Metric"}
CONN = {  # ref -> (library, footprint)
    "J_EAR_R": ("Connector_PinSocket_2.54mm", "PinSocket_1x05_P2.54mm_Vertical"),
    "J_EAR_L": ("Connector_PinSocket_2.54mm", "PinSocket_1x05_P2.54mm_Vertical"),
    "J_BACK": ("Connector_PinSocket_2.54mm", "PinSocket_1x05_P2.54mm_Vertical"),
    "J_BACK_SD": ("Connector_PinHeader_2.54mm", "PinHeader_1x01_P2.54mm_Vertical"),
    "J_TOUCH": ("Connector_PinHeader_2.54mm", "PinHeader_1x03_P2.54mm_Vertical"),
    "J_TOUCH_3V3": ("Connector_PinSocket_2.54mm", "PinSocket_1x01_P2.54mm_Vertical"),
    "J_SPK": ("TerminalBlock", "TerminalBlock_Xinya_XY308-2.54-2P_1x02_P2.54mm_Horizontal"),
    "J_UP": ("Connector_Molex", "Molex_PicoBlade_53047-0510_1x05_P1.25mm_Vertical"),
    "J_CAM": ("Connector_Molex", "Molex_PicoBlade_53047-0510_1x05_P1.25mm_Vertical"),
}
# pads that are not in the netlist: (kind or ref, pad) -> net
EXTRA = {("XTAL", "2"): "GND", ("XTAL", "4"): "GND"}   # the flash exposed pad 9 floats, as on the Pico (Winbond: "can be left floating")
# netlist pin -> footprint pad, where they differ
PADMAP = {"XTAL": {"1": "1", "2": "3"}, "LED": {"1": "2", "2": "1"}, "CH334F": {"0": "25"}}
POWER_NETS = {"VBUS": 0.4, "+3V3": 0.3, "+1V1": 0.25, "HUB_3V3": 0.25, "AMP_P": 0.3, "AMP_N": 0.3, "SPK_P": 0.4, "SPK_N": 0.4}

sys.path.insert(0, str(HERE))
from placement import PLACE  # noqa: E402  ref -> (x, y, rotation degrees, side "F"/"B")


def pad_of(kind, pin):
    num = pin.split("_", 1)[0] if pin[0].isdigit() else pin
    return PADMAP.get(kind, {}).get(num, num)


def footprint_for(ref, kind, value):
    if ref in CONN:
        return CONN[ref]
    lib, name = FOOT[kind]
    if kind == "C":
        for k, n in BIG_C.items():
            if value.startswith(k):
                name = n
    return lib, name


def place():
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    ds = board.GetDesignSettings()
    nc = ds.m_NetSettings.GetDefaultNetclass()
    nc.SetClearance(MM(0.13)); nc.SetTrackWidth(MM(0.15)); nc.SetViaDiameter(MM(0.5)); nc.SetViaDrill(MM(0.3))
    ds.m_TrackMinWidth = MM(0.1); ds.m_ViasMinSize = MM(0.45); ds.m_MinThroughDrill = MM(0.2); ds.m_MinClearance = MM(0.1)
    ds.m_CopperEdgeClearance = MM(0.3)
    for width in sorted(set(POWER_NETS.values())):          # one net class per power track width
        name = f"W{int(round(width * 100)):03d}"
        pc = pcbnew.NETCLASS(name)
        pc.SetClearance(MM(0.13)); pc.SetTrackWidth(MM(width)); pc.SetViaDiameter(MM(0.5)); pc.SetViaDrill(MM(0.3))
        ds.m_NetSettings.SetNetclass(name, pc)
        for n, w in POWER_NETS.items():
            if w == width:
                ds.m_NetSettings.SetNetclassPatternAssignment(n, name)
    nets = {}

    def net(name):
        if name not in nets:
            nets[name] = pcbnew.NETINFO_ITEM(board, name)
            board.Add(nets[name])
        return nets[name]

    missing = []
    for members in NL.GROUPS.values():
        for ref, kind, value, conn in members:
            lib, name = footprint_for(ref, kind, value)
            fp = pcbnew.FootprintLoad(str(FPLIB / f"{lib}.pretty"), name)
            if fp is None:
                raise SystemExit(f"{ref}: footprint {lib}:{name} not found")
            fp.SetReference(ref); fp.SetValue(value)
            want = {}
            for pin, n in conn.items():
                want[pad_of(kind, pin)] = n
            for (k, padnum), n in EXTRA.items():
                if k in (kind, ref):
                    want[padnum] = n
            seen = set()
            for pad in fp.Pads():
                num = pad.GetNumber()
                seen.add(num)
                if want.get(num):
                    pad.SetNet(net(want[num]))
            lost = [p for p, n in want.items() if n and p not in seen]
            if lost:
                raise SystemExit(f"{ref} ({lib}:{name}): netlist pins with no pad: {lost}")
            if ref not in PLACE:
                missing.append(ref)
                x, y, rot, side = -10.0 - 3 * (len(missing) % 8), 3.0 * (len(missing) // 8), 0, "F"
            else:
                x, y, rot, side = PLACE[ref]
            board.Add(fp)
            fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
            if side == "B":
                fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
            fp.SetOrientationDegrees(rot)
    if missing:
        print("NOT PLACED (parked left of the board):", " ".join(missing))
    # outline
    for (x1, y1, x2, y2) in ((0, 0, W, 0), (W, 0, W, H), (W, H, 0, H), (0, H, 0, 0)):
        s = pcbnew.PCB_SHAPE(board)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I(MM(x1), MM(y1))); s.SetEnd(pcbnew.VECTOR2I(MM(x2), MM(y2)))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1))
        board.Add(s)
    # inner planes
    for layer, name in ((pcbnew.In1_Cu, "GND"), (pcbnew.In2_Cu, "+3V3")):
        z = pcbnew.ZONE(board)
        z.SetLayer(layer); z.SetNet(net(name))
        o = z.Outline(); o.NewOutline()
        for x, y in ((0.5, 0.5), (W - 0.5, 0.5), (W - 0.5, H - 0.5), (0.5, H - 0.5)):
            o.Append(MM(x), MM(y))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        # 0.2 mm keeps a copper web between neighbouring 2.54 mm header holes; KiCad's default 0.5 mm
        # merged their openings into a slot that cut the plane into islands
        z.SetLocalClearance(MM(0.2)); z.SetMinThickness(MM(0.15))
        board.Add(z)
    n_via, failed, owner = plane_fanout(board, nets)
    print(f"plane vias {n_via}; pads with no room for a plane via: {failed or 'none'}")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    out = HERE / "build"
    out.mkdir(exist_ok=True)
    pcbnew.SaveBoard(str(out / "board.kicad_pcb"), board)
    write_project(out / "board.kicad_pro")
    # The router cannot drop vias to a plane itself, so in its copy every plane pad sits on a private,
    # already-complete net (pad + stub + via) and it routes signals only. The planes stay, each with one
    # anchor pad (ANCHOR), so the inner layers count as planes and get no signal tracks. Tried and rejected:
    # no planes (router then routes signals on the inner layers) and wire keep-outs (it then places no vias).
    router_board = pcbnew.LoadBoard(str(out / "board.kicad_pcb"))
    # The router keeps only its track clearance (0.13 mm) from the outline; the board rule is 0.3 mm. Its copy
    # of the outline is therefore drawn 0.2 mm inside the real one.
    inset = 0.2
    for d in list(router_board.GetDrawings()):
        if d.GetLayer() == pcbnew.Edge_Cuts:
            clamp = lambda p: pcbnew.VECTOR2I(min(max(p.x, MM(inset)), MM(W - inset)), min(max(p.y, MM(inset)), MM(H - inset)))
            d.SetStart(clamp(d.GetStart())); d.SetEnd(clamp(d.GetEnd()))
    solo = {}

    def solo_net(key):                    # one private net per plane pad: already complete, so nothing to route
        if key not in solo:
            solo[key] = pcbnew.NETINFO_ITEM(router_board, f"PL_{key}")
            router_board.Add(solo[key])
        return solo[key]

    for fp in router_board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() in PLANE_NETS and (fp.GetReference(), pad.GetNumber()) not in ANCHOR:
                pad.SetNet(solo_net(f"{fp.GetReference()}.{pad.GetNumber()}"))
    for t in router_board.GetTracks():
        if t.GetNetname() in PLANE_NETS:
            e = t.GetPosition() if t.GetClass() == "PCB_VIA" else t.GetEnd()
            t.SetNet(solo_net(owner[(e.x, e.y)]))
    ok = pcbnew.ExportSpecctraDSN(router_board, str(out / "board.dsn"))
    # KiCad exports every copper layer as "signal"; the two inner layers are planes, so declare them "power"
    # (Specctra's word for a layer the router must not put signal tracks on). Without this the router cut the
    # planes into islands with signal tracks and left ground and 3V3 pads unconnected.
    import re
    dsn = (out / "board.dsn").read_text()
    dsn, n = re.subn(r"(\(layer In[12]\.Cu\s+\(type )signal", r"\1power", dsn)
    if n != 2:
        raise SystemExit(f"expected to retype 2 inner layers in the DSN, did {n}")
    (out / "board.dsn").write_text(dsn)
    print(f"placed {len(list(board.GetFootprints()))} footprints, {len(nets)} nets, dsn {'ok' if ok else 'FAILED'}")


PLANE_NETS = ("GND", "+3V3")
ANCHOR = {("J_EAR_R", "1"), ("J_EAR_R", "2")}     # through-hole 3V3 and GND pins that keep the plane nets alive for the router
VIA_D, VIA_DRILL, CLR = 0.5, 0.3, 0.13


def plane_fanout(board, nets):
    """Give every surface pad on a plane net its own via (in the pad when the pad is large, else on a short stub).

    Greedy and geometric: the nearest free spot around each pad that keeps clearance to other nets' pads, to
    other vias and stubs, to the board edge and to the straight escape lane in front of fine-pitch pins.
    Returns (via count, [pads that found no spot]).
    """
    import math
    to_mm = pcbnew.ToMM
    pads = []
    for fp in board.GetFootprints():
        c = fp.GetPosition()
        for pad in fp.Pads():
            bb = pad.GetBoundingBox()
            p = pad.GetPosition()
            pads.append({"ref": fp.GetReference(), "num": pad.GetNumber(), "net": pad.GetNetname(),
                         "x": to_mm(p.x), "y": to_mm(p.y), "w": to_mm(bb.GetWidth()), "h": to_mm(bb.GetHeight()),
                         "cx": to_mm(c.x), "cy": to_mm(c.y), "smd": pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD})

    def rect_dist(q, x, y):
        dx = max(abs(x - q["x"]) - q["w"] / 2, 0.0)
        dy = max(abs(y - q["y"]) - q["h"] / 2, 0.0)
        return math.hypot(dx, dy)

    def seg_dist(a, b, x, y):
        ax, ay, bx, by = *a, *b
        L2 = (bx - ax) ** 2 + (by - ay) ** 2
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - ax) * (bx - ax) + (y - ay) * (by - ay)) / L2))
        return math.hypot(x - ax - t * (bx - ax), y - ay - t * (by - ay))

    lanes = []            # (start, end, net): escape lane in front of every fine-pitch pin
    for q in pads:
        if q["smd"] and min(q["w"], q["h"]) < 0.35 and q["net"]:
            ox, oy = q["x"] - q["cx"], q["y"] - q["cy"]
            if abs(ox) > abs(oy):
                d = (math.copysign(1, ox), 0.0); half = q["w"] / 2
            else:
                d = (0.0, math.copysign(1, oy)); half = q["h"] / 2
            s = (q["x"] + d[0] * half, q["y"] + d[1] * half)
            lanes.append((s, (s[0] + d[0] * 1.2, s[1] + d[1] * 1.2), q["net"], q["ref"], q["num"]))
    vias, stubs, failed = [], [], []      # vias: (x, y, net); stubs: (a, b, width, net)
    owner = {}                            # copper position (nm) -> "ref.pad" it belongs to

    def via_ok(x, y, net, me):
        if not (0.3 + VIA_D / 2 <= x <= W - 0.3 - VIA_D / 2 and 0.3 + VIA_D / 2 <= y <= H - 0.3 - VIA_D / 2):
            return False
        for q in pads:
            if q is me:
                continue
            gap = rect_dist(q, x, y) - VIA_D / 2
            if gap < (CLR if q["net"] != net else (0.0 if q["smd"] else 0.25)) + 0.02:
                return False
        for vx, vy, vn in vias:
            if math.hypot(x - vx, y - vy) < VIA_D + (CLR if vn != net else 0.1) + 0.02:
                return False
        for a, b, w, sn in stubs:
            if sn != net and seg_dist(a, b, x, y) < VIA_D / 2 + w / 2 + CLR + 0.02:
                return False
        for a, b, ln, ref, num in lanes:
            if (ref, num) != (me["ref"], me["num"]) and ln != net and seg_dist(a, b, x, y) < VIA_D / 2 + CLR + 0.075 + 0.02:
                return False
        return True

    def stub_ok(a, b, w, net, me):
        n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.05))
        for i in range(n + 1):
            x, y = a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n
            for q in pads:
                if q is not me and q["net"] != net and rect_dist(q, x, y) < w / 2 + CLR + 0.02:
                    return False
            for vx, vy, vn in vias:
                if vn != net and math.hypot(x - vx, y - vy) < VIA_D / 2 + w / 2 + CLR + 0.02:
                    return False
            for sa, sb, sw, sn in stubs:
                if sn != net and seg_dist(sa, sb, x, y) < w / 2 + sw / 2 + CLR + 0.02:
                    return False
        return True

    def add_via(x, y, net, me_ref, me_num):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        v.SetWidth(pcbnew.F_Cu, MM(VIA_D)); v.SetDrill(MM(VIA_DRILL))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(nets[net])
        board.Add(v)
        vias.append((x, y, net))
        owner[(MM(x), MM(y))] = f"{me_ref}.{me_num}"

    targets = [q for q in pads if q["smd"] and q["net"] in PLANE_NETS]
    targets.sort(key=lambda q: min(q["w"], q["h"]))          # the tightest pads choose first
    for q in targets:
        small = min(q["w"], q["h"])
        if small >= 2.0:                                     # big exposed pad: four vias in the pad
            for sx in (-1, 1):
                for sy in (-1, 1):
                    add_via(q["x"] + sx * q["w"] / 4, q["y"] + sy * q["h"] / 4, q["net"], q["ref"], q["num"])
            continue
        if small >= 0.9:                                     # exposed pad: one via in its centre
            add_via(q["x"], q["y"], q["net"], q["ref"], q["num"])
            continue
        width = min(0.25, small)
        ox, oy = q["x"] - q["cx"], q["y"] - q["cy"]
        on = math.hypot(ox, oy) or 1.0
        cands = []
        for k in range(24):
            ang = 2 * math.pi * k / 24
            dx, dy = math.cos(ang), math.sin(ang)
            for dist in [0.55 + 0.1 * i for i in range(24)]:
                cands.append((dist - 0.3 * (dx * ox + dy * oy) / on, q["x"] + dx * dist, q["y"] + dy * dist))
        for _, x, y in sorted(cands):
            if via_ok(x, y, q["net"], q) and stub_ok((q["x"], q["y"]), (x, y), width, q["net"], q):
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(pcbnew.VECTOR2I(MM(q["x"]), MM(q["y"]))); t.SetEnd(pcbnew.VECTOR2I(MM(x), MM(y)))
                t.SetWidth(MM(width)); t.SetLayer(pcbnew.F_Cu); t.SetNet(nets[q["net"]])
                board.Add(t)
                stubs.append(((q["x"], q["y"]), (x, y), width, q["net"]))
                add_via(x, y, q["net"], q["ref"], q["num"])
                break
        else:
            failed.append(f"{q['ref']}.{q['num']}")
    return len(vias), failed, owner


def write_project(path):
    """KiCad keeps board constraints and net classes in the project file, not the board; kicad-cli drc reads them
    from there. Minimums are JLCPCB's 4-layer limits with margin (track/space 0.09 mm, via 0.45/0.2 mm)."""
    import json
    cls = lambda name, width: {"name": name, "clearance": 0.13, "track_width": width, "via_diameter": 0.5,
                               "via_drill": 0.3, "microvia_diameter": 0.3, "microvia_drill": 0.1,
                               "diff_pair_width": 0.15, "diff_pair_gap": 0.15, "diff_pair_via_gap": 0.25,
                               "bus_width": 12, "wire_width": 6, "line_style": 0,
                               "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)"}
    widths = sorted(set(POWER_NETS.values()))
    name = lambda w: f"W{int(round(w * 100)):03d}"
    pro = {
        "board": {"design_settings": {"rules": {
            "min_clearance": 0.1, "min_track_width": 0.1, "min_via_diameter": 0.45, "min_through_hole_diameter": 0.2,
            "min_via_annular_width": 0.1, "min_copper_edge_clearance": 0.3, "min_hole_clearance": 0.2,
            "min_hole_to_hole": 0.25, "min_connection": 0.0, "solder_mask_to_copper_clearance": 0.0}}},
        "meta": {"filename": path.name, "version": 3},
        "net_settings": {"classes": [cls("Default", 0.15)] + [cls(name(w), w) for w in widths],
                         "meta": {"version": 4},
                         "netclass_patterns": [{"netclass": name(w), "pattern": n} for n, w in POWER_NETS.items()]},
    }
    path.write_text(json.dumps(pro, indent=2) + "\n")


def finish():
    out = HERE / "build"
    board = pcbnew.LoadBoard(str(out / "board.kicad_pcb"))
    if not pcbnew.ImportSpecctraSES(board, str(out / "board.ses")):
        raise SystemExit("SES import failed")
    # The router necks a few very short segments below the 0.1 mm minimum where it squeezes past a pad. They
    # are widened back to 0.1 mm here; the rule check that follows still judges their clearance.
    widened = 0
    for t in board.GetTracks():
        if t.GetClass() != "PCB_VIA" and t.GetWidth() < MM(0.1):
            t.SetWidth(MM(0.1)); widened += 1
    print(f"segments widened to 0.1 mm: {widened}")
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(str(out / "board.kicad_pcb"), board)
    print(f"tracks and vias: {len(list(board.GetTracks()))}")


if __name__ == "__main__":
    {"place": place, "finish": finish}[sys.argv[1]]()
