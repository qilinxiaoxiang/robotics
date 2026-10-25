"""Head routes for the mouth floor (Shawn 2026-10-24, version 3): A* on a 1 mm occupancy grid of the head solids with the new parts.

The speaker and the amplifier moved to the yellow floor and the XIAO touch board to the middle of the roof
(build_mouth_floor.py, build_cap_xiao.py), so every wire that ends on one of them is routed again (robot frame, mm):
- audio_amp_*: the five soldered amplifier wires from the input row (JP1) up and back to the head gather point over the
  left-rear exit (11.5, 19.5, 132), then down the neck on their D-025 tails (unchanged from the gather point on).
- audio_spk_plus, audio_spk_minus: from the two speaker pads straight up and across the 4 mm gap into the amplifier's
  green terminal, which opens towards -y on the same centre line (x 64). Their + and - pads were swapped against the datasheet;
  route_spk_polarity.py (2026-10-25) replaces both with the crossing pair.
- touch_pad_*: from the five copper pads (unchanged) to the XIAO pad holes at the roof centre.
- touch_a7z_*: from the XIAO (3V3, GND, SCL, SDA) to the gather point, then their D-025 tails down the neck.
The old start and end points on the moved boards are carried by the same rigid transforms that moved the boards (fitted
from the board meshes, residual below 1e-4 mm), so each wire still starts in its own hole. Routes keep CLEAR from occupied
voxel centres; cables.py checks the drawn tubes exactly. The microphone routes do not change.

    /tmp/microduck-cad-venv/bin/python route_mouth_floor.py      (writes routes_mouth_floor.json)
"""
import heapq
import json
import sys
from pathlib import Path

import numpy as np
import trimesh
from scipy import ndimage

HERE = Path(__file__).resolve().parent
GUIDE = HERE.parents[1]
WORLD = GUIDE / 'print/world'
sys.path.insert(0, str(GUIDE / 'content' / 'interference-audit'))
import ia_lib  # noqa: E402

G = 1.0
LO, HI = np.array([-34.0, -48.0, 96.0]), np.array([96.0, 48.0, 160.0])
CLEAR = 1.6
NEW = {'head_cap': HERE / 'head_cap_mouth-world.stl', 'head_bottom': HERE / 'head_bottom_mouth-world.stl',
       'jaw_support': HERE / 'jaw_support_exit.stl', 'speaker': HERE / 'speaker_floor-world.stl',
       'speaker_tape': HERE / 'speaker_tape_floor-world.stl', 'amplifier': HERE / 'amplifier_floor-world.stl',
       'amp_tape': HERE / 'amp_tape-world.stl', 'touch_xiao': HERE / 'touch_xiao_centre-world.stl',
       'touch_xiao_tape': HERE / 'touch_xiao_tape_centre-world.stl'}
REPLACED = set(NEW) | {'speaker_box', 'speaker_box_tape'}
GATHER = np.array([11.5, 19.5, 132.0])
R0 = json.loads((GUIDE / 'content/routes.json').read_text())['routes']
AMP = ['audio_amp_vin_pin04', 'audio_amp_lrc_pin35', 'audio_amp_din_pin40', 'audio_amp_bclk_pin12', 'audio_amp_gnd_pin39']
PADS = ['touch_pad_l1', 'touch_pad_r1', 'touch_pad_l2', 'touch_pad_r2', 'touch_pad_m']
XA7Z = ['touch_a7z_pin17', 'touch_a7z_pin25', 'touch_a7z_pin29', 'touch_a7z_pin31']


def fit(a, new):
    """Affine map old -> new from corresponding triangle corners (the build scripts move each board with one rigid transform;
    STL keeps the triangle order, so corners correspond when both sides are read unprocessed)."""
    a = a.triangles.reshape(-1, 3); b = trimesh.load(new, force='mesh', process=False).triangles.reshape(-1, 3)
    X, *_ = np.linalg.lstsq(np.c_[a, np.ones(len(a))], b, rcond=None)
    res = float(np.abs(np.c_[a, np.ones(len(a))] @ X - b).max()); assert res < 1e-4, res
    return lambda p: np.c_[np.atleast_2d(p), np.ones(len(np.atleast_2d(p)))] @ X, res


amp_T, amp_res = fit(trimesh.load(WORLD / 'amplifier.stl', force='mesh', process=False), HERE / 'amplifier_floor-world.stl')
xiao_T, xiao_res = fit(trimesh.Trimesh(*ia_lib.load_solid('touch_xiao'), process=False), HERE / 'touch_xiao_centre-world.stl')   # build_cap_xiao.py moved the cached solid
# the speaker mesh loses a few duplicate vertices on export, so its transform is built from build_mouth_floor.py's rotation
Rs = np.array([[0, -1.0, 0], [0, 0, 1.0], [-1.0, 0, 0]])
sb_old = trimesh.load(WORLD / 'speaker.stl', force='mesh').bounds; sb_new = trimesh.load(HERE / 'speaker_floor-world.stl', force='mesh').bounds
ts = sb_new.mean(0) - Rs @ sb_old.mean(0)
spk_T = lambda p: np.atleast_2d(p) @ Rs.T + ts
assert np.allclose(np.sort(spk_T(sb_old), 0), np.sort(sb_new, 0), atol=1e-3)

meshes = {}
for k in json.loads((ia_lib.CACHE / 'solids-manifest.json').read_text()):
    if k in REPLACED:
        continue
    v, f = ia_lib.load_solid(k)
    if v[:, 2].max() > LO[2] and v[:, 0].min() < HI[0] and v[:, 0].max() > LO[0] and v[:, 2].min() < HI[2]:
        meshes[k] = trimesh.Trimesh(v, f, process=False)
for k, p in NEW.items():
    meshes[k] = trimesh.load(p, force='mesh')

shape = tuple(np.ceil((HI - LO) / G).astype(int))
occ = np.zeros(shape, bool)
for k, m in meshes.items():
    vox = m.voxelized(G)
    try:
        vox = vox.fill()
    except Exception:
        pass
    idx = np.floor((vox.points - LO) / G).astype(int)
    ok = np.all((idx >= 0) & (idx < shape), axis=1)
    occ[tuple(idx[ok].T)] = True
dist = ndimage.distance_transform_edt(~occ) * G
free_all = dist >= CLEAR
lab, _ = ndimage.label(free_all)
centre = lab[tuple(np.floor((np.array([20, 0, 135]) - LO) / G).astype(int))]
assert centre, 'head centre not free'
free_all = lab == centre
cost_mult = np.where(dist < 2.8, 1.0, 1.6)        # prefer lying against a surface, as a taped wire does
NB = [d for d in np.argwhere(np.ones((3, 3, 3), bool)) - 1 if np.any(d)]
NBL = [float(np.linalg.norm(d)) for d in NB]


def cell(p):
    return tuple(np.floor((np.asarray(p) - LO) / G).astype(int))


def nearest_free(p, free):
    i = np.array(cell(p)); best, bd = None, 1e9
    for d in np.argwhere(np.ones((11, 11, 11), bool)) - 5:
        q = i + d
        if np.all(q >= 0) and np.all(q < shape) and free[tuple(q)] and np.linalg.norm(d) < bd:
            best, bd = tuple(q), float(np.linalg.norm(d))
    assert best is not None, p
    return best


def chord_free(a, b, free):
    n = max(2, int(np.ceil(np.linalg.norm(b - a) / 0.25)) + 1)
    for t in np.linspace(0, 1, n):
        c = np.floor((a + t * (b - a) - LO) / G).astype(int)
        if not (np.all(c >= 0) and np.all(c < shape) and free[tuple(c)]):
            return False
    return True


def astar(a, b):
    free = free_all
    a, b = nearest_free(a, free), nearest_free(b, free)
    bb = np.array(b); openq = [(0.0, 0.0, a)]; g = {a: 0.0}; par = {a: None}
    while openq:
        _, gc, u = heapq.heappop(openq)
        if u == b:
            break
        if gc > g[u]:
            continue
        for d, l in zip(NB, NBL):
            v = (u[0] + d[0], u[1] + d[1], u[2] + d[2])
            if not (0 <= v[0] < shape[0] and 0 <= v[1] < shape[1] and 0 <= v[2] < shape[2]) or not free[v]:
                continue
            ng = gc + l * cost_mult[v]
            if ng < g.get(v, 1e18):
                g[v] = ng; par[v] = u
                heapq.heappush(openq, (ng + float(np.linalg.norm(np.array(v) - bb)), ng, v))
    assert b in par, 'no path'
    path = [b]
    while par[path[-1]] is not None:
        path.append(par[path[-1]])
    pts = LO + (np.array(path[::-1]) + 0.5) * G
    # keep a grid point only where the straight chord from the last kept point to the next point would leave the free cells
    keep = [pts[0]]
    for i in range(1, len(pts) - 1):
        if not chord_free(keep[-1], pts[i + 1], free):
            keep.append(pts[i])
    keep.append(pts[-1])
    return np.array(keep)


def tail(key):
    """The D-025 route of this wire from the gather point on (down the exit and the neck to the A7Z pin)."""
    v = np.array(R0[key], float)
    i = int(np.argmin(np.linalg.norm(v - GATHER, axis=1))); assert np.linalg.norm(v[i] - GATHER) < 1e-6, key
    return v[i:]


routes = {}
for k in AMP:                                     # input hole, lift-off point (both carried with the board), then A*
    head = amp_T(np.array(R0[k][:2], float))
    mid = astar(head[-1], GATHER)
    routes[k] = np.vstack([head, mid[1:-1], tail(k)])
for k in XA7Z:                                    # XIAO hole and lift-off point carried with the board
    head = xiao_T(np.array(R0[k][:2], float))
    mid = astar(head[-1], GATHER)
    routes[k] = np.vstack([head, mid[1:-1], tail(k)])
for k in PADS:                                    # copper pad start unchanged; the last two points (XIAO approach, hole) carried
    v = np.array(R0[k], float)
    end = xiao_T(v[-2:])
    mid = astar(v[1], end[0])
    routes[k] = np.vstack([v[:2], mid[1:-1], end])
spk_top = trimesh.load(HERE / 'speaker_floor-world.stl', force='mesh').bounds[1, 2]
for k in ('audio_spk_plus', 'audio_spk_minus'):   # pad on the speaker back (now its top), straight up, across into the terminal
    v = np.array(R0[k], float)
    pad = spk_T(v[0])[0]; pad[2] = spk_top + 0.3
    entry, inside = amp_T(v[-2:])
    up = np.array([pad[0], pad[1], entry[2]])
    routes[k] = np.vstack([pad, up, entry, inside])

out = {k: np.round(v, 2).tolist() for k, v in routes.items()}
L = {k: round(float(np.linalg.norm(np.diff(np.array(v), axis=0), axis=1).sum()), 1) for k, v in out.items()}
L0 = {k: round(float(np.linalg.norm(np.diff(np.array(R0[k]), axis=0), axis=1).sum()), 1) for k in out}
(HERE / 'routes_mouth_floor.json').write_text(json.dumps({'_doc': __doc__.strip().splitlines()[0], 'clearMm': CLEAR,
                                                          'transformResidualMm': {'amplifier': amp_res, 'touch_xiao': xiao_res},
                                                          'lengthsMm': L, 'lengthsBeforeMm': L0, 'routes': out}, indent=1))
for k, v in out.items():
    print(f'{k:22s} {L0[k]:6.1f} -> {L[k]:6.1f}', v[:2], '...', v[-1])
