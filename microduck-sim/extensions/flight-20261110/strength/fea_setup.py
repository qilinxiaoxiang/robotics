"""Write out/fea_inputs.json (supports, load patches, regions) for fea_run.py from the same load cases as hand_calcs.py,
and copy the part STLs into out/geometry/ for the Mac mini mirror.
    /tmp/microduck-cad-venv/bin/python strength/fea_setup.py
"""
import hashlib
import json
import shutil

import numpy as np

import hand_calcs as hc
from common import BUILD, OUT, M2_PRELOAD, Pm, snapshot, thrust_dir

GEO = OUT / "geometry"
GEO.mkdir(exist_ok=True)


def J(v):
    return np.round(np.asarray(v, float), 4).tolist()


def mirror(loads):
    return [(np.asarray(f) * [1, -1, 1], np.asarray(p) * [1, -1, 1]) for f, p in loads]


def flist(loads):
    return [[J(f), J(p)] for f, p in loads]


def stl(name):
    src = BUILD / f"{name}-world.stl"
    shutil.copy(src, GEO / src.name)
    return f"out/geometry/{src.name}", hashlib.sha256(src.read_bytes()).hexdigest()[:16]


def wing_model():
    path, sha = stl("wing_plate")
    fixed = []
    for (y, z) in hc.POSTS:
        fixed.append(dict(box=dict(x=[-45.35, -44.65], y=[y - 3.0, y + 3.0], z=[z - 3.0, z + 3.0]), normal=[1, 0, 0]))
        fixed.append(dict(cyl=[[-47.0, y, z], [1, 0, 0], [1.0, 1.5]], box=dict(x=[-48.6, -44.9], y=[y - 2, y + 2], z=[z - 2, z + 2])))

    def patches(side, L):
        s = 1 if side > 0 else -1
        lug = dict(name=f"lug_{'L' if s > 0 else 'R'}", sel=dict(box=dict(x=[-45.35, -44.65], y=sorted([s * 70.0, s * 82.0]), z=[37.0, 58.5]),
                                                                normal=[1, 0, 0]), normal=[1, 0, 0])
        tray = dict(name=f"tray_{'L' if s > 0 else 'R'}", sel=dict(box=dict(x=[-45.35, -44.65], y=sorted([s * 37.9, s * 69.5]), z=[22.0, 36.0]),
                                                                  normal=[1, 0, 0]), normal=[1, 0, 0])
        nac, tr = (L["nac"], L["tray"]) if s > 0 else (mirror(L["nac"]), mirror(L["tray"]))
        out = []
        if nac:
            out.append(dict(lug, forces=flist(nac)))
        if tr:
            out.append(dict(tray, forces=flist(tr)))
        return out
    cases = {}
    both = ("thrust_1.5x_on_ground", "vertical_impact_15.6g", "fore_aft_10g", "lateral_10g")
    for cname, L in hc.CASES.items():
        ps = patches(+1, L)
        if cname in both:
            ps += patches(-1, L) if cname != "lateral_10g" else patches(-1, dict(nac=[(f * [1, 1, 1], p * [1, -1, 1]) for f, p in L["nac"]],
                                                                                    tray=[(f, p * [1, -1, 1]) for f, p in L["tray"]]))
        cases[cname] = ps
    return dict(stl=path, stl_sha256=sha, fixed=fixed, cases=cases, exclude_mm=2.0, grid_origin=[-45.0, 0.0, 0.0],
                regions=dict(band_L=dict(y=[19.0, 31.0]), column_L=dict(y=[31.0, 38.0]), arm_L=dict(y=[38.0, 80.0]),
                             band_R=dict(y=[-31.0, -19.0]), centre=dict(y=[-18.6, 18.6])),
                probes=dict(lug_L=[-45.0, 76.0, 48.0], tray_L=[-45.0, 50.0, 31.0]), views=[[20, -50], [20, 140]],
                sections=[dict(axis="y", at=[21.0, 25.0, 29.0, 31.0, 35.0, 45.0, 60.0])])


def nacelle_inner_model():
    path, sha = stl("nacelle_inner_L")
    fixed = [dict(box=dict(x=[-45.35, -44.65], y=[69.9, 82.1], z=[37.0, 58.5]), normal=[-1, 0, 0])]
    bore_r = Pm.NAC["bore"] / 2

    def bore(which):
        a0 = Pm.fan_point(which, 0.0)
        return dict(cyl=[J(a0), J(thrust_dir(which)), [bore_r - 0.7, bore_r + 0.7]],
                    box=dict(z=[Pm.LIP_Z - Pm.NAC["t1"] * Pm.C - 2, Pm.LIP_Z - Pm.NAC["t0"] * Pm.C + 2]))

    def bore_load(which, F):
        return dict(name=f"bore_{which}", sel=bore(which), t_resultant=J(F))
    cases = {}
    T = hc.PEAK * hc.THRUST_N
    m_fan = hc.SIDE["fan_g"] / 1000 * hc.G
    cases["thrust_1.5x_on_ground"] = [bore_load(w, T * thrust_dir(w) - m_fan * np.array([0, 0, 1])) for w in ("front", "rear")]
    cases["vertical_impact_15.6g"] = [bore_load(w, -m_fan * hc.IMPACT_G * np.array([0, 0, 1])) for w in ("front", "rear")]
    cases["handling_lift_by_nacelle"] = [bore_load("front", hc.HANDLING_N * np.array([0, 0, 1]))]
    cases["topple_strike_front_end"] = [dict(name="front_end", sel=dict(box=dict(x=[62.0, 70.0]), normal=[1, 0, 0], cos=0.8),
                                             normal=[1, 0, 0], F=J(-hc.TOPPLE_N * np.array([1, 0, 0])), M=[0, 0, 0])]
    cases["unit_front_end_minus_x"] = [dict(name="front_end", sel=dict(box=dict(x=[62.0, 70.0]), normal=[1, 0, 0], cos=0.8),
                                            normal=[1, 0, 0], F=[-10.0, 0, 0], M=[0, 0, 0])]
    return dict(stl=path, stl_sha256=sha, fixed=fixed, cases=cases, exclude_mm=2.0, grid_origin=[-45.0, 108.5, 37.63],
                regions=dict(lug_root=dict(x=[-46.0, -30.0], y=[69.0, 92.0]), rear_collar=dict(x=[-80.0, -30.0], y=[92.0, 109.0]),
                             middle_web=dict(x=[-21.0, -3.0]), front_collar=dict(x=[-10.0, 52.0]), front_block=dict(x=[52.0, 66.0]),
                             skirts_lead_slots=dict(z=[37.0, 42.0])),
                probes=dict(front_end=[64.0, 104.0, 50.0], front_fan_centre_wall=[21.9, 84.0, 53.0]), views=[[25, -60], [25, 120]],
                sections=[dict(axis="x", at=[-36.0, -25.0, -12.0, 0.0, 10.0]),
                          dict(axis="y", at=[80.5], box=dict(x=[-45.0, -30.8], z=[30.0, 70.0]))])


def nacelle_outer_preload_model():
    path, sha = stl("nacelle_outer_L")
    bore_r = Pm.NAC["bore"] / 2
    wsel = [dict(cyl=[J(Pm.fan_point(w, 0.0)), J(thrust_dir(w)), [bore_r - 0.7, bore_r + 0.7]]) for w in ("front", "rear")]
    hs = Pm.NAC["head_seat"][0] / 2
    y_floor = Pm.FAN_Y + Pm.NAC["split_gap"] / 2 + Pm.NAC["under_head"]
    cases = {}
    for lab, P in (("preload_snug", M2_PRELOAD["snug"]), ("preload_to_strip_260N", hc.M2_PULLOUT["high"])):
        ps = []
        for k, (x, z) in enumerate(hc.BJ["nacelle"]["holes_xz"]):
            ps.append(dict(name=f"seat_{k}", sel=dict(box=dict(x=[x - hs - 0.1, x + hs + 0.1], y=[y_floor - 0.35, y_floor + 0.35],
                                                                 z=[z - hs - 0.1, z + hs + 0.1]), normal=[0, 1, 0]),
                           normal=[0, 1, 0], F=[0.0, -P, 0.0], M=[0, 0, 0]))
        cases[lab] = ps
    return dict(stl=path, stl_sha256=sha, fixed=[], grid_origin=[-45.0, y_floor, 37.63], winkler=dict(sel=wsel, k=3.0, kt=0.01), cases=cases, exclude_mm=1.5,
                regions=dict(front_collar=dict(x=[-8.0, 50.0]), rear_collar=dict(x=[-74.0, -18.0]), front_block=dict(x=[50.0, 66.0]),
                             rear_block=dict(x=[-90.0, -74.0]), middle_web=dict(x=[-20.0, -4.0])),
                probes=dict(front_crown=[Pm.fan_point("front", 18.0)[0], 110 + bore_r, Pm.fan_point("front", 18.0)[2]]),
                views=[[25, -60], [25, 120]])


# Proposed root fix, analysed only (cad/ is not edited): per side
#  - band raised: x -50.2..-46.8, |y| 20.3..30.0, z 28..42.5 (the free slot left by the removed cross channel; same limits as
#    the transition: under z 45, 1.5 mm behind the saddle zone, in front of the backpack at x -50.5)
#  - corner filled: x -46.8..-45, |y| 28.2..30.0, z -1..24.9 (the band's lower front lip and the column's front lip met only
#    along one edge at y 28.5, z 9; outboard of the shell side lip |y| <= 28, inboard of the leg reach |y| >= 30)
ROOT_FIX = [((-50.2, 20.3, 28.0), (-46.8, 30.0, 42.5)), ((-46.8, 28.2, -1.0), (-45.0, 30.0, 24.9))]


def wing_fix_model(base):
    import manifold3d as m3
    import trimesh
    w = trimesh.load(BUILD / "wing_plate-world.stl", force="mesh")
    man = m3.Manifold(m3.Mesh(vert_properties=np.asarray(w.vertices, np.float32), tri_verts=np.asarray(w.faces, np.uint32)))
    for s in (1, -1):
        for lo, hi in ROOT_FIX:
            y0, y1 = sorted((s * lo[1], s * hi[1]))
            b = m3.Manifold.cube([hi[0] - lo[0], y1 - y0, hi[2] - lo[2]]).translate([lo[0], y0, lo[2]])
            man = man + b
    mm = man.to_mesh()
    out = trimesh.Trimesh(mm.vert_properties[:, :3], mm.tri_verts)
    dst = GEO / "wing_plate_rootfix-world.stl"
    out.export(dst)
    added = (man.volume() - w.volume) / 1000
    cfg = json.loads(json.dumps(base))
    cfg["stl"] = f"out/geometry/{dst.name}"
    cfg["stl_sha256"] = hashlib.sha256(dst.read_bytes()).hexdigest()[:16]
    cfg["added_cm3"] = round(added, 3)
    cfg["cases"] = {k: v for k, v in cfg["cases"].items() if k in ("fore_aft_10g", "lateral_10g", "vertical_impact_15.6g",
                                                                    "topple_strike_front_end", "handling_lift_by_nacelle")}
    return cfg


def main():
    cfg = dict(wing=wing_model(), nacelle_inner=nacelle_inner_model(), nacelle_outer_preload=nacelle_outer_preload_model())
    cfg["wing_fix"] = wing_fix_model(cfg["wing"])
    # bore loads: uniform traction = resultant / bore area (computed on the mini from the selected facets)
    (OUT / "fea_inputs.json").write_text(json.dumps(dict(cfg, geometry=snapshot()), indent=1))
    print("wrote", OUT / "fea_inputs.json")


if __name__ == "__main__":
    main()
