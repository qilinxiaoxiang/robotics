"""Shared helpers for the jaw-neck check (read-only on V1.8 / guide / simulator sources).

Kinematics: neck-route/nr_lib.FK (MJCF robot_allcollisions.xml; qpos in rad; jaw in degrees about the V1.8 pivot
[26.1, 0, 118.6146] mm, axis +y, + = open). Solids: the interference-audit closed solid cache (ia_lib.CACHE), checked
against the current print/world STL and guide-data.json display meshes by check_solids().
Classes as integrated/jaw_pickup.py: 'interference' = overlap > 0.01 mm3; 'contact' = no overlap, gap < 0.2 mm;
'clear' = gap >= 0.2 mm.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent
EXT = OUT.parent
sys.path.insert(0, str(EXT / 'neck-route'))
os.environ.setdefault('NR_SCRATCH', str(Path(os.environ.get('TMPDIR', '/tmp')) / 'jaw-neck-check-nr'))
from nr_lib import BODY_OF, FK, ia_lib, load_solid  # noqa: E402

PARTS = {   # body -> parts below the head that the jaw can reach (same list as integrated/jaw_pickup.py BELOW)
    'neck_pitch': ['neck_pitch', 'neck_pitch_ring', 'idler11', 'idler_cap11'],
    'neck': ['motor11', 'motor12', 'neck_link_a', 'neck_link_b'],
    'trunk_base': ['shell_right', 'shell_left', 'torso_base', 'rear_pack', 'rear_pack_cover', 'openrb_board',
                   'idler12', 'idler_cap12'],
}
# joints that change the jaw's pose relative to each body (the jaw angle always does)
DEPENDS = {'neck_pitch': ('head_yaw', 'head_roll'), 'neck': ('head_pitch', 'head_yaw', 'head_roll'),
           'trunk_base': ('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll')}
HEAD_REST = ['head_bottom', 'jaw_support', 'face_panel', 'head_cap', 'motor14', 'motor15', 'mouth_sliding_ring',
             'motor13', 'head_yaw_link', 'head_roll_ring_a', 'head_roll_ring_b']
JOINTS = ('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll')
TRAIN_JAW_MAX_DEG = float(np.degrees(0.32))      # app/src/game/duck.js JAW_MAX_OPEN; beak_joint range 0..0.32 rad


def cls(ov, g):
    return 'interference' if ov > 0.01 else ('contact' if g < 0.2 else 'clear')


class Checker:
    def __init__(self, extra=()):
        self.fk = FK()
        keys = ['jaw_frame'] + [k for ks in PARTS.values() for k in ks] + list(extra)
        self.man = {k: ia_lib.to_manifold(*load_solid(k)) for k in keys}

    def T(self, qdeg: dict, jaw: float):
        q = {j: np.radians(qdeg.get(j, 0.0)) for j in JOINTS}
        return self.fk.part_T({**q, 'jaw': float(jaw)})

    def jaw_vs(self, T, bodies=('neck_pitch', 'neck', 'trunk_base'), search=10.0, detail=False):
        """Rows for every part within `search` mm of the jaw frame at transforms T, worst first."""
        J = self.man['jaw_frame'].transform(T['jaw'][:3, :].tolist())
        out = []
        for b in bodies:
            for k in PARTS[b]:
                P = self.man[k].transform(T[b][:3, :].tolist())
                g = float(J.min_gap(P, search))
                if g >= search:
                    continue
                ov = 0.0
                row = {'part': k, 'body': b, 'overlapMm3': 0.0, 'gapMm': round(g, 3)}
                if g < 1e-6:
                    X = J ^ P
                    ov = float(X.volume())
                    row['overlapMm3'] = round(ov, 3)
                    if detail and ov > 0.01:
                        v = np.asarray(X.to_mesh().vert_properties)[:, :3]
                        c = v.mean(0)
                        Ti = np.linalg.inv(T['jaw'])
                        row['onJawAtRestMm'] = np.round(Ti[:3, :3] @ c + Ti[:3, 3], 1).tolist()
                        row['overlapDepthMm'] = round(float(np.ptp(v @ np.linalg.svd(v - c, full_matrices=False)[2][2])), 2)
                row['class'] = cls(ov, g)
                out.append(row)
        out.sort(key=lambda r: (-r['overlapMm3'], r['gapMm']))
        return out

    def first_contact(self, qdeg, bodies, lo=0.0, hi=40.0, step=1.0, refine=0.25):
        """Smallest jaw angle (deg) with contact or interference, by `step` scan then bisection to `refine`.
        Returns (angle, worst row); (None, None) if clear up to hi; (lo, row) if already touching at lo."""
        prev = None
        for a in np.arange(lo, hi + 1e-9, step):
            rows = self.jaw_vs(self.T(qdeg, a), bodies)
            if rows and rows[0]['class'] != 'clear':
                if prev is None:
                    return float(a), rows[0]
                b_lo, b_hi, hit = prev, float(a), rows[0]
                while b_hi - b_lo > refine:
                    m = 0.5 * (b_lo + b_hi)
                    r = self.jaw_vs(self.T(qdeg, m), bodies)
                    if r and r[0]['class'] != 'clear':
                        b_hi, hit = m, r[0]
                    else:
                        b_lo = m
                return round(b_hi, 2), hit
            prev = float(a)
        return None, None


def jdump(obj, path):
    Path(path).write_text(json.dumps(obj, indent=1))


def check_solids(keys):
    """Cached audit solid vs current source: print/world STL (WORLD_FILE keys) and guide-data display-mesh bounds."""
    import trimesh
    guide = {p['key']: p for p in ia_lib.load_guide()['parts']}
    rows = []
    for k in keys:
        v, f = load_solid(k)
        sb = np.array([v.min(0), v.max(0)])
        row = {'key': k, 'solidBounds': np.round(sb, 2).tolist(),
               'solidVolumeMm3': round(float(ia_lib.to_manifold(v, f).volume()), 1)}
        if k in ia_lib.WORLD_FILE:
            m = trimesh.load(ia_lib.WORLD / ia_lib.WORLD_FILE[k], force='mesh', process=False)
            wb = np.array([m.vertices.min(0), m.vertices.max(0)])
            row['source'] = f'print/world/{ia_lib.WORLD_FILE[k]}'
            row['worldBoundsDevMm'] = round(float(np.abs(wb - sb).max()), 3)
            row['worldVolumeMm3'] = round(float(abs(m.volume)), 1)
        if k in guide:
            gv, gf = ia_lib.decode_guide_part(guide[k])
            gb = np.array([gv.min(0), gv.max(0)])
            row['guideDisplayBoundsDevMm'] = round(float(np.abs(gb - sb).max()), 3)
            row['guideStatus'] = guide[k].get('status')
        rows.append(row)
    return rows
