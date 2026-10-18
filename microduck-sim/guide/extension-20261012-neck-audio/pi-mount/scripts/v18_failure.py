#!/usr/bin/env python3
"""Why the V1.8 Pi rails break: section sizes along each rail, layer direction against the bending stress, and the
support the released Orange slice actually printed around the rails. Read-only on all V1.8 inputs.

Sections: the V1.8 cap (print/world/head_cap.stl) cut by planes normal to the rail axis (perpendicular to the Pi
screw axis, i.e. the Pi plane direction) every 0.25 mm. Each cut is restricted to the rail's window, so the merged
shell above the rail root is excluded. Section properties (area, second moments, elastic section moduli) are taken in
the rail frame: a = screw axis (load from pushing housings onto the header), b = y (sideways prying).
Bending per unit load: a 1 N force at a Pi screw centre gives moment F * (distance along the rail) at every section
between that screw and the root; stress = M / Z. That is beam statics on measured geometry (no material data).
Support: every support / support-interface extrusion in run/native/Orange_Bambu/plate_1.gcode mapped back to the
robot frame (bed = gcode + extruder offset; world = inverse(sourceToPrint + drop) of (bed - plate translation)).
Writes ../v18-failure.json and ../png/v18-rail-sections.png, ../png/v18-rail-support.png.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import trimesh
from shapely.geometry import Polygon, box

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent
SIM = STUDY.parents[2]
REL = SIM / 'guide/print/release-V1.8'
CAP = SIM / 'guide/print/world/head_cap.stl'

A_SCREW = np.array([-0.984808, 0.0, 0.173648])     # screw insertion direction (fasteners.json E-pi-01..04)
AX = np.array([0.173648, 0.0, 0.984808])           # rail axis (in the Pi plane, perpendicular to the screws)
SCREWS = {'E-pi-01': (-1, np.array([57.341, -29.0, 118.245]), 'M2 x 6 TAP'),
          'E-pi-02': (+1, np.array([57.341, 29.0, 118.245]), 'M2 x 4 TAP'),
          'E-pi-03': (-1, np.array([61.335, -29.0, 140.895]), 'M2 x 6 TAP'),
          'E-pi-04': (+1, np.array([61.335, 29.0, 140.895]), 'M2 x 6 TAP')}


def _ring(c, ccw=True):
    c = np.asarray(c)[:, :2]
    x0, y0, x1, y1 = c[:-1, 0], c[:-1, 1], c[1:, 0], c[1:, 1]
    cr = x0 * y1 - x1 * y0
    t = np.array([cr.sum() / 2, ((x0 + x1) * cr).sum() / 6, ((y0 + y1) * cr).sum() / 6,
                  ((y0 ** 2 + y0 * y1 + y1 ** 2) * cr).sum() / 12, ((x0 ** 2 + x0 * x1 + x1 ** 2) * cr).sum() / 12])
    return t if t[0] > 0 else -t          # orientation-independent (positive area)


def sec_props(poly: Polygon):
    """Area, centroid, second moments and elastic section moduli of a (possibly holed) polygon in its 2-D frame (u, v).
    Zu: bending about the u axis (stress varies with v); Zv: bending about the v axis (stress varies with u)."""
    A, Sx, Sy, Ixx, Iyy = _ring(poly.exterior.coords) - sum((_ring(r.coords) for r in poly.interiors), np.zeros(5))
    cu, cv = Sx / A, Sy / A
    Iu, Iv = Ixx - A * cv ** 2, Iyy - A * cu ** 2
    xy = np.asarray(poly.exterior.coords)
    return dict(area=A, Iu=Iu, Iv=Iv, Zu=Iu / np.abs(xy[:, 1] - cv).max(), Zv=Iv / np.abs(xy[:, 0] - cu).max(),
                extentU=float(np.ptp(xy[:, 0])), extentV=float(np.ptp(xy[:, 1])))


def rail_sections(cap, side):
    """Sections normal to AX along the rail through the lower screw line. Frame: u = screw axis (A_SCREW), v = y."""
    base = SCREWS['E-pi-01' if side < 0 else 'E-pi-02'][1] + 4.0 * A_SCREW   # a point inside the rail on the lower pilot axis
    rows = []
    for s in np.arange(-4.0, 30.01, 0.25):
        o = base + s * AX
        sec = cap.section(plane_origin=o, plane_normal=AX)
        if sec is None:
            continue
        T = np.eye(4)
        T[:3, 0], T[:3, 1], T[:3, 2], T[:3, 3] = A_SCREW, [0, 1, 0], -AX, o   # right-handed; v = y - o_y
        pl, _ = sec.to_2D(to_2D=np.linalg.inv(T))
        win = box(-7.0, -6.0, 7.0, 6.0)
        best = None
        for P in pl.polygons_full:
            Q = P.intersection(win)
            for g in getattr(Q, 'geoms', [Q]):
                if g.is_empty or g.area < 0.3 or g.geom_type != 'Polygon':
                    continue
                # the rail component: the one containing the rail centreline (u near 0..-1, v = +-29)
                if g.distance(Polygon([(0, -1), (0, 1), (2, 1), (2, -1)])) > 0.5:
                    continue
                touches_win = g.bounds[0] <= -6.99 or g.bounds[2] >= 6.99 or g.bounds[1] <= -5.99 or g.bounds[3] >= 5.99
                best = (g, touches_win)
        if best is None:
            continue
        g, merged = best
        p = sec_props(g)
        rows.append(dict(s=round(float(s), 2), z=round(float(o[2]), 2), merged=bool(merged), area=round(p['area'], 2),
                         depthAlongScrewMm=round(p['extentU'], 2), widthYmm=round(p['extentV'], 2),
                         ZforScrewAxisLoadMm3=round(p['Zv'], 3), ZforSideLoadMm3=round(p['Zu'], 3),
                         holes=len(g.interiors)))
    return rows


def bending(rows, side):
    """Max stress per 1 N at each screw, along the free (unmerged) length, for both load directions."""
    out = {}
    for sid, (sd, c, spec) in SCREWS.items():
        if sd != side:
            continue
        base = SCREWS['E-pi-01' if side < 0 else 'E-pi-02'][1] + 4.0 * A_SCREW
        s_load = float((c - base) @ AX)
        best = {}
        for r in rows:
            if r['merged'] or r['s'] <= s_load + 0.01:
                continue
            arm = r['s'] - s_load
            for k, zk in (('screwAxis', 'ZforScrewAxisLoadMm3'), ('sideways', 'ZforSideLoadMm3')):
                st = arm / r[zk]          # MPa per N  (N*mm / mm^3)
                if st > best.get(k, {}).get('mpaPerN', 0):
                    best[k] = dict(mpaPerN=round(st, 3), atZ=r['z'], armMm=round(arm, 2), area=r['area'],
                                   depth=r['depthAlongScrewMm'], width=r['widthYmm'])
        out[sid] = best
    return out


def support_points(machine='Bambu', features=('support',)):
    prep = json.loads((REL / 'run/preparation.json').read_text())
    part = next(p for p in prep['parts'] if p['key'] == 'head_cap')
    row = next(x for x in prep['rows'] if x['color'] == 'Orange' and x['machine'] == machine)
    tr = np.array(next(pl['translation'] for pl in row['placements'] if pl['key'] == 'head_cap'))
    T = np.array(part['sourceToPrint'])
    T[2, 3] += part['dropToBedMm']
    Ti = np.linalg.inv(T)
    g = (REL / f'run/native/Orange_{machine}/plate_1.gcode').read_text(errors='replace')
    off = np.array([0.0, 0.0])
    m = re.search(r'^; extruder_offset = ([-\d.]+)x([-\d.]+)', g, re.M)
    if m:
        off = np.array([float(m[1]), float(m[2])])
    kind, xyz, pts = '', np.zeros(3), []
    for line in g.splitlines():
        if line.startswith(('; FEATURE:', ';TYPE:')):
            kind = line.split(':', 1)[1].strip().lower()
            continue
        if not (line.startswith('G1 ') or line.startswith('G2 ') or line.startswith('G3 ')):
            continue
        v = {k: float(t) for k, t in re.findall(r'([XYZE])([-+]?\d*\.?\d+)', line.split(';')[0])}
        end = np.array([v.get('X', xyz[0]), v.get('Y', xyz[1]), v.get('Z', xyz[2])])
        if v.get('E', 0) > 0 and any(f in kind for f in features) and (end[:2] != xyz[:2]).any():
            n = max(2, int(np.linalg.norm(end[:2] - xyz[:2]) / 0.5) + 1)
            for f in np.linspace(0, 1, n):
                p = xyz + f * (end - xyz)
                pts.append((p[0] + off[0], p[1] + off[1], end[2], features.index(next(f for f in features if f in kind))))
        xyz = end
    P = np.array(pts)
    bed = P[:, :3] - tr
    world = (Ti @ np.c_[bed, np.ones(len(bed))].T).T[:, :3]
    return world, P[:, 3].astype(int), T


def main():
    cap = trimesh.load(CAP, force='mesh')
    res = {'source': str(CAP), 'method': __doc__}
    rails = {}
    for side, name in ((-1, 'minus_y_rail (E-pi-01 lower, E-pi-03 upper)'), (1, 'plus_y_rail (E-pi-02 lower, E-pi-04 upper)')):
        rows = rail_sections(cap, side)
        free = [r for r in rows if not r['merged']]
        thin = min((r for r in free if r['holes'] == 0), key=lambda r: r['area'])
        rails[name] = {'sections': rows, 'freeLengthZ': [free[0]['z'], free[-1]['z']] if free else None,
                       'thinnestSolidSection': thin, 'bendingPerNewton': bending(rows, side)}
        print(name, 'free z', rails[name]['freeLengthZ'], 'thinnest', thin)
        print('  bending', json.dumps(rails[name]['bendingPerNewton']))
    res['rails'] = rails
    # print orientation: layer normal (print +z) in the robot frame
    world, kindi, T = support_points('Bambu')
    layer_n = T[2, :3] / np.linalg.norm(T[2, :3])
    ang = float(np.degrees(np.arccos(abs(layer_n @ AX))))
    res['printOrientation'] = {'printUpInRobotFrame': np.round(layer_n, 4).tolist(),
                               'angleRailAxisToLayerNormalDeg': round(ang, 1),
                               'fractionOfRailBendingStressNormalToLayers': round(float(np.cos(np.radians(ang)) ** 2), 3),
                               'meaning': 'the cap prints roof-down, so each hanging rail is a column built upward from '
                                          'the roof; its layers stack along the rail, and bending stress along the rail '
                                          'pulls the layers apart (inter-layer bond)'}
    # support and unsupported overhang extrusions near each rail, both released Orange slices
    boxes = {'minus_y_rail': ([45, -35, 112], [64, -20, 150]), 'plus_y_rail': ([45, 20, 112], [64, 35, 150])}
    sup, keep = {}, {}
    for machine in ('Bambu', 'Elegoo'):
        W_all, K, _ = support_points(machine, features=('support', 'overhang wall', 'bridge'))
        for k, (lo, hi) in boxes.items():
            m = np.all((W_all >= lo) & (W_all <= hi), axis=1)
            entry = {'box': [lo, hi]}
            for i, f in enumerate(('support', 'overhang wall', 'bridge')):
                W = W_all[m & (K == i)]
                e = {'samples0p5mm': int(len(W))}
                if len(W):
                    e['bounds'] = [np.round(W.min(0), 1).tolist(), np.round(W.max(0), 1).tolist()]
                    for sid, (sd, c, spec) in SCREWS.items():
                        if (sd > 0) == k.startswith('plus'):
                            e[f'nearestTo_{sid}_mm'] = round(float(np.linalg.norm(W - c, axis=1).min()), 1)
                entry[f] = e
            sup[f'{machine}:{k}'] = entry
            keep[f'{machine}:{k}'] = (W_all[m], K[m])
            print('slice', machine, k, json.dumps(entry))
    res['releasedOrangeSlicesNearRails'] = sup
    res['sliceSettings'] = {'support_type': 'tree(auto)', 'support_threshold_angle': 30, 'support_on_build_plate_only': 0,
                            'wall_loops': 4, 'layer_height': 0.2, 'filament_type': 'PLA',
                            'source': [str(REL / f'run/native/Orange_{m}/plate_1.gcode') for m in ('Bambu', 'Elegoo')]}
    (STUDY / 'v18-failure.json').write_text(json.dumps(res, indent=1))
    # plots
    fig, ax = plt.subplots(1, 2, figsize=(12, 5))
    for name, r in rails.items():
        S = r['sections']
        z = [x['z'] for x in S]
        ax[0].plot(z, [x['area'] for x in S], label=name.split(' ')[0])
        ax[1].plot(z, [x['ZforScrewAxisLoadMm3'] for x in S], label=name.split(' ')[0] + ' Z (push along screw)')
        ax[1].plot(z, [x['ZforSideLoadMm3'] for x in S], ls='--', label=name.split(' ')[0] + ' Z (sideways)')
    for c in (118.245, 140.895):
        for a in ax:
            a.axvline(c, color='grey', lw=0.6)
    ax[0].set_xlabel('z mm (along the rail)'); ax[0].set_ylabel('section area mm2'); ax[0].legend(fontsize=8)
    ax[1].set_xlabel('z mm'); ax[1].set_ylabel('section modulus mm3'); ax[1].set_yscale('log'); ax[1].legend(fontsize=7)
    fig.suptitle('V1.8 Pi rails: sections normal to the rail (grey lines = screw centres; merged shell above the root excluded)', fontsize=9)
    fig.tight_layout(); fig.savefig(STUDY / 'png/v18-rail-sections.png', dpi=110); plt.close(fig)
    fig, axs = plt.subplots(2, 2, figsize=(12, 11))
    cols = {0: ('#2563eb', 'support'), 1: ('#dc2626', 'overhang wall (printed in air)'), 2: ('#059669', 'bridge')}
    for a, (machine, (k, (lo, hi)), y0) in zip(axs.ravel(), [(m, kv, y) for m in ('Bambu', 'Elegoo') for kv, y in zip(boxes.items(), (-29, 29))]):
        s_ = cap.section(plane_origin=[0, y0, 0], plane_normal=[0, 1, 0])
        for e in s_.entities:
            p = s_.vertices[e.points]
            a.plot(p[:, 0], p[:, 2], color='#d97706', lw=0.8)
        W, K = keep[f'{machine}:{k}']
        for i, (c, lab) in cols.items():
            a.scatter(W[K == i, 0], W[K == i, 2], s=1, color=c, label=lab)
        for sid, (sd, c, spec) in SCREWS.items():
            if np.sign(c[1]) == np.sign(y0):
                a.plot(c[0], c[2], 'kx'); a.annotate(sid, (c[0] + 0.5, c[2] + 0.5), fontsize=7)
        a.set_xlim(40, 66); a.set_ylim(108, 155); a.set_aspect('equal'); a.grid(lw=0.3)
        a.set_title(f'{k}: cap section y = {y0}; extrusions with |y| 20..35, released Orange {machine} slice', fontsize=8)
        a.legend(fontsize=7, markerscale=6); a.set_xlabel('x mm'); a.set_ylabel('z mm')
    fig.tight_layout(); fig.savefig(STUDY / 'png/v18-rail-support.png', dpi=110); plt.close(fig)


if __name__ == '__main__':
    main()
