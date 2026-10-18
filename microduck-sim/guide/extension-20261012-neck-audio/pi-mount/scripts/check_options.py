#!/usr/bin/env python3
"""Exact checks of a Pi-mount option against the V1.8 head plus the recommended audio layout.

usage: check_options.py A|B
For every new solid (cap additions, separate parts, screw envelopes):
  static     overlap and gap to every head-fixed solid and the Pi group (Pi board, components, header, 13 receiving
             housings); intended contacts listed per option do not fail
  sweeps     yaw body over head roll +-25 deg (1 deg), jaw 0..40 deg (1 deg)
  descent    cap-mounted parts lowered with the cap (40 mm, 0.5 mm steps)
  cables     CSI ribbon and head bundle centrelines (routes.json, half sizes 8 / 3 mm)
  audio      overlap and gap to every audio study solid and audio wire tube
  corridor   overlap with the neck-route keep-outs (behind the Pi in the middle, below z 111.9, below the header)
  exterior   added cap material outside the V1.8 hull or in its exterior grooves
Also: print-overhang area of the cap around the rails (V1.8 vs option, robot-to-print transform of the V1.8 manifest)
and beam section numbers (MPa per N at the lower screw). Writes ../<opt>-checks.json.
"""
from __future__ import annotations

import json
import sys

import manifold3d as m3
import numpy as np
import trimesh

from pm_lib import (csi_ribbon_strip, AUDIO_SOLIDS, AX, A_SCREW, CAP_V18, FIXED, SCREWS, SOURCE_TO_PRINT, STUDY, Head, audio_solid,
                    audio_wire_tubes, box, cable_clearance, corridor_keepouts, cyl, j, load_stl_man, tm_from_man)

S = STUDY / 'study-solids'
Y = np.array([0.0, 1.0, 0.0])


def overhang(cap_tm, regions):
    R = SOURCE_TO_PRINT[:3, :3]
    n = cap_tm.face_normals @ R.T
    cen = cap_tm.triangles_center
    area = cap_tm.area_faces
    theta = np.degrees(np.arccos(np.clip(-n[:, 2], -1, 1)))     # angle of a down-facing face from the print horizontal
    down = n[:, 2] < 0
    # pilot surfaces: within 1.0 mm of a pilot axis (bridged holes, not support-holding ledges)
    pil = np.zeros(len(cen), bool)
    for c in SCREWS.values():
        d = cen - c
        t = d @ A_SCREW
        r = np.linalg.norm(d - np.outer(t, A_SCREW), axis=1)
        pil |= (r < 1.0) & (t > -0.5) & (t < 9)
    out = {}
    for k, (lo, hi) in regions.items():
        m = np.all((cen >= lo) & (cen <= hi), axis=1) & down
        sel = m & ~pil & (theta < 30)
        if sel.any():
            sub = cap_tm.submesh([np.where(sel)[0]], append=True)
            out.setdefault('clustersBelow30deg', {})[k] = [
                {'areaMm2': round(float(cc.area), 2), 'bounds': np.round(cc.bounds, 1).tolist()}
                for cc in sorted(sub.split(only_watertight=False), key=lambda cc: -cc.area) if cc.area > 0.2]
        out[k] = {f'below{a}degMm2': round(float(area[m & ~pil & (theta < a)].sum()), 2) for a in (30, 40)}
        out[k]['pilotBridgeFacesBelow30degMm2'] = round(float(area[m & pil & (theta < 30)].sum()), 2)
        worst = m & ~pil & (theta < 40)
        if worst.any():
            out[k]['locationsBelow40deg'] = np.round(cen[worst][np.argsort(-area[worst])[:6]], 1).tolist()
    return out


def section_uv(cap_tm, c, w, win):
    from shapely.geometry import box as sbox
    o = c + w * AX
    sec = cap_tm.section(plane_origin=o, plane_normal=AX)
    if sec is None:
        return None
    T = np.eye(4)
    T[:3, 0], T[:3, 1], T[:3, 2], T[:3, 3] = A_SCREW, Y, -AX, o
    pl, _ = sec.to_2D(to_2D=np.linalg.inv(T))
    g = [p.intersection(sbox(win[0], win[1] - c[1], win[2], win[3] - c[1])) for p in pl.polygons_full]
    from shapely.ops import unary_union
    U = unary_union([x for x in g if not x.is_empty])
    core = sbox(3.0, -1.0, 6.0, 1.0)            # the rail body around the screw line; drop pieces not joined to it
    keep = [p for p in getattr(U, 'geoms', [U]) if p.geom_type == 'Polygon' and p.distance(core) < 1e-6]
    return unary_union(keep) if keep else None


def _ring(c):
    c = np.asarray(c)[:, :2]
    x0, y0, x1, y1 = c[:-1, 0], c[:-1, 1], c[1:, 0], c[1:, 1]
    cr = x0 * y1 - x1 * y0
    t = np.array([cr.sum() / 2, ((x0 + x1) * cr).sum() / 6, ((y0 + y1) * cr).sum() / 6,
                  ((x0 ** 2 + x0 * x1 + x1 ** 2) * cr).sum() / 12, ((y0 ** 2 + y0 * y1 + y1 ** 2) * cr).sum() / 12])
    return t if t[0] > 0 else -t


def zmod(geom, axis):
    """Area and elastic section modulus of a shapely (multi)polygon (holes subtracted) for bending whose stress varies
    along coordinate `axis` (0 = first 2-D coordinate, 1 = second): Z = I / c_max, I = integral (x_axis - centroid)^2."""
    polys = [p for p in getattr(geom, 'geoms', [geom]) if p.geom_type == 'Polygon' and p.area > 1e-3]
    if not polys:
        return 0.0, 0.0
    tot = sum((_ring(p.exterior.coords) - sum((_ring(r.coords) for r in p.interiors), np.zeros(5)) for p in polys),
              np.zeros(5))
    A, Sx, Sy, Ixx_, Iyy_ = tot          # Ixx_ = integral x^2, Iyy_ = integral y^2 (about the origin)
    cen = (Sx / A, Sy / A)
    I = (Ixx_ - A * cen[0] ** 2) if axis == 0 else (Iyy_ - A * cen[1] ** 2)
    cmax = max(np.abs(np.asarray(p.exterior.coords)[:, axis] - cen[axis]).max() for p in polys)
    return A, I / cmax


def rail_strength(cap_tm, label, part_tm=None):
    """MPa per N for a 1 N load at the lower screw (u direction = pushing housings on; v = sideways), along the rail."""
    out = {}
    for side, sid in ((-1, 'E-pi-01'), (1, 'E-pi-02')):
        c = SCREWS[sid]
        tm = part_tm[side] if part_tm else cap_tm
        lo, hi = (25.0, 33.5) if side > 0 else (-33.5, -25.0)
        rows = []
        for w in np.arange(3.5, 20.01, 0.5):
            g = section_uv(tm, c, w, (0.3, lo, 12.0, hi))
            if g is None or g.is_empty:
                continue
            A, Zu = zmod(g, 0)
            _, Zv = zmod(g, 1)
            rows.append(dict(w=round(float(w), 2), z=round(float((c + w * AX)[2]), 2), area=round(A, 2), Zu=round(Zu, 3),
                             Zv=round(Zv, 3), mpaPerN_u=round(w / Zu, 3), mpaPerN_v=round(w / Zv, 3)))
        worst = max(rows, key=lambda r: r['mpaPerN_u'])
        worst_v = max(rows, key=lambda r: r['mpaPerN_v'])
        out['minus_y' if side < 0 else 'plus_y'] = {'worstPush': worst, 'worstSideways': worst_v,
                                                    'window': f'|y| 25..33.5 (side wall excluded), u 0.3..12'}
    return out


def web_path(cap_tm):
    """Second load path of option A: the web carries the lower-screw load to the side wall. Section y = +-33 (between
    the screw line and the wall), material within 4 mm above/below the lower boss (assumed effective width);
    stress along y, i.e. in the layer plane."""
    from shapely.geometry import box as sbox
    out = {}
    for side, sid in ((-1, 'E-pi-01'), (1, 'E-pi-02')):
        c = SCREWS[sid]
        y0 = side * 33.0
        o = np.array([c[0], y0, c[2]])
        sec = cap_tm.section(plane_origin=o, plane_normal=Y)
        T = np.eye(4)
        T[:3, 0], T[:3, 1], T[:3, 2], T[:3, 3] = A_SCREW, AX, np.cross(A_SCREW, AX), o
        pl, _ = sec.to_2D(to_2D=np.linalg.inv(T))
        g = [p.intersection(sbox(0.3, -7.1, 12.0, 7.1)) for p in pl.polygons_full]
        from shapely.ops import unary_union
        G = unary_union([x for x in g if not x.is_empty])
        A, Zu = zmod(G, 0)
        arm = abs(y0 - c[1])
        out['minus_y' if side < 0 else 'plus_y'] = {'sectionAtY': y0, 'areaMm2': round(A, 2), 'Zmm3': round(Zu, 3),
                                                    'armMm': arm, 'mpaPerN': round(arm / Zu, 3) if Zu else None}
    return out


def main(opt):
    cfg = json.loads((STUDY / f'{opt}-parts.json').read_text())
    cap_opt = load_stl_man(S / cfg['cap'])
    H = Head(cap_override=cap_opt)
    v18 = load_stl_man(CAP_V18)
    base = load_stl_man(cfg['baseCap'])
    parts = {k: load_stl_man(S / v) for k, v in cfg['parts'].items()}
    intended = {tuple(k.split('|')): v for k, v in cfg.get('intended', {}).items()}
    aud = {('audio_' + k): audio_solid(k) for k in AUDIO_SOLIDS}
    aud.update(audio_wire_tubes())
    keep = corridor_keepouts()
    res = {'option': opt, 'parts': {}, 'failures': []}
    for k, M in parts.items():
        cap_mounted = True
        skip = ('head_cap',) if k.startswith('cap_added') else ()
        st = H.static(k, M, skip=skip)
        for r in st:
            r['intended'] = intended.get((k, r['with']))
            if r['overlapMm3'] > 1e-3 and not r['intended']:
                res['failures'].append({'part': k, **r})
        rib = csi_ribbon_strip()
        rec = {'csiRibbonStrip16mm': {'overlapMm3': round((rib ^ M).volume(), 4), 'gapMm': round(float(rib.min_gap(M, 10)), 3)},
               'static': st[:8], 'roll': H.roll_sweep(M, 1.0), 'jaw': H.jaw_sweep(M, 1.0),
               'descentWithCap': H.descent(M, 0.5) if cap_mounted else None, 'cables': cable_clearance(M)}
        if rec['roll']['overlapMm3'] > 0 or rec['jaw']['overlapMm3'] > 0:
            res['failures'].append({'part': k, 'sweep': True, 'roll': rec['roll'], 'jaw': rec['jaw']})
        for o, d in (rec['descentWithCap'] or {}).items():
            if d['excessMm3'] > 0.5:
                res['failures'].append({'part': k, 'descent': o, **d})
        arows = []
        for ak, A in aud.items():
            if (A ^ m3.Manifold()).volume() < 0 or not len(A.decompose()):
                continue
            Ab, Mb = np.array(A.bounding_box()).reshape(2, 3), np.array(M.bounding_box()).reshape(2, 3)
            if np.any(Ab[0] - 8 > Mb[1]) or np.any(Mb[0] - 8 > Ab[1]):
                continue
            ov = (A ^ M).volume()
            arows.append({'with': ak, 'overlapMm3': round(ov, 4), 'gapMm': round(float(A.min_gap(M, 8)), 3)})
            if ov > 1e-3 and not intended.get((k, ak)):
                res['failures'].append({'part': k, 'with': ak, 'overlapMm3': ov})
        rec['audio'] = sorted(arows, key=lambda r: r['gapMm'])[:4]
        rec['corridor'] = {kk: round((K ^ M).volume(), 4) for kk, K in keep.items()}
        for kk, v in rec['corridor'].items():
            if v > 1e-3:
                res['failures'].append({'part': k, 'corridor': kk, 'overlapMm3': v})
        res['parts'][k] = rec
        print(k, 'static', [(r['with'], r['overlapMm3'], r['gapMm']) for r in st[:4]], 'roll', rec['roll'], 'jaw',
              rec['jaw'], 'descent', rec['descentWithCap'], 'cables', rec['cables'], 'audio', rec['audio'][:2],
              'corridor', rec['corridor'], flush=True)
    # the V1.8 rails' own cable distances, for comparison
    rails18 = v18 ^ (box([49, -32.4, 114], [61, -25.4, 145]) + box([49, 25.4, 114], [61, 32.4, 145]))
    res['v18RailsCables'] = cable_clearance(rails18)
    res['v18RailsCsiRibbonStripGapMm'] = round(float(csi_ribbon_strip().min_gap(rails18, 10)), 3)
    # exterior against the V1.8 skin
    added = m3.Manifold.batch_boolean([b for b in (cap_opt - base).decompose() if b.volume() > 0.01] or [m3.Manifold()],
                                      m3.OpType.Add)
    hull = m3.Manifold.batch_hull([v18])
    pieces = sorted((hull - v18).decompose(), key=lambda m: -m.volume())
    grooves = m3.Manifold.batch_boolean(pieces[1:], m3.OpType.Add)
    res['exterior'] = {'addedOutsideV18HullMm3': round((added - hull).volume(), 4),
                       'addedInExteriorGroovesMm3': round((added ^ grooves).volume(), 4),
                       'removedVsBaseMm3': round((base - cap_opt).volume(), 3)}
    if res['exterior']['addedOutsideV18HullMm3'] > 1e-3 or res['exterior']['addedInExteriorGroovesMm3'] > 1e-3:
        res['failures'].append({'exterior': res['exterior']})
    # print overhangs around the rails, V1.8 vs option
    # rail features only: below the roof (z <= 146.5); higher faces are the roof and its exterior grooves (unchanged)
    regions = {'minus_y_rail': ([47, -46, 112], [64, -24, 146.5]), 'plus_y_rail': ([47, 24, 112], [64, 46, 146.5])}
    res['overhang'] = {'V1.8': overhang(trimesh.load(CAP_V18, force='mesh'), regions),
                       opt: overhang(tm_from_man(cap_opt), regions),
                       'rule': 'faces pointing down in the print pose whose slope from the print horizontal is below '
                               '30 deg (the slice profiles use support_threshold_angle 30) or below 40 deg (margin); '
                               'pilot bores reported separately (they bridge)'}
    if 'strength' in cfg:
        res['strength'] = {'V1.8 (bare rail, across layers)': rail_strength(trimesh.load(CAP_V18, force='mesh'), 'V1.8')}
        if cfg['strength'] == 'cap':
            tm = tm_from_man(cap_opt)
            res['strength'][f'{opt} along the rail (across layers, side wall excluded)'] = rail_strength(tm, opt)
            res['strength'][f'{opt} web to side wall (along layers)'] = web_path(tm)
        else:
            pt = {s: trimesh.load(S / cfg['strength'][str(s)], force='mesh') for s in (-1, 1)}
            res['strength'][f'{opt} bracket (along layers)'] = rail_strength(None, opt, part_tm=pt)
    res['ok'] = not res['failures']
    (STUDY / f'{opt}-checks.json').write_text(json.dumps(j(res), indent=1))
    print('exterior', res['exterior'])
    print('overhang', json.dumps(j(res['overhang']))[:1500])
    print('strength', json.dumps(j(res.get('strength')))[:2500])
    print('FAILURES', json.dumps(j(res['failures']))[:2500])


if __name__ == '__main__':
    main(sys.argv[1])
