"""Head routes for D-025 (ears and mouth speaker): A* on a 1 mm occupancy grid of the current head solids with the new parts.

Routes (robot frame, mm):
- mic_r_harness: the five wires (SCK, WS, SD, VDD, GND) soldered on the back of the right INMP441 leave through the open top
  of its locator, cross the cap behind the camera and end on the back of the left INMP441, where each is soldered onto the
  same pad as the left board's own wire (Shawn 2026-10-23: "别排针了 直接焊吧").
- mic_l_harness: the five wires from the left INMP441 along the cap to the head gather point over the dia 11 left-rear exit
  (11.5, 19.5, 132). There SCK is spliced into the amplifier BCLK wire (flag 12), WS into the amplifier LRC wire (flag 35) and
  VDD into the XIAO 3V3 wire (flag 17); SD and GND go on down the neck.
- mic_sd_pin38, mic_gnd_pin34: from the gather point down the head-down bundle to A7Z pin 38 (I2S0 DIN0) and pin 34 (GND) in
  the roof saddle: the audio_amp_din_pin40 route from the gather point on, with its last lane points moved to the pin.
- spk_plus, spk_minus: the speaker leads from the two pads at the top of the speaker back, back over the jaw support and up
  round the front (-x) end of the amplifier into its green terminal, which opens towards -x.

Every mic wire rides on the cap (z >= 113, above the cap rim) and so passes over the servos, never under them or the neck
(Shawn 2026-10-23: "杜邦线从舵机上面过"). Routes keep CLEAR from occupied voxel centres; cables.py checks the drawn tubes exactly.

    /tmp/microduck-cad-venv/bin/python route_ears_mouth.py      (writes routes_ears_mouth.json)
"""
import heapq
import json
import sys
from pathlib import Path

import numpy as np
import trimesh
from scipy import ndimage

HERE = Path(__file__).resolve().parent
EM = HERE.parent
GUIDE = EM.parents[1]
sys.path.insert(0, str(GUIDE / 'content' / 'interference-audit'))
import ia_lib  # noqa: E402

G = 1.0
LO, HI = np.array([-34.0, -48.0, 96.0]), np.array([96.0, 48.0, 160.0])
CLEAR = 1.6
REPLACED = {'speaker', 'speaker_retainer', 'speaker_tape', 'head_cap', 'head_bottom'}
NEW = {'head_cap': EM / 'head-cap/head_cap_ears-world.stl', 'head_bottom': EM / 'yellow-reprint/head_bottom_ports-world.stl',
       'speaker_box': EM / 'speaker-box/speaker_box-world.stl', 'speaker': EM / 'speaker-box/speaker_mouth-world.stl',
       'mic_left': EM / 'head-cap/mic_left-world.stl', 'mic_right': EM / 'head-cap/mic_right-world.stl',
       'mic_foam_left': EM / 'head-cap/mic_foam_left-world.stl', 'mic_foam_right': EM / 'head-cap/mic_foam_right-world.stl'}
GATHER = np.array([11.5, 19.5, 132.0])
R0 = json.loads((GUIDE / 'content/routes.json').read_text())['routes']
CAP = json.loads((EM / 'head-cap/checks.json').read_text())
SPK = json.loads((EM / 'speaker-box/checks.json').read_text())
PINS = json.loads((GUIDE / 'print/a7z-saddle/build/pins.json').read_text())['pinTop']

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


def astar(a, b, zmin=None):
    free = free_all.copy()
    if zmin is not None:
        free[:, :, :int(np.ceil((zmin - LO[2]) / G))] = False
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
    # (a dropped corner lets the drawn tube cut through the part the search went round)
    keep = [pts[0]]
    for i in range(1, len(pts) - 1):
        if not chord_free(keep[-1], pts[i + 1], free):
            keep.append(pts[i])
    keep.append(pts[-1])
    return np.array(keep)


def chord_free(a, b, free):
    n = max(2, int(np.ceil(np.linalg.norm(b - a) / 0.25)) + 1)
    for t in np.linspace(0, 1, n):
        c = np.floor((a + t * (b - a) - LO) / G).astype(int)
        if not (np.all(c >= 0) and np.all(c < shape) and free[tuple(c)]):
            return False
    return True


def mic_points(side):
    e = next(x for x in CAP['ears'] if x['side'] == side)
    p, a = np.array(e['innerHit']), np.array(e['axisIntoCavity'])
    up = np.array([0, 0, 1.0]) - a * a[2]; up /= np.linalg.norm(up)
    back = p + a * (e['boardFaceAlongAxisMm'] + 1.0 + 0.7)          # just off the board back (PCB 1.0 mm)
    pad = back + up * 4.5                                            # pad row near the top edge of the board
    exit_ = pad + up * 5.5 + a * 2.5                                 # out through the open top of the locator
    return pad, exit_


routes = {}
lp, le = mic_points('left'); rp, re_ = mic_points('right')
mid = astar(re_, le, zmin=113.0)
routes['mic_r_harness'] = np.vstack([rp, re_, mid[1:-1], le, lp])
mid = astar(le, GATHER + [3.0, 3.0, 4.0], zmin=113.0)
routes['mic_l_harness'] = np.vstack([lp, le, mid[1:-1], GATHER + [3.0, 3.0, 4.0], GATHER])

# down the neck: the pin-40 amplifier route from the gather point on, its saddle lane end moved to the pin
din = np.array(R0['audio_amp_din_pin40'], float)
i0 = int(np.argmin(np.linalg.norm(din - GATHER, axis=1)))
lane_end = [i for i in range(len(din)) if abs(din[i, 1] - 24.13) < 1e-6][0]        # first point on the pin-40 column
for pin, key in ((38, 'mic_sd_pin38'), (34, 'mic_gnd_pin34')):
    x, y, z = PINS[str(pin)]
    tail = din[lane_end:].copy(); tail[:, 1] = y; tail[-1, 0] = x; tail[-1, 2] = z
    routes[key] = np.vstack([din[i0:lane_end], tail])

# speaker leads: pad at the top of the speaker back to the amplifier terminal entry (old spk route ends, which open to -x)
sb = np.array(SPK['speakerBounds'])
for s, key in ((1, 'spk_plus'), (-1, 'spk_minus')):
    old = np.array(R0[f'audio_spk_{key[4:]}'], float)
    pad = np.array([sb[0, 0] + 0.3, -3.0 + 1.5 * s, sb[1, 2] - 2.5])
    up = pad + [-2.5, 0, 0]
    entry = old[-2]                                                   # (18.25, +-1.75, 142.8): in line with the terminal
    mid = astar(up, entry + [-2.0, 0, 0], zmin=None)
    routes[key] = np.vstack([pad, up, mid[1:-1], entry + [-2.0, 0, 0], old[-2:]])

out = {k: np.round(v, 2).tolist() for k, v in routes.items()}
L = {k: round(float(np.linalg.norm(np.diff(np.array(v), axis=0), axis=1).sum()), 1) for k, v in out.items()}
(HERE / 'routes_ears_mouth.json').write_text(json.dumps({'_doc': __doc__.strip().splitlines()[0], 'clearMm': CLEAR, 'lengthsMm': L, 'routes': out}, indent=1))
print(json.dumps(L, indent=1))
for k, v in out.items():
    print(k, v[:3], '...', v[-2:])
