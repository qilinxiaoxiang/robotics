#!/usr/bin/env python3
"""Final route A3 for the 8-wire neck bundle in the integrated head, its wire solids and its two in-head clips.

Below the head the route is neck-route A2 unchanged (torso clip S12-horn-025, neck clip S11-case-094, bracket clip
S11-horn-040) and enters through the -y slot. In the head it is three exact-checked maximin corridors joined end to end:
  1. slot top -> over the jaw-support cross wall -> down to the head clip under H-jaw_support-03
     (route_search/route_exact scenario 'A3-slot-to-clip')
  2. head clip -> up behind the Pi under the amplifier -> over the Pi top at y 17..22 -> down the +y front edge
     ('A3-clip-over-top-plus-y'); the cap clip sits on this stretch under E-pi-04
  3. corridor end -> gather point in front of the header, outboard of the pin 1/2 housings, and from there each wire to
     its own housing (fan_search.py, ../route-fan.json; the fan stays out of the camera/face descent column)
All corridor polylines are simplified (Ramer-Douglas-Peucker 0.6 mm).
Wire solids (study envelopes, inference on the wire size): the group = round tube r 1.7 mm (8 wires lying two deep);
fan wires = tubes r 0.65 mm (26 AWG silicone 1.3 mm). Clips (envelopes, inference on the shape): a 1.0 mm washer tab
under the screw head plus a 3 x 1.2 mm arm to a hook around the group.
  clip_head  under H-jaw_support-03 (M2.5, seat 42.1 -30 113.215, axis -z): lower head; the group turns up here
  clip_cap   under E-pi-04 (M2, the +y upper Pi screw, seat 61.335 29 140.895): rides on the Pi, i.e. on the cap
Cap-lift slack: with the Pi plugged, the cap is lowered the last 40 mm; the stretch from clip_head (lower head) to
clip_cap (cap) must reach the raised clip_cap. Needed extra length = straight distance clip_head -> clip_cap + 40 z
minus the stretch's closed length (a taut lower bound).
Solids: A3_group_slot_to_clip (span 1), A3_group_free (span 2 up to the cap clip), A3_group_cap_held (rest of span 2 and
span 3 group), A3_fan_wires, A3_clip_head, A3_clip_cap, A3_group_in_head (union of the three group parts).
Writes ../route-A3.json (route-candidates format + wire polylines), ../study-solids/A3_*-world.stl.
"""
import json

import manifold3d as m3
import numpy as np

import int_lib as L
from check_lib import tm_from_man
from route_scene import cable_tube

R_GROUP, R_WIRE = 1.7, 0.65
A2_BELOW = [[-16.0, 3.0, 41.0, 'trunk_base', 'tie'], [-6.0, -14.0, 43.5, 'trunk_base', 'guide'],
            [10.0, -21.0, 42.5, 'trunk_base', 'guide'], [20.0, -21.4, 32.5, 'trunk_base', 'tie'],
            [18.0, -16.5, 59.9, 'neck', 'tie'], [20.0, -20.5, 82.4, 'neck_pitch', 'tie'],
            [22.0, -20.5, 95.0, 'neck_pitch', 'guide'], [30.0, -26.7, 105.0, 'jaw_soft', 'guide'],
            [33.3, -26.9, 118.9, 'jaw_soft', 'guide']]
CLIP_HEAD_SEAT, CLIP_HEAD_AX = np.array([42.1, -30.0, 113.215]), np.array([0, 0, -1.0])
CLIP_CAP_SEAT, CLIP_CAP_AX = np.array([61.335, 29.0, 140.895]), np.array([-0.984808, 0.0, 0.173648])
PINS = {1: (24.13, 'odd'), 2: (24.13, 'even'), 3: (21.59, 'odd'), 5: (19.05, 'odd'), 6: (19.05, 'even'),
        8: (16.51, 'even'), 9: (13.97, 'odd'), 10: (13.97, 'even')}
FACE = {'odd': (73.705, 114.07), 'even': (74.146, 116.571)}   # V1.8 bundle housings: exit-face centre x, z (measured on the meshes)
SLOT_UP = [[34.0, -26.3, 130.8], [35.6, -23.0, 136.3]]                        # neck-route A2 slot, up to its top


def rdp(P, eps):
    P = np.asarray(P, float)
    if len(P) < 3:
        return P
    a, b = P[0], P[-1]
    ab = b - a
    t = np.clip(((P - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
    d = np.linalg.norm(P - (a + t[:, None] * ab), axis=1)
    i = int(np.argmax(d))
    if d[i] <= eps:
        return np.array([a, b])
    return np.vstack([rdp(P[:i + 1], eps)[:-1], rdp(P[i:], eps)])


def frame(ax):
    ax = ax / np.linalg.norm(ax)
    a = np.array([0, 0, 1.0]) if abs(ax[2]) < 0.9 else np.array([1.0, 0, 0])
    u = np.cross(ax, a)
    u /= np.linalg.norm(u)
    return u, np.cross(ax, u), ax


def clip(seat, ax, hook, w=3.0, t=1.2):
    """Washer tab (Ø5 x 1.0 under the head, i.e. at seat .. seat - 1.0 ax) + arm (w x t) from the washer rim to the hook
    + hook (a tube ring of wall t around the group, open on one side: modelled closed as an envelope)."""
    u, v, a = frame(ax)
    washer = m3.Manifold.cylinder(1.0, 2.5, 2.5, 32).transform(np.c_[u, v, a, seat - 1.0 * a])
    d = hook - seat
    d_perp = d - (d @ a) * a
    rim = seat - 0.5 * a + 2.0 * d_perp / max(np.linalg.norm(d_perp), 1e-9)
    side = np.cross(hook - rim, a)
    side = side / max(np.linalg.norm(side), 1e-9)
    pts = [p + s * side * w / 2 + q * a * t / 2 for p in (rim, hook) for s in (-1, 1) for q in (-1, 1)]
    arm = m3.Manifold.hull_points([list(map(float, p)) for p in pts])
    return washer + arm


def main():
    s2c = np.load(L.SCRATCH / 'route-exact-A3-slot-to-clip.npz')['S']           # slot top -> head clip (route_exact)
    S = np.load(L.SCRATCH / 'route-exact-A3-clip-over-top-plus-y.npz')['S']     # head clip -> front of the header
    fanj = json.loads((L.STUDY / 'route-fan.json').read_text())                 # fan_search.py
    G = np.array(fanj['gatherPoint'])
    hook_head = S[0]
    slot = np.array([p[:3] for p in A2_BELOW[-1:]] + SLOT_UP, float)
    up = np.vstack([slot[-1:], rdp(s2c, 0.6)[1:], hook_head])                    # slot top -> clip hook
    head = rdp(S, 0.6)
    tail = np.array(fanj['group']['polyline'], float)[1:]                        # corridor end -> gather point G
    s_cum = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(S, axis=0), axis=1))])
    k_cap = int(np.argmin(np.linalg.norm(S - (CLIP_CAP_SEAT + np.array([4.0, -4.0, 5.0])), axis=1)))
    hook_cap = S[k_cap]
    fan = {int(p): np.array(w['polyline'], float) for p, w in fanj['wires'].items()}
    group_pts = np.vstack([np.array([p[:3] for p in A2_BELOW[-2:]], float), slot[1:], up[1:], head[1:], tail])
    i_cap = int(np.argmin(np.linalg.norm(head - hook_cap, axis=1)))
    sol = {'A3_group_slot_to_clip': cable_tube(up, R_GROUP, 16),
           'A3_group_free': cable_tube(head[:i_cap + 1], R_GROUP, 16),
           'A3_group_cap_held': cable_tube(np.vstack([head[i_cap:], tail]), R_GROUP, 16),
           'A3_fan_wires': m3.Manifold.batch_boolean([cable_tube(v, R_WIRE, 12) for v in fan.values()], m3.OpType.Add),
           'A3_clip_head': clip(CLIP_HEAD_SEAT, CLIP_HEAD_AX, hook_head),
           'A3_clip_cap': clip(CLIP_CAP_SEAT, CLIP_CAP_AX, hook_cap)}
    sol['A3_group_in_head'] = sol['A3_group_slot_to_clip'] + sol['A3_group_free'] + sol['A3_group_cap_held']
    for k, M in sol.items():
        tm_from_man(M).export(L.SOL / f'{k}-world.stl')
    # each fan wire against the bundle housings and header pins of the OTHER seven pins (pairwise.py checks the fan as one
    # solid, where every bundle housing is an intended contact)
    from scene import load_man
    cross = {}
    for p, v in fan.items():
        W = cable_tube(v, R_WIRE, 12)
        worst = (99.0, None)
        for q in PINS:
            if q == p:
                continue
            for k in (f'head_pi_gpio_pin_{q:02d}_receiving', f'head_pi_zero_w_header_pin_{q:02d}'):
                M = load_man(k)
                ov = (W ^ M).volume()
                g = 0.0 if ov > 1e-4 else float(W.min_gap(M, 5.0))
                if g < worst[0]:
                    worst = (g, k)
        cross[p] = {'minGapMm': round(worst[0], 3), 'to': worst[1]}
    L_free = float(s_cum[k_cap])
    raised = hook_cap + np.array([0, 0, 40.0])
    straight = float(np.linalg.norm(raised - hook_head))
    length = lambda P: float(np.linalg.norm(np.diff(np.asarray(P, float), axis=0), axis=1).sum())
    pts_route = [list(map(float, p[:3])) + [p[3], p[4]] for p in A2_BELOW] + \
        [list(map(float, p)) + ['jaw_soft', 'guide'] for p in slot[1:]] + \
        [list(map(float, p)) + ['jaw_soft', 'guide'] for p in up[1:-1]] + \
        [list(map(float, hook_head)) + ['jaw_soft', 'tie']] + \
        [list(map(float, p)) + ['jaw_soft', 'guide'] for p in head[1:]] + \
        [list(map(float, p)) + ['jaw_soft', 'guide'] for p in tail[:-1]] + [list(map(float, G)) + ['jaw_soft', 'end']]
    out = {'_doc': __doc__.strip(),
           'routes': [{'name': 'A3-integrated', 'groupRadiusMm': 0.0,
                       'description': 'A2 below the head; -y slot; over the jaw-support cross wall and down to the head clip '
                                      'under H-jaw_support-03; up behind the Pi under the amplifier; over the Pi top at '
                                      'y 17..22 (cap clip under E-pi-04); down the +y front edge outboard of the pin 1/2 '
                                      'housings to a gather point in front of the header; each wire to its housing',
                       'points': pts_route}],
           'inHeadLengthMm': {'slotTopToHeadClip': round(length(up), 1),
                              'headClipToCorridorEnd': round(float(s_cum[-1]), 1),
                              'corridorEndToGather': round(length(np.vstack([S[-1:], tail])), 1),
                              'fanWiresMm': {p: round(length(v), 1) for p, v in fan.items()}},
           'clips': {'clip_head': {'screw': 'H-jaw_support-03', 'seat': CLIP_HEAD_SEAT, 'hook': hook_head, 'body': 'lower head'},
                     'clip_cap': {'screw': 'E-pi-04', 'seat': CLIP_CAP_SEAT, 'hook': hook_cap, 'body': 'Pi (cap)',
                                  'routeMmFromHeadClip': round(L_free, 1)}},
           'capLiftSlack': {'closedLengthClipToClipMm': round(L_free, 1), 'straightToRaisedCapClipMm': round(straight, 1),
                            'extraNeededTautMm': round(max(0.0, straight - L_free), 1),
                            'method': 'taut lower bound: straight line from the head clip hook to the cap clip hook raised 40 mm'},
           'fanWireVsOtherBundleHousings': cross,
           'fan': {str(p): v for p, v in fan.items()}, 'fanPoint': G, 'groupPolyline': group_pts,
           'solids': {k: str(L.SOL / f'{k}-world.stl') for k in sol}}
    L.jdump(L.rnd(out, 3), L.STUDY / 'route-A3.json')
    print(json.dumps(L.rnd({k: v for k, v in out.items() if k not in ('_doc', 'routes', 'fan', 'groupPolyline')}, 2), indent=1))
    print('route points', len(pts_route))


if __name__ == '__main__':
    main()
