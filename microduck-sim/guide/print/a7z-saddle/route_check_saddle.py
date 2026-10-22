#!/usr/bin/env python3
"""Saddle-era cable routes (D-022, 2026-10-22): the Radxa Cubie A7Z leaves the head and sits in the printed saddle on the
torso roof (build_saddle.py), so every wire that ended on the A7Z header in the head now ends on the same pin in the saddle.

    route_check_saddle.py --write   rewrite the changed routes in guide/content/routes.json (anchors + saddle tails below)
    route_check_saddle.py           check the changed/new routes: drawn spline and polyline sampled at 0.25 mm against the
                                    audit solids (guide-data.json parts plus the saddle world files), penetration > 0.1 mm
                                    reported with its arc position; the gate (interference-audit/cables.py) accepts a
                                    finding only within 8 mm of a cable end (inside its housing, plug or terminal).

Frame: guide world, mm, x forward, y left, z up. Geometry source of truth: build_saddle.py docstring, build/build.json,
build/pins.json (pin tops z 57.1, Dupont housing tops z 63.1, fan x -36.8..-6.8 |y| <= 16.4 z >= 64.4, floor passage
x -21..-5 |y| <= 16 open below the board, front wall bottom z 46.5 over the passage, USB-C plug notch y 3..15 z 46..56).

Wire path design: a Dupont wire leaves its housing top straight up into the space behind the fan (x -42..-37, z 63..70),
bends sideways at x -40, z 67 to |y| 21 (outside the fan and the lid bars, which run the fan's full length at y -18.2..-16.6
and 13.2..15.4 from x -37 to -6.6), runs forward along y = -21 (pins 1-12) or y = +21 (pins 17-40), descending over the
board to z 59 once past the housings, drops in the gap between the board front edge (x -13.1)
and the front wall (x -6.6) at x -9.8, converging to y -9 (-y lane) or y -1 (+y lane, passing over the USB-C plug, whose
envelope is y 4.6..13.7 z <= 55.1), and goes straight down through the floor passage into the torso roof opening.
"""
from __future__ import annotations

import argparse
import base64
import json
import math
import sys
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
MS = HERE.parents[2]
ROUTES = MS / 'guide/content/routes.json'
GUIDE_DATA = MS / 'guide/data/guide-data.json'
WORLD = MS / 'guide/print/world'
PINS = json.loads((HERE / 'build/pins.json').read_text())['pinTop']

Z_PIN, Z_HOUSING, Z_SIDE = 57.1, 63.1, 67.0
X_SIDE = -40.0         # sideways run behind the fan: 3 mm behind the lid bar ends (x -37), 2 mm in front of the lid lip (x -42)
X_DROP = -9.8          # between the board front edge (-13.1) and the front wall inner face (-6.6)

# Torso-side / head-side anchors: the last kept point of each existing route (exact match required), the rest is rebuilt.
ANCHOR = {
    'imu': [-6.6, 0.8, 36.0],            # BNO085 STEMMA QT socket, plug from above; the old climb to the neck bundle goes
    'uart': [-16.0, 1.5, 41.0],          # pack notch exit under the board
    'pi-lead': [-14.11, 1.098, 42.451],     # up in front of the roof rib; the old pack-notch zigzag to (-6, -14, 43.5) goes
    'audio_amp_vin_pin04': [42.4, 7.62, 143.82],   # 1.1 mm in front of the amplifier face (soldered wire)
    'audio_amp_bclk_pin12': [42.4, -5.08, 143.82],
    'audio_amp_lrc_pin35': [42.4, -7.62, 143.82],
    'audio_amp_gnd_pin39': [42.4, 5.08, 143.82],
    'audio_amp_din_pin40': [42.4, -2.54, 143.82],
    'touch_a7z_pin17': [50.5, 17.5, 148.5],        # cap-top A* lane above the old cap clip
    'touch_a7z_pin25': [50.5, 17.5, 148.5],
    'touch_a7z_pin29': [45.5, 4.5, 150.5],
    'touch_a7z_pin31': [45.5, 2.5, 150.5],
}
PIN = {'imu': 3, 'uart': 7, 'pi-lead': 2, 'audio_amp_vin_pin04': 4, 'audio_amp_bclk_pin12': 12, 'audio_amp_lrc_pin35': 35,
       'audio_amp_gnd_pin39': 39, 'audio_amp_din_pin40': 40, 'touch_a7z_pin17': 17, 'touch_a7z_pin25': 25,
       'touch_a7z_pin29': 29, 'touch_a7z_pin31': 31}
RADIUS = {'imu': 0.8, 'uart': 0.7, 'pi-lead': 0.9, 'fan_lead': 0.7, 'cam_usb': 1.5}
RADIUS.update({k: 0.65 for k in PIN if k.startswith(('audio_', 'touch_'))})
VIA_NECK = [k for k in PIN if k.startswith(('audio_', 'touch_'))]      # head -> neck bundle -> saddle

# bundle_head points reused inside the head (old route reversed: from the point under the amplifier down through the head
# clip to the bracket clip at the top of the neck, where bundle_neck ends).
HEAD_DOWN = [[49.5, -7.51, 137.0], [49.6, -17.5, 117.92], [49.6, -21.7, 117.92], [49.6, -21.7, 124.42], [41.26, -29.61, 134.1],
             [35.6, -23.0, 136.3], [34.0, -26.3, 130.8], [33.3, -26.9, 118.9]]
HEAD_JOIN = {   # from the anchor into HEAD_DOWN[0]
    'audio': lambda y: [[46.5, y, 140.3]],
    'touch_hi': [[50.44, 16.38, 146.21], [49.5, 14.98, 144.48], [49.5, 9.33, 137.4]],   # old bundle_head points
    'touch_mid': [[48.5, 3.0, 144.0], [49.5, -2.0, 137.5]],
}


def lane_tail(pin: int) -> list:
    """Saddle tail in route order: from the bottom of the drop column (z 46) to the pin top."""
    px, py, _ = PINS[str(pin)]
    if pin <= 12:
        ly = -21.0
        pts = [[X_DROP, -9.0, 46.0], [X_DROP, -9.5, 50.0], [X_DROP, -14.0, 54.0], [-11.0, -19.0, 57.5], [-15.0, ly, 59.0]]
    else:
        ly = 21.0
        pts = [[X_DROP, -1.0, 46.0], [X_DROP, -1.0, 50.0], [X_DROP, 0.0, 54.5], [X_DROP, 6.0, 58.0], [-11.0, 15.0, 58.5], [-15.0, ly, 59.0]]
    pts += [[-22.0, ly, 59.0], [-30.0, ly, 61.0], [-35.5, ly, 64.5]]
    if abs(py - ly) >= 2.0:
        pts.append([X_SIDE, ly, Z_SIDE])
    # out of the housing top the wire leans straight back (odd pins sit 1.3 mm behind the lid bar ends at x -37)
    pts += [[X_SIDE, py, Z_SIDE], [(px + X_SIDE) / 2, py, 65.0], [px, py, Z_HOUSING], [px, py, Z_PIN]]
    return pts


def torso_join(rid: str) -> list:
    """From the anchor (or from the bundle exit under the front wall) to the drop column bottom."""
    if rid == 'imu':
        return [[-7.5, -1.0, 40.0], [-9.3, -6.0, 44.0]]
    if rid == 'uart':      # stay under the PCIe FPC socket (board underside, x -16.6..-11.9, y -12..0, z 45.5..47)
        return [[-12.5, -3.0, 43.0], [-10.0, -7.0, 44.5]]
    if rid == 'pi-lead':
        return [[-11.8, -3.0, 43.5], [-10.0, -7.0, 44.5]]
    return [[-8.5, -8.0, 45.0]] if PIN[rid] > 12 else []


def build(routes: dict) -> dict:
    R = routes['routes']
    neck = R['bundle_neck']
    assert neck[0] == [-16.0, 3.0, 41.0] and neck[1] == [-6.0, -14.0, 43.5], neck[:2]
    neck_down = list(reversed(neck[1:]))        # (30, -27, 105) ... (10, -21, 42.5), (-6, -14, 43.5)
    # one point just in front of the saddle wall keeps the drawn spline off the wall's inner bottom corner (x -5, y -16, z 46.5
    # over the passage, down to the roof outside |y| 16) as the wire turns from the torso top to the passage.
    neck_down.insert(-1, [-2.0, -14.5, 43.4])
    new = {}
    for rid, anchor in ANCHOR.items():
        path = R[rid]
        idx = [i for i, p in enumerate(path) if np.allclose(p, anchor, atol=1e-6)]
        if not idx:
            raise SystemExit(f'{rid}: anchor {anchor} not in the current route')
        head = [list(p) for p in path[:idx[0] + 1]]
        if rid in VIA_NECK:
            if rid.startswith('audio'):
                join = HEAD_JOIN['audio'](anchor[1])
            elif rid in ('touch_a7z_pin17', 'touch_a7z_pin25'):
                join = HEAD_JOIN['touch_hi']
            else:
                join = HEAD_JOIN['touch_mid']
            head = head + join + HEAD_DOWN + neck_down
        new[rid] = head + torso_join(rid) + lane_tail(PIN[rid])
    # future USB camera: camera back face centre (retired camera_board.stl body x 76..80, lens centre y 0, z 131.1) to the
    # bundle under the old amplifier point, down the neck, over the torso roof opening in front of the saddle and into the
    # right-angle plug from its outer end (envelope x -13.6..-3 through the front-wall notch).
    new['cam_usb'] = [[76.0, 0.0, 131.1], [73.0, -1.0, 131.5], [62.0, -4.0, 134.5], [54.0, -6.5, 136.5]] + HEAD_DOWN + neck_down[:-2] + \
                     [[3.0, -13.0, 43.0], [1.0, -4.0, 44.5], [0.0, 4.0, 46.5], [-1.0, 8.5, 49.5], [-3.0, 9.1, 51.8], [-8.0, 9.1, 51.8]]
    # fan lead: out of the fan's rear face at its -y end into the pocket behind the fan, round the pin-1 end of the housings
    # and down the -y side of the board to J6 (pin-1 end, front corner).
    new['fan_lead'] = [[-36.0, -14.5, 66.0], [-38.8, -16.0, 65.5], [-39.5, -21.0, 65.0], [-38.5, -27.0, 64.5], [-36.0, -29.5, 60.0],
                       [-28.0, -29.5, 54.5], [-22.2, -30.4, 52.5], [-22.2, -30.4, 51.6]]
    # antenna_coax: first withdrawn (strip-to-housing gap 0.96 mm < the 1.13 mm pigtail), then drawn by hand in routes.json
    # after the board moved 0.3 mm forward (wall-to-housing gap 1.56 mm; the pigtail runs beyond the strip end at y -21).
    return new


RETIRE = ['bundle_head', 'head_csi'] + [f'fan_pin_{n:02d}' for n in (1, 2, 3, 5, 6, 8, 9, 10)]
DOC = (" 2026-10-22 saddle (D-022, print/a7z-saddle/build_saddle.py, route_check_saddle.py): the A7Z leaves the head and sits in the"
       " printed saddle on the torso roof over the rear pack, header along the rear edge (pin tops z 57.1, Dupont housing tops 63.1,"
       " fan above them at x -36.8..-6.8). Every wire that ended on a head pin now ends on the same pin in the saddle: it leaves its"
       " housing straight up behind the fan, bends sideways at x -40, z 67 to |y| 21, runs forward beside the fan and its lid bars and down"
       " over the board to z 59,"
       " drops in the gap between the board front edge and the saddle front wall at x -9.8 (the -y lane, pins 1-12, at y -9; the +y lane,"
       " pins 17-40, over the USB-C plug at y -1) and goes down through the saddle floor passage (x -21..-5, |y| <= 16) into the torso"
       " roof opening (uart and pi-lead stay under z 44.5 until they pass the PCIe FPC socket on the board underside). imu, uart and pi-lead"
       " keep their torso points to the roof opening and lose the neck and head tail. The five"
       " amplifier wires and the four XIAO wires now run from the head down the neck bundle: amplifier face / cap-top lane -> the old"
       " bundle_head points in reverse (under the old amplifier point, through the head clip, to the bracket clip) -> bundle_neck in"
       " reverse -> under the saddle front wall (bottom z 46.5 over the passage) -> the saddle tail; (-16, 3, 41) is not on these wires"
       " (it lies under the board behind the drop gap), bundle_neck itself is unchanged as the shared neck centreline. New: fan_lead"
       " (out of the fan's rear face at its -y end into the pocket behind the fan, round the pin-1 end of the housings and down the -y side"
       " of the board to J6, r 0.7), cam_usb (future USB camera: camera back face centre"
       " (76, 0, 131.1), head and neck bundle, over the roof opening in front of the saddle into the right-angle plug from its outer end,"
       " r 1.5); the antenna coax is not drawn (the AC019 strip ends at |y| 21 inside the housing span, 0.96 mm behind the housings, too"
       " narrow for the 1.1 mm pigtail). bundle_head, head_csi (the CSI camera is"
       " gone) and the fan_pin_* records move to retired. touch_a7z_pin* are hand-edited here from the cap-top anchor on; regenerating"
       " them in extension-20261015-touch/build_touch_geometry.py would restore the head pins. Checked by route_check_saddle.py.")


def write(routes: dict) -> None:
    new = build(routes)
    R = routes['routes']
    ret = routes.setdefault('retired', {})
    note = (" 2026-10-22: bundle_head (neck top to the head header), head_csi and fan_pin_* retired with the A7Z move to the torso"
            " saddle (D-022); the head bundle points live on in the audio, touch and cam_usb routes.")
    ret['_doc'] = ret.get('_doc', '') + note
    for rid in RETIRE:
        if rid in R:
            ret[rid] = R.pop(rid)
    # antenna_coax (hand-written in routes.json after the board moved 0.3 mm forward on 2026-10-22, wall-housing gap 1.56 mm) is kept
    for rid, path in new.items():
        R[rid] = [[round(float(c), 2) for c in p] for p in path]
    if DOC.strip()[:30] not in routes['_doc']:
        routes['_doc'] = routes['_doc'] + DOC
    ROUTES.write_text(json.dumps(routes, indent=1))
    print('wrote', ROUTES, 'routes', sorted(new), 'retired', [r for r in RETIRE if r in ret])


# ---- check -----------------------------------------------------------------------------------------------------------
def catmull_centripetal(points, t):   # copy of interference-audit/cables.py
    P = np.asarray(points, float)
    l = len(P)
    p = (l - 1) * t
    ip = np.floor(p).astype(int)
    w = p - ip
    end = (w == 0) & (ip == l - 1)
    ip[end] = l - 2
    w[end] = 1.0
    ip = np.clip(ip, 0, l - 2)
    p1, p2 = P[ip], P[ip + 1]
    p0 = np.where((ip > 0)[:, None], P[np.maximum(ip - 1, 0)], 2 * P[0] - P[1])
    p3 = np.where((ip + 2 < l)[:, None], P[np.minimum(ip + 2, l - 1)], 2 * P[-1] - P[-2])
    dt0 = np.sum((p1 - p0) ** 2, 1) ** 0.25
    dt1 = np.sum((p2 - p1) ** 2, 1) ** 0.25
    dt2 = np.sum((p3 - p2) ** 2, 1) ** 0.25
    dt1 = np.where(dt1 < 1e-4, 1.0, dt1)
    dt0 = np.where(dt0 < 1e-4, dt1, dt0)
    dt2 = np.where(dt2 < 1e-4, dt1, dt2)
    dt0, dt1, dt2 = dt0[:, None], dt1[:, None], dt2[:, None]
    t1 = ((p1 - p0) / dt0 - (p2 - p0) / (dt0 + dt1) + (p2 - p1) / dt1) * dt1
    t2 = ((p2 - p1) / dt1 - (p3 - p1) / (dt1 + dt2) + (p3 - p2) / dt2) * dt1
    c0, c1 = p1, t1
    c2 = -3 * p1 + 3 * p2 - 2 * t1 - t2
    c3 = 2 * p1 - 2 * p2 + t1 + t2
    ww = w[:, None]
    return c0 + c1 * ww + c2 * ww ** 2 + c3 * ww ** 3, ip


def polyline_samples(points, step=0.25):
    P = np.asarray(points, float)
    xs, segs = [], []
    for i in range(len(P) - 1):
        n = max(2, int(math.ceil(np.linalg.norm(P[i + 1] - P[i]) / step)) + 1)
        tt = np.linspace(0, 1, n)[:-1] if i < len(P) - 2 else np.linspace(0, 1, n)
        xs.append(P[i] + (P[i + 1] - P[i]) * tt[:, None])
        segs.append(np.full(len(tt), i))
    return np.vstack(xs), np.concatenate(segs)


def spline_samples(points, step=0.25):
    P = np.asarray(points, float)
    L = sum(np.linalg.norm(P[i + 1] - P[i]) for i in range(len(P) - 1))
    n = max(200, int(L / step) * 3)
    return catmull_centripetal(P, np.linspace(0, 1, n))


def arclen(x):
    return np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(x, axis=0), axis=1))])


def runs(mask):
    out, i = [], 0
    while i < len(mask):
        if mask[i]:
            j = i
            while j + 1 < len(mask) and mask[j + 1]:
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


SKIP_PARTS = ('pi', 'camera_board', 'camera_ribbon', 'antenna', 'antenna_coax', 'antenna_ipex', 'battery_backpack_frame',
              'battery_backpack_cap', 'bp_switch', 'bp_battery', 'bp_dfr1202', 'bp_plugs', 'bp_swap_plugs')


def solids() -> dict:
    """name -> Trimesh: guide-data.json parts (minus the head A7Z set and the battery alternates) plus the saddle world files."""
    out = {}
    g = json.loads(GUIDE_DATA.read_text())
    for p in g['parts']:
        k = p['key']
        if k in SKIP_PARTS or k.startswith('head_pi_'):
            continue
        v = np.frombuffer(base64.b64decode(p['positionB64']), '<f4').reshape(-1, 3).astype(np.float64)
        f = np.frombuffer(base64.b64decode(p['indexB64']), '<u4').reshape(-1, 3).astype(np.int64)
        out[k] = trimesh.Trimesh(v, f, process=False)
    for f in sorted(WORLD.glob('sd_*.stl')) + [WORLD / 'saddle_body.stl', WORLD / 'saddle_lid.stl']:
        out[f.stem] = trimesh.load(str(f), force='mesh')
    return out


def check(routes: dict, ids: list, verbose: bool) -> int:
    R = routes['routes']
    S = solids()
    bounds = {k: m.bounds for k, m in S.items()}
    bad = 0
    for rid in ids:
        r = RADIUS.get(rid, 0.9)
        path = [[round(float(c), 1) for c in p] for p in R[rid]]          # build_guide_data rounds to 0.1 mm
        path = [path[0]] + [p for a, p in zip(path, path[1:]) if math.dist(a, p) > 1e-6]
        worst_mid, worst_part, pens = math.inf, None, []
        for mode, (x, seg) in (('spline', spline_samples(path)), ('polyline', polyline_samples(path))):
            s = arclen(x)
            end_zone = (s < 8.0) | ((s[-1] - s) < 8.0)
            lo, hi = x.min(0) - r - 0.5, x.max(0) + r + 0.5
            for k, b in bounds.items():
                if not (np.all(b[0] <= hi) and np.all(b[1] >= lo)):
                    continue
                near = np.all((x >= b[0] - r - 0.5) & (x <= b[1] + r + 0.5), axis=1)
                if not near.any():
                    continue
                m = S[k]
                idx = np.flatnonzero(near)
                sd = np.full(len(x), -np.inf)
                for q in range(0, len(idx), 64):
                    pts = x[idx[q:q + 64]]
                    if m.is_watertight:
                        sd[idx[q:q + 64]] = trimesh.proximity.signed_distance(m, pts)
                    else:   # open mesh (speaker, touch_xiao): unsigned distance, treated as outside
                        sd[idx[q:q + 64]] = -trimesh.proximity.closest_point(m, pts)[1]
                clr = -sd - r
                mid = ~end_zone
                if mid.any() and clr[mid].min() < worst_mid:
                    w = int(np.flatnonzero(mid)[np.argmin(clr[mid])])
                    worst_mid, worst_part = float(clr[mid].min()), f'{k} ({mode}) at {x[w].round(1).tolist()} arc {s[w]:.0f}/{s[-1]:.0f}'
                for i, j in runs(sd + r > 0.1):
                    kk = i + int(np.argmax(sd[i:j + 1]))
                    at_end = 'start' if s[i] < 8 else ('end' if s[-1] - s[j] < 8 else None)
                    pens.append((mode, k, round(float(sd[kk] + r), 2), round(float(s[i]), 1), round(float(s[j]), 1), round(float(s[-1]), 1), at_end, x[kk].round(2).tolist()))
        mid_pens = [p for p in pens if p[6] is None]
        bad += len(mid_pens)
        print(f'{rid:22s} r {r:4.2f} pts {len(path):3d} min mid-route clearance {worst_mid:6.2f} mm  ({worst_part})'
              f'  end findings {len(pens) - len(mid_pens)}  MID-ROUTE PENETRATIONS {len(mid_pens)}')
        for p in pens:
            if p[6] is None or verbose:
                print('    ', ('   ok-at-' + p[6]) if p[6] else '   FAIL', p[0], p[1], 'depth', p[2], 'arc', p[3], '..', p[4], 'of', p[5], 'at', p[7])
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--ids', nargs='*')
    ap.add_argument('-v', action='store_true')
    a = ap.parse_args()
    routes = json.loads(ROUTES.read_text())
    if a.write:
        write(routes)
        routes = json.loads(ROUTES.read_text())
    ids = a.ids or (list(ANCHOR) + ['cam_usb', 'fan_lead'])
    bad = check(routes, ids, a.v)
    print('mid-route penetrations:', bad)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
