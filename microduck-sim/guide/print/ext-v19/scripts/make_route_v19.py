#!/usr/bin/env python3
"""Write ../route-v19.json: the V1.9 neck bundle route (8-wire group through the four release clips), the fan wires
at the Pi header, and the amplifier/speaker jumper wires, in the route-candidates format of the neck-route study
(points [x, y, z, body, kind] in the robot frame at q = 0; kind tie = held by a clip, guide = where the slack group is
laid, end = connector).

Changes against integrated/route-A3.json:
  below the head: the torso and bracket ties move into the release clip channels (on the neck-pitch and head-pitch
  axes), the neck tie on the ID11 case is dropped (no clip there, owner decision), the guide above the bracket follows
  the bracket channel up (x 26, 1.2 mm further out in -y) and the slot-entry point moves 0.3 mm out (-y), so the
  span between them clears motor13;
  in the head: the head clip is the elbow clip (group down its channel, turn on its plate, out of its +y window);
  the stretch under the amplifier housings runs 1.8 mm lower so it also clears housings on a header whose pins stand
  1.27 mm above the amp board (Sullins-type right-angle header; the audio study assumed 4.02 mm);
  the cap clip holds the group where it crosses the Pi top edge (channel along the Pi normal at y 18).
Audio jumpers: the audio study's wire-routes.json with ground on Pi pin 34 (alt_gnd_pin34), as the audio study
recommends and the integrated study adopted (route_scene.py); the pin-14 ground route is not used.
guideCables: proposed routes.json paths for the three guide cables the bundle carries (pi-trunk, imu, uart). Each keeps
its V1.8 path up to its pack-notch point, then follows the bundle to the gather point and its own fan wire (pi-trunk
to pin 2, imu to pin 3, uart to pin 8; the guide draws one tube per cable).
Group radius 1.7 mm (8 wires lying two deep; inference), single wires 0.65 mm (26 AWG silicone).
"""
from __future__ import annotations

import json

import numpy as np

import clips_v19 as C
import ext_lib as E

R_GROUP = 1.7
R_WIRE = 0.65
BRACKET_OUT_X = 26.0      # x of the guide point 10 mm above the bracket channel
BRACKET_OUT_DY = -1.2     # that guide point sits 1.2 mm further out (-y) than the channel, towards the slot side
SLOT_ENTRY_DY = -0.3      # the A3 slot-entry point (30, -26.7, 105) moves 0.3 mm out (-y); together these keep the
                          # straight span from the bracket to the slot 0.28 mm off motor13 (probe_route, both modes)
CAP_OUT_N = 2.5           # guide point this far past the cap channel end, along the channel axis
HEAD_X_SHIFT = 0.4        # group centre in the head channel, +x of the channel centre (interior play is 0.7)


def r3(p):
    return [round(float(v), 3) for v in p]


def main():
    a3 = json.loads((E.STUDY_INT / 'route-A3.json').read_text())
    F = E.fasteners()
    # torso and bracket channels: interior centre FLOOR + CH_H/2 off the seat plane
    off = C.FLOOR + C.CH_H / 2
    st = np.array(F['S12-horn-025']['center'])
    br = np.array(F['S11-horn-040']['center'])
    ty = st[1] - (C.TAB_T - 0.1) - off                  # raised torso channel
    by = br[1] - off
    x0, x1 = C.TORSO_X0, C.TORSO_X0 + C.TORSO_L
    zc = C.TORSO_ZC
    torso = [[x0, ty, zc, 'trunk_base', 'tie'], [x1, ty, zc, 'trunk_base', 'tie']]
    # the group comes straight down from the torso top corner onto the channel, and bends up after it to the bracket
    torso_in = []
    torso_out = [[x1 + 2.4, ty, zc + 1.3, 'trunk_base', 'guide']]
    bracket = [[26.0, by, br[2] - C.CH_L / 2, 'neck_pitch', 'tie'], [26.0, by, br[2] + C.CH_L / 2, 'neck_pitch', 'tie']]
    # head clip (elbow)
    hc = np.array(F[C.HEAD_SCREW]['center'])
    z0 = hc[2] + C.TAB_T
    xm = C.HEAD_FLOOR_X + C.HEAD_CH['floor'] + C.HEAD_CH['ch_h'] / 2
    wo = C.HEAD_CH['ch_w'] + 2 * C.HEAD_CH['wall']
    xm = xm + HEAD_X_SHIFT                              # the group hugs the channel's mouth side: clear of the jaw-support wall
    head = [[xm, C.HEAD_CENTRE_Y, z0 + C.HEAD_H, 'jaw_soft', 'tie'],
            [xm, C.HEAD_CENTRE_Y, z0 + C.HEAD_TURN_Z, 'jaw_soft', 'tie'],
            [xm, C.HEAD_CENTRE_Y + wo / 2 + 0.6, z0 + C.HEAD_TURN_Z, 'jaw_soft', 'tie']]
    # cap clip
    yc = C.CAP_Y_FLOOR - C.CAP_CH['floor'] - C.CAP_CH['ch_h'] / 2
    cap = [[*C.cap_point(-1.6, yc, C.CAP_T_MID), 'jaw_soft', 'guide'],
           [*C.cap_point(0.0, yc, C.CAP_T_MID), 'jaw_soft', 'tie'],
           [*C.cap_point(C.CAP_CH['length'], yc, C.CAP_T_MID), 'jaw_soft', 'tie']]
    # past the channel end the group continues along the channel axis before it bends down the Pi front
    cap_out = [[*C.cap_point(C.CAP_CH['length'] + CAP_OUT_N, yc, C.CAP_T_MID), 'jaw_soft', 'guide']]
    pts = [p for p in a3['routes'][0]['points']]
    trunk = pts[:3]
    a3_head_entry = [list(p) for p in pts[7:12]]          # (30,-26.7,105) .. (41.261,-29.615,134.099)
    assert a3_head_entry[0][:3] == [30.0, -26.7, 105.0], a3_head_entry[0]
    a3_head_entry[0][1] = round(a3_head_entry[0][1] + SLOT_ENTRY_DY, 3)
    after_head = [[49.5, -7.507, 137.0, 'jaw_soft', 'guide'], [49.5, 9.326, 137.4, 'jaw_soft', 'guide'],
                  [49.5, 14.982, 144.482, 'jaw_soft', 'guide'], [50.437, 16.375, 146.205, 'jaw_soft', 'guide'],
                  [53.76, 17.077, 146.537, 'jaw_soft', 'guide'], [57.353, 18.4, 147.887, 'jaw_soft', 'guide']]
    to_header = [p for p in pts[26:]]   # (74.793,25.5,136.974) .. end
    route = (trunk + torso_in + torso + torso_out + bracket + [[BRACKET_OUT_X, round(by + BRACKET_OUT_DY, 3), 95.0, 'neck_pitch', 'guide']]
             + a3_head_entry + head + after_head + cap + cap_out + to_header)
    route = [r3(p[:3]) + list(p[3:]) for p in route]
    wires = json.loads((E.AUDIO / 'wire-routes.json').read_text())
    wires.pop('amp_gnd_pin14')                       # ground on pin 34 (alt_gnd_pin34) instead
    # guide cables carried by the bundle: V1.8 path to the pack-notch point, then the bundle, then the cable's fan wire
    g = E.ia_lib.load_guide()
    notch = np.array(route[0][:3], float)
    fan = a3['fan']
    guide = {}
    for cid, pin in (('pi-trunk', '2'), ('imu', '3'), ('uart', '8')):
        c = next(c for c in g['cables'] if c['id'] == cid)
        P = np.array(c['path'], float)
        j = int(np.argmin(np.linalg.norm(P - notch, axis=1)))
        fp = [list(map(float, q[:3])) for q in fan[pin]][::-1]      # fan polylines run housing -> gather point
        trunk_to_gather = [p[:3] for p in route[1:]]
        if np.linalg.norm(np.array(trunk_to_gather[-1]) - np.array(fp[0])) < 1e-6:
            fp = fp[1:]
        path = [r3(p) for p in P[:j + 1]] + [r3(p) for p in trunk_to_gather] + [r3(p) for p in fp]
        guide[cid] = {'radius': c.get('radius'), 'keptV18PointsUpToIndex': j, 'notchPointV18': r3(P[j]),
                      'fanPin': int(pin), 'path': path}
    out = {
        '_doc': __doc__.strip(),
        'routes': [{'name': 'neck-bundle-v19', 'groupRadiusMm': R_GROUP,
                    'description': 'pack notch -> torso side -> torso clip (S12-horn-025) -> up the neck -> bracket clip '
                                   '(S11-horn-040) -> -y head slot -> over the jaw-support cross wall -> down the head clip '
                                   '(H-jaw_support-03), out of its window -> under the amplifier housings behind the Pi -> '
                                   'cap clip (E-pi-04) over the Pi top edge -> down the Pi front to the gather point -> fan',
                    'points': route}],
        'fanWires': {'radiusMm': R_WIRE, 'polylines': a3['fan'], 'gatherPoint': a3['fanPoint']},
        'audioWires': {'radiusMm': R_WIRE, 'polylines': wires, 'groundPin': 34},
        'guideCables': guide,
        'clipTies': {'torso': torso, 'bracket': bracket, 'head': head, 'cap': cap[1:]},
        'designGuides': {'torsoIn': torso_in, 'torsoOut': torso_out, 'capOut': cap_out},
    }
    E.jdump(out, E.OUT / 'route-v19.json')
    L = float(np.linalg.norm(np.diff(np.array([p[:3] for p in route]), axis=0), axis=1).sum())
    print('points', len(route), 'length at q0', round(L, 1))


if __name__ == '__main__':
    main()
