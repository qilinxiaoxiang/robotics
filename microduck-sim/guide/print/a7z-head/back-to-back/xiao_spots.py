"""Where the touch XIAO (22 x 18 x 5 mm; 26 x 18 x 5 with its wire exits) fits in the back-to-back head, off the five pad
areas. Same rules as extension-20261015-touch/analysis/head_space.py: 1 mm grid, parts that move against the head shell
(neck motors 13/14, yaw link, roll rings, neck pitch) grown 3 mm, the jaw swept 0..27 deg, everything else grown 1 mm.
Obstacles are the print gate's closed solids without the old A7Z, its cap clip, the old XIAO and the old cap, plus this
folder's cap, board, heatsink, fan air gap, plugs, fan lead, antenna cable, camera ribbon and ear screws, and the drawn
neck servo and speaker cables (the header, amplifier and touch wires are rerouted with the new pose and left out).
Writes xiao_spots.json.
"""
import json
import math
import sys

import numpy as np
import trimesh
from scipy import ndimage

import build_b2b as B

sys.path.insert(0, str(B.GUIDE / 'content' / 'interference-audit'))
from ia_lib import load_solid, manifest  # noqa: E402  (print-gate closed solids, as the touch study used)

LO, HI, P = np.array([-34., -50., 104.]), np.array([96., 50., 160.]), 1.0
shape = np.ceil((HI - LO) / P).astype(int)
MOVING = {'motor13', 'motor14', 'head_yaw_link', 'head_roll_ring_a', 'head_roll_ring_b', 'neck_pitch', 'neck_pitch_ring'}
SHELL = {'head_cap', 'head_bottom', 'face_panel', 'jaw_frame', 'eye_trim'}
DROP = {'touch_xiao', 'touch_xiao_tape', 'head_cap'}
FLOOR_Z = 111.3
PADS = ('touch_pad_m', 'touch_pad_l1', 'touch_pad_r1', 'touch_pad_l2', 'touch_pad_r2')


def vox(mesh):
    g = np.zeros(shape, bool)
    v = mesh.voxelized(P).fill()
    idx = np.floor((v.points - LO) / P).astype(int)
    ok = np.all((idx >= 0) & (idx < shape), axis=1)
    g[tuple(idx[ok].T)] = True
    return g


def hit(g, axis, forward):
    a = g if forward else np.flip(g, axis)
    c = np.maximum.accumulate(a, axis=axis)
    return c if forward else np.flip(c, axis)


def oriented(free, pad_zone):
    """The touch study's oriented fit (oriented_fit.py: 15 degree grid of roll and pitch, six yaws), with each fitting
    region kept apart: one entry per connected group of centres, its share of centres on the pad areas."""
    import itertools
    from scipy.spatial.transform import Rotation as R
    f = free.astype(np.float32); c = (np.array(f.shape) - 1) / 2
    angles = np.arange(-60, 61, 15); res = {}
    for name, dims in (('xiao_22x18x5', (22, 18, 5)), ('xiao_wires_26x18x5', (26, 18, 5))):
        hits = []
        for yaw in (0, 30, 60, 90, 120, 150):
            for roll, pitch in itertools.product(angles, angles):
                M = R.from_euler('zyx', [yaw, pitch, roll], degrees=True).as_matrix()
                g = ndimage.affine_transform(f, M, offset=c - M @ c, order=0, mode='constant', cval=0)
                ok = ndimage.uniform_filter(g, size=dims, mode='constant') * np.prod(dims) > np.prod(dims) - 0.5
                if not ok.any():
                    continue
                lab, n = ndimage.label(ok)
                for j in range(1, n + 1):
                    o = np.argwhere(lab == j)
                    wi = (M @ (o - c).T).T + c
                    w = wi * P + LO + P / 2
                    ii = np.clip(np.round(wi).astype(int), 0, np.array(f.shape) - 1)
                    hits.append({'yaw_pitch_roll': [int(yaw), int(pitch), int(roll)], 'n': int(len(o)),
                                 'centre_mean': np.round(w.mean(0), 1).tolist(),
                                 'onPadZone_share': round(float(pad_zone[tuple(ii.T)].mean()), 2)})
        # group by place: centres within 6 mm belong to one place; keep the orientation with most centres
        places = []
        for h in sorted(hits, key=lambda h: -h['n']):
            for pl in places:
                if np.linalg.norm(np.array(pl['centre_mean']) - h['centre_mean']) < 6:
                    pl['orientations'] += 1
                    break
            else:
                places.append(dict(h, orientations=1))
        res[name] = places[:10]
        print(name, places[:10])
    return res


def main():
    parts = {}
    for k in manifest():
        if k in DROP or k.startswith(('touch_pad', 'head_pi_')) or k in ('pi', 'clip_cap', 'camera_ribbon', 'antenna_coax',
                                                                         'antenna_ipex'):
            continue
        v, f = load_solid(k)
        m = trimesh.Trimesh(v, f, process=False)
        if np.all(m.bounds[1] > LO) and np.all(m.bounds[0] < HI):
            parts[k] = m
    rigid_cam = B.guide_parts()['camera_board']                 # without the V1.17 ribbon stub
    if 'camera_board' in parts:
        parts['camera_board'] = rigid_cam
    parts['head_cap'] = trimesh.load(B.HERE / 'head_cap_b2b-world.stl')
    for f in sorted((B.HERE / 'parts').glob('*.stl')):
        parts['b2b_' + f.stem] = trimesh.load(f)
    jaw = parts['jaw_frame']
    for a in np.arange(3.0, B.JAW_HI + 0.01, 3.0):
        m = jaw.copy(); m.apply_transform(trimesh.transformations.rotation_matrix(math.radians(a), B.JAW_AXIS, B.JAW_PIVOT))
        parts[f'jaw_frame@{a:.0f}'] = m
    occ = np.zeros(shape, bool); grown = np.zeros(shape, bool); shell = np.zeros(shape, bool)
    gdata = json.loads((B.GUIDE / 'data/guide-data.json').read_text())
    for c in gdata.get('cables', []):
        if not str(c.get('id', '')).startswith(('dxl-', 'spk-')):
            continue
        pts = np.array(c['path'], float); r = float(c.get('radius') or 0.9) + 0.5
        seg = np.concatenate([np.linspace(a, b, max(2, int(np.linalg.norm(b - a) / 0.5))) for a, b in zip(pts[:-1], pts[1:])])
        tube = trimesh.util.concatenate([trimesh.creation.icosphere(subdivisions=1, radius=r).apply_translation(q) for q in seg[::2]])
        parts['cable:' + c['id']] = tube.convex_hull if len(seg) < 3 else tube
    for k, m in parts.items():
        g = vox(m)
        if not g.any():
            continue
        occ |= g
        grown |= ndimage.binary_dilation(g, iterations=3 if k in MOVING else 1)
        if k in SHELL:
            shell |= g
    # above the head floor (z 111.3) rather than "something below": the floor is open under the left rear (neck opening)
    zc = (np.arange(shape[2]) * P + LO[2] + P / 2)[None, None, :] >= FLOOR_Z
    inside = (hit(shell, 0, True) & hit(shell, 0, False) & hit(shell, 1, True) & hit(shell, 1, False)
              & hit(shell[:, :, ::-1], 2, True)[:, :, ::-1] & zc) & ~occ
    free = inside & ~grown
    pad_zone = np.zeros(shape, bool)                       # the five pads now, grown 6 mm: where foil goes
    gd = {p['key']: p for p in json.loads((B.GUIDE / 'data/guide-data.json').read_text())['parts']}
    for k in PADS:
        lo, hi = np.array(gd[k]['bounds'][0]) - 6, np.array(gd[k]['bounds'][1]) + 6
        i0 = np.clip(np.floor((lo - LO) / P).astype(int), 0, shape); i1 = np.clip(np.ceil((hi - LO) / P).astype(int), 0, shape)
        pad_zone[i0[0]:i1[0], i0[1]:i1[1], i0[2]:i1[2]] = True
    out = {'free_cm3': round(free.sum() * P ** 3 / 1000, 1), 'fits': {}}
    for name, d in (('xiao_22x18x5', (22, 18, 5)), ('xiao_wires_26x18x5', (26, 18, 5))):
        res = []
        for perm in {(0, 1, 2), (1, 0, 2), (0, 2, 1), (2, 0, 1), (1, 2, 0), (2, 1, 0)}:
            dd = [d[i] for i in perm]
            fit = ndimage.binary_erosion(free, structure=np.ones(dd, bool), border_value=0)
            # taped: one of the two big faces (the axis of the 5 mm side) lies within 2 mm of a solid surface
            thin = int(np.argmin(dd))
            near = ndimage.binary_dilation(occ, iterations=2)
            shift = (dd[thin] + 1) // 2 + 1
            taped = np.roll(near, shift, axis=thin) | np.roll(near, -shift, axis=thin)
            ok = fit & taped
            if not ok.any():
                continue
            lab, n = ndimage.label(ok)
            for j in range(1, n + 1):
                idx = np.argwhere(lab == j)
                pts = idx * P + LO + P / 2
                res.append({'box_xyz_mm': dd, 'centres': int(len(pts)), 'centre_mean': np.round(pts.mean(0), 1).tolist(),
                            'x': [round(pts[:, 0].min()), round(pts[:, 0].max())], 'y': [round(pts[:, 1].min()), round(pts[:, 1].max())],
                            'z': [round(pts[:, 2].min()), round(pts[:, 2].max())],
                            'onPadZone_share': round(float(pad_zone[tuple(idx.T)].mean()), 2)})
        out['fits'][name] = sorted(res, key=lambda r: -r['centres'])[:12]
    out['oriented'] = oriented(free, pad_zone)
    (B.HERE / 'xiao_spots.json').write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=0)[:6000])


if __name__ == '__main__':
    main()
