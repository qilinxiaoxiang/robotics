#!/usr/bin/env python3
"""Step 4c: check the proposed fixes for approaches that have no clean straight path in the current step order.

Each scenario moves a set of parts (one union solid) along a piecewise-straight path of offsets from the
final pose (the last offset is [0, 0, 0]) through the parts that are physically present: the installed state
before a step (steps_audit.physical_state), with listed parts removed or added, and optionally with listed
parts rotated about an axis (the jaw opened about its sliding-ring axis). Each leg is sampled at 41 positions
and intersected exactly (manifold3d). A collision is excess over the final-pose overlap > 0.5 mm^3 with local
thickness > 0.1 mm, as in steps_audit.py. With 'search', 32 straight directions (9 samples) are also screened.
Writes whatif.json.
"""
from __future__ import annotations

import json
import sys

import manifold3d as m3d
import numpy as np

from approach_search import fib
from ia_lib import HERE, from_manifold, load_guide, manifest, rnd
from pairs import local_thickness
from steps_audit import Solids, physical_state, resolve

JAW_AXIS_POINT = [26.1, 0.0, 118.62]   # mouth_sliding_ring centre (x, z); ring axis is +y (PCA, see README)
JAW_MOVING = ['jaw_frame', 'lower_pad']  # the jaw frame and the moving lower pad turn; support, ring and ID15 body stay

GPIO = None  # filled from the guide (head_pi_gpio_pin_*_receiving)


def rot_y(deg, p):
    t = np.radians(deg)
    R = np.array([[np.cos(t), 0, np.sin(t)], [0, 1, 0], [-np.sin(t), 0, np.cos(t)]])
    p = np.asarray(p, float)
    return np.c_[R, p - R @ p]  # 3x4 affine: x' = R (x - p) + p


SCEN = [
    # id, step whose installed state is the base, movers, path offsets, remove, add, rotate {deg, parts}, search
    ('tray-two-stage', 'tray', ['openrb_tray'], [[-30, 0, 4], [0, 0, 4], [0, 0, 0]], [], [], None, False),
    ('tray-two-stage-lift3', 'tray', ['openrb_tray'], [[-30, 0, 3], [0, 0, 3], [0, 0, 0]], [], [], None, False),
    ('speaker-cage-down', 'speaker', ['speaker_cradle', 'speaker', 'speaker_keeper', 'speaker_mount_screw_1', 'speaker_mount_screw_2'],
     [[0, 0, -20], [0, 0, 0]], [], [], None, True),
    ('head-bottom-before-jaw-from-below', 'head-bottom', ['head_bottom'], [[0, 0, -30], [0, 0, 0]],
     ['jaw_support', 'mouth_sliding_ring', 'jaw_frame', 'lower_pad', 'motor15'], [], None, True),
    ('jaw-group-after-head-bottom', 'jaw', ['jaw_support', 'mouth_sliding_ring', 'jaw_frame', 'lower_pad', 'motor15'],
     [[0, 0, 30], [0, 0, 0]], [], ['head_bottom'], None, True),
    ('upper-pad-into-head-bottom-before-jaw', 'jaw', ['upper_pad'], [[0, 0, 30], [0, 0, 0]], [], ['head_bottom'], None, True),
    ('jaw-group-after-head-bottom-and-upper-pad', 'jaw', ['jaw_support', 'mouth_sliding_ring', 'jaw_frame', 'lower_pad', 'motor15'],
     [[0, 0, 30], [0, 0, 0]], [], ['head_bottom', 'upper_pad'], None, True),
    ('head-bottom-jaw-open-30', 'head-bottom', ['head_bottom'], [[0, 0, -30], [0, 0, 0]], [], [], {'deg': 30, 'parts': JAW_MOVING}, False),
    ('upper-pad-jaw-open-30-front', 'close', ['upper_pad'], [[30, 0, 0], [0, 0, 0]], [], [], {'deg': 30, 'parts': JAW_MOVING}, False),
    ('upper-pad-jaw-open-30-below', 'close', ['upper_pad'], [[0, 0, -15], [0, 0, 0]], [], [], {'deg': 30, 'parts': JAW_MOVING}, False),
    ('cap-on-without-gpio', 'cap-on', '__cap_no_gpio__', [[0, 0, 40], [0, 0, 0]], [], [], None, True),
    ('gpio-after-cap-along-pins', 'cap-on', '__gpio__', [[19.6, 0, -3.4], [0, 0, 0]], [], ['__cap_no_gpio__'], None, True),
    ('cap-on-face-absent', 'cap-on', '__cap_all__', [[0, 0, 40], [0, 0, 0]], ['face_panel', 'eye_trim', 'camera_board', 'camera_retainer',
     'camera_clamp_screw_1', 'camera_clamp_screw_2', 'camera_clamp_screw_3'], [], None, False),
    ('close-upper-pad-short', 'close', ['upper_pad'], [[3, 0, 0], [0, 0, 0]], [], [], None, False),
    # torso base sandwiched between the hip-yaw motors (above) and the yaw brackets on their horns (below)
    ('torso-rings-before-base-motors-off', 'torso-base', ['ring10_torso', 'ring5_torso'], [[0, 0, 28], [0, 0, 0]],
     ['motor10', 'motor5'], [], None, False),
    ('torso-base-from-above-motors-off', 'torso-base', ['torso_base'], [[0, 0, 28], [0, 0, 0]],
     ['motor10', 'motor5'], ['ring10_torso', 'ring5_torso'], None, True),
    ('hip-yaw-motors-onto-base', 'torso-base', ['motor10', 'motor5'], [[0, 0, 28], [0, 0, 0]],
     ['motor10', 'motor5'], ['ring10_torso', 'ring5_torso', 'torso_base'], None, False),
    ('power-support-after-base', 'torso-base', ['power_support'], [[-28, 0, 0], [0, 0, 0]],
     [], ['ring10_torso', 'ring5_torso', 'torso_base'], None, False),
    # proposed straight vectors re-checked against everything physically present, co-added predecessors included
    ('converter-insert-from-rear', 'converter', ['regulator_insert'], [[-40, 0, 0], [0, 0, 0]], [], [], None, False),
    ('converter-regulator-from-rear', 'converter', ['regulator'], [[-48, 0, 0], [0, 0, 0]], [], ['regulator_insert'], None, False),
    ('xt30-with-converter', 'converter', ['xt30_robot'], [[-20, 0, 0], [0, 0, 0]], [], ['regulator_insert', 'regulator'], None, False),
    ('board-short-slide', 'board', ['openrb_board'], [[-15, 0, 0], [0, 0, 0]], [], [], None, False),
    ('imu-plug-sideways', 'imu-board', ['imu_sh4_receiving'], [[0, 14.4, 0], [0, 0, 0]], [], ['imu_board'], None, False),
    ('imu-board-from-rear', 'imu-board', ['imu_board'], [[-24, 0, 0], [0, 0, 0]], [], [], None, False),
    ('jaw-as-group-from-above', 'jaw', ['jaw_support', 'mouth_sliding_ring', 'jaw_frame', 'lower_pad', 'motor15'],
     [[0, 0, 30], [0, 0, 0]], [], [], None, False),
    ('face-from-above', 'face', ['face_panel'], [[0, 0, 40], [0, 0, 0]], [], [], None, False),
    # bench: ID15 into the jaw support before the support goes on the head (search screens 32 straight directions)
    ('motor15-into-support-bench', 'cap', ['motor15'], [[0, 30, 0], [0, 0, 0]], [], ['jaw_support'], None, True),
    ('motor15-into-support-bench-from-above', 'cap', ['motor15'], [[0, 0, 30], [0, 0, 0]], [], ['jaw_support'], None, False),
    # camera fitted to the face on the bench (no stubby driver needed), then face, trim and camera lowered as one unit
    ('face-camera-group-from-above', 'face', ['face_panel', 'eye_trim', 'camera_board', 'camera_retainer', 'camera_clamp_screw_1',
     'camera_clamp_screw_2', 'camera_clamp_screw_3'], [[0, 0, 40], [0, 0, 0]], [], [], None, False),
    ('eye-trim-after-face', 'face', ['eye_trim'], [[50, 0, 0], [0, 0, 0]], [], ['face_panel'], None, False),
    ('camera-board-from-rear', 'camera', ['camera_board'], [[-20, 0, 0], [0, 0, 0]], [], [], None, False),
    ('camera-retainer-short', 'camera', ['camera_retainer'], [[-22.5, 0, 0], [0, 0, 0]], [], ['camera_board'], None, False),
    ('camera-screws-from-front', 'camera', ['camera_clamp_screw_1', 'camera_clamp_screw_2', 'camera_clamp_screw_3'],
     [[10, 0, 0], [0, 0, 0]], [], ['camera_board', 'camera_retainer'], None, False),
    ('converter-group-from-rear', 'converter', ['regulator_insert', 'regulator'], [[-40, 0, 0], [0, 0, 0]], [], [], None, False),
    ('camera-screws-from-rear', 'camera', ['camera_clamp_screw_1', 'camera_clamp_screw_2', 'camera_clamp_screw_3'],
     [[-10, 0, 0], [0, 0, 0]], [], ['camera_board', 'camera_retainer'], None, False),
    ('face-camera-unit-after-cap', 'close', ['face_panel', 'eye_trim', 'camera_board', 'camera_retainer', 'camera_clamp_screw_1',
     'camera_clamp_screw_2', 'camera_clamp_screw_3'], [[40, 0, 0], [0, 0, 0]], [], [], None, True),
    ('jaw-support-after-head-bottom', 'jaw', ['jaw_support', 'mouth_sliding_ring', 'motor15'], [[0, 0, 30], [0, 0, 0]], [], ['head_bottom'], None, True),
    ('moving-jaw-after-shell-and-support', 'jaw', ['jaw_frame', 'lower_pad'], [[0, 0, -30], [0, 0, 0]], [],
     ['head_bottom', 'jaw_support', 'mouth_sliding_ring', 'motor15'], None, True),
    ('moving-jaw-swing-in-after-shell', 'jaw', ['jaw_frame', 'lower_pad'], {'swing': [45, 0]}, [],
     ['head_bottom', 'jaw_support', 'mouth_sliding_ring', 'motor15'], None, False),
    ('upper-pad-swing-check-jaw-closed-on-pad', 'close', ['jaw_frame', 'lower_pad'], {'swing': [30, 0]}, [], ['upper_pad'], None, False),
    ('cap-on-dogleg-back3', 'cap-on', '__cap_all__', [[-3, 0, 40], [-3, 0, 0], [0, 0, 0]], [], [], None, False),
    ('cap-on-dogleg-back5', 'cap-on', '__cap_all__', [[-5, 0, 40], [-5, 0, 0], [0, 0, 0]], [], [], None, False),
    ('cap-on-dogleg-back5-high', 'cap-on', '__cap_all__', [[-5, 0, 40], [-5, 0, 3], [0, 0, 3], [0, 0, 0]], [], [], None, False),
    # original one-piece jaw kept (2026-10-08 decision): orders that avoid the rigid shell-over-closed-jaw failure.
    # Remaining contact is the jaw ears passing the shell; that is the elastic insertion left to the physical check.
    ('jaw-seat-in-shell-on-robot', 'jaw', ['jaw_frame', 'mouth_sliding_ring', 'lower_pad'], [[0, 0, -30], [0, 0, 0]],
     ['jaw_support', 'motor15'], ['head_bottom'], None, True),
    ('shell-and-jaw-group-from-below', 'head-bottom', ['head_bottom', 'jaw_frame', 'mouth_sliding_ring', 'lower_pad'],
     [[0, 0, -30], [0, 0, 0]], ['jaw_support', 'motor15'], [], None, True),
    ('support-motor15-from-above-after-shell-jaw', 'jaw', ['jaw_support', 'motor15'], [[0, 0, 30], [0, 0, 0]], [],
     ['head_bottom', 'jaw_frame', 'mouth_sliding_ring', 'lower_pad'], None, True),
    ('jaw-frame-ring-swing30-shell-only', 'jaw', ['jaw_frame', 'lower_pad', 'mouth_sliding_ring'], {'swing': [30, 0]},
     ['jaw_support', 'motor15'], ['head_bottom'], None, False),
    # bench: the jaw (frame, ring on its boss, lower pad) opened about its axis and slid into the loose shell from the front
    ('bench-jaw-into-shell-open30-front', 'cap', ['jaw_frame', 'mouth_sliding_ring', 'lower_pad'], [[30, 0, 0], [0, 0, 0]],
     [], ['head_bottom'], None, True, {'moverRotDeg': 30}),
    ('bench-jaw-into-shell-open45-front', 'cap', ['jaw_frame', 'mouth_sliding_ring', 'lower_pad'], [[30, 0, 0], [0, 0, 0]],
     [], ['head_bottom'], None, True, {'moverRotDeg': 45}),
    ('bench-jaw-into-shell-open30-front-below', 'cap', ['jaw_frame', 'mouth_sliding_ring', 'lower_pad'], [[25, 0, -15], [0, 0, 0]],
     [], ['head_bottom'], None, False, {'moverRotDeg': 30}),
    # bench, from above: the shell is open on top until the cap goes on
    ('bench-jaw-from-above-closed', 'cap', ['jaw_frame', 'mouth_sliding_ring', 'lower_pad'], [[0, 0, 30], [0, 0, 0]],
     [], ['head_bottom'], None, True, {'moverRotDeg': 0}),
    ('bench-jaw-from-above-open30', 'cap', ['jaw_frame', 'mouth_sliding_ring', 'lower_pad'], [[0, 0, 30], [0, 0, 0]],
     [], ['head_bottom'], None, True, {'moverRotDeg': 30}),
    ('bench-jaw-front-then-down-open30', 'cap', ['jaw_frame', 'mouth_sliding_ring', 'lower_pad'], [[30, 0, 12], [0, 0, 12], [0, 0, 0]],
     [], ['head_bottom'], None, False, {'moverRotDeg': 30}),
    # bench, ring and pad after the jaw: the ring's 2 mm clash with its seat comes only at the end of the front slide
    ('bench-jaw-no-ring-front-open30', 'cap', ['jaw_frame', 'lower_pad'], [[30, 0, 0], [0, 0, 0]],
     [], ['head_bottom'], None, False, {'moverRotDeg': 30}),
    ('bench-jawframe-only-front-open30', 'cap', ['jaw_frame'], [[30, 0, 0], [0, 0, 0]],
     [], ['head_bottom'], None, False, {'moverRotDeg': 30}),
    ('bench-ring-onto-seated-jaw-from-inside', 'cap', ['mouth_sliding_ring'], [[0, 12, 0], [0, 0, 0]],
     [], ['head_bottom', 'jaw_frame', 'lower_pad'], None, False),
    ('bench-pad-onto-seated-jaw-from-above', 'cap', ['lower_pad'], [[0, 0, 15], [0, 0, 0]],
     [], ['head_bottom', 'jaw_frame', 'mouth_sliding_ring'], None, True),
    ('bench-jaw-swing30-shell-only', 'cap', ['jaw_frame', 'mouth_sliding_ring', 'lower_pad'], {'swing': [30, 0]},
     [], ['head_bottom'], None, False),
    # torso on built legs: each hip is opened (leg guide steps 13-20 reversed), the torso is built on the yaw links,
    # ID9/ID4 go back in, then each leg slides back onto its hip-roll output (leg guide approach reversed)
    ('left-leg-onto-roll-output', 'torso-fasten', ['thigh', 'plate', 'lower', 'ankle', 'foot', 'hip', 'ring7', 'ring8', 'ring9',
     'smallring', 'motor6', 'motor7', 'motor8', 'washer6'], [[45, 0, 0], [0, 0, 0]], [], [], None, False),
    ('right-leg-onto-roll-output', 'torso-fasten', ['right_thigh', 'right_plate', 'right_lower', 'right_ankle', 'right_foot', 'right_hip',
     'ring2', 'ring3', 'ring4', 'right_smallring', 'motor1', 'motor2', 'motor3', 'washer1'], [[45, 0, 0], [0, 0, 0]], [], [], None, False),
    ('hip-roll-motors-back-before-power-support', 'torso-base', ['motor9', 'passive', 'washer9', 'motor4', 'right_passive', 'washer4'],
     [[45, 0, 0], [0, 0, 0]], ['power_support', 'thigh', 'plate', 'lower', 'ankle', 'foot', 'hip', 'ring7', 'ring8', 'ring9', 'smallring',
     'motor6', 'motor7', 'motor8', 'washer6', 'right_thigh', 'right_plate', 'right_lower', 'right_ankle', 'right_foot', 'right_hip', 'ring2',
     'ring3', 'ring4', 'right_smallring', 'motor1', 'motor2', 'motor3', 'washer1'], ['torso_base', 'ring10_torso', 'ring5_torso'], None, False),
    ('amp-down', 'amp', ['amplifier'], [[0, 0, -20], [0, 0, 0]], [], [], None, False),
    ('pi-group-down', 'pi', '__pi__', [[0, 0, -25], [0, 0, 0]], [], [], None, False),
    ('gpio-on-bench', 'gpio', '__gpio__', [[19.6, 0, -3.4], [0, 0, 0]], [], ['__pi__'], None, False),
    # candidate cap change: the Pi (with header and plugged housing) sits further back on the cap rails, so the housing
    # passes behind the camera stack while the cap is lowered. 9th field: shift these movers relative to the rest.
    ('cap-on-pi-back-4.6', 'cap-on', '__cap_all__', [[0, 0, 40], [0, 0, 0]], [], [], None, False, {'by': [-4.6, 0, 0], 'parts': '__pi_gpio__'}),
    ('cap-on-pi-back-5.5', 'cap-on', '__cap_all__', [[0, 0, 40], [0, 0, 0]], [], [], None, False, {'by': [-5.5, 0, 0], 'parts': '__pi_gpio__'}),
]


def main():
    g = load_guide()
    man = manifest()
    steps, mods = resolve(g)
    phys = physical_state(steps, mods)
    by = {s['id']: s for s in steps}
    S = Solids(cap=60)
    only = set(sys.argv[1:])
    cap_all = by['cap-on']['add']
    gpio = [k for k in cap_all if k.startswith('head_pi_gpio_pin_')]
    groups = {'__cap_all__': cap_all, '__gpio__': gpio, '__cap_no_gpio__': [k for k in cap_all if k not in gpio],
              '__pi__': by['pi']['add']}
    out = []
    groups['__pi_gpio__'] = groups['__pi__'] + gpio
    for sid_, base, movers, path, remove, add, rot, search, *extra in SCEN:
        if only and sid_ not in only:
            continue
        shift = extra[0] if extra else None
        mover_rot = shift.get('moverRotDeg') if shift else None   # movers start opened about the jaw axis
        if mover_rot is not None:
            shift = None
        mv = groups.get(movers, movers) if isinstance(movers, str) else movers
        present = set(phys[base]['installedBefore'])
        if phys[base]['bench']:
            present = set(phys[base]['bench'][1]) - set(by[base]['add'])
        for a in add:
            present |= set(groups.get(a, [a]))
        present -= set(remove) | set(mv)
        present = [k for k in present if k in man]
        shifted = set(groups.get(shift['parts'], shift['parts'])) & set(mv) if shift else set()
        dv = np.array(shift['by'], float) if shift else np.zeros(3)
        sol = {k: (S.get(k).translate(list(dv)) if k in shifted else S.get(k)) for k in mv}
        M = m3d.Manifold.batch_boolean(list(sol.values()), m3d.OpType.Add)
        if mover_rot is not None:
            M = M.transform(rot_y(mover_rot, JAW_AXIS_POINT))
        mb = np.array([np.min([np.array(man[k]['bounds'][0]) + (dv if k in shifted else 0) for k in mv], 0),
                       np.max([np.array(man[k]['bounds'][1]) + (dv if k in shifted else 0) for k in mv], 0)])
        if mover_rot is not None:
            mb = np.array(M.bounding_box()).reshape(2, 3)
        obst = {}
        for k in present:
            O = S.get(k)
            if rot and k in rot['parts']:
                O = O.transform(rot_y(rot['deg'], JAW_AXIS_POINT))
            obst[k] = O

        def place(off):
            # a 'swing' path entry is ('swing', degrees): rotate the movers about the jaw axis instead of translating
            if isinstance(off, tuple):
                return M.transform(rot_y(off[1], JAW_AXIS_POINT))
            return M.translate(list(off))

        def run(path_, n=41):
            if isinstance(path_, dict):  # {'swing': [deg_start, deg_end]}
                a0, a1 = path_['swing']
                poses = [('swing', float(d)) for d in np.linspace(a0, a1, n)]
                lo, hi = mb[0] - 40, mb[1] + 40
            else:
                pts = np.asarray(path_, float)
                lo = np.minimum(mb[0], mb[0] + pts.min(0)) - 0.2
                hi = np.maximum(mb[1], mb[1] + pts.max(0)) + 0.2
                poses = [a + (b - a) * s for a, b in zip(pts[:-1], pts[1:]) for s in np.linspace(0, 1, n)]
            res = {}
            for k, O in obst.items():
                ob = np.array(O.bounding_box()).reshape(2, 3)
                if np.any(ob[0] > hi) or np.any(ob[1] < lo):
                    continue
                fin = (M ^ O).volume()
                worst = (0.0, None)
                for off in poses:
                    ex = (place(off) ^ O).volume() - fin
                    if ex > worst[0]:
                        worst = (ex, off)
                if worst[0] > 0.5:
                    v, f = from_manifold(place(worst[1]) ^ O)
                    th = local_thickness(v, f, n=200)[0] if len(f) else 0
                    if th > 0.1:
                        at = {'swingDeg': rnd(worst[1][1], 1)} if isinstance(worst[1], tuple) else rnd(worst[1], 2)
                        res[k] = {'excessMm3': rnd(worst[0], 2), 'atOffset': at, 'thicknessMm': rnd(th, 3),
                                  'centroid': rnd(v.mean(0), 1)}
            return res
        hits = run(path)
        rec = {'scenario': sid_, 'baseStep': base, 'movers': movers if isinstance(movers, str) else mv, 'path': path,
               'removed': remove, 'added': add, 'rotated': rot, 'clean': not hits, 'collisions': hits}
        if shift:
            # final-pose overlap of the shifted parts with everything else (other movers and present parts), against the unshifted pose
            Sh = m3d.Manifold.batch_boolean([sol[k] for k in shifted], m3d.OpType.Add)
            Sh0 = m3d.Manifold.batch_boolean([S.get(k) for k in shifted], m3d.OpType.Add)
            others = {k: S.get(k) for k in mv if k not in shifted}
            others.update(obst)
            fo = {}
            for k, O in others.items():
                v1, v0 = (Sh ^ O).volume(), (Sh0 ^ O).volume()
                if v1 > 0.01 or v0 > 0.01:
                    fo[k] = {'shiftedMm3': rnd(v1, 2), 'originalMm3': rnd(v0, 2)}
            rec['shift'] = {'by': shift['by'], 'parts': sorted(shifted), 'finalOverlap': fo}
        if search and not isinstance(path, dict):
            L = float(np.linalg.norm(path[0]))
            cand = []
            for d in fib(32):
                h = run([list(d * L), [0, 0, 0]], n=9)
                cand.append({'vector': rnd(d * L, 1), 'excessMm3': rnd(sum(x['excessMm3'] for x in h.values()), 2), 'obstacles': sorted(h)})
            cand.sort(key=lambda c: c['excessMm3'])
            rec['cleanStraightDirections'] = sum(c['excessMm3'] == 0 for c in cand)
            rec['bestStraight'] = cand[:3]
        out.append(rec)
        print(sid_, 'clean' if not hits else {k: v['excessMm3'] for k, v in hits.items()}, rec.get('cleanStraightDirections', ''), file=sys.stderr, flush=True)
        p = HERE / 'whatif.json'
        prev = json.loads(p.read_text()) if p.exists() else []
        p.write_text(json.dumps([r for r in prev if r['scenario'] != sid_] + [rec], indent=1))


if __name__ == '__main__':
    main()
