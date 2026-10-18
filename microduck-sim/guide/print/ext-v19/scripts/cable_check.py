#!/usr/bin/env python3
"""Final-pose cable penetration of the V1.9 routes (route-v19.json): the neck bundle (r 1.7), the fan wires and the
audio jumper wires (r 0.65) against every solid at q = 0, with the release cap, the V1.9 rear pack and the new parts
(clips, retainer, speaker, amplifier and housings, resistor envelope, the assumed Pi mini-HDMI socket envelope).
Two centrelines per route, as the guide's interference-audit cables.py samples them: the raw polyline (every 0.5 mm)
and the curve the guide viewer draws (centripetal Catmull-Rom through the points, cables.spline_samples, imported
read-only). Clearance = exact distance to the part surface minus the wire radius (negative = the wire envelope
enters the part; inside = the centreline is inside the part).
Excluded (intended): the first 3.0 mm of each fan wire (from its Pi housing) and the first and last 3.0 mm of each
audio wire (amp housing, Pi housing).
Also checks the bundle against amp housings lowered 2.75 mm (pins 1.27 mm above the amp board instead of 4.02 mm).
Proposed guide cables (route-v19.json guideCables: pi-trunk, imu, uart at their guide radii, default 0.9): checked from
their V1.8 pack-notch point to 3 mm short of the Pi housing (the V1.8 part below the notch is unchanged; the V1.9 pack
check already covers it).
Unchanged guide cables against the changed solids (cables.py sampling, 0.25 mm, drawn spline and polyline, guide
radius, finding = tube depth > 0.1 mm as in cables.py): every other guide cable against the new parts (clips, raised
clip screw heads, retainer, audio parts, resistor envelope, mini-HDMI envelope) and against the release cap, with the
V1.8 cap clearance of the same cable for comparison.
Writes ../checks/cable-check-v19.json.
"""
from __future__ import annotations

import json

import numpy as np
import trimesh

import clips_v19 as C
import ext_lib as E
import scene_check as SCN
from cables import polyline_samples, spline_samples   # guide viewer curve (read-only import)
from nr_lib import body_of

STEP = 0.5
END_SKIP = 3.0


def samples(P):
    P = np.asarray(P, float)
    out, s_along = [], []
    acc = 0.0
    for i in range(len(P) - 1):
        a, b = P[i], P[i + 1]
        L = float(np.linalg.norm(b - a))
        n = max(2, int(np.ceil(L / STEP)) + 1)
        for t in np.linspace(0, 1, n)[:-1]:
            out.append(a + t * (b - a))
            s_along.append(acc + t * L)
        acc += L
    out.append(P[-1])
    s_along.append(acc)
    return np.array(out), np.array(s_along), acc


def nearest(meshes, pts, maxd=6.0):
    best = np.full(len(pts), np.inf)
    who = np.full(len(pts), '', dtype=object)
    inside = np.zeros(len(pts), bool)
    for k, m in meshes:
        lo, hi = m.bounds
        gap = np.linalg.norm(np.maximum(0, np.maximum(lo - pts, pts - hi)), axis=1)
        sel = gap < np.minimum(best, maxd)
        if not sel.any():
            continue
        ps = pts[sel]
        res = [trimesh.proximity.closest_point(m, ps[i:i + 64]) for i in range(0, len(ps), 64)]
        c = np.concatenate([r[0] for r in res])
        d = np.concatenate([r[1] for r in res])
        tri = np.concatenate([r[2] for r in res])
        ins = ((ps - c) * m.face_normals[tri]).sum(1) < 0
        d = np.where(ins, -d, d)
        better = d < best[sel]
        idx = np.where(sel)[0][better]
        best[idx] = d[better]
        who[idx] = k
        inside[idx] = ins[better]
    return best, inside, who


def unchanged_guide_cables(spec, meshes):
    g = E.ia_lib.load_guide()
    replaced = set(spec['guideCables'])
    newk = {k for k, _ in meshes if k in SCN.new_parts_names()} - {'head_cap_v19'}
    newm = [(k, m) for k, m in meshes if k in newk]
    capv19 = [(k, m) for k, m in meshes if k == 'head_cap_v19']
    v, f = E.ia_lib.load_solid('head_cap')
    capv18 = [('head_cap_v18', trimesh.Trimesh(v, f, process=False))]
    res = {}
    for c in g['cables']:
        if c['id'] in replaced:
            continue
        r = float(c.get('radius') or 0.9)
        rec = {'radius': r}
        for mode, (x, _) in (('drawn-spline', spline_samples(c['path'])), ('polyline', polyline_samples(c['path']))):
            for tag, ms in (('newParts', newm), ('capV19', capv19), ('capV18', capv18)):
                d, ins, who = nearest(ms, x, maxd=8.0)
                depth = r - d
                i = int(np.argmin(d))
                rec[f'{mode}:{tag}'] = {'minClearanceMm': float(d[i] - r) if np.isfinite(d[i]) else None,
                                        'part': who[i] or None, 'at': x[i], 'findingsDepthOver0.1': int((depth > 0.1).sum())}
        res[c['id']] = E.rnd(rec, 3)
        print('guide cable', c['id'], {k: (v['minClearanceMm'], v['part'], v['findingsDepthOver0.1'])
                                       for k, v in rec.items() if k != 'radius'}, flush=True)
    return res


def main():
    spec = json.loads((E.OUT / 'route-v19.json').read_text())
    man = E.ia_lib.manifest()
    meshes = []
    for k in man:
        if k in ('head_cap', 'rear_pack'):
            continue
        v, f = E.ia_lib.load_solid(k)
        meshes.append((k, trimesh.Trimesh(v, f, process=False)))
    meshes.append(('rear_pack_v19', trimesh.load(E.PACK_V19, force='mesh')))
    for nm, (M, body, capg, _) in SCN.new_parts().items():
        meshes.append((nm, E.tm(M)))
    housings = trimesh.load(E.AUDIO / 'study-solids' / 'amp_housings-world.stl', force='mesh')
    low = housings.copy()
    low.apply_translation([0, 0, -2.75])
    out = {'_method': __doc__.strip(), 'routes': {}}
    jobs = [('neck-bundle-v19', spec['routes'][0]['points'], spec['routes'][0]['groupRadiusMm'], 'bundle')]
    for nm, pl in spec['fanWires']['polylines'].items():
        jobs.append((f'fan-{nm}', pl, spec['fanWires']['radiusMm'], 'fan'))
    for nm, pl in spec['audioWires']['polylines'].items():
        jobs.append((f'audio-{nm}', pl, spec['audioWires']['radiusMm'], 'audio'))
    notch_s = {}
    for cid, gc in spec['guideCables'].items():
        jobs.append((f'guide-{cid}', gc['path'], float(gc['radius'] or 0.9), 'guide'))
        notch_s[f'guide-{cid}'] = np.array(gc['notchPointV18'], float)
    worst_all = []
    for name0, pl, rad, kind in jobs:
      P = np.array([p[:3] for p in pl], float)
      for mode in ('polyline', 'drawn-spline'):
        name = name0 if mode == 'polyline' else name0 + ' [drawn-spline]'
        if mode == 'polyline':
            pts, s, L = samples(P)
        else:
            pts, _ = spline_samples(P)
            s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
            L = float(s[-1])
        keep = np.ones(len(pts), bool)
        if kind == 'guide':
            j0 = int(np.argmin(np.linalg.norm(pts - notch_s[name0], axis=1)))
            keep &= s >= s[j0]
            keep &= s <= L - END_SKIP
        if kind in ('fan', 'audio'):
            keep &= s >= END_SKIP            # fan wires start in their Pi housing; audio wires start in an amp housing
        if kind == 'audio':
            keep &= s <= L - END_SKIP        # and end in their Pi housing
        ms = meshes
        if name0.startswith('audio-spk_'):
            # the speaker leads are the wires the speaker_leads_envelope reserves room for (intended)
            ms = [(k, m) for k, m in meshes if k != 'speaker_leads_envelope']
        d, ins, who = nearest(ms, pts[keep])
        clr = d - rad
        order = np.argsort(clr)
        bad = {}
        for i in order:
            if clr[i] >= 0:
                break
            k = who[i]
            if k not in bad:
                bad[k] = {'minClearanceMm': float(clr[i]), 'at': pts[keep][i], 'centrelineInside': bool(ins[i]), 'samples': 0}
            bad[k]['samples'] += 1
        rec = {'kind': kind, 'mode': mode, 'radiusMm': rad, 'lengthMm': L, 'samples': int(keep.sum()),
               'minClearanceMm': float(clr.min()), 'nearestPart': who[int(np.argmin(clr))],
               'at': pts[keep][int(np.argmin(clr))], 'penetrations': bad}
        if kind == 'bundle':
            dl, _, _ = nearest([('amp_housings_low_variant', low)], pts[keep])
            rec['ampHousingsLowVariantClearanceMm'] = float((dl - rad).min())
            rec['ampHousingsLowVariantAt'] = pts[keep][int(np.argmin(dl))]
            dh, _, _ = nearest([('amp_housings', housings)], pts[keep])
            rec['ampHousingsStudyClearanceMm'] = float((dh - rad).min())
        out['routes'][name] = E.rnd(rec, 3)
        worst_all.append((rec['minClearanceMm'], name, rec['nearestPart']))
        print(name, 'min clearance', round(rec['minClearanceMm'], 3), rec['nearestPart'], 'penetrating', list(bad),
              ('low housings %.3f' % rec['ampHousingsLowVariantClearanceMm']) if kind == 'bundle' else '', flush=True)
    out['unchangedGuideCables'] = unchanged_guide_cables(spec, meshes)
    out['summary'] = {'routes': len(jobs), 'routesWithPenetration': [n for n, r in out['routes'].items() if r['penetrations']],
                      'worst': sorted(worst_all)[:5]}
    E.jdump(out, E.OUT / 'checks' / 'cable-check-v19.json')


if __name__ == '__main__':
    main()
