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
import re
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

Z_PIN, Z_HOUSING, Z_OVER = 58.1, 64.1, 66.5   # V2 (D-028): pin tops, housing tops, and the height at which a wire swings over the open header strip
X_DROP = -9.8          # between the board front edge (-12.0) and the front wall inner face (-6.6); the tray ends at x -11.7 and is notched |y| < 16

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
RADIUS = {'imu': 0.8, 'uart': 0.7, 'pi-lead': 0.9, 'fan_lead': 0.7, 'cam_usb': 1.5, 'antenna_coax': 0.57}
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
    # V2: the header is at the front edge under the open strip. The wire rises in the drop column (torso wires at y -9, head wires
    # at y -1, both inside the floor cut |y| <= 16), swings sideways at z 66.5 over the housing tops (64.1) to its pin column and
    # goes straight down into the housing. Pins 1-12 (torso wires) are at y 24.1..11.4, pins 17-40 (head wires) at y 4.1..-24.1.
    y0 = -9.0 if pin <= 12 else -1.0
    yc = max(-14.0, min(14.0, py))
    pts = [[X_DROP, y0, 46.0], [X_DROP, y0, 52.0], [X_DROP, yc, 60.0], [X_DROP, py, Z_OVER], [px, py, Z_OVER], [px, py, Z_HOUSING], [px, py, Z_PIN]]
    return pts


NECK = [10.8, 16.5, 60.0]     # where every head wire (and the camera cable) leaves the neck above the torso roof
Z_WALL_TOP = 63.0             # front wall top over the header strip (build_saddle.py FRONT_TOP)


def head_tail(pin: int) -> list:
    """Head-wire tail from the neck point: over the lowered front wall top (z 63, |y| <= 28; wire centre 1.6 above it) straight into
    the open header strip and down into the housing. Nothing goes under the saddle (Shawn 2026-10-25)."""
    px, py, _ = PINS[str(pin)]
    yw = max(-26.0, min(26.0, py))
    return [[9.0, 15.0, 63.5], [-5.0, yw, Z_WALL_TOP + 1.6], [px, py, 65.5], [px, py, Z_HOUSING], [px, py, Z_PIN]]


def torso_join(rid: str) -> list:
    """From the anchor (or from the bundle exit under the front wall) to the drop column bottom."""
    if rid == 'imu':
        return [[-7.5, -1.0, 40.0], [-9.3, -6.0, 44.0]]
    if rid == 'uart':      # stay under the PCIe FPC socket (board underside, x -16.6..-11.9, y -12..0, z 45.5..47)
        return [[-12.5, -3.0, 43.0], [-10.0, -7.0, 44.5]]
    if rid == 'pi-lead':
        return [[-11.8, -3.0, 43.5], [-10.0, -7.0, 44.5]]
    return [[-8.5, -8.0, 45.0]] if PIN[rid] > 12 else []


PIN_RE = re.compile(r'pin(\d+)$')


def pin_of(rid: str) -> int | None:
    if rid in PIN:
        return PIN[rid]
    m = PIN_RE.search(rid)
    return int(m.group(1)) if m else None


def build(routes: dict) -> dict:
    """V2 (D-028, 2026-10-25): every torso route that ends on a header pin keeps its drawn path down to the bottom of the drop column
    (X_DROP, -9, 46), where the V1.29 saddle tail began, and gets the V2 tail from there (lane_tail); every head route (it passes the
    neck point NECK) keeps its head and neck part and comes over the lowered front wall (head_tail). cam_usb, fan_lead
    and antenna_coax are rebuilt for the rear-window plug, the 6530B blower and the front-wall antenna."""
    R = routes['routes']
    new = {}
    for rid, path in R.items():
        pin = pin_of(rid)
        if pin is None or not path or abs(path[-1][2] - PINS[str(pin)][2]) > 1.0 and abs(path[-1][2] - 57.1) > 0.05:
            continue
        neck = [i for i, p in enumerate(path) if np.allclose(p, NECK, atol=1e-6)]
        if neck:   # head wire: keep the head and neck part, then over the front wall into the strip
            new[rid] = [list(p) for p in path[:neck[0] + 1]] + head_tail(pin)
            continue
        idx = [i for i, p in enumerate(path) if abs(p[0] - X_DROP) < 0.01 and abs(p[2] - 46.0) < 0.01]
        if not idx:
            raise SystemExit(f'{rid}: no drop-column point ({X_DROP}, y, 46) in the current route')
        new[rid] = [list(p) for p in path[:idx[0]]] + lane_tail(pin)
    # Camera cable (D-023 head part kept as drawn by hand down the left side of the neck to (10.8, 16.5, 60)); V2 tail: down the
    # robot's left outside the saddle (the saddle +y wall is at y 34.4, its bulge 36.4; the shell ends at y 31.8), back along
    # y 40 at z 50 (the guide draws it r 2.0; the bulge outer face is y 36.4) to behind the rear wall, into the right-angle plug from its +y end (plug body x -61.4..-43.6, y -14.8..7,
    # z 48.85..56.85, leg to +y, in USB-C ② through the rear window).
    cam = R['cam_usb']
    k = [i for i, p in enumerate(cam) if np.allclose(p, [10.8, 16.5, 60.0], atol=1e-6)]
    if not k:
        raise SystemExit('cam_usb: the neck point (10.8, 16.5, 60) is not in the current route')
    new['cam_usb'] = [list(p) for p in cam[:k[0] + 1]] + [[7.0, 26.0, 56.0], [2.0, 36.5, 52.0], [-10.0, 40.0, 50.0], [-30.0, 40.0, 50.0],
                                                           [-46.0, 39.5, 50.5], [-52.5, 30.0, 52.0], [-52.5, 14.0, 52.85], [-52.5, 8.0, 52.85]]
    # 6530B fan lead: out of the blower at the +y end of the heatsink, down the +y channel to J6 (pin-1 end, x -35.3..-30.4,
    # y 29.2..31.6, top z 52.6). The lead is about 10 mm; whether the 6530B base is relieved over J6 is checked on the part.
    new['fan_lead'] = [[-31.0, 31.0, 59.5], [-31.0, 33.6, 58.0], [-32.8, 33.6, 54.5], [-32.8, 30.4, 53.3], [-32.8, 30.4, 52.6]]
    # IPEX pigtail (AC019, 40-50 mm): from the IPEX socket (x -28.4..-25.4, y 29..32, top z 50.85) sideways into the +y bulge
    # channel (board edge y 32.5, wall inner face 34.8, x -35..-6, z 46..59), forward to the front wall and onto the antenna
    # feed end at the strip's +y end (strip x -6.9..-6.6, y -11..31, z 50..62).
    new['antenna_coax'] = [[-26.9, 30.5, 51.2], [-26.9, 33.6, 52.5], [-20.0, 33.6, 53.0], [-12.0, 33.6, 54.0], [-8.6, 32.6, 55.0], [-7.4, 30.6, 56.0]]
    return new


DOC = (" 2026-10-25 saddle V2 (D-028, print/a7z-saddle/build_saddle.py, route_check_saddle.py): the board is turned 180 deg, the 40-pin header"
       " is at the saddle's front edge under an open strip (pin tops z 58.1, Dupont housing tops 64.1, pin 1 at +y), USB-C and HDMI face the"
       " rear wall window. Every wire that ends on a header pin keeps its path to the bottom of the drop column between the board front edge"
       " and the front wall (x -9.8, y -9, inside the floor cut x -21..-5, |y| <= 16), rises there to z 60, swings at z 66.5 over the open"
       " housing tops to its pin column and goes straight down into the housing. Every head wire comes from the neck point (10.8, 16.5, 60)"
       " straight over the lowered front wall top (z 63 over |y| <= 28; wire centre z 64.6) into the open strip and down into its housing;"
       " nothing goes under the saddle. cam_usb: the head and"
       " neck part stays (left side of the neck); from (10.8, 16.5, 60) it runs down the robot's left outside the saddle wall, back along"
       " y 39 at z 50 and into the right-angle plug from its +y end, the plug in USB-C 2 through the rear window (body along the rear wall"
       " towards +y, USB-C 1 free). fan_lead: the 6530B blower lead down the +y channel to J6 (about 10 mm). antenna_coax: IPEX socket,"
       " sideways into the +y bulge channel outside the board edge, forward to the front wall, onto the AC019 feed end at the strip's +y end"
       " (strip on the front wall inner face, y -11..31, z 50..62). Checked by route_check_saddle.py.")


def write(routes: dict) -> None:
    new = build(routes)
    R = routes['routes']
    for rid, path in new.items():
        R[rid] = [[round(float(c), 2) for c in p] for p in path]
    if DOC.strip()[:30] not in routes['_doc']:
        routes['_doc'] = routes['_doc'] + DOC
    ROUTES.write_text(json.dumps(routes, indent=1))
    print('wrote', ROUTES, 'routes', sorted(new))


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
    ids = a.ids or sorted(build(json.loads(ROUTES.read_text())))
    bad = check(routes, ids, a.v)
    print('mid-route penetrations:', bad)
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
