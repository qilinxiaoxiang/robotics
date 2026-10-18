#!/usr/bin/env python3
"""Shaded VTK views of the GAIN resistor placement (run after resistor_study.py).

png/resistor-placement.png      : oblique view from below the amplifier (underside envelope, tails, neighbours)
png/resistor-endview.png        : slab y -2..10 seen along +y (parallel), with the yaw link at its worst head-roll pose
Inputs: resistor-placement.json (worst poses and clearances) and the scratch meshes written by resistor_study.py.
"""
from __future__ import annotations

import argparse
import json
import sys

sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/guide/print/ext-v19/scripts')
import ext_lib as E  # noqa: E402

import manifold3d as m3  # noqa: E402
import numpy as np  # noqa: E402

import nr_lib  # noqa: E402
from vtk_render import render  # noqa: E402

ROWX = 41.3 - 2.54

SCR = E.SCRATCH / 'resistor'
PNG = E.OUT / 'png'


def crop(M, lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return M ^ m3.Manifold.cube((hi - lo).tolist()).translate(lo.tolist())


def tmesh(M):
    return E.tm(M) if not M.is_empty() else None


def find(rows, k):
    for r in rows:
        if r['with'] == k:
            return r
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--json', default=str(E.OUT / 'resistor-placement.json'))
    ap.add_argument('--cap', default=str(E.STUDY_CAP))
    a = ap.parse_args()
    J = json.loads(open(a.json).read())
    PNG.mkdir(exist_ok=True)
    rows = J['candidates']['U4_box']['externalChecks']
    fk = nr_lib.FK()
    yr = find(rows, 'head_yaw_link')['rollSweep']['rollDeg'] or 0.0
    T = fk.part_T({'head_roll': np.radians(yr)})
    Tyaw = np.linalg.inv(T['jaw_soft']) @ T['yaw_roll_motion']
    lo, hi = [14, -26, 118], [66, 26, 158]
    import resistor_study as RS
    AP = RS.amp_parts(RS.TAIL_NOM)
    under = RS.union([M for k, M in AP.items() if k == 'amp_board' or k.startswith('tail_') or k.startswith('tb_tail')])
    # top side as the audio study models it (lumped header block, housings at its 4.02 mm pin height)
    top = crop(E.stl_man(E.AUDIO / 'study-solids' / 'amplifier-world.stl'), [0, -30, RS.PCB_TOP], [80, 30, 170])
    amp = under + top
    cap = crop(E.stl_man(a.cap), lo, hi)
    box = E.stl_man(E.OUT / 'resistor_envelope_v19-world.stl')
    det = E.stl_man(SCR / 'env_U4_detail.stl')
    hous = E.stl_man(E.AUDIO / 'study-solids' / 'amp_housings-world.stl')
    scr = E.stl_man(E.AUDIO / 'study-solids' / 'amp_screws_envelope-world.stl')
    a3 = crop(E.stl_man(E.STUDY_INT / 'study-solids' / 'A3_group_in_head-world.stl'), lo, hi)
    yaw = crop(E.load_man('head_yaw_link').transform(Tyaw[:3, :]), lo, hi)
    ring = crop(E.load_man('head_roll_ring_b').transform(Tyaw[:3, :]), lo, hi)
    js = crop(E.load_man('jaw_support'), lo, hi)
    pi = crop(E.load_man('pi'), lo, hi)
    m15 = crop(E.load_man('motor15'), lo, hi)
    g = {r['with']: r for r in rows}

    def gap_txt(k, key=None):
        r = g[k]
        v = r[key]['gapMm'] if key else r['staticGapMm']
        return '>40' if v is None else f'{v:.2f}'
    det_rec = J['candidates']['U4_detail']['record']
    bc = np.array(det_rec['bodyCentre'])
    # 1. oblique view from below, local crop
    llo, lhi = [24, -14, 126], [54, 16, 147]
    items = [(tmesh(crop(cap, llo, lhi)), (0.75, 0.75, 0.78), 0.25), (tmesh(amp), (0.15, 0.35, 0.7), 1.0),
             (tmesh(hous), (0.12, 0.12, 0.12), 1.0), (tmesh(scr), (0.6, 0.6, 0.6), 1.0),
             (tmesh(box), (0.95, 0.55, 0.1), 0.35), (tmesh(det), (0.55, 0.78, 0.92), 1.0),
             (tmesh(crop(a3, llo, lhi)), (0.2, 0.65, 0.3), 0.85), (tmesh(crop(yaw, llo, lhi)), (0.6, 0.2, 0.2), 0.8),
             (tmesh(crop(ring, llo, lhi)), (0.6, 0.3, 0.3), 0.8), (tmesh(crop(js, llo, lhi)), (0.85, 0.82, 0.6), 0.45)]
    labels = [((bc[0] - 2, bc[1] - 7, bc[2] - 1.5), 'resistor: 4.0 mm stack (orange), body + legs (blue)', (0.75, 0.35, 0.0)),
              ((39.5, -1.6, 136.4), 'GAIN', (0.4, 0.1, 0.6)), ((39.5, 9.6, 136.4), 'Vin', (0.7, 0.1, 0.1)),
              ((32, -12, 128.5), f'head_yaw_link at roll {yr:.0f} deg: {gap_txt("head_yaw_link", "rollSweep")} mm', (0.55, 0.1, 0.1)),
              ((32, 12, 127.5), f'jaw_support {gap_txt("jaw_support")} mm', (0.45, 0.4, 0.1)),
              ((49.5, -9, 139.5), f'A3 bundle {gap_txt("A3_group_in_head")} mm', (0.1, 0.45, 0.15)),
              ((48, 9, 146.5), f'amp housings {gap_txt("amp_housings")} mm', (0.1, 0.1, 0.1)),
              ((24.8, -10, 136.0), f'amp screw heads {gap_txt("amp_screws_envelope")} mm', (0.3, 0.3, 0.3))]
    render(items, PNG / 'resistor-placement.png', cam=((60, -48, 108), (37, 3, 136), (0, 0, 1)), size=(1400, 1050),
           title=f'Underside GAIN resistor; yaw link at worst roll {yr:.0f} deg', labels=labels + [
               ((27, -13, 123.5), f'Pi {gap_txt("pi")} mm, camera {gap_txt("camera_board")} mm, jumpers '
                               f'{gap_txt("jumper_amp_vin_pin04")} mm', (0.1, 0.4, 0.1))])
    # 2. end view: slab along the resistor, parallel projection along +y
    slo, shi = [14, -2.0, 118], [66, 10.0, 158]
    sl = [(crop(M, slo, shi), c, o) for M, c, o in [(cap, (0.75, 0.75, 0.78), 0.35), (amp, (0.15, 0.35, 0.7), 1.0),
                                                    (hous, (0.12, 0.12, 0.12), 1.0), (box, (0.95, 0.55, 0.1), 0.45),
                                                    (det, (0.55, 0.78, 0.92), 1.0), (a3, (0.2, 0.65, 0.3), 1.0),
                                                    (yaw, (0.6, 0.2, 0.2), 1.0), (ring, (0.6, 0.3, 0.3), 1.0),
                                                    (js, (0.85, 0.82, 0.6), 1.0), (pi, (0.25, 0.55, 0.25), 1.0),
                                                    (m15, (0.3, 0.3, 0.35), 1.0)]]
    items2 = [(tmesh(M), c, o) for M, c, o in sl]
    d4 = J['candidates']['U4_box']['record']['depthBelowPcbMm']
    labels2 = [((36.9, -30, 133.0), f'resistor stack {d4:.1f} mm below PCB', (0.75, 0.35, 0.0)),
               ((30, -30, 126.0), f'yaw link + roll ring at worst roll {yr:.0f} deg', (0.55, 0.1, 0.1)),
               ((49.5, -30, 136.0), 'A3 bundle', (0.1, 0.45, 0.15)), ((57, -30, 130), 'Pi', (0.1, 0.4, 0.1)),
               ((27, -30, 141.5), 'amp board', (0.1, 0.25, 0.6)),
               ((49, -30, 146.6), 'housings (audio-study height)', (0.1, 0.1, 0.1)), ((22, -30, 150.5), 'cap roof', (0.4, 0.4, 0.45))]
    render(items2, PNG / 'resistor-endview.png', cam=((40, -200, 137), (40, 0, 137), (0, 0, 1)), size=(1400, 900),
           parallel_scale=17, title='Slab y -2..10 seen along +y (x forward to the right): underside stack and what is below it',
           labels=labels2)
    # 3. plan view from below (looking up +z), the layout of the bench drawing in the robot frame
    plo, phi = [26, -11, 128], [46, 11, 139.9]
    items3 = [(tmesh(crop(under, plo, phi)), (0.15, 0.35, 0.7), 1.0), (tmesh(scr), (0.6, 0.6, 0.6), 1.0),
              (tmesh(box), (0.95, 0.55, 0.1), 0.3), (tmesh(det), (0.55, 0.78, 0.92), 1.0)]
    labels3 = [((ROWX + 1.6, y, 130), nm, (0.7, 0.1, 0.1) if nm == 'Vin' else ((0.4, 0.1, 0.6) if nm == 'GAIN' else (0.2, 0.2, 0.2)))
               for nm, y in RS.PINS.items()]
    labels3 += [((bc[0] - 2.6, bc[1], 130), '3.0 mm inboard of row', (0.75, 0.35, 0.0)),
                ((42.2, 3.8, 130), 'board edge, header', (0.1, 0.25, 0.6)),
                ((25.8, 0.0, 130), 'terminal-block tails', (0.3, 0.3, 0.3))]
    render(items3, PNG / 'resistor-underside-plan.png', cam=((36, 0, 60), (36, 0, 138), (1, 0, 0)), size=(1100, 1100),
           parallel_scale=11.5, title='Underside seen from below (x forward = up, +y to the right; Vin at +y): box 10.0 x 6.2 mm, body 3.0 mm inboard',
           labels=labels3)
    print('rendered')


if __name__ == '__main__':
    main()
