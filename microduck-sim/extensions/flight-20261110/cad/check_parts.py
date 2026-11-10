"""Checks of the built flight-pack parts (build_pack.py output). Guide frame, mm. Writes checks/check_parts.json.
    zsh cad/mini_sync.sh run 'cd cad && $PY check_parts.py'      (Mac mini; about 1-2 min)

1. Overlap volume and minimum gap of every printed part and bought-part dummy against the world parts at rest
   (guide/print/world, as built: battery backpack group moved +5.2 mm in x from the Dual Lock pose the world files hold,
   i.e. 3.5 mm behind today's no-plate pose), and against each other.
2. Gaps to the protected items: saddle (>= 1.5), backpack hatch, top plugs, side plug, power switch, A7Z USB-C plug and
   the saddle rear window.
3. Moving parts: minimum distance from every part to the cached pose clouds (pose_clouds.npz, from sweep_check.py's pose
   sets; stand-world = guide + 120 z), and the MTF-01 42 deg cone.
4. Wall thickness: inward ray length from surface samples; samples under 1.2 mm are listed with their positions.
Forward kinematics only, no simulation.
"""
import json
import sys
import time
from pathlib import Path
import numpy as np
import trimesh
import manifold3d as m3
from scipy.spatial import cKDTree

H = Path(__file__).resolve().parent
B = H / "build"
WORLD = H.parents[2] / "guide" / "print" / "world"
OUT = H / "checks"; OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(H))
import flight_params as Pm  # noqa: E402

T0 = time.time()
BACKPACK_SHIFT = 8.7 - 3.5     # world files hold the Dual Lock pose (-8.7); with the wing plate the pack sits 3.5 behind today's
BACKPACK = ("battery_backpack_frame.", "battery_backpack_cap.", "battery_backpack_bars.", "battery_hatch.", "bp_battery.",
            "bp_plugs.", "bp_plug2.", "bp_switch.", "bp_dfr1202.")
SKIP = {   # world files that are not on the robot as built, with the reason
    "rear_pack_cover": "replaced by the backpack front plate (no back plate fitted)",
    "duallock_plate": "not fitted (Shawn 2026-11-10)", "duallock_strips": "not fitted",
    "rear_frame": "retired V1.2x backpack", "rear_lid": "retired V1.2x backpack", "pd5991": "retired V1.2x backpack",
    "xl4015_left": "retired V1.2x backpack", "xl4015_right": "retired V1.2x backpack",
    "openrb-board": "retired flat OpenRB pose", "openrb_tray": "retired flat OpenRB pose",
    "saddle_lid": "not fitted (CURRENT-STATE parts_a7z_extensions: V1.35 saddle, '盖没有盖')",
}
PROTECT = {"saddle_body": 1.5, "saddle_lid": 1.5, "battery_hatch": 1.0, "bp_plugs": 2.0, "bp_plug2": 2.0, "bp_switch": 2.0,
           "bp_swap_plugs": 2.0, "sd_usb_c_plug": 2.0, "camera_cable_stub": 2.0}
SADDLE_WINDOW = dict(x=(-47.0, -44.0), y=(-30.0, 30.0), z=(47.8, 58.0))   # rear window of the saddle (keep clear behind it)

PARTS = ["wing_plate", "tray_L", "tray_R", "nacelle_inner_L", "nacelle_outer_L", "nacelle_inner_R", "nacelle_outer_R",
         "fc_bracket"]
DUMMIES = sorted(p.name[6:-10] for p in B.glob("dummy_*-world.stl"))
DESIGNED = {   # contacts by design (face contact or a bought part seated in its printed seat)
    ("wing_plate", "rear_pack"): "centre plate on the pack posts (face contact x -45)",
    ("wing_plate", "battery_backpack_frame"): "backpack front plate on the centre plate (face contact x -48.5)",
    ("tray_L", "wing_plate"): "flange on the arm web (face contact)", ("tray_R", "wing_plate"): "flange on the arm web",
    ("nacelle_inner_L", "wing_plate"): "lug on the arm web", ("nacelle_inner_R", "wing_plate"): "lug on the arm web",
    ("nacelle_inner_L", "nacelle_outer_L"): "split plane, 0.6 gap", ("nacelle_inner_R", "nacelle_outer_R"): "split plane",
    ("fc_bracket", "wing_plate"): "plate on the flange bosses",
    ("dummy:battery_L", "tray_L"): "pack on its deck", ("dummy:battery_R", "tray_R"): "pack on its deck",
    ("dummy:mtf01", "fc_bracket"): "under its shelf",
    ("dummy:battery_leads_L", "dummy:battery_L"): "leads leave the pack end", ("dummy:battery_leads_R", "dummy:battery_R"): "leads leave the pack end",
    ("wing_plate", "bp_swap_plugs"): "unchanged: plugs 3 + 4 stand 0.8 in front of the x -45 face today (backpack front plate)",
    ("dummy:fc_esc_stack", "fc_bracket"): "on its standoffs", ("dummy:esc_capacitor", "wing_plate"): "lies on the top flange",
    ("dummy:esc_capacitor", "fc_bracket"): "rests on the plate top edge",
    ("dummy:a7z_link", "sd_dupont_housings"): "the lead's Dupont housings are on the header (world block covers all 40 pins)",
    ("dummy:a7z_link", "saddle_body"): "lead lies on the right side wall top edge",
    ("dummy:a7z_link", "dummy:fc_esc_stack"): "lead ends in the UART1 plug",
}
EXISTING = {   # world-part relations the wing plate inherits unchanged from today's backpack front plate at x -45
    ("wing_plate", "bp_swap_plugs"),
}
RESTING = {    # a flexible lead (3 x 28 AWG, about 3 g) lying unattached on a protected part: no tie, no load path through it
    ("dummy:a7z_link", "saddle_body"),
}


def load(path, shift=None):
    m = trimesh.load(path, force="mesh")
    if shift is not None:
        m.apply_translation(shift)
    return m


def to_man(t):
    return m3.Manifold(m3.Mesh(vert_properties=np.asarray(t.vertices, np.float32), tri_verts=np.asarray(t.faces, np.uint32)))


def samples(t, spacing=0.5):
    n = int(min(400000, max(2000, t.area / spacing ** 2)))
    p, _ = trimesh.sample.sample_surface_even(t, n, seed=1)
    return np.vstack([p, t.vertices])


def pair(a, b, ta, tb, sa, sb):
    """overlap volume (mm3) and approximate minimum surface gap (mm) of two meshes."""
    lo = np.maximum(ta.bounds[0], tb.bounds[0]) - 6
    hi = np.minimum(ta.bounds[1], tb.bounds[1]) + 6
    if np.any(lo > hi):
        return None
    try:
        v = float((a ^ b).volume()) if a is not None and b is not None else None
    except Exception:
        v = None
    pa = sa[np.all((sa >= lo) & (sa <= hi), axis=1)]
    pb = sb[np.all((sb >= lo) & (sb <= hi), axis=1)]
    if len(pa) == 0 or len(pb) == 0:
        return None
    d, i = cKDTree(pb).query(pa, k=1)
    k = int(np.argmin(d))
    return dict(overlap_mm3=None if v is None else round(v, 2), min_gap_mm=round(float(d[k]), 2),
                at=np.round(pa[k], 1).tolist())


def thickness(t, n=8000, edge_skip=0.6):
    """Inward ray length from surface samples. Samples within edge_skip of a sharp edge (> 40 deg) are skipped: a ray
    started next to an edge leaves through the neighbouring face and reads the distance to the edge, not a wall."""
    p, fi = trimesh.sample.sample_surface_even(t, n, seed=2)
    sharp = t.face_adjacency_edges[t.face_adjacency_angles > np.radians(40)]
    if len(sharp):
        a, b = t.vertices[sharp[:, 0]], t.vertices[sharp[:, 1]]
        k = np.ceil(np.linalg.norm(b - a, axis=1) / 0.2).astype(int) + 1
        ep = np.vstack([a[i] + (b[i] - a[i]) * np.linspace(0, 1, k[i])[:, None] for i in range(len(a))])
        de, _ = cKDTree(ep).query(p, k=1)
        keep = de > edge_skip
        p, fi = p[keep], fi[keep]
    nrm = t.face_normals[fi]
    o = p - nrm * 0.02
    loc, ri, _ = t.ray.intersects_location(o, -nrm, multiple_hits=True)
    d = np.full(len(p), np.inf)
    if len(loc):
        dist = np.linalg.norm(loc - o[ri], axis=1)
        ok = dist > 0.05
        np.minimum.at(d, ri[ok], dist[ok] + 0.02)
    thin = np.isfinite(d) & (d < 1.2)
    return dict(min_mm=round(float(d[np.isfinite(d)].min()), 2), p1_mm=round(float(np.percentile(d[np.isfinite(d)], 1)), 2),
                n_under_1_2=int(thin.sum()), n=int(len(p)),
                thin_at=np.round(p[thin][:12], 1).tolist(), thin_d=np.round(d[thin][:12], 2).tolist())


def main():
    res = dict(backpack_shift_mm=BACKPACK_SHIFT, skipped=SKIP)
    world = {}
    for f in sorted(WORLD.glob("*.stl")):
        stem = f.stem
        if any(stem.startswith(k) for k in SKIP) or "-v1" in stem or "_v18" in stem or "-2026" in stem or stem.startswith("a7z_"):
            continue
        shift = [BACKPACK_SHIFT, 0, 0] if f.name.startswith(BACKPACK) else None
        world[stem] = load(f, shift)
    mine = {n: load(B / f"{n}-world.stl") for n in PARTS}
    mine.update({f"dummy:{n}": load(B / f"dummy_{n}-world.stl") for n in DUMMIES})
    lo = np.min([m.bounds[0] for m in mine.values()], axis=0) - 10
    hi = np.max([m.bounds[1] for m in mine.values()], axis=0) + 10
    world = {k: m for k, m in world.items() if not (np.any(m.bounds[1] < lo) or np.any(m.bounds[0] > hi))}
    man = {k: (to_man(m) if m.is_watertight else None) for k, m in list(world.items()) + list(mine.items())}
    smp = {k: samples(m) for k, m in list(world.items()) + list(mine.items())}
    print(f"loaded {len(world)} world parts near the pack, {len(mine)} own; {time.time() - T0:.0f} s", flush=True)

    # 1+2: own vs world, own vs own
    fit, issues = {}, []
    keys = list(mine)
    for a in keys:
        fit[a] = {}
        others = list(world) + [k for k in keys if k != a]
        for b in others:
            r = pair(man[a], man[b], mine[a], world[b] if b in world else mine[b], smp[a], smp[b])
            if r is None:
                continue
            designed = DESIGNED.get((a, b)) or DESIGNED.get((b, a))
            r["designed"] = designed
            if r["min_gap_mm"] < 3.0 or (r["overlap_mm3"] or 0) > 0.01:
                fit[a][b] = r
                need = 0.0 if (a, b) in EXISTING or (a, b) in RESTING else PROTECT.get(b, 0.0)
                bad = ((r["overlap_mm3"] or 0) > 0.05 and not designed) or (need and r["min_gap_mm"] < need) or \
                      (r["overlap_mm3"] is None and r["min_gap_mm"] < 0.3 and not designed)
                if bad:
                    issues.append(f"{a} vs {b}: overlap {r['overlap_mm3']} mm3, gap {r['min_gap_mm']} at {r['at']}"
                                  + (f" (needs >= {need})" if need else ""))
    res["fit"] = fit
    # saddle rear window: nothing of ours inside the box behind it
    win_lo = np.array([SADDLE_WINDOW[a][0] for a in "xyz"]) - np.array([12.0, 0, 0])
    win_hi = np.array([SADDLE_WINDOW[a][1] for a in "xyz"])
    res["saddle_window_hits"] = {k: int(np.all((s >= win_lo) & (s <= win_hi), axis=1).sum()) for k, s in smp.items() if k in mine}
    for k, n in res["saddle_window_hits"].items():
        if n:
            issues.append(f"{k}: {n} surface samples in the saddle rear window zone")
    print(f"fit done {time.time() - T0:.0f} s", flush=True)

    # 3: pose clouds (stand-world)
    pc = np.load(H / "build" / "pose_clouds.npz")
    names = list(pc["names"])
    clouds = {n: pc[f"s{i}"] for i, n in enumerate(names)}
    moving = {}
    for a, m in mine.items():
        sa = smp[a] + np.array([0, 0, 120.0])
        tree = cKDTree(sa)
        lo_, hi_ = sa.min(0) - 20, sa.max(0) + 20
        row = {}
        for n, P in clouds.items():
            q = P[np.all((P >= lo_) & (P <= hi_), axis=1)]
            if len(q) == 0:
                row[n] = None; continue
            d, _ = tree.query(q, k=1)
            near = q[d < 2.0]
            inside = int(m.contains(near[:20000] - np.array([0, 0, 120.0])).sum()) if len(near) else 0
            k = int(np.argmin(d))
            row[n] = dict(min_mm=round(float(d[k]), 2), inside_pts=inside, at_guide=np.round(q[k] - [0, 0, 120.0], 1).tolist())
        moving[a] = row
    res["moving"] = moving
    # MTF-01 cone: apex at the lens (module underside centre), axis -z, half angle 21 deg, down to the ground (guide z -120)
    mtf = mine["dummy:mtf01"]
    apex = np.array([(mtf.bounds[0][0] + mtf.bounds[1][0]) / 2, (mtf.bounds[0][1] + mtf.bounds[1][1]) / 2, mtf.bounds[0][2]])
    tan = np.tan(np.radians(Pm.MTF01["cone_half_deg"]))

    def in_cone(P):
        dz = apex[2] - P[:, 2]
        r = np.linalg.norm(P[:, :2] - apex[:2], axis=1)
        return (dz > 0.5) & (r < dz * tan) & (P[:, 2] > -120.0)
    cone = {}
    for n, P in clouds.items():
        cone[n] = int(in_cone(P - np.array([0, 0, 120.0])).sum())
    for k, s in smp.items():
        if k != "dummy:mtf01":
            c = int(in_cone(s).sum())
            if c:
                cone[k] = c
    res["mtf_cone"] = dict(apex_guide=np.round(apex, 1).tolist(), hits=cone)
    print(f"moving done {time.time() - T0:.0f} s", flush=True)

    # 4: wall thickness of the printed parts
    res["thickness"] = {n: thickness(mine[n]) for n in PARTS}
    res["issues"] = issues
    res["seconds"] = round(time.time() - T0, 1)
    (OUT / "check_parts.json").write_text(json.dumps(res, indent=1))
    for a, row in fit.items():
        for b, r in row.items():
            print(f"  {a:24s} {b:26s} overlap {r['overlap_mm3']!s:>8}  gap {r['min_gap_mm']:6.2f}  {r['designed'] or ''}")
    print("moving (min mm to pose clouds, inside pts):")
    for a, row in moving.items():
        worst = sorted(((v["min_mm"], n, v["inside_pts"]) for n, v in row.items() if v), key=lambda x: x[0])[:2]
        print(f"  {a:24s} " + "; ".join(f"{n[:40]} {d} ({i})" for d, n, i in worst))
    print("mtf cone:", res["mtf_cone"])
    for n, t in res["thickness"].items():
        print(f"  thickness {n:18s} min {t['min_mm']} p1 {t['p1_mm']} under1.2 {t['n_under_1_2']}/{t['n']}")
    print("ISSUES:" if issues else "no issues", *issues, sep="\n  ")
    print(f"{res['seconds']} s")


if __name__ == "__main__":
    main()
