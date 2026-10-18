#!/usr/bin/env python3
"""Flexible-wire screen for the recommended layout: hand-set centrelines of the five I2S/power jumpers (amp header
housings -> Pi pins 4, 12, 14, 35, 40) and the speaker lead pair, checked against every rigid solid near them.

This is a route-plausibility screen, not a cable model: wires are tubes (jumper r 0.7 mm, speaker lead r 0.6 mm), each
end is allowed to sit in its own housing / terminal for its last 2 mm, and the yaw body is taken at its worst roll.
Writes ../wires.json and ../wire-routes.json (polylines in the routes.json format).
"""
from __future__ import annotations

import json

import numpy as np
import trimesh

from check_lib import FIXED, Head, YAW, ROLL_P, rot, tm_from_man, man_from_tm
from scene import STUDY

S = STUDY / 'study-solids'
R_JUMPER, R_LEAD = 0.7, 0.6


def pi_end(pin):
    """Centre of the wire end face of a Pi-pin housing (receiving envelope end, x 73.9-74.4)."""
    y = 24.13 - 2.54 * ((pin + 1) // 2 - 1)
    return np.array([74.15, y, 116.57]) if pin % 2 == 0 else np.array([73.70, y, 114.06])


def routes(build):
    amp = build['amplifier']
    xa, za = amp['housingEndX'], amp['pcbTopZ'] + 4.02
    py = amp['pinYOrder']

    def amp_side(ya, yb):
        return [[xa, ya, za], [xa + 1.6, ya, za + 2.4], [61.0, yb, 147.4], [64.8, yb, 145.6]]

    out = {}
    # pins outside the camera's y range (y -9.6..14.3): leave the housing, turn up in front of it, climb the Pi face
    for name, pin, yb in (('amp_vin_pin04', 4, 9.0), ('amp_lrc_pin35', 35, -8.0), ('amp_din_pin40', 40, -10.5)):
        e = pi_end(pin)
        a = {'amp_vin_pin04': 'Vin', 'amp_lrc_pin35': 'LRC', 'amp_din_pin40': 'DIN'}[name]
        up = [[76.4, e[1], e[2] + 0.6], [76.4, e[1], 121.5], [69.5, e[1], 127.5], [66.8, 0.5 * (e[1] + yb), 137.5]]
        out[name] = amp_side(py[a], yb) + up[::-1] + [e.tolist()]
    # alternative ground (recommended): Pi pin 34 is outside the camera shadow; same climb as pins 35/40
    e = pi_end(34)
    up = [[76.4, e[1], e[2] + 0.6], [76.4, e[1], 121.5], [69.5, e[1], 127.5], [66.8, 0.5 * (e[1] + 4.0), 137.5]]
    out['alt_gnd_pin34'] = amp_side(py['GND'], 4.0) + up[::-1] + [e.tolist()]
    # pins 12 and 14 sit behind the camera board: turn down, run +y under the housing ends, climb at y 16.3
    for name, pin, a, yb in (('amp_bclk_pin12', 12, 'BCLK', 12.0), ('amp_gnd_pin14', 14, 'GND', 13.5)):
        e = pi_end(pin)
        lane = 113.9 if pin == 12 else 112.6
        tail = [[76.4, e[1], e[2] - 0.5], [76.4, e[1], lane], [76.4, 16.3, lane], [76.4, 16.3, 121.5],
                [69.5, 16.3, 127.5], [66.8, 15.0, 137.5]]
        out[name] = amp_side(py[a], yb) + tail[::-1] + [e.tolist()]
    # speaker leads: pad notch (speaker +u end, back face) -> terminal block mouths (facing -x) at the amp hole edge
    f = build['speakerFrame']
    c0, u, n = np.array(f['originFrontFaceCentre']), np.array(f['u_long']), np.array(f['n_front'])
    x0 = amp['boardX'][0]
    for name, vy, ty in (('spk_plus', 1.5, 1.75), ('spk_minus', -1.5, -1.75)):
        p0 = c0 + 13.2 * u + vy * np.array([0, 1.0, 0]) - 3.4 * n
        p1 = p0 - 2.5 * n
        out[name] = [p0.tolist(), p1.tolist(), [x0 - 4.0, ty, amp['pcbTopZ'] + 3.0], [x0 - 0.5, ty, amp['pcbTopZ'] + 3.0]]
    return out


def sample(p, step=0.25):
    p = np.asarray(p, float)
    seg = [np.linspace(a, b, max(2, int(np.ceil(np.linalg.norm(b - a) / step)) + 1)) for a, b in zip(p[:-1], p[1:])]
    pts = np.vstack(seg)
    s = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    return pts, s


def main():
    build = json.loads((STUDY / 'study-build.json').read_text())
    W = routes(build)
    cap_ext = man_from_tm(trimesh.load(S / 'head_cap_extension-world.stl', force='mesh'))
    H = Head(cap_override=cap_ext)
    solids = {k: tm_from_man(H.get(k)) for k in FIXED + H.pi}
    for k in ('speaker', 'speaker_retainer', 'amplifier', 'amp_housings', 'pi_housing_pin04', 'pi_housing_pin12',
              'pi_housing_pin14', 'pi_housing_pin35', 'pi_housing_pin40', 'speaker_screws_envelope', 'amp_screws_envelope'):
        solids[k] = trimesh.load(S / f'{k}-world.stl', force='mesh')
    for k in YAW:
        for a in (-25, -12.5, 0, 12.5, 25):
            T = np.eye(4)
            T[:3, :] = rot([-1, 0, 0], a, ROLL_P)
            solids[f'{k}@roll{a:+}'] = tm_from_man(H.get(k)).apply_transform(T)
    T = np.eye(4)
    res = {}
    own = {'amp_vin_pin04': ('amp_housings', 'pi_housing_pin04', 'head_pi_zero_w_header_pin_04'),
           'amp_lrc_pin35': ('amp_housings', 'pi_housing_pin35', 'head_pi_zero_w_header_pin_35'),
           'amp_din_pin40': ('amp_housings', 'pi_housing_pin40', 'head_pi_zero_w_header_pin_40'),
           'amp_bclk_pin12': ('amp_housings', 'pi_housing_pin12', 'head_pi_zero_w_header_pin_12'),
           'amp_gnd_pin14': ('amp_housings', 'pi_housing_pin14', 'head_pi_zero_w_header_pin_14'),
           'alt_gnd_pin34': ('amp_housings', 'head_pi_zero_w_header_pin_34'),
           'spk_plus': ('speaker', 'amplifier'), 'spk_minus': ('speaker', 'amplifier')}
    for name, poly in W.items():
        r = R_LEAD if name.startswith('spk') else R_JUMPER
        pts, s = sample(poly)
        end = (s < 2.0) | (s > s[-1] - 2.0)
        lo, hi = pts.min(0) - 10, pts.max(0) + 10
        best = []
        for k, m in solids.items():
            if np.any(m.bounds[0] > hi) or np.any(m.bounds[1] < lo):
                continue
            q = pts[~end] if k in own[name] else pts
            if not len(q):
                continue
            _, d, _ = m.nearest.on_surface(q)
            ins = m.contains(q) if m.is_watertight else np.zeros(len(q), bool)
            d = np.where(ins, -d, d)
            best.append((float(d.min()) - r, k))
        best.sort()
        length = float(s[-1])
        res[name] = {'lengthMm': round(length, 1), 'radiusMm': r, 'closest': [{'with': k, 'clearanceMm': round(c, 2)} for c, k in best[:4]],
                     'clear': best[0][0] >= 0.0}
        print(name, round(length, 1), [(k, round(c, 2)) for c, k in best[:3]], flush=True)
    routes_json = {k: [[round(float(x), 2) for x in p] for p in v] for k, v in W.items()}
    (STUDY / 'wire-routes.json').write_text(json.dumps(routes_json, indent=1))
    (STUDY / 'wires.json').write_text(json.dumps({'method': __doc__, 'wires': res}, indent=1))




def tube_manifold(poly, r):
    import manifold3d as m3
    segs = []
    for a, b in zip(poly[:-1], poly[1:]):
        sa = m3.Manifold.sphere(r, 16).translate(list(map(float, a)))
        sb = m3.Manifold.sphere(r, 16).translate(list(map(float, b)))
        segs.append(m3.Manifold.batch_hull([sa, sb]))
    return m3.Manifold.batch_boolean(segs, m3.OpType.Add)


def descent_screen():
    """Wires ride down with the populated cap (both ends are cap-mounted). Sweep each tube straight down 40 mm and
    report the worst overlap excess against the parts already on the robot (exact booleans)."""
    W = json.loads((STUDY / 'wire-routes.json').read_text())
    H = Head()
    out = {}
    for name, poly in W.items():
        r = R_LEAD if name.startswith('spk') else R_JUMPER
        T = tube_manifold(np.asarray(poly, float), r)
        out[name] = H.descent(T, 0.5)
        print('descent', name, out[name], flush=True)
    d = json.loads((STUDY / 'wires.json').read_text())
    d['descentWithCap'] = out
    (STUDY / 'wires.json').write_text(json.dumps(d, indent=1))


if __name__ == '__main__':
    main()
    descent_screen()
