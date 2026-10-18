"""Focused checks for the V1.9 BNO085 rib (the only body change from V1.8). Writes check_v19_imu.json.

1. new material (V1.9 body minus V1.8 body) against every final-pose part that is not the pack, its contents or retired;
2. board against the rib (contact face) and the two M2 x 4 (head on the PCB front, shank through the board hole into the pilot);
3. right hip link dxl-5-4 tube against the new material;
4. pack-in: the pack with the board and both screws already fitted slides in along the guide's pack-in approach, extended
   backwards until its box clears every obstacle box (the steps_audit lead-in rule), 0.5 mm steps, exact booleans.
"""
import sys, json
from pathlib import Path
import numpy as np
import trimesh
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'rear-pack'))
import pack_lib as P  # noqa: E402
import ia_lib  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

G = HERE.parent.parent
data = json.load(open(G / 'data' / 'guide-data.json'))
steps = {s['id']: s for s in data['steps']}
V19 = P.mesh_to_m(P.load_stl(HERE / 'rear_pack-world.stl'))
V18 = P.mesh_to_m(P.load_stl(HERE.parent / 'rear-pack' / 'rear_pack-world.stl'))
new = V19 - V18
gone = V18 - V19
imu_mesh = P.imu_mesh(); IMU = P.mesh_to_m(imu_mesh)
res = dict(newMaterialMm3=round(new.volume(), 2), removedMaterialMm3=round(gone.volume(), 2))

# 1. final-pose overlaps of the new material
present = set()
for s in data['steps']:
    present |= set(s.get('show', [])) | set(s.get('add', []))
present -= set(P.RETIRED) | set(P.SELF_KEYS)
man = ia_lib.manifest()
hits = []; gaps = {}
nb = np.array(new.bounding_box()).reshape(2, 3)
for k in sorted(present):
    if k not in man:
        continue
    lo, hi = np.array(man[k]['bounds'])
    if np.any(lo > nb[1] + 3) or np.any(hi < nb[0] - 3):
        continue
    S = P.solid_m(k)
    v = (new ^ S).volume()
    if v > 1e-3:
        hits.append((k, round(v, 3)))
    gaps[k] = round(float(new.min_gap(S, 5.0)), 3)
res['finalPose'] = dict(partsNear=len(gaps), overlaps=hits, nearestGaps=dict(sorted(gaps.items(), key=lambda t: t[1])[:6]))

# 2. board and screws
res['boardVsRib'] = dict(overlapMm3=round((IMU ^ V19).volume(), 4), gapMm=round(float(V19.min_gap(IMU, 5.0)), 4))
pcb_front = None
for (x, z) in ((-15.46, 8.04), (-15.46, 28.36)):
    o = np.array([x + 1.6, 5.0, z]); hit = imu_mesh.ray.intersects_location([o], [[0, -1, 0]])[0]
    ys = sorted(set(np.round(hit[:, 1], 3))) if len(hit) else []
    res.setdefault('boardSurfacesNearHole_y', {})[f'{x},{z}'] = ys
pcb_front = -2.265 + 1.6
screws = []
for (x, z) in ((-15.46, 8.04), (-15.46, 28.36)):
    head = P.cyl_y(2.0, pcb_front, pcb_front + 1.5, x, z)
    shank = P.cyl_y(1.0, pcb_front - 4.0, pcb_front, x, z)
    screws.append((head, shank))
    r = res.setdefault('screws', [])
    r.append(dict(at=[x, z], headVsBoardMm3=round((head ^ IMU).volume(), 4), shankVsBoardMm3=round((shank ^ IMU).volume(), 4),
                  shankInRibMm=round(-2.27 - (pcb_front - 4.0), 2), threadMm3=round((shank ^ V19).volume(), 3),
                  tipToRibBackMm=round((pcb_front - 4.0) - (-5.5), 2),
                  headEnv=[(k, round((head ^ P.solid_m(k)).volume(), 4)) for k in gaps if (head ^ P.solid_m(k)).volume() > 1e-3]))
SCR = P.union([h + s for h, s in screws])

# 3. dxl-5-4
cab = [c for c in data['cables'] if c['id'] == 'dxl-5-4'][0]
pts = np.array(cab['path'], float)
seg = []
for a, b in zip(pts[:-1], pts[1:]):
    n = max(2, int(np.ceil(np.linalg.norm(b - a) / 0.25)))
    seg.append(a + (b - a) * np.linspace(0, 1, n)[:, None])
cp = np.vstack(seg)
rib_pts = trimesh.sample.sample_surface(P.clean_mesh(new), 40000)[0]
d, _ = cKDTree(rib_pts).query(cp)
res['dxl54'] = dict(polylineSamples=len(cp), radius=cab['radius'], minSurfaceGapMm=round(float(d.min() - cab['radius']), 3),
                    note='distance from the drawn route polyline (control points, 0.25 mm resampled) to the new material surface, minus the tube radius')

# 4. pack-in sweep with the board and screws fitted
appr = np.array(steps['pack-in']['approach']['rear_pack'], float); u = appr / np.linalg.norm(appr)
moving = V19 + IMU + SCR
mb = np.array(moving.bounding_box()).reshape(2, 3)
obst = []
for k in sorted(set(steps['pack-in'].get('show', [])) - set(P.RETIRED) - set(P.SELF_KEYS)):
    if k in man:
        obst.append((k, P.solid_m(k), np.array(man[k]['bounds'])))
seated = {k: (moving ^ S).volume() for k, S, _ in obst}
hitlog = {}; t = 0.0; clear_at = None
while t <= 600.0:
    off = u * t; lo = mb[0] + off; hi = mb[1] + off
    near = [(k, S) for k, S, b in obst if np.all(lo <= b[1]) and np.all(hi >= b[0])]
    if not near and t > np.linalg.norm(appr):
        clear_at = t; break
    for k, S in near:
        v = (moving.translate(off.tolist()) ^ S).volume() - seated[k]
        if v > 0.5:
            hitlog.setdefault(k, []).append(round(t, 1))
    t += 0.5
res['packInSweep'] = dict(approach=appr.tolist(), obstacles=[k for k, _, _ in obst], seatedOverlapMm3={k: round(v, 3) for k, v in seated.items() if v > 1e-3},
                          clearAtMm=clear_at, hits={k: (v[0], v[-1], len(v)) for k, v in hitlog.items()})
json.dump(res, open(HERE / 'check_v19_imu.json', 'w'), indent=1)
print(json.dumps(res, indent=1))
