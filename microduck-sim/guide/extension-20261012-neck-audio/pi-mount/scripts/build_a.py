#!/usr/bin/env python3
"""Option A: web-braced integral Pi rails, built on the audio-extension study cap (study solids only).

Per rail (frame: u along the Pi screw axis into the rail, v = y, w along the rail; origin at the lower screw centre):
  web        a plate from the rail's outer face to the side wall, from the lower boss to the roof, front face at the
             rail's (recessed) front face so the Pi's back is untouched; clipped to the cap interior so it merges with
             the side wall and roof and never reaches the outside
  ledges     the flat tops of the lower boss (support-holding ledges in the Elegoo slice) become 55 deg ramps up to the
             rail body; the upper boss is joined to the roof by a root block (inner face kept at the V1.8 rail inner
             face, clear of the head bundle)
  pilots     all four Ø1.7 pilots re-cut along the screw axis, open past the screw tip
Every Pi seat face, pilot position and screw stays where V1.8 has it. Writes ../study-solids/A-*.stl, ../A-build.json.
"""
from __future__ import annotations

import json
import os

import manifold3d as m3
import numpy as np
import trimesh

from pm_lib import AUDIO, A_SCREW, AX, SCREWS, STUDY, box, j, load_stl_man, man_from_tm, tm_from_man

S = STUDY / 'study-solids'
BASE_CAP = AUDIO / 'study-solids' / 'head_cap_extension-world.stl'   # audio study cap (V1.8 + audio additions)
Y = np.array([0.0, 1.0, 0.0])
RAMP_DEG = 55.0           # slope of the new ramps from the print horizontal is >= this minus the 14 deg print tilt
PILOT_D, PILOT_U = (1.7, (1.0, 7.0))   # pilot diameter; u range (seat face at u 1.55)
WEB_V_START = 28.0        # web starts inside the rail (outer face at |y| 30.6) so it fuses with it
# (w, u_back) web back-face profile. +y: the cap passes jaw_support on the way down (descent), so below w 14
# (z ~132) the web keeps x >= 52.9 like the V1.8 trimmed +y rail; above that it deepens.
U_BACK = {-1: [(-9, 8.0), (40, 8.0)], +1: [(-9, 4.2), (0.0, 4.2), (15.0, 6.84), (15.3, 9.0), (40, 9.0)]}
WEB_OUTER_FRONT_U = 2.4   # outboard of the rail (|y| > 30.4) the web comes forward to 0.9 mm behind the Pi's back
WEB_OUTER_V = 30.4
ROOT_FRONT_U = 1.57       # ramp and root fronts flush with the boss seat face (u 1.55), so no ledge is left on a boss top


def P(c, u, v, w):
    return c + u * A_SCREW + (v - c[1]) * Y + w * AX


def hull_pts(pts):
    return m3.Manifold.hull_points([list(map(float, p)) for p in pts])


def rail_section(cap_tm, c, w, side):
    """Rail outline (u, v) at height w: the cut component that holds the screw line (u 0..7, v = side*29)."""
    o = c + w * AX
    sec = cap_tm.section(plane_origin=o, plane_normal=AX)
    if sec is None:
        return None
    T = np.eye(4)
    T[:3, 0], T[:3, 1], T[:3, 2], T[:3, 3] = A_SCREW, Y, -AX, o
    pl, _ = sec.to_2D(to_2D=np.linalg.inv(T))
    from shapely.geometry import box as sbox
    best = None
    for poly in pl.polygons_full:
        q = poly.intersection(sbox(0.5, -6.0, 9.0, 6.0))
        for g in getattr(q, 'geoms', [q]):
            if g.geom_type == 'Polygon' and g.area > 0.3 and g.distance(sbox(2.0, -1, 5.0, 1)) < 0.3:
                best = g
    if best is None:
        return None
    xy = np.asarray(best.exterior.coords)
    return np.c_[xy[:, 0], xy[:, 1] + c[1]]        # (u, v absolute y)


def lift(c, uv, w):
    return [P(c, u, v, w) for u, v in uv]


def profile(c, w0, w1, u0, uprof, v0, v1):
    """Web block: the (u, w) outline (front face u0, back face u_back(w) piecewise linear, w0..w1) extruded along y
    from v0 to v1 (absolute y). One extrusion, so the block has no internal seams."""
    ub = lambda w: float(np.interp(w, [p[0] for p in uprof], [p[1] for p in uprof]))
    ws = [w0] + [w for w, _ in uprof if w0 < w < w1] + [w1]
    pts = [(u0, w0)] + [(ub(w), w) for w in ws] + [(u0, w1)]
    cs = m3.CrossSection([pts])
    if cs.area() < 0:
        cs = m3.CrossSection([pts[::-1]])
    lo, hi = sorted((v0, v1))
    M = cs.extrude(hi - lo).translate([0, 0, lo - c[1]])
    T = np.c_[A_SCREW, AX, Y, c]              # local (u, w, y - c_y) -> world; (A, AX, Y) is right-handed
    return M.transform(T)


def main():
    base = load_stl_man(BASE_CAP)
    base_tm = trimesh.load(BASE_CAP, force='mesh')
    hull = m3.Manifold.batch_hull([base])
    pieces = sorted((hull - base).decompose(), key=lambda m: -m.volume())
    # clip = the cap's convex hull minus every outside concavity (exterior grooves): one solid with no internal seam
    # along the cap's inner surface, so clipped additions merge with the wall without zero-thickness slivers
    clip = hull - m3.Manifold.batch_boolean(pieces[1:], m3.OpType.Add)
    adds, cuts, info, raw = [], [], {}, []
    for side, low, up in ((-1, 'E-pi-01', 'E-pi-03'), (+1, 'E-pi-02', 'E-pi-04')):
        c = SCREWS[low]
        w_up = float((SCREWS[up] - c) @ AX)
        # scan the V1.8 rail to find the boss tops/bottoms and the rail body faces
        scan = []
        for w in np.arange(-5.0, w_up + 6.0, 0.1):
            uv = rail_section(base_tm, c, w, side)
            if uv is not None:
                scan.append((round(float(w), 2), uv[:, 0].min(), uv[:, 0].max(), np.abs(uv[:, 1]).min(), np.abs(uv[:, 1]).max()))
        scan = np.array(scan)
        scan = scan[(scan[:, 3] > 23.2) & (scan[:, 4] < 34.8)]   # drop cuts merged with the wide shell
        boss = scan[:, 1] < 2.2                          # Pi seat (u 1.55) present -> boss
        low_boss = scan[(scan[:, 0] < w_up / 2) & boss]
        up_boss = scan[(scan[:, 0] > w_up / 2) & boss]
        w_lb0, w_lt = float(low_boss[:, 0].min()), float(low_boss[:, 0].max())
        up_boss = up_boss[up_boss[:, 0] < w_up + 4.5]       # the boss itself, not the roof cut beyond it
        w_ub0, w_ut = float(up_boss[:, 0].min()), float(up_boss[:, 0].max())
        mid = scan[(scan[:, 0] > w_lt + 4) & (scan[:, 0] < w_ub0 - 2)]
        u_front = float(np.median(mid[:, 1]))
        v_in, v_out = float(np.median(mid[:, 3])), float(np.median(mid[:, 4]))
        info[f'{"minus" if side < 0 else "plus"}_y'] = dict(lowerBossW=[w_lb0, w_lt], upperBossW=[w_ub0, w_ut],
                                                            railFrontU=u_front, railYAbs=[v_in, v_out],
                                                            upperScrewW=w_up)
        # 1. web to the side wall
        web = profile(c, w_lb0 + 0.5, w_up + 12.0, u_front, U_BACK[side], side * WEB_V_START, side * (WEB_OUTER_V + 0.2)) + \
            profile(c, w_lb0 + 0.5, w_up + 12.0, WEB_OUTER_FRONT_U, U_BACK[side], side * WEB_OUTER_V, side * 46.0)
        adds.append(('web', side, web ^ clip)); raw.append(web)
        # 2. lower-boss ledge ramps: hull of the full boss outline (taken inside the boss, below its flat top) and the
        #    rail outline higher up, so every top ledge of the boss becomes a RAMP_DEG slope
        w_in = w_lt - 1.0
        boss_out = rail_section(base_tm, c, w_in, side)
        prot = max(u_front - boss_out[:, 0].min(), v_in - np.abs(boss_out[:, 1]).min(), np.abs(boss_out[:, 1]).max() - v_out)
        H = prot * np.tan(np.radians(RAMP_DEG)) + 1.2
        rail_up = rail_section(base_tm, c, w_in + H, side)
        seat = [P(c, ROOT_FRONT_U, side * v, w) for v in (np.abs(boss_out[:, 1]).min(), np.abs(boss_out[:, 1]).max())
                for w in (w_in, w_lt + 0.1)]
        ramp = hull_pts(lift(c, boss_out, w_in) + seat + lift(c, rail_up, w_in + H))
        adds.append(('lower_ramp', side, ramp ^ clip)); raw.append(ramp)
        # 3. upper boss root block: the full boss outline taken inside the boss (2 mm above the screw line) ramps to
        #    the outline trimmed at the rail inner face (clear of the head bundle at y ~ +-23), then runs straight up
        #    into the roof; front face flush with the seat face, so no ledge is left on the boss top
        w_in = w_up + 2.0
        ub_out = rail_section(base_tm, c, w_in, side)
        u_b = float(ub_out[:, 0].max())
        v_o = float(np.abs(ub_out[:, 1]).max())
        h2 = max(0.5, v_in - np.abs(ub_out[:, 1]).min()) * np.tan(np.radians(RAMP_DEG)) + 1.2
        trimmed = [P(c, u, side * v, w) for u in (ROOT_FRONT_U, u_b) for v in (v_in, v_o) for w in (w_in + h2,)]
        root = hull_pts(lift(c, ub_out, w_in) + trimmed) + \
            hull_pts([P(c, u, side * v, w) for u in (ROOT_FRONT_U, u_b) for v in (v_in, v_o) for w in (w_in + h2 - 0.3, w_up + 14.0)])
        adds.append(('upper_root', side, root ^ clip)); raw.append(root)
        info[f'{"minus" if side < 0 else "plus"}_y'].update(rootStartW=w_in, upperBossBackU=u_b, upperBossOuterY=v_o)
        # pilots (re-cut after the union)
        for sid in (low, up):
            p0 = SCREWS[sid] + PILOT_U[0] * A_SCREW
            L = PILOT_U[1] - PILOT_U[0]
            cuts.append((sid, m3.Manifold.cylinder(L, PILOT_D / 2, PILOT_D / 2, 32).transform(
                np.c_[np.c_[np.cross(Y, A_SCREW), Y, A_SCREW], p0])))
    for n_, s_, a_ in adds:
        print('piece', n_, s_, np.round(np.array(a_.bounding_box()).reshape(2, 3), 1).tolist())
    added = m3.Manifold.batch_boolean([a for _, _, a in adds], m3.OpType.Add)
    cut = m3.Manifold.batch_boolean([cc for _, cc in cuts], m3.OpType.Add)
    capA = (base + added) - cut
    bodies = sorted(capA.decompose(), key=lambda m: -m.volume())
    dropped = sum(b.volume() for b in bodies[1:])
    capA = bodies[0]
    print('manifold status', capA.status(), 'bodies', len(bodies), 'dropped loose volume', round(dropped, 5))
    # the added material is reported inside the unclipped pieces only: (capA - base) also returns zero-thickness
    # slivers where the re-triangulated wall surface of capA meets base's (no volume, but they spoil distance checks)
    region = m3.Manifold.batch_boolean(raw, m3.OpType.Add)
    add_net = m3.Manifold.batch_boolean([b for b in ((capA - base) ^ region).decompose() if b.volume() > 0.01], m3.OpType.Add)
    stray = ((capA - base) - region).volume()
    rem_net = m3.Manifold.batch_boolean([b for b in (base - capA).decompose() if b.volume() > 0.01], m3.OpType.Add)
    for name, M in (('A-head_cap-world', capA), ('A-added-world', add_net), ('A-removed-world', rem_net)):
        tm = tm_from_man(M)
        tm.export(S / f'{name}.stl')
    out = {'base': str(BASE_CAP), 'parameters': dict(RAMP_DEG=RAMP_DEG, PILOT_D=PILOT_D, PILOT_U=PILOT_U,
                                                      WEB_V_START=WEB_V_START, U_BACK=U_BACK,
                                                      WEB_OUTER_FRONT_U=WEB_OUTER_FRONT_U, WEB_OUTER_V=WEB_OUTER_V,
                                                      ROOT_FRONT_U=ROOT_FRONT_U),
           'railScan': info,
           'pieces': {f'{n}{"+y" if s > 0 else "-y"}': round(M.volume(), 1) for n, s, M in adds},
           'addedMm3': round(add_net.volume(), 1), 'removedMm3': round(rem_net.volume(), 2),
           'addedBounds': np.round(np.array(add_net.bounding_box()).reshape(2, 3), 2),
           'removedNote': 'removed = pilot re-cuts only (inside V1.8 material they coincide with the V1.8 pilots)',
           'differenceOutsideThePiecesMm3': round(stray, 4), 'droppedLooseBodiesMm3': round(dropped, 5),
           'capBodies': len(capA.decompose()), 'genus': capA.genus()}
    from pm_lib import screw_envelope
    scr = m3.Manifold.batch_boolean([screw_envelope(c, 4.0 if k == 'E-pi-02' else 6.0) for k, c in SCREWS.items()],
                                    m3.OpType.Add)
    tm_from_man(scr).export(S / 'A-pi_screws_envelope-world.stl')
    (STUDY / 'A-parts.json').write_text(json.dumps({
        'cap': 'A-head_cap-world.stl', 'baseCap': str(BASE_CAP),
        'parts': {'cap_added_A': 'A-added-world.stl', 'pi_screws_V18_specs': 'A-pi_screws_envelope-world.stl'},
        'intended': {'pi_screws_V18_specs|head_cap': 'thread in the Ø1.7 pilots (Ø2.0 envelope)',
                     'pi_screws_V18_specs|pi': 'shank through the Pi holes, head on the board'},
        'strength': 'cap'}, indent=1))
    (STUDY / 'A-build.json').write_text(json.dumps(j(out), indent=1))
    print(json.dumps(j(out), indent=1))


if __name__ == '__main__':
    main()
