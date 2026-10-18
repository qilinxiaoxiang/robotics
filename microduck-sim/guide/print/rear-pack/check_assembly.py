"""Check 6: straight assembly sweeps (0.5 mm steps, exact manifold3d booleans) and dia 6 x 60 screwdriver reach. Writes check_assembly.json."""
import json, time
import numpy as np
import pack_lib as P
import pso_lib as L
import ia_lib

t0 = time.time()
OUT = P.OUT
bm = P.load_stl(OUT / 'rear_pack-world.stl'); cm = P.load_stl(OUT / 'rear_pack_cover-world.stl')
B = P.mesh_to_m(bm); C = P.mesh_to_m(cm)
orb_mesh = P.openrb_mesh(); imu_mesh = P.imu_mesh()
ORB = P.mesh_to_m(orb_mesh); IMU = P.mesh_to_m(imu_mesh)
DFR = P.box(*P.DFR_BOX)
man = ia_lib.manifest()
legs = set()
for sd in L.SIDE.values():
    for ks in sd['parts'].values():
        legs.update(ks)
SHELLS = {'shell_left', 'shell_right'}


def env_parts(exclude_legs, exclude_shells, sweep_bounds):
    out = []
    for k, rec in man.items():
        if k in P.RETIRED or k in P.SELF_KEYS or (exclude_legs and k in legs) or (exclude_shells and k in SHELLS):
            continue
        lo, hi = np.array(rec['bounds'])
        if np.all(lo - 3 <= sweep_bounds[1]) and np.all(hi + 3 >= sweep_bounds[0]):
            out.append((k, P.solid_m(k), (lo, hi)))
    return out


def sweep(name, mover, mover_bounds, path, obstacles, gap_search=3.0):
    """path: list of (dx, dy, dz) offsets in order of motion (last = final seat). Returns per-step worst overlap and gap."""
    steps = []
    worst = dict(maxOverlapMm3=0.0, minGapMm=gap_search, firstCollision=None, closestObstacle=None, closestOffset=None)
    for off in path:
        mv = mover.translate(list(map(float, off)))
        mb = (mover_bounds[0] + off, mover_bounds[1] + off)
        ov = 0.0; gap = gap_search; who = None
        for k, om, ob in obstacles:
            if not (np.all(ob[0] - gap_search <= mb[1]) and np.all(ob[1] + gap_search >= mb[0])):
                continue
            v = float((mv ^ om).volume())
            if v > 1e-6:
                ov = max(ov, v)
                if worst['firstCollision'] is None:
                    worst['firstCollision'] = dict(offset=list(map(float, off)), obstacle=k, overlapMm3=round(v, 4))
            g = float(mv.min_gap(om, gap_search))
            if g < gap:
                gap = g; who = k
        steps.append((list(map(float, off)), round(ov, 4), round(gap, 4), who))
        if ov > worst['maxOverlapMm3']:
            worst['maxOverlapMm3'] = round(ov, 4)
        if gap < worst['minGapMm']:
            worst.update(minGapMm=round(gap, 4), closestObstacle=who, closestOffset=list(map(float, off)))
    worst['steps'] = len(path); worst['stepMm'] = 0.5
    worst['collisionSteps'] = int(sum(1 for s in steps if s[1] > 1e-6))
    worst['pass'] = worst['collisionSteps'] == 0
    worst['stepTable'] = steps if len(steps) <= 80 else steps[::2]
    print(name, {k: v for k, v in worst.items() if k != 'stepTable'}, flush=True)
    return worst


def line(axis, dist, step=0.5):
    n = int(round(dist / step)); ax = np.zeros(3); ax[axis] = 1.0
    return [tuple(-ax * (dist - i * step)) for i in range(n + 1)]       # from far away to the seat (offset 0)


res = {}
# ---- pack body +x 30 (legs and shells off)
pb = (bm.bounds[0] + np.array([-30, 0, 0]), bm.bounds[1])
res['pack_body_plus_x_30'] = sweep('pack +x', B, (bm.bounds[0], bm.bounds[1]), line(0, 30.0), env_parts(True, True, pb))
# ---- cover +x 15 vs body, boards, torso parts (shells off) and again with shells on
cb = (cm.bounds[0] + np.array([-15, 0, 0]), cm.bounds[1])
obst = [('body', B, (bm.bounds[0], bm.bounds[1])), ('openrb', ORB, orb_mesh.bounds), ('imu', IMU, imu_mesh.bounds), ('dfr_box', DFR, P.DFR_BOX)]
res['cover_plus_x_15_shells_off'] = sweep('cover +x (shells off)', C, (cm.bounds[0], cm.bounds[1]), line(0, 15.0), obst + env_parts(False, True, cb))
res['cover_plus_x_15_shells_on'] = sweep('cover +x (shells on)', C, (cm.bounds[0], cm.bounds[1]), line(0, 15.0), obst + env_parts(False, False, cb))
# ---- OpenRB: straight +x 20 (as specified) and the drop-in path: down 30 at x -3, then +x 3
ob_ = (orb_mesh.bounds[0] + np.array([-20, 0, -30]), orb_mesh.bounds[1] + np.array([0, 0, 30]))
obst_orb = [('body', B, (bm.bounds[0], bm.bounds[1]))] + env_parts(False, True, ob_)
res['openrb_plus_x_20_straight'] = sweep('openrb +x 20', ORB, orb_mesh.bounds, line(0, 20.0), obst_orb)
path = [(-3.0, 0.0, 30.0 - i * 0.5) for i in range(61)] + [(-3.0 + 0.5 * i, 0.0, 0.0) for i in range(1, 7)]
res['openrb_drop_in_z30_at_xminus3_then_plus_x_3'] = sweep('openrb drop-in', ORB, orb_mesh.bounds, path, obst_orb)
# ---- DFR box from above 35 (cover off, OpenRB in)
db = (P.DFR_BOX[0], P.DFR_BOX[1] + np.array([0, 0, 35]))
res['dfr_from_above_35'] = sweep('dfr from above', DFR, P.DFR_BOX, [(0.0, 0.0, 35.0 - i * 0.5) for i in range(71)],
                                 [('body', B, (bm.bounds[0], bm.bounds[1])), ('openrb', ORB, orb_mesh.bounds)] + env_parts(False, True, db))
# ---- IMU from above 30
ib = (imu_mesh.bounds[0], imu_mesh.bounds[1] + np.array([0, 0, 30]))
res['imu_from_above_30'] = sweep('imu from above', IMU, imu_mesh.bounds, [(0.0, 0.0, 30.0 - i * 0.5) for i in range(61)],
                                 [('body', B, (bm.bounds[0], bm.bounds[1])), ('openrb', ORB, orb_mesh.bounds)] + env_parts(False, True, ib))
# ---- screwdriver dia 6 x 60 along +x: to each OpenRB screw head (head top at x -28.4; DFR not in) and to each cover post
drv = {}
for (y, z) in P.openrb_holes_world():
    cyl = P.cyl_x(3.0, -88.4, -28.4, y, z); cb_ = (np.array([-88.4, y - 3, z - 3]), np.array([-28.4, y + 3, z + 3]))
    obs = [('body', B, (bm.bounds[0], bm.bounds[1])), ('openrb', ORB, orb_mesh.bounds), ('imu', IMU, imu_mesh.bounds)] + env_parts(False, True, cb_)
    row = {}
    for k, om, ob in obs:
        v = float((cyl ^ om).volume()); g = float(cyl.min_gap(om, 3.0))
        if v > 1e-6 or g < 3.0:
            row[k] = dict(overlapMm3=round(v, 4), gapMm=round(g, 4))
    shells = {k: dict(overlapMm3=round(float((cyl ^ P.solid_m(k)).volume()), 4), gapMm=round(float(cyl.min_gap(P.solid_m(k), 3.0)), 4)) for k in SHELLS}
    # largest shaft radius that clears the OpenRB's own components and the body along this axis (tip at x -28.4)
    V = orb_mesh.vertices; sel = V[V[:, 0] < -28.4]; rr = np.hypot(sel[:, 1] - y, sel[:, 2] - z)
    rad = {'openrbComponentsMm': round(float(rr.min()), 3)}
    for rtest in (3.0, 2.5, 2.25, 2.0):
        cyl2 = P.cyl_x(rtest, -88.4, -28.4, y, z)
        rad[f'dia{2*rtest:g}_overlapOpenrbMm3'] = round(float((cyl2 ^ ORB).volume()), 4); rad[f'dia{2*rtest:g}_overlapBodyMm3'] = round(float((cyl2 ^ B).volume()), 4)
    drv[f'openrb_screw_y{y}_z{z}'] = {'tipX': -28.4, 'nearest': row, 'shellsOn': shells, 'shaftRadiusLimits': rad, 'pass': all(r['overlapMm3'] < 1e-6 for r in row.values())}
    print('driver openrb', y, z, drv[f'openrb_screw_y{y}_z{z}'], flush=True)
for (y, z) in [(16.1, 26.0), (16.1, -36.5), (-16.1, 26.0), (-16.1, -36.5)]:
    cyl = P.cyl_x(3.0, -107.0, -47.0, y, z); cb_ = (np.array([-107.0, y - 3, z - 3]), np.array([-47.0, y + 3, z + 3]))
    obs = [('body', B, (bm.bounds[0], bm.bounds[1])), ('cover', C, (cm.bounds[0], cm.bounds[1]))] + env_parts(False, False, cb_)
    row = {}
    for k, om, ob in obs:
        v = float((cyl ^ om).volume()); g = float(cyl.min_gap(om, 3.0))
        if v > 1e-6 or g < 3.0:
            row[k] = dict(overlapMm3=round(v, 4), gapMm=round(g, 4))
    drv[f'cover_screw_y{y}_z{z}'] = {'tipX': -47.0, 'nearest': row, 'pass': all(r['overlapMm3'] < 1e-6 for r in row.values())}
    print('driver cover', y, z, drv[f'cover_screw_y{y}_z{z}'], flush=True)
res['screwdriver_dia6_len60'] = drv
res['elapsed_s'] = round(time.time() - t0, 1)
P.jdump(res, OUT / 'check_assembly.json')
print('DONE', res['elapsed_s'], {k: v.get('pass') for k, v in res.items() if isinstance(v, dict) and 'pass' in v})
