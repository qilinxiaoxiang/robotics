#!/usr/bin/env python3
"""q = 0 distances (centreline to surface, minus 1.7 mm) from each candidate route to named head parts. -> part_dist_q0.json"""
import sys, json, os
os.environ['EXT19_IA_CACHE'] = '/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/ia-cache'
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/print/ext-v19/scripts')
import numpy as np, trimesh
import ext_lib as E
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, 'routes_candidates.json')))
names = ['speaker', 'speaker_retainer', 'speaker_tape', 'amplifier', 'clip_cap', 'clip_head', 'pi', 'head_pi_zero_w_header_base', 'camera_board', 'face_panel',
         'jaw_frame', 'motor15', 'jaw_support', 'head_yaw_link', 'motor13', 'motor14', 'head_bottom', 'neck_pitch', 'motor11', 'motor12', 'head_roll_ring_a', 'head_roll_ring_b']
M = {}
for k in names:
    v, f = E.ia_lib.load_solid(k); M[k] = trimesh.Trimesh(v, f, process=False); print(k, len(f), flush=True)
def dens(P, step=0.5):
    out = []
    for a, b in zip(P[:-1], P[1:]):
        n = max(2, int(np.ceil(np.linalg.norm(b - a) / step))); out.append(np.linspace(a, b, n, endpoint=False))
    out.append(P[-1:]); return np.vstack(out)
res = {}
for rname, r in R.items():
    P = dens(np.array([p[:3] for p in r['points']], float)); res[rname] = {}
    for k, m in M.items():
        cs, ds, ts = [], [], []
        for i in range(0, len(P), 64):
            c, d, t = trimesh.proximity.closest_point(m, P[i:i + 64]); cs.append(c); ds.append(d); ts.append(t)
        c, d, t = np.vstack(cs), np.concatenate(ds), np.concatenate(ts)
        inside = ((P - c) * m.face_normals[t]).sum(1) < 0
        s = np.where(inside, -d, d) - 1.7
        j = int(np.argmin(s)); res[rname][k] = {'clearanceMm': round(float(s[j]), 2), 'routeAt': [round(float(x), 1) for x in P[j]]}
json.dump(res, open(os.path.join(HERE, 'part_dist_q0.json'), 'w'), indent=1)
for rname in res: print(rname, {k: v['clearanceMm'] for k, v in sorted(res[rname].items(), key=lambda kv: kv[1]['clearanceMm'])})
