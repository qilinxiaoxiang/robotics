"""Build the flight-pack printed parts (DESIGN-CONTRACT.json). Guide frame, mm (x forward, y left, z up).
Writes build/<part>-world.stl (robot pose), build/<part>-print.stl (print pose, on the bed), build/dummy_*-world.stl
(bought parts with plug and lead keep-outs), build/build.json, build/screws.json and FITS.json (cad-practice/fit_check.py).
    /tmp/microduck-cad-venv/bin/python cad/build_pack.py          (about 10 s)
"""
import json
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
X_AX, Y_AX, Z_AX = (1, 0, 0), (0, 1, 0), (0, 0, 1)
WEB_T = WING["x_front"] - WING["x_back"]       # 5.2

FITS, SCREWS = [], []


def fit_pilot(fid, part, axis, d, teardrop, clamped, depth, eng):
    FITS.append(dict(id=fid, type="pilot", part=part, screw="M2", kind="any", d=d, axis=list(axis), teardrop=teardrop,
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
FCB_WINDOW_Z = (25.5, 37.0)                                          # 2.5 mm above the lower plate screws' holes
CAP_SLOTS_Y = (-58.0, -76.0)                                         # capacitor y -79..-54 on the arm's outer half (head reach ends near y -47)
CAP_Y0 = -79.0
MTF_C = (-86.0, -59.0)                                               # MTF-01 centre (x, y): behind the leg sweep at x > -70
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
        p = [B(xcb, xf, W["centre_half_w"] - 0.01, W["centre_ext_w"], W["band_z"][0], W["centre_top"]),
             B(xb, xcb + 0.01, W["centre_half_w"] + 0.3, W["centre_ext_w"], W["band_z"][0], W["centre_top"]),
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
        parts += p
    for (yb, zb_) in FCB_SCREWS:      # FC plate bosses on the right arm's flange rear edges
        z0, z1 = (zb, zb + 7.5) if zb_ < 40 else (zt - 7.5, zt)
        parts.append(L.box((W["arm_x_rear"], yb - 3.5, z0), (W["arm_x_rear"] + 8.0, yb + 3.5, z1)))
    w = L.union(parts)
    cuts = []
    for i, (y, z) in enumerate(W["holes"]):
        cuts.append(L.cyl(CLR_V / 2, (xcb - 1, y, z), X_AX, 6))
        fit_clear(f"wing-post-{i}", "wing_plate", X_AX, CLR_V)
        # shared with the backpack: head inside the backpack box on its 2 mm front plate (x -50.5 shifted), through the
        # wing centre (3.5) into the existing OpenRB-pack post pilot; driven with the backpack open, as today
        screw(f"post-{i}", "M2 x 10 (existing backpack screw)", "backpack front plate + wing centre to the OpenRB pack post",
              (xcb - 2.0, y, z), (1, 0, 0), 5.5, "wing plate and backpack on the pack")
    for s, nm in ((1, "L"), (-1, "R")):
        for j, (y, z) in enumerate(W["tray_screws"]):
            cuts.append(L.cyl(CLR_V / 2, (xb - 1, s * y, z), X_AX, WEB_T + 2))
            fit_clear(f"wing-tray-{nm}{j}", "wing_plate", X_AX, CLR_V)
            screw(f"tray-{nm}-{j}", "M2 x 10", f"tray {nm} flange to the wing arm web (from behind)",
                  (xb, s * y, z), (1, 0, 0), WEB_T, f"tray {nm} on wing")
        for j, z in enumerate(NAC["lug_screw_z"]):
            cuts.append(L.cyl(CLR_V / 2, (xb - 1, s * NAC["lug_screw_y"], z), X_AX, WEB_T + 2))
            fit_clear(f"wing-lug-{nm}{j}", "wing_plate", X_AX, CLR_V)
        cs = W["centre_step"]
        y0, y1 = sorted((s * cs["y"], s * (W["centre_ext_w"] + 0.01)))
        cuts.append(L.box((xr, y0, cs["z"]), (xf + 1, y1, W["centre_top"] + 1)))
        y0, y1 = sorted((s * cs["y_low"], s * (W["centre_ext_w"] + 0.01)))       # shell side lip starts at |y| 20
        cuts.append(L.box((xr, y0, W["band_lip_z"]), (xf + 1, y1, cs["z"] + 0.01)))
        y0, y1 = sorted((s * 14.5, s * (W["centre_half_w"] + 0.01)))             # lower corners: 50 % leg reach at z -40
        cuts.append(L.box((xcb - 1, y0, W["centre_bot"] - 1), (xf + 1, y1, -40.5)))
        for win in (W["lead_window"], W["fan_window"]):
            y0, y1 = sorted((s * win["y"][0], s * win["y"][1]))
            cuts.append(L.box((xb - 1, y0, win["z"][0]), (xf + 1, y1, win["z"][1])))
        gw = W["gusset_window"]
        for (g0, g1) in W["gussets"]:
            y0, y1 = sorted((s * (g0 - 1), s * (g1 + 1)))
            cuts.append(L.box((gw["x"][0], y0, gw["z"][0]), (gw["x"][1], y1, gw["z"][1])))
    sw = W["swap_window"]
    cuts.append(L.box((xcb - 1, sw["y"][0], sw["z"][0]), (xf + 1, sw["y"][1], sw["z"][1])))
    for j, (yb, zb_) in enumerate(FCB_SCREWS):
        cuts.append(L.cyl(PIL_V / 2, (W["arm_x_rear"] - 1, yb, zb_), X_AX, 9.01))
        fit_pilot(f"wing-fcb-{j}", "wing_plate", X_AX, PIL_V, None, FCB_T, "through", 8 - FCB_T)
    for yc in CAP_SLOTS_Y:            # zip-tie slots around the ESC input capacitor lying on the right top flange
        cuts.append(L.box((-58.5, yc - 1.75, zt - W["flange_t"] - 1), (-55.5, yc + 1.75, zt + 1)))
    w = w - L.union(cuts)
    named = dict(centre=centre)
    return w, named


# ================================================================== battery tray (printed deck-down)
def tray():
    T = TRAY
    deck = L.box((T["x"][0], T["y"][0], T["deck_z"][0]), (T["x"][1], T["y"][1], T["deck_z"][1]))
    fl = [L.box((T["flange_x"][0], fy[0], T["flange_z"][0] - 0.01), (T["flange_x"][1], fy[1], T["flange_z"][1]))
          for fy in (T["flange_y"], T["flange2_y"])]
    t = L.union([deck] + fl)
    cuts = []
    for (x0, x1) in T["strap_x"]:
        for (y0, y1) in (T["strap_y_in"], T["strap_y_out"]):
            cuts.append(L.box((x0, y0, T["deck_z"][0] - 1), (x1, y1, T["deck_z"][1] + 1)))
    for j, (y, z) in enumerate(WING["tray_screws"]):
        cuts.append(L.teardrop(PIL_H, (T["flange_x"][0] - 0.5, y, z), X_AX, T["flange_x"][1] - T["flange_x"][0] + 1.0, up=(0, 0, 1)))
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


def fan_keepout(which, side=+1):
    """Space no printed part enters: lip and band (r 32.5 for t < 9.7), the duct bore, the rim, stator, motor and jet."""
    m = lcyl(NAC["keep_lip_r"], -30.0, 9.7) + lcyl(NAC["bore"] / 2, 9.6, 36.6) + lcyl(NAC["relief"] / 2, 36.5, 110.0)
    return fan_place(m, which, side)


def fan_dummy(which, side=+1):
    """Bought-part envelope: lip, band, duct, rim, stator cone, motor (FAN dict), lead exit toward the body."""
    f = FAN
    m = L.union([lcyl(f["lip_od"] / 2, *f["lip_t"]), lcyl(f["band_od"] / 2, *f["band_t"]), lcyl(f["duct_od"] / 2, *f["duct_t"]),
                 lcyl(f["rim_od"] / 2, *f["rim_t"]), lcyl(f["motor_od"] / 2, *f["motor_t"]),
                 lcyl(f["stator_od"][1] / 2, f["stator_t"][0], f["stator_t"][1], r2=f["stator_od"][0] / 2)])
    # three leads leave the motor front ring radially; keep-out 6 x 6 toward the body (world -side*y), 20 mm past the can
    lead = m3.Manifold.cube([6.0, f["motor_od"] / 2 + 8.0, 6.0]).translate([-3.0, 0.0, -f["lead_t"][1] - 2.0])
    lead = lead.mirror([0, 1, 0]) if side > 0 else lead
    return fan_place(m + lead, which, side)


def nacelle(side=+1):
    N = NAC
    ro = N["r_out"]
    nm = "L" if side > 0 else "R"
    top = Pm.LIP_Z - N["t0"] * C
    bed = N["bed_z"]
    solids = [fan_place(lcyl(ro, N["t0"], N["t1"] + 12.0) - lcyl(N["bore"] / 2, N["t0"] - 1, N["t1"] + 13.0), w, side)
              for w in ("front", "rear")]
    y0, y1 = sorted((side * (Pm.FAN_Y - N["inner_y"]), side * (Pm.FAN_Y + N["outer_y"])))
    holes = []
    for w, sgn in (("front", +1), ("rear", -1)):
        xs = [Pm.fan_point(w, t, side)[0] + sgn * N["screw_r"] for t in N["ear_screw_t"]]
        holes += [(x, Pm.fan_point(w, t, side)[2]) for x, t in zip(xs, N["ear_screw_t"])]
        axs = [Pm.fan_point(w, t, side)[0] for t in (N["t0"], N["t1"])]
        if sgn > 0:
            xa, xb = max(axs) + ro - 2.0, max(xs) + N["ear_out"]
        else:
            xa, xb = min(xs) - N["ear_out"], min(axs) - ro + 2.0
        solids.append(L.box((xa, y0, bed), (xb, y1, top)))
    # middle web top stays under both lip keep-outs (their tilted lower faces reach z 59.2 at the web edges): no feather edge
    web_top = Pm.LIP_Z - 9.7 * C - (N["keep_lip_r"] - 4.9) * S - 0.3
    solids.append(L.box((N["web_x"][0], y0, bed), (N["web_x"][1], y1, web_top)))
    holes.append((sum(N["web_x"]) / 2, Pm.fan_point("front", N["web_screw_t"], side)[2]))
    keep = fan_keepout("front", side) + fan_keepout("rear", side)
    above = L.box((-300, -300, bed), (300, 300, 300))
    solid = (L.union(solids) - keep) ^ above
    g = N["split_gap"] / 2
    inner_space = L.box((-300, min(0, side * (Pm.FAN_Y - g)), -300), (300, max(0, side * (Pm.FAN_Y - g)), 300))
    outer_space = L.box((-300, min(side * (Pm.FAN_Y + g), side * 300), -300), (300, max(side * (Pm.FAN_Y + g), side * 300), 300))
    ly0, ly1 = sorted((side * N["lug_y"][0], side * N["lug_y"][1]))
    lug = L.box((N["lug_x"][0], ly0, bed), (N["lug_x"][1], ly1, N["lug_top"]))
    inner = (solid ^ inner_space) + ((lug - keep) ^ above)
    outer = solid ^ outer_space
    ci, co = [], []
    for k, (x, z) in enumerate(holes):
        ci.append(L.teardrop(PIL_H, (x, side * (Pm.FAN_Y - N["inner_y"] - 0.5), z), (0, side, 0), N["inner_y"] + 0.5 - g + 0.01, up=(0, 0, 1)))
        co.append(L.teardrop(CLR_H, (x, side * (Pm.FAN_Y + g - 0.5), z), (0, side, 0), N["outer_y"] + 1.0, up=(0, 0, 1)))
        clamped = N["outer_y"] - g + N["split_gap"]
        if side > 0:
            fit_pilot(f"nac-split-pilot-{k}", "nacelle_inner_L", Y_AX, PIL_H, [0, 0, 1], clamped, "through", 10 - clamped)
            fit_clear(f"nac-split-clear-{k}", "nacelle_outer_L", Y_AX, CLR_H, [0, 0, 1])
        screw(f"nac-{nm}-{k}", "M2 x 10", f"nacelle outer {nm} to nacelle inner {nm} (clamps the duct band)",
              (x, side * (Pm.FAN_Y + N["outer_y"]), z), (0, -side, 0), round(clamped, 2), f"nacelle {nm}")
    for k, z in enumerate(N["lug_screw_z"]):
        ci.append(L.teardrop(PIL_H, (N["lug_x"][0] - 0.01, side * N["lug_screw_y"], z), X_AX, N["lug_x"][1] - N["lug_x"][0] + 0.02, up=(0, 0, 1)))
        if side > 0:
            fit_pilot(f"nac-lug-pilot-{k}", "nacelle_inner_L", X_AX, PIL_H, [0, 0, 1], WEB_T, "through", 10 - WEB_T)
        screw(f"lug-{nm}-{k}", "M2 x 10", f"nacelle inner {nm} lug to the wing arm web (from behind)",
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
        screw(f"fc-standoff-{j}", "M3 x 6 male-female nylon standoff (male end into the pilot)", "FC/ESC stack to the FC bracket",
              (x0 - FC_BOSS, y, z), (1, 0, 0), 0.0, "stack")
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
    esc = L.box((x0 - 6.0 - 6.0, yc - 20.5, zc - 20.5), (x0 - 6.0, yc + 20.5, zc + 20.5))
    fc = L.box((x0 - 12.0 - 5.0 - 8.0, yc - 18.0, zc - 18.0), (x0 - 12.0 - 5.0, yc + 18.0, zc + 18.0))
    plugs = L.box((x0 - 12.0 - 5.0 - 8.0, yc - 18.0 - 10.0, zc - 18.0), (x0 - 12.0 - 5.0, yc - 18.0, zc + 18.0))   # JST-SH plugs, outboard edge
    D["fc_esc_stack"] = esc + fc + plugs
    D["esc_capacitor"] = L.cyl(Pm.CAP["d"] / 2, (-57.0, CAP_Y0, W["arm_z"][1] + Pm.CAP["d"] / 2), Y_AX, Pm.CAP["h"])
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
    parts = {"wing_plate": wing, "tray_L": tl, "tray_R": L.mirror_y(tl), "nacelle_inner_L": nil, "nacelle_outer_L": nol,
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
