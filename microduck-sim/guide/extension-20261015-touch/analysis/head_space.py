"""Free space inside the A7Z head and where touch readout boards fit.

Inputs: the print-gate closed solids (ia_lib CACHE, built by build_solids.py from guide-data and print/world) and the
drawn head cables in guide/data/guide-data.json. Output: head_space.json and head_space.npz next to this file.
Grid 1 mm, robot frame (x forward, y left, z up). Parts that move against the head shell (neck motors 13/14, the
yaw link and roll rings) are grown by 3 mm; every other solid and cable by 0.5 mm.
"""
import json, sys
from pathlib import Path
import numpy as np, trimesh
from scipy import ndimage

HERE = Path(__file__).resolve().parent
IA = HERE.parents[1] / 'content' / 'interference-audit'
sys.path.insert(0, str(IA))
from ia_lib import load_solid, manifest, load_guide   # noqa: E402

LO, HI, P = np.array([-34., -50., 96.]), np.array([96., 50., 160.]), 1.0
shape = np.ceil((HI - LO) / P).astype(int)
MOVING = {'motor13', 'motor14', 'head_yaw_link', 'head_roll_ring_a', 'head_roll_ring_b', 'neck_pitch', 'neck_pitch_ring'}
SHELL = {'head_cap', 'head_bottom', 'face_panel', 'jaw_frame', 'eye_trim'}


def vox(mesh):
    g = np.zeros(shape, bool)
    v = mesh.voxelized(P).fill()
    idx = np.floor((v.points - LO) / P).astype(int)   # np.round sends .5 to even and drops every second voxel
    ok = np.all((idx >= 0) & (idx < shape), axis=1)
    g[tuple(idx[ok].T)] = True
    return g


man = manifest()
occ = np.zeros(shape, bool); grown = np.zeros(shape, bool); shell = np.zeros(shape, bool); names = []
for k, m in man.items():
    b = np.array(m['bounds'])
    if np.any(b[1] < LO) or np.any(b[0] > HI):
        continue
    v, f = load_solid(k)
    g = vox(trimesh.Trimesh(v, f, process=False))
    if not g.any():
        continue
    names.append(k)
    occ |= g
    grown |= ndimage.binary_dilation(g, iterations=3 if k in MOVING else 1)
    if k in SHELL:
        shell |= g
cab = np.zeros(shape, bool)
for c in load_guide()['cables']:
    pts = np.array(c['path'], float)
    if pts[:, 2].max() < LO[2]:
        continue
    r = float(c.get('radius') or 0.9) + 0.5
    seg = np.concatenate([np.linspace(a, b, max(2, int(np.linalg.norm(b - a) / 0.5))) for a, b in zip(pts[:-1], pts[1:])])
    for p in seg:
        i0 = np.floor((p - r - LO) / P).astype(int); i1 = np.ceil((p + r - LO) / P).astype(int)
        i0 = np.clip(i0, 0, shape); i1 = np.clip(i1, 0, shape)
        if np.any(i1 <= i0):
            continue
        ax = [LO[d] + (np.arange(i0[d], i1[d]) + .5) * P for d in range(3)]
        X, Y, Z = np.meshgrid(*ax, indexing='ij')
        cab[i0[0]:i1[0], i0[1]:i1[1], i0[2]:i1[2]] |= (X - p[0])**2 + (Y - p[1])**2 + (Z - p[2])**2 <= r * r
# Head interior: close the shell, fill it, keep what no solid or cable takes.
def hit(g, axis, forward):
    a = np.flip(g, axis) if not forward else g
    c = np.maximum.accumulate(a, axis=axis)
    return np.flip(c, axis) if not forward else c


# A voxel is inside the head when the shell lies beyond it along +x, -x, +y, -y and +z, and some solid lies below it.
# Ray enclosure instead of a flood fill, because the neck opening and sound holes leave the shell open.
inside = (hit(shell, 0, True) & hit(shell, 0, False) & hit(shell, 1, True) & hit(shell, 1, False)
          & hit(shell[:, :, ::-1], 2, True)[:, :, ::-1] & hit(occ, 2, True)) & ~occ
free = inside & ~grown & ~cab
np.savez_compressed(HERE / 'head_space.npz', free=free, inside=inside, occ=occ, cab=cab, lo=LO, p=P)

BOXES = {   # name: (dims mm, what it is)
    'mpr121_flat': ((43, 19, 6), 'MPR121 1982 board 33 x 19, one STEMMA QT plug + cable bend on one end, pad leads soldered and leaving flat'),
    'mpr121_right_angle': ((43, 39, 6), 'MPR121 with a right-angle header, Dupont housings lying flat beside the long edge'),
    'mpr121_straight': ((43, 19, 26), 'MPR121 with a straight header, Dupont housings standing 14 mm plus wire bend'),
    'ads1115_flat': ((36, 18, 6), 'ADS1115 1085 board 25.4 x 17.8, one STEMMA QT plug, FSR leads soldered and leaving flat'),
    'ads1115_straight': ((36, 18, 26), 'ADS1115 with a straight header and Dupont housings'),
}
out = {'grid_mm': P, 'solids': len(names), 'inside_cm3': round(inside.sum() * P**3 / 1000, 1),
       'free_cm3': round(free.sum() * P**3 / 1000, 1), 'fits': {}}
for name, (d, desc) in BOXES.items():
    res = []
    for perm in {(0, 1, 2), (1, 0, 2), (0, 2, 1), (2, 0, 1), (1, 2, 0), (2, 1, 0)}:
        dd = [int(round(d[i] / P)) for i in perm]
        fit = ndimage.binary_erosion(free, structure=np.ones(dd, bool), border_value=0)
        if fit.any():
            lab, n = ndimage.label(fit)
            for j in range(1, n + 1):
                pts = np.argwhere(lab == j) * P + LO + P / 2
                res.append({'box_xyz_mm': dd, 'centres': int(len(pts)), 'centre_mean': np.round(pts.mean(0), 1).tolist(),
                            'x': [round(pts[:, 0].min()), round(pts[:, 0].max())], 'y': [round(pts[:, 1].min()), round(pts[:, 1].max())],
                            'z': [round(pts[:, 2].min()), round(pts[:, 2].max())]})
    out['fits'][name] = {'desc': desc, 'dims_mm': d, 'regions': sorted(res, key=lambda r: -r['centres'])[:6]}
(HERE / 'head_space.json').write_text(json.dumps(out, indent=1))
print(json.dumps({k: (v['dims_mm'], len(v['regions']), v['regions'][:3]) for k, v in out['fits'].items()}, indent=0)[:4000])
print('inside', out['inside_cm3'], 'free', out['free_cm3'], 'solids', len(names))
