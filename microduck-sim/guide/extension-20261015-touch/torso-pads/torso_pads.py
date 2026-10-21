"""Torso-shell touch pads: placement, clearances, wire routes and a torso-board fit, from the print-gate solids.

Inputs (read-only): the print-gate closed solids (ia_lib CACHE) in the final pose, guide/data/guide-data.json (cables,
screws), ../analysis/head_space.npz (1 mm head grid), ../touch_routes.json (XIAO ESP32-S3 pose) and ../world/*.stl.
Outputs next to this file: results.json, pad_shell_left.png, pad_shell_right.png.
Frame: robot, mm, x forward, y left, z up. Distances are point-cloud distances (surface samples about 0.4 mm apart),
so they read up to about 0.3 mm high against the exact surfaces.
Run: run_bounded_cad.py --max-mib 2000 --report <file> -- /tmp/microduck-cad-venv/bin/python torso_pads.py
"""
import heapq, json, sys
from pathlib import Path
import numpy as np, trimesh
from scipy import ndimage
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation as R

HERE = Path(__file__).resolve().parent
TOUCH = HERE.parent
GUIDE = TOUCH.parent
sys.path.insert(0, str(GUIDE / 'content' / 'interference-audit'))
from ia_lib import load_solid, manifest, load_guide   # noqa: E402

PAD = 18                                  # mm square, four 5 mm strips
MOVE_MIN, METAL_MIN = 4.0, 3.0            # Shawn's limits: moving parts, metal and boards
AX12 = (np.array([26.0, 0.0, 32.5]), np.array([0.0, 1.0, 0.0]))   # ID12 horn axis (shell screw pattern centre)
NECK = ['motor12', 'idler_cap12', 'neck_link_a', 'neck_link_b', 'motor11', 'idler11', 'idler_cap11', 'neck_pitch',
        'neck_pitch_ring', 'motor13', 'head_yaw_link']                          # turn with ID12
LEG_L = ['yaw', 'hip', 'passive', 'ring9', 'motor9', 'ring8', 'motor8', 'thigh', 'plate']
LEG_R = ['right_yaw', 'right_hip', 'right_passive', 'ring4', 'motor4', 'ring3', 'motor3', 'right_thigh', 'right_plate']
YAW_AX = {'shell_left': np.array([6.0, 17.5]), 'shell_right': np.array([6.0, -17.5])}   # ring10/ring5 centres (x, y)
SERVO = ['motor10', 'motor5']
BOARD = ['imu_board', 'openrb_board', 'xl4015_top', 'xl4015_mid', 'pd5991', 'bp_switch', 'bp_battery', 'bp_dfr1202',
         'bp_plugs', 'bp_swap_plugs']
PRINTED = ['rear_pack', 'rear_frame', 'rear_lid', 'battery_backpack_frame', 'battery_backpack_cap', 'torso_base',
           'ring10_torso', 'ring5_torso', 'idler12', 'clip_torso', 'imu_sh4_receiving']
BUNDLE = ['imu', 'uart', 'pi-lead']

man = manifest()
guide = load_guide()
cables = {c['id']: c for c in guide['cables']}


def mesh(k):
    v, f = load_solid(k)
    return trimesh.Trimesh(v, f, process=False)


def cloud(k, per_mm2=1 / 0.15):
    m = mesh(k)
    n = int(min(300000, max(3000, m.area * per_mm2)))
    return np.vstack([m.vertices, trimesh.sample.sample_surface_even(m, n, seed=0)[0]]).astype(np.float64)


C = {k: cloud(k) for k in set(NECK + LEG_L + LEG_R + SERVO + BOARD + PRINTED) if k in man}
T = {k: cKDTree(v) for k, v in C.items()}
shells = {k: mesh(k) for k in ('shell_left', 'shell_right')}
print('clouds', len(C), flush=True)


def cable_pts(cid, step=0.5):
    p = np.array(cables[cid]['path'], float)
    return np.concatenate([np.linspace(a, b, max(2, int(np.linalg.norm(b - a) / step))) for a, b in zip(p[:-1], p[1:])])


def screw_pts(s):
    c, a = np.array(s['center'], float), np.array(s['axis'], float)
    t = np.linspace(0, s['lengthMm'], int(s['lengthMm'] / 0.25) + 1)
    return c + t[:, None] * a, s['diameterMm'] / 2, c, s['headDiameterMm'] / 2


def rot(points, centre, axis, deg):
    return R.from_rotvec(np.deg2rad(deg) * axis).apply(points - centre) + centre


# ---------------------------------------------------------------- ID12 range without collision with the torso
static_near = np.vstack([C[k] for k in SERVO + BOARD + PRINTED if k in C] +
                        [trimesh.sample.sample_surface_even(m, 60000, seed=3)[0] for m in shells.values()])
static_tree = cKDTree(static_near)
neck_pts = np.vstack([C[k] for k in NECK if k in C])
neck_pts = neck_pts[np.linalg.norm((neck_pts - AX12[0])[:, [0, 2]], axis=1) < 90]
free_deg = []
# Contacts that exist at rest (horn on the left shell, idler on the right shell, idler12 in the motor) are not limits:
# test only neck points more than 14 mm from the ID12 axis against torso parts other than idler12.
coll_static = cKDTree(np.vstack([C[k] for k in SERVO + BOARD + PRINTED if k in C and k != 'idler12'] +
                                [trimesh.sample.sample_surface_even(m, 60000, seed=3)[0] for m in shells.values()]))
far = neck_pts[np.linalg.norm((neck_pts - AX12[0])[:, [0, 2]], axis=1) > 14][::5]
base = coll_static.query(far)[0].min()
print('neck far-point clearance at rest', round(base, 2), flush=True)
for sgn in (+1, -1):
    for d in range(0, 181, 2):
        q = rot(far, AX12[0], AX12[1], sgn * d)
        if d and coll_static.query(q, distance_upper_bound=0.4)[0].min() < min(0.4, base - 0.05):
            break
        free_deg.append(sgn * d)
pitch_lo, pitch_hi = min(free_deg), max(free_deg)
# Clip to the model joint range under either sign convention (-90..60 or -60..90): union [-66, 90] here.
pitch_lo, pitch_hi = max(pitch_lo, -90), min(pitch_hi, 90)
model_range = (-90.0, 60.0)               # robot_groundcontact.xml neck_pitch range (sign convention not checked)
print('ID12 collision-free range', pitch_lo, pitch_hi, flush=True)
ANG = np.arange(pitch_lo, pitch_hi + 1, 2.0)
neck_tree = cKDTree(neck_pts)
n12_moving = cable_pts('dxl-n12')[cable_pts('dxl-n12')[:, 0] > 14]        # last stretch rides on ID12


def swept_neck(p):
    return np.min([neck_tree.query(rot(p, AX12[0], AX12[1], -a))[0] for a in ANG], axis=0)


def swept_leg(p, side):
    """Full-turn swept distance about the hip-yaw axis (conservative: the real range is -25..30 deg)."""
    keys = LEG_L if side == 'shell_left' else LEG_R
    q = np.vstack([C[k] for k in keys if k in C]); c = YAW_AX[side]
    rq, zq = np.linalg.norm(q[:, :2] - c, axis=1), q[:, 2]
    tr = cKDTree(np.column_stack([rq, zq]))
    return tr.query(np.column_stack([np.linalg.norm(p[:, :2] - c, axis=1), p[:, 2]]))[0]


def classify_dist(p, side):
    out = {}
    for k in SERVO + BOARD + PRINTED:
        if k in T:
            out[k] = T[k].query(p)[0]
    out['moving:neck(ID12 swept)'] = swept_neck(p)
    out['moving:leg(hip yaw swept 360)'] = swept_leg(p, side)
    for cid, c in cables.items():
        q = cable_pts(cid)
        if np.all(q.max(0) < p.min(0) - 40) or np.all(q.min(0) > p.max(0) + 40):
            continue
        out['cable:' + cid] = cKDTree(q).query(p)[0] - float(c.get('radius') or 0.9)
    for s in guide['screws']:
        q, r, head, hr = screw_pts(s)
        if np.linalg.norm(head - p.mean(0)) > 60:
            continue
        d = np.minimum(cKDTree(q).query(p)[0] - r, np.linalg.norm(p - head, axis=1) - hr)
        out['screw:' + s['id'] + ' ' + s['spec']] = d
    return out


def cls(name):
    if name.startswith('moving'):
        return 'moving'
    if name.startswith('screw') or name in SERVO or name in BOARD:
        return 'metal'
    if name.startswith('cable'):
        return 'cable'
    return 'printed'


# ---------------------------------------------------------------- inner face grid of each shell (rays along y)
XS, ZS = np.arange(-46.0, 21.0, 1.0), np.arange(0.0, 43.0, 1.0)
res = {'units': 'mm', 'frame': 'robot: x forward, y left, z up', 'neck_pitch_collision_free_deg': [pitch_lo, pitch_hi],
       'neck_pitch_model_range_deg': model_range, 'limits': {'moving_min': MOVE_MIN, 'metal_board_min': METAL_MIN},
       'shells': {}}
grids = {}
for side, sh in shells.items():
    sgn = 1 if side == 'shell_left' else -1
    ri = trimesh.ray.ray_triangle.RayMeshIntersector(sh)
    X, Z = np.meshgrid(XS, ZS, indexing='ij')
    O = np.column_stack([X.ravel(), np.full(X.size, sgn * 60.0), Z.ravel()])
    D = np.tile([0, -sgn, 0.0], (len(O), 1))
    outer = np.full(len(O), np.nan); inner = np.full(len(O), np.nan)
    for c0 in range(0, len(O), 400):
        loc, iray, _ = ri.intersects_location(O[c0:c0 + 400], D[c0:c0 + 400], multiple_hits=True)
        for r in np.unique(iray):
            ys = np.sort(loc[iray == r, 1])[::-1] if sgn > 0 else np.sort(loc[iray == r, 1])
            if len(ys) >= 2 and abs(ys[0] - ys[1]) <= 5.0:
                outer[c0 + r], inner[c0 + r] = ys[0], ys[1]
    outer, inner = outer.reshape(X.shape), inner.reshape(X.shape)
    th = np.abs(outer - inner)
    valid = ~np.isnan(inner)
    P = np.column_stack([X[valid], inner[valid] - sgn * 0.1, Z[valid]])     # 0.1 mm into the cavity: copper face
    dist = classify_dist(P, side)
    # free space behind the wall: march along -sgn*y from the inner face until a solid, cable or the other wall
    other = [k for k in shells if k != side][0]
    own_free = cKDTree(np.vstack([C[k] for k in SERVO + BOARD + PRINTED + LEG_L + LEG_R if k in C] +
                                 [trimesh.sample.sample_surface_even(shells[other], 60000, seed=3)[0]]))
    blockers = [own_free, cKDTree(np.vstack([cable_pts(c) for c in cables]))]
    depth = np.full(len(P), 40.0); alive = np.ones(len(P), bool)
    for t in np.arange(0.5, 40.0, 0.25):
        q = P - np.array([0, sgn * t, 0])
        dmin = np.minimum(own_free.query(q)[0], blockers[1].query(q)[0] - 0.9)
        newly = alive & (dmin < 0.4)
        depth[newly] = t; alive &= ~newly
        if not alive.any():
            break
    grid = {k: np.full(X.shape, np.nan) for k in list(dist) + ['depth', 'th']}
    for k, v in dist.items():
        grid[k][valid] = v
    grid['depth'][valid] = depth; grid['th'] = np.where(valid, th, np.nan)
    grids[side] = (X, Z, inner, valid, grid)
    print(side, 'nodes', valid.sum(), flush=True)

_dump = {}
for side, (X, Z, inner, valid, grid) in grids.items():
    for c in ('moving', 'metal', 'cable', 'printed'):
        _dump[f'{side}_{c}'] = np.nanmin(np.stack([grid[k] for k in grid if k not in ('depth', 'th') and cls(k) == c]), axis=0)
    _dump[f'{side}_inner'] = inner; _dump[f'{side}_th'] = grid['th']; _dump[f'{side}_depth'] = grid['depth']
    _dump[f'{side}_metalname'] = np.array([k for k in grid if k not in ('depth', 'th') and cls(k) == 'metal'])
    _dump[f'{side}_metalarg'] = np.nanargmin(np.stack([np.nan_to_num(grid[k], nan=1e9) for k in grid if k not in ('depth', 'th') and cls(k) == 'metal']), axis=0)
np.savez('/private/tmp/claude-501/-Users-xiangzheng-code-robotics/62d918d5-0929-4cc8-9e55-8fc983e284e8/scratchpad/diag.npz', XS=XS, ZS=ZS, **_dump)
# ---------------------------------------------------------------- 18 x 18 window search


def window_min(a, s=PAD + 1):
    b = np.where(np.isnan(a), 1e9, a)          # missing nodes (ray grazing a mesh edge) do not count
    return ndimage.minimum_filter(b, size=s, mode='constant', cval=-1e9, origin=-(s // 2))


def window_max(a, s=PAD + 1):
    b = np.where(np.isnan(a), -1e9, a)
    return ndimage.maximum_filter(b, size=s, mode='constant', cval=1e9, origin=-(s // 2))


for side, (X, Z, inner, valid, grid) in grids.items():
    keys = [k for k in grid if k not in ('depth', 'th')]
    W = {k: window_min(grid[k]) for k in keys}
    flat = window_max(np.where(valid, inner, np.nan)) - (-window_max(-np.where(valid, inner, np.nan)))
    thmax = window_max(grid['th'])
    vfrac = ndimage.uniform_filter(valid.astype(float), size=PAD + 1, mode='constant', cval=0.0, origin=-((PAD + 1) // 2))
    holes = ndimage.minimum_filter((~valid).astype(int), size=2, mode='constant', cval=0)
    big_hole = window_max(np.where(holes > 0, 1.0, 0.0)) > 0     # a 2 x 2 block of missing nodes = a real gap (rib, boss)
    ok = (vfrac >= 0.97) & ~big_hole & (flat <= 3.0) & (thmax <= 4.0)
    by = {c: np.min([W[k] for k in keys if cls(k) == c], axis=0) for c in ('moving', 'metal', 'cable', 'printed')}
    margin = np.minimum(by['moving'] - MOVE_MIN, by['metal'] - METAL_MIN)
    feas = ok & (margin >= 0)
    print(side, 'windows mostly-valid', int(((vfrac >= 0.97) & ~big_hole).sum()), 'ok', int(ok.sum()), 'margin>=0', int((margin >= 0).sum()), 'feasible', int(feas.sum()), flush=True)
    # Score: margin first (capped at 5 mm), then height nearest the flank middle (a hand stroking the side)
    cz = Z + PAD / 2
    score = np.where(feas, np.minimum(margin, 5.0) - 0.05 * np.abs(cz - 21) - 0.5 * flat, -1e9)
    assert feas.any(), side + ': no 18 x 18 window meets the limits'
    i, j = np.unravel_index(np.argmax(score), score.shape)
    x0, z0 = X[i, j], Z[i, j]
    sl = (slice(i, i + PAD + 1), slice(j, j + PAD + 1))
    near = sorted(((float(np.nanmin(grid[k][sl])), k) for k in keys), key=lambda t: t[0])
    feas_cnt = int(feas.sum())
    # middle of the flank (where most of a palm lands), for comparison
    mi, mj = int(np.argmin(np.abs(XS - (-12 - PAD / 2)))), int(np.argmin(np.abs(ZS - (21 - PAD / 2))))
    msl = (slice(mi, mi + PAD + 1), slice(mj, mj + PAD + 1))
    mid = sorted(((float(np.nanmin(grid[k][msl])), k) for k in keys), key=lambda t: t[0])[:4]
    feas_x = X[feas] + PAD / 2; feas_z = Z[feas] + PAD / 2
    res['shells'][side] = {
        'pad': {'x': [float(x0), float(x0 + PAD)], 'z': [float(z0), float(z0 + PAD)],
                'inner_face_y': [round(float(np.nanmin(inner[sl])), 2), round(float(np.nanmax(inner[sl])), 2)],
                'centre': [float(x0 + PAD / 2), round(float(np.nanmean(inner[sl])), 1), float(z0 + PAD / 2)]},
        'wall_thickness': {'min': round(float(np.nanmin(grid['th'][sl])), 2), 'max': round(float(np.nanmax(grid['th'][sl])), 2),
                           'median': round(float(np.nanmedian(grid['th'][sl])), 2)},
        'free_space_behind_wall': {'min': round(float(np.nanmin(grid['depth'][sl])), 1),
                                   'p10': round(float(np.nanpercentile(grid['depth'][sl], 10)), 1),
                                   'median': round(float(np.nanmedian(grid['depth'][sl])), 1)},
        'nearest': [{'part': k, 'class': cls(k), 'mm': round(d, 1)} for d, k in near[:14]],
        'by_class_min': {c: round(float(np.min([np.nanmin(grid[k][sl]) for k in keys if cls(k) == c])), 1)
                         for c in ('moving', 'metal', 'cable', 'printed')},
        'feasible_window_count': feas_cnt,
        'feasible_centre_range': {'x': [float(feas_x.min()), float(feas_x.max())], 'z': [float(feas_z.min()), float(feas_z.max())]}
        if feas_cnt else None,
        'mid_flank_window_x_-21_-3_z_12_30': [{'part': k, 'mm': round(d, 1)} for d, k in mid],
    }
    print(side, json.dumps(res['shells'][side]['pad']), res['shells'][side]['by_class_min'], flush=True)

# ---------------------------------------------------------------- wire route: XIAO D9 / D10 -> bundle -> pad
tr = json.loads((TOUCH / 'touch_routes.json').read_text())
Rb, org = np.array(tr['board_axes']), np.array(tr['board_origin'])
Tb = np.eye(4); Tb[:3, :3] = Rb; Tb[:3, 3] = org
PCB = (21.0, 17.8, 1.2)


def pin_xyz(i, side=-1):
    x = -PCB[0] / 2 + 2.88 + i * 2.54
    y = side * (PCB[1] / 2 - 0.9)
    return (Tb @ [x, y, PCB[2] + 0.7, 1])[:3], (Tb @ [x, y + side * 3.5, PCB[2] + 0.7, 1])[:3]


XPIN = {'D10': 3, 'D9': 4}
bpath = np.array(cables['imu']['path'], float)
bcum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(bpath, axis=0), axis=1))])


def arc(p):
    """Arc length along the bundle (imu path) of the nearest point to p."""
    best = (1e9, 0)
    for a, b, s in zip(bpath[:-1], bpath[1:], bcum[:-1]):
        d = b - a; t = np.clip((p - a) @ d / (d @ d), 0, 1); q = a + t * d
        e = np.linalg.norm(p - q)
        if e < best[0]:
            best = (e, s + t * np.linalg.norm(d))
    return best[1], best[0]


def astar(free, LO, G, cost, a, b_cells):
    shape = free.shape
    NB = [d for d in np.argwhere(np.ones((3, 3, 3), bool)) - 1 if np.any(d)]
    NBL = [np.linalg.norm(d) for d in NB]
    bset = set(b_cells); bb = np.array(b_cells).mean(0)
    openq = [(0, 0, a)]; g = {a: 0}; par = {a: None}; end = None
    while openq:
        _, gc, u = heapq.heappop(openq)
        if u in bset:
            end = u; break
        if gc > g[u]:
            continue
        for d, l in zip(NB, NBL):
            v = (u[0] + d[0], u[1] + d[1], u[2] + d[2])
            if not (0 <= v[0] < shape[0] and 0 <= v[1] < shape[1] and 0 <= v[2] < shape[2]) or not free[v]:
                continue
            ng = gc + l * cost[v]
            if ng < g.get(v, 1e18):
                g[v] = ng; par[v] = u
                heapq.heappush(openq, (ng + 0.5 * np.linalg.norm(np.array(v) - bb), ng, v))
    assert end is not None, 'no path'
    path = [end]
    while par[path[-1]] is not None:
        path.append(par[path[-1]])
    pts = LO + (np.array(path[::-1]) + 0.5) * G
    return pts


def plen(p):
    return float(np.sum(np.linalg.norm(np.diff(p, axis=0), axis=1)))


def smooth(p, k=3):
    if len(p) < 2 * k + 1:
        return p
    q = p.copy()
    for i in range(k, len(p) - k):
        q[i] = p[i - k:i + k + 1].mean(0)
    return q


# Head grid (analysis/head_space.py) with the XIAO, its tape and the five head pads stamped in, as build_touch_geometry does.
hs = np.load(TOUCH / 'analysis' / 'head_space.npz')
hocc, HLO, HG = hs['occ'].copy(), hs['lo'], float(hs['p'])
for f in ['touch_xiao', 'touch_xiao_tape', 'touch_pad_l1', 'touch_pad_r1', 'touch_pad_l2', 'touch_pad_r2', 'touch_pad_m']:
    m = trimesh.load(TOUCH / 'world' / f'{f}.stl')
    lo, hi = np.floor((m.bounds[0] - HLO) / HG).astype(int) - 1, np.ceil((m.bounds[1] - HLO) / HG).astype(int) + 1
    ax = [HLO[d] + (np.arange(lo[d], hi[d]) + 0.5) * HG for d in range(3)]
    Q = np.stack(np.meshgrid(*ax, indexing='ij'), -1).reshape(-1, 3)
    hocc[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]] |= (trimesh.proximity.ProximityQuery(m).signed_distance(Q) > -0.5 * HG).reshape([len(a) for a in ax])
hdist = ndimage.distance_transform_edt(~hocc) * HG
hfree = hdist >= 1.75
hfree[:, :, :int(np.ceil((113.0 - HLO[2]) / HG))] = False          # rides on the cap, above the cap rim with 2 mm spare
lab, _ = ndimage.label(hfree)
hfree = lab == lab[tuple(np.floor((np.array([20, 0, 135]) - HLO) / HG).astype(int))]
hcost = np.where(hdist < 2.8, 1.0, 1.6)


def hcell(p):
    return tuple(np.floor((np.asarray(p) - HLO) / HG).astype(int))


def nearest(free, LO, G, p, r=6):
    i = np.array(np.floor((np.asarray(p) - LO) / G).astype(int)); best, bd = None, 1e9
    for d in np.argwhere(np.ones((2 * r + 1,) * 3, bool)) - r:
        q = i + d
        if np.all(q >= 0) and np.all(q < free.shape) and free[tuple(q)] and np.linalg.norm(d) < bd:
            best, bd = tuple(q), np.linalg.norm(d)
    assert best is not None, p
    return best


# Inline plug on the cap seam: in the bundle stretch behind the A7Z, from the head clip window up to the cap clip.
# Candidates: the two straight bundle segments there; check a mated plug envelope against the head solids.
PLUGS = {'dupont_1x2_mated': (28.0, 5.1, 2.6), 'jst_zh_2p_mated_wire_to_wire': (12.0, 4.5, 3.5), 'jst_xh_2p_mated': (16.0, 5.8, 6.0)}
plug_fit = {}
seg_opts = [(np.array([49.6, -17.5, 117.9]), np.array([49.5, -7.5, 137.0])),
            (np.array([49.5, -7.5, 137.0]), np.array([49.5, 9.3, 137.4]))]
occ_tree = cKDTree(HLO + (np.argwhere(hocc) + 0.5) * HG)
other_head_cables = np.vstack([cable_pts(c) for c in cables if c not in BUNDLE and np.array(cables[c]['path'])[:, 2].max() > 100])
oc_tree = cKDTree(other_head_cables)
for name, (L, w, h) in PLUGS.items():
    best = None
    for a, b in seg_opts:
        d = (b - a) / np.linalg.norm(b - a); seg_len = np.linalg.norm(b - a)
        for t in np.arange(0, max(0.01, seg_len - L) + 0.01, 1.0):
            for side_off in ([0, 0, 0],):
                # plug lies beside the bundle: offset 2.6 mm from the bundle centreline, towards the free side
                for o in (np.cross(d, [1, 0, 0]), -np.cross(d, [1, 0, 0]), np.array([-1.0, 0, 0]), np.array([1.0, 0, 0])):
                    o = o / np.linalg.norm(o)
                    c0 = a + d * (t + L / 2) + o * (2.0 + h / 2)
                    ex = np.cross(d, o)
                    g = np.stack(np.meshgrid(np.linspace(-L / 2, L / 2, 15), np.linspace(-w / 2, w / 2, 4), np.linspace(-h / 2, h / 2, 3), indexing='ij'), -1).reshape(-1, 3)
                    pts = c0 + g[:, :1] * d + g[:, 1:2] * ex + g[:, 2:3] * o
                    clr = min(occ_tree.query(pts)[0].min() - 0.5 * HG, oc_tree.query(pts)[0].min() - 0.65)
                    if best is None or clr > best[0]:
                        best = (clr, c0.round(1).tolist(), d.round(3).tolist(), o.round(3).tolist(), float(t))
    plug_fit[name] = {'envelope_LxWxH': [L, w, h], 'best_clearance_mm': round(best[0], 1), 'centre': best[1],
                      'axis': best[2], 'offset_dir': best[3], 'fits': bool(best[0] >= 0.0)}
print('plug fit', plug_fit, flush=True)
PLUG_PT = np.array([49.5, -12.5, 127.5])          # middle of the first segment (head-clip window to the bend behind the A7Z)

head_routes = {}
for pin, idx in XPIN.items():
    end, out = pin_xyz(idx)
    goal = [nearest(hfree, HLO, HG, PLUG_PT)]
    p = astar(hfree, HLO, HG, hcost, nearest(hfree, HLO, HG, out), goal)
    p = np.vstack([end, out, smooth(p)[1:-1], PLUG_PT])
    head_routes[pin] = p
    print('head route', pin, round(plen(p), 1), flush=True)

# Torso grid: shells, every torso solid, the ID12 group swept over its free range (kept 4 mm away), cables.
TLO, TG = np.array([-50.0, -36.0, -4.0]), 1.0
tshape = np.ceil((np.array([40.0, 36.0, 50.0]) - TLO) / TG).astype(int)


def stamp(pts, grid):
    i = np.floor((pts - TLO) / TG).astype(int)
    ok = np.all((i >= 0) & (i < tshape), axis=1)
    grid[tuple(i[ok].T)] = True


tocc = np.zeros(tshape, bool)
stamp(static_near, tocc)
for k in LEG_L + LEG_R:
    if k in C:
        stamp(C[k], tocc)
for cid in cables:
    if cid not in BUNDLE:
        stamp(cable_pts(cid), tocc)
# Routing keeps 4 mm from the ID12 body and its links over the swept range; the parts above (ID11 and the head) only
# come down to the torso top at extreme back pitch, where the existing bundle lies too, so the lead inherits the bundle's
# clearance there (checked separately in coupling_along_bundle).
tneck = np.zeros(tshape, bool)
low_neck = np.vstack([C[k] for k in ('motor12', 'idler_cap12', 'neck_link_a', 'neck_link_b') if k in C])
for a in ANG:
    stamp(rot(low_neck[::3], AX12[0], AX12[1], a), tneck)
tdist = ndimage.distance_transform_edt(~tocc) * TG
ndist = ndimage.distance_transform_edt(~tneck) * TG
tfree = (tdist >= 1.75) & (ndist >= MOVE_MIN + 0.65)
# inside the torso: shell wall beyond the voxel at +y and -y (any x), or above the torso top (bundle level)
shell_occ = np.zeros(tshape, bool)
for m in shells.values():
    stamp(trimesh.sample.sample_surface_even(m, 120000, seed=5)[0], shell_occ)
inside = np.maximum.accumulate(shell_occ, axis=1) & np.maximum.accumulate(shell_occ[:, ::-1], axis=1)[:, ::-1]
zc = TLO[2] + (np.arange(tshape[2]) + 0.5) * TG
inside[:, :, zc > 47] = False
inside[:, :, zc < 2] = False
tfree &= inside | (zc[None, None, :] > 40)
tfree[:, :, zc > 47] = False
tcost = np.where(tdist < 2.8, 1.0, 1.6)
# Join targets: the bundle polyline on the torso top, from the pack notch to the torso clip.
s0, s1 = arc(np.array([-14.1, 1.1, 42.5]))[0], arc(np.array([22.6, -23.9, 36.0]))[0]
ss = np.arange(s0, s1, 0.5)
join_pts = np.array([np.interp(s, bcum, bpath[:, 0]) for s in ss]), np.array([np.interp(s, bcum, bpath[:, 1]) for s in ss]), np.array([np.interp(s, bcum, bpath[:, 2]) for s in ss])
join_pts = np.column_stack(join_pts)
routes = {}
for side, info in res['shells'].items():
    sgn = 1 if side == 'shell_left' else -1
    x0, x1 = info['pad']['x']; z0, z1 = info['pad']['z']; yy = info['pad']['inner_face_y']
    y_in = (max(yy) if sgn < 0 else min(yy)) - sgn * 1.0
    start = np.array([x1, y_in, z1])                       # top front corner of the pad, where the lead is soldered
    goals = []
    for q in join_pts[::4]:
        try:
            goals.append(nearest(tfree, TLO, TG, q, r=3))
        except AssertionError:
            pass
    goals = sorted(set(goals))
    used = None
    for clr in (1.75, 1.25):
        tf = (tdist >= clr) & (ndist >= MOVE_MIN + 0.65) & (inside | (zc[None, None, :] > 40))
        tf[:, :, zc > 47] = False
        goals = []
        for q in join_pts[::4]:
            try:
                goals.append(nearest(tf, TLO, TG, q, r=3))
            except AssertionError:
                pass
        a0 = nearest(tf, TLO, TG, start)
        labs, _ = ndimage.label(tf)
        comp = np.argwhere(labs == labs[a0])
        print(side, 'clearance', clr, 'start comp bbox', (TLO + comp.min(0) * TG).round(0).tolist(), (TLO + comp.max(0) * TG).round(0).tolist(),
              'goal labels', sorted({int(labs[g]) for g in goals})[:6], 'start label', int(labs[a0]), flush=True)
        if labs[a0] in {labs[g] for g in goals}:
            p = astar(tf, TLO, TG, tcost, a0, sorted(set(goals))); used = clr
            break
    assert used is not None, side + ': no torso route'
    p = np.vstack([start, smooth(p)])
    s_join, _ = arc(p[-1])
    # where the lead leaves the shell: last point inside the shell envelope
    ii = np.floor((p - TLO) / TG).astype(int); ii = np.clip(ii, 0, tshape - 1)
    ins = inside[tuple(ii.T)] & (p[:, 2] < 41.5)
    exit_pt = p[np.where(ins)[0].max()] if ins.any() else p[0]
    s_plug = arc(PLUG_PT)[0]
    L_t, L_b = plen(p), float(s_plug - s_join)
    routes[side] = {'grid_clearance_mm': used, 'torso_path': p.round(2).tolist(), 'join_point': p[-1].round(1).tolist(), 'shell_exit_point': exit_pt.round(1).tolist(),
                    'torso_mm': round(L_t, 1), 'bundle_mm': round(L_b, 1)}
    print('torso route', side, round(L_t, 1), 'bundle', round(L_b, 1), flush=True)

pin_of = {'shell_left': 'D9', 'shell_right': 'D10'}
res['routes'] = {}
for side, r in routes.items():
    hp = head_routes[pin_of[side]]
    tot = plen(hp) + r['bundle_mm'] + r['torso_mm']
    res['routes'][side] = {'xiao_pin': pin_of[side], 'head_mm_xiao_to_cap_plug': round(plen(hp), 1),
                           'bundle_mm_cap_plug_to_join': r['bundle_mm'], 'torso_mm_join_to_pad': r['torso_mm'],
                           'total_mm': round(tot, 1), 'cut_mm_plus_15': int(5 * np.ceil((tot + 15) / 5)),
                           'xiao_side_lead_mm': round(plen(hp), 1), 'torso_side_lead_mm': round(r['bundle_mm'] + r['torso_mm'], 1),
                           'join_point': r['join_point'], 'shell_exit_point': r['shell_exit_point'],
                           'head_path': hp.round(2).tolist(), 'torso_path': r['torso_path']}
res['cap_plug'] = {'point': PLUG_PT.tolist(), 'bundle_arc_mm_from_imu_socket': round(arc(PLUG_PT)[0], 1), 'fit': plug_fit}

# ---------------------------------------------------------------- coupling: what the lead passes along the bundle
segs = {'torso top (pack notch -> torso clip)': (s0, s1),
        'torso clip -> bracket clip (bends with ID12 neck pitch)': (arc(np.array([30.0, -23.9, 37.3]))[0], arc(np.array([26.0, -21.1, 85.2]))[0]),
        'bracket clip -> head clip (bends with ID11 head pitch, ID13 yaw, ID14 roll)': (arc(np.array([26.0, -21.1, 85.2]))[0], arc(np.array([49.6, -21.7, 117.9]))[0]),
        'head clip -> cap plug (rides with the head; jaw ID15 alongside)': (arc(np.array([49.6, -21.7, 117.9]))[0], arc(PLUG_PT)[0])}
hd = {k: cloud(k, 1 / 0.6) for k in ['motor11', 'motor12', 'motor13', 'motor14', 'motor15', 'motor10', 'motor5', 'jaw_support', 'head_yaw_link', 'pi'] if k in man}
coup = {}
for name, (a, b) in segs.items():
    ss = np.arange(a, b, 0.5)
    q = np.column_stack([np.interp(ss, bcum, bpath[:, d]) for d in range(3)])
    row = {'length_mm': round(b - a, 1)}
    for k, v in hd.items():
        row[k] = round(float(cKDTree(v).query(q)[0].min()) - 0.65, 1)
    for cid in ['dxl-n12', 'dxl-12-11', 'dxl-11-13', 'dxl-13-14', 'dxl-14-15', 'pw-7v', 'dxl-l10', 'dxl-r5']:
        row['cable:' + cid] = round(float(cKDTree(cable_pts(cid)).query(q)[0].min()) - 0.65 - float(cables[cid].get('radius') or 0.9), 1)
    coup[name] = row
res['coupling_along_bundle'] = coup

# ---------------------------------------------------------------- option B: a XIAO SAMD21 (21 x 17.5 x 3.5, wires flat: 5 mm) in the torso
grown = ndimage.binary_dilation(tocc, iterations=1) | ndimage.binary_dilation(tneck, iterations=3) | shell_occ
tin = inside & ~grown
tin[:, :, zc > 41] = False
fits = []
for dims in {(21, 18, 5), (21, 5, 18), (5, 21, 18), (18, 21, 5), (18, 5, 21), (5, 18, 21)}:
    f = ndimage.binary_erosion(tin, structure=np.ones(dims, bool), border_value=0)
    if f.any():
        pts = TLO + (np.argwhere(f) + 0.5) * TG
        fits.append({'box_xyz': list(dims), 'centres': int(len(pts)), 'centre_mean': pts.mean(0).round(1).tolist()})
largest = []
for t_ax in range(3):
    best = None
    for L in range(24, 7, -1):
        for W in range(L, 7, -1):
            if best and L * W <= best[0] * best[1]:
                continue
            dims = [0, 0, 0]; o = [i for i in range(3) if i != t_ax]
            for dl in (0, 1):
                dims[t_ax] = 5; dims[o[0]], dims[o[1]] = (L, W) if dl == 0 else (W, L)
                f = ndimage.binary_erosion(tin, structure=np.ones(dims, bool), border_value=0)
                if f.any():
                    pts = TLO + (np.argwhere(f) + 0.5) * TG
                    best = (L, W, list(dims), pts.mean(0).round(1).tolist(), [pts.min(0).round(0).tolist(), pts.max(0).round(0).tolist()])
                    break
    largest.append({'thin_axis': 'xyz'[t_ax], 'LxW': best[:2] if best else None, 'box_xyz': best[2] if best else None,
                    'centre_mean': best[3] if best else None, 'centre_range': best[4] if best else None})
res['torso_board_fit'] = {'xiao_21x18x5_fits': fits, 'largest_5mm_thick_box': largest,
                          'rule': 'solids grown 1 mm, ID12 group swept and grown 3 mm, inside the shells, below z 41'}
# BNO085 lower STEMMA QT socket: room below it for a plug
ib = C['imu_board']; low = ib[ib[:, 2] < 10]
res['bno085_lower_socket'] = {'board_bottom_z': round(float(ib[:, 2].min()), 1),
                              'base_plate_top_z': round(float(C['torso_base'][:, 2].max()), 1),
                              'gap_mm': round(float(ib[:, 2].min() - C['torso_base'][:, 2].max()), 1)}
op = C['openrb_board']
res['openrb'] = {'bounds': [op.min(0).round(1).tolist(), op.max(0).round(1).tolist()],
                 'dxl_plus_y_port_cable_start': cables['dxl-n12']['path'][0]}
tp_tree = cKDTree(np.vstack([static_near] + [cable_pts(c) for c in cables if c not in BUNDLE]))
low_tree = cKDTree(low_neck)
tp = {}
for name, (L, w, h) in PLUGS.items():
    best = None
    jp = np.mean([np.array(r['join_point']) for r in routes.values()], axis=0)
    for s_c in np.arange(s0 - 10, s0 + 40, 1.0):
        c = np.array([np.interp(s_c, bcum, bpath[:, d]) for d in range(3)])
        d_ = np.array([np.interp(s_c + 1, bcum, bpath[:, d]) for d in range(3)]) - c; d_ /= np.linalg.norm(d_)
        for o in (np.array([0, 0, 1.0]), np.cross(d_, [0, 0, 1.0]), -np.cross(d_, [0, 0, 1.0])):
            o = o / np.linalg.norm(o); c0 = c + o * (2.0 + h / 2); ex = np.cross(d_, o)
            g = np.stack(np.meshgrid(np.linspace(-L / 2, L / 2, 15), np.linspace(-w / 2, w / 2, 4), np.linspace(-h / 2, h / 2, 3), indexing='ij'), -1).reshape(-1, 3)
            pts = c0 + g[:, :1] * d_ + g[:, 1:2] * ex + g[:, 2:3] * o
            clr = tp_tree.query(pts)[0].min()
            mv = min(low_tree.query(rot(pts, AX12[0], AX12[1], -a))[0].min() for a in ANG[::3])
            sc = min(clr, mv - MOVE_MIN)
            if best is None or sc > best[0]:
                best = (sc, round(float(clr), 1), round(float(mv), 1), c0.round(1).tolist(), round(float(np.linalg.norm(c0 - jp)), 1))
    tp[name] = {'envelope_LxWxH': [L, w, h], 'clearance_to_solids_and_other_cables_mm': best[1],
                'clearance_to_ID12_group_swept_mm': best[2], 'centre': best[3], 'distance_from_join_points_mm': best[4]}
res['torso_top_plug'] = tp
pads_head = {f: cKDTree(trimesh.load(TOUCH / 'world' / f'touch_pad_{f}.stl').vertices) for f in ('l1', 'r1', 'l2', 'r2', 'm')}
res['head_route_to_head_pads_mm'] = {pin: {f: round(float(t.query(smooth_pts)[0].min()), 1) for f, t in pads_head.items()}
                                     for pin, smooth_pts in ((p_, np.concatenate([np.linspace(a, b, 10) for a, b in zip(hp[:-1], hp[1:])])) for p_, hp in head_routes.items())}
(HERE / 'results.json').write_text(json.dumps(res, indent=1))
np.savez_compressed(Path('/private/tmp/claude-501/-Users-xiangzheng-code-robotics/62d918d5-0929-4cc8-9e55-8fc983e284e8/scratchpad/torso_grids.npz'),
                    **{f'{s}_{k}': v for s, (X, Z, inner, valid, g) in grids.items() for k, v in [('X', X), ('Z', Z), ('inner', inner), ('depth', g['depth']), ('th', g['th'])]})
print('done', flush=True)


# ---------------------------------------------------------------- analytic signal estimate (inference), seams, PLAN notes
import math
r = json.loads((HERE / 'results.json').read_text())
e0 = 8.854e-12


def mutual(s, a, er):
    return math.pi * e0 * er / math.acosh(s / (2 * a))          # F/m, two parallel wires


def plane(h, a, er):
    return 2 * math.pi * e0 * er / math.acosh(h / a)            # F/m, wire over a plane


a, s_, er = 0.2e-3, 1.3e-3, 2.0
cm = mutual(s_, a, er)
bund = r['routes']['shell_left']['bundle_mm_cap_plug_to_join'] / 1000
cp = {'bundle_3_neighbours_pF': round(3 * cm * bund * 1e12, 1),
      'xiao_side_in_cap_1_neighbour_pF': round(cm * r['routes']['shell_left']['head_mm_xiao_to_cap_plug'] / 1000 * 1e12, 1),
      'torso_side_pF': round(cm * r['routes']['shell_left']['torso_mm_join_to_pad'] / 1000 * 1e12, 1),
      'two_inline_plugs_pF': '1-2', 'pad_to_surroundings_pF': '~0.5'}
total = cp['bundle_3_neighbours_pF'] + cp['xiao_side_in_cap_1_neighbour_pF'] + cp['torso_side_pF'] + 1.5 + 0.5


def touch(A, d, er_=3.0):
    return e0 * er_ * A / d * 1e12


r['signal_estimate'] = {
    'status': 'inference: analytic estimates, not measured',
    'assumptions': {'conductor_radius_mm': 0.2, 'insulated_wire_diameter_mm': 1.3, 'effective_permittivity_bundle': er,
                    'PLA_relative_permittivity': 3.0, 'fingertip_contact_mm2': 100, 'palm_over_pad_mm2': 324},
    'mutual_capacitance_per_adjacent_wire_pF_per_m': round(cm * 1e12, 1),
    'lead_parasitic_breakdown': cp, 'lead_parasitic_total_pF': round(total, 1), 'lead_parasitic_range_pF': [15, 35],
    'head_pad_lead_parasitic_pF_for_comparison': '3-5 (31-71 mm leads taped on the cap wall)',
    'touch_capacitance_pF': {'fingertip_through_2.2mm_shell': round(touch(100e-6, 2.2e-3), 2),
                             'palm_over_whole_pad_2.2mm': round(touch(324e-6, 2.2e-3), 2),
                             'fingertip_through_1.7mm_cap': round(touch(100e-6, 1.7e-3), 2)},
    'change_rate_percent': {'torso_pad_fingertip': round(100 * touch(100e-6, 2.2e-3) / total, 1),
                            'torso_pad_palm': round(100 * touch(324e-6, 2.2e-3) / total, 1),
                            'head_pad_fingertip_at_4pF': round(100 * touch(100e-6, 1.7e-3) / 4, 1),
                            'torso_reader_option_fingertip_at_3pF': round(100 * touch(100e-6, 2.2e-3) / 3, 1)},
    'espressif_reference': 'esp-iot-solution touch_sensor_design_en.md: trace length should not exceed 300 mm; keep 4 mm from '
                           'high-frequency digital lines, do not run parallel to them; 5 pF on 20 pF = 25 % change, 100 pF = 5 %',
    'motion_coupling_example_pF': {'20mm_of_lead_moving_2_to_5mm_from_a_servo_case': round((plane(2.0e-3, a, 1.5) - plane(5.0e-3, a, 1.5)) * 0.02e12, 2)},
    'digital_lines_alongside_mm': round(bund * 1000, 0),
    'injected_charge_per_3.3V_edge_from_one_adjacent_signal_pC': round(cm * bund * 3.3 * 1e12, 1),
}
r['seams'] = [
    {'seam': 'torso shells (each screwed on, slides off sideways 40 mm)', 'plug': 'one 2-pin inline plug on the torso top beside the bundle, where both pad leads reach it',
     'space': r['torso_top_plug'], 'pad_side_lead_mm': {k: v['torso_mm_join_to_pad'] for k, v in r['routes'].items()}},
    {'seam': 'neck (ID12, ID11, ID13, ID14 move)', 'plug': 'none; two stranded wires ride in the 8-wire bundle through the torso, bracket and head clips',
     'clip_channel_mm': 4.8, 'densest_packing_side_mm': {'8_wires_dia_1.3': 3.81, '10_wires_dia_1.3': 4.39},
     'note': 'inference from circle-packing values (side/diameter 2.93 for 8, 3.37 for 10); spiral wrap does not fit inside the clip with 10 wires'},
    {'seam': 'head cap (lifts about 40 mm with the A7Z, the XIAO and the 8 bundle plugs)', 'plug': 'one 2-pin inline plug in the bundle stretch behind the A7Z, unplugged together with the 8 header plugs',
     'space': r['cap_plug']},
]
r['plan_contradictions'] = [
    'PLAN.md "Five pads leave four spare XIAO touch inputs": the XIAO ESP32-S3 has nine touch inputs (D0-D5, D8-D10); five pads plus D4/D5 for I2C leave two (D9, D10).',
    'PLAN.md and the guide touch step cut pads from 6 mm strips ("two or three"); the tape on hand is about 5 mm, so an 18 mm pad needs four strips overlapping about 0.7 mm.',
    'PLAN.md "Open decisions" says "the six head pads above"; the design has five (N dropped).',
    'PLAN.md describes sensing through a 1.7 mm wall; the torso shell wall at the pads is 2.2 mm (measured median), so a torso pad gives about 1.7/2.2 = 77 % of the head-pad signal per area before the longer lead is counted.',
    'PLAN.md "body back (the shells; wires would join the neck route)": the measured lead is about 325 mm, over the 300 mm Espressif trace guidance, and it needs two inline plugs (torso top and cap).',
]
(HERE / 'results.json').write_text(json.dumps(r, indent=1))
print('signal block written', flush=True)
