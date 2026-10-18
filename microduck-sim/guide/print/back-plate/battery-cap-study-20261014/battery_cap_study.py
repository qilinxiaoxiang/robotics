"""Battery cap study (2026-10-14): where a 3S LiPo could ride on the released layout-F rear box, with numbers.

Read-only with respect to every release file. World = guide frame (mm, x forward, y left, z up, trunk_base origin).
Writes battery_cap_study.json and scene_home.pkl (render input, guide/content/render.py scene format) next to this file.

    ~/.venvs/microduck-dyn/bin/python battery_cap_study.py      (under run_bounded_cad.py)

Method:
- Packs are axis-aligned boxes at the manufacturer nominal size; the printed pocket of a "battery cap" adds a 1.2 mm wall
  around the pack. Clearances are checked on the pocket outer envelope (what a leg would touch).
- Leg clearance: hip_sweep.py's method (each hip pitch HOME +-30 deg in 5 deg steps x hip roll +-10 deg, other joints
  at HOME; mujoco.mj_geomDistance = convex-hull lower bound; sampled true surfaces where the hull distance is under 5 mm).
- Floor: feet-flat trunk pose at HOME and at the SIT keyframe (ctrl values of scene_backlash.xml's SIT key); the floor is
  z = 0 under the lowest sole point.
- COM: layout-F mass_estimate.json (as-built + layout F, 849.5 g) plus the pack and the extra printed pocket walls.
"""
import sys, json, itertools, pickle
from pathlib import Path
import numpy as np, mujoco, trimesh
from scipy.spatial import cKDTree
HERE = Path(__file__).resolve().parent
SIM = Path('/Users/xiangzheng/code/robotics/microduck-sim')
LF = SIM / 'guide/print/back-plate/layout-F'
REAL = SIM / 'hardware-design-20260912/whole-robot-20260912/dynamics/realgap-20261014'
sys.path.insert(0, str(REAL))
from static_gap import NAMES, HOME, setup, feet_flat_rot, sole_points
import evaluate_delay as ev
mm = 0.001

# ---------------------------------------------------------------- inputs
PACKS = {
    'tattu650': dict(label='Tattu 3S1P 650 mAh 75C XT30', L=58.0, W=31.0, T=16.0, g=59.0, tolLWT=[5.0, 2.0, 2.0], gTol=20.0,
                     source='retail spec sheets (getfpv.com / readymaderc.com / grobotronics.com, read 2026-10-14): 58 x 31 x 16 mm, net weight 59 g (+-20 g); grobotronics lists +-5 / +-2 / +-2 mm'),
    'tattu850': dict(label='Tattu 3S1P 850 mAh 75C XT30', L=60.0, W=30.0, T=23.0, g=80.0, tolLWT=None, gTol=20.0,
                     source='readymaderc.com / adorama.com / racedayquads.com (read 2026-10-14): 60 x 30 x 23 mm, 80 g (+-20 g on adorama); getfpv.com lists 57 mm long'),
}
NPF550 = dict(label='NP-F550 type (Pollen MicroDuck stock battery, 2S 7.2 V)', L=71.0, W=38.0, T=20.5, g=90.0,
              source='third-party listings (read 2026-10-14): about 70-71 x 38 x 20-23 mm, 88-110 g; reference only')
WALL = 1.2; CAP_FRONT = -59.1; CAP_BACK = -67.1; CAP_DEPTH = CAP_FRONT - CAP_BACK
Y_MAX = 32.05; Z_MAX = 43.0; Z_MIN = -36.02; SHELL_REAR = -46.4           # shell_right.stl min x (bounds.py 2026-10-14)
DFR = dict(x=[-45.0, -36.7], y=[-13.6, 13.6], z=[-42.8, 28.5])              # rear-pack-v19 channel, empty since V1.9
IN2_WINDOW = dict(x=[-65.9, -53.205], y=-32.05, z=[-5.6, 4.8])              # XL4015 #2 IN window, -y wall (layout-F README)
CONN = (25.0, 12.0, 8.0)                                                    # XT30 pair envelope to reserve (study brief)
MASS = json.loads((LF / 'mass_estimate.json').read_text())
M0, C0 = MASS['newTotalG'], np.array(MASS['newComMm'])                     # as-built + layout F
OFFICIAL_COM = np.array([0.56, -0.01, 21.75]); FILL = 0.851                 # v19-walk-summary official; v19-mass-items fill fraction


def pocket(lo, hi):
    return np.array(lo) - WALL, np.array(hi) + WALL


def placements():
    """Each placement: pack box (lo, hi) in world mm. Flat = thickness along x, length along y, width along z.
    Upright = length along z. Edge = width along x (pack standing on its long edge)."""
    out = {}
    for pk, p in PACKS.items():
        L, W, T = p['L'], p['W'], p['T']
        for ori, (dx, dy, dz) in dict(flat=(T, L, W), upright=(T, W, L), edge=(W, L, T)).items():
            x1 = CAP_BACK; x0 = x1 - dx
            zs = {'high': (Z_MAX - WALL - dz, Z_MAX - WALL), 'mid': (3.5 - dz / 2, 3.5 + dz / 2), 'low': (Z_MIN + WALL, Z_MIN + WALL + dz)}
            for zk, (z0, z1) in zs.items():
                if ori == 'upright' and zk != 'high':
                    continue                                                # a 58-60 mm tall pack only fits top-flush
                if ori == 'edge' and zk == 'mid':
                    continue
                out[f'{pk}-{ori}-{zk}'] = dict(pack=pk, orientation=ori, zpos=zk, lo=[x0, -dy / 2, z0], hi=[x1, dy / 2, z1])
    return out


def dfr_fit():
    ch = np.array([DFR['x'][1] - DFR['x'][0], DFR['y'][1] - DFR['y'][0], DFR['z'][1] - DFR['z'][0]])
    res = {}
    for pk, p in list(PACKS.items()) + [('npf550', NPF550)]:
        dims = (p['L'], p['W'], p['T']); best = None
        for perm in itertools.permutations(dims):
            clr = ch - np.array(perm)
            if best is None or clr.min() > best[1].min():
                best = (perm, clr)
        res[pk] = dict(channelInnerMm=ch.round(2).tolist(), bestOrientationXYZ=list(best[0]), clearanceXYZmm=best[1].round(2).tolist(),
                       fits=bool((best[1] >= 0).all()))
    return res


# ---------------------------------------------------------------- model
spec = mujoco.MjSpec.from_file(str(ev.MODEL_DIR / 'scene.xml')); trunk = spec.body('trunk_base')
for g in list(spec.geoms):
    if g.name in ('power_support', 'np_f970'):
        spec.delete(g)
STL = {'frame': LF / 'rear_frame-world.stl', 'lid': LF / 'rear_lid-world.stl', 'pack': SIM / 'guide/print/world/rear_pack-v18.stl'}
for tag, f in STL.items():
    a = spec.add_mesh(name=f'm_{tag}', file=str(f), scale=[mm] * 3)
    trunk.add_geom(name=f'box_{tag}', type=mujoco.mjtGeom.mjGEOM_MESH, meshname=a.name, contype=0, conaffinity=0, mass=0)
PL = placements()
CONNS = {
    'K1-behind-cap-under-pack': dict(lo=[CAP_BACK - CONN[2], -Y_MAX, -5.6], hi=[CAP_BACK, -Y_MAX + CONN[0], -5.6 + CONN[1]],
                                     what='lies across the cap back at window height, long axis y, mates by pulling toward -y; 8 mm deep in x'),
    'K2-beside-wall-along-x': dict(lo=[-66.0, -Y_MAX - CONN[1], -4.4], hi=[-41.0, -Y_MAX, 3.6],
                                   what='outboard of the -y wall at the IN window, long axis x'),
    'K3-beside-wall-along-z': dict(lo=[-65.9, -Y_MAX - CONN[1], -12.5], hi=[-57.9, -Y_MAX, 12.5],
                                   what='outboard of the -y wall at the IN window, long axis z'),
    'K4-behind-cap-corner-along-x': dict(lo=[CAP_BACK - CONN[0], -Y_MAX, -5.6], hi=[CAP_BACK, -Y_MAX + CONN[1], 2.4],
                                         what='behind the cap at the -y corner, long axis x (mates by pulling backward)'),
}
boxes = {}
for k, p in PL.items():
    boxes[k] = pocket(p['lo'], p['hi'])
for k, c in CONNS.items():
    boxes[k] = (np.array(c['lo'], float), np.array(c['hi'], float))
for k, (lo, hi) in boxes.items():
    trunk.add_geom(name=k, type=mujoco.mjtGeom.mjGEOM_BOX, pos=(lo + hi) / 2 * mm, size=(hi - lo) / 2 * mm, contype=0, conaffinity=0, mass=0)
# released wire loops outside the -y wall (wires_F.json, |y| > 30.85), as hip_sweep.py builds them
W = json.loads((LF / 'wires_F.json').read_text()); loop_caps = []
for k, v in W.items():
    p = np.array(v['points']); idx = np.where(np.abs(p[:, 1]) > 30.85)[0]
    if not len(idx):
        continue
    seg = p[max(idx[0] - 1, 0):idx[-1] + 2][::2]
    for i in range(len(seg) - 1):
        if np.linalg.norm(seg[i + 1] - seg[i]) < 1e-3:
            continue
        n = f'loop_{k}_{i}'; loop_caps.append(n)
        trunk.add_geom(name=n, type=mujoco.mjtGeom.mjGEOM_CAPSULE, fromto=np.r_[seg[i] * mm, seg[i + 1] * mm], size=[0.9 * mm, 0, 0], contype=0, conaffinity=0, mass=0)
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
gname = lambda g: m.geom(g).name or f'{m.body(m.geom_bodyid[g]).name}#geom{g}'
DMAX = 0.05
PITCH = np.radians(np.arange(-30, 30.1, 5.0)); ROLL = np.radians(np.arange(-10, 10.1, 5.0))
targets = {k: m.geom(k).id for k in boxes}
res = {t: dict(minMm=1e9) for t in targets}; home = {}; near = []
for side in ('left', 'right'):
    for dp, dr in [(0.0, 0.0)] + list(itertools.product(PITCH, ROLL)):
        pose = dict(HOME); pose[f'{side}_hip_pitch'] = HOME[f'{side}_hip_pitch'] + dp; pose[f'{side}_hip_roll'] = HOME[f'{side}_hip_roll'] + dr
        setup(m, d, NAMES, pose)
        for t, a in targets.items():
            best = (1e9, None)
            for b in legs[side]:
                dist = mujoco.mj_geomDistance(m, d, a, b, DMAX, None)
                if dist < best[0]:
                    best = (dist, b)
            dmm = best[0] / mm
            if dmm < 5.0:
                near.append((side, float(dp), float(dr), t))
            if dp == 0 and dr == 0:
                home[f'{t} | {side}'] = dict(minMm=round(dmm, 2), legGeom=gname(best[1]))
            if dmm < res[t]['minMm']:
                res[t] = dict(minMm=round(dmm, 2), legGeom=gname(best[1]), side=side,
                              hipPitchDeltaDeg=round(float(np.degrees(dp)), 1), hipRollDeltaDeg=round(float(np.degrees(dr)), 1))
# refinement on sampled true surfaces (boxes are exact; leg meshes sampled at 0.4 mm)
def samples(tm, spacing=0.25):
    n = int(tm.area / spacing ** 2) + 100
    p, _ = trimesh.sample.sample_surface(tm, n, seed=1); return np.vstack([p, tm.vertices])
TGT = {k: cKDTree(samples(trimesh.creation.box(bounds=np.array(b)))) for k, b in boxes.items()}
LEGS = {}
for side in ('left', 'right'):
    for g in legs[side]:
        if m.geom_type[g] != mujoco.mjtGeom.mjGEOM_MESH:
            continue
        mid = m.geom_dataid[g]; a, nv = m.mesh_vertadr[mid], m.mesh_vertnum[mid]; fa, nf = m.mesh_faceadr[mid], m.mesh_facenum[mid]
        LEGS[g] = samples(trimesh.Trimesh(m.mesh_vert[a:a + nv] / mm, m.mesh_face[fa:fa + nf], process=False), 0.4)
tb = m.body('trunk_base').id; refined = {}
for side, dp, dr, t in near:
    pose = dict(HOME); pose[f'{side}_hip_pitch'] = HOME[f'{side}_hip_pitch'] + dp; pose[f'{side}_hip_roll'] = HOME[f'{side}_hip_roll'] + dr
    setup(m, d, NAMES, pose)
    Rt = d.xmat[tb].reshape(3, 3); pt = d.xpos[tb]; best = (1e9, None); lo, hi = boxes[t]
    for g in legs[side]:
        if g not in LEGS:
            continue
        Rg = d.geom_xmat[g].reshape(3, 3); pg = d.geom_xpos[g]
        loc = ((LEGS[g] * mm) @ Rg.T + pg - pt) @ Rt / mm
        loc = loc[np.all((loc >= lo - 6.0) & (loc <= hi + 6.0), axis=1)]
        if not len(loc):
            continue
        dist, _ = TGT[t].query(loc, k=1)
        if dist.min() < best[0]:
            best = (float(dist.min()), g)
    key = f'{t} | {side} pitch {np.degrees(dp):+.0f} roll {np.degrees(dr):+.0f}'
    refined[key] = dict(sampledMinMm=round(best[0], 2), legGeom=gname(best[1])) if best[1] is not None else dict(sampledMinMm=6.0, legGeom='none within 6 mm')
for t in targets:
    rows = {k: v for k, v in refined.items() if k.startswith(t + ' |')}
    if rows:
        k, v = min(rows.items(), key=lambda kv: kv[1]['sampledMinMm'])
        res[t]['refinedTrueSurfaceMinMm'] = v['sampledMinMm']; res[t]['refinedAt'] = k
legMin = {t: r.get('refinedTrueSurfaceMinMm', r['minMm']) for t, r in res.items()}

# ---------------------------------------------------------------- floor at HOME and SIT (feet flat)
SIT_CTRL = [0, 0, -0.5236, 1.0472, 0, 0.5, 1.6, 0, 0, 0, 0, 0, 0.5236, -1.0472, 0]   # scene_backlash.xml key SIT ctrl, policy order
SIT = dict(zip(NAMES, [SIT_CTRL[i] for i in (0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14)]))
floor = {}
def mesh_world_pts(g):
    mid = m.geom_dataid[g]; a, nv = m.mesh_vertadr[mid], m.mesh_vertnum[mid]
    return m.mesh_vert[a:a + nv] @ d.geom_xmat[g].reshape(3, 3).T + d.geom_xpos[g]
for pn, pose in (('HOME', HOME), ('SIT', SIT)):
    if pn == 'HOME':
        Rt = feet_flat_rot(m, d, NAMES, pose); q = np.zeros(4); mujoco.mju_mat2Quat(q, Rt.ravel()); setup(m, d, NAMES, pose, q)
        z = np.vstack(sole_points(m, d))[:, 2].min()
    else:
        # SIT keyframe: trunk upright (quat 1 0 0 0, z 0.07); the robot rests on whatever is lowest (feet are not flat)
        setup(m, d, NAMES, pose, (1, 0, 0, 0))
        z = min(mesh_world_pts(g)[:, 2].min() for g in range(m.ngeom) if m.geom_type[g] == mujoco.mjtGeom.mjGEOM_MESH and not m.geom(g).name.startswith('box_'))
    d.qpos[2] -= z; mujoco.mj_forward(m, d)
    R = d.xmat[tb].reshape(3, 3); p = d.xpos[tb]
    pitch = float(np.degrees(np.arctan2(-R[2, 0], R[2, 2])))
    def lowest(lo, hi):
        c = np.array(list(itertools.product(*zip(lo, hi)))) * mm
        return round(float(((c @ R.T) + p)[:, 2].min() / mm), 1)
    todays = {}
    for tag in STL:
        g = m.geom(f'box_{tag}').id; mid = m.geom_dataid[g]; a, nv = m.mesh_vertadr[mid], m.mesh_vertnum[mid]
        w = m.mesh_vert[a:a + nv] @ d.geom_xmat[g].reshape(3, 3).T + d.geom_xpos[g]
        todays[tag] = round(float(w[:, 2].min() / mm), 1)
    floor[pn] = dict(trunkOriginHeightMm=round(float(p[2] / mm), 1), trunkPitchDegNoseDown=round(pitch, 2), todayLowestPointAboveFloorMm=todays,
                     candidates={k: lowest(*boxes[k]) for k in boxes})
    if pn == 'HOME':
        # export the posed robot for the vtk render (guide/content/render.py scene format: v mm, f, color 0-255)
        scene = {}
        for g in range(m.ngeom):
            if m.geom_type[g] != mujoco.mjtGeom.mjGEOM_MESH or 'collision' in (m.geom(g).name or ''):
                continue
            if m.geom(g).name.startswith('box_'):
                continue
            mid = m.geom_dataid[g]; a, nv = m.mesh_vertadr[mid], m.mesh_vertnum[mid]; fa, nf = m.mesh_faceadr[mid], m.mesh_facenum[mid]
            w = (m.mesh_vert[a:a + nv] @ d.geom_xmat[g].reshape(3, 3).T + d.geom_xpos[g]) / mm
            rgba = m.geom_rgba[g]; body = m.body(m.geom_bodyid[g]).name
            scene[f'{body}#{g}'] = dict(v=w.astype(np.float32), f=m.mesh_face[fa:fa + nf].copy(), color=[int(255 * c) for c in rgba[:3]], module=body)
        pickle.dump(dict(trunkPos=p.copy(), trunkR=R.copy(), floorZ=0.0, scene=scene), open(HERE / 'scene_home.pkl', 'wb'))

# ---------------------------------------------------------------- static checks: box rules, shells, frame/lid, wire loops, connectors vs packs
FR = trimesh.load(str(STL['frame']), force='mesh'); CP = trimesh.load(str(STL['lid']), force='mesh')
SH = [trimesh.load(str(SIM / f'guide/print/world/{s}.stl'), force='mesh') for s in ('shell_left', 'shell_right')]
def box_gap(tm, lo, hi):
    """Signed distance from mesh samples to the box (negative = sample inside the box)."""
    pts = np.vstack([tm.vertices] + [trimesh.sample.sample_surface(tm, int(tm.area / 0.5 ** 2) + 100, seed=1)[0]])
    dlo = lo - pts; dhi = pts - hi; out = np.maximum(np.maximum(dlo, dhi), 0)
    outside = np.linalg.norm(out, axis=1); inside = np.max(np.maximum(dlo, dhi), axis=1)
    return round(float(np.where(outside > 0, outside, inside).min()), 2)
def box_box_gap(a, b):
    g = np.maximum(a[0] - b[1], b[0] - a[1]); return round(float(np.linalg.norm(np.maximum(g, 0))) if (g > 0).any() else float(g.max()), 2)
loop_tm = None
for n in loop_caps:
    g = m.geom(n).id; a, b = m.geom_pos[g] / mm, m.geom_size[g]
    # fromto capsules: geom_pos is the centre, geom_quat its axis; rebuild from the local quaternion
    R = np.zeros(9); mujoco.mju_quat2Mat(R, m.geom_quat[g]); R = R.reshape(3, 3); h = b[1] / mm
    seg = trimesh.creation.capsule(radius=0.9, height=2 * h, count=[8, 8])
    T = np.eye(4); T[:3, :3] = R; T[:3, 3] = a; seg.apply_transform(T)
    loop_tm = seg if loop_tm is None else trimesh.util.concatenate([loop_tm, seg])
static = {}
for k, (lo, hi) in boxes.items():
    static[k] = dict(frameGapMm=box_gap(FR, lo, hi), capGapMm=box_gap(CP, lo, hi), shellGapMm=min(box_gap(s, lo, hi) for s in SH),
                     releasedWireLoopsGapMm=box_gap(loop_tm, lo, hi), yMaxAbs=round(float(max(abs(lo[1]), abs(hi[1]))), 2),
                     zRange=[round(float(lo[2]), 2), round(float(hi[2]), 2)], insideYRule=bool(max(abs(lo[1]), abs(hi[1])) <= Y_MAX + 1e-6),
                     insideZRule=bool(lo[2] >= Z_MIN - 1e-6 and hi[2] <= Z_MAX + 1e-6))
# ---------------------------------------------------------------- placement numbers and COM
rows = {}
for k, p in PL.items():
    pk = PACKS[p['pack']]; lo, hi = np.array(p['lo']), np.array(p['hi']); plo, phi = boxes[k]
    dx, dy, dz = hi - lo
    rearmost = float(plo[0]); depth = CAP_FRONT - rearmost
    pocket_area = (dy + 2 * WALL) * (dz + 2 * WALL) + 2 * (dy + 2 * WALL) * dx + 2 * (dz + 2 * WALL) * dx
    cap_extra_g = pocket_area * WALL / 1000 * 1.24 * FILL
    c_pack = (lo + hi) / 2; c_pocket = (plo + phi) / 2
    dm = pk['g'] + cap_extra_g
    shift = (pk['g'] * (c_pack - C0) + cap_extra_g * (c_pocket - C0)) / (M0 + dm)
    tol = pk['tolLWT']
    rows[k] = dict(pack=pk['label'], orientation=p['orientation'], zPosition=p['zpos'], packBoxMm=[lo.round(2).tolist(), hi.round(2).tolist()],
                   pocketOuterMm=[plo.round(2).tolist(), phi.round(2).tolist()], capDepthMm=round(depth, 1), capDepthTodayMm=CAP_DEPTH,
                   rearmostXmm=round(rearmost, 1), rearOverhangBehindShellsMm=round(SHELL_REAR - rearmost, 1), rearOverhangTodayMm=round(SHELL_REAR - CAP_BACK, 1),
                   pocketHalfWidthY=round(float(phi[1]), 2), insideYRule=static[k]['insideYRule'], insideZRule=static[k]['insideZRule'],
                   pocketHalfWidthYWithLengthTolerance=(round(float(phi[1] + tol[0] / 2), 2) if tol and p['orientation'] in ('flat', 'edge') else None),
                   legSweepMinMm=legMin[k], legSweepWorst=res[k], legAtHomeMm=min(home[f'{k} | {s}']['minMm'] for s in ('left', 'right')),
                   lowestAboveFloorHomeMm=floor['HOME']['candidates'][k], lowestAboveFloorSitMm=floor['SIT']['candidates'][k],
                   shellGapMm=static[k]['shellGapMm'], frameGapMm=static[k]['frameGapMm'], capGapMm=static[k]['capGapMm'],
                   releasedWireLoopsGapMm=static[k]['releasedWireLoopsGapMm'],
                   mass=dict(packG=pk['g'], packGTol=pk['gTol'], capExtraPrintedG=round(cap_extra_g, 1), addedG=round(dm, 1), newTotalG=round(M0 + dm, 1),
                             packCentreMm=c_pack.round(2).tolist(), leverArmXmm=round(float(c_pack[0] - C0[0]), 1),
                             comShiftMm=shift.round(2).tolist(), newComMm=(C0 + shift).round(2).tolist(),
                             newComVsOfficialMm=(C0 + shift - OFFICIAL_COM).round(2).tolist(),
                             comShiftWithPackTolPlus20g=round(float(((pk['g'] + 20) * (c_pack - C0) + cap_extra_g * (c_pocket - C0))[0] / (M0 + dm + 20)), 2)))
conn = {}
for k, c in CONNS.items():
    lo, hi = boxes[k]
    conn[k] = dict(what=c['what'], envelopeMm=[lo.tolist(), hi.tolist()], legSweepMinMm=legMin[k], legSweepWorst=res[k],
                   frameGapMm=static[k]['frameGapMm'], capGapMm=static[k]['capGapMm'], shellGapMm=static[k]['shellGapMm'],
                   releasedWireLoopsGapMm=static[k]['releasedWireLoopsGapMm'], lowestAboveFloorSitMm=floor['SIT']['candidates'][k],
                   gapToPackPocketMm={pk: box_box_gap(boxes[k], boxes[pk]) for pk in PL},
                   in2WindowOverlapX=[round(max(lo[0], IN2_WINDOW['x'][0]), 1), round(min(hi[0], IN2_WINDOW['x'][1]), 1)])
out = dict(method=__doc__, inputs=dict(packs=PACKS, npf550Reference=NPF550, wallMm=WALL, capTodayX=[CAP_BACK, CAP_FRONT], boxRule=dict(absYMax=Y_MAX, z=[Z_MIN, Z_MAX]),
                                       shellRearX=SHELL_REAR, dfrChannel=DFR, in2Window=IN2_WINDOW, connectorEnvelopeMm=list(CONN),
                                       massBaseline=dict(source='layout-F/mass_estimate.json newTotalG/newComMm', totalG=M0, comMm=C0.tolist(), officialComMm=OFFICIAL_COM.tolist())),
           sweepGrid=dict(hipPitchDeltaDeg=[-30, 30, 5], hipRollDeltaDeg=[-10, 10, 5]), dfrChannelFit=dfr_fit(), placements=rows, connectors=conn,
           floor={k: {kk: vv for kk, vv in v.items() if kk != 'candidates'} for k, v in floor.items()},
           todayBoxLegSweep=dict(source='layout-F/hip_sweep.json', frameRefinedMm=13.25, lidHullMm=17.66, usbcPlugRefinedMm=4.28))
(HERE / 'battery_cap_study.json').write_text(json.dumps(out, indent=1, default=float) + '\n')
for k, r in rows.items():
    print(f"{k:28s} depth {r['capDepthMm']:5.1f} rear x {r['rearmostXmm']:6.1f} overhang {r['rearOverhangBehindShellsMm']:5.1f} |y| {r['pocketHalfWidthY']:5.2f} z {r['pocketOuterMm'][0][2]:6.1f}..{r['pocketOuterMm'][1][2]:5.1f} legs {r['legSweepMinMm']:6.2f} floorSIT {r['lowestAboveFloorSitMm']:6.1f} com {r['mass']['comShiftMm']}")
for k, r in conn.items():
    print(f"{k:28s} legs {r['legSweepMinMm']:6.2f} frame {r['frameGapMm']} cap {r['capGapMm']} shell {r['shellGapMm']} loops {r['releasedWireLoopsGapMm']} floorSIT {r['lowestAboveFloorSitMm']}")
print(json.dumps(out['dfrChannelFit'], indent=0)); print(json.dumps(out['floor'], indent=0))
