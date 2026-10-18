#!/usr/bin/env python3
"""Design probe for route candidates: per-segment clearance of candidate polylines (raw polyline and the guide
viewer's centripetal Catmull-Rom curve) against the q = 0 scene (guide audit solids with the release cap and V1.9
pack, plus the new parts of scene_check.new_parts). Optional: rebuild the clips first (to test clip geometry).
Usage: probe_route.py candidates.json [out.json]
candidates.json: {"name": {"points": [[x, y, z], ...], "radius": 1.7, "skipStartMm": 0, "skipEndMm": 0,
                            "ignore": ["part", ...]}, ...}
Prints, per candidate and mode, the minimum clearance (distance to the nearest surface minus the radius) and, for each
segment with clearance < 0.3 mm, the segment index, its worst clearance, the part and the point.
"""
from __future__ import annotations

import json
import sys

import numpy as np
import trimesh

import importlib.util

import ext_lib as E

# this folder's cable_check.py (the guide's interference-audit folder has a module of the same name on sys.path)
_spec = importlib.util.spec_from_file_location('ext19_cable_check', E.HERE / 'cable_check.py')
_cc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cc)
nearest, samples = _cc.nearest, _cc.samples
import scene_check as SCN  # noqa: E402
from cables import spline_samples  # noqa: E402


def main():
    cand = json.loads(open(sys.argv[1]).read())
    man = E.ia_lib.manifest()
    allp = []
    for c in cand.values():
        allp += [p[:3] for p in c['points']]
    allp = np.array(allp, float)
    lo, hi = allp.min(0) - 12, allp.max(0) + 12
    meshes = []
    for k, m in man.items():
        if k in ('head_cap', 'rear_pack'):
            continue
        b = np.array(m['bounds'])
        if np.any(b[0] > hi) or np.any(b[1] < lo):
            continue
        v, f = E.ia_lib.load_solid(k)
        meshes.append((k, trimesh.Trimesh(v, f, process=False)))
    meshes.append(('rear_pack_v19', trimesh.load(E.PACK_V19, force='mesh')))
    for nm, (M, body, capg, _) in SCN.new_parts().items():
        meshes.append((nm, E.tm(M)))
    out = {}
    for name, c in cand.items():
        P = np.array([p[:3] for p in c['points']], float)
        r = float(c.get('radius', 1.7))
        ign = set(c.get('ignore', []))
        ms = [(k, m) for k, m in meshes if k not in ign]
        rec = {}
        for mode in ('polyline', 'drawn-spline'):
            if mode == 'polyline':
                pts, s, L = samples(P)
                seg = np.searchsorted(np.cumsum(np.r_[0, np.linalg.norm(np.diff(P, axis=0), axis=1)]), s, side='right') - 1
            else:
                pts, seg = spline_samples(P)
                s = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
                L = s[-1]
            keep = (s >= c.get('skipStartMm', 0)) & (s <= L - c.get('skipEndMm', 0))
            d, ins, who = nearest(ms, pts[keep], maxd=8.0)
            clr = d - r
            segk = np.asarray(seg)[keep]
            bad = {}
            for i in np.argsort(clr):
                if clr[i] >= 0.3:
                    break
                sg = int(min(segk[i], len(P) - 2))
                if sg not in bad:
                    bad[sg] = {'clearanceMm': round(float(clr[i]), 3), 'part': who[i], 'at': np.round(pts[keep][i], 2).tolist(),
                               'centrelineInside': bool(ins[i])}
            rec[mode] = {'min': round(float(clr.min()), 3), 'part': who[int(np.argmin(clr))], 'badSegments': bad}
            print(name, mode, 'min', rec[mode]['min'], rec[mode]['part'], flush=True)
            for sg in sorted(bad):
                print('    seg', sg, bad[sg], flush=True)
        out[name] = rec
    if len(sys.argv) > 2:
        E.jdump(out, sys.argv[2])


if __name__ == '__main__':
    main()
