#!/usr/bin/env python3
"""Exploration renders of the clip sites (scratch only). Usage: explore_render.py"""
import numpy as np
import trimesh

import ext_lib as E
from vtk_render import render

F = E.fasteners()


def part(k):
    v, f = E.ia_lib.load_solid(k)
    return trimesh.Trimesh(v, f, process=False)


def screws_near(c, r=25):
    out = []
    for sid, s in F.items():
        if s.get('center') is None:
            continue
        if np.linalg.norm(np.array(s['center']) - c) < r:
            out.append(E.tm(E.screw_solid(s['center'], s['axis'], s['lengthMm'], d=s['diameterMm'],
                                          head_d=s['headDiameterMm'], head_h=s['headHeightMm'])))
    return out


def crop(m, c, r):
    cen = m.triangles_center
    keep = np.all(np.abs(cen - c) < r, axis=1)
    mm = m.copy()
    mm.update_faces(keep)
    mm.remove_unreferenced_vertices()
    return mm


def main():
    import json
    route = np.array(json.loads((E.STUDY_INT / 'route-A3.json').read_text())['groupPolyline'], float)
    cols = {'shell_right': (0.95, 0.95, 0.9), 'idler12': (0.6, 0.8, 0.6), 'idler_cap12': (0.5, 0.7, 0.9), 'motor12': (0.3, 0.3, 0.3),
            'motor11': (0.3, 0.3, 0.3), 'neck_pitch': (0.9, 0.85, 0.6), 'idler11': (0.6, 0.8, 0.6), 'idler_cap11': (0.5, 0.7, 0.9),
            'neck_link_a': (0.8, 0.6, 0.6), 'neck_link_b': (0.8, 0.6, 0.6), 'motor13': (0.3, 0.3, 0.3), 'head_bottom': (1.0, 0.9, 0.3),
            'neck_pitch_ring': (0.2, 0.2, 0.2), 'motor5': (0.3, 0.3, 0.3), 'shell_left': (0.95, 0.95, 0.9), 'jaw_frame': (1, 0.85, 0.2)}
    # torso + neck from -y, rear-ish
    c = np.array([20.0, -20.0, 55.0])
    items = [(crop(part(k), c, 45), cols.get(k, (0.7, 0.7, 0.7)), 1.0) for k in cols]
    items += [(s, (0.85, 0.1, 0.1), 1.0) for s in screws_near(np.array([20, -18, 55.0]), 40)]
    for name, pos in (('neck-side', c + [0, -200, 0]), ('neck-rear', c + [-140, -140, 20]), ('neck-front', c + [140, -140, 20])):
        render(items, E.SCRATCH / f'r-{name}.png', (pos, c, (0, 0, 1)), size=(1000, 1200), parallel_scale=40,
               lines=[(route[:12], (0.9, 0.0, 0.0), 3)])
    # head clip site, from above/-y, cap hidden
    c = np.array([44.0, -28.0, 118.0])
    hk = ['head_bottom', 'jaw_support', 'motor13', 'head_yaw_link', 'jaw_frame', 'mouth_sliding_ring', 'pi', 'motor14', 'motor15']
    items = [(crop(part(k), c, 30), (0.8, 0.8, 0.75) if k not in ('pi',) else (0.2, 0.6, 0.2), 1.0) for k in hk]
    items += [(s, (0.85, 0.1, 0.1), 1.0) for s in screws_near(c, 30)]
    for name, pos in (('head-top', c + [0, 0, 200]), ('head-side', c + [0, -200, 30]), ('head-rear', c + [-150, -100, 120])):
        render(items, E.SCRATCH / f'r-{name}.png', (pos, c, (1, 0, 0) if name == 'head-top' else (0, 0, 1)), size=(1100, 1000),
               parallel_scale=22, lines=[(route[8:20], (0.9, 0.0, 0.0), 3)])
    # cap clip site with the study cap, from the front
    c = np.array([62.0, 24.0, 140.0])
    cap = trimesh.load(E.STUDY_CAP, force='mesh')
    items = [(crop(cap, c, 25), (1.0, 0.6, 0.2), 0.35), (crop(part('pi'), c, 25), (0.2, 0.6, 0.2), 1.0)]
    for k in ['head_pi_gpio_pin_01_receiving', 'head_pi_gpio_pin_02_receiving', 'head_pi_component_bottom-usb-edge-context']:
        items.append((part(k), (0.2, 0.2, 0.2), 1.0))
    items += [(s, (0.85, 0.1, 0.1), 1.0) for s in screws_near(c, 25)]
    for name, pos in (('cap-front', c + [200, 0, 0]), ('cap-side', c + [40, 200, 40]), ('cap-top', c + [60, 0, 200])):
        render(items, E.SCRATCH / f'r-{name}.png', (pos, c, (0, 0, 1) if name != 'cap-top' else (-1, 0, 0)), size=(1000, 1000),
               parallel_scale=20, lines=[(route[17:], (0.9, 0.0, 0.0), 3)])


if __name__ == '__main__':
    main()
