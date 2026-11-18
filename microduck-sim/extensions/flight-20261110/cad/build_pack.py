"""Build the flight-pack printed parts (DESIGN-CONTRACT.json). Guide frame, mm (x forward, y left, z up).
Writes build/<part>-world.stl (robot pose), build/<part>-print.stl (print pose, on the bed), build/dummy_*-world.stl
(bought parts with plug and lead keep-outs), build/build.json, build/screws.json and FITS.json (cad-practice/fit_check.py).
    /tmp/microduck-cad-venv/bin/python cad/build_pack.py          (about 10 s)
"""
import json
import math
from pathlib import Path
import numpy as np
import manifold3d as m3

import flight_params as Pm
from flight_params import F, FAN, NAC, WING, TRAY, BATT, FC, MTF01, S, C
import cadlib as L

H = Path(__file__).resolve().parent
OUT = H / "build"; OUT.mkdir(exist_ok=True)
PR = Pm.PRINTER
CLR_V = F.clear("M2", "vertical", PR)          # 2.5
CLR_H = F.clear("M2", "horizontal", PR)        # 2.7
PIL_V = F.pilot("M2", "vertical", "any", PR)   # 1.95
PIL_H = F.pilot("M2", "horizontal", "any", PR) # 2.15
M3_PIL_V = F.pilot("M3", "vertical", "any", PR)  # 2.9
LUG_PIL_H = F.pilot(NAC["lug_screw"], "horizontal", "any", PR)   # M3: 3.1 (nacelle lug, axis in the layer plane)
LUG_CLR_V = F.clear(NAC["lug_screw"], "vertical", PR)            # M3: 3.5 (arm web, axis vertical in the wing pose)
X_AX, Y_AX, Z_AX = (1, 0, 0), (0, 1, 0), (0, 0, 1)
WEB_T = WING["x_front"] - WING["x_back"]       # 5.2

FITS, SCREWS = [], []


def fit_pilot(fid, part, axis, d, teardrop, clamped, depth, eng, screw="M2"):
    FITS.append(dict(id=fid, type="pilot", part=part, screw=screw, kind="any", d=d, axis=list(axis), teardrop=teardrop,
                     at_bed=False, chamfer=0.0, engagement=round(eng, 2), depth=depth, clamped=round(clamped, 2)))


def fit_clear(fid, part, axis, d, teardrop=None, screw="M2"):
    FITS.append(dict(id=fid, type="clear", part=part, screw=screw, d=d, axis=list(axis), teardrop=teardrop))


def screw(sid, size, joins, seat, axis, through, step):
    SCREWS.append(dict(id=sid, spec=size, joins=joins, seat=[round(float(c), 2) for c in seat], axis=list(axis),
                       through_mm=through, step=step))


# ------------------------------------------------------------------ bracket positions (shared by plate and brackets)
FCB_T = 3.0
FCB_X = (WING["arm_x_rear"] - FCB_T, WING["arm_x_rear"])            # FC plate x -67..-64, behind the right arm
# (y, z): flange-edge bosses, clear of M3 bosses; the upper pair sits 0.5 further from the M3 bosses at z 55.25 so the
# driver corridor is 4.25 mm radius (access_check: 3.77 at y -48/-64, 2026-11-10)
FCB_SCREWS = [(-48.0, 21.75), (-64.0, 21.75), (-48.5, 55.75), (-63.5, 55.75)]
FC_CENTRE = (-56.0, 40.0)                                            # 30.5 pattern centre (y, z)
FC_BOSS = 4.0                                                        # M3 standoff bosses behind the plate
# 2.5 mm above the lower plate screws' holes; 17.5 high (11 wide) so the right pigtail, soldered to the ESC on the bench,
# passes with its XT60 upright (Pm.XT60_ENV 15.8 x 8.2)
FCB_WINDOW_Z = (25.5, 43.0)
# ESC input capacitor (12.5 x 20 mm, keep-out d 13 x 25 with the leg roots) lies along x on the right top flange with its
# legs toward the ESC battery tabs (x -80, y -60.6 / -51.5, z 60.6; wiring/wiring.json esc_tabs_world), so its own legs
# reach the tabs (about 8.5 mm end face to tab). Body x -50.6..-75.6, y -62.5..-49.5 (outboard of the head reach near
# y -47), resting on the flange (x -64..-50.2) and the FC plate top edge (x -67..-64). One zip tie through two flange
# slots at x -55.5..-52.5 (the upper FC bosses fill x -64..-56); the soldered legs hold the far end.
CAP_AXIS = dict(x0=-50.6, y=-56.0)
CAP_SLOTS = [(-66.0, -62.5), (-49.5, -46.0)]                         # (y0, y1) of the two tie slots
CAP_SLOT_X = (-55.5, -52.5)
# Stack spacing (x, rear = -x). Sources: MicoAir 55A ESC dimension drawing (wiring/sources/micoair-55a-esc-dimensions.png:
# 6 mm overall, side-entry SH1.0-8P socket on the board edge) and the MicoAir743v2 manual ("36 x 36 x 8 mm"). The maker
# publishes no spacer length. ESC component side rearward (wiring.json notes_for_cad): ESC PCB 1.6 + parts 4.4; an 8 mm
# ESC-to-FC spacer leaves 8 - 4.4 = 3.6 mm for the FC's underside parts (assumed <= 2 mm of its 8 mm) and the
# side-entry plug clears the board gap edge-on.
STACK = dict(esc_pcb=1.6, esc_h=6.0, spacer=8.0, fc_pcb=1.6, fc_h=8.0, fc_under=2.0, grommet=1.0)
# A7Z-to-FC lead centreline (guide frame). Header pin pair k sits at y = 24.13 - 2.54 (k - 1) (pin 1 at robot left):
# pins 14/16/18 = pairs 7/8/9 at y 8.89 / 6.35 / 3.81. Ends on the UART1 plug on the FC top edge (z 58 + 6 mm plug).
# Over the right saddle wall in front of the lid (lid x <= -19.6), then rearward outboard of the lid edge (|y| 34.4) at
# y -36.3 along the wall's outer top corner, behind the transition column, over the ESC top (above the left battery tail)
# and down into the plug.
A7Z_LINK = [(-15.2, 6.35, 67.0), (-15.2, -33.4, 68.6), (-15.6, -36.4, 68.4), (-17.5, -36.4, 66.5), (-46.8, -36.3, 66.5), (-48.8, -36.3, 64.0),
            (-76.0, -36.3, 64.0), (-82.0, -38.0, 68.5), (-88.6, -50.0, 68.0), (-88.6, -56.0, 65.0)]


def tube_path(r, pts):
    """Round-cornered tube along a polyline (keep-out of a flexible lead)."""
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        d = np.subtract(b, a)
        out.append(L.cyl(r, a, tuple(d), float(np.linalg.norm(d))))
    out += [m3.Manifold.sphere(r, 24).translate(p) for p in pts]
    return out
# The capacitor is held by a strip of 1 mm double-sided foam tape on the right top flange plus its soldered legs. The two
# tie slots (CAP_SLOTS) cannot take a tie on D1: under the flange the gusset at y -54.5..-52.5 is solid down to its
# window (z 22..34), and a tie taken round through that window runs taut straight across the outer bay, behind the battery
# lead window the pack's XT60 passes at every battery change (2026-11-18, found when the guide drew the tie).
CAP_TAPE = dict(t=1.0, x=(-63.5, -51.5), w=6.0)
MTF_C = (-86.0, -59.0)                                             # MTF-01 centre (x, y): behind the leg sweep at x > -70
SHELF_Z = (13.5, 17.5)


# ================================================================== wing plate
def wing_plate():
    W = WING
    xf, xb, xr, xcb = W["x_front"], W["x_back"], W["x_recess"], W["x_centre_back"]
    zt, zb = W["arm_z"][1], W["arm_z"][0]
    centre = L.box((xcb, -W["centre_half_w"], W["centre_bot"]), (xf, W["centre_half_w"], W["centre_top"]))
    parts = [centre]
    for s in (1, -1):
        def B(x0, x1, y0, y1, z0, z1):
            return L.box((x0, min(s * y0, s * y1), z0), (x1, max(s * y0, s * y1), z1))
        xd, yd = W["x_band_back"], W["root_y"]
        p = [B(xcb, xf, W["centre_half_w"] - 0.01, W["centre_ext_w"], W["band_z"][0], W["centre_top"]),
             B(xd, xcb + 0.01, W["centre_half_w"] + 0.3, W["centre_ext_w"], W["band_z"][0], W["centre_top"]),
             # root: band, column and transition solid 8.5 deep (x_band_back) out to root_y; the arm web stays 5.2 so the
             # tray M2 x 10 still bites 4.8 (strength/SPAR-OPTION.md, landing case); lug screws are M3 x 12 (bite 6.8)
             B(xd, xb + 0.01, W["band_y"][0] - 0.01, W["band_y"][1] + 0.01, W["band_z"][0], W["band_z"][1]),
             B(xd, xb + 0.01, W["col_y"][0], yd, W["col_z"][0], W["col_z"][1]),
             B(xd, xb + 0.01, W["trans_y"][0], yd, W["col_z"][1] - 0.01, W["trans_z"][1]),
             B(xb, xf, W["band_y"][0] - 0.01, W["band_y"][1], W["band_z"][0], W["band_lip_z"]),
             B(xb, xr, W["band_y"][0] - 0.01, W["band_y"][1], W["band_lip_z"] - 0.01, W["band_z"][1]),
             B(xb, xf, W["col_y"][0] - 0.01, W["col_y"][1], W["col_z"][0], W["saddle_zone"]["z"]),
             B(xb, xr, W["col_y"][0] - 0.01, W["col_y"][1], W["saddle_zone"]["z"] - 0.01, W["col_z"][1]),
             B(xb, -46.5, W["trans_y"][0], W["trans_y"][1] + 0.01, W["col_z"][1] - 0.01, W["trans_z"][1]),
             B(xb, xf, W["arm_y"][0], W["arm_y"][1], zb, zt),
             B(W["arm_x_rear"], xb + 0.01, W["arm_y"][0], W["arm_y"][1], zt - W["flange_t"], zt),
             B(W["arm_x_rear"], xb + 0.01, W["arm_y"][0], W["arm_y"][1], zb, zb + W["flange_t"]),
             B(W["arm_x_rear"], xb + 0.01, 33.0, W["arm_y"][0] + 0.01, W["col_z"][0], W["col_z"][0] + W["flange_t"]),
             B(xb, xf, W["col_y"][1] - 0.01, W["arm_y"][0] + 2.1, W["col_z"][0], zb + 0.01)]
        for (g0, g1) in W["gussets"]:
            z0 = W["col_z"][0] if g0 < 39 else zb
            p.append(B(W["arm_x_rear"], xb + 0.01, g0, g1, z0, zt))
        for rf in W["root_fix"]:
            p.append(B(rf["x"][0], rf["x"][1], rf["y"][0], rf["y"][1], rf["z"][0], rf["z"][1]))
        # arm root wedge: (|y|, z) profile extruded along x over the web depth (local a = |y|, b = z, c = x - xb)
        wedge = m3.CrossSection([list(W["arm_root_wedge"])]).extrude(xf - xb)
        wedge = wedge.transform(np.array([[0, 0, 1, xb], [1, 0, 0, 0], [0, 1, 0, 0]], float))
        p.append(wedge if s > 0 else L.mirror_y(wedge))
        parts += p
    for (yb, zb_) in FCB_SCREWS:      # FC plate bosses on the right arm's flange rear edges
        z0, z1 = (zb, zb + 7.5) if zb_ < 40 else (zt - 7.5, zt)
        parts.append(L.box((W["arm_x_rear"], yb - 3.5, z0), (W["arm_x_rear"] + 8.0, yb + 3.5, z1)))
    w = L.union(parts)
    cuts = []
    for i, (y, z) in enumerate(W["holes"]):
        cuts.append(L.cyl(CLR_V / 2, (xcb - 1, y, z), X_AX, xf - xcb + 2))
        fit_clear(f"wing-post-{i}", "wing_plate", X_AX, CLR_V)
        # shared with the backpack: head inside the backpack box on its 2 mm front plate, through the wing centre (6.9)
        # into the existing OpenRB-pack post pilot (4.8 deep); M2 x 12 bites 3.1 (Shawn '用 M2×12'); driven with the
        # backpack open, as today
        stack = W["backpack_plate_t"] + (xf - xcb)
        screw(f"post-{i}", f"{W['post_screw']} (existing backpack screw position; Zuorery M2 kit)",
              "backpack front plate + wing centre to the OpenRB pack post",
              (xcb - W["backpack_plate_t"], y, z), (1, 0, 0), round(stack, 2), "wing plate and backpack on the pack")
    for s, nm in ((1, "L"), (-1, "R")):
        for j, (y, z) in enumerate(W["tray_screws"]):
            cuts.append(L.cyl(CLR_V / 2, (xb - 1, s * y, z), X_AX, WEB_T + 2))
            fit_clear(f"wing-tray-{nm}{j}", "wing_plate", X_AX, CLR_V)
            screw(f"tray-{nm}-{j}", "M2 x 10", f"tray {nm} flange to the wing arm web (from behind)",
                  (xb, s * y, z), (1, 0, 0), WEB_T, f"tray {nm} on wing")
        for j, z in enumerate(NAC["lug_screw_z"]):
            cuts.append(L.cyl(LUG_CLR_V / 2, (xb - 1, s * NAC["lug_screw_y"], z), X_AX, WEB_T + 2))
            fit_clear(f"wing-lug-{nm}{j}", "wing_plate", X_AX, LUG_CLR_V, screw=NAC["lug_screw"])
        cs = W["centre_step"]
        y0, y1 = sorted((s * cs["y"], s * (W["centre_ext_w"] + 0.01)))
        cuts.append(L.box((xr, y0, cs["z"]), (xf + 1, y1, W["centre_top"] + 1)))
        y0, y1 = sorted((s * cs["y_low"], s * (W["centre_ext_w"] + 0.01)))       # shell side lip starts at |y| 20
        cuts.append(L.box((xr, y0, W["band_lip_z"]), (xf + 1, y1, cs["z"] + 0.01)))
        y0, y1 = sorted((s * 14.5, s * (W["centre_half_w"] + 0.01)))             # lower corners: 50 % leg reach at z -40
        cuts.append(L.box((xcb - 1, y0, W["centre_bot"] - 1), (xf + 1, y1, -40.5)))
        win = W["lead_window"]
        y0, y1 = sorted((s * win["y"][0], s * win["y"][1]))
        cuts.append(L.box((xb - 1, y0, win["z"][0]), (xf + 1, y1, win["z"][1])))
        if s > 0:                     # the camera USB cable runs on the left only
            cn = W["cam_notch"]
            cuts.append(L.box((cn["x"][0], cn["y"][0], cn["z"][0]), (cn["x"][1], cn["y"][1], cn["z"][1])))
        gw = W["gusset_window"]
        for (g0, g1) in W["gussets"]:
            y0, y1 = sorted((s * (g0 - 1), s * (g1 + 1)))
            gx0 = gw["x_open"] if (g0, g1) in gw["open_rear"] else gw["x"][0]
            cuts.append(L.box((gx0, y0, gw["z"][0]), (gw["x"][1], y1, gw["z"][1])))
    sw = W["swap_window"]
    cuts.append(L.box((xcb - 1, sw["y"][0], sw["z"][0]), (xf + 1, sw["y"][1], sw["z"][1])))
    for j, (yb, zb_) in enumerate(FCB_SCREWS):
        cuts.append(L.cyl(PIL_V / 2, (W["arm_x_rear"] - 1, yb, zb_), X_AX, 9.01))
        fit_pilot(f"wing-fcb-{j}", "wing_plate", X_AX, PIL_V, None, FCB_T, "through", 8 - FCB_T)
    for (ya, yb_) in CAP_SLOTS:       # zip-tie slots around the ESC input capacitor lying on the right top flange
        cuts.append(L.box((CAP_SLOT_X[0], ya, zt - W["flange_t"] - 1), (CAP_SLOT_X[1], yb_, zt + 1)))
    w = w - L.union(cuts)
    # R slot_fillet_r fillet in the top front corner (x gw x1, z gw z1) of each rear-open slot, across the gusset only
    gw, r = W["gusset_window"], W["slot_fillet_r"]
    gxf, gzt = gw["x"][1], gw["z"][1]
    fil = []
    for s in (1, -1):
        for (g0, g1) in gw["open_rear"]:
            y0, y1 = sorted((s * g0, s * g1))
            sq = L.box((gxf - r, y0, gzt - r), (gxf + 0.01, y1, gzt + 0.01))
            fil.append(sq - L.cyl(r, (gxf - r, y0 - 1, gzt - r), Y_AX, y1 - y0 + 2))
    w = w + L.union(fil)
    named = dict(centre=centre)
    return w, named


# ================================================================== battery tray (printed deck-down)
def tray(cam=True):
    """Left tray (y > 0); the right tray is its mirror built with cam=False (the camera USB cable runs on the left only)."""
    T = TRAY
    deck = L.box((T["x"][0], T["y"][0], T["deck_z"][0]), (T["x"][1], T["y"][1], T["deck_z"][1]))
    fl = [L.box((T["flange_x"][0], fy[0], T["flange_z"][0] - 0.01), (T["flange_x"][1], fy[1], T["flange_z"][1]))
          for fy in (T["flange_y"], T["flange2_y"])]
    for fy, top in zip((T["flange_y"], T["flange2_y"]), T["flange_top"]):
        if top > T["flange_z"][1]:      # raised inboard flange for the third screw (strength case 'tray flange screws')
            fl.append(L.box((T["flange_x"][0], T["flange_raised_y0"], T["flange_z"][1] - 0.01), (T["flange_x"][1], fy[1], top)))
    t = L.union([deck] + fl)
    cuts = []
    for (x0, x1) in T["strap_x"]:
        for (y0, y1) in (T["strap_y_in"], T["strap_y_out"]):
            cuts.append(L.box((x0, y0, T["deck_z"][0] - 1), (x1, y1, T["deck_z"][1] + 1)))
    if cam:
        cn = T["cam_notch"]
        cuts.append(L.box((cn["x"][0], cn["y"][0], cn["z"][0]), (cn["x"][1], cn["y"][1], cn["z"][1])))
    for j, (y, z) in enumerate(WING["tray_screws"]):
        cuts.append(L.teardrop(PIL_H, (T["flange_x"][0] - 0.5, y, z), X_AX, T["flange_x"][1] - T["flange_x"][0] + 1.0, up=(0, 0, 1)))
        if cam:                       # declared once: the right tray's pilots are the mirror of these
            fit_pilot(f"tray-pilot-{j}", "tray_L", X_AX, PIL_H, [0, 0, 1], WEB_T, "through", 10 - WEB_T)
    return t - L.union(cuts)


# ================================================================== fans and nacelle
def fan_place(m, which, side=+1):
    """Local frame: +z up the fan axis toward the inlet, origin at the lip-face centre (axial t = -z)."""
    d = Pm.DIR[which]
    up = np.array([-d * S, 0.0, C])
    return L.place(m, Pm.fan_point(which, 0.0, side), up, up=(1, 0, 0))


def lcyl(r, t0, t1, r2=None):
    """Local cylinder from axial t0 to t1 (t grows toward the motor); r2 is the radius at t0 when given."""
    return m3.Manifold.cylinder(t1 - t0, r, r if r2 is None else r2, L.SEG).translate([0, 0, -t1])


def ear_boxes(r, w, t0, t1):
    """The two ears (or their pockets) in the local frame: along local +-x (the nacelle split plane), from the axis to r."""
    b = m3.Manifold.cube([r, w, t1 - t0]).translate([0.0, -w / 2, -t1])
    return b + b.rotate([0, 0, 180])


def fan_keepout(which, side=+1):
    """Space no printed part enters: lip (and band) ahead of the duct, the duct bore, the ear pockets, the rim, stator,
    motor and jet. Every number from FAN through NAC."""
    ft = NAC["front_t"]
    m = (lcyl(NAC["keep_lip_r"], -30.0, ft) + lcyl(NAC["bore"] / 2, ft - 0.1, NAC["t1"] + 0.2)
         + lcyl(NAC["relief"] / 2, NAC["t1"] + 0.1, 110.0))
    if "ear_pocket" in NAC:
        p = NAC["ear_pocket"]
        m = m + ear_boxes(p["r"], 2 * p["half_w"], *p["t"])
        # between the pocket floor and the skirt relief the collar end ring was 0.7 mm thick: open it inside the relief
        # radius; the ear's motor-side stop is the pocket floor outside that radius (relief/2 .. pocket r)
        m = m + ear_boxes(NAC["relief"] / 2, 2 * p["half_w"], p["t"][1] - 0.01, NAC["t1"] + 0.2)
    # a lead slot in every direction the leads may leave (Pm.lead_angles): no printed material there, whichever moulding
    f, T = FAN, Pm.TOL
    for a in Pm.lead_angles(side):
        slot = m3.Manifold.cube([60.0, 9.0, f["lead_t"][1] - f["lead_t"][0] + 2 * T + 1.0])
        m = m + slot.translate([0.0, -4.5, -f["lead_t"][1] - T - 0.5]).rotate([0, 0, a])
    return fan_place(m, which, side)


def fan_dummy(which, side=+1):
    """Envelope of the largest fan in the band of the active FAN set (every size + tol, every end pushed out by tol):
    spinner, lip, band, duct, ears, rim, stator cone, motor, and a lead stub in every possible lead direction."""
    f, T = FAN, Pm.TOL
    parts = [lcyl(f["lip_od"] / 2 + T, f["lip_t"][0], f["lip_t"][1] + T), lcyl(Pm.CLAMP[1] / 2, *f["duct_t"]),
             lcyl(f["rim_od"] / 2 + T, f["rim_t"][0] - T, f["rim_t"][1] + T),
             lcyl(f["motor_od"] / 2 + T, f["motor_t"][0], f["motor_t"][1] + T),
             lcyl(f["stator_od"][1] / 2 + T, f["stator_t"][0], f["stator_t"][1], r2=f["stator_od"][0] / 2 + T)]
    if "band_t" in f:
        parts.append(lcyl(f["band_od"] / 2 + T, *f["band_t"]))
    if "spinner_t" in f:
        parts.append(lcyl(f["spinner_od"] / 2 + T, f["spinner_t"][0] - T, f["spinner_t"][1], r2=1.5))
    if "ear_t" in f:
        parts.append(ear_boxes(f["ear_r"] + T, f["ear_w"] + T, f["ear_t"][0] - T, f["ear_t"][1] + T))
    # three leads leave the motor front ring radially; a 6 x 6 stub to 8 mm past the can in each possible direction
    for a in Pm.lead_angles(side):
        lead = m3.Manifold.cube([f["motor_od"] / 2 + T + 8.0, 6.0, 6.0]).translate([0.0, -3.0, -f["lead_t"][1] - 1.5])
        parts.append(lead.rotate([0, 0, a]))
    return fan_place(L.union(parts), which, side)


def end_walls(which, side=+1):
    """Thick collar wall (NAC end_wall) where the fore and aft screw blocks and the middle web end, tapering back to the
    normal wall over NAC end_taper of arc (strength/README.md, clamp case). Local frame: both blocks lie on local +-x."""
    N = NAC
    rw, ro = N["bore"] / 2 + N["end_wall"], N["r_out"]
    edge = math.asin(max(N["inner_y"], N["outer_y"]) / rw)      # block edge
    h = N["t1"] + 12.0 - N["t0"]

    def lobe(pe, taper, smooth):
        pt = pe + taper / ro                                      # taper end
        pts = [(0.0, 0.0)]
        for a in np.linspace(-pt, pt, 97):
            f = min(1.0, max(0.0, (abs(a) - pe) / (pt - pe)))
            if smooth:
                f = f * f * (3.0 - 2.0 * f)
            r = rw + (ro - rw) * f
            pts.append((r * math.cos(a), r * math.sin(a)))
        return m3.CrossSection([pts]).extrude(h).translate([0, 0, -(N["t1"] + 12.0)])
    # outer-end block (front fan local +x, rear fan local -x; local x is world +x): long thick stretch, long smooth taper
    end = lobe(max(edge, math.radians(N["end_thick_deg"])), N["end_taper_long"], True)
    web = lobe(edge, N["end_taper"], False).rotate([0, 0, 180])
    if which == "rear":
        end, web = end.rotate([0, 0, 180]), web.rotate([0, 0, 180])
    return fan_place(end + web, which, side)


def lug_fillet(side=+1):
    """3 mm round where the inner half's lug (+x face, x = lug_x[1]) meets the rear collar (strength/README.md, handling
    case). The corner wedge (lug face, collar surface, buried 0.3..0.5 into both) is hulled between the bottom and top of
    the lug, so it follows the canted collar; the round is a cylinder through the fillet centres at both ends."""
    N = NAC
    r, R, Y, xl = N["lug_fillet_r"], N["r_out"], Pm.FAN_Y, N["lug_x"][1]
    z_lo, z_hi = N["bed_z"] - 1.0, N["lug_top"] + 1.0
    wedge, centres = [], []
    for z in (z_lo, z_hi):
        ax = Pm.fan_point("rear", (Pm.LIP_Z - z) / C, side)[0]
        ox = xl + r
        oy = Y - math.sqrt((R + r) ** 2 - (ox - ax) ** 2)
        bx, by = ax + (ox - ax) * R / (R + r), Y + (oy - Y) * R / (R + r)
        cx = xl - 0.5
        cy = Y - math.sqrt(R ** 2 - (cx - ax) ** 2)
        cin = (cx + (ax - cx) * 0.2 / R, cy + (Y - cy) * 0.2 / R)          # 0.2 inside the collar
        bin_ = (ax + (bx - ax) * (R - 0.3) / R, Y + (by - Y) * (R - 0.3) / R)
        for (x, y) in ((cx, oy), cin, bin_, (bx, by), (xl, oy)):
            wedge.append((x, side * y, z))
        centres.append((ox, side * oy, z))
    w = m3.Manifold.hull_points(wedge)
    disc = m3.Manifold.cylinder(0.01, r, r, L.SEG)
    cutter = (disc.translate(list(centres[0])) + disc.translate(list(centres[1]))).hull()
    band = L.box((-300, -300, N["bed_z"]), (300, 300, N["lug_top"]))
    return (w - cutter) ^ band


def nacelle(side=+1):
    N = NAC
    ro = N["r_out"]
    nm = "L" if side > 0 else "R"
    top = Pm.LIP_Z - N["t0"] * C
    bed = N["bed_z"]
    y0, y1 = sorted((side * (Pm.FAN_Y - N["inner_y"]), side * (Pm.FAN_Y + N["outer_y"])))
    # thick end walls everywhere except outboard of the middle web on the outer half: the web screw's driver comes in there
    # (its axis is only 33.6 from each fan axis, inside the 34.0 thick-wall face); the inner side of the web keeps them
    ax_r = max(Pm.fan_point("rear", t, side)[0] for t in (N["t0"], N["t1"]))
    ax_f = min(Pm.fan_point("front", t, side)[0] for t in (N["t0"], N["t1"]))
    oy0, oy1 = sorted((side * (Pm.FAN_Y + N["outer_y"]), side * 300.0))
    web_drv = L.box((ax_r, oy0, -300), (ax_f, oy1, 300))
    solids = [(fan_place(lcyl(ro, N["t0"], N["t1"] + 12.0), w, side) + (end_walls(w, side) - web_drv))
              - fan_place(lcyl(N["bore"] / 2, N["t0"] - 1, N["t1"] + 13.0), w, side) for w in ("front", "rear")]
    holes = []
    for w, sgn in (("front", +1), ("rear", -1)):
        xs = [Pm.fan_point(w, t, side)[0] + sgn * N["screw_r"] for t in N["ear_screw_t"]]
        holes += [(x, Pm.fan_point(w, t, side)[2]) for x, t in zip(xs, N["ear_screw_t"])]
        axs = [Pm.fan_point(w, t, side)[0] for t in (N["t0"], N["t1"])]
        # the block's inner face reaches 2 mm into the collar where the canted axis is nearest the block (the bore cut
        # removes the excess): a face that only met the round collar at one end left a 1 mm sliver (2026-11-10)
        if sgn > 0:
            xa, xb = min(axs) + ro - 2.0, max(xs) + N["ear_out"]
        else:
            xa, xb = min(xs) - N["ear_out"], max(axs) - ro + 2.0
        solids.append(L.box((xa, y0, bed), (xb, y1, top)))
    # middle web top stays under both lip keep-outs (their tilted lower faces reach z 59.2 at the web edges): no feather edge
    ft = N["front_t"]
    dists = ((Pm.fan_point("front", ft)[0] - N["web_x"][1]) / C, (N["web_x"][0] - Pm.fan_point("rear", ft)[0]) / C)
    web_top = Pm.LIP_Z - ft * C - min(min(d, N["keep_lip_r"]) for d in dists) * S - 0.3
    if "ear_pocket" in N:      # the web screw sits above the ear pockets: the web rises to the collar top, the lip keep-outs cut it
        web_top = Pm.LIP_Z - N["t0"] * C
    solids.append(L.box((N["web_x"][0], y0, bed), (N["web_x"][1], y1, web_top)))
    holes.append((sum(N["web_x"]) / 2, Pm.fan_point("front", N["web_screw_t"], side)[2]))
    keep = fan_keepout("front", side) + fan_keepout("rear", side)
    above = L.box((-300, -300, bed), (300, 300, 300))
    # 4 mm free radius over every clamp screw axis outside the outer face, for the driver (the thick end walls of the middle
    # web otherwise wrap over the web screw, whose axis sits only 33.6 from each fan axis)
    drv = L.union([L.cyl(4.0, (x, side * (Pm.FAN_Y + N["outer_y"]), z), (0, side, 0), 60.0) for x, z in holes])
    solid = (L.union(solids) - keep - drv) ^ above
    g = N["split_gap"] / 2
    inner_space = L.box((-300, min(0, side * (Pm.FAN_Y - g)), -300), (300, max(0, side * (Pm.FAN_Y - g)), 300))
    outer_space = L.box((-300, min(side * (Pm.FAN_Y + g), side * 300), -300), (300, max(side * (Pm.FAN_Y + g), side * 300), 300))
    ly0, ly1 = sorted((side * N["lug_y"][0], side * N["lug_y"][1]))
    lug = L.box((N["lug_x"][0], ly0, bed), (N["lug_x"][1], ly1, N["lug_top"])) + lug_fillet(side)
    inner = (solid ^ inner_space) + ((lug - keep) ^ above)
    outer = solid ^ outer_space
    ci, co = [], []
    # clamp screws: blind pilot in the inner half for the longest bite (smallest fan, seams nearly closed) + 1 mm; the head
    # sits in a counterbore so under_head of material stays under it and the bite stays within 2.5 d over the travel
    uh, bite_max = N["under_head"], N["bite"][1]
    pdep = bite_max + 1.0
    hs_d = N["head_seat"][0]
    for k, (x, z) in enumerate(holes):
        ci.append(L.teardrop(PIL_H, (x, side * (Pm.FAN_Y - g - pdep), z), (0, side, 0), pdep + 0.01, up=(0, 0, 1)))
        co.append(L.teardrop(CLR_H, (x, side * (Pm.FAN_Y + g - 0.5), z), (0, side, 0), N["outer_y"] + 1.0, up=(0, 0, 1)))
        co.append(L.teardrop(hs_d, (x, side * (Pm.FAN_Y + g + uh), z), (0, side, 0), N["outer_y"] - g - uh + 1.0, up=(0, 0, 1)))
        wt = N["washer"]["t"]                                     # M2 washer in the 5.4 seat, head on top of it
        clamped = uh + wt + (N["split_gap"] - N["travel"])      # smallest fan: seams 0.5 apart, bite 5.0
        if side > 0:
            fit_pilot(f"nac-split-pilot-{k}", "nacelle_inner_L", Y_AX, PIL_H, [0, 0, 1], round(clamped, 2), round(pdep, 2), round(N["screw_len"] - clamped, 2))
            fit_clear(f"nac-split-clear-{k}", "nacelle_outer_L", Y_AX, CLR_H, [0, 0, 1])
        screw(f"nac-{nm}-{k}", f"M2 x {N['screw_len']:.0f} (with M2 washer)", f"nacelle outer {nm} to nacelle inner {nm} (closes the seams onto the taped duct)",
              (x, side * (Pm.FAN_Y + g + uh + wt), z), (0, -side, 0), round(uh + wt, 2), f"nacelle {nm}")
    ls, ll = N["lug_screw"], N["lug_screw_len"]
    for k, z in enumerate(N["lug_screw_z"]):
        ci.append(L.teardrop(LUG_PIL_H, (N["lug_x"][0] - 0.01, side * N["lug_screw_y"], z), X_AX, N["lug_x"][1] - N["lug_x"][0] + 0.02, up=(0, 0, 1)))
        if side > 0:
            fit_pilot(f"nac-lug-pilot-{k}", "nacelle_inner_L", X_AX, LUG_PIL_H, [0, 0, 1], WEB_T, "through", ll - WEB_T, screw=ls)
        screw(f"lug-{nm}-{k}", f"{ls} x {ll:.0f}", f"nacelle inner {nm} lug to the wing arm web (from behind)",
              (WING["x_back"], side * N["lug_screw_y"], z), (1, 0, 0), WEB_T, f"nacelle {nm} on wing")
    inner, outer = inner - L.union(ci), outer - L.union(co)
    return inner, outer, dict(holes=holes, top=top, bed=bed)


# ================================================================== brackets
def fc_bracket():
    """Plate behind the right arm carrying the 30.5 mm FC + ESC stack, with a shelf under it for the MTF-01 (lens down)."""
    x0, x1 = FCB_X
    W = WING
    plate = L.box((x0, -74.0, SHELF_Z[0]), (x1, -37.0, W["arm_z"][1]))
    yc, zc = FC_CENTRE
    pat = FC["pattern"] / 2
    m3h = [(yc + a * pat, zc + b * pat) for a in (-1, 1) for b in (-1, 1)]
    bosses = [L.cyl(3.5, (x0 - FC_BOSS, y, z), X_AX, FC_BOSS + 0.01) for (y, z) in m3h]
    shelf = L.box((MTF_C[0] - 16.0, -72.0, SHELF_Z[0]), (x1, -46.0, SHELF_Z[1]))
    b = L.union([plate, shelf] + bosses)
    cuts = [L.box((x0 - 1, -66.5, FCB_WINDOW_Z[0]), (x1 + 1, -55.5, FCB_WINDOW_Z[1]))]   # leads from the bay into the ESC gap
    for j, (y, z) in enumerate(FCB_SCREWS):
        cuts.append(L.cyl(CLR_V / 2, (x0 - 1, y, z), X_AX, FCB_T + 2))
        fit_clear(f"fcb-clear-{j}", "fc_bracket", X_AX, CLR_V)
        screw(f"fcb-{j}", "M2 x 8", "FC bracket plate to the right arm flange boss", (x0, y, z), (1, 0, 0), FCB_T, "FC bracket on wing (before the stack)")
    for j, (y, z) in enumerate(m3h):
        cuts.append(L.cyl(M3_PIL_V / 2, (x0 - FC_BOSS - 0.5, y, z), X_AX, FC_BOSS + FCB_T + 1))
        FITS.append(dict(id=f"fcb-m3-{j}", type="pilot", part="fc_bracket", screw="M3", kind="any", d=M3_PIL_V, axis=[1, 0, 0],
                         teardrop=None, at_bed=False, chamfer=0.0, engagement=FC_BOSS + FCB_T, depth="through", clamped=0.0))
        # metal (brass/steel) since 2026-11-12: RoboClub has no nylon M3 standoffs (Shawn: "尼龙换成金属"); the 2.9 pilot is the
        # PRINT-FIT "any" M3 value, which machine threads form without a drill
        screw(f"fc-standoff-{j}", "M3 x 6 male-female metal standoff (male end into the pilot)", "FC/ESC stack to the FC bracket",
              (x0 - FC_BOSS, y, z), (1, 0, 0), 0.0, "stack")
        xe = x0 - FC_BOSS - 6.0 - STACK["esc_pcb"]          # ESC rear PCB face
        screw(f"esc-fc-spacer-{j}", f"M3 x {STACK['spacer']:.0f} male-female metal spacer (male end through the ESC into the standoff)",
              "ESC clamped between the plate standoff and this spacer; carries the FC", (xe, y, z), (1, 0, 0), STACK["esc_pcb"], "stack")
        xf = xe - STACK["spacer"] - STACK["fc_pcb"] - STACK["grommet"]   # head seat on the FC grommet
        screw(f"fc-screw-{j}", "M3 x 8 metal screw into the spacer's female end (the spacer chain ends female, so a nut has no thread to sit on)",
              "FC on the ESC-to-FC spacer", (xf, y, z), (1, 0, 0), STACK["fc_pcb"] + STACK["grommet"], "stack")
    mx, my = MTF_C
    for j, (a, bb) in enumerate(((-1, -1), (-1, 1), (1, -1), (1, 1))):
        p = (mx + a * MTF01["holes"][0] / 2, my + bb * MTF01["holes"][1] / 2)
        cuts.append(L.teardrop(PIL_H, (p[0], p[1], SHELF_Z[0] - 0.01), Z_AX, SHELF_Z[1] - SHELF_Z[0] + 0.02, up=(-1, 0, 0)))
        fit_pilot(f"mtf-pilot-{j}", "fc_bracket", Z_AX, PIL_H, [-1, 0, 0], 1.6, "through", 4 - 1.6)
        screw(f"mtf-{j}", "M2 x 4", "MTF-01 board (1.6 mm flange) to the shelf, from below", (p[0], p[1], SHELF_Z[0] - 1.6), (0, 0, 1), 1.6, "flow module")
    return b - L.union(cuts), dict(m3=m3h)


# No compass bracket: the external GPS/compass module was deleted (Shawn 2026-11-10, "删掉"); heading comes from the
# duck's IMU via the A7Z (ArduPilot ExternalNav yaw) with the FC's onboard compass as fallback.


# ================================================================== dummies (bought parts with plug and lead keep-outs)
def dummies():
    D = {}
    W = WING
    for side, nm in ((1, "L"), (-1, "R")):
        D[f"fan_front_{nm}"] = fan_dummy("front", side)
        D[f"fan_rear_{nm}"] = fan_dummy("rear", side)
        bx, by = BATT["x0"], BATT["y0"]
        lx, wy, hz = BATT["size"]
        z0 = TRAY["deck_z"][1]
        y0, y1 = sorted((side * by, side * (by + wy)))
        D[f"battery_{nm}"] = L.box((bx, y0, z0), (bx + lx, y1, z0 + hz))
        # XT60 (12 AWG) and balance lead leave the rear end, bend up and pass the arm web lead window into the bay
        lw = W["lead_window"]
        wy0, wy1 = sorted((side * (lw["y"][0] + 0.5), side * (lw["y"][1] - 0.5)))
        D[f"battery_leads_{nm}"] = L.box((W["x_back"] - 4.0, wy0, lw["z"][0] + 0.5), (bx + 0.01, wy1, lw["z"][1] - 0.5))
    x0 = FCB_X[0] - FC_BOSS
    yc, zc = FC_CENTRE
    st = STACK
    xe0 = x0 - 6.0                                     # ESC front PCB face on the 6 mm plate standoffs
    xe1 = xe0 - st["esc_h"]
    xf0 = xe0 - st["esc_pcb"] - st["spacer"] + st["fc_under"]     # FC envelope front (underside parts)
    xf1 = xf0 - st["fc_h"]
    esc = L.box((xe1, yc - 20.5, zc - 20.5), (xe0, yc + 20.5, zc + 20.5))
    fc = L.box((xf1, yc - 18.0, zc - 18.0), (xf0, yc + 18.0, zc + 18.0))
    plugs = L.box((xf1, yc - 18.0 - 10.0, zc - 18.0), (xf0, yc - 18.0, zc + 18.0))   # UART4 SH plug + MTF lead, outboard edge
    uart1 = L.box((xf1, yc - 5.0, zc + 18.0 - 0.01), (xf0, yc + 5.0, zc + 18.0 + 6.0))  # UART1 SH plug on the top edge
    D["fc_esc_stack"] = esc + fc + plugs + uart1
    zt_tape = W["arm_z"][1] + CAP_TAPE["t"]          # can on the foam tape strip, not on the bare flange
    D["esc_capacitor"] = L.cyl(Pm.CAP["d"] / 2, (CAP_AXIS["x0"], CAP_AXIS["y"], zt_tape + Pm.CAP["d"] / 2), (-1, 0, 0), Pm.CAP["h"])
    D["cap_tape"] = L.box((CAP_TAPE["x"][0], CAP_AXIS["y"] - CAP_TAPE["w"] / 2, W["arm_z"][1]),
                          (CAP_TAPE["x"][1], CAP_AXIS["y"] + CAP_TAPE["w"] / 2, zt_tape))
    # A7Z-to-FC lead (A7Z header pins 14 GND, 16 UART4 TX, 18 RX -> FC UART1; SH1.0 to Dupont, 3 wires, bundle d 3).
    # Dupont housings on the edge row (world sd_dupont_housings models housings on all 40 pins: x -17.7..-12.7, z to
    # 64.1); wires leave the housing tops, run along the header strip (not over the 6530B fan intake) to the right saddle
    # side wall, along its top edge rearward, drop outboard of the saddle rear window (|y| < 30), run behind the right
    # transition column inboard of the arm flange (y -35) to the stack, and end in the UART1 plug on the FC top edge.
    D["a7z_link"] = L.union([L.box((-17.7, 2.5, 64.1 - 0.01), (-12.7, 10.2, 68.0))] + tube_path(1.5, A7Z_LINK))
    mx, my = MTF_C
    sz = MTF01["size"]
    D["mtf01"] = L.box((mx - sz[0] / 2, my - sz[1] / 2, SHELF_Z[0] - sz[2]), (mx + sz[0] / 2, my + sz[1] / 2, SHELF_Z[0]))
    hs, hr = W["harness_side"], W["harness_rear"]
    D["cross_harness"] = L.union([L.box((hs["x"][0], hs["y"][0], hs["z"][0]), (hs["x"][1], hs["y"][1], hs["z"][1])),
                                  L.box((hr["x"][0], hr["y"][0], hr["z"][0]), (hr["x"][1] + 0.01, hr["y"][1], hr["z"][1]))])
    return D


# ================================================================== main
POSES = {   # print_rot as print_fit.to_print expects (applied in order)
    "wing_plate": [((0, 1, 0), 90.0), ((0, 0, 1), -90.0)],        # front face (x -45) on the bed
    "tray_L": [], "tray_R": [],                                    # deck underside on the bed
    "nacelle_inner_L": [], "nacelle_outer_L": [], "nacelle_inner_R": [], "nacelle_outer_R": [],   # upright, bed plane z 32.35
    "fc_bracket": [((0, 1, 0), 90.0)],                             # plate front face (x -64) on the bed
}
COLOUR = {"wing_plate": "Orange", "tray_L": "Orange", "tray_R": "Orange", "fc_bracket": "Orange",
          # the four nacelle halves (148 x 140 together) do not fit the 220 mm usable square beside the wing plate: own plate
          "nacelle_inner_L": "Black", "nacelle_outer_L": "Black", "nacelle_inner_R": "Black", "nacelle_outer_R": "Black"}


def main():
    wing, named = wing_plate()
    nil, nol, ninfo = nacelle(+1)
    nir, nor, _ = nacelle(-1)
    tl = tray()
    fcb, _ = fc_bracket()
    parts = {"wing_plate": wing, "tray_L": tl, "tray_R": L.mirror_y(tray(cam=False)), "nacelle_inner_L": nil, "nacelle_outer_L": nol,
             "nacelle_inner_R": nir, "nacelle_outer_R": nor, "fc_bracket": fcb}
    contract = {"wing_plate_centre": named["centre"], "wing_plate_mid": wing ^ L.box((-100, -37, -100), (0, 37, 200))}
    info = {}
    for n, man in list(parts.items()) + list(contract.items()):
        t = L.to_trimesh(man)
        t.export(OUT / f"{n}-world.stl")
        if n in POSES:
            pr = L.to_print(t, POSES[n])
            pr.export(OUT / f"{n}-print.stl")
            info[n] = dict(colour=COLOUR[n], volume_cm3=round(float(man.volume()) / 1000, 2), watertight=bool(t.is_watertight),
                           bodies=len(t.split(only_watertight=False)), genus=int(man.genus()),
                           bounds=np.round(t.bounds, 2).tolist(), print_size=np.round(pr.extents, 1).tolist(),
                           centroid=np.round(t.center_mass, 1).tolist(), print_rot=POSES[n])
    written = {f"{n}-world.stl" for n in list(parts) + list(contract)} | {f"{n}-print.stl" for n in POSES}
    for n, man in dummies().items():
        L.to_trimesh(man).export(OUT / f"dummy_{n}-world.stl")
        written.add(f"dummy_{n}-world.stl")
    for f in OUT.glob("*.stl"):          # a part removed from the design (e.g. the compass bracket) must not linger
        if f.name not in written:
            print("removed stale", f.name)
            f.unlink()
    info["nacelle"] = dict(bed_z=round(NAC["bed_z"], 2), collar_top=round(ninfo["top"], 2), bore=NAC["bore"],
                           holes_xz=[[round(a, 2) for a in p] for p in ninfo["holes"]])
    info["clamp"] = dict(
        fan=Pm.FAN_ID, duct_od_range=list(Pm.CLAMP), tol=Pm.TOL, bore=NAC["bore"], tape=NAC["tape"],
        printed_seam_gap=NAC["split_gap"], screw_travel=NAC["travel"], under_head=NAC["under_head"], bite_mm=list(NAC["bite"]),
        collar_t=[round(NAC["t0"], 2), round(NAC["t1"], 2)], ear_pocket=NAC.get("ear_pocket"), lead_slots_deg=Pm.lead_angles(1),
        says=(f"closes on duct OD {Pm.CLAMP[0]}..{Pm.CLAMP[1]} mm with one layer of 1 mm foam tape in each bore: largest fan with "
              f"the seams {NAC['split_gap']} apart (tape at {NAC['tape']['firm']}), smallest after the screws close them "
              f"{NAC['travel']} mm (tape at {NAC['tape']['grip']}); M2 x {NAC['screw_len']:.0f} bite {NAC['bite'][0]}..{NAC['bite'][1]} mm"))
    print("clamp:", info["clamp"]["says"])
    info["fan"] = dict(lip_centre_z=round(Pm.LIP_Z, 2),
                       motor_end_axis={w: [round(v, 2) for v in Pm.fan_point(w, FAN["motor_t"][1])] for w in ("front", "rear")},
                       motor_end_lowest_z=round(Pm.LIP_Z - FAN["motor_t"][1] * C - FAN["motor_od"] / 2 * S, 2))
    (OUT / "build.json").write_text(json.dumps(info, indent=1))
    (H / "FITS.json").write_text(json.dumps(dict(printer=PR, poses={k: [[list(a), d] for a, d in v] for k, v in POSES.items()},
                                                 fits=FITS), indent=1))
    (OUT / "screws.json").write_text(json.dumps(SCREWS, indent=1))
    for k, v in info.items():
        if "volume_cm3" in v:
            print(f"{k:18s} {v['volume_cm3']:7.2f} cm3  watertight {v['watertight']}  bodies {v['bodies']}  print {v['print_size']}")
        else:
            print(k, v)


if __name__ == "__main__":
    main()
