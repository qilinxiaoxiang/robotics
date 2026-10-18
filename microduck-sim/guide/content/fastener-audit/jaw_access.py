#!/usr/bin/env python3
"""Driver access to the two front head-closure screws (K-head_close-01/02) as the jaw opens.

The jaw (jaw_frame + lower_pad) is rotated about the ID15 output axis (world y through x=26.1, z=118.61, the centre
of the four S15 horn screws). Positive angle opens the mouth (front of the jaw moves down). For each angle the script
reports (a) the straight Ø3 mm driver corridor below each screw head (first solid along -z within r <= 1.5 mm) and
(b) whether the rotated jaw_frame/lower_pad has run into the lower head shell, face or neck parts (mechanical stop,
sampled vertices inside watertight neighbours).
"""
import gc, json, math, sys
from pathlib import Path
import numpy as np
import trimesh
sys.path.insert(0, str(Path(__file__).resolve().parent))
import geom
import screw_defs

PIVOT = np.array([26.1, 0.0, 118.61])
JAW = ['jaw_frame', 'lower_pad']
STATIC_STOP = ['head_bottom', 'face_panel', 'jaw_support', 'mouth_sliding_ring', 'head_yaw_link']


def rot_y(th):
    c, s = math.cos(th), math.sin(th)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def main(out):
    D = {d['id']: d for d in screw_defs.defs()}
    probe = json.loads(Path(sys.argv[2]).read_text()) if len(sys.argv) > 2 else {}
    jaw = {k: geom.mesh(k) for k in JAW}
    others = [k for k in geom.available('full') if k not in JAW + ['upper_pad', 'jaw_support_guide_pose']
              and not k.startswith(('camera_clamp_screw_', 'speaker_mount_screw_'))]
    stops = {k: geom.mesh(k) for k in STATIC_STOP}
    res = {'pivot': PIVOT.tolist(), 'note': 'upper_pad is excluded: the close step fits it after the screws', 'angles': []}
    rng = np.random.default_rng(0)
    samp = {k: m.vertices[rng.choice(len(m.vertices), min(2500, len(m.vertices)), replace=False)] for k, m in jaw.items()}
    for deg in range(0, 61, 5):
        R = rot_y(math.radians(deg))
        row = {'openDeg': deg, 'screws': {}}
        rotated = {}
        for k, m in jaw.items():
            mm = trimesh.Trimesh((m.vertices - PIVOT) @ R.T + PIVOT, m.faces, process=False)
            rotated[k] = mm
        for sid in ('K-head_close-01', 'K-head_close-02'):
            s = D[sid]
            seat = np.array(probe.get(sid, {}).get('seat', s['center']))
            top = seat - 1.5 * np.array([0, 0, 1.0])          # underside of a 1.5 mm head
            best, who = None, None
            for k, mm in rotated.items():
                origins = [top + np.array([r * math.cos(t), r * math.sin(t), 0]) for r in (0.0, 0.75, 1.5) for t in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
                locs, ri, _ = mm.ray.intersects_location(np.array(origins), np.repeat([[0, 0, -1.0]], len(origins), 0), multiple_hits=False)
                if len(locs):
                    d = float(np.min(origins[0][2] - locs[:, 2]))
                    if best is None or d < best:
                        best, who = d, k
            row['screws'][sid] = {'jawFreeLengthMm': round(best, 2) if best is not None else '>80', 'firstJawPart': who}
        hits = {}
        for k, pts in samp.items():
            P = (pts - PIVOT) @ R.T + PIVOT
            for q, Q in stops.items():
                lo, hi = Q.bounds
                inb = np.all((P >= lo) & (P <= hi), axis=1)
                if not inb.any():
                    continue
                PP = P[inb]
                iv = geom.solid_intervals(Q, PP - np.array([0, 0, 200.0]), [0, 0, 1.0])
                n = int(sum(any(a + 0.05 < 200.0 < b - 0.05 for a, b in ints) for ints in iv))
                if n:
                    hits[f'{k}->{q}'] = n
        row['jawInterference'] = hits
        del rotated
        gc.collect()
        res['angles'].append(row)
        print(deg, row['screws'], hits, flush=True)
    # corridor below the jaw with the jaw removed: the rest of the robot
    rest = {}
    for sid in ('K-head_close-01', 'K-head_close-02'):
        seat = np.array(probe.get(sid, {}).get('seat', D[sid]['center'])); top = seat - np.array([0, 0, 1.5])
        best = None; who = None
        for k in others:
            m = geom.mesh(k)
            if m.bounds[0][0] > top[0] + 2 or m.bounds[1][0] < top[0] - 2 or m.bounds[0][1] > top[1] + 2 or m.bounds[1][1] < top[1] - 2:
                continue
            origins = np.array([top + np.array([r * math.cos(t), r * math.sin(t), 0]) for r in (0.0, 0.75, 1.5) for t in np.linspace(0, 2 * math.pi, 8, endpoint=False)])
            locs, ri, _ = m.ray.intersects_location(origins, np.repeat([[0, 0, -1.0]], len(origins), 0), multiple_hits=False)
            if len(locs):
                d = float(np.min(top[2] - locs[:, 2]))
                if d > 0.05 and (best is None or d < best):
                    best, who = d, k
        rest[sid] = {'freeLengthWithoutJawMm': round(best, 2) if best is not None else '>robot', 'firstPart': who}
    res['withoutJaw'] = rest
    print(rest)
    Path(out).write_text(json.dumps(res, indent=1))


if __name__ == '__main__':
    main(sys.argv[1])
