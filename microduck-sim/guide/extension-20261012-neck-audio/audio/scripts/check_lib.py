"""Exact clearance checks for audio study solids against the V1.8 head (manifold3d booleans and min_gap).

Every study solid is tagged with the body it rides on:
  'cap'  - mounted in the cap; moves with the populated cap during cap-on (straight down 40 mm, guide group approach)
  'head' - the same rigid head body after closure (all cap-mounted parts are also head parts after closure)
Checks:
  static   : overlap volume and minimum gap against every head-fixed V1.8 solid (cap, lower shell, face, trim, camera,
             motor14, motor15, jaw support, mouth ring, Pi group with the 8 plugged housings)
  roll     : yaw body (motor13, head_yaw_link, both roll rings) swept through head roll -25..+25 deg (MJCF limit
             +-0.4363 rad) about the MJCF head_roll anchor [8.1, 0, 115.615], axis x, 1 deg steps
  jaw      : jaw frame swept 0..40 deg about the pivot [26.1, 0, 118.6146], axis +y, 1 deg steps
  descent  : cap-mounted study solids translated +z 0..40 mm (0.5 mm steps) against everything that is already on
             the robot at cap-on (lower shell, face, trim, camera, motors 13/14/15, jaw support, ring, jaw, neck parts)
  cables   : minimum distance from the solid to the drawn centreline of head_csi and bundle_head (routes.json),
             minus the cable half-size used here (ribbon 8 mm half-width, bundle 3 mm)
"""
from __future__ import annotations

import json

import manifold3d as m3
import numpy as np
import trimesh

from scene import JAW_PIVOT, SIM, ia_lib, load_man, manifest, pi_group_keys

ROLL_P = np.array([8.1, 0.0, 115.615])
FIXED = ['head_cap', 'head_bottom', 'face_panel', 'eye_trim', 'camera_board', 'motor14', 'motor15', 'jaw_support',
         'mouth_sliding_ring']
YAW = ['motor13', 'head_yaw_link', 'head_roll_ring_a', 'head_roll_ring_b']
AT_CAP_ON = ['head_bottom', 'face_panel', 'eye_trim', 'camera_board', 'motor13', 'motor14', 'motor15', 'jaw_support',
             'mouth_sliding_ring', 'jaw_frame', 'head_yaw_link', 'head_roll_ring_a', 'head_roll_ring_b',
             'neck_pitch_ring', 'neck_pitch']
CABLE_HALF = {'head_csi': 8.0, 'bundle_head': 3.0}


def rot(axis, deg, p):
    a = np.radians(deg)
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    R = np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K
    return np.c_[R, np.asarray(p) - R @ np.asarray(p)]


def man_from_tm(m: trimesh.Trimesh):
    return ia_lib.to_manifold(np.asarray(m.vertices), np.asarray(m.faces))


def tm_from_man(M) -> trimesh.Trimesh:
    v, f = ia_lib.from_manifold(M)
    return trimesh.Trimesh(v, f, process=False)


def bbox(M):
    return np.array(M.bounding_box()).reshape(2, 3)


def near(a, b, pad):
    A, B = bbox(a), bbox(b)
    return np.all(A[0] - pad <= B[1]) and np.all(B[0] - pad <= A[1])


def gap(a, b, search=8.0):
    if not near(a, b, search):
        return None
    return float(a.min_gap(b, search))


class Head:
    def __init__(self, cap_override=None):
        self.man = manifest()
        self.pi = pi_group_keys(self.man)
        self.S = {}
        self.cap_override = cap_override

    def get(self, k):
        if k not in self.S:
            self.S[k] = self.cap_override if (k == 'head_cap' and self.cap_override is not None) else load_man(k)
        return self.S[k]

    def static(self, name, M, skip=(), search=8.0):
        rows = []
        for k in FIXED + self.pi:
            if k in skip:
                continue
            O = self.get(k)
            if not near(M, O, search):
                continue
            ov = (M ^ O).volume()
            g = float(M.min_gap(O, search))
            rows.append({'with': k, 'overlapMm3': round(ov, 4), 'gapMm': round(g, 3)})
        rows.sort(key=lambda r: (-r['overlapMm3'], r['gapMm']))
        return rows

    def roll_sweep(self, M, step=1.0):
        worst = {'overlapMm3': 0.0, 'gapMm': 99.0}
        for k in YAW:
            O0 = self.get(k)
            for a in np.arange(-25.0, 25.0 + 1e-9, step):
                O = O0.transform(rot([-1, 0, 0], a, ROLL_P))
                if not near(M, O, 8):
                    continue
                ov = (M ^ O).volume()
                g = float(M.min_gap(O, 8))
                if ov > worst['overlapMm3'] or (ov == 0 and g < worst['gapMm']):
                    worst = {'overlapMm3': round(ov, 4), 'gapMm': round(g, 3), 'with': k, 'rollDeg': float(a)}
        return worst

    def jaw_sweep(self, M, step=1.0):
        worst = {'overlapMm3': 0.0, 'gapMm': 99.0}
        O0 = self.get('jaw_frame')
        for a in np.arange(0.0, 40.0 + 1e-9, step):
            O = O0.transform(rot([0, 1, 0], a, JAW_PIVOT))
            if not near(M, O, 8):
                continue
            ov = (M ^ O).volume()
            g = float(M.min_gap(O, 8))
            if ov > worst['overlapMm3'] or (ov == 0 and g < worst['gapMm']):
                worst = {'overlapMm3': round(ov, 4), 'gapMm': round(g, 3), 'jawDeg': float(a)}
        return worst

    def descent(self, M, step=0.5, travel=40.0):
        """Cap-mounted solid lowered with the cap. Returns the worst overlap excess over the final pose and the minimum
        gap seen along the path (per obstacle)."""
        out = {}
        for k in AT_CAP_ON:
            O = self.get(k)
            b = bbox(O)
            mb = bbox(M)
            if np.any(b[0] > mb[1] + [8, 8, travel + 8]) or np.any(b[1] < mb[0] - 8):
                continue
            f0 = (M ^ O).volume()
            worst_ex, min_g = 0.0, 99.0
            for dz in np.arange(0.0, travel + 1e-9, step):
                P = M.translate([0, 0, float(dz)])
                if not near(P, O, 6):
                    continue
                ex = (P ^ O).volume() - f0
                worst_ex = max(worst_ex, ex)
                if ex <= 1e-9:
                    min_g = min(min_g, float(P.min_gap(O, 6)))
            if worst_ex > 1e-6 or min_g < 6:
                out[k] = {'excessMm3': round(worst_ex, 4), 'minGapAlongPathMm': round(min_g, 3)}
        return out


def cable_clearance(M, routes=None):
    if routes is None:
        routes = json.loads((SIM / 'guide' / 'content' / 'routes.json').read_text())['routes']
    tm = tm_from_man(M)
    out = {}
    for cid, half in CABLE_HALF.items():
        p = np.asarray(routes[cid], float)
        pts = np.vstack([np.linspace(a, b, max(2, int(np.linalg.norm(b - a) / 0.5))) for a, b in zip(p[:-1], p[1:])])
        mb = bbox(M)
        keep = np.all((pts > mb[0] - 30) & (pts < mb[1] + 30), axis=1)
        if not keep.any():
            out[cid] = {'centrelineDistanceMm': None}
            continue
        _, d, _ = tm.nearest.on_surface(pts[keep])
        inside = tm.contains(pts[keep]) if tm.is_watertight else np.zeros(keep.sum(), bool)
        d = np.where(inside, -d, d)
        out[cid] = {'centrelineDistanceMm': round(float(d.min()), 2), 'assumedHalfSizeMm': half,
                    'clearanceMm': round(float(d.min()) - half, 2)}
    return out
