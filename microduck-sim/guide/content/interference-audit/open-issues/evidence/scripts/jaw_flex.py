"""Jaw flex-fit evidence (read-only on guide sources).

1. Sections of jaw_frame and head_bottom (x-slices: YZ polygons; z-slices: XY polygons) saved for offline beam analysis.
2. Rigid insertion from below (guide jaw-bench approach [0,0,-30]) of jaw(+ring) vs head_bottom: overlap pieces per
   offset with their y-extent (= lateral spread needed at that spot), for jaw+ring and jaw alone.
3. Final-pose overlaps (baseline) and ring-from-inside order.
4. Print orientation: register community-4.stl (print frame) onto the robot-frame jaw_frame.
5. Jaw opening sweep (0..60 deg about the ring axis) against every head/electronics/camera/neck solid (V1.7 cache).
Writes jaw-flex.json incrementally.
"""
import json
import sys
import time

import numpy as np
import manifold3d as m3

sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit')
from ia_lib import load_solid, manifest, to_manifold  # noqa: E402

OUT = '/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/open-issues/jaw-flex.json'
res = {'started': time.strftime('%Y-%m-%d %H:%M:%S')}


def save():
    json.dump(res, open(OUT, 'w'), indent=1)


def log(*a):
    print(time.strftime('%H:%M:%S'), *a, flush=True)


def M(key):
    return to_manifold(*load_solid(key))


def bnds(man):
    b = man.bounding_box()
    return [list(map(lambda v: round(float(v), 3), b[:3])), list(map(lambda v: round(float(v), 3), b[3:]))]


def polys(cs, nd=3):
    return [np.round(np.asarray(p, float), nd).tolist() for p in cs.to_polygons()]


def moments(pl):
    """Area, centroid (u, v) and central second moments Iuu=int (u-ub)^2 dA, Ivv for a list of signed polygons."""
    A = Su = Sv = Iuu = Ivv = 0.0
    for p in pl:
        p = np.asarray(p, float)
        u, v = p[:, 0], p[:, 1]
        u1, v1 = np.roll(u, -1), np.roll(v, -1)
        cr = u * v1 - u1 * v
        A += cr.sum() / 2
        Su += ((u + u1) * cr).sum() / 6
        Sv += ((v + v1) * cr).sum() / 6
        Iuu += ((u * u + u * u1 + u1 * u1) * cr).sum() / 12
        Ivv += ((v * v + v * v1 + v1 * v1) * cr).sum() / 12
    if abs(A) < 1e-9:
        return None
    cu, cv = Su / A, Sv / A
    return {'area': A, 'cu': cu, 'cv': cv, 'Iuu': Iuu - A * cu * cu, 'Ivv': Ivv - A * cv * cv}


# x -> slicing axis: map (x, y, z) to (y, z, x) so slice(height=x0) gives polygons in (u=y, v=z)
TX = [[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0]]
# z slicing is native: polygons in (u=x, v=y)

log('load')
jaw, shell, ring, pad = M('jaw_frame'), M('head_bottom'), M('mouth_sliding_ring'), M('lower_pad')
res['bounds'] = {k: bnds(v) for k, v in (('jaw_frame', jaw), ('head_bottom', shell), ('mouth_sliding_ring', ring), ('lower_pad', pad))}
res['jawVolumeMm3'] = round(jaw.volume(), 2)
save()

# 1. sections -------------------------------------------------------------------------------------------
log('sections')
jx, sx = jaw.transform(TX), shell.transform(TX)
secX = []
for x0 in np.arange(17.25, 86.0, 0.5):
    cs = jx.slice(float(x0))
    comps = []
    for c in cs.decompose():
        pl = c.to_polygons()
        mo = moments(pl)
        if mo is None:
            continue
        b = c.bounds()
        allu = np.concatenate([np.asarray(p)[:, 0] for p in pl])
        comps.append({'y': [round(float(b[0]), 3), round(float(b[2]), 3)], 'z': [round(float(b[1]), 3), round(float(b[3]), 3)],
                      'area': round(mo['area'], 3), 'cy': round(mo['cu'], 3), 'cz': round(mo['cv'], 3),
                      'Iy_about_z': round(mo['Iuu'], 3), 'Iz_about_y': round(mo['Ivv'], 3),
                      'cMaxY': round(float(np.max(np.abs(allu - mo['cu']))), 3), 'polys': polys(c, 2)})
    secX.append({'x': round(float(x0), 3), 'parts': comps})
res['jawSectionsX'] = secX
shX = []
for x0 in np.arange(15.25, 70.0, 1.0):
    cs = sx.slice(float(x0))
    comps = []
    for c in cs.decompose():
        b = c.bounds()
        if max(abs(b[0]), abs(b[2])) < 28:
            continue
        comps.append({'y': [round(float(b[0]), 3), round(float(b[2]), 3)], 'z': [round(float(b[1]), 3), round(float(b[3]), 3)], 'polys': polys(c, 2)})
    shX.append({'x': round(float(x0), 3), 'parts': comps})
res['shellSectionsX'] = shX
secZ = []
for z0 in np.arange(98.5, 127.6, 1.0):
    cs = jaw.slice(float(z0))
    secZ.append({'z': round(float(z0), 3), 'polys': polys(cs, 2)})
res['jawSectionsZ'] = secZ
save()

# 2./3. insertion from below ---------------------------------------------------------------------------
log('insertion')


def overlap_pieces(mov, fixed, dz):
    inter = mov.translate([0, 0, float(dz)]) ^ fixed
    out = []
    if inter.is_empty():
        return out
    for p in inter.decompose():
        v = p.volume()
        if v < 0.05:
            continue
        b = p.bounding_box()
        out.append({'vol': round(v, 3), 'x': [round(b[0], 2), round(b[3], 2)], 'y': [round(b[1], 2), round(b[4], 2)],
                    'z': [round(b[2], 2), round(b[5], 2)], 'dy': round(b[4] - b[1], 3)})
    return out


ins = {}
for name, mov in (('jawPlusRing', jaw + ring), ('jawAlone', jaw), ('jawRingPad', jaw + ring + pad), ('jawPad', jaw + pad)):
    rows = []
    for dz in np.arange(-30.0, 0.01, 0.25):
        pcs = overlap_pieces(mov, shell, dz)
        if pcs:
            rows.append({'dz': round(float(dz), 2), 'pieces': pcs})
    ins[name] = rows
    log(name, len(rows))
res['insertionFromBelow'] = ins
res['finalPoseOverlap'] = {k: overlap_pieces(v, shell, 0.0) for k, v in (('jaw', jaw), ('ring', ring), ('pad', pad))}
save()

# 4. print orientation ----------------------------------------------------------------------------------
log('registration')
try:
    import trimesh
    from scipy.spatial import cKDTree
    pr = trimesh.load('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/assembly/print-parts/community-4.stl')
    jv, jf = load_solid('jaw_frame')

    def inertia(v, f):
        a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
        vol = np.einsum('ij,ij->i', a, np.cross(b, c)) / 6
        cen = (a + b + c) / 4
        V = vol.sum()
        com = (vol[:, None] * cen).sum(0) / V
        pts = np.concatenate([a, b, c]) - com
        w = np.concatenate([vol, vol, vol]) / 3
        C = (w[:, None, None] * pts[:, :, None] * pts[:, None, :]).sum(0)
        return V, com, C

    Vp, cp, Cp = inertia(np.asarray(pr.vertices, float), np.asarray(pr.faces))
    Vj, cj, Cj = inertia(jv, jf)
    ep, Ep = np.linalg.eigh(Cp)
    ej, Ej = np.linalg.eigh(Cj)
    tree = cKDTree(jv)
    best = None
    for s in [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]:
        R = Ej @ np.diag(s) @ Ep.T
        if np.linalg.det(R) < 0:
            continue
        pv = (np.asarray(pr.vertices, float) - cp) @ R.T + cj
        d, _ = tree.query(pv[::3])
        if best is None or d.mean() < best[0]:
            best = (float(d.mean()), R)
    R = best[1]
    pz = R @ np.array([0, 0, 1.0])
    res['printOrientation'] = {'meanVertexDistMm': round(best[0], 3), 'volumes': [round(Vp, 1), round(Vj, 1)],
                               'printZinRobotFrame': np.round(pz, 4).tolist(),
                               'angleToRobotZdeg': round(float(np.degrees(np.arccos(min(1, abs(pz[2]))))), 2),
                               'printExtent': np.round(pr.extents, 3).tolist(), 'R': np.round(R, 5).tolist()}
except Exception as e:  # keep the rest of the evidence
    res['printOrientation'] = {'error': repr(e)}
save()

# 5. jaw opening sweep -----------------------------------------------------------------------------------
log('swing')
PIV = np.array([26.1, 0.0, 118.62])


def rot_y(deg):
    t = np.radians(deg)
    Rm = np.array([[np.cos(t), 0, np.sin(t)], [0, 1, 0], [-np.sin(t), 0, np.cos(t)]])
    return np.c_[Rm, PIV - Rm @ PIV].tolist()


man = manifest()
skip = {'jaw_frame', 'lower_pad', 'mouth_sliding_ring', 'upper_pad'}
mods = {'head', 'electronics', 'camera', 'neck', 'head-close'}
keys = [k for k, v in man.items() if v.get('module') in mods and k not in skip]
mover = jaw + pad
mb = mover.bounding_box()
obs = {}
for k in keys:
    try:
        obs[k] = M(k)
    except Exception:
        pass
base = {k: (mover ^ o).volume() for k, o in obs.items()}
first = {}
angles = list(range(1, 61))
for ang in angles:
    mv = mover.transform(rot_y(ang))
    bb = mv.bounding_box()
    for k, o in obs.items():
        if k in first:
            continue
        ob = o.bounding_box()
        if any(bb[i] > ob[i + 3] or ob[i] > bb[i + 3] for i in range(3)):
            continue
        ex = (mv ^ o).volume() - base[k]
        if ex > 0.5:
            first[k] = {'deg': ang, 'excessMm3': round(ex, 2)}
res['jawOpenSweep'] = {'axisPoint': PIV.tolist(), 'axis': '+y (positive opens: front goes down)', 'parts': len(obs),
                       'baselineOverlapMm3': {k: round(v, 3) for k, v in base.items() if v > 0.01},
                       'firstContact': dict(sorted(first.items(), key=lambda kv: kv[1]['deg']))}
res['finished'] = time.strftime('%Y-%m-%d %H:%M:%S')
save()
log('done', list(res['jawOpenSweep']['firstContact'].items())[:6])
