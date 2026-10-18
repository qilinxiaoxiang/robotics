#!/usr/bin/env python3
"""V1.8 head screws: ray-cast the camera screws (C-camera-01/02) and the moved Pi screws (E-pi-01..04) against the
meshes the guide draws, and write the measured evidence into fasteners.json.

Method (as fastener-audit/probe.py): rays parallel to the screw axis, one on the axis and eight at each radius in
RADII, from 70 mm behind the nominal centre to 12 mm past the tip. Solid intervals come from entry/exit crossings
(face normal against the ray). t runs along the insertion axis from the nominal centre (the head seat).
Per screw: head seat, the stack of parts along the shank with their hole diameter range, thread engagement in
intoPart (less 0.3 mm tip lead-in, the fasteners.json convention), margin from the tip to the next solid,
intrusion of the shank into any other part, head clash, and straight 3 mm driver clearance behind the head at the
step (bench: only the step's parts) and on the assembled robot. Writes camera-screws-v18.json and updates the
records in ../fasteners.json (evidence, stack, checks, engagement, pilot range, tip margin, driver clearance).
"""
from __future__ import annotations

import json
import sys

import numpy as np
import trimesh

from ia_lib import GUIDE, HERE, WORLD, WORLD_FILE, decode_guide_part, load_guide, rnd

RADII = [0.5, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.35, 1.4, 1.5, 1.6, 1.75, 1.9, 2.0, 2.25, 2.5, 2.75, 3.0, 3.5]
NANG = 8
BACK, AHEAD = 70.0, 12.0
DRIVER_R = 1.5          # 3 mm straight driver
PILOT_RANGE = {'M2': (1.3, 1.8), 'M2.5': (1.9, 2.3)}
MIN_ENGAGEMENT = 1.5
FASTENERS = GUIDE / 'content' / 'fasteners.json'
IDS = ['C-camera-01', 'C-camera-02', 'E-pi-01', 'E-pi-02', 'E-pi-03', 'E-pi-04']
# Parts present when each screw is driven (bench steps): the step's show + add.
BENCH = {'camera': ['face_panel', 'eye_trim', 'camera_board'],
         'pi': None}  # resolved from the guide step (cap + speaker + amplifier + Pi group)


def basis(a):
    a = np.asarray(a, float)
    a = a / np.linalg.norm(a)
    u = np.cross(a, [0, 0, 1.0])
    if np.linalg.norm(u) < 1e-6:
        u = np.cross(a, [0, 1.0, 0])
    u /= np.linalg.norm(u)
    return a, u, np.cross(a, u)


def intervals_from(t, sgn, length):
    """Solid intervals [(t0, t1)] in [0, length] from one ray's sorted crossings (sgn < 0 entering, > 0 leaving)."""
    order = np.argsort(t)
    out, depth, start = [], 0, None
    for k in order:
        if sgn[k] < 0:          # entering
            if depth == 0:
                start = t[k]
            depth += 1
        elif sgn[k] > 0:        # leaving
            depth = max(0, depth - 1)
            if depth == 0 and start is not None:
                if t[k] - start > 1e-4:
                    out.append((float(start), float(t[k])))
                start = None
    if start is not None:
        out.append((float(start), float(length)))
    return [(max(a, 0.0), min(b, length)) for a, b in out if b > 0 and a < length]


def intervals_batch(mesh, origins, direction, length):
    """Solid intervals per ray for all origins (one intersects_location call per mesh)."""
    O = np.asarray(origins, float)
    D = np.tile(np.asarray(direction, float), (len(O), 1))
    loc, idx, tri = mesh.ray.intersects_location(O, D, multiple_hits=True)
    out = [[] for _ in range(len(O))]
    if not len(loc):
        return out
    t = np.einsum('ij,j->i', loc - O[idx], direction)
    sgn = mesh.face_normals[tri] @ direction
    for i in range(len(O)):
        sel = idx == i
        if sel.any():
            out[i] = intervals_from(t[sel], sgn[sel], length)
    return out


def solid_at(ivs, t):
    return any(a - 1e-6 <= t <= b + 1e-6 for a, b in ivs)


def main():
    g = load_guide()
    gparts = {p['key']: p for p in g['parts']}
    steps = {s['id']: s for s in g['steps']}
    fast = json.loads(FASTENERS.read_text())
    recs = {s['id']: s for s in fast['screws']}
    meshes = {}

    def mesh(k):
        if k not in meshes:
            if k in WORLD_FILE:
                m = trimesh.load(WORLD / WORLD_FILE[k], force='mesh', process=True)
            else:
                v, f = decode_guide_part(gparts[k])
                m = trimesh.Trimesh(v, f, process=True)
            meshes[k] = m
        return meshes[k]

    def present(step_id):
        s = steps[step_id]
        mods = {}
        for p in g['parts']:
            mods.setdefault(p['module'], []).append(p['key'])
        out = []
        for r in (s.get('show') or []) + (s.get('add') or []):
            for k in (mods[r] if r in mods else [r]):
                if k in gparts and k not in out:
                    out.append(k)
        return out

    results = {}
    for sid in IDS:
        r = recs[sid]
        c = np.array(r['center'], float)
        a, u, w = basis(r['axis'])
        L = float(r['lengthMm'])
        rh, hh = r['headDiameterMm'] / 2, r['headHeightMm']
        o0 = c - BACK * a
        span = BACK + L + AHEAD
        lo, hi = np.minimum(c - BACK * a, c + (L + AHEAD) * a) - 4, np.maximum(c - BACK * a, c + (L + AHEAD) * a) + 4
        cand = [k for k, p in gparts.items() if np.all(np.array(p['bounds'][1]) >= lo) and np.all(np.array(p['bounds'][0]) <= hi)]
        # ray families: fam[radius][part] = intervals per ray, t relative to the centre (one batched cast per part)
        ray_origins, ray_tag = [o0], [(0.0, 0)]
        for rad in RADII:
            for j, q in enumerate(np.linspace(0, 2 * np.pi, NANG, endpoint=False)):
                ray_origins.append(o0 + rad * (np.cos(q) * u + np.sin(q) * w))
                ray_tag.append((rad, j))
        fam = {rad: {} for rad in [0.0] + RADII}
        for k in cand:
            per_ray = intervals_batch(mesh(k), ray_origins, a, span)
            for (rad, j), ivs in zip(ray_tag, per_ray):
                lst = fam[rad].setdefault(k, [[] for _ in range(1 if rad == 0 else NANG)])
                lst[j] = [(t0 - BACK, t1 - BACK) for t0, t1 in ivs]
            for rad in fam:
                if k in fam[rad] and not any(fam[rad][k]):
                    del fam[rad][k]
        ax = fam[0.0]
        thru, into = list(r['throughParts']), r['intoPart']
        stack_parts = thru + [into]
        # stack: axis-adjacent solid spans of each stack part (take the span nearest t=0 moving forward, from the r=1.1 family
        # when the axis ray passes through an open hole)
        def spans(k):
            ss = set()
            for rad in (0.0, 1.0, 1.1, 1.2, 1.25, 1.3, 1.4, 1.5, 1.6, 1.75, 1.9, 2.0):
                for ivs in fam[rad].get(k, []):
                    for t0, t1 in ivs:
                        if t1 > -0.5 and t0 < L + AHEAD:
                            ss.add((round(t0, 2), round(t1, 2)))
            return sorted(ss)

        def hole_range(k, t):
            """Largest probed radius void on all 8 rays at t, as [2r, 2r_next]; 'closed' when the r=0.5 ring is solid."""
            best = None
            for rad in RADII:
                ivs = fam[rad].get(k)
                if ivs is None:
                    best = rad
                    continue
                if any(solid_at(iv, t) for iv in ivs):
                    break
                best = rad
            if best is None:
                return None
            nxt = [x for x in RADII if x > best + 1e-6]
            return [round(2 * best, 2), round(2 * nxt[0], 2) if nxt else None]

        stack = []
        pre_contact = None
        for k in stack_parts:
            sp = [s for s in spans(k) if s[1] > 0]
            if not sp:
                stack.append({'part': k, 'fromMm': None, 'toMm': None, 'holeDiameterRangeMm': None, 'hit': False})
                continue
            # merge spans that overlap within 0.05 mm
            merged = [list(sp[0])]
            for t0, t1 in sp[1:]:
                if t0 <= merged[-1][1] + 0.05:
                    merged[-1][1] = max(merged[-1][1], t1)
                else:
                    merged.append([t0, t1])
            t0, t1 = merged[0]
            if k == into:
                # The thread engages where the pilot wall surrounds the shank: at the smallest radius that is solid on all
                # 8 rays at mid-depth of the span, take the latest entry of the interval each ray is in there. Material a
                # ray grazes before that (a chamfer, a key) is reported separately and not counted as engagement.
                tm = (max(t0, 0) + min(t1, L)) / 2
                for rad in RADII:
                    ivs = fam[rad].get(k)
                    if ivs and all(solid_at(iv, tm) for iv in ivs):
                        wall = max(next(t0x for t0x, t1x in iv if t0x - 1e-6 <= tm <= t1x + 1e-6) for iv in ivs)
                        if wall - t0 > 0.02:
                            # Material ahead of the wall counts as a shank graze only when a ray within the thread crest
                            # radius (diameter / 2) meets it; spans() also probes wider rays (up to the head radius), and
                            # material seen only there is clear of the screw and is not reported.
                            for rr in [x for x in RADII if x <= r['diameterMm'] / 2 + 1e-6]:   # shank and thread crest
                                if any(any(t0x < wall - 0.02 and t1x > t0 for t0x, t1x in iv) for iv in fam[rr].get(k, [])):
                                    pre_contact = {'fromMm': round(t0, 2), 'toMm': round(wall, 2), 'atRadiusMm': rr}
                                    break
                        t0 = wall
                        break
            mid = (max(t0, 0) + min(t1, L)) / 2
            stack.append({'part': k, 'fromMm': round(t0, 2), 'toMm': round(t1, 2), 'holeDiameterRangeMm': hole_range(k, mid), 'hit': True})
        into_rec = next(s for s in stack if s['part'] == into)
        engagement = round(L - into_rec['fromMm'] - 0.3, 2) if into_rec['hit'] else None
        pilot = into_rec['holeDiameterRangeMm']
        # head seat: first solid under the head ring (radius between the shank and the head edge) ahead of t=-hh
        seat = None
        for rad in (1.25, 1.5, 1.75, 1.9):
            for k in stack_parts:
                for ivs in fam[rad].get(k, []):
                    for t0, t1 in ivs:
                        if t1 > -hh - 0.3 and (seat is None or t0 < seat):
                            seat = t0
        # tip margin: first solid on the axis ray past the tip
        past = [t0 - L for k, ivs in ax.items() for t0, t1 in ivs[0] if t0 >= L - 1e-3]
        tip_margin = round(min(past), 2) if past else None
        tip_part = None
        if past:
            for k, ivs in ax.items():
                for t0, t1 in ivs[0]:
                    if abs(t0 - L - min(past)) < 1e-6:
                        tip_part = k
        # intrusion: shank (r <= 1.0) solid in a part outside the stack between the seat and the tip
        intr = {}
        for rad in (0.0, 0.5, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0):
            for k, ivs in fam[rad].items():
                if k in stack_parts:
                    continue
                for iv in ivs:
                    for t0, t1 in iv:
                        if t1 > 0 and t0 < L:
                            intr[k] = max(intr.get(k, 0.0), min(t1, L) - max(t0, 0))
        # head clash: any part other than the head seat part with solid in the head cylinder (r <= rh, t in [-hh, 0])
        clash = {}
        for rad in [x for x in [0.0] + RADII if x <= rh + 1e-6]:
            for k, ivs in fam[rad].items():
                if k == thru[0]:
                    continue
                for iv in ivs:
                    for t0, t1 in iv:
                        if t1 > -hh and t0 < 0:
                            clash[k] = max(clash.get(k, 0.0), min(t1, 0) - max(t0, -hh))
        # driver clearance behind the head (rays r <= 1.5, t from -hh back to -BACK), at the step and on the robot
        def driver_clear(keys):
            best = BACK - hh - 2.0
            who = None
            for rad in [x for x in [0.0] + RADII if x <= DRIVER_R + 1e-6]:
                for k, ivs in fam[rad].items():
                    if k not in keys or k == thru[0]:
                        continue
                    for iv in ivs:
                        for t0, t1 in iv:
                            if t1 <= -hh:
                                d = -hh - t1
                                if d < best:
                                    best, who = d, k
            return (f'>{best:.1f}' if who is None else round(best, 2)), who
        step_keys = set(BENCH.get(r['step']) or present(r['step']))
        d_step, who_step = driver_clear(step_keys)
        d_robot, who_robot = driver_clear(set(gparts))
        size = r['spec'].split()[0]
        checks = {
            'fullMeshHit': all(s['hit'] for s in stack),
            'guideMeshHit': all(s['hit'] for s in stack),   # the guide draws these exact meshes (print/world files)
            'seatWithin0_3mm': seat is not None and abs(seat) <= 0.3,
            'throughClearanceOk': all(s['holeDiameterRangeMm'] and s['holeDiameterRangeMm'][0] >= r['diameterMm'] - 0.05 for s in stack[:-1]),
            'pilotInTapRange': bool(pilot) and PILOT_RANGE[size][0] <= pilot[0] <= PILOT_RANGE[size][1],
            'engagementOk': engagement is not None and engagement >= MIN_ENGAGEMENT,
            'noBottoming': tip_margin is None or tip_margin > 0.2,
            'noIntrusion': not intr,
            'noHeadClash': not clash,
        }
        ev = (f"Ray cast, guide meshes (print/world V1.8 files for the head set; full-build source meshes moved by their shiftMm for the rest): "
              f"head seats on {thru[0]} {seat:+.2f} mm from the nominal centre; stack " +
              '; '.join(f"{s['part']} {s['fromMm']}-{s['toMm']} mm (hole {s['holeDiameterRangeMm'][0]}-{s['holeDiameterRangeMm'][1]} mm)" if s['hit'] and s['holeDiameterRangeMm'] else f"{s['part']} MISSED" for s in stack) +
              f"; thread engagement in {into} {engagement} mm ({round(L - into_rec['fromMm'], 2)} mm of shank in the pilot less 0.3 mm tip lead-in)" +
              (f"; before the pilot wall one shank ray at radius {pre_contact['atRadiusMm']} mm grazes {into} material from {pre_contact['fromMm']} to {pre_contact['toMm']} mm (not counted)" if pre_contact else '') + '; ' +
              (f"{tip_margin} mm to the first solid past the tip ({tip_part})" if tip_margin is not None else 'pilot open past the tip') +
              f"; intrusions {len(intr)}" + (f" ({', '.join(f'{k} {v:.2f} mm' for k, v in intr.items())})" if intr else '') +
              f"; head clash {len(clash)}" + (f" ({', '.join(f'{k} {v:.2f} mm' for k, v in clash.items())})" if clash else '') +
              f"; straight 3 mm driver clear {d_step} mm at the {r['step']} step" + (f" (then {who_step})" if who_step else '') +
              f", {d_robot} mm on the assembled robot" + (f" (then {who_robot})" if who_robot else '') + '.')
        results[sid] = {'center': r['center'], 'axis': r['axis'], 'spec': r['spec'], 'seatMm': rnd(seat, 3) if seat is not None else None,
                        'stack': stack, 'engagementMm': engagement, 'pilotDiameterRangeMm': pilot, 'tipMarginMm': tip_margin, 'tipPart': tip_part,
                        'intrusions': rnd(intr, 3) if intr else {}, 'headClash': rnd(clash, 3) if clash else {}, 'preEngagementContact': pre_contact,
                        'driverClearAtStepMm': d_step, 'driverStepObstacle': who_step, 'driverClearOnRobotMm': d_robot, 'driverRobotObstacle': who_robot,
                        'checks': checks, 'candidateParts': cand, 'evidence': ev}
        print(sid, 'seat', rnd(seat, 3) if seat is not None else None, 'eng', engagement, 'pilot', pilot, 'tip', tip_margin, tip_part,
              'intr', list(intr), 'clash', list(clash), 'driver', d_step, d_robot, 'checks', all(checks.values()), file=sys.stderr, flush=True)
        # write back
        r['stack'] = [{k: v for k, v in s.items() if k != 'hit'} for s in stack]
        r['engagementMm'] = engagement
        r['pilotDiameterRangeMm'] = pilot
        r['tipMarginMm'] = tip_margin
        r['driverClearAtStepMm'] = d_step
        r['checks'] = checks
        r['verified'] = all(checks.values())
        if sid.startswith('C-camera'):
            r['evidence'] = ev
        else:
            r['evidence'] = r['evidence'].split(' V1.8 cap:')[0] + ' V1.8 cap: seat moved [-4.6, 0, 1.0] with the Pi (V1.7 verify-cap x shift plus the V1.8 rail raise, print/world/v18-sources.json). Re-measured on the V1.8 cap: ' + ev

    # camera board versus the jumper-wire ends while both are seated (the cap-on step text quotes this gap)
    cam = mesh('camera_board')
    gaps = {}
    for k in gparts:
        if k.startswith('head_pi_gpio_pin_') and k.endswith('_receiving'):
            m = mesh(k)
            pts = np.vstack([m.vertices, trimesh.sample.sample_surface(m, 400, seed=0)[0]])
            d = cam.nearest.on_surface(pts)[1]
            gaps[k] = rnd(d.min(), 3)
    nearest = min(gaps, key=gaps.get)
    results['_cameraBoardToJumperEnds'] = {'minMm': gaps[nearest], 'nearest': nearest, 'perPin': gaps,
                                           'note': 'exact distance from each jumper-wire end envelope (sampled surface + vertices) to the camera board solid, both seated'}
    print('camera board to jumper ends', gaps[nearest], nearest, file=sys.stderr)

    counts = fast['counts']
    S = fast['screws']
    counts['verified'] = sum(bool(s.get('verified')) for s in S)
    counts['fullMeshHit'] = sum(bool((s.get('checks') or {}).get('fullMeshHit')) for s in S)
    counts['guideMeshHit'] = sum(bool((s.get('checks') or {}).get('guideMeshHit')) for s in S)
    FASTENERS.write_text(json.dumps(fast, indent=1, ensure_ascii=False) + '\n')
    (HERE / 'camera-screws-v18.json').write_text(json.dumps({'frame': 'robot frame, mm; x forward, y left, z up',
                                                             'method': __doc__.strip(), 'screws': results}, indent=1))
    print(json.dumps({k: v['checks'] for k, v in results.items() if not k.startswith('_')}))


if __name__ == '__main__':
    main()
