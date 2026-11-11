"""Which random poses put leg or head points into the wing plate, their joint values, the body that does it, and whether
the same pose already puts that body into the duck's own trunk-fixed parts (guide/print/world, as built). Read-only.
Mac mini (about 2 min):  zsh cad/mini_sync.sh run '$RUN --max-mib 3000 --seconds 600 -- $PY cad/pose_culprits.py'
Writes checks/pose_culprits.json.
"""
import json, sys
from pathlib import Path
import numpy as np, trimesh

H = Path(__file__).resolve().parents[1]
src = (H / "sweep_check.py").read_text().split("ONLY = sys.argv[2]")[0]
src = src.replace("    return q\n\n# pose sets", "    QLOG.append(q); return q\n\n# pose sets")
g = dict(__file__=str(H / "sweep_check.py"), __name__="sc", QLOG=[])
sys.argv = ["sweep_check.py", "600"]
exec(compile(src, "sweep_check.py", "exec"), g)
QLOG, sets, setq, local, names, LEG, HEAD, d, m = (g[k] for k in ("QLOG", "sets", "setq", "local", "names", "LEG", "HEAD", "d", "m"))
hinge, q0 = g["hinge"], g["q0"]
N = 600
wing = trimesh.load(H / "cad/build/wing_plate-world.stl", force="mesh")
W = H.parents[1] / "guide/print/world"
SKIP = ("rear_pack_cover", "duallock", "rear_frame", "rear_lid", "pd5991", "xl4015", "openrb-board", "openrb_tray", "saddle_lid",
        "ankle", "leg", "hip", "knee", "foot", "thigh", "shin", "head", "neck", "jaw", "beak", "eye", "cam", "touch")
BP = ("battery_backpack_frame.", "battery_backpack_cap.", "battery_backpack_bars.", "battery_hatch.", "bp_battery.", "bp_plugs.",
      "bp_plug2.", "bp_switch.", "bp_dfr1202.")
world = {}
for f in sorted(W.glob("*.stl")):
    if any(s in f.stem for s in SKIP) or "-v" in f.stem:
        continue
    mm = trimesh.load(f, force="mesh")
    if f.name.startswith(BP):
        mm.apply_translation([1.8, 0, 0])
    if mm.is_watertight:
        world[f.stem] = mm


def body_pts(b):
    return (local[b] @ d.xmat[b].reshape(3, 3).T + d.xpos[b]) * 1000.0 - np.array([0, 0, 120.0])


def depth(mesh, P):
    lo, hi = mesh.bounds[0] - 3, mesh.bounds[1] + 3
    k = np.all((P >= lo) & (P <= hi), axis=1)
    if not k.any():
        return None
    Q = P[k]
    _, dist, _ = trimesh.proximity.closest_point(mesh, Q)
    sd = np.where(mesh.contains(Q), -dist, dist)
    return float(sd.min())


out = {}
for label, off, bodies, box in (("legs random 50", 0, LEG, ([-56, -26, -48], [-40, 26, -28])),
                                ("head random 50", N, HEAD, ([-75, -80, 40], [-40, 80, 75]))):
    lo, hi = np.array(box[0]), np.array(box[1])
    rows = []
    for i in range(N):
        q = QLOG[off + i]
        setq(q)
        for b in bodies:
            P = body_pts(b)
            P = P[np.all((P >= lo) & (P <= hi), axis=1)]
            if not len(P):
                continue
            sw = depth(wing, P)
            if sw is not None and sw < 1.0:
                rows.append((sw, i, b))
    rows.sort()
    res = []
    for sw, i, b in rows[:8]:
        q = QLOG[off + i]
        setq(q)
        P = body_pts(b)
        own = {}
        for k, mm in world.items():
            v = depth(mm, P)
            if v is not None and v < 0.5:
                own[k] = round(v, 2)
        frac = {}
        for k, v in q.items():
            j = hinge[k]; lo_, hi_ = m.jnt_range[j]; c = q0[m.jnt_qposadr[j]]
            frac[k] = [round(float(v), 3), round(float(lo_), 2), round(float(hi_), 2), round(float(c), 2)]
        res.append(dict(pose=i, body=names[b], wing_signed_mm=round(sw, 2), own_parts_within_0p5=own, q_value_lo_hi_stand=frac))
    out[label] = dict(n_poses_under_1mm=len({i for _, i, _ in rows}), worst=res)
    print(label, out[label]["n_poses_under_1mm"], flush=True)
    for r in res:
        print(json.dumps(r))
(H / "cad/checks/pose_culprits.json").write_text(json.dumps(out, indent=1))
