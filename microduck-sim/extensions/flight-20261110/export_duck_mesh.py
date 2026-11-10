"""Export the as-built MicroDuck visual model (standing keyframe, world frame, metres) as merged per-colour meshes.

  microduck_rl/.venv/bin/python export_duck_mesh.py   -> duck_mesh.json (base64 float32 positions + uint32 indices)
"""
import base64, json
from pathlib import Path
import mujoco, numpy as np

HERE = Path(__file__).resolve().parent
SCENE = HERE.parents[1] / "microduck_rl/cmu/model/scenes/scene_battery-20261104.xml"
m = mujoco.MjModel.from_xml_path(str(SCENE)); d = mujoco.MjData(m)
mujoco.mj_resetDataKeyframe(m, d, 1); mujoco.mj_forward(m, d)
try:
    import fast_simplification
except Exception:
    fast_simplification = None
groups, bbox = {}, {}
for g in range(m.ngeom):
    if m.geom_type[g] != mujoco.mjtGeom.mjGEOM_MESH or m.geom_group[g] != 2:
        continue
    mid = m.geom_dataid[g]
    v = m.mesh_vert[m.mesh_vertadr[mid]:m.mesh_vertadr[mid] + m.mesh_vertnum[mid]].astype(np.float64)
    f = m.mesh_face[m.mesh_faceadr[mid]:m.mesh_faceadr[mid] + m.mesh_facenum[mid]].astype(np.int64)
    if fast_simplification is not None and len(f) > 3000:
        v, f = fast_simplification.simplify(v.astype(np.float32), f.astype(np.int32), target_reduction=1 - max(0.25, 3000 / len(f)))
    w = v @ d.geom_xmat[g].reshape(3, 3).T + d.geom_xpos[g]
    key = tuple(round(float(c), 3) for c in m.geom_rgba[g][:3])
    grp = groups.setdefault(key, {"v": [], "f": [], "n": 0})
    grp["v"].append(w); grp["f"].append(f + grp["n"]); grp["n"] += len(w)
    body = m.body(m.geom_bodyid[g]).name
    lo, hi = bbox.get(body, (np.full(3, 9.0), np.full(3, -9.0)))
    bbox[body] = (np.minimum(lo, w.min(0)), np.maximum(hi, w.max(0)))
out = {"groups": [], "bbox_mm": {}}
faces = 0
for key, grp in groups.items():
    v = np.concatenate(grp["v"]).astype(np.float32); f = np.concatenate(grp["f"]).astype(np.uint32); faces += len(f)
    out["groups"].append({"color": key, "pos": base64.b64encode(v.tobytes()).decode(), "idx": base64.b64encode(f.tobytes()).decode()})
for b, (lo, hi) in bbox.items():
    out["bbox_mm"][b] = [[round(float(x) * 1000, 1) for x in lo], [round(float(x) * 1000, 1) for x in hi]]
    print(b, out["bbox_mm"][b])
root = m.body("trunk_base").id
out["com_mm"] = [round(float(x) * 1000, 1) for x in d.subtree_com[root]]
out["mass_g"] = round(float(sum(m.body_mass)) * 1000, 1)
print("faces", faces, "com", out["com_mm"], "mass", out["mass_g"], "decimated", fast_simplification is not None)
(HERE / "duck_mesh.json").write_text(json.dumps(out))
print("bytes", (HERE / "duck_mesh.json").stat().st_size)
