"""Fit check for pluggable connectors at the two V1.8 board-solder points (OpenRB-150 J12, DFR1202 pads).

Robot frame, mm (x forward, y left, z up). Read-only on the guide: loads the interference-audit solid cache through
ia_lib.load_solid (rear_pack, rear_pack_cover, openrb_board, regulator, imu_board, xt30_robot, plus every cached solid
whose bounds reach the pack) and the torso cable centrelines in guide/content/routes.json.

Each candidate is a set of axis-aligned boxes: connector body, mated plug, wire-exit room, pin tails, and (for the
DFR1202) the adapter board. For every box set the script reports, per rigid part, the exact overlap volume (manifold3d
boolean) and the minimum gap (manifold3d min_gap), plus the insertion sweep for the assembly order the pack uses.
Dimensions and their sources are in CANDIDATES; anything marked "inference" is not a datasheet number.

Run (bounded runner, as for every geometry job in this repo):
  /tmp/microduck-cad-venv/bin/python <repo>/microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py \
      --max-mib 1400 --seconds 300 --wait-lock-seconds 60 --report run-report.json -- \
      /tmp/microduck-cad-venv/bin/python fit_connectors.py
Writes fit-results.json next to this file.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
sys.path.insert(0, str(REPO / 'microduck-sim/guide/content/interference-audit'))
import ia_lib  # noqa: E402
import manifold3d as m3  # noqa: E402

SEARCH = 6.0          # mm: gaps larger than this are reported as ">6"
PCB_FACE = -26.45     # OpenRB component-side copper face (most frequent vertex x of the board mesh; PCB x -26.45..-24.8)
PCB_BACK = -24.8
DFR_FRONT = -37.0     # DFR1202 bare back face (thermal-pad side), resting on the pack lips at x -37

# ---------------------------------------------------------------- J12 geometry (measured in this script, see j12_holes)
J12_Z = 6.7
J12_Y = [-3.7, -1.7, 0.3, 2.3]   # pin 4 (SERIAL_TX), 3 (SERIAL_RX), 2 (+3V3), 1 (GND); order inferred, see README


def box(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    lo2, hi2 = np.minimum(lo, hi), np.maximum(lo, hi)
    return m3.Manifold.cube((hi2 - lo2).tolist()).translate(lo2.tolist())


def union(parts):
    out = parts[0]
    for p in parts[1:]:
        out = out + p
    return out


def j12_holes():
    """Find the J12 row in the placed board mesh (guide/print/world/openrb-board-upright.stl): four holes of about
    0.8 mm on one z row at 2.0 mm pitch, next to the JP1 header."""
    import trimesh
    mesh = trimesh.load(REPO / 'microduck-sim/guide/print/world/openrb-board-upright.stl')
    sec = mesh.section(plane_origin=[(PCB_FACE + PCB_BACK) / 2, 0, 0], plane_normal=[1, 0, 0])
    holes = []
    for p in sec.discrete:
        p = np.asarray(p)
        ext = p.max(0) - p.min(0)
        if 0.6 < ext[1] < 1.0 and abs(ext[1] - ext[2]) < 0.05:
            c = p.mean(0)
            holes.append((round(float(c[1]), 2), round(float(c[2]), 2), round(float(ext[1]), 2)))
    rows = {}
    for y, z, d in holes:
        rows.setdefault(round(z, 1), []).append((y, d))
    found = []
    for z, row in rows.items():
        ys = sorted(y for y, _ in row)
        if len(ys) == 4 and np.allclose(np.diff(ys), 2.0, atol=0.05):
            found.append({'z': z, 'y': ys, 'pitch': round(float(np.mean(np.diff(ys))), 3),
                          'holeDiameter': sorted({d for _, d in row})})
    return found


# ---------------------------------------------------------------- candidates
def ph_top(latch_side):
    """JST B4B-PH-K-S top entry + PHR-4. JST PH datasheet: header 9.9 along the row (pins 6.0 + 1.95 each end),
    4.5 deep with the pin row 1.7 from one face, 6.0 tall; mated height (8) above the board. Which face carries the
    1.7 mm offset is not fixed here, so both orientations are checked (latch_side = +1 or -1 picks the 2.8 mm side)."""
    y0, y1 = min(J12_Y) - 1.95, max(J12_Y) + 1.95
    z0, z1 = (J12_Z - 1.7, J12_Z + 2.8) if latch_side > 0 else (J12_Z - 2.8, J12_Z + 1.7)
    body = box([PCB_FACE - 0.05, y0, z0], [PCB_FACE - 8.0, y1, z1])
    # Wire exit: the two 26 AWG wires leave the housing top at pins 3 and 4 and need about 2.5 mm before they can
    # turn (inference: bend radius about 2.5 x a 1.0 mm insulation diameter).
    exit_ = box([PCB_FACE - 8.0, J12_Y[0] - 1.0, J12_Z - 1.0], [PCB_FACE - 10.5, J12_Y[1] + 1.0, J12_Z + 1.0])
    tails = box([PCB_BACK, y0 + 1.6, J12_Z - 0.5], [PCB_BACK + 1.8, y1 - 1.6, J12_Z + 0.5])  # 3.4 tail - 1.6 PCB
    return {'body+plug': body, 'wire exit': exit_, 'pin tails (board back)': tails}


def ph_side(direction):
    """JST S4B-PH-K-S side entry + PHR-4, mating along -z (direction -1) or +z (+1). JST layout figure values:
    4.8 tall, 7.6 deep, (6.25) pin row to header front, (9.6) pin row to the mated housing rear. The reading of the two
    bracketed values is inference from the layout figure."""
    y0, y1 = min(J12_Y) - 1.95, max(J12_Y) + 1.95
    s = direction
    back, front, plug = J12_Z - s * 1.35, J12_Z + s * 6.25, J12_Z + s * 9.6
    header = box([PCB_FACE - 0.05, y0, back], [PCB_FACE - 4.8, y1, front])
    housing = box([PCB_FACE - 0.05, y0 + 0.05, front], [PCB_FACE - 4.5, y1 - 0.05, plug])
    exit_ = box([PCB_FACE - 0.5, J12_Y[0] - 1.0, plug], [PCB_FACE - 3.5, J12_Y[1] + 1.0, plug + s * 2.5])
    return {'header': header, 'plug': housing, 'wire exit': exit_}


TB_H, TB_D = 8.5, 6.9   # Same Sky TB0011-350: 8.50 tall, 6.90 deep, pin row centred (3.45), pitch 3.5, L = 3.5 N


def carrier(z_bottom):
    """DFR adapter board, 1.6 mm FR4 in front of the DFR1202 (x -37..-35.4). It overlaps the converter's lower 5 mm
    (castellated edge at z -3) and stays inside |y| 11.5 so it passes between the pack lips (|y| >= 11.9) with 0.4 mm."""
    return box([DFR_FRONT, -11.5, z_bottom], [DFR_FRONT + 1.6, 11.5, 2.0])


def tb_rear(n, ztop, yc=0.0):
    """TB0011-350-0n on the adapter's rear face (towards the cover), pin row along y, wire entry facing down (-z),
    screw heads facing the cover. Pin tails 3.4 long: 1.8 mm past the adapter, trimmed flush to 0.3 mm (inference): the OpenRB's stacking sockets sit 0.44 mm in front of the adapter."""
    half = 3.5 * n / 2
    zc = ztop - TB_D / 2
    body = box([DFR_FRONT, yc - half, ztop - TB_D], [DFR_FRONT - TB_H, yc + half, ztop])
    wires = box([DFR_FRONT - 1.0, yc - half, ztop - TB_D], [DFR_FRONT - TB_H + 1.0, yc + half, ztop - TB_D - 4.0])
    py = 3.5 * (n - 1) / 2 + 0.5          # outermost pin centre + 0.5 mm pin half-width
    tails = box([DFR_FRONT + 1.6, yc - py, zc - 0.6], [DFR_FRONT + 1.9, yc + py, zc + 0.6])
    return body, wires, tails


def tb_front(n, ztop, yc=0.0):
    half = 3.5 * n / 2
    body = box([DFR_FRONT + 1.6, yc - half, ztop - TB_D], [DFR_FRONT + 1.6 + TB_H, yc + half, ztop])
    wires = box([DFR_FRONT + 2.6, yc - half, ztop - TB_D], [DFR_FRONT + 1.6 + TB_H - 1.0, yc + half, ztop - TB_D - 4.0])
    zc = ztop - TB_D / 2
    py = 3.5 * (n - 1) / 2 + 0.5
    tails = box([DFR_FRONT, yc - py, zc - 0.6], [DFR_FRONT - 1.0, yc + py, zc + 0.6])   # 1.0 mm on the cover side
    return body, wires, tails


def dfr_rear6():
    """Recommended layout: block top 0.6 mm under the converter's pad edge, inside the pack's DFR pad room
    (pack_lib.DFR_PAD_ROOM, x -45..-37, z -11..-3), adapter ending at z -11.5 so leads can pass under it."""
    b, w, t = tb_rear(6, -3.6)
    return {'adapter board': carrier(-11.5), 'TB0011-350-06 body': b, 'wire entry room': w, 'pin tails (lane side)': t}


def dfr_rear6_low():
    """Variant with the block below the feet (top z -7.6): avoids the feet in the final pose only."""
    b, w, t = tb_rear(6, -7.6)
    return {'adapter board': carrier(-15.0), 'TB0011-350-06 body': b, 'wire entry room': w, 'pin tails (lane side)': t}


def dfr_front6():
    b, w, t = tb_front(6, -3.6)
    return {'adapter board': carrier(-15.0), 'TB0011-350-06 body': b, 'wire entry room': w, 'pin tails (cover side)': t}


def dfr_front4_rear2():
    """Input pair + ORB pair on a 4-pole block on the OpenRB side (y -8.5..5.5, clear of the stacking sockets at
    |y| >= 9), PI pair on a 2-pole block on the cover side, centred, above the feet's reach."""
    b4, w4, t4 = tb_front(4, -3.6, yc=-1.5)
    b2, w2, t2 = tb_rear(2, -3.6, yc=0.0)
    return {'adapter board': carrier(-15.0), 'TB0011-350-04 body (front)': b4, 'front wire entry room': w4,
            'front pin tails (cover side)': t4, 'TB0011-350-02 body (rear)': b2, 'rear wire entry room': w2,
            'rear pin tails (lane side)': t2}


def dfr_carrier_only():
    return {'adapter board': carrier(-15.0)}


CANDIDATES = {
    'J12-PH-top-a': {'board': 'openrb', 'make': lambda: ph_top(+1), 'what': 'JST B4B-PH-K-S top entry + PHR-4, 2.8 mm side towards +z (terminal block)'},
    'J12-PH-top-b': {'board': 'openrb', 'make': lambda: ph_top(-1), 'what': 'JST B4B-PH-K-S top entry + PHR-4, 2.8 mm side towards -z (USB-C)'},
    'J12-PH-side-down': {'board': 'openrb', 'make': lambda: ph_side(-1), 'what': 'JST S4B-PH-K-S side entry, plug from below (-z)'},
    'J12-PH-side-up': {'board': 'openrb', 'make': lambda: ph_side(+1), 'what': 'JST S4B-PH-K-S side entry, plug from above (+z)'},
    'DFR-adapter-only': {'board': 'dfr', 'make': dfr_carrier_only, 'what': 'DFR adapter board alone (1.6 mm, in front of the converter)'},
    'DFR-adapter-TB6-rear': {'board': 'dfr', 'make': dfr_rear6, 'what': 'Adapter + Same Sky TB0011-350-06 on the cover side, top at z -3.6, wires enter from below (recommended layout)'},
    'DFR-adapter-TB6-rear-low': {'board': 'dfr', 'make': dfr_rear6_low, 'what': 'Same, block lowered under the feet (top z -7.6)'},
    'DFR-adapter-TB4-front-TB2-rear': {'board': 'dfr', 'make': dfr_front4_rear2, 'what': 'Adapter + TB0011-350-04 on the OpenRB side (input and ORB pairs) + TB0011-350-02 on the cover side (PI pair)'},
    'DFR-adapter-TB6-front': {'board': 'dfr', 'make': dfr_front6, 'what': 'Adapter + Same Sky TB0011-350-06 on the OpenRB side, wires enter from below'},
}

# Rigid parts the envelopes must clear. The board's own PCB is excluded for J12 (the header sits on it); its components
# above the copper face are kept.
CABLE_R = {'uart_lower': 0.7, 'openrbpwr': 1.0, 'trunk': 1.0, 'vin20': 1.2, 'dxl5': 1.1, 'dxl10': 1.1, 'dxl12': 1.1, 'imu': 0.8}


# Rooms the pack reserves (rear-pack/pack_lib.py). The DFR pad room is where the converter leads go, so the DFR
# candidates may use it; the others must stay clear.
ROOMS = {'ROOM_LEG_PLUGS': ([-42.45, -4.3, -27.75], [-32.45, 3.6, -17.75]),
         'ROOM_NECK_PLUG': ([-30.65, 12.4, -27.75], [-26.45, 22.4, -17.75]),
         'ROOM_TERMINAL': ([-34.7, -4.7, 24.9], [-22.4, 4.8, 32.9]),
         'ROOM_USB': ([-31.4, -7.3, -57.0], [-23.9, 6.7, -42.0])}


# Not present during the board / converter drop-in (rear-pack/check_assembly.py: shells off, cover after).
LATER = {'shell_left', 'shell_right', 'rear_pack_cover', 'regulator', 'imu_board', 'imu_sh4_receiving', 'xt30_robot'}


def load_parts():
    man = ia_lib.manifest()
    pack_lo = np.array(man['rear_pack']['bounds'][0]) - 8
    pack_hi = np.array(man['rear_pack']['bounds'][1]) + 8
    parts = {}
    for key, rec in man.items():
        lo, hi = np.array(rec['bounds'][0]), np.array(rec['bounds'][1])
        if np.all(hi >= pack_lo) and np.all(lo <= pack_hi):
            parts[key] = ia_lib.to_manifold(*ia_lib.load_solid(key))
    comp = parts['openrb_board'] ^ box([PCB_FACE - 0.001, -40, -80], [-80, 40, 80])   # component side only
    parts['openrb_board (components)'] = comp
    parts['openrb_board (whole, incl. PCB)'] = parts.pop('openrb_board')
    return parts


def seg_box_distance(points, lo, hi, n=40):
    """Minimum distance from a polyline to an axis-aligned box (dense sampling of the polyline, 0.05 mm or finer)."""
    best = 1e9
    for a, b in zip(points[:-1], points[1:]):
        a, b = np.asarray(a, float), np.asarray(b, float)
        k = max(n, int(np.linalg.norm(b - a) / 0.05) + 1)
        t = np.linspace(0, 1, k)[:, None]
        p = a + t * (b - a)
        d = np.linalg.norm(np.maximum(np.maximum(lo - p, 0), p - hi), axis=1)
        best = min(best, float(d.min()))
    return best


def check(env: dict, parts: dict, skip=()):
    out = {}
    for name, solid in parts.items():
        if name in skip:
            continue
        per = {}
        for ek, e in env.items():
            inter = e ^ solid
            ov = inter.volume()
            gap = e.min_gap(solid, SEARCH)
            per[ek] = {'overlapMm3': round(ov, 3), 'minGapMm': round(gap, 3) if gap < SEARCH else f'>{SEARCH:g}'}
            if ov > 1e-6:
                bb = np.asarray(inter.bounding_box())
                per[ek]['overlapBox'] = [ia_lib.rnd(list(bb[:3])), ia_lib.rnd(list(bb[3:]))]
                per[ek]['overlapExtentMm'] = ia_lib.rnd(list(bb[3:] - bb[:3]))
        worst_gap = min((v['minGapMm'] for v in per.values() if not isinstance(v['minGapMm'], str)), default=None)
        worst_ov = max(v['overlapMm3'] for v in per.values())
        if worst_ov > 0 or worst_gap is not None:
            out[name] = {'overlapMm3': round(worst_ov, 3), 'minGapMm': worst_gap, 'byEnvelope': per}
    return out


def sweep(env: dict, path):
    """Swept volume of a pure translation path: hull of each box over consecutive path points."""
    pieces = []
    for e in env.values():
        for a, b in zip(path[:-1], path[1:]):
            pieces.append(m3.Manifold.batch_hull([e.translate(list(a)), e.translate(list(b))]))
    return {'swept': union(pieces)}


def summarise(res, ignore=()):
    ov = {k: {'overlapMm3': v['overlapMm3'],
              'overlapBoxes': [e['overlapBox'] for e in v['byEnvelope'].values() if 'overlapBox' in e]}
          for k, v in res.items() if v['overlapMm3'] > 0 and k not in ignore}
    gaps = [(v['minGapMm'], k) for k, v in res.items() if v['minGapMm'] is not None and k not in ignore]
    mg = min(gaps) if gaps else (None, None)
    return {'overlaps': ov, 'minGapMm': mg[0], 'minGapPart': mg[1], 'fits': not ov,
            'gapsByPart': {k: v['minGapMm'] for k, v in res.items() if k not in ignore}}


def main():
    parts = load_parts()
    j12 = j12_holes()
    routes = json.loads((REPO / 'microduck-sim/guide/content/routes.json').read_text())['routes']
    res = {'frame': 'robot frame, mm (x forward, y left, z up)', 'searchMm': SEARCH,
           'j12Measured': j12, 'partsChecked': sorted(parts), 'candidates': {}}
    for cid, c in CANDIDATES.items():
        env = c['make']()
        skip = ('openrb_board (whole, incl. PCB)',) if c['board'] == 'openrb' else ('openrb_board (components)', 'regulator')
        static = check(env, parts, skip)
        rec = {'what': c['what'],
               'envelopes': {k: [ia_lib.rnd(list(np.asarray(v.bounding_box()[:3]))), ia_lib.rnd(list(np.asarray(v.bounding_box()[3:])))]
                             for k, v in env.items()},
               'static': static, 'staticSummary': summarise(static)}
        # Cable clearance (flexible parts, information only): distance from each envelope box to each torso centreline
        # minus the cable radius. The UART route starts at the old J12 joint and is replaced, so it is skipped for J12.
        cab = {}
        for rid, r in CABLE_R.items():
            if rid not in routes or (c['board'] == 'openrb' and rid == 'uart_lower'):
                continue
            d = min(seg_box_distance(routes[rid], np.asarray(v.bounding_box()[:3]), np.asarray(v.bounding_box()[3:])) for v in env.values())
            cab[rid] = round(d - r, 2)
        rec['cableClearanceMm'] = cab
        rec['packRooms'] = summarise(check(env, {k: box(*v) for k, v in ROOMS.items()}))
        if c['board'] == 'openrb':
            # The pack's board path: drop in 30 mm at x -3, then move +3 onto the pads (rear-pack README check 6).
            # Two cases: header only (plug added after mounting) and header with the plug and wires already on.
            path = [(-3.0, 0, 30.0), (-3.0, 0, 0.0), (0.0, 0, 0.0)]
            hdr = {k: v for k, v in env.items() if k in ('body+plug', 'header', 'pin tails (board back)')}
            # Obstacles as in rear-pack/check_assembly.py: pack body and torso parts, shells off; the pack's own
            # later parts (cover, converter, IMU, XT30) are not in yet.
            env_parts = {k: v for k, v in parts.items() if not k.startswith('openrb_board') and k not in LATER}
            rec['boardInsertion'] = {
                'path': path, 'note': 'DFR1202 not yet fitted (it goes in after the board); board itself moves with the header.',
                'withPlugAndWires': summarise(check(sweep(env, path), env_parts)),
                'headerOnly': summarise(check(sweep(hdr, path), env_parts)),
            }
        else:
            # The converter drops in from above (35 mm) before the cover goes on (rear-pack README check 6). The
            # converter box moves with the adapter. Cover excluded (fitted afterwards).
            reg = parts['regulator']
            env2 = dict(env, **{'DFR1202 box': reg})
            path = [(0, 0, 35.0), (0, 0, 0.0)]
            env_parts = {k: v for k, v in parts.items() if k not in LATER and k != 'openrb_board (components)'}
            rec['dfrInsertionFromAbove'] = summarise(check(sweep(env2, path), env_parts))
        if cid == 'DFR-adapter-TB6-rear':
            body = env['TB0011-350-06 body']
            ed = {}
            cov = body ^ parts['rear_pack_cover']
            if cov.volume() > 0:
                bb = np.asarray(cov.bounding_box())
                ed['coverPocket'] = {'box': [ia_lib.rnd(list(bb[:3])), ia_lib.rnd(list(bb[3:]))],
                                     'depthMm': round(float(bb[3] - bb[0]), 3)}
            for side, half in (('+y', box([-80, 0, -80], [0, 40, 80])), ('-y', box([-80, -40, -80], [0, 0, 80]))):
                swept = sweep({'b': body}, [(0, 0, 35.0), (0, 0, 0.0)])['swept']
                f = swept ^ parts['rear_pack'] ^ half
                if f.volume() > 0:
                    bb = np.asarray(f.bounding_box())
                    ed[f'foot{side}'] = {'box': [ia_lib.rnd(list(bb[:3])), ia_lib.rnd(list(bb[3:]))],
                                         'trimAlongYMm': round(float(bb[4] - bb[1]), 3)}
            rec['packEditsNeeded'] = ed
        res['candidates'][cid] = rec
    summ = {}
    for cid, rec in res['candidates'].items():
        ins = rec.get('boardInsertion', {}).get('withPlugAndWires') or rec.get('dfrInsertionFromAbove')
        summ[cid] = {'staticFits': rec['staticSummary']['fits'], 'staticMinGapMm': rec['staticSummary']['minGapMm'],
                     'staticMinGapPart': rec['staticSummary']['minGapPart'],
                     'staticOverlaps': {k: v['overlapMm3'] for k, v in rec['staticSummary']['overlaps'].items()},
                     'insertionFits': ins['fits'], 'insertionMinGapMm': ins['minGapMm'],
                     'insertionOverlaps': {k: v['overlapMm3'] for k, v in ins['overlaps'].items()},
                     'packRoomsClear': rec['packRooms']['fits'],
                     'packEditsNeeded': rec.get('packEditsNeeded')}
    res['summary'] = summ
    # The two recommended changes together: J12 header + plug next to the converter adapter and its block.
    a, b = CANDIDATES['J12-PH-top-b']['make'](), CANDIDATES['DFR-adapter-TB6-rear']['make']()
    pair = {}
    for ka, ea in a.items():
        for kb, eb in b.items():
            g = ea.min_gap(eb, SEARCH)
            pair[f'{ka} | {kb}'] = {'overlapMm3': round((ea ^ eb).volume(), 3), 'minGapMm': round(g, 3) if g < SEARCH else f'>{SEARCH:g}'}
    res['recommendedPairJ12vsDfrAdapter'] = pair
    out = HERE / 'fit-results.json'
    out.write_text(json.dumps(res, indent=1) + '\n')
    for cid, rec in res['candidates'].items():
        extra = rec.get('boardInsertion') or rec.get('dfrInsertionFromAbove')
        print(cid, json.dumps(rec['staticSummary']), '| insertion:', json.dumps(extra)[:400])
    print('J12 rows found:', j12)


if __name__ == '__main__':
    main()
