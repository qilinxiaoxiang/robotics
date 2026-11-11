"""Why the root twists, and what the geometry allows (strength/SPAR-OPTION.md, "Thrust centre and the arm").
Hand calculation only.  /tmp/microduck-cad-venv/bin/python strength/root_alignment.py  -> out/root_alignment.json

1. thrust centre of each side's fan pair, side mass centroid, and where the root band is;
2. hover trim if the fan pair moves back (sim/out/authority.json: COM, pitch authority at 80 % thrust, demand);
3. root band SF in PLA at 100 % infill if the band is a solid rectangle d mm deep in x (rearward growth only: the saddle
   keep-out is in front), for d = today's 5.1 mm and deeper.
"""
import json

import numpy as np

import hand_calcs as hc
from common import MAT, OUT, Pm, fan_centre, resultant, section_stress

PLA = MAT["PLA"]
EY = np.eye(3)[1]
AUTH = json.loads((OUT.parents[1] / "sim" / "out" / "authority.json").read_text())
CASES = ["thrust_1.5x_on_ground", "vertical_impact_15.6g", "handling_lift_by_nacelle", "fore_aft_10g", "lateral_10g"]
# band rows (z extent) of the real sections at y 21 / 29 / 31 (hand_calcs.WING_SECTIONS), front face x -45.05
BAND = {21.0: (-0.95, 27.95), 29.0: (9.05, 27.95), 31.0: (9.05, 42.45)}
X_FRONT = -45.05
ALPHA = [(1.0, 0.208), (1.5, 0.231), (2.0, 0.246), (2.5, 0.258), (3.0, 0.267), (4.0, 0.282), (5.0, 0.291), (6.0, 0.299),
         (10.0, 0.312), (100.0, 0.333)]       # Roark, solid rectangle: tau_max = T / (alpha b t^2), b >= t


def rect_raster(d, z0, z1, step=0.1):
    a = np.arange(X_FRONT - d + step / 2, X_FRONT, step)
    b = np.arange(z0 + step / 2, z1, step)
    A, B = np.meshgrid(a, b, indexing="ij")
    m = np.ones_like(A, bool)
    return dict(A=A, B=B, mask=m, w=m.astype(float), step=step)


def tau_rect(T, d, h):
    b, t = max(d, h), min(d, h)
    al = float(np.interp(b / t, [r for r, _ in ALPHA], [a for _, a in ALPHA]))
    return abs(T) / (al * b * t * t)


def geometry():
    fF, fR = fan_centre("front"), fan_centre("rear")
    lipF, lipR = Pm.fan_point("front", 0.0), Pm.fan_point("rear", 0.0)
    nac = [(m, np.asarray(p)) for m, p in hc.NAC_MASSES]
    tray = [(m, np.asarray(p)) for m, p in hc.TRAY_MASSES]
    cx = lambda ms: sum(m * p[0] for m, p in ms) / sum(m for m, _ in ms)
    return dict(
        thrust_centre_x=round(0.5 * (fF[0] + fR[0]), 2),
        note="equal thrust, canted +-6 deg: the horizontal parts cancel and the resultant is vertical at the midpoint "
             f"(collar centres x {fF[0]:.2f} / {fR[0]:.2f}, lip points x {lipF[0]:.1f} / {lipR[0]:.1f})",
        hover_com_x=AUTH["com_mm"][0], nacelle_mass_centroid_x=round(cx(nac), 1), tray_mass_centroid_x=round(cx(tray), 1),
        side_mass_centroid_x=round(cx(nac + tray), 1),
        root_band=dict(x=[-50.15, X_FRONT], centroid_x=-47.6, y=[20.3, 31.0]),
        lever_thrust_mm=round(0.5 * (fF[0] + fR[0]) - (-47.6), 1))


def trim():
    """Shift both fans (and their nacelles) back by s. Thrust centre moves s, the COM moves s * m_moved / m."""
    m = AUTH["mass_g"]
    moved = 4 * hc.SIDE["fan_g"] + 2 * hc.SIDE["nacelle_g"]
    W = AUTH["weight_n"]
    a = AUTH["now"]["0.8"]
    auth, dem = a["pitch_authority_nm"], a["pitch_roll_demand_nm"]
    rows = []
    for s in (0.0, 0.5, 1.0, 5.0, 10.0, 20.0, 35.6):
        off = s * (1 - moved / m)                 # thrust centre minus COM, mm (both start at -12)
        trim_nm = W * off / 1000
        rows.append(dict(shift_mm=s, thrust_minus_com_mm=round(off, 2), trim_moment_nm=round(trim_nm, 3),
                         pitch_margin_80=round(auth / (dem + trim_nm), 2) if auth > trim_nm else 0.0))
    s_max = max(0.0, (auth / 2 - dem) / W * 1000 / (1 - moved / m))
    return dict(moved_mass_g=round(moved, 1), total_mass_g=m, pitch_authority_80_nm=auth, demand_nm=dem, rows=rows,
                max_shift_for_margin_2_mm=round(s_max, 2),
                to_reach_arm=dict(shift_needed_mm=35.6, battery_move_to_rebalance_mm=round(35.6 * (1 - moved / m) * m / (2 * hc.SIDE["batt_g"]), 0)))


def band(depths=(5.1, 6.0, 7.0, 8.0, 8.5, 9.0)):
    out = {}
    for d in depths:
        res = {}
        for case in CASES:
            L = hc.CASES[case]
            F, Mf = resultant(L["nac"] + L["tray"])
            worst = None
            for y, (z0, z1) in BAND.items():
                r = rect_raster(d, z0, z1)
                s = section_stress(r, (0, 2), EY, F, lambda c2, y=y: Mf(np.array([c2[0], y, c2[2]])), solid=True)
                tau = tau_rect(s["torsion"], d, z1 - z0)
                vm = float(np.hypot(s["sigma"], np.sqrt(3) * tau))
                sf = min(PLA["design_xy"] / max(s["sigma"], 1e-9), 0.55 * PLA["design_xy"] / max(tau, 1e-9), PLA["design_xy"] / vm)
                row = dict(y=y, sigma_MPa=round(s["sigma"], 1), tau_MPa=round(tau, 1), sf=round(sf, 2))
                if worst is None or sf < worst["sf"]:
                    worst = row
            res[case] = worst
        res["min_sf"] = min(v["sf"] for k, v in res.items() if isinstance(v, dict))
        res["added_g_per_side"] = round((d - 5.1) * 11.0 * 30.0 / 1000 * 1.24, 1)    # band y 20..31, about 30 mm tall
        out[f"{d:.1f} mm"] = res
    return out


def main():
    g, t, b = geometry(), trim(), band()
    blockers = [
        dict(what="rear pack (OpenRB enclosure) and its four post screws", at="x -45..-13, |y| < 27.6, z -44..39",
             kind="duck's own printed part with the servo board inside; the posts are the only hard points"),
        dict(what="A7Z saddle body", at="x -45..-5, |y| < 36.4, z 26.4..66.5", kind="duck's own printed part (reprintable); "
             "the 1.5 mm keep-out in front of it and its rear window (x -59..-44, z 47.8..58, |y| < 30) are design choices"),
        dict(what="trunk shells (side lip |y| <= 28, top lip x -46.1 at |y| < 18)", at="x up to 34.5, |y| < 36", kind="duck's own printed body"),
        dict(what="head sweep above the trunk", at="z > 66 (guide)", kind="physical: moving head (pickup scan, yaw)"),
        dict(what="hips and upper legs below the trunk", at="|y| 25..71, z < -7", kind="physical: moving legs"),
        dict(what="batteries on the trays", at="x -36..42, |y| 42.5..75.5, z 26..57", kind="bought parts on printed trays (both movable)"),
        dict(what="battery backpack front plate", at="x -50.5 (rear face of the band slot), |y| < 32, z -44..43",
             kind="printed backpack (reprintable); its position is a design choice"),
        dict(what="FC/ESC stack", at="x -102..-50.6, y -84..-35.5", kind="bought boards on a printed bracket (movable)"),
    ]
    res = dict(geometry=g, hover_trim=t, band_solid_rectangle=b, blockers=blockers)
    (OUT / "root_alignment.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(g, indent=1))
    print(json.dumps(t, indent=1))
    for d, r in b.items():
        print(d, r["min_sf"], {k: (v["sf"], v["y"], v["sigma_MPa"], v["tau_MPa"]) for k, v in r.items() if isinstance(v, dict)}, r["added_g_per_side"])


if __name__ == "__main__":
    main()
