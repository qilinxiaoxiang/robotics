#!/usr/bin/env python3
"""MicroDuck V1.9 head audio: placement and clearance study for the 100 kOhm GAIN-to-Vin resistor on the MAX98357A
breakout (Adafruit 3006). Problem IDs P5 (head integration) and P6 (build and assembly).

Owner decision (settled): a YAGEO MFR-25FBF52-100K axial resistor bridges the header GAIN pin and Vin pin for 3 dB.
The bench procedure (bringup/build/audio-bench, img/underside + img/endview) puts it on the board UNDERSIDE: body
parallel to the header row, axis 3.0 mm inboard of the row (away from the board edge) and 2.45 mm below the PCB,
clear heat-shrink over the body (1.0 mm below the PCB), legs bent 1.3 mm from the body, run towards the row and hooked
round the outer side of the GAIN and Vin tails, solder over each hook, Kapton over the joints. Finished stack about
4.0 mm below the PCB bottom. The amplifier stays where the audio study put it.

Frame: robot frame at q = 0, mm, x forward, y left, z up. Amp board x 22.25..41.3, y -8.89..8.89, z 138.23..139.8,
components up, header edge at +x. Board mapping from the Adafruit EAGLE file: x_world = 41.3 - y_brd,
y_world = x_brd - 8.89 (a proper rotation, top side up).

Envelopes (all checked):
  U4_box    the coordinator's 4.0 mm stack: one box under the board, 10.0 mm along the row (outside of the GAIN hook to
            outside of the Vin hook), 6.2 mm across (a 4 mm band centred on the body axis, extended outboard over the
            tail hooks and joints), 4.0 mm deep. Exported as resistor_envelope_v19-world.stl.
  U4_detail body (datasheet max 6.8 x 2.6 + 0.25 heat-shrink wall + 0.1 margin per side) + 0.8 mm legs + hook rings +
            solder/Kapton joints, drawing placement, 1.5 mm tails.
  U5_box / U5_detail  2.5 mm tails with everything lowered 1.0 mm (hook keeps its place on the longer tail): 5.0 mm
            stack. The other five tails are also built 2.5 mm long and checked (tails_2p5).
  T_detail  top-side fallback: body behind the vertical pin segments, legs hooked round the GAIN and Vin pin roots.
Checks: exact manifold3d overlap volume and min_gap against every solid near the amp (cap, Pi and its parts, camera,
amp housings and jumpers, A3 bundle, speaker parts, head-fixed lower parts), jaw 0..40 deg and head roll over the
MJCF range (nr_lib.FK), neck_pitch body over head yaw x roll, and the 40 mm cap descent as an exact swept solid (hull
of each convex envelope piece with its copy 40 mm higher). Pass: >= 0.5 mm static, >= 0.3 mm swept, zero overlap.
Soldering access: a generic fine conical iron (assumption) placed on each joint over a direction grid.

Run with the bounded runner:
  run_bounded_cad.py --max-mib 1536 --seconds 1500 --wait-lock-seconds 60 --report <json> --
      /tmp/microduck-cad-venv/bin/python resistor_study.py [--cap PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/print/ext-v19/scripts')
import ext_lib as E  # noqa: E402

import manifold3d as m3  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402

import nr_lib  # noqa: E402  (on sys.path through ext_lib)

OUT_JSON = E.OUT / 'resistor-placement.json'
OUT_STL = E.OUT / 'resistor_envelope_v19-world.stl'
SCR = E.SCRATCH / 'resistor'
SCR.mkdir(parents=True, exist_ok=True)
BENCH = E.SIM / 'bringup' / 'build' / 'audio-bench'
AUDIO_SOLIDS = E.AUDIO / 'study-solids'
INT_SOLIDS = E.STUDY_INT / 'study-solids'
WIRE_ROUTES = E.AUDIO / 'wire-routes.json'
BRD_LOCAL = SCR / 'brd' / 'mono.brd'
YAGEO_LOCAL = SCR / 'sources' / 'yageo' / 'YAGEO-MFR_DATASHEET.pdf'
SULLINS_LOCAL = SCR / 'sources' / 'sullins' / '11637.pdf'

STATIC_MIN, SWEPT_MIN, SEARCH = 0.5, 0.3, 12.0
REPORT_SEARCH = 40.0                         # static gaps are reported out to 40 mm (Pi, camera, jumpers)
SEG = 40

# ---- board (Adafruit "Adafruit MAX98357 Breakout.brd", verified 2026-10-13) ----
BOARD_EDGE_X, BOARD_W, BOARD_L, BOARD_T = 41.3, 17.78, 19.05, 1.57
PCB_TOP = 139.8
PCB_BOT = PCB_TOP - BOARD_T                  # 138.23
ROW_FROM_EDGE = 2.54                         # JP1 pads at y_brd = 2.54
ROW_X = BOARD_EDGE_X - ROW_FROM_EDGE         # 38.76
PAD_D = 1.9304                               # JP1 round pads, drill 1.0
PITCH = 2.54
PINS = {'LRC': -7.62, 'BCLK': -5.08, 'DIN': -2.54, 'GAIN': 0.0, 'SD': 2.54, 'GND': 5.08, 'Vin': 7.62}
PIN_SQ = 0.64                                # 0.025 in square post (Sullins drawing; header brand unknown: inference)

# ---- resistor (YAGEO MFR datasheet V.4, 3 Apr 2024, p3: MFR-25 row "6.3 ± 0.5  2.4 ± 0.2  28 ± 2.0  0.55 ± 0.05") ----
R_L_NOM, R_L_MAX, R_D_NOM, R_D_MAX, R_LEAD_D = 6.3, 6.8, 2.4, 2.6, 0.55
HS_WALL = 0.25                               # bench drawing: body r 1.2 -> clear heat-shrink r 1.45
HS_OVER = 0.35                               # bench drawing: heat-shrink 7.0 long over the 6.3 body
MARGIN = 0.1                                 # +0.2 mm on each dimension
LEAD_ENV_R = 0.4                             # 0.8 mm lead cylinders (task); real lead 0.55 +/- 0.05
# ---- bench drawing placement (img/endview.html 34 px/mm, img/underside.html 30 px/mm) ----
AXIS_INBOARD = 3.0                           # body axis 3.0 mm inboard of the row (endview 473.4-371.4 px)
AXIS_BELOW = 2.45                            # body axis 2.45 mm below the PCB bottom (endview 344.3-261 px)
HOOK_BELOW = 0.9                             # leg crosses the tail 0.9 mm below the PCB (endview 291.6-261 px)
LEAD_OUT = 0.67                              # leg runs 0.67 mm outboard of each tail centre (underside 20 px)
HOOK_R = 0.67                                # hook arc radius round the tail (underside A20)
JOINT_R = 1.2                                # solder over the hook (underside r 0.67 + 0.4 leg) + Kapton, rounded up
TAIL_NOM, TAIL_LONG = 1.5, 2.5               # coordinator: about 1.5 mm, assume up to 2.5 mm
STACK_NOM = 4.0                              # bench drawing "约 4 mm"
BAND_W = 4.0                                 # coordinator: 4 mm wide band centred on the body

# ---- top-side parts from the .brd (positions verified; heights are inference, conservative) ----
# (name, brd x, brd y, rotated 90?, long side, short side, height)
SMD = [('U1', 8.89, 7.62, True, 3.0, 3.0, 0.8), ('R1', 13.716, 5.334, False, 2.0, 1.25, 0.65),
       ('C1', 12.7, 8.128, True, 2.0, 1.25, 1.45), ('C2', 14.732, 8.128, True, 2.0, 1.25, 1.45),
       ('FB1', 11.43, 10.922, False, 2.0, 1.25, 1.45), ('FB2', 6.35, 10.922, False, 2.0, 1.25, 1.45),
       ('C4', 2.54, 10.922, False, 2.0, 1.25, 1.45), ('C5', 15.113, 10.922, False, 2.0, 1.25, 1.45)]
TB_TAILS_BRD = [(7.09, 15.494), (10.59, 15.494)]
# right-angle header, top side (Sullins 11637 rev F geometry; the owner's header brand is unknown: inference)
RA_PIN_H = 1.27             # pin centre above the board (drawn centred in the 2.54 insulator)
RA_TAIL_TO_FRONT = 4.02     # ".158[4.02]" tail centreline to insulator front face
RA_INS_DEPTH, RA_INS_H, RA_MATE = 2.50, 2.54, 5.84


def w(xb, yb):
    return np.array([BOARD_EDGE_X - yb, xb - BOARD_W / 2])


# ------------------------------------------------------------------------------------------------ geometry helpers
def boxm(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return m3.Manifold.cube((hi - lo).tolist()).translate(lo.tolist())


def sph(c, r):
    return m3.Manifold.sphere(float(r), 24).translate([float(v) for v in c])


def seg(a, b, r):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return E.cyl(a, b - a, np.linalg.norm(b - a), r, 24)


def tube(pts, r):
    pts = [np.asarray(p, float) for p in pts]
    return [seg(p, q, r) for p, q in zip(pts[:-1], pts[1:]) if np.linalg.norm(q - p) > 1e-6] + [sph(p, r) for p in pts]


def zcyl(cx, cy, z0, z1, r):
    return m3.Manifold.cylinder(float(z1 - z0), float(r), float(r), SEG).translate([float(cx), float(cy), float(z0)])


def frustum_down(cx, cy, ztop, rtop, rbot, h):
    return m3.Manifold.cylinder(float(h), float(rbot), float(rtop), SEG).translate([float(cx), float(cy), float(ztop - h)])


def union(ps):
    ps = [p for p in ps if p is not None and not p.is_empty()]
    return m3.Manifold.batch_boolean(ps, m3.OpType.Add) if len(ps) > 1 else ps[0]


def swept_z(pieces, travel=40.0):
    return union([m3.Manifold.batch_hull([p, p.translate([0, 0, travel])]) for p in pieces])


def ring(cx, cy, z, R, n=16):
    a = np.linspace(0, 2 * np.pi, n + 1)
    return [np.array([cx + R * np.cos(t), cy + R * np.sin(t), z]) for t in a]


def bbox(M):
    return np.array(M.bounding_box()).reshape(2, 3)


def near(a, b, pad):
    A, B = bbox(a), bbox(b)
    return bool(np.all(A[0] - pad <= B[1]) and np.all(B[0] - pad <= A[1]))


def clearance(A, B, search=SEARCH):
    """(overlap mm3, min gap mm or None if farther than search)."""
    if not near(A, B, search):
        return 0.0, None
    ov = float((A ^ B).volume())
    g = float(A.min_gap(B, search))
    return ov, (None if g >= search - 1e-9 else g)


def man_of(path):
    return E.stl_man(str(path))


# ------------------------------------------------------------------------------------------------ amp model
def amp_parts(tail):
    """Detailed amp items near the resistor (board, header tails with fillets, terminal-block tails, top SMD parts and
    the right-angle header). Returns dict name -> Manifold."""
    P = {}
    P['amp_board'] = boxm([BOARD_EDGE_X - BOARD_L, -BOARD_W / 2, PCB_BOT], [BOARD_EDGE_X, BOARD_W / 2, PCB_TOP])
    for nm, y in PINS.items():
        t = boxm([ROW_X - PIN_SQ / 2, y - PIN_SQ / 2, PCB_BOT - tail], [ROW_X + PIN_SQ / 2, y + PIN_SQ / 2, PCB_BOT])
        fil = frustum_down(ROW_X, y, PCB_BOT, PAD_D / 2, 0.45, 0.6)      # pad-wide fillet cone (inference)
        P[f'tail_{nm}'] = t + fil
        # top side: vertical segment, bend run to the insulator, mating pin
        zc = PCB_TOP + RA_PIN_H
        vert = boxm([ROW_X - PIN_SQ / 2, y - PIN_SQ / 2, PCB_TOP], [ROW_X + PIN_SQ / 2, y + PIN_SQ / 2, zc + PIN_SQ / 2])
        horiz = boxm([ROW_X - PIN_SQ / 2, y - PIN_SQ / 2, zc - PIN_SQ / 2],
                     [ROW_X + RA_TAIL_TO_FRONT + RA_MATE, y + PIN_SQ / 2, zc + PIN_SQ / 2])
        topfil = zcyl(ROW_X, y, PCB_TOP, PCB_TOP + 0.3, PAD_D / 2)        # top pad + small fillet (inference)
        P[f'pinvert_{nm}'] = vert + topfil
        P[f'pinrun_{nm}'] = horiz - boxm([ROW_X - 1, y - 1, PCB_TOP], [ROW_X + PIN_SQ / 2, y + 1, zc + 1])
    xf = ROW_X + RA_TAIL_TO_FRONT
    P['header_insulator'] = boxm([xf - RA_INS_DEPTH, -BOARD_W / 2, PCB_TOP], [xf, BOARD_W / 2, PCB_TOP + RA_INS_H])
    for i, (xb, yb) in enumerate(TB_TAILS_BRD):
        x, y = w(xb, yb)
        P[f'tb_tail_{i + 1}'] = zcyl(x, y, PCB_BOT - tail, PCB_BOT, 0.5) + frustum_down(x, y, PCB_BOT, 1.09, 0.5, 0.6)
    for nm, xb, yb, rot, L, S, h in SMD:
        x, y = w(xb, yb)
        dx, dy = (L, S) if rot else (S, L)          # R90 parts: long side along brd y = world x
        P[f'smd_{nm}'] = boxm([x - dx / 2, y - dy / 2, PCB_TOP], [x + dx / 2, y + dy / 2, PCB_TOP + h])
    return P


# ------------------------------------------------------------------------------------------------ envelopes
def underside_detail(tail, shift):
    """Bench-drawing placement with datasheet-max body. Returns (pieces, parts, record)."""
    zb = PCB_BOT - shift
    xc, yc, zc = ROW_X - AXIS_INBOARD, (PINS['GAIN'] + PINS['Vin']) / 2, zb - AXIS_BELOW
    r_env = R_D_MAX / 2 + HS_WALL + MARGIN
    L_env = R_L_MAX + 2 * HS_OVER + 2 * MARGIN
    body = E.cyl([xc, yc - L_env / 2, zc], [0, 1, 0], L_env, r_env, SEG)
    pieces, legs, joints = [body], [], []
    rec = {'bodyCentre': [xc, yc, zc], 'bodyAxis': [0, 1, 0], 'bodyEnvelopeDiameterMm': 2 * r_env,
           'bodyEnvelopeLengthMm': L_env, 'legs': {}}
    for nm, sgn in (('GAIN', -1), ('Vin', +1)):
        yp = PINS[nm]
        yend = yc + sgn * R_L_MAX / 2               # lead leaves the end cap on the axis
        ybend = yp + sgn * LEAD_OUT                 # legs run 0.67 outboard of each tail
        zh = PCB_BOT - HOOK_BELOW - shift
        p0 = [xc, yend, zc]
        p1 = [xc, ybend, zc]
        p2 = [ROW_X - LEAD_OUT, ybend, zh]
        hook = ring(ROW_X, yp, zh, HOOK_R)
        lp = tube([p0, p1, p2], LEAD_ENV_R) + tube(hook, LEAD_ENV_R) + tube([p2, hook[10 if sgn < 0 else 6]], LEAD_ENV_R)
        # solder over the hook + Kapton: pad-wide at the board (solder mask stops it), JOINT_R from 0.5 mm down to the
        # tail tip + 0.3 mm
        jt = union([frustum_down(ROW_X, yp, PCB_BOT, PAD_D / 2, JOINT_R, 0.5),
                    zcyl(ROW_X, yp, PCB_BOT - tail - 0.3, PCB_BOT - 0.5, JOINT_R)])
        legs += lp
        joints.append(jt)
        rec['legs'][nm] = {'leavesBodyAt': p0, 'bendAt': p1, 'reachesRowAt': p2, 'hookCentre': [ROW_X, yp, zh],
                           'hookRadiusMm': HOOK_R, 'bendDistanceFromBodyEndMm': round(abs(ybend - yend), 3),
                           'solderPoint': [ROW_X, yp, zh], 'jointEnvelope': {'radiusMm': JOINT_R,
                                                                           'z': [PCB_BOT - tail - 0.3, PCB_BOT]}}
    pieces += legs + joints
    rec['depthBelowPcbMm'] = round(PCB_BOT - (zc - r_env), 3)
    return pieces, {'body': body, 'legs': union(legs), 'joints': union(joints)}, rec


def underside_box(depth, tail):
    x_in = ROW_X - AXIS_INBOARD - BAND_W / 2
    x_out = ROW_X + JOINT_R
    y0, y1 = PINS['GAIN'] - JOINT_R, PINS['Vin'] + JOINT_R
    B = boxm([x_in, y0, PCB_BOT - depth], [x_out, y1, PCB_BOT])
    return [B], {'box': B}, {'x': [x_in, x_out], 'y': [y0, y1], 'z': [PCB_BOT - depth, PCB_BOT],
                             'alongRowMm': y1 - y0, 'acrossRowMm': x_out - x_in, 'depthBelowPcbMm': depth,
                             'tailMm': tail}


def topside_detail():
    """Fallback: body behind the vertical pin segments, over R1, legs hooked round the GAIN and Vin pin roots."""
    r_env = R_D_MAX / 2 + HS_WALL + MARGIN
    L_env = R_L_MAX + 2 * HS_OVER + 2 * MARGIN
    xc = ROW_X - PIN_SQ / 2 - STATIC_MIN - r_env
    zc = PCB_TOP + 0.65 + STATIC_MIN + r_env          # above R1 (0.65 high, inference)
    yc = (PINS['GAIN'] + PINS['Vin']) / 2
    body = E.cyl([xc, yc - L_env / 2, zc], [0, 1, 0], L_env, r_env, SEG)
    legs, joints, rec = [], [], {'bodyCentre': [xc, yc, zc], 'bodyAxis': [0, 1, 0], 'legs': {},
                                 'bodyEnvelopeDiameterMm': 2 * r_env, 'bodyEnvelopeLengthMm': L_env}
    zh = PCB_TOP + 0.8                                # hook above the top-pad fillet
    for nm, sgn in (('GAIN', -1), ('Vin', +1)):
        yp = PINS[nm]
        p0, p1, p2 = [xc, yc + sgn * R_L_MAX / 2, zc], [xc, yp + sgn * LEAD_OUT, zc], [ROW_X - LEAD_OUT, yp + sgn * LEAD_OUT, zh]
        hook = ring(ROW_X, yp, zh, HOOK_R)
        legs += tube([p0, p1, p2], LEAD_ENV_R) + tube(hook, LEAD_ENV_R) + tube([p2, hook[10 if sgn < 0 else 6]], LEAD_ENV_R)
        # solder over the hook: pad-wide at the board, widening to 1.1 mm (hook outer radius 1.07) at 0.6 mm, to 1.6 mm
        joints.append(union([m3.Manifold.cylinder(0.6, PAD_D / 2, 1.1, SEG).translate([ROW_X, yp, PCB_TOP]),
                             zcyl(ROW_X, yp, PCB_TOP + 0.6, PCB_TOP + 1.6, 1.1)]))
        rec['legs'][nm] = {'leavesBodyAt': p0, 'bendAt': p1, 'reachesPinAt': p2, 'solderPoint': [ROW_X, yp, zh]}
    rec['heightAbovePcbMm'] = round(zc + r_env - PCB_TOP, 3)
    return [body] + legs + joints, {'body': body, 'legs': union(legs), 'joints': union(joints)}, rec


# ------------------------------------------------------------------------------------------------ scene
def load_scene(cap_path):
    man = E.ia_lib.manifest()
    S = {}   # name -> (Manifold, ride, source)
    S['head_cap'] = (man_of(cap_path), 'cap', str(cap_path))
    for k in ['amp_housings', 'amp_screws_envelope', 'speaker', 'speaker_leads_envelope', 'speaker_retainer',
              'speaker_screws_envelope', 'pi_housing_pin04', 'pi_housing_pin12', 'pi_housing_pin14',
              'pi_housing_pin35', 'pi_housing_pin40']:
        S[k] = (man_of(AUDIO_SOLIDS / f'{k}-world.stl'), 'cap', str(AUDIO_SOLIDS / f'{k}-world.stl'))
    for k, ride in [('A3_group_cap_held', 'cap'), ('A3_fan_wires', 'cap'), ('A3_clip_cap', 'cap'),
                    ('A3_group_slot_to_clip', 'lower'), ('A3_clip_head', 'lower'), ('A3_group_free', 'flex'),
                    ('A3_group_in_head', 'flex')]:
        S[k] = (man_of(INT_SOLIDS / f'{k}-world.stl'), ride, str(INT_SOLIDS / f'{k}-world.stl'))
    routes = json.loads(WIRE_ROUTES.read_text())
    for k, pts in routes.items():
        r = 0.6 if k.startswith('spk') else 0.7
        S[f'jumper_{k}'] = (union(tube(pts, r)), 'cap', f'{WIRE_ROUTES}:{k} r {r}')
    want = {'pi', 'camera_board', 'jaw_support', 'jaw_frame', 'motor14', 'motor15', 'head_bottom', 'face_panel',
            'mouth_sliding_ring', 'eye_trim', 'motor13', 'head_yaw_link', 'head_roll_ring_a', 'head_roll_ring_b',
            'neck_pitch', 'neck_pitch_ring'}
    lo, hi = np.array([30.0, -6.0, 132.0]), np.array([45.0, 14.0, 146.0])   # around every candidate
    for k, m in man.items():
        b = np.array(m['bounds'])
        d = np.linalg.norm(np.maximum(0, np.maximum(b[0] - hi, lo - b[1])))
        if k.startswith('head_pi_') or (d < 30 and k != 'head_cap'):
            want.add(k)
    for k in sorted(want):
        body = nr_lib.body_of(k)
        ride = {'jaw_soft': 'cap' if (k == 'pi' or k.startswith('head_pi_')) else 'lower', 'jaw': 'jaw',
                'yaw_roll_motion': 'yaw', 'neck_pitch': 'neckpitch'}.get(body, 'other')
        S[k] = (E.load_man(k), ride, f'ia-cache:{k}')
    return S


class Motion:
    def __init__(self):
        self.fk = nr_lib.FK()
        self.roll = [float(v) for v in self.fk.range['head_roll']]
        self.yaw = [float(v) for v in self.fk.range['head_yaw']]

    def rel(self, q, body):
        T = self.fk.part_T(q)
        return np.linalg.inv(T['jaw_soft']) @ T[body]


def worst_sweep(env, O0, Tfun, grid, refine):
    """grid: list of parameter tuples; Tfun(params) -> 4x4. Coarse pass then a refine pass around the worst pose."""
    best = {'overlapMm3': 0.0, 'gapMm': None, 'at': None}

    def visit(p):
        O = O0.transform(Tfun(p)[:3, :])
        ov, g = clearance(env, O)
        if ov > best['overlapMm3'] + 1e-9 or (best['overlapMm3'] <= 1e-9 and ov <= 1e-9 and g is not None
                                               and (best['gapMm'] is None or g < best['gapMm'])):
            best.update({'overlapMm3': ov, 'gapMm': g, 'at': list(p)})
    for p in grid:
        visit(p)
    if best['at'] is not None:
        for p in refine(best['at']):
            visit(p)
    return best


def check_envelope(name, env, pieces, S, mot, amp, amp_skip=()):
    rows = []
    swept = swept_z(pieces, 40.0)
    for k, (O, ride, _) in S.items():
        ov, g = clearance(env, O, REPORT_SEARCH)
        row = {'with': k, 'ride': ride, 'staticOverlapMm3': round(ov, 4), 'staticGapMm': None if g is None else round(g, 3)}
        if ride == 'jaw':
            def T(p):
                return mot.rel({'jaw': p[0]}, 'jaw')
            grid = [(a,) for a in np.arange(0.0, 40.0 + 1e-9, 1.0)]
            ref = (lambda at: [(a,) for a in np.arange(max(0, at[0] - 1), min(40, at[0] + 1) + 1e-9, 0.1)])
            r = worst_sweep(env, O, T, grid, ref)
            row['jawSweep'] = {'overlapMm3': round(r['overlapMm3'], 4), 'gapMm': None if r['gapMm'] is None else round(r['gapMm'], 3),
                               'jawDeg': None if r['at'] is None else round(r['at'][0], 2)}
        if ride == 'yaw':
            lo, hi = np.degrees(mot.roll)

            def T(p):
                return mot.rel({'head_roll': np.radians(p[0])}, 'yaw_roll_motion')
            grid = [(a,) for a in np.arange(lo, hi + 1e-9, 1.0)] + [(hi,)]
            ref = (lambda at: [(a,) for a in np.arange(max(lo, at[0] - 1), min(hi, at[0] + 1) + 1e-9, 0.1)])
            r = worst_sweep(env, O, T, grid, ref)
            row['rollSweep'] = {'overlapMm3': round(r['overlapMm3'], 4), 'gapMm': None if r['gapMm'] is None else round(r['gapMm'], 3),
                                'rollDeg': None if r['at'] is None else round(r['at'][0], 2)}
        if ride == 'neckpitch':
            rl, rh = np.degrees(mot.roll)
            yl, yh = np.degrees(mot.yaw)

            def T(p):
                return mot.rel({'head_yaw': np.radians(p[0]), 'head_roll': np.radians(p[1])}, 'neck_pitch')
            grid = [(a, b) for a in np.linspace(yl, yh, 13) for b in np.linspace(rl, rh, 11)]
            ref = (lambda at: [(a, b) for a in np.linspace(max(yl, at[0] - 6), min(yh, at[0] + 6), 7)
                               for b in np.linspace(max(rl, at[1] - 5), min(rh, at[1] + 5), 7)])
            r = worst_sweep(env, O, T, grid, ref)
            row['yawRollSweep'] = {'overlapMm3': round(r['overlapMm3'], 4), 'gapMm': None if r['gapMm'] is None else round(r['gapMm'], 3),
                                   'yawRollDeg': None if r['at'] is None else [round(v, 2) for v in r['at']]}
        if ride in ('lower', 'jaw', 'yaw', 'neckpitch', 'other'):
            ovs, gs = clearance(swept, O)
            row['capDescent40'] = {'sweptOverlapMm3': round(max(0.0, ovs - ov), 4), 'minGapAlongPathMm': None if gs is None else round(gs, 3)}
        rows.append(row)
    amp_rows = []
    for k, O in amp.items():
        if k in amp_skip:
            continue
        ov, g = clearance(env, O)
        amp_rows.append({'with': k, 'staticOverlapMm3': round(ov, 4), 'staticGapMm': None if g is None else round(g, 3)})
    return rows, amp_rows


def verdict(rows, amp_rows):
    fails, worst = [], []
    for r in rows:
        if r['staticOverlapMm3'] > 1e-6 or (r['staticGapMm'] is not None and r['staticGapMm'] < STATIC_MIN):
            fails.append({'with': r['with'], 'check': 'static', 'overlapMm3': r['staticOverlapMm3'], 'gapMm': r['staticGapMm']})
        for key in ('jawSweep', 'rollSweep', 'yawRollSweep'):
            if key in r and (r[key]['overlapMm3'] > 1e-6 or (r[key]['gapMm'] is not None and r[key]['gapMm'] < SWEPT_MIN)):
                fails.append({'with': r['with'], 'check': key, **r[key]})
        if 'capDescent40' in r:
            d = r['capDescent40']
            if d['sweptOverlapMm3'] > 1e-6 or (d['minGapAlongPathMm'] is not None and d['minGapAlongPathMm'] < SWEPT_MIN):
                fails.append({'with': r['with'], 'check': 'capDescent40', **d})
    for r in amp_rows:
        if r['staticOverlapMm3'] > 1e-6 or (r['staticGapMm'] is not None and r['staticGapMm'] < STATIC_MIN):
            fails.append({'with': r['with'], 'check': 'amp static', 'overlapMm3': r['staticOverlapMm3'], 'gapMm': r['staticGapMm']})
    # five closest numbers of any kind
    cand = []
    for r in rows:
        if r['staticGapMm'] is not None:
            cand.append((r['staticGapMm'], r['with'], 'static'))
        for key in ('jawSweep', 'rollSweep', 'yawRollSweep'):
            if key in r and r[key]['gapMm'] is not None:
                cand.append((r[key]['gapMm'], r['with'], key))
        if 'capDescent40' in r and r['capDescent40']['minGapAlongPathMm'] is not None:
            cand.append((r['capDescent40']['minGapAlongPathMm'], r['with'], 'capDescent40'))
    cand.sort()
    worst = [{'gapMm': g, 'with': k, 'check': c} for g, k, c in cand[:8]]
    return {'pass': not fails, 'failures': fails, 'closest': worst}


# ------------------------------------------------------------------------------------------------ soldering access
def iron(P, d):
    """Assumed generic fine conical tip (Hakko T18-B class, not measured): R0.5 tip, cone to r 2.0 over 10 mm, r 2.0 to
    20 mm, then a r 3.5 heater/grip barrel to 80 mm. P = tip-sphere centre, d = unit direction towards the handle."""
    d = np.asarray(d, float) / np.linalg.norm(d)
    u, v, a = E.frame(d)
    T = np.c_[u, v, a, np.asarray(P, float)]
    cone = m3.Manifold.cylinder(10.0, 0.5, 2.0, 24).transform(T)
    shaft = m3.Manifold.cylinder(10.0, 2.0, 2.0, 24).translate([0, 0, 10.0]).transform(T)
    barrel = m3.Manifold.cylinder(60.0, 3.5, 3.5, 24).translate([0, 0, 20.0]).transform(T)
    return union([sph(P, 0.5), cone, shaft, barrel])


def fib_dirs(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = np.pi * (1 + 5 ** 0.5) * i
    return np.c_[np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)]


def access(joint_pts, side, obstacles, n=500):
    """For each joint: directions (hemisphere on the joint's side of the board) where the iron touches the joint
    without touching any obstacle. Tip sphere centre 1.3 mm from the pin axis, horizontal offset along d."""
    D = fib_dirs(n)
    D = D[(D[:, 2] < -0.05) if side == 'under' else (D[:, 2] > 0.05)]
    out = {}
    for nm, J in joint_pts.items():
        ok, best = [], (-1.0, None)
        for d in D:
            P = np.asarray(J, float) + 1.3 * d
            Ir = iron(P, d)
            gmin = SEARCH
            hit = False
            for k, O in obstacles.items():
                if not near(Ir, O, 1.0):
                    continue
                if (Ir ^ O).volume() > 1e-6:
                    hit = True
                    break
                gmin = min(gmin, float(Ir.min_gap(O, 1.0)))
            if not hit:
                ok.append(d)
                if gmin > best[0]:
                    best = (gmin, d)
        ok = np.array(ok)
        axis = np.array([0, 0, -1.0 if side == 'under' else 1.0])
        out[nm] = {'directionsTested': int(len(D)), 'directionsClear': int(len(ok)),
                   'fractionClear': round(len(ok) / max(1, len(D)), 3),
                   'maxTiltFromBoardNormalDeg': None if not len(ok) else round(float(np.degrees(np.arccos(np.clip(ok @ axis, -1, 1))).max()), 1),
                   'straightOnClear': bool(len(ok) and np.any(ok @ axis > 0.97)),
                   'bestDirection': None if best[1] is None else np.round(best[1], 3).tolist(),
                   'bestClearanceMm(capped 1.0)': None if best[1] is None else round(min(best[0], 1.0), 3)}
    return out


# ------------------------------------------------------------------------------------------------ facts and summary
SOURCES = [
    {'id': 'adafruit-brd', 'what': 'Adafruit MAX98357 breakout EAGLE board file "Adafruit MAX98357 Breakout.brd"',
     'url': 'https://github.com/adafruit/Adafruit-MAX98357-I2S-Amp-Breakout', 'revision': 'master, last commit c7cf21b4a8 2026-08-27',
     'local': str(BRD_LOCAL), 'checked': '2026-10-13'},
    {'id': 'yageo-mfr', 'what': 'YAGEO MFR series datasheet, Product specification April 3, 2024 V.4 (p3 dimensions, p4 soldering heat)',
     'url': 'https://yageogroup.com/content/Resource%20Library/Datasheet/YAGEO-MFR_DATASHEET.pdf',
     'local': str(YAGEO_LOCAL), 'checked': '2026-10-13'},
    {'id': 'sullins-11637', 'what': 'Sullins drawing 11637 rev F (03/16/2017), right-angle 0.100 in male header family M71RC',
     'url': 'https://drawings-pdf.s3.amazonaws.com/11637.pdf', 'local': str(SULLINS_LOCAL), 'checked': '2026-10-13',
     'use': 'reference only: the owner header is a right-angle header of unknown brand'},
    {'id': 'bench-procedure', 'what': 'Bench soldering procedure and drawings (underside placement, heat-shrink, Kapton)',
     'local': str(BENCH / 'README.md'), 'drawings': [str(BENCH / 'img' / 'underside.html'), str(BENCH / 'img' / 'endview.html')],
     'checked': '2026-10-13'},
    {'id': 'audio-study', 'what': 'Head audio study amplifier placement and solids', 'local': str(E.AUDIO / 'scripts' / 'build_study.py'),
     'checked': '2026-10-13'},
]
FACTS = {
    'verifiedFromPrimarySources': [
        'Board outline 17.78 x 19.05 mm; header JP1 pads on a line 2.54 mm from the header edge, pitch 2.54 mm, round pads '
        'diameter 1.9304 mm, drill 1.0 mm (adafruit-brd).',
        'Header pad nets: pad 1 VDD (Vin), 2 GND, 3 SD_MODE, 4 GAIN, 5 DIN, 6 BCLK, 7 LRCLK; silkscreen LRC BCLK DIN GAIN SD GND '
        'Vin. In the robot frame GAIN is at y 0, SD 2.54, GND 5.08, Vin 7.62 (adafruit-brd + audio-study mapping).',
        'Every SMD part is on the top copper layer; the underside carries only the header and terminal-block through-hole '
        'tails and the mounting-hole pads (adafruit-brd).',
        'R1 (1 MOhm, VDD to SD_MODE, 0805) sits at brd (13.716, 5.334) = world x 35.97, y 4.83, directly behind the SD/GND '
        'pins on the top side; U1 at world x 33.68, y 0 (adafruit-brd).',
        'YAGEO MFR-25 (normal size, the 1/4 W part in MFR-25FBF52-100K): L 6.3 +/- 0.5 mm, D 2.4 +/- 0.2 mm, lead '
        '0.55 +/- 0.05 mm, lead length 28 +/- 2.0 mm; no minimum bend distance given; resistance-to-soldering-heat test '
        'immersed to 3 +/- 0.5 mm from the body; -55 to +155 C (yageo-mfr p3-p4). "52" = 52.4 mm tape spacing.',
        'Sullins 11637 rev F, termination BA: tail 0.120 in (3.05 mm) from the insulator seating face, mating 0.230 in '
        '(5.84 mm), post 0.025 in (0.64 mm) square, insulator 2.54 mm high x 2.50 mm deep, tail centreline to insulator '
        'front face 0.158 in (4.02 mm) (sullins-11637; reference only).',
    ],
    'fromStudyOrBenchFilesNotReverified': [
        'Board thickness 1.57 mm and the amp position (board x 22.25..41.3, y +/-8.89, top z 139.8): audio-study constants.',
        'Resistor placement: body axis 3.0 mm inboard of the row and 2.45 mm below the PCB, heat-shrink 2.9 x 7.0 mm with '
        '1.0 mm to the PCB, legs bent 1.3 mm from the body (nominal L), legs 0.67 mm outboard of each tail, hooks 0.9 mm '
        'below the PCB, stack about 4 mm: measured from the bench drawings (endview 34 px/mm, underside 30 px/mm).',
    ],
    'inference': [
        'Tail length of the owner header: 1.5 mm nominal (bench README; Sullins-like 3.05 - 1.57 = 1.48 mm), 2.5 mm worst '
        'case (coordinator). Brand unknown.',
        'Header top side for the top fallback: pin centre 1.27 mm above the board, vertical segment 0.64 mm square, insulator '
        'front 4.02 mm ahead of the tail (Sullins geometry applied to an unknown header).',
        'SMD heights used: U1 0.8, R1 0.65, other 0805 parts 1.45 mm (conservative, unverified).',
        'Solder: header fillet cone pad diameter 1.93 mm to 0.9 mm over 0.6 mm; hook joint with Kapton radius 1.2 mm down to '
        'the tail tip + 0.3 mm, pad-wide at the board.',
        'Iron: generic fine conical tip (R0.5, cone to r 2.0 over 10 mm, r 2.0 to 20 mm, r 3.5 barrel to 80 mm).',
    ],
}
SIDE_NOTE = ('Outside the resistor scope. The audio study puts the header pin centreline 4.02 mm above the board (RA_PIN_Z); '
             'on Sullins 11637 0.158 in [4.02 mm] is the tail-to-insulator-front distance and the pin is drawn centred '
             'in the 2.54 mm insulator (about 1.27 mm high), as the bench end-view drawing also shows. hous_low = six '
             'housings at that lower height, 14 mm long from the insulator front face (Sullins-like header, inference).')


def summarize(results, acc):
    def worst(nm, swept):
        best = None
        for r in results[nm]['externalChecks']:
            vals = []
            if not swept:
                vals.append((r['staticGapMm'], r['staticOverlapMm3'], 'static'))
            else:
                for key in ('jawSweep', 'rollSweep', 'yawRollSweep'):
                    if key in r:
                        vals.append((r[key]['gapMm'], r[key]['overlapMm3'], key))
                if 'capDescent40' in r:
                    vals.append((r['capDescent40']['minGapAlongPathMm'], r['capDescent40']['sweptOverlapMm3'], 'capDescent40'))
            for g, ov, key in vals:
                score = -ov if ov > 1e-6 else (99.0 if g is None else g)
                if best is None or score < best[0]:
                    best = (score, {'with': r['with'], 'check': key, 'gapMm': g, 'overlapMm3': ov})
        return best[1] if best else None

    out = {}
    for nm in ('U4_box', 'U4_detail', 'U5_box', 'U5_detail', 'T_detail', 'tails_2p5'):
        ws, wd = worst(nm, False), worst(nm, True)
        ent = {'pass': results[nm]['verdict']['pass'], 'worstStatic': ws, 'worstSwept': wd}
        if ws and ws['gapMm'] is not None:
            ent['staticMarginMm'] = round(ws['gapMm'] - STATIC_MIN, 3)
        if wd and wd['gapMm'] is not None:
            ent['sweptMarginMm'] = round(wd['gapMm'] - SWEPT_MIN, 3)
        out[nm] = ent
    under_ok = out['U4_box']['pass'] and out['U4_detail']['pass']
    w4, w5 = out['U4_box']['worstSwept'], out['U5_box']['worstSwept']
    if w4 and w5 and w4['with'] == w5['with'] and w4['gapMm'] is not None and w5['gapMm'] is not None:
        slope = (w4['gapMm'] - w5['gapMm']) / (TAIL_LONG - TAIL_NOM)      # mm of gap lost per mm of extra depth
        out['depthLimit'] = {'limitingPart': w4['with'], 'check': w4['check'], 'gapLostPerMmDepth': round(slope, 3),
                             'maxStackDepthBelowPcbAtSweptMinMm': round(STACK_NOM + (w4['gapMm'] - SWEPT_MIN) / slope, 2),
                             'note': 'linear between the measured 4.0 and 5.0 mm boxes (inference beyond 5.0 mm)'}
    legs = results['U4_detail']['record']['legs']
    out['legPathBodyToJointMm'] = {}
    for nm, L in legs.items():
        p0, p1, p2 = (np.array(L[k]) for k in ('leavesBodyAt', 'bendAt', 'reachesRowAt'))
        out['legPathBodyToJointMm'][nm] = {'withMaxBodyLength': round(float(np.linalg.norm(p1 - p0) + np.linalg.norm(p2 - p1)), 2),
                                           'withNominalBodyLength': round(float(np.linalg.norm(p1 - p0) + (R_L_MAX - R_L_NOM) / 2
                                                                                + np.linalg.norm(p2 - p1)), 2),
                                           'bendFromBodyEndMaxL': L['bendDistanceFromBodyEndMm'],
                                           'bendFromBodyEndNominalL': round(L['bendDistanceFromBodyEndMm'] + (R_L_MAX - R_L_NOM) / 2, 2)}
    ins = [r for r in results['U4_detail']['ampInternal'] if r['envelopePart'] in ('body', 'legs', 'joints')
           and r['with'] in ('tail_SD', 'tail_GND', 'tail_DIN')]
    rec = {'recommended': 'underside, bench-drawing placement' if under_ok else ('top side' if out['T_detail']['pass'] else 'none'),
           'perCandidate': out,
           'insulationFromSdGndDin': ins,
           'placement': {'side': 'underside of the amplifier board', 'pins': 'GAIN tail (y 0) to Vin tail (y 7.62)',
                         'body': 'axis along the header row (world y), centred at y 3.81 between GAIN and Vin, 3.0 mm '
                                 'inboard of the row (world x 35.76, towards the terminal block) and 2.45 mm below the PCB '
                                 '(z 135.78)',
                         'insulation': 'lateral offset: the heat-shrunk body runs beside the SD and GND tails, not under '
                                       'them; clear heat-shrink over the body; legs reach GAIN and Vin from outside the '
                                       'pair, so no bare lead passes SD or GND; Kapton over the two joints'}}
    if acc:
        b = acc.get('underside_bench_amp_loose', {})
        m = acc.get('underside_amp_on_cap_upside_down', {})
        rec['fitting'] = {'bench': {k: v['fractionClear'] for k, v in b.items()},
                          'mountedOnCapUpsideDown': {k: v['fractionClear'] for k, v in m.items()},
                          'topsideMountedOnCap': {k: v['fractionClear'] for k, v in acc.get('topside_amp_on_cap', {}).items()}}
    return rec


# ------------------------------------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--cap', default=str(E.STUDY_CAP), help='head cap world STL (default: integrated study cap)')
    ap.add_argument('--json', default=str(OUT_JSON))
    ap.add_argument('--stl', default=str(OUT_STL))
    ap.add_argument('--no-access', action='store_true')
    args = ap.parse_args()
    t0 = time.time()
    S = load_scene(Path(args.cap))
    mot = Motion()
    # jaw transform sanity: part_T takes the jaw opening in degrees
    Tj = mot.rel({'jaw': 40.0}, 'jaw')
    jaw_check_deg = float(np.degrees(np.arccos(np.clip((np.trace(Tj[:3, :3]) - 1) / 2, -1, 1))))
    print('scene', len(S), 'parts', round(time.time() - t0, 1), 's; jaw 40 ->', round(jaw_check_deg, 3), 'deg', flush=True)

    amp_nom, amp_long = amp_parts(TAIL_NOM), amp_parts(TAIL_LONG)
    cands = {}
    p, parts, rec = underside_box(STACK_NOM, TAIL_NOM)
    cands['U4_box'] = dict(pieces=p, parts=parts, rec=rec, amp=amp_nom, kind='box')
    p, parts, rec = underside_detail(TAIL_NOM, 0.0)
    cands['U4_detail'] = dict(pieces=p, parts=parts, rec=rec, amp=amp_nom, kind='detail')
    p, parts, rec = underside_box(STACK_NOM + (TAIL_LONG - TAIL_NOM), TAIL_LONG)
    cands['U5_box'] = dict(pieces=p, parts=parts, rec=rec, amp=amp_long, kind='box')
    p, parts, rec = underside_detail(TAIL_LONG, TAIL_LONG - TAIL_NOM)
    cands['U5_detail'] = dict(pieces=p, parts=parts, rec=rec, amp=amp_long, kind='detail')
    p, parts, rec = topside_detail()
    cands['T_detail'] = dict(pieces=p, parts=parts, rec=rec, amp=amp_nom, kind='detail')

    results = {}
    joint_skip = ('tail_GAIN', 'tail_Vin', 'pinvert_GAIN', 'pinvert_Vin', 'pinrun_GAIN', 'pinrun_Vin', 'amp_board')
    for nm, c in cands.items():
        env = union(c['pieces'])
        c['env'] = env
        E.tm(env).export(SCR / f'env_{nm}.stl')
        rows, _ = check_envelope(nm, env, c['pieces'], S, mot, {}, ())
        # amp-internal: the box contains the row by construction, so only the detailed envelopes are checked inside
        amp_rows = []
        if c['kind'] == 'detail':
            for part_nm, M in c['parts'].items():
                for k, O in c['amp'].items():
                    if k in joint_skip and part_nm != 'body':
                        continue
                    ov, g = clearance(M, O)
                    if g is None and ov == 0:
                        continue
                    amp_rows.append({'envelopePart': part_nm, 'with': k, 'staticOverlapMm3': round(ov, 4),
                                     'staticGapMm': None if g is None else round(g, 3)})
        body_board = [r for r in amp_rows if r['envelopePart'] == 'body' and r['with'] == 'amp_board']
        v = verdict(rows, [{'with': f"{r['envelopePart']}->{r['with']}", 'staticOverlapMm3': r['staticOverlapMm3'],
                            'staticGapMm': r['staticGapMm']} for r in amp_rows])
        results[nm] = {'record': E.rnd(c['rec'], 3), 'bounds': E.rnd(bbox(env), 3), 'volumeMm3': round(env.volume(), 3),
                       'externalChecks': rows, 'ampInternal': amp_rows, 'verdict': v,
                       'bodyToBoardGapMm': body_board[0]['staticGapMm'] if body_board else None}
        print(nm, 'pass' if v['pass'] else 'FAIL', v['closest'][:3], v['failures'][:4], round(time.time() - t0, 1), 's', flush=True)

    # 2.5 mm tails of all seven header pins (amp-side change if the header has long tails)
    tails_long = union([amp_long[f'tail_{k}'] for k in PINS])
    rows, _ = check_envelope('tails_2p5', tails_long, [amp_long[f'tail_{k}'] for k in PINS], S, mot, {}, ())
    results['tails_2p5'] = {'record': {'description': 'all seven header tails 2.5 mm below the PCB with pad-wide fillets'},
                            'externalChecks': rows, 'verdict': verdict(rows, [])}
    print('tails_2p5', results['tails_2p5']['verdict']['closest'][:3], flush=True)

    # ---- soldering access
    acc = {}
    if not args.no_access:
        c = cands['U4_detail']
        jp = {nm: c['rec']['legs'][nm]['solderPoint'] for nm in ('GAIN', 'Vin')}
        body_only = {'resistor_body': c['parts']['body']}
        amp_obs = {k: O for k, O in amp_nom.items() if k not in ('tail_GAIN', 'tail_Vin', 'pinvert_GAIN', 'pinvert_Vin')}
        acc['underside_bench_amp_loose'] = access(jp, 'under', {**amp_obs, **body_only})
        mounted = {k: O for k, (O, ride, _) in S.items() if ride == 'cap' and not k.startswith('jumper_spk')}
        acc['underside_amp_on_cap_upside_down'] = access(jp, 'under', {**amp_obs, **body_only, **mounted})
        c = cands['T_detail']
        jp = {nm: c['rec']['legs'][nm]['solderPoint'] for nm in ('GAIN', 'Vin')}
        body_only = {'resistor_body': c['parts']['body']}
        acc['topside_bench_housings_off'] = access(jp, 'top', {**amp_obs, **body_only})
        acc['topside_amp_on_cap'] = access(jp, 'top', {**amp_obs, **body_only, 'head_cap': S['head_cap'][0],
                                                       'amp_housings': S['amp_housings'][0]})
        print('access', json.dumps(acc)[:600], round(time.time() - t0, 1), 's', flush=True)

    # ---- side finding: header pin height vs the A3 bundle (outside the resistor scope)
    side = {}
    zc = PCB_TOP + RA_PIN_H
    hx0 = ROW_X + RA_TAIL_TO_FRONT
    hous_low = union([boxm([hx0, y - 1.27, zc - 1.27], [hx0 + 14.0, y + 1.27, zc + 1.27]) for k, y in PINS.items() if k != 'SD'])
    for k in ('A3_group_in_head', 'A3_group_cap_held', 'A3_group_free'):
        ov, g = clearance(hous_low, S[k][0])
        side[k] = {'overlapMm3': round(ov, 3), 'gapMm': None if g is None else round(g, 3)}
    ov, g = clearance(S['amp_housings'][0], S['A3_group_in_head'][0])
    side['studyHousings_vs_A3_group_in_head'] = {'overlapMm3': round(ov, 3), 'gapMm': None if g is None else round(g, 3)}
    # how far the study housings can drop (pin lower than the study's 4.02 mm) before the A3 gap falls under 0.5 mm
    lo_, hi_ = 0.0, 4.02 - RA_PIN_H
    for _ in range(14):
        mid = (lo_ + hi_) / 2
        ov, g = clearance(S['amp_housings'][0].translate([0, 0, -mid]), S['A3_group_in_head'][0])
        if ov <= 1e-9 and (g is None or g >= STATIC_MIN):
            lo_ = mid
        else:
            hi_ = mid
    side['housingDropAllowedMm'] = round(lo_, 3)
    side['lowestPinCentreAboveBoardForA3Mm'] = round(4.02 - lo_, 3)

    # ---- export the coordinator's 4.0 mm stack envelope
    env = cands['U4_box']['env']
    E.tm(env).export(args.stl)
    mrep = E.mesh_report(args.stl)
    # scene meshes for the render
    E.tm(tails_long).export(SCR / 'tails_2p5.stl')
    E.tm(union([O for kk, O in amp_nom.items()])).export(SCR / 'amp_detail_nom.stl')
    E.jdump({'U4_box': results['U4_box']['externalChecks']}, SCR / 'rows_U4_box.json')

    # ---- recommendation
    rec = summarize(results, acc)

    inputs = {'cap': args.cap, 'buildStudy': str(E.AUDIO / 'scripts' / 'build_study.py'), 'wireRoutes': str(WIRE_ROUTES),
              'benchReadme': str(BENCH / 'README.md'), 'benchUnderside': str(BENCH / 'img' / 'underside.html'),
              'benchEndview': str(BENCH / 'img' / 'endview.html'), 'routeA3': str(E.STUDY_INT / 'route-A3.json'),
              'nrLib': str(E.NR / 'nr_lib.py'), 'mjcf': str(nr_lib.XML), 'iaManifest': str(Path(E.ia_lib.__file__))}
    for k, (_, _, src) in S.items():
        if src.startswith('/') and ':' not in src:
            inputs[k] = src
    inputs_sha = {k: {'path': v, 'sha256': E.sha(v)} for k, v in inputs.items() if Path(v).is_file()}
    for p_ in (BRD_LOCAL, YAGEO_LOCAL, SULLINS_LOCAL):
        if p_.is_file():
            inputs_sha[p_.name] = {'path': str(p_), 'sha256': E.sha(p_)}
    out = {
        'study': 'MicroDuck V1.9 GAIN resistor placement (MAX98357A breakout, 100 kOhm GAIN to Vin)',
        'problemIds': ['P5', 'P6'], 'date': '2026-10-13', 'frame': 'robot frame at q = 0, mm, x forward, y left, z up',
        'script': str(Path(__file__).resolve()), 'elapsedSeconds': round(time.time() - t0, 1),
        'thresholds': {'staticMinMm': STATIC_MIN, 'sweptMinMm': SWEPT_MIN, 'staticSearchMm': REPORT_SEARCH,
                       'sweptSearchMm': SEARCH, 'note': 'gap null = farther than the search length (static 40 mm, '
                       'sweeps and descent 12 mm)'},
        'jawTransformCheckDeg40': round(jaw_check_deg, 3),
        'motionRanges': {'headRollDeg': E.rnd(np.degrees(mot.roll), 2), 'headYawDeg': E.rnd(np.degrees(mot.yaw), 2),
                         'jawDeg': [0, 40], 'capDescentMm': 40},
        'candidates': results, 'solderAccess': acc, 'recommendation': rec,
        'envelopeStl': {'path': args.stl, 'is': 'U4_box (4.0 mm stack)', 'meshReport': mrep, 'sha256': mrep['sha256']},
        'sideFindingHeaderHeight': {**side, 'note': SIDE_NOTE}, 'facts': FACTS, 'sources': SOURCES, 'inputs': inputs_sha,
    }
    E.jdump(E.rnd(out, 4), SCR / 'raw-results.json')
    E.jdump(E.rnd(out, 4), args.json)
    print('done', round(time.time() - t0, 1), 's', flush=True)


if __name__ == '__main__':
    main()
