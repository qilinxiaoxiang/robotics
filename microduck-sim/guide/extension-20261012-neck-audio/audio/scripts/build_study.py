#!/usr/bin/env python3
"""Build the study solids for the recommended head-audio layout (study geometry only, not a print release).

Layout "roof pair" (robot frame, mm, x forward, y left, z up):
  * Speaker (Same Sky CMS-30204-18SP, 30 x 20 x 4.0 obround) under the rear half of the cap roof, front face up and
    tilted to the local roof, sealed by a 1.0 mm foam ring (0.6 mm compressed) to a seat collar printed into the cap.
    A printed retainer frame presses the back rim and screws to two collar bosses (2 x M2 x 6 TAP).
  * Grille: Ø1.8 mm holes, hexagonal 2.8 mm pitch, drilled along the cap's print z axis through the roof over the
    front chamber.
  * Amplifier (Adafruit 3006, 17.78 x 19.05 x 1.57 board) flat under the roof between the speaker and the Pi,
    components up, held by two cap posts through its two Ø2.5 holes (2 x M2 x 6 TAP from below). A 7-pin right-angle
    header (soldered by the owner) points +x at the Pi; six female Dupont housings (LRC, BCLK, DIN, GAIN option, GND,
    Vin) lie flat under the roof and end 3.3 mm behind the Pi.
  * Pi end: five more housings on pins 4, 12, 14, 35, 40 (copies of the guide's receiving envelopes).
Outputs (all under ../study-solids/, robot frame STL) and ../study-build.json with every parameter.
"""
from __future__ import annotations

import json

import manifold3d as m3
import numpy as np
import trimesh

from check_lib import Head, tm_from_man
from scene import STUDY

OUT = STUDY / 'study-solids'
OUT.mkdir(exist_ok=True)
PRINT_Z_WORLD = np.array([0.07654276042668799, -0.021537583923671277, -0.9968336562862398])  # manifest-V1.8 head_cap row 3
SEG = 64

# ---- purchased parts (sources in README) ----
SPK_L, SPK_W, SPK_T, SPK_FRAME, SPK_BOSS_D = 30.0, 20.0, 4.0, 2.5, 12.7   # Same Sky datasheet drawing, solder-pad version
PAD_NOTCH_W, PAD_NOTCH_D = 6.2, 1.9                                      # measured from the drawing (approximate)
AMP_W, AMP_L, AMP_T = 17.78, 19.05, 1.57                                 # Adafruit .brd / fab print / CAD STL
AMP_HOLE_D, AMP_HOLE_IN = 2.5, 2.54
TB_W, TB_D, TB_H = 7.2, 8.0, 10.0   # ASSUMPTION: pre-soldered 3.5 mm 2-way block envelope (height unpublished; measure)
RA_PIN_Z, RA_BODY, RA_MATE, RA_TAIL = 4.02, 2.5, 5.84, 3.05               # Sullins 11637 rev B right-angle header
HOUSING_L, HOUSING_S = 14.0, 2.54                                         # Pololu 1900 1x1 crimp housing
FOAM_COMPRESSED = 0.6

# ---- layout parameters (chosen with freespace.py and iterated with check_study.py) ----
SPK_CENTRE_XY = (2.0, 0.0)
CHAMBER_MIN = 1.0       # minimum front-chamber height above the seat landing over the speaker outline
FRONT_GAP = float(__import__('os').environ.get('AUDIO_FRONT_GAP', 1.0))  # front chamber depth above the landing: a filler plate closes the rest up to the roof
RING_CLEAR, RING_WALL, LIP_W = 0.2, 2.0, 1.5
BOSS_D, BOSS_V, PILOT_D, PILOT_DEPTH = 5.2, 14.6, 1.7, 5.0   # M2 x 6 TAP: 4.4 mm thread + 0.6 tip room
RET_T, RET_INSET = 1.6, 2.0
GRILLE_D = float(__import__('os').environ.get('AUDIO_GRILLE_D', 1.8))
GRILLE_PITCH = float(__import__('os').environ.get('AUDIO_GRILLE_PITCH', 2.7))
GRILLE_EDGE = 0.5
AMP_HEADER_EDGE_X = 41.3     # board edge carrying the 7-pin row; housings end at x = edge + 15.2 = 56.5
AMP_PCB_TOP_Z = 139.8
AMP_POST_D = 4.0


def stadium(L, W, delta=0.0):
    r = W / 2 + delta
    a = m3.CrossSection.circle(r, SEG).translate([-(L - W) / 2, 0])
    b = m3.CrossSection.circle(r, SEG).translate([(L - W) / 2, 0])
    return m3.CrossSection.batch_hull([a, b])


def extrude(cs, z0, z1):
    return m3.Manifold.extrude(cs, z1 - z0).translate([0, 0, z0])


def frame_T(c, u, v, n):
    T = np.eye(4)
    T[:3, 0], T[:3, 1], T[:3, 2], T[:3, 3] = u, v, n, c
    return T


def apply(M, T):
    return M.transform(T[:3, :])


def roof_points(cap_tm, xy):
    """Underside of the cap roof straight above each (x, y): first cap hit of a +z ray started at z 128."""
    o = np.c_[xy, np.full(len(xy), 128.0)]
    loc, idx, _ = cap_tm.ray.intersects_location(o, np.tile([0, 0, 1.0], (len(xy), 1)), multiple_hits=True)
    z = np.full(len(xy), np.nan)
    for p, i in zip(loc, idx):
        if np.isnan(z[i]) or p[2] < z[i]:
            z[i] = p[2]
    return np.c_[xy, z]


def speaker_frame(cap_tm):
    cx, cy = SPK_CENTRE_XY
    g = np.mgrid[-18:18.01:1.0, -13:13.01:1.0].reshape(2, -1).T + [cx, cy]
    P = roof_points(cap_tm, g)
    P = P[~np.isnan(P[:, 2])]
    A = np.c_[np.ones(len(P)), P[:, 0], P[:, 1]]
    a, b, c = np.linalg.lstsq(A, P[:, 2], rcond=None)[0]
    n = np.array([-b, -c, 1.0])
    n /= np.linalg.norm(n)
    u = np.array([1.0, 0, 0]) - n[0] * n
    u /= np.linalg.norm(u)
    v = np.cross(n, u)
    centre_guess = np.array([cx, cy, a + b * cx + c * cy])
    # landing plane: speaker front at n = 0, landing at n = FOAM_COMPRESSED; roof at least CHAMBER_MIN above landing
    # over the ring footprint (outline + ring wall)
    loc = (P - centre_guess) @ np.c_[u, v, n]
    L, W = SPK_L + 2 * (RING_CLEAR + RING_WALL), SPK_W + 2 * (RING_CLEAR + RING_WALL)
    inside = (np.abs(loc[:, 1]) <= W / 2) & (np.maximum(np.abs(loc[:, 0]) - (L - W) / 2, 0) ** 2 + loc[:, 1] ** 2 <= (W / 2) ** 2)
    shift = loc[inside, 2].min() - (FOAM_COMPRESSED + CHAMBER_MIN)
    c0 = centre_guess + shift * n
    return c0, u, v, n, {'roofPlaneFit': [a, b, c], 'tiltDeg': float(np.degrees(np.arccos(n[2]))),
                         'roofPointsUsed': int(inside.sum())}


def bbox_(M):
    return np.array(M.bounding_box()).reshape(2, 3)


def main():
    H = Head()
    cap = H.get('head_cap')
    cap_tm = tm_from_man(cap)
    # Clip region for added cap material: the cap plus the head cavity under it (the largest body of hull - cap).
    # Small bodies of hull - cap are exterior grooves bridged by the hull; added material must never fill them.
    pieces = sorted((m3.Manifold.batch_hull([cap]) - cap).decompose(), key=lambda m: -m.volume())
    hull = cap + pieces[0]
    c0, u, v, n, fit = speaker_frame(cap_tm)
    T = frame_T(c0, u, v, n)
    rec = {'speakerFrame': {'originFrontFaceCentre': c0.tolist(), 'u_long': u.tolist(), 'v_short': v.tolist(),
                            'n_front': n.tolist(), **fit}}

    # --- speaker (front face at n = 0, body to n = -4) and its lead envelope at the +u end (pads face the amp)
    spk = extrude(stadium(SPK_L, SPK_W), -SPK_FRAME, 0) + extrude(m3.CrossSection.circle(SPK_BOSS_D / 2, SEG), -SPK_T, -SPK_FRAME)
    # pads sit in a 6.2 x 1.9 mm notch of the back rim at one narrow end (drawing); solder joints + lead bend envelope
    pad_env = m3.Manifold.cube([4.0, 7.2, 3.55]).translate([SPK_L / 2 - 4.0, -3.6, -6.0])   # n -6.0..-2.45, below the ring wall
    speaker = apply(spk, T)
    speaker_leads = apply(pad_env - spk, T)

    # --- seat collar (cap material): ring wall + landing lip + two bosses, all extruded up into the roof
    top = 25.0
    ring = extrude(stadium(SPK_L, SPK_W, RING_CLEAR + RING_WALL) - stadium(SPK_L, SPK_W, RING_CLEAR), -SPK_FRAME + 0.2, top)
    lip = extrude(stadium(SPK_L, SPK_W, RING_CLEAR) - stadium(SPK_L, SPK_W, -LIP_W), FOAM_COMPRESSED, top)
    bosses = sum((extrude(m3.CrossSection.circle(BOSS_D / 2, SEG).translate([0, s * BOSS_V]), -SPK_FRAME, top)
                  for s in (-1, 1)), m3.Manifold())
    filler = extrude(stadium(SPK_L, SPK_W, -LIP_W + 0.01), FOAM_COMPRESSED + FRONT_GAP, top)  # keeps the front chamber shallow
    collar_local = ring + lip + bosses + filler
    chamber_local = extrude(stadium(SPK_L, SPK_W, -LIP_W), FOAM_COMPRESSED - 0.01, FOAM_COMPRESSED + FRONT_GAP)
    pocket_local = extrude(stadium(SPK_L, SPK_W, RING_CLEAR), -SPK_FRAME - 1, FOAM_COMPRESSED)
    pilots_local = sum((extrude(m3.CrossSection.circle(PILOT_D / 2, 24).translate([0, s * BOSS_V]), -SPK_FRAME - 0.01,
                                -SPK_FRAME + PILOT_DEPTH) for s in (-1, 1)), m3.Manifold())
    collar = (apply(collar_local - chamber_local - pocket_local, T) ^ hull)

    # --- retainer frame (separate print): rim band + ears, lead notch at +u, clearance holes Ø2.4
    ret_cs = (stadium(SPK_L, SPK_W, RING_CLEAR + RING_WALL) - stadium(SPK_L, SPK_W, -RET_INSET))
    for s in (-1, 1):
        ret_cs = ret_cs + m3.CrossSection.circle(BOSS_D / 2 + 0.6, SEG).translate([0, s * BOSS_V])
        ret_cs = ret_cs + m3.CrossSection.square([BOSS_D, BOSS_V]).translate([-BOSS_D / 2, 0 if s > 0 else -BOSS_V])
    ret_cs = ret_cs - stadium(SPK_L, SPK_W, -RET_INSET)
    for s in (-1, 1):
        ret_cs = ret_cs - m3.CrossSection.circle(1.2, 24).translate([0, s * BOSS_V])
    ret_cs = ret_cs - m3.CrossSection.square([12, PAD_NOTCH_W + 1.6]).translate([SPK_L / 2 - 4.0, -(PAD_NOTCH_W + 1.6) / 2])
    retainer = apply(extrude(ret_cs, -SPK_FRAME - RET_T, -SPK_FRAME), T)
    screws_spk = sum((apply(extrude(m3.CrossSection.circle(2.0, 32).translate([0, s * BOSS_V]), -SPK_FRAME - RET_T - 1.5,
                                    -SPK_FRAME - RET_T) + extrude(m3.CrossSection.circle(1.0, 24).translate([0, s * BOSS_V]),
                                                                  -SPK_FRAME - RET_T, -SPK_FRAME - RET_T + 6.0), T)
                      for s in (-1, 1)), m3.Manifold())

    # --- grille: holes along the print z axis, centres on a hex grid in the (u, v) plane, inside the chamber outline
    d = PRINT_Z_WORLD / np.linalg.norm(PRINT_Z_WORLD)
    centres = []
    rstep = GRILLE_PITCH * np.sqrt(3) / 2
    for k in range(-6, 7):                       # mirror-symmetric hex pattern about u = 0 and v = 0
        for j in range(-8, 9):
            centres.append(((j + 0.5 + 0.5 * (k % 2)) * GRILLE_PITCH, k * rstep))
    # filter with an exact test (stadium inset)
    Lc, Wc = SPK_L - 2 * (LIP_W + GRILLE_EDGE + GRILLE_D / 2), SPK_W - 2 * (LIP_W + GRILLE_EDGE + GRILLE_D / 2)
    centres = [(a, b) for a, b in centres if np.hypot(max(abs(a) - (Lc - Wc) / 2, 0), b) <= Wc / 2]
    holes = []
    for a, b in centres:
        p = c0 + a * u + b * v + FOAM_COMPRESSED * n
        cyl = m3.Manifold.cylinder(30.0, GRILLE_D / 2, GRILLE_D / 2, 24)
        z = np.array([0, 0, 1.0])
        ax = n   # along the speaker axis: hole walls stay parallel to the chamber wall (no slivers); 18 deg from print z
        k = np.cross(z, ax)
        s, cth = np.linalg.norm(k), z @ ax
        K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]]) / (s if s else 1)
        R = np.eye(3) + s * K + (1 - cth) * K @ K
        Tm = np.eye(4)
        Tm[:3, :3] = R
        Tm[:3, 3] = p
        holes.append(cyl.transform(Tm[:3, :]))
    grille = m3.Manifold.batch_boolean(holes, m3.OpType.Add)

    # --- amplifier (board frame: x from header edge backwards, y across, z up from PCB top)
    xe, zt = AMP_HEADER_EDGE_X, AMP_PCB_TOP_Z
    x0 = xe - AMP_L
    board_cs = m3.CrossSection.square([AMP_L, AMP_W]).translate([x0, -AMP_W / 2])
    board = extrude(board_cs, zt - AMP_T, zt)
    hole_xy = [(x0 + AMP_HOLE_IN, -AMP_W / 2 + AMP_HOLE_IN), (x0 + AMP_HOLE_IN, AMP_W / 2 - AMP_HOLE_IN)]
    for hx, hy in hole_xy:
        board = board - extrude(m3.CrossSection.circle(AMP_HOLE_D / 2, 24).translate([hx, hy]), zt - 3, zt + 1)
    # terminal block over the hole edge (brd centre 3.56 mm from that edge), mouths facing -x (the speaker)
    tb = extrude(m3.CrossSection.square([TB_D, TB_W]).translate([x0 - 0.5, -TB_W / 2]), zt, zt + TB_H)
    smd = extrude(m3.CrossSection.square([AMP_L - TB_D - 4.5, AMP_W - 3]).translate([x0 + TB_D, -AMP_W / 2 + 1.5]), zt, zt + 1.2)
    under = extrude(m3.CrossSection.square([AMP_L - 1, AMP_W - 1]).translate([x0 + 0.5, -AMP_W / 2 + 0.5]), zt - AMP_T - 1.5, zt - AMP_T)
    pins_y = [-AMP_W / 2 + 1.27 + 2.54 * i for i in range(7)]   # LRC at -y ... Vin at +y (silkscreen order)
    names = ['LRC', 'BCLK', 'DIN', 'GAIN', 'SD', 'GND', 'Vin']
    ra_body = extrude(m3.CrossSection.square([RA_BODY + 2.54, AMP_W]).translate([xe - 2.54 - 1.27, -AMP_W / 2]), zt,
                      zt + RA_PIN_Z + RA_BODY / 2)
    amp = board + tb + smd + under + ra_body
    housings = []
    hx0 = xe - 2.54 - 1.27 + RA_BODY + 2.54   # mating face of the RA body
    for nm, yy in zip(names, pins_y):
        if nm == 'SD':
            continue
        housings.append((nm, m3.Manifold.cube([HOUSING_L, HOUSING_S, HOUSING_S]).translate([hx0, yy - HOUSING_S / 2, zt + RA_PIN_Z - HOUSING_S / 2])))
    amp_housings = m3.Manifold.batch_boolean([h for _, h in housings], m3.OpType.Add)
    posts = sum((extrude(m3.CrossSection.circle(AMP_POST_D / 2, SEG).translate([hx, hy]), zt, 170) for hx, hy in hole_xy), m3.Manifold())
    post_pilots = sum((extrude(m3.CrossSection.circle(PILOT_D / 2, 24).translate([hx, hy]), zt - 0.01, zt + 5.5) for hx, hy in hole_xy), m3.Manifold())
    posts = (posts ^ hull)
    amp_screws = sum((extrude(m3.CrossSection.circle(2.0, 32).translate([hx, hy]), zt - AMP_T - 1.5, zt - AMP_T)
                      + extrude(m3.CrossSection.circle(1.0, 24).translate([hx, hy]), zt - AMP_T, zt - AMP_T + 6.0)
                      for hx, hy in hole_xy), m3.Manifold())

    # --- Pi-end housings on pins 4, 12, 14 (even, from the pin 6 envelope) and 35 (odd, from pin 5), 40 (even)
    e6, e5 = H.get('head_pi_gpio_pin_06_receiving'), H.get('head_pi_gpio_pin_05_receiving')
    y6, y5 = 24.13 - 2.54 * 2, 24.13 - 2.54 * 2
    pi_h = {f'pin{p:02d}': (e6 if p % 2 == 0 else e5).translate([0, (24.13 - 2.54 * ((p + 1) // 2 - 1)) - (y6 if p % 2 == 0 else y5), 0])
            for p in (4, 12, 14, 35, 40)}

    # --- extension cap = V1.8 cap + collar + posts - chamber/pocket voids - grille - pilots
    cap_ext = (cap + collar + posts) - grille - apply(pilots_local, T) - post_pilots
    # boolean round-off leaves zero-volume crumbs along the old cap surface; keep only real bodies (> 0.01 mm3)
    rec['removedOutsideIntendedCutsMm3'] = round(((cap - cap_ext) - grille - apply(pilots_local, T) - post_pilots).volume(), 4)
    added = m3.Manifold.batch_boolean([b for b in (cap_ext - cap).decompose() if b.volume() > 0.01], m3.OpType.Add)
    removed = m3.Manifold.batch_boolean([b for b in (cap - cap_ext).decompose() if b.volume() > 0.01], m3.OpType.Add)

    parts = {'speaker': speaker, 'speaker_leads_envelope': speaker_leads, 'speaker_retainer': retainer,
             'speaker_screws_envelope': screws_spk, 'amplifier': amp, 'amp_housings': amp_housings,
             'amp_screws_envelope': amp_screws, 'cap_added_material': added, 'cap_removed_material': removed,
             'head_cap_extension': cap_ext, **{f'pi_housing_{k}': m for k, m in pi_h.items()}}
    files = {}
    for k, M in parts.items():
        tm = tm_from_man(M)
        f = OUT / f'{k}-world.stl'
        tm.export(f)
        files[k] = {'file': str(f), 'volumeMm3': round(M.volume(), 3), 'bounds': np.round(tm.bounds, 3).tolist(),
                    'closed': bool(tm.is_watertight), 'bodies': len(M.decompose())}
    rec['clearances'] = {
        'terminalBlockToCapMm': round(float(tb.min_gap(cap_ext, 10)), 3),
        'ampHousingsToCapMm': round(float(amp_housings.min_gap(cap_ext, 10)), 3),
        'ampHousingsToPiMm': round(float(amp_housings.min_gap(H.get('pi'), 10)), 3),
        'speakerToCapMm': round(float(speaker.min_gap(cap_ext, 10)), 3),
        'speakerFrontToLandingMm': FOAM_COMPRESSED,
        'speakerCollarToAmpMm': round(float(collar.min_gap(amp + amp_housings, 10)), 3),
        'retainerToAmpMm': round(float(retainer.min_gap(amp + amp_housings, 10)), 3),
        'note': 'terminal block height is an assumed 10 mm envelope (unpublished); measure the owned board'}
    hole_area = len(centres) * np.pi * (GRILLE_D / 2) ** 2
    rec.update({
        'parameters': {k: v for k, v in globals().items() if k.isupper() and isinstance(v, (int, float, tuple, list))},
        'grille': {'holes': len(centres), 'holeDiameterMm': GRILLE_D, 'pitchMm': GRILLE_PITCH,
                   'openAreaMm2': round(hole_area, 1),
                   'chamberOpeningAreaMm2': round(stadium(SPK_L, SPK_W, -LIP_W).area(), 1),
                   'speakerOutlineAreaMm2': round(stadium(SPK_L, SPK_W).area(), 1),
                   'axisWorld': n.tolist(), 'axisFromPrintZDeg': float(np.degrees(np.arccos(abs(n @ d)))), 'centresUV': [list(map(float, c)) for c in centres]},
        'amplifier': {'boardX': [x0, xe], 'boardY': [-AMP_W / 2, AMP_W / 2], 'pcbTopZ': zt, 'holesXY': hole_xy,
                      'pinYOrder': dict(zip(names, pins_y)), 'housingEndX': hx0 + HOUSING_L},
        'files': files})
    (STUDY / 'study-build.json').write_text(json.dumps(rec, indent=1, default=float))
    print(json.dumps({k: (v['volumeMm3'], v['bodies'], v['closed']) for k, v in files.items()}))
    for k in ('head_cap_extension', 'cap_added_material', 'cap_removed_material'):
        bs = sorted(parts[k].decompose(), key=lambda m: -m.volume())
        print(k, [(round(b.volume(), 3), np.round(bbox_(b), 1).tolist()) for b in bs[:6]])
    print('grille', rec['grille']['holes'], rec['grille']['openAreaMm2'], 'frame', rec['speakerFrame'])


if __name__ == '__main__':
    main()
