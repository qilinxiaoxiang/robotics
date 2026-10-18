#!/usr/bin/env python3
"""Option B: separate flat-printed Pi brackets on short cap stubs (study solids, coarse, for the comparison).

Per side: the V1.8 rail is cut away below the roof root; a printed bracket (plate in the Pi plane, printed lying on
its back so its layers run along its length and every hole is vertical in print) carries the Pi seat pads and the two
Pi pilots; its top bears against a stub block that hangs from the roof behind it, and two M2 x 8 TAP screws driven
from behind through the stub (Ø2.4 clearance, head on the stub's back face) thread into Ø1.7 pilots in the bracket.
Same frame as build_a.py (u along the Pi screws into the rail, v = y, w along the rail, origin at the lower screw).
Writes ../study-solids/B-*.stl, ../B-parts.json, ../B-build.json.
"""
from __future__ import annotations

import json

import manifold3d as m3
import numpy as np

from build_a import BASE_CAP, P, Y, hull_pts, profile
from pm_lib import A_SCREW, AX, SCREWS, STUDY, box, j, load_stl_man, screw_envelope, tm_from_man

S = STUDY / 'study-solids'
SEAT_U = 1.57               # bracket pad face (V1.8 boss face 1.55)
BODY_FRONT_U = 3.0          # bracket body recessed behind the pads (Pi back components)
V_IN = {-1: 26.2, +1: 27.4}  # bracket inner face |y|; +y stays at the V1.8 rail's inner face (head bundle beside it)
V_OUT = 33.0                # bracket outer face |y|; pads and body share the width, so the bracket is a prism along y
U_BACK = {-1: [(-9, 8.0), (40, 8.0)], +1: [(-9, 4.2), (0.0, 4.2), (15.0, 6.84), (15.3, 8.0), (40, 8.0)]}
BRACKET_W = (-3.1, 26.1)    # bracket length along the rail (lower boss bottom .. V1.8 upper boss top)
LAP_W = 15.3                # above this the bracket is a 3 mm tongue (u .. LAP_U) lapped on the cap stub behind it
LAP_U = 6.0
TONGUE_V_OUT = 32.4        # tongue and upper pad stop short of the sloping side wall near the roof
STUB_U1 = 9.5               # stub back face (screw heads seat here)
SCREW_W = 17.5              # two bracket-to-stub M2 x 6 TAP screws, driven from behind
SCREW_V = (28.9, 31.5)
PI_LEN = {'E-pi-01': 6.0, 'E-pi-02': 4.0, 'E-pi-03': 6.0, 'E-pi-04': 6.0}   # V1.8 Pi screw specs, unchanged
FIT = 0.2                   # bracket clearance to the roof and side wall
CUT = (1.3, 7.2, 25.4, 32.6, -4.0, 27.3)   # V1.8 rail + both bosses removed: (u0, u1, |v|0, |v|1, w0, w1)


def along(p0, axis, L, r):
    return m3.Manifold.cylinder(L, r, r, 24).transform(np.c_[np.c_[np.cross(Y, axis), Y, axis], p0])


def main():
    base = load_stl_man(BASE_CAP)
    hull = m3.Manifold.batch_hull([base])
    pieces = sorted((hull - base).decompose(), key=lambda m: -m.volume())
    clip = hull - m3.Manifold.batch_boolean(pieces[1:], m3.OpType.Add)
    cap = base
    brackets, stubs, screws, holes, info = {}, [], [], [], {}
    for side, low, up in ((-1, 'E-pi-01', 'E-pi-03'), (+1, 'E-pi-02', 'E-pi-04')):
        c = SCREWS[low]
        w_up = float((SCREWS[up] - c) @ AX)
        u0, u1, a0, a1, w0, w1 = CUT
        cap = cap - hull_pts([P(c, u, side * v, w) for u in (u0, u1) for v in (a0, a1) for w in (w0, w1)])
        # bracket: lower body (front 3.0, back U_BACK) + tongue (front 3.0, back LAP_U) + two seat pads (front 1.57)
        body = profile(c, BRACKET_W[0], LAP_W, BODY_FRONT_U, U_BACK[side], side * V_IN[side], side * V_OUT)
        tongue = profile(c, LAP_W - 0.01, BRACKET_W[1], BODY_FRONT_U, [(-9, LAP_U), (40, LAP_U)], side * V_IN[side],
                         side * TONGUE_V_OUT)
        pads = [profile(c, wc - 3.1, wc + 3.1, SEAT_U, [(-9, BODY_FRONT_U + 0.1), (40, BODY_FRONT_U + 0.1)],
                        side * V_IN[side], side * vo) for wc, vo in ((0.0, V_OUT), (w_up, TONGUE_V_OUT))]
        br = m3.Manifold.batch_boolean([body, tongue] + pads, m3.OpType.Add) ^ clip
        # stub: hangs from the roof behind the tongue (u LAP_U .. STUB_U1), from w LAP_W up, merged with roof and wall
        stub = profile(c, LAP_W, w_up + 16.0, LAP_U, [(-9, STUB_U1), (40, STUB_U1)], side * V_IN[side], side * V_OUT) ^ clip
        stubs.append(stub)
        for v in SCREW_V:
            head = P(c, STUB_U1, side * v, SCREW_W)                # head seat on the stub back face
            screws.append(screw_envelope(head, 6.0, axis=-A_SCREW))
            holes.append(along(P(c, STUB_U1 + 0.5, side * v, SCREW_W), -A_SCREW, STUB_U1 - LAP_U + 0.5, 1.2))  # stub clearance
            br = br - along(P(c, LAP_U + 0.01, side * v, SCREW_W), -A_SCREW, LAP_U - BODY_FRONT_U - 0.4, 0.85)  # blind pilot
        for sid in (low, up):
            br = br - along(SCREWS[sid] + 1.0 * A_SCREW, A_SCREW, 8.0, 0.85)    # Pi pilots, through
        brackets[side] = br
        info['minus_y' if side < 0 else 'plus_y'] = dict(bracketVolumeMm3=round(br.volume(), 1), stubVolumeMm3=round(stub.volume(), 1),
                                                         upperScrewW=w_up)
    stub_all = m3.Manifold.batch_boolean(stubs, m3.OpType.Add)
    capB = (cap + stub_all) - m3.Manifold.batch_boolean(holes, m3.OpType.Add)
    # trim the bracket where the roof/wall comes down over it, with FIT mm clearance (the stub lap face stays exact)
    grown = m3.Manifold.batch_boolean([cap.translate((d * e).tolist()) for e in (A_SCREW, AX, Y) for d in (-FIT, FIT)]
                                      + [capB], m3.OpType.Add)
    for side, br in brackets.items():
        brackets[side] = sorted((br - grown).decompose(), key=lambda m: -m.volume())[0]
    capB = sorted(capB.decompose(), key=lambda m: -m.volume())[0]
    for side, br in brackets.items():
        info['minus_y' if side < 0 else 'plus_y']['bracketCapOverlapMm3'] = round((br ^ capB).volume(), 4)
    tm_from_man(capB).export(S / 'B-head_cap-world.stl')
    added = m3.Manifold.batch_boolean([b for b in ((capB - base) ^ stub_all).decompose() if b.volume() > 0.01], m3.OpType.Add)
    tm_from_man(added).export(S / 'B-cap_added-world.stl')
    for side, br in brackets.items():
        tm_from_man(br).export(S / f'B-bracket{"-" if side < 0 else "+"}y-world.stl')
    pi_scr = m3.Manifold.batch_boolean([screw_envelope(c, PI_LEN[k]) for k, c in SCREWS.items()], m3.OpType.Add)
    tm_from_man(pi_scr).export(S / 'B-pi_screws_envelope-world.stl')
    tm_from_man(m3.Manifold.batch_boolean(screws, m3.OpType.Add)).export(S / 'B-bracket_screws_envelope-world.stl')
    (STUDY / 'B-parts.json').write_text(json.dumps({
        'cap': 'B-head_cap-world.stl', 'baseCap': str(BASE_CAP),
        'parts': {'cap_added_B_stubs': 'B-cap_added-world.stl', 'bracket_minus_y': 'B-bracket-y-world.stl',
                  'bracket_plus_y': 'B-bracket+y-world.stl', 'pi_screws_V18_specs': 'B-pi_screws_envelope-world.stl',
                  'bracket_screws_4xM2x6': 'B-bracket_screws_envelope-world.stl'},
        'intended': {'bracket_minus_y|pi': 'Pi seated on the bracket pads (face contact)',
                     'bracket_plus_y|pi': 'Pi seated on the bracket pads (face contact)',
                     'pi_screws_V18_specs|head_cap': 'none expected (the Pi screws thread into the brackets)',
                     'pi_screws_V18_specs|pi': 'shank through the Pi holes, head on the board',
                     'bracket_screws_4xM2x6|head_cap': 'head on the stub back face, shank in the Ø2.4 clearance hole',
                     'pi_screws_V18_specs|bracket_minus_y': 'thread in the bracket pilot',
                     'pi_screws_V18_specs|bracket_plus_y': 'thread in the bracket pilot',
                     'bracket_screws_4xM2x6|bracket_minus_y': 'thread in the bracket pilot',
                     'bracket_screws_4xM2x6|bracket_plus_y': 'thread in the bracket pilot'},
        'strength': {'-1': 'B-bracket-y-world.stl', '1': 'B-bracket+y-world.stl'}}, indent=1))
    out = {'parameters': dict(SEAT_U=SEAT_U, BODY_FRONT_U=BODY_FRONT_U, V_IN=V_IN, V_OUT=V_OUT, U_BACK=U_BACK,
                              BRACKET_W=BRACKET_W, LAP_W=LAP_W, LAP_U=LAP_U, STUB_U1=STUB_U1, PI_LEN=PI_LEN, SCREW_W=SCREW_W, SCREW_V=SCREW_V, CUT=CUT),
           'sides': info, 'capRemovedMm3': round((base - capB).volume(), 1), 'stubAddedMm3': round(added.volume(), 1)}
    (STUDY / 'B-build.json').write_text(json.dumps(j(out), indent=1))
    print(json.dumps(j(out), indent=1))


if __name__ == '__main__':
    main()
