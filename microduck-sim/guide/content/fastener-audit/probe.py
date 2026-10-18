#!/usr/bin/env python3
"""Ray-cast every candidate screw against the V1.6 meshes and measure seat, stack, hole diameters, engagement,
blind-end margin, intrusion into other parts, head clearance and straight-driver access.

Rays run parallel to the screw axis: one on the axis and eight at each radius in RADII. Solid intervals come from
face-normal entry/exit (geom.solid_intervals). t is measured along the insertion axis from the nominal centre.
Run once per mesh set: --kind full (full-resolution V1.6 meshes) and --kind guide (meshes drawn by the viewer).
"""
import argparse, json, math, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import geom
import screw_defs

RADII = [0.5, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.35, 1.4, 1.5, 1.6, 1.75, 1.9, 2.0, 2.25, 2.5, 2.75, 3.0, 3.5]
NANG = 8
BACK = 70.0          # rays start this far behind the nominal centre
AHEAD = 12.0         # and extend this far past the tip
SCREW_MODELS = ('camera_clamp_screw_', 'speaker_mount_screw_')
G = Path(__file__).resolve().parents[2]


def step_parts():
    """Parts present at each step (show + add), evaluated from the current steps.py with a stub context built from the
    guide-data part list. Falls back to the step lists stored in guide-data.json."""
    d = json.loads((G / 'data/guide-data.json').read_text())
    parts = {p['key']: {'module': p['module'], 'bounds': p['bounds']} for p in d['parts']}
    try:
        from collections import defaultdict
        sys.path.insert(0, str(G / 'content'))
        import steps as content

        class Ctx:
            def __init__(self):
                self.parts = parts
                self.L = defaultdict(lambda: 100.0)

            def has(self, k):
                return k in self.parts

            def keys(self, *ks):
                return [k for k in ks if k in self.parts]

            def module_keys(self, m):
                return [k for k, p in self.parts.items() if p['module'] == m]

            def cam(self, *a, **k):
                return {'position': [0, 0, 0], 'target': [0, 0, 0]}

        _, steps, _ = content.build(Ctx())
        return {s['id']: set(s['show']) | set(s['add']) for s in steps}, 'steps.py'
    except Exception as e:  # noqa: BLE001
        print('steps.py evaluation failed, using guide-data step lists:', e, file=sys.stderr)
        return {s['id']: set(s['show']) | set(s['add']) for s in d['steps']}, 'guide-data.json'


def candidates(kind, c, a, L):
    lo = np.minimum(c - BACK * a, c + (L + AHEAD) * a) - 3.0
    hi = np.maximum(c - BACK * a, c + (L + AHEAD) * a) + 3.0
    out = []
    for k in geom.available(kind):
        if k.startswith(SCREW_MODELS) or k == 'jaw_support_guide_pose':
            continue
        m = geom.mesh(k, kind)
        b = m.bounds
        if np.all(b[1] >= lo) and np.all(b[0] <= hi):
            out.append(k)
    return out


def cast(kind, key, c, a, u, v):
    m = geom.mesh(key, kind)
    origins = [c - BACK * a]
    meta = [(0.0, 0)]
    for r in RADII:
        for j in range(NANG):
            th = 2 * math.pi * (j + 0.5) / NANG
            origins.append(c - BACK * a + r * (math.cos(th) * u + math.sin(th) * v))
            meta.append((r, j))
    iv = geom.solid_intervals(m, np.array(origins), a)
    res = {}
    for (r, j), ints in zip(meta, iv):
        res[(r, j)] = [[x - BACK, y - BACK] for x, y in ints]
    return res


def solid_at(ints, t):
    return any(x <= t <= y for x, y in ints)


def analyse(s, kind, present):
    c = np.array(s['center']); a = np.array(s['axis']); a = a / np.linalg.norm(a)
    u, v, _ = geom.frame(a)
    d, L, hd, hh = s['diameterMm'], s['lengthMm'], s['headDiameterMm'], s['headHeightMm']
    keys = candidates(kind, c, a, L)
    rays = {k: cast(kind, k, c, a, u, v) for k in keys}
    ts = np.round(np.arange(-6.0, L + 4.0 + 1e-9, 0.05), 3)
    declared = list(s['throughPart']) + [s['intoPart']]
    tip_target = s['expect'].get('tipTarget')
    declared_all = set(declared) | ({tip_target} if tip_target else set())

    def frac(k, r, t):
        return sum(solid_at(rays[k][(r, j)], t) for j in range(NANG)) / NANG

    def frac_any(k, t):
        """Fraction of the 8 directions with material at any probed radius (the part surrounds the axis here)."""
        return sum(any(solid_at(rays[k][(r, j)], t) for r in RADII) for j in range(NANG)) / NANG

    # head seat: first t (from -4) where a declared part meets the head annulus (r=1.6, or 1.75 for M2.6) in >= 5/8 rays
    r_seat = 1.6 if hd <= 4.0 else 1.75
    seat = None
    for t in ts[ts >= -4.0]:
        for k in declared:
            if k in rays and frac(k, r_seat, t) >= 5 / 8:
                seat = (float(t), k); break
        if seat:
            break
    t0 = seat[0] if seat else 0.0
    tip = t0 + L
    r_wall = min(RADII, key=lambda r: abs(r - (d / 2 + 0.3)))
    r_eng = min(RADII, key=lambda r: abs(r - 0.45 * d))
    r_core = 0.7 if d <= 2.0 else 0.8

    # part sequence along the shank: any part with material within r=3.5 in >= 4/8 directions
    seq = []
    for k in keys:
        on = [t for t in ts if t0 - 0.01 <= t <= tip + 3 and frac_any(k, t) >= 4 / 8]
        if on:
            seq.append({'part': k, 'from': round(on[0] - t0, 2), 'to': round(on[-1] - t0, 2)})
    seq.sort(key=lambda x: x['from'])

    def void_r(k, t):
        """Largest probed radius that is void in all 8 directions at t (0 when the axis is solid)."""
        if solid_at(rays[k][(0.0, 0)], t):
            return 0.0
        last = 0.0
        for r in RADII:
            if any(solid_at(rays[k][(r, j)], t) for j in range(NANG)):
                return last
            last = r
        return RADII[-1]

    per_part = {}
    for k in declared:
        if k not in rays:
            per_part[k] = {'present': False}
            continue
        span = [t for t in ts if t0 - 0.01 <= t <= tip and frac_any(k, t) >= 4 / 8]
        if not span:
            per_part[k] = {'present': True, 'inShankPath': False}
            continue
        vr = [void_r(k, t) for t in span]
        axis_void = sum(1 for x in vr if x > 0) / len(vr)
        eng = [geom.clip_len(rays[k][(r_eng, j)], t0, tip - 0.3) for j in range(NANG)]
        through_len = geom.clip_len([[span[0], span[-1]]], t0, tip)
        vr_pos = [x for x in vr if x > 0]
        per_part[k] = {'present': True, 'inShankPath': True,
                       'fromMm': round(span[0] - t0, 2), 'toMm': round(span[-1] - t0, 2), 'lengthInShankMm': round(through_len, 2),
                       'axisVoidFraction': round(axis_void, 3),
                       'holeDiameterMinMm': round(2 * min(vr_pos), 2) if vr_pos else 0.0,
                       'holeDiameterMedianMm': round(2 * float(np.median(vr_pos)), 2) if vr_pos else 0.0,
                       'threadEngagedMm': round(float(np.median(eng)), 2), 'threadEngagedMinMm': round(float(min(eng)), 2)}

    # first solid on the axis or the minor-diameter ring after the seat (blind end / obstruction)
    core_hits = []
    for k in keys:
        for r in (0.0, r_core):
            for j in ([0] if r == 0.0 else range(NANG)):
                for x, y in rays[k][(r, j)]:
                    if y > t0 + 0.02 and x < tip + 6:
                        core_hits.append((max(x, t0), k))
    core_hits.sort()
    blind = core_hits[0] if core_hits else None

    # shank intrusion into parts that are not declared
    intr = []
    for k in keys:
        if k in declared_all:
            continue
        lens = [geom.clip_len(rays[k][(r, j)], t0 + 0.02, tip) for r in RADII if r <= d / 2 for j in range(NANG)]
        if lens and max(lens) > 0.05:
            intr.append({'part': k, 'maxSolidMm': round(max(lens), 2)})
    # head envelope (any part, including the seat part, more than 0.1 mm inside the head cylinder)
    head = []
    for k in keys:
        lens = [geom.clip_len(rays[k][(r, j)], t0 - hh, t0 - 0.05) for r in RADII if r <= hd / 2 for j in range(NANG)]
        if lens and max(lens) > 0.1:
            head.append({'part': k, 'maxSolidMm': round(max(lens), 2)})

    # straight driver: shaft diameter 3 mm on the axis behind the head
    top = t0 - hh

    def driver(only):
        drv = {}
        for k in keys:
            if only is not None and k not in only:
                continue
            best = None
            for r in [0.0] + [x for x in RADII if x <= 1.5]:
                for j in ([0] if r == 0.0 else range(NANG)):
                    for x, y in rays[k][(r, j)]:
                        if x < top - 0.02:
                            gap = top - min(y, top)
                            if best is None or gap < best:
                                best = gap
            if best is not None:
                drv[k] = round(best, 2)
        return dict(sorted(drv.items(), key=lambda kv: kv[1])[:4])

    drv_step = driver(present)
    drv_final = driver(None)
    free = round(BACK - hh - 0.5, 1)

    # hole hit: every declared part on the path has a hole on this axis (axis void over >= 90 % of its span)
    hit_parts = {}
    for k in declared:
        pp = per_part[k]
        hit_parts[k] = bool(pp.get('inShankPath')) and pp['axisVoidFraction'] >= 0.9
    return {
        'id': s['id'], 'kind': kind,
        'seatOffsetMm': round(t0, 2), 'seatPart': seat[1] if seat else None,
        'seat': [round(float(x), 3) for x in (c + t0 * a)],
        'sequence': seq, 'perPart': per_part,
        'firstCoreSolidAfterSeatMm': round(blind[0] - t0, 2) if blind else None, 'firstCoreSolidPart': blind[1] if blind else None,
        'tipMarginMm': round(blind[0] - tip, 2) if blind else None,
        'intrusions': intr, 'headClash': head,
        'driverStep': {'clearMm': next(iter(drv_step.values()), f'>{free}'), 'obstacles': drv_step},
        'driverFinal': {'clearMm': next(iter(drv_final.values()), f'>{free}'), 'obstacles': drv_final},
        'holeHit': all(hit_parts.values()), 'holeHitParts': hit_parts,
        'radii': {'seat': r_seat, 'wall': r_wall, 'thread': r_eng, 'core': r_core},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--kind', default='full')
    ap.add_argument('--out', required=True)
    ap.add_argument('--ids', nargs='*')
    ap.add_argument('--defs', help='optional JSON list of extra/override definitions')
    a = ap.parse_args()
    ds = screw_defs.defs()
    if a.defs:
        extra = json.loads(Path(a.defs).read_text())
        byid = {d['id']: d for d in ds}
        for e in extra:
            byid[e['id']] = e
        ds = list(byid.values())
    if a.ids:
        ds = [d for d in ds if d['id'] in a.ids]
    present, present_src = step_parts()
    print('step presence from', present_src, flush=True)
    outp = Path(a.out)
    res = json.loads(outp.read_text()) if outp.exists() else {}
    for s in ds:
        r = analyse(s, a.kind, present.get(s['step']))
        res[s['id']] = r
        outp.write_text(json.dumps(res, indent=1))
        print(s['id'], 'hit', r['holeHit'], 'seat', r['seatOffsetMm'], r['seatPart'], flush=True)


if __name__ == '__main__':
    main()
