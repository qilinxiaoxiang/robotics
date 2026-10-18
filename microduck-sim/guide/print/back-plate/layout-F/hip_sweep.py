"""Layout F hip-swing sweep (2026-10-14): minimum clearance of the rear box (frame, lid), the USB-C plug envelope and
every wire (all segments, capsule chains) to every leg geom while each hip pitch swings over HOME +-30 deg (no walk61 joint range is
recorded in the repository, so the coordinator's fallback range is used) combined with hip roll HOME +-10 deg; the
other joints stay at HOME. STAND moves only the ankles and the neck/head, so it is covered by the same sweep.

Model: the as-built MuJoCo scene (evaluate_delay.MODEL_DIR/scene.xml) with the box parts added to trunk_base, as
render_scene.py does. Distances come from mujoco.mj_geomDistance, which treats every mesh as its convex hull: the
frame's hull covers the box, and each leg mesh hull covers its link, so the reported minimum is a lower bound of the
true gap. Wires are chains of 0.9 mm capsules (wire radius) along every third point of wires_F.json.

    ~/.venvs/microduck-dyn/bin/python hip_sweep.py      (writes hip_sweep.json)"""
import sys, json, itertools
from pathlib import Path
import numpy as np, mujoco
HERE = Path(__file__).resolve().parent
REAL = Path('/Users/xiangzheng/code/robotics/microduck-sim/hardware-design-20260912/whole-robot-20260912/dynamics/realgap-20261014')
sys.path.insert(0, str(REAL))
from static_gap import NAMES, HOME, setup
import evaluate_delay as ev
mm = 0.001
PLUG = ([-57.0, 15.05, -30.66], [-49.5, 40.05, -17.66])        # real world: USB-C exits +y (layout F mirrored for the XL4015 handedness)
spec = mujoco.MjSpec.from_file(str(ev.MODEL_DIR / 'scene.xml')); trunk = spec.body('trunk_base')
for g in list(spec.geoms):
    if g.name in ('power_support', 'np_f970'):
        spec.delete(g)
for tag, f in (('frame', 'frame_F-world.stl'), ('lid', 'lid_F-world.stl')):
    a = spec.add_mesh(name=f'm_{tag}', file=str(HERE / f), scale=[mm] * 3)
    trunk.add_geom(name=f'box_{tag}', type=mujoco.mjtGeom.mjGEOM_MESH, meshname=a.name, contype=0, conaffinity=0, mass=0)
lo, hi = np.array(PLUG[0]), np.array(PLUG[1])
trunk.add_geom(name='usbc_plug', type=mujoco.mjtGeom.mjGEOM_BOX, pos=(lo + hi) / 2 * mm, size=(hi - lo) / 2 * mm, contype=0, conaffinity=0, mass=0)
W = json.loads((HERE / 'wires_F.json').read_text()); loops = {}
for k, v in W.items():
    p = np.array(v['points'])                           # every segment of every wire (outside routes since 2026-10-14)
    seg = np.vstack([p[::3], p[-1:]])
    names = []
    for i in range(len(seg) - 1):
        if np.linalg.norm(seg[i + 1] - seg[i]) < 1e-3:
            continue
        n = f'loop_{k}_{i}'; names.append(n)
        trunk.add_geom(name=n, type=mujoco.mjtGeom.mjGEOM_CAPSULE, fromto=np.r_[seg[i] * mm, seg[i + 1] * mm], size=[0.9 * mm, 0, 0], contype=0, conaffinity=0, mass=0)
    loops[k] = names
m = spec.compile(); d = mujoco.MjData(m)


def subtree(body):
    out = {body}; ch = True
    while ch:
        ch = False
        for b in range(m.nbody):
            if m.body_parentid[b] in out and b not in out:
                out.add(b); ch = True
    return out


legs = {}
for side in ('left', 'right'):
    bodies = subtree(m.jnt_bodyid[m.joint(f'{side}_hip_yaw').id])
    legs[side] = [g for g in range(m.ngeom) if m.geom_bodyid[g] in bodies]
targets = {'frame': [m.geom('box_frame').id], 'lid': [m.geom('box_lid').id], 'usbc_plug': [m.geom('usbc_plug').id]}
targets.update({f'wire {k}': [m.geom(n).id for n in v] for k, v in loops.items()})
gname = lambda g: m.geom(g).name or f'{m.body(m.geom_bodyid[g]).name}#geom{g}'
DMAX = 0.05
PITCH = np.radians(np.arange(-30, 30.1, 5.0)); ROLL = np.radians(np.arange(-10, 10.1, 5.0))
res = {t: dict(minMm=1e9) for t in targets}; home = {}; near = []
for side in ('left', 'right'):
    for dp, dr in [(0.0, 0.0)] + list(itertools.product(PITCH, ROLL)):
        pose = dict(HOME); pose[f'{side}_hip_pitch'] = HOME[f'{side}_hip_pitch'] + dp; pose[f'{side}_hip_roll'] = HOME[f'{side}_hip_roll'] + dr
        setup(m, d, NAMES, pose)
        for t, gs in targets.items():
            best = (1e9, None)
            for a in gs:
                for b in legs[side]:
                    dist = mujoco.mj_geomDistance(m, d, a, b, DMAX, None)
                    if dist < best[0]:
                        best = (dist, b)
            dmm = best[0] / mm
            if dmm < 5.0 and t in ('frame', 'lid', 'usbc_plug'):
                near.append((side, float(dp), float(dr), t))
            if dp == 0 and dr == 0:
                home[f'{t} | {side} leg'] = dict(minMm=round(dmm, 2), legGeom=gname(best[1]))
            if dmm < res[t]['minMm']:
                res[t] = dict(minMm=round(dmm, 2), legGeom=gname(best[1]), side=side,
                              hipPitchDeltaDeg=round(float(np.degrees(dp)), 1), hipRollDeltaDeg=round(float(np.degrees(dr)), 1))
# ---- refinement where the convex-hull distance is under 5 mm: sampled true surfaces (frame and cap STLs, plug box, leg meshes),
# nearest-neighbour distance between 0.25 mm surface samples (error under about 0.2 mm)
import trimesh
from scipy.spatial import cKDTree
def samples(tm, spacing=0.25):
    n = int(tm.area / spacing ** 2) + 100
    p, _ = trimesh.sample.sample_surface(tm, n, seed=1); return np.vstack([p, tm.vertices])
FR = trimesh.load(str(HERE / 'frame_F-world.stl'), force='mesh'); CP = trimesh.load(str(HERE / 'lid_F-world.stl'), force='mesh')
TGT = {'frame': cKDTree(samples(FR)), 'lid': cKDTree(samples(CP)), 'usbc_plug': cKDTree(samples(trimesh.creation.box(bounds=[lo, hi])))}
BOX = {'frame': FR.bounds, 'lid': CP.bounds, 'usbc_plug': np.array([lo, hi])}                 # leg samples outside the target box + 6 mm cannot be nearer
LEGS = {}
for side in ('left', 'right'):
    for g in legs[side]:
        if m.geom_type[g] != mujoco.mjtGeom.mjGEOM_MESH:
            continue
        mid = m.geom_dataid[g]; a, nv = m.mesh_vertadr[mid], m.mesh_vertnum[mid]; fa, nf = m.mesh_faceadr[mid], m.mesh_facenum[mid]
        tm = trimesh.Trimesh(m.mesh_vert[a:a + nv] / mm, m.mesh_face[fa:fa + nf], process=False)
        LEGS[g] = samples(tm, 0.4)
tb = m.body('trunk_base').id; refined = {}
for side, dp, dr, t in near:
    pose = dict(HOME); pose[f'{side}_hip_pitch'] = HOME[f'{side}_hip_pitch'] + dp; pose[f'{side}_hip_roll'] = HOME[f'{side}_hip_roll'] + dr
    setup(m, d, NAMES, pose)
    Rt = d.xmat[tb].reshape(3, 3); pt = d.xpos[tb]
    best = (1e9, None)
    for g in legs[side]:
        if g not in LEGS:
            continue
        Rg = d.geom_xmat[g].reshape(3, 3); pg = d.geom_xpos[g]
        w = (LEGS[g] * mm) @ Rg.T + pg; loc = (w - pt) @ Rt / mm         # leg samples in the trunk frame (mm)
        loc = loc[np.all((loc >= BOX[t][0] - 6.0) & (loc <= BOX[t][1] + 6.0), axis=1)]
        if not len(loc):
            continue
        dist, _ = TGT[t].query(loc, k=1)
        if dist.min() < best[0]:
            best = (float(dist.min()), g)
    key = f'{t} | {side} pitch {np.degrees(dp):+.0f} roll {np.degrees(dr):+.0f}'
    refined[key] = dict(sampledMinMm=round(best[0], 2), legGeom=gname(best[1])) if best[1] is not None else dict(sampledMinMm=6.0, legGeom='none within 6 mm of the target box')
for t in ('frame', 'lid', 'usbc_plug'):
    rows = {k: v for k, v in refined.items() if k.startswith(t + ' |')}
    if rows:
        k, v = min(rows.items(), key=lambda kv: kv[1]['sampledMinMm'])
        res[t]['refinedTrueSurfaceMinMm'] = v['sampledMinMm']; res[t]['refinedAt'] = k; res[t]['refinedLegGeom'] = v['legGeom']
out = dict(method=__doc__, grid=dict(hipPitchDeltaDeg=[-30, 30, 5], hipRollDeltaDeg=[-10, 10, 5], posesPerLeg=len(PITCH) * len(ROLL)),
           homeJointsRad={k: round(v, 4) for k, v in HOME.items()}, minimumOverSweep=res, atHomeConvexHull=home,
           under2mm=[t for t, r in res.items() if r.get('refinedTrueSurfaceMinMm', r['minMm']) < 2.0], refinedPoses=refined)
(HERE / 'hip_sweep.json').write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps(dict(minimumOverSweep=res, under2mm=out['under2mm']), indent=1))
