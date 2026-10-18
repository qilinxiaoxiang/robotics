"""Shared helpers for the Pi-mount study. Reuses the audio study's scene loader and exact check library
(../../audio/scripts: scene.py, check_lib.py), read-only on every V1.8 file."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import manifold3d as m3
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
AUDIO = STUDY.parent / 'audio'
sys.path.insert(0, str(AUDIO / 'scripts'))
from check_lib import (AT_CAP_ON, FIXED, ROLL_P, YAW, Head, bbox, cable_clearance, man_from_tm, near, rot,  # noqa: E402,F401
                       tm_from_man)
from scene import JAW_PIVOT, SIM, manifest, pi_group_keys  # noqa: E402,F401

CAP_V18 = SIM / 'guide/print/world/head_cap.stl'
A_SCREW = np.array([-0.984808, 0.0, 0.173648])      # Pi screw insertion direction (fasteners.json E-pi-01..04)
AX = np.array([0.173648, 0.0, 0.984808])            # rail axis, in the Pi plane, perpendicular to the screws
SCREWS = {'E-pi-01': np.array([57.341, -29.0, 118.245]), 'E-pi-02': np.array([57.341, 29.0, 118.245]),
          'E-pi-03': np.array([61.335, -29.0, 140.895]), 'E-pi-04': np.array([61.335, 29.0, 140.895])}
AUDIO_SOLIDS = ['speaker', 'speaker_retainer', 'amplifier', 'amp_housings', 'amp_screws_envelope',
                'speaker_screws_envelope', 'cap_added_material', 'pi_housing_pin04', 'pi_housing_pin12',
                'pi_housing_pin14', 'pi_housing_pin35', 'pi_housing_pin40']
_MAN18 = json.loads((SIM / 'guide/print/release-V1.8/manifest-V1.8.json').read_text())
SOURCE_TO_PRINT = np.array(next(p for p in _MAN18['parts'] if p['key'] == 'head_cap')['sourceToPrint'])
PRINT_UP = SOURCE_TO_PRINT[2, :3] / np.linalg.norm(SOURCE_TO_PRINT[2, :3])   # print +z expressed in the robot frame


def load_stl_man(p):
    return man_from_tm(trimesh.load(p, force='mesh'))


def audio_solid(k):
    return load_stl_man(AUDIO / 'study-solids' / f'{k}-world.stl')


def audio_wire_tubes():
    sys.path.insert(0, str(AUDIO / 'scripts'))
    from wires import R_JUMPER, R_LEAD, tube_manifold
    W = json.loads((AUDIO / 'wire-routes.json').read_text())
    return {f'audio_wire_{k}': tube_manifold(np.asarray(v, float), R_LEAD if k.startswith('spk') else R_JUMPER)
            for k, v in W.items()}


def box(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return m3.Manifold.cube((hi - lo).tolist()).translate(lo.tolist())


def frame_box(origin, e1, e2, e3, size, centred=(True, True, False)):
    """Box with edges along the orthonormal frame (e1, e2, e3); size (a, b, c); origin = reference corner/centre."""
    a, b, c = size
    off = [-a / 2 if centred[0] else 0.0, -b / 2 if centred[1] else 0.0, -c / 2 if centred[2] else 0.0]
    B = m3.Manifold.cube([a, b, c]).translate(off)
    T = np.eye(4)[:3]
    T[:, 0], T[:, 1], T[:, 2], T[:, 3] = e1, e2, e3, origin
    return B.transform(T)


def cyl(p0, axis, length, r, seg=32):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    C = m3.Manifold.cylinder(length, r, r, seg)
    z = np.array([0, 0, 1.0])
    v = np.cross(z, axis)
    s, c = np.linalg.norm(v), z @ axis
    if s < 1e-9:
        R = np.eye(3) if c > 0 else np.diag([1, -1, -1.0])
    else:
        K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        R = np.eye(3) + K + K @ K * ((1 - c) / s ** 2)
    T = np.c_[R, np.asarray(p0, float)]
    return C.transform(T)


def corridor_keepouts():
    """Volumes the parallel neck-route study needs free (from the audio occupancy report and the coordinator brief):
    behind the Pi in the middle (x < 59.5, |y| < 25), everything below z 111.9 inside the head, and the region just
    below the Pi header in front of the Pi (x 59..78, |y| < 26, z 104..113)."""
    return {'behind_pi_middle': box([20, -25, 111.9], [59.5, 25, 150]),
            'below_z111.9': box([-40, -50, 90], [95, 50, 111.9]),
            'below_header': box([59, -26, 104], [78, 26, 113])}


def j(o):
    return json.loads(json.dumps(o, default=lambda x: x.tolist() if hasattr(x, 'tolist') else float(x)))


def screw_envelope(c, length, axis=A_SCREW, d=2.0, head_d=4.0, head_h=1.5):
    """Pan-head screw envelope: head (head_d x head_h) behind the seat point c, shank d x length along axis."""
    ax = np.asarray(axis, float) / np.linalg.norm(axis)
    return cyl(c, ax, length, d / 2, 24) + cyl(c - head_h * ax, ax, head_h, head_d / 2, 32)


def csi_ribbon_strip(width=16.0, thick=0.3):
    """Flat ribbon model along routes.json head_csi: width along world z (the ribbon stands on edge beside the Pi and
    the camera), thickness 0.3 mm. 16 mm is the 15-way camera-end width (the 22-way Pi end is narrower)."""
    routes = json.loads((SIM / 'guide/content/routes.json').read_text())['routes']
    p = np.asarray(routes['head_csi'], float)
    segs = []
    for a, b in zip(p[:-1], p[1:]):
        t = (b - a) / np.linalg.norm(b - a)
        nrm = np.cross(t, [0, 0, 1.0])
        nrm /= np.linalg.norm(nrm)
        pts = [q + s * nrm * thick / 2 + h * np.array([0, 0, width / 2]) for q in (a, b) for s in (-1, 1) for h in (-1, 1)]
        segs.append(m3.Manifold.hull_points([list(map(float, x)) for x in pts]))
    return m3.Manifold.batch_boolean(segs, m3.OpType.Add)
