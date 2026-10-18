#!/usr/bin/env python3
"""Find every screw-sized hole in the current printed MicroDuck parts and say whether the build guide screws it.

Problem P5 (MicroDuck physical build). Read-only on every guide, print and step source; writes only into this folder
and a work cache (UH_WORK, default: the session scratchpad named below).

Stages (all run by default; `--stage` picks one, earlier results are read from the work cache):
  detect    section each printed part on planes normal to x, y and z every 0.25 mm, keep circular interiors
            (circularity > 0.85, area-equivalent diameter 1.2-6.5 mm), link them across slices into tracks and merge
            coaxial tracks into hole axes (bore and counterbore segments, tilt-corrected diameters).
  probe     for every hole axis, intersect each nearby assembled part with a 3.5 mm radius cylinder on the axis that
            reaches 15 mm past both hole ends, slice it every 0.1 mm and record per part whether the axis is in
            material, in an enclosed coaxial hole (with its radius) or free.
  classify  a = a guide screw lies on the axis (line distance < 0.5 mm, parallel within 8 deg, shank overlaps the
            hole span); a-upstream = only a leg-guide screw does (legs built before this guide);
            b = no screw, and an open end of the hole faces a coaxial hole in another part on the same rigid body
            within 15 mm with nothing in between: CANDIDATE MISSING SCREW;
            c = no screw and no partner hole (nothing in front, or a plain face);
            d = documented other purpose (tie slot, cable hole, retired mount, ...) or a coaxial alignment across a
            moving joint (a screw would lock the joint).
  clear     for every b joint: grip, pilot depth and the stocked TAP screw that fits; the screw head (dia 4.0 x 1.5 mm
            cylinder on the entry face) against every part at the zero pose and against the parts on the far side of
            each joint between the head and them, swept over the robot_allcollisions.xml joint ranges.

Run (bounded runner, one job at a time):
  R=microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py
  /tmp/microduck-cad-venv/bin/python $R --max-mib 1536 --seconds 1800 --wait-lock-seconds 60 --report run.json -- \
    /tmp/microduck-cad-venv/bin/python -I unscrewed_holes.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from ia_lib import CACHE, GUIDE, GUIDE_DATA, SIM, load_solid, manifest, rnd  # noqa: E402

WORK = Path(os.environ.get('UH_WORK', '/private/tmp/claude-501/-Users-xiangzheng-code-robotics/'
                                      '489bc788-e1d1-48fa-9db3-43edcefdef75/scratchpad/uh-work'))
WORK.mkdir(parents=True, exist_ok=True)
OUT = HERE / 'unscrewed-holes.json'
TAG = ''
UPSTREAM = SIM / 'build-pack-20260913' / 'redesign-20260913' / 'leg-guide-20261006' / 'full-build-data-current.json'
FASTENERS = GUIDE / 'content' / 'fasteners.json'
FEATURES = GUIDE / 'print' / 'rear-pack' / 'features.json'
MJCF = SIM / 'microduck-simulator' / 'app' / 'public' / 'robot' / 'mjlab' / 'robot_allcollisions.xml'

RETIRED = {'power_support', 'regulator_insert', 'openrb_tray', 'fuse_main', 'imu_clamp', 'imu_cover', 'junction_j'}
PRINT_COLORS = {'#ff8000', '#202020', '#ffff00', '#e99436', '#292b30', '#edc447', '#e9e7df'}

STEP = 0.25          # detection slice spacing (mm)
CIRC_MIN = 0.85
SWEEPS = {'x': (1, 0, 0), 'y': (0, 1, 0), 'z': (0, 0, 1)}
# Sensitivity sweeps (--sensitivity): diagonal planes catch bores tilted towards 45 deg; lower circularity catches
# teardrop or coarse polygon bores.
DIAG_SWEEPS = {'xy+': (1, 1, 0), 'xy-': (1, -1, 0), 'xz+': (1, 0, 1), 'xz-': (1, 0, -1), 'yz+': (0, 1, 1),
               'yz-': (0, 1, -1)}
D_DETECT = (1.2, 6.5)
D_BORE = (1.5, 3.5)  # screw-sized bore (task range)
LINK_TOL = 0.35      # centroid move between slices for one track (mm)
REACH = 15.0         # probe reach past each hole end (mm)
PROBE_R = 3.5        # probe cylinder radius (mm)
PSTEP = 0.1          # probe slice spacing (mm)
STOCK = [('M2', 4), ('M2', 6), ('M2', 7), ('M2', 8), ('M2', 10), ('M2.5', 6), ('M2.5', 8), ('M2.6', 6)]
HEAD_D, HEAD_H = 4.0, 1.5
TIP_LEADIN = 0.3

# Rigid bodies of robot_allcollisions.xml that carry each guide part (motor = its case; horn holes belong to HORN_BODY).
BODY = {}
for _b, _keys in {
    'trunk_base': ['torso_base', 'shell_left', 'shell_right', 'ring10_torso', 'ring5_torso', 'rear_pack',
                   'rear_pack_cover', 'motor10', 'motor5', 'openrb_board', 'regulator', 'imu_board',
                   'imu_sh4_receiving', 'xt30_robot', 'idler12'],
    'neck': ['motor12', 'neck_link_a', 'neck_link_b', 'motor11', 'idler_cap12', 'idler_cap11'],
    'neck_pitch': ['neck_pitch', 'neck_pitch_ring', 'idler11'],
    'yaw_roll_motion': ['head_yaw_link', 'motor13', 'head_roll_ring_a', 'head_roll_ring_b'],
    'jaw_soft': ['motor14', 'jaw_support', 'motor15', 'head_bottom', 'head_cap', 'face_panel', 'eye_trim',
                 'camera_board', 'pi', 'mouth_sliding_ring'],
    'jaw': ['jaw_frame'],
    'yaw2roll': ['yaw', 'passive', 'motor9', 'washer9', 'ring9'],
    'hip_l': ['hip', 'ring8'],
    'upper_leg_left': ['thigh', 'plate', 'motor8', 'motor7', 'ring7'],
    'leg': ['lower', 'motor6', 'smallring', 'washer6'],
    'ankle_left': ['ankle', 'foot'],
    'bearing_roll': ['right_yaw', 'right_passive', 'motor4', 'washer4', 'ring4'],
    'hip_l_2': ['right_hip', 'ring3'],
    'upper_leg_right': ['right_thigh', 'right_plate', 'motor3', 'motor2', 'ring2'],
    'leg_2': ['right_lower', 'motor1', 'right_smallring', 'washer1'],
    'ankle_right': ['right_ankle', 'right_foot'],
}.items():
    for _k in _keys:
        BODY[_k] = _b
# Output horn of each motor: (joint, body the horn turns with). motor12/13/14 sit with their case on the child body.
HORN = {'motor10': ('left_hip_yaw', 'yaw2roll'), 'motor9': ('left_hip_roll', 'hip_l'),
        'motor8': ('left_hip_pitch', 'hip_l'), 'motor7': ('left_knee', 'leg'), 'motor6': ('left_ankle', 'ankle_left'),
        'motor5': ('right_hip_yaw', 'bearing_roll'), 'motor4': ('right_hip_roll', 'hip_l_2'),
        'motor3': ('right_hip_pitch', 'hip_l_2'), 'motor2': ('right_knee', 'leg_2'),
        'motor1': ('right_ankle', 'ankle_right'), 'motor12': ('neck_pitch', 'trunk_base'),
        'motor11': ('head_pitch', 'neck_pitch'), 'motor13': ('head_yaw', 'neck_pitch'),
        'motor14': ('head_roll', 'yaw_roll_motion'), 'motor15': ('jaw', 'jaw')}
# The jaw (ID15) has no joint in robot_allcollisions.xml; its axis is the ID15 horn axis from the guide's jaw screws.
JAW_JOINT = {'name': 'jaw', 'parent': 'jaw_soft', 'child': 'jaw', 'anchor': [26.1, 0.0, 118.615], 'axis': [0, 1, 0],
             'range': [-0.70, 0.0], 'note': 'not in robot_allcollisions.xml; axis from the S15-horn screws, range '
                                             'assumed 0 to 40 deg open (fastener-audit/jaw_access.py: the jaw meets the '
                                             'lower shell at about 40 deg)'}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def jdump(path: Path, obj):
    path.write_text(json.dumps(obj, indent=1))


# --------------------------------------------------------------------------------------------- parts and screws
def guide_parts():
    g = json.loads(GUIDE_DATA.read_text())
    parts = {p['key']: p for p in g['parts']}
    shown = set()
    for s in g['steps']:
        shown |= set(s.get('show', [])) | set(s.get('add', []))
    # The legs and other modules are shown by module name in some steps.
    mods = {}
    for k, p in parts.items():
        mods.setdefault(p.get('module'), set()).add(k)
    for s in g['steps']:
        for x in s.get('show', []):
            if x in mods:
                shown |= mods[x]
    assembled = sorted(k for k in parts if k in shown and k not in RETIRED)
    printed = sorted(k for k in assembled if (parts[k].get('color') or '').lower() in PRINT_COLORS
                     and not k.startswith('motor') and not k.startswith('washer'))
    return g, parts, assembled, printed


def guide_screws(g):
    out = []
    for s in g['screws']:
        out.append({'id': s['id'], 'src': 'guide', 'step': s['step'], 'spec': s['spec'], 'L': float(s['lengthMm']),
                    'center': np.array(s['center'], float), 'axis': np.array(s['axis'], float) /
                    np.linalg.norm(s['axis']), 'through': s.get('throughPart'), 'into': s.get('intoPart')})
    return out


def upstream_screws():
    d = json.loads(UPSTREAM.read_text())
    out = []
    for s in d['screws']:
        if s.get('world_center_mm') is None or s.get('world_axis') is None:
            continue
        ax = -np.array(s['world_axis'], float)  # source world_axis points against the direction of travel
        out.append({'id': s['id'], 'src': 'leg-guide', 'step': s.get('moduleId'), 'spec': s.get('spec'),
                    'L': float(s.get('length_mm') or 6), 'center': np.array(s['world_center_mm'], float),
                    'axis': ax / np.linalg.norm(ax), 'through': s.get('component'), 'into': s.get('partKey')})
    return out


# --------------------------------------------------------------------------------------------- stage 1: detect
def frame(a):
    a = np.asarray(a, float); a = a / np.linalg.norm(a)
    h = np.array([1.0, 0, 0]) if abs(a[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(a, h); u /= np.linalg.norm(u)
    return u, np.cross(a, u), a


def detect_part(key, sweeps=None, circ_min=None):
    import trimesh
    from shapely.geometry import Polygon
    v, f = load_solid(key)
    m = trimesh.Trimesh(v, f, process=False)
    tracks = []
    sweeps = sweeps or SWEEPS
    circ_min = CIRC_MIN if circ_min is None else circ_min
    for ai, nv in sweeps.items():
        n = np.asarray(nv, float); n = n / np.linalg.norm(n)
        proj = m.vertices @ n
        lo, hi = proj.min(), proj.max()
        hs = np.arange(lo + STEP / 2, hi, STEP)
        secs = m.section_multiplane(plane_origin=np.zeros(3), plane_normal=n, heights=hs)
        open_t = []
        for h, s in zip(hs, secs):
            found = []
            if s is not None:
                T = s.metadata['to_3D']
                for poly in s.polygons_full:
                    for ring in poly.interiors:
                        p = Polygon(ring)
                        A, P = p.area, p.length
                        if A <= 0 or P <= 0:
                            continue
                        d = 2 * math.sqrt(A / math.pi)
                        circ = 4 * math.pi * A / (P * P)
                        if D_DETECT[0] <= d <= D_DETECT[1] and circ > circ_min:
                            c = (T @ [p.centroid.x, p.centroid.y, 0, 1])[:3]
                            found.append((c, d, circ))
            nxt = []
            for c, d, circ in found:
                best = None
                for i, t in enumerate(open_t):
                    dist = np.linalg.norm(c - t['c'][-1] - n * (h - t['h'][-1]))
                    if dist < LINK_TOL and (best is None or dist < best[0]):
                        best = (dist, i)
                if best:
                    t = open_t.pop(best[1])
                else:
                    t = {'ax': ai, 'n': n, 'h': [], 'c': [], 'd': [], 'circ': []}; tracks.append(t)
                t['h'].append(float(h)); t['c'].append(c); t['d'].append(d); t['circ'].append(circ)
                nxt.append(t)
            open_t = nxt
    return [t for t in tracks if len(t['h']) >= 2]


def fit_line(pts, fallback):
    pts = np.asarray(pts)
    c = pts.mean(0)
    if len(pts) < 3 or np.ptp(pts, 0).max() < 0.6:
        return c, np.asarray(fallback, float)
    _, _, vt = np.linalg.svd(pts - c)
    a = vt[0]
    if a @ fallback < 0:
        a = -a
    # Accept the fitted direction only when it stays near the section normal (tilted holes); else the normal.
    if a @ fallback < math.cos(math.radians(50)):
        a = np.asarray(fallback, float)
    return c, a / np.linalg.norm(a)


def merge_axes(key, tracks):
    """Coaxial tracks (any sweep) -> one hole axis with segments along it."""
    items = []
    for t in tracks:
        n = t['n']
        c, a = fit_line(t['c'], n)
        cosang = abs(a @ n)
        dcorr = [d * math.sqrt(cosang) for d in t['d']]  # ellipse of a tilted bore -> true diameter
        s = [float((np.asarray(p) - c) @ a) for p in t['c']]
        items.append({'c': c, 'a': a, 'sweep': t['ax'], 'cos': cosang, 'smin': min(s) - STEP / 2,
                      'smax': max(s) + STEP / 2, 'd': dcorr, 's': s, 'circ': t['circ']})
    groups = []
    for it in items:
        for g in groups:
            a = g[0]['a']
            if abs(it['a'] @ a) < math.cos(math.radians(8)):
                continue
            dvec = it['c'] - g[0]['c']
            if np.linalg.norm(dvec - (dvec @ a) * a) < 0.35:
                g.append(it); break
        else:
            groups.append([it])
    holes = []
    for g in groups:
        # Prefer the sweep whose plane normal is closest to the axis (truest circles); others only confirm.
        best = max(g, key=lambda it: (round(it['cos'], 2), it['smax'] - it['smin']))
        a = best['a']; c0 = best['c']
        segs = []
        for it in g:
            if it['cos'] < best['cos'] - 0.05:
                continue  # oblique sweep of the same bore
            off = float((it['c'] - c0) @ a)
            for s, d, ci in zip(it['s'], it['d'], it['circ']):
                segs.append((s + off, d, ci))
        segs.sort()
        # dedupe slices from equal sweeps
        prof = []
        for s, d, ci in segs:
            if prof and abs(s - prof[-1][0]) < STEP * 0.4:
                continue
            prof.append((s, d, ci))
        holes.append({'part': key, 'c': c0, 'a': a, 'sweep': best['sweep'], 'profile': prof})
    return holes


def split_segments(prof):
    """Runs of nearly constant diameter along the axis (gaps > 0.6 mm or diameter jumps > 0.3 mm split)."""
    runs = []
    for s, d, ci in prof:
        if runs and s - runs[-1][-1][0] <= STEP * 2.4 and abs(d - np.median([x[1] for x in runs[-1]])) <= 0.3:
            runs[-1].append((s, d, ci))
        else:
            runs.append([(s, d, ci)])
    segs = []
    for r in runs:
        ds = np.array([x[1] for x in r])
        segs.append({'s0': r[0][0] - STEP / 2, 's1': r[-1][0] + STEP / 2, 'dMm': float(np.median(ds)),
                     'dMin': float(ds.min()), 'dMax': float(ds.max()), 'n': len(r),
                     'circ': float(np.median([x[2] for x in r]))})
    return segs


def stage_detect(printed, sensitivity=False):
    t0 = time.time()
    res = {}
    for key in printed:
        if sensitivity:
            tr = detect_part(key, {**SWEEPS, **DIAG_SWEEPS}, 0.70)
        else:
            tr = detect_part(key)
        holes = merge_axes(key, tr)
        keep = []
        for h in holes:
            segs = split_segments(h['profile'])
            bores = [s for s in segs if D_BORE[0] - 0.3 <= s['dMm'] <= D_BORE[1] + 0.1]
            if not bores:
                continue
            # Orthogonal-sweep artefact: a "bore" shorter than 0.5 mm seen only on a side sweep.
            if max(s['s1'] - s['s0'] for s in bores) < 0.45:
                continue
            keep.append({'part': key, 'center': h['c'].tolist(), 'axis': h['a'].tolist(), 'sweep': h['sweep'],
                         'segments': segs})
        res[key] = keep
        print(f'detect {key}: {len(tr)} tracks, {len(keep)} screw-sized hole axes ({time.time() - t0:.1f} s)',
              flush=True)
    jdump(WORK / f'detect{TAG}.json', res)
    return res


# --------------------------------------------------------------------------------------------- stage 2: probe
_MAN: dict = {}


def part_manifold(key):
    if key not in _MAN:
        from ia_lib import to_manifold
        v, f = load_solid(key)
        _MAN[key] = (to_manifold(v, f), v.min(0), v.max(0))
    return _MAN[key]


def contour_state(polys):
    """State of the axis point (0, 0) in one probe slice: S material, H enclosed hole (area-equivalent diameter),
    O material within the probe radius but not around the axis (2 x distance to it), - nothing."""
    if not polys:
        return '-', 0.0
    wtot = 0
    rmin = np.inf
    encl = []
    for P in polys:
        P = np.asarray(P, float)
        if len(P) < 3:
            continue
        x1, y1 = P[:, 0], P[:, 1]
        x2, y2 = np.roll(x1, -1), np.roll(y1, -1)
        isl = (x2 - x1) * (-y1) - (-x1) * (y2 - y1)
        w = int(np.sum((y1 <= 0) & (y2 > 0) & (isl > 0)) - np.sum((y2 <= 0) & (y1 > 0) & (isl < 0)))
        wtot += w
        ex, ey = x2 - x1, y2 - y1
        L2 = ex * ex + ey * ey
        t = np.clip(np.where(L2 > 0, -(x1 * ex + y1 * ey) / np.where(L2 > 0, L2, 1), 0), 0, 1)
        rmin = min(rmin, float(np.sqrt(((x1 + t * ex) ** 2 + (y1 + t * ey) ** 2).min())))
        if w != 0:
            area = 0.5 * float(np.sum(x1 * y2 - x2 * y1))
            encl.append(area)
    if wtot != 0:
        return 'S', 0.0
    holes = [-a for a in encl if a < 0]
    if holes:
        return 'H', 2 * math.sqrt(min(holes) / math.pi)
    return 'O', 2 * rmin


def rle(z, st, d):
    runs = []
    for zi, si, di in zip(z, st, d):
        if runs and runs[-1][2] == si and (si in 'S-' or abs(di - runs[-1][4][0]) <= 0.2):
            runs[-1][1] = zi; runs[-1][4].append(di)
        else:
            runs.append([zi, zi, si, None, [di]])
    out = []
    for z0, z1, si, _, ds in runs:
        out.append([round(z0 - PSTEP / 2, 3), round(z1 + PSTEP / 2, 3), si, round(float(np.median(ds)), 3),
                    round(float(min(ds)), 3)])
    return out


def probe_axis(hax, assembled):
    import manifold3d as m3
    c = np.array(hax['center']); a = np.array(hax['axis'])
    u, v, a = frame(a)
    s_lo = min(s['s0'] for s in hax['segments']); s_hi = max(s['s1'] for s in hax['segments'])
    z0, z1 = s_lo - REACH - 1.0, s_hi + REACH + 1.0
    R = np.stack([u, v, a])  # rows: world -> local
    M = np.zeros((3, 4), np.float32); M[:, :3] = R; M[:, 3] = -R @ c
    cyl = m3.Manifold.cylinder(z1 - z0, PROBE_R, -1, 48, False).translate((0, 0, z0))
    p0, p1 = c + a * z0, c + a * z1
    lo = np.minimum(p0, p1) - PROBE_R; hi = np.maximum(p0, p1) + PROBE_R
    zs = np.arange(z0 + PSTEP / 2, z1, PSTEP)
    prof = {}
    for q in assembled:
        man, qlo, qhi = part_manifold(q)
        if np.any(qhi < lo) or np.any(qlo > hi):
            continue
        inter = man.transform(M) ^ cyl
        if inter.is_empty():
            continue
        st, dd = [], []
        for z in zs:
            s, d = contour_state(inter.slice(float(z)).to_polygons())
            st.append(s); dd.append(d)
        if all(s == '-' for s in st):
            continue
        prof[q] = rle(zs, st, dd)
    return prof


def other_solids(assembled):
    """Cached solids of parts that are not in the current build (retired, deferred or superseded), used only to
    explain holes that no current part uses."""
    have = {p.stem[len('solid-'):] for p in CACHE.glob('solid-*.npz')}
    return sorted(k for k in have - set(assembled) if not k.startswith('head_pi_'))


def stage_probe(assembled, detect):
    t0 = time.time()
    out = []
    n = sum(len(v) for v in detect.values())
    extra = other_solids(assembled)
    for key, hs in detect.items():
        for h in hs:
            prof = probe_axis(h, assembled)
            prof_x = probe_axis(h, extra)
            out.append({**h, 'probe': prof, 'probeOther': prof_x})
            print(f'probe {len(out)}/{n} {key} {rnd(h["center"])} {sorted(prof)} ({time.time() - t0:.0f} s)',
                  flush=True)
    jdump(WORK / f'probe{TAG}.json', out)
    return out


# --------------------------------------------------------------------------------------------- stage 3: classify
D_SCREWSIZED = 3.6   # a partner opening up to this diameter is a screw hole (pilot, case bore or clearance)
D_SHANK = 2.0        # material closer than 1.0 mm to the axis blocks an M2 shank


def runs_at(runs, z):
    for r in runs:
        if r[0] <= z < r[1]:
            return r
    return None


def own_holes(hax):
    """Split one probed hole axis into holes: enclosed runs of the own part that contain a bore. A gap of at most
    0.6 mm where the bore breaks out sideways (open, not solid) stays inside one hole."""
    runs = hax['probe'].get(hax['part'], [])
    seqs, cur, gap = [], [], []
    for r in runs:
        if r[2] == 'H' and r[3] <= D_DETECT[1]:
            if cur and abs((gap[-1][1] if gap else cur[-1][1]) - r[0]) > 1e-6:
                seqs.append(cur); cur = []
            cur.extend(gap); gap = []
            cur.append(r)
        elif cur and r[2] in 'O-' and r[1] - r[0] <= 0.6 + 1e-6 and not gap:
            gap = [r]
        else:
            if cur:
                seqs.append(cur); cur = []
            gap = []
    if cur:
        seqs.append(cur)
    holes = []
    for sq in seqs:
        hs = [r for r in sq if r[2] == 'H']
        bore = [r for r in hs if D_BORE[0] - 0.3 <= r[3] <= D_BORE[1] + 0.1]
        blen = sum(r[1] - r[0] for r in bore)
        if blen < 0.3:
            continue
        z0, z1 = sq[0][0], sq[-1][1]
        d = float(np.average([r[3] for r in bore], weights=[r[1] - r[0] for r in bore]))
        # Taper: a cone (diameter changing steadily along the bore) is a pit or countersink, not a screw bore.
        zb = np.array([(r[0] + r[1]) / 2 for r in bore]); db = np.array([r[4] if len(r) > 4 else r[3] for r in bore])
        taper = float(np.polyfit(zb, db, 1)[0]) if len(bore) >= 3 and np.ptp(zb) > 0.3 else 0.0
        before = runs_at(runs, z0 - PSTEP / 2)
        after = runs_at(runs, z1 + PSTEP / 2)
        holes.append({'z0': z0, 'z1': z1, 'dMm': round(d, 2), 'boreLenMm': round(blen, 2),
                      'dRangeMm': [round(min(r[3] for r in bore), 2), round(max(r[3] for r in bore), 2)],
                      'taperMmPerMm': round(taper, 2),
                      'runs': [[r[0], r[1], r[3], r[2]] for r in sq],
                      'endLo': before[2] if before else '-', 'endHi': after[2] if after else '-'})
    return holes


def match_screws(c, a, z0, z1, screws):
    hits = []
    mid = c + a * (z0 + z1) / 2
    for s in screws:
        if abs(s['axis'] @ a) < math.cos(math.radians(8)):
            continue
        w = mid - s['center']
        if np.linalg.norm(w - (w @ s['axis']) * s['axis']) > 0.5:
            continue
        ta = (s['center'] - c) @ a
        tb = (s['center'] + s['axis'] * s['L'] - c) @ a
        lo, hi = min(ta, tb), max(ta, tb)
        if hi >= z0 - 0.5 and lo <= z1 + 0.5:
            hits.append(s)
    return hits


def body_of(part, at=None):
    """Rigid body of a part; a motor's horn holes turn with HORN body."""
    b = BODY.get(part, '?')
    if part in HORN and at is not None and HORN_GEOM.get(part):
        anchor, axis, hc = HORN_GEOM[part]
        w = np.asarray(at) - anchor
        r = np.linalg.norm(w - (w @ axis) * axis)
        if 3.5 <= r <= 8.5 and abs((w - hc) @ axis) < 6.0:
            return HORN[part][1]
    return b


HORN_GEOM: dict = {}


def horn_geometry(screws, joints):
    """Horn face centre of each motor from the horn screws (guide or leg guide) and its joint axis."""
    for mkey, (jn, _) in HORN.items():
        if jn == 'jaw':
            j = JAW_JOINT
            anchor, axis = np.array(j['anchor'], float), np.array(j['axis'], float)
        elif jn in joints:
            anchor, axis = joints[jn]['anchor'], joints[jn]['axis']
        else:
            continue
        hs = [s for s in screws if s['into'] == mkey and '-horn-' in s['id']]
        if not hs:
            continue
        hc = np.mean([s['center'] + s['axis'] * min(s['L'], 3.0) for s in hs], 0)
        hc = anchor + ((hc - anchor) @ axis) * axis
        HORN_GEOM[mkey] = (anchor, axis, hc)


def walk(hax, z_start, direction, own):
    """Walk from a hole end along the axis; return what the screw path meets first."""
    prof = hax['probe']
    zs = np.arange(z_start + direction * PSTEP / 2, z_start + direction * (REACH + PSTEP / 2), direction * PSTEP)
    passed = []
    for z in zs:
        dist = abs(z - z_start)
        hits = {q: runs_at(r, z) for q, r in prof.items()}
        hits = {q: r for q, r in hits.items() if r is not None and r[2] != '-'}
        solid = [q for q, r in hits.items() if r[2] == 'S']
        if solid:
            return {'kind': 'face', 'part': solid[0], 'distMm': round(dist - PSTEP / 2, 2), 'passed': passed}
        small = [(q, r) for q, r in hits.items() if r[2] == 'H' and r[3] <= D_SCREWSIZED and q != own]
        if small:
            q, r = small[0]
            # extent of the partner hole along the walk
            zz = z; zend = None; dd = []
            while abs(zz - z_start) <= REACH + 6:
                rr = runs_at(prof[q], zz)
                if rr is None or rr[2] != 'H' or rr[3] > D_SCREWSIZED + 0.6:
                    zend = zz; break
                dd.append((rr[3], rr[1] - rr[0])); zz += direction * PSTEP
            zend = zend if zend is not None else zz
            beyond = runs_at(prof[q], zend)
            depth = abs(zend - z) + PSTEP / 2
            return {'kind': 'partner', 'part': q, 'distMm': round(dist - PSTEP / 2, 2),
                    'zIn': round(z - direction * PSTEP / 2, 2), 'zOut': round(zend - direction * PSTEP / 2, 2),
                    'depthMm': round(depth, 2), 'dMm': round(r[3], 2),
                    'farEnd': beyond[2] if beyond else '-', 'passed': passed}
        if own in hits and hits[own][2] == 'H' and hits[own][3] <= D_SCREWSIZED:
            if own not in passed:
                passed.append(own)
            continue
        edge = [(q, r) for q, r in hits.items() if r[2] == 'O' and r[3] < D_SHANK]
        if edge:
            q, r = edge[0]
            return {'kind': 'edge', 'part': q, 'distMm': round(dist - PSTEP / 2, 2), 'clearRadiusMm': round(r[3] / 2, 2),
                    'passed': passed}
        for q, r in hits.items():
            if r[2] == 'H' and q not in passed:
                passed.append(q)
    return {'kind': 'open', 'part': None, 'distMm': REACH, 'passed': passed}


def doc_lookup(part, center, axis, docs):
    for dd in docs:
        if dd['part'] != part:
            continue
        w = np.asarray(center) - dd['center']
        ax = dd['axis']
        if abs(ax @ axis) < math.cos(math.radians(15)):
            continue
        if np.linalg.norm(w - (w @ ax) * ax) < 1.0 and abs(w @ ax) < 8:
            return dd
    return None


def load_docs():
    docs = []
    fa = json.loads(FASTENERS.read_text())
    for h in fa.get('unassignedHoles', []):
        ax = np.array(h['axis'], float)
        docs.append({'part': h['part'], 'center': np.array(h['center'], float), 'axis': ax / np.linalg.norm(ax),
                     'source': 'guide/content/fasteners.json unassignedHoles', 'should': h.get('shouldTakeScrew'),
                     'reason': h.get('reason')})
    return docs


def mjcf_joints():
    root = ET.parse(MJCF).getroot()

    def qmat(q):
        w, x, y, z = np.asarray(q, float) / np.linalg.norm(q)
        return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                         [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                         [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    bodies = {}

    def rec(b, T, parent):
        L = np.eye(4)
        L[:3, :3] = qmat([float(x) for x in b.get('quat', '1 0 0 0').split()])
        L[:3, 3] = [float(x) for x in b.get('pos', '0 0 0').split()]
        Tb = T @ L
        js = [j for j in b.findall('joint') if j.get('name') and j.get('type', 'hinge') == 'hinge']
        bodies[b.get('name')] = {'T': Tb, 'parent': parent, 'joint': js[0] if js else None}
        for c in b.findall('body'):
            rec(c, Tb, b.get('name'))
    for b in root.find('worldbody').findall('body'):
        rec(b, np.eye(4), None)
    T0 = np.linalg.inv(bodies['trunk_base']['T'])
    joints, parent = {}, {}
    for name, b in bodies.items():
        parent[name] = b['parent'] if b['parent'] in bodies else None
        j = b['joint']
        if j is None:
            continue
        T = T0 @ b['T']
        ax = np.array([float(x) for x in j.get('axis', '0 0 1').split()])
        jp = np.array([float(x) for x in j.get('pos', '0 0 0').split()])
        joints[j.get('name')] = {'name': j.get('name'), 'child': name, 'parent': b['parent'],
                                 'anchor': (T[:3, :3] @ jp + T[:3, 3]) * 1000, 'axis': T[:3, :3] @ ax,
                                 'range': [float(x) for x in j.get('range').split()]}
    joints['jaw'] = {**JAW_JOINT, 'anchor': np.array(JAW_JOINT['anchor'], float),
                     'axis': np.array(JAW_JOINT['axis'], float)}
    parent['jaw'] = 'jaw_soft'
    return joints, parent


def dedupe(cands):
    """One record per physical hole. Same-part coaxial records whose spans overlap or nearly touch are one hole;
    a record whose centre lies inside another record's bore at an oblique angle is a section artefact of it."""
    order = sorted(range(len(cands)), key=lambda i: -cands[i]['boreLenMm'])
    keep, dropped = [], []
    for i in order:
        h = cands[i]
        why = None
        for o in keep:
            if o['part'] != h['part']:
                continue
            a = o['axis']
            w = h['center'] - o['center']
            lat = np.linalg.norm(w - (w @ a) * a)
            ax = abs(w @ a)
            half = (o['z1'] - o['z0']) / 2
            if abs(h['axis'] @ a) >= math.cos(math.radians(8)):
                hh = (h['z1'] - h['z0']) / 2
                if lat < 0.3 and ax <= half + hh + 0.6:
                    why = 'coaxial duplicate'; break
            elif lat <= o['dMm'] / 2 + 0.3 and ax <= half + 0.5:
                why = 'oblique section of the same bore'; break
        if why:
            dropped.append({'part': h['part'], 'center': rnd(h['center']), 'axis': rnd(h['axis'], 4), 'dMm': h['dMm'],
                            'keptAs': rnd(o['center']), 'why': why})
        else:
            keep.append(h)
    return keep, dropped


def stage_classify(probe, screws_g, screws_u, printed):
    docs = load_docs()
    joints, parent = mjcf_joints()
    horn_geometry(screws_g + screws_u, joints)
    cands = []
    for hax in probe:
        c = np.array(hax['center']); a = np.array(hax['axis'])
        for h in own_holes(hax):
            h = {'part': hax['part'], 'axisRef': hax, **h}
            zc = (h['z0'] + h['z1']) / 2
            h['center'] = c + a * zc
            h['axis'] = a
            cands.append(h)
    holes, dropped = dedupe(cands)
    for h in holes:
        hax = h['axisRef']
        c = np.array(hax['center']); a = h['axis']
        g = match_screws(c, a, h['z0'], h['z1'], screws_g)
        u = match_screws(c, a, h['z0'], h['z1'], screws_u)
        h['guideScrews'] = [s['id'] for s in g]
        h['legGuideScrews'] = [s['id'] for s in u]
        ends = []
        for side, zend, est in ((-1, h['z0'], h['endLo']), (1, h['z1'], h['endHi'])):
            if est == 'S':
                ends.append({'side': side, 'state': 'blind'})
                continue
            w = walk(hax, zend, side, h['part'])
            w['side'] = side
            ends.append(w)
        h['ends'] = ends
        other = []
        for q, runs in hax.get('probeOther', {}).items():
            for r in runs:
                if r[2] == 'H' and r[3] <= D_SCREWSIZED and r[1] > h['z0'] - REACH and r[0] < h['z1'] + REACH:
                    other.append({'part': q, 'zIn': r[0], 'zOut': r[1], 'dMm': r[3]})
                    break
        h['otherSolids'] = other
        h['doc'] = doc_lookup(h['part'], h['center'], a, docs)
    # classification
    for h in holes:
        partners = [e for e in h['ends'] if e.get('kind') == 'partner']
        for e in partners:
            e['bodyOwn'] = body_of(h['part'])
            e['bodyPartner'] = body_of(e['part'], h['center'] + h['axis'] * ((e['zIn'] + e['zOut']) / 2 -
                                                                                (h['z0'] + h['z1']) / 2))
        if h['guideScrews']:
            h['class'] = 'a'
        elif h['legGuideScrews']:
            h['class'] = 'a-upstream'
        elif any(e['bodyOwn'] == e['bodyPartner'] for e in partners):
            h['class'] = 'b'
        elif partners:
            h['class'] = 'd'
            h['dReason'] = 'coaxial with a hole on another rigid body (moving joint): a screw here would lock the joint'
        elif h['doc'] is not None:
            h['class'] = 'd'
            h['dReason'] = 'documented: ' + (h['doc']['reason'] or '')
        elif abs(h['taperMmPerMm']) >= 0.5:
            h['class'] = 'd'
            h['dReason'] = (f"tapered pit, not a screw bore: diameter changes {h['taperMmPerMm']} mm per mm along the "
                            f"axis ({h['dRangeMm'][0]}-{h['dRangeMm'][1]} mm)")
        else:
            h['class'] = 'c'
    return holes, dropped, joints, parent


def hole_summary(h):
    return {'part': h['part'], 'center': rnd(h['center']), 'axis': rnd(h['axis'], 4), 'dMm': h['dMm'],
            'dRangeMm': h['dRangeMm'], 'taperMmPerMm': h['taperMmPerMm'],
            'spanMm': rnd([h['z1'] - h['z0']])[0], 'boreLenMm': h['boreLenMm'], 'class': h['class'],
            'guideScrews': h['guideScrews'], 'legGuideScrews': h['legGuideScrews'],
            'ends': [{k: v for k, v in e.items() if k != 'passed'} | ({'passed': e['passed']} if e.get('passed') else {})
                     for e in h['ends']],
            'profile': [[round(r[0] - (h['z0'] + h['z1']) / 2, 2), round(r[1] - (h['z0'] + h['z1']) / 2, 2), r[2]]
                        for r in h['runs']],
            **({'dReason': h['dReason']} if h.get('dReason') else {}),
            **({'doc': {k: h['doc'][k] for k in ('source', 'should', 'reason')}} if h.get('doc') else {}),
            **({'otherSolids': h['otherSolids']} if h['otherSolids'] else {})}


# --------------------------------------------------------------------------------------------- stage 4: joints and clearance
SIZES = {'M2': 2.0, 'M2.5': 2.5, 'M2.6': 2.6}


def rot_about(anchor, axis, ang):
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    R = np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * (K @ K)
    M = np.zeros((3, 4)); M[:, :3] = R; M[:, 3] = np.asarray(anchor) - R @ np.asarray(anchor)
    return M


def compose(A, B):
    """3x4 affine A after B."""
    Ah = np.vstack([A, [0, 0, 0, 1]]); Bh = np.vstack([B, [0, 0, 0, 1]])
    return (Ah @ Bh)[:3]


def cyl_world(p_start, direction, length, radius, segs=40):
    """Manifold cylinder from p_start along direction for length."""
    import manifold3d as m3
    u, v, a = frame(direction)
    M = np.zeros((3, 4), np.float32); M[:, 0] = u; M[:, 1] = v; M[:, 2] = a; M[:, 3] = p_start
    return m3.Manifold.cylinder(length, radius, -1, segs, False).transform(M)


def path_joints(b_head, b_q, joints, parent):
    """Joints between two bodies: (joint, moves) with moves = 'head' if the head side is the child side."""
    def chain(b):
        out = [b]
        while parent.get(out[-1]):
            out.append(parent[out[-1]])
        return out
    ch, cq = chain(b_head), chain(b_q)
    lca = next(b for b in ch if b in cq)
    by_child = {j['child']: j for j in joints.values()}
    res = []
    for b in ch[:ch.index(lca)]:
        if b in by_child:
            res.append((by_child[b], 'head'))
    for b in cq[:cq.index(lca)]:
        if b in by_child:
            res.append((by_child[b], 'part'))
    return res


def build_joints(holes):
    """Group class-b holes into screw joints (one per axis line and part pair)."""
    out = []
    for h in holes:
        if h['class'] != 'b':
            continue
        for e in h['ends']:
            if e.get('kind') != 'partner' or e['bodyOwn'] != e['bodyPartner']:
                continue
            pair = frozenset([h['part'], e['part']])
            pt = h['center']
            for j in out:
                if j['pair'] == pair and abs(j['axis'] @ h['axis']) > math.cos(math.radians(8)):
                    w = pt - j['point']
                    if np.linalg.norm(w - (w @ j['axis']) * j['axis']) < 0.6:
                        j['holes'].append((h, e)); break
            else:
                out.append({'pair': pair, 'axis': h['axis'], 'point': pt, 'holes': [(h, e)]})
    return out


def stack_of(jt):
    """Entry part (clearance, larger hole), into part (pilot), head seat, grip and pilot geometry along one axis."""
    # Use the hole with the larger diameter as the frame: it is the clearance side.
    h, e = max(jt['holes'], key=lambda he: he[0]['dMm'])
    hax = h['axisRef']
    c = np.array(hax['center']); a = h['axis']
    side = e['side']                      # direction from h towards the partner (pilot) in hax coordinates
    t = a * side                          # direction of travel
    # Head seat: the clearance hole's outer end, or the floor of a counterbore of at least the head diameter there.
    runs = sorted(h['runs'], key=lambda r: r[0] * side)   # from the outer end inwards
    outer = runs[0][0] if side > 0 else runs[0][1]
    seat = outer
    for r in runs:
        if r[3] == 'H' and r[2] >= HEAD_D + 0.1:
            seat = r[1] if side > 0 else r[0]
        else:
            break
    zin, zout = e['zIn'], e['zOut']
    grip = abs(zin - seat)
    depth = e['depthMm']
    # Free length past the pilot's far end before any part (other than an open bore) comes within 1 mm of the axis.
    prof = hax['probe']
    free = 0.0
    if e['farEnd'] != 'S':
        z = zout + side * PSTEP / 2
        while free < REACH:
            hit = None
            for q, rr in prof.items():
                r = runs_at(rr, z)
                if r is None or r[2] == '-':
                    continue
                if r[2] == 'S' or (r[2] in 'OH' and r[3] < D_SHANK):
                    hit = q; break
            if hit:
                break
            free += PSTEP; z += side * PSTEP
    seat_pt = c + a * seat
    return {'entryPart': h['part'], 'intoPart': e['part'], 'clearanceDMm': h['dMm'], 'clearanceSpanMm':
            round(abs(h['z1'] - h['z0']), 2), 'pilotDMm': e['dMm'], 'pilotDepthMm': depth,
            'pilotFarEnd': 'blind' if e['farEnd'] == 'S' else 'open', 'gripMm': round(grip, 2),
            'freePastPilotMm': round(free, 2) if e['farEnd'] != 'S' else 0.0,
            'seat': seat_pt, 'travel': t, 'hole': h, 'partner': e}


def screw_options(st):
    dc, dp = st['clearanceDMm'], st['pilotDMm']
    sizes = [n for n, maj in SIZES.items() if dc >= maj + 0.1 and maj - 0.8 <= dp <= maj + 0.1]
    if not sizes:
        sizes = [n for n, maj in SIZES.items() if dc >= maj + 0.05]
    opts = []
    for n in sizes:
        for sz, L in STOCK:
            if sz != n:
                continue
            into = L - st['gripMm']
            eng = max(0.0, min(into, st['pilotDepthMm']) - TIP_LEADIN)
            poke = into - st['pilotDepthMm']
            if st['pilotFarEnd'] == 'blind':
                ok_tip = poke <= -0.2
                tip = 'bottoms out' if poke > -0.2 else f'{-poke:.2f} mm short of the pilot bottom'
            else:
                ok_tip = poke <= st['freePastPilotMm'] - 0.3
                tip = (f'tip stays {-poke:.2f} mm inside the pilot' if poke <= 0 else
                       f'tip {poke:.2f} mm past the pilot end ({st["freePastPilotMm"]:.2f} mm free there)')
            opts.append({'spec': f'{n} x {L} TAP', 'size': n, 'L': L, 'intoPilotMm': round(into, 2),
                         'engagementMm': round(eng, 2), 'tipPastPilotMm': round(poke, 2), 'tip': tip,
                         'tipOk': bool(ok_tip), 'threadRadialMm': round((SIZES[n] - dp) / 2, 3)})
    return opts


def screw_solid(st, L, size):
    head = cyl_world(st['seat'] - st['travel'] * (HEAD_H + 0.02), st['travel'], HEAD_H, HEAD_D / 2)
    shank = cyl_world(st['seat'] + st['travel'] * 0.0, st['travel'], L, SIZES[size] / 2, 24)
    return head, shank


def static_hits(man, assembled, skip=(), min_vol=0.005):
    hits = []
    lo, hi = np.array(man.bounding_box()[:3]), np.array(man.bounding_box()[3:])
    for q in assembled:
        if q in skip:
            continue
        mq, qlo, qhi = part_manifold(q)
        if np.any(qhi < lo - 0.01) or np.any(qlo > hi + 0.01):
            continue
        inter = man ^ mq
        vol = inter.volume()
        if vol > min_vol:
            hits.append({'part': q, 'overlapMm3': round(vol, 3)})
    return hits


def sweep_clearance(man, body, assembled, joints, parent, near=25.0, step_deg=1.0):
    """Min gap between a solid on `body` and every part on another body within `near` mm, sweeping each joint
    between them over its range (others at zero), and the two adjacent joints together on a coarse grid."""
    res = []
    lo, hi = np.array(man.bounding_box()[:3]), np.array(man.bounding_box()[3:])
    for q in assembled:
        bq = BODY.get(q)
        if bq is None or bq == body:
            continue
        mq, qlo, qhi = part_manifold(q)
        if np.any(qhi < lo - near) or np.any(qlo > hi + near):
            continue
        pj = path_joints(body, bq, joints, parent)
        if not pj:
            continue
        for j, moves in pj:
            r0, r1 = j['range']
            angs = np.arange(r0, r1 + 1e-9, math.radians(step_deg))
            best = (np.inf, None, 0.0)
            contact = []
            for ang in angs:
                M = rot_about(j['anchor'], j['axis'], ang if moves == 'head' else -ang)
                mm = man.transform(M.astype(np.float32))
                vol = (mm ^ mq).volume()
                gap = 0.0 if vol > 1e-4 else mm.min_gap(mq, 5.0)
                if vol > 1e-4:
                    contact.append(round(math.degrees(ang), 1))
                if gap < best[0] or (gap == 0 and vol > best[2]):
                    best = (gap, round(math.degrees(ang), 1), vol)
            res.append({'part': q, 'joint': j['name'], 'rangeDeg': [round(math.degrees(r0), 1), round(math.degrees(r1), 1)],
                        'minGapMm': round(float(best[0]), 3), 'atDeg': best[1],
                        'contactDeg': [contact[0], contact[-1]] if contact else None,
                        'maxOverlapMm3': round(float(best[2]), 3)})
        if len(pj) >= 2:
            (j1, m1), (j2, m2) = pj[0], pj[1]
            g1 = np.linspace(*j1['range'], 13); g2 = np.linspace(*j2['range'], 13)
            best = (np.inf, None)
            for a1 in g1:
                for a2 in g2:
                    M1 = rot_about(j1['anchor'], j1['axis'], a1 if m1 == 'head' else -a1)
                    M2 = rot_about(j2['anchor'], j2['axis'], a2 if m2 == 'head' else -a2)
                    # Zero-pose axes: a head-side pose is R(outer) R(inner); a part-side pose acts on the head as
                    # its inverse, R(inner)^-1 R(outer)^-1. pj lists head-side joints inner first, then part-side
                    # joints inner first.
                    M = compose(M1, M2) if (m1 == m2 == 'part') else compose(M2, M1)
                    mm = man.transform(M.astype(np.float32))
                    vol = (mm ^ mq).volume()
                    gap = 0.0 if vol > 1e-4 else mm.min_gap(mq, 5.0)
                    if gap < best[0]:
                        best = (gap, [round(math.degrees(a1), 1), round(math.degrees(a2), 1)])
            res.append({'part': q, 'joint': f"{j1['name']}+{j2['name']}", 'grid': '13x13',
                        'minGapMm': round(float(best[0]), 3), 'atDeg': best[1]})
    return res


def stage_clear(holes, assembled, joints, parent):
    out = []
    for jt in build_joints(holes):
        st = stack_of(jt)
        opts = screw_options(st)
        body = BODY.get(st['entryPart'])
        for o in opts:
            head, shank = screw_solid(st, o['L'], o['size'])
            # Shank against every part except the two it joins; the into part is checked past its pilot only
            # through tipOk (the probe), the entry part through the clearance diameter.
            o['shankHits'] = static_hits(shank, assembled, skip=(st['entryPart'], st['intoPart']))
            o['headHits'] = static_hits(head, assembled, skip=())
        good = [o for o in opts if o['tipOk'] and not o['shankHits'] and o['engagementMm'] >= 1.5]
        rec = max(good, key=lambda o: (o['engagementMm'], -o['L'])) if good else None
        if rec:
            head, shank = screw_solid(st, rec['L'], rec['size'])
            screw = head + shank
            moving = sweep_clearance(screw, body, assembled, joints, parent)
        else:
            moving = []
        h = st['hole']
        out.append({'entryPart': st['entryPart'], 'intoPart': st['intoPart'], 'body': body,
                    'seat': rnd(st['seat']), 'travel': rnd(st['travel'], 4),
                    'clearanceHole': {'part': st['entryPart'], 'dMm': st['clearanceDMm'], 'depthMm': st['clearanceSpanMm']},
                    'pilotHole': {'part': st['intoPart'], 'dMm': st['pilotDMm'], 'depthMm': st['pilotDepthMm'],
                                  'farEnd': st['pilotFarEnd'], 'freePastEndMm': st['freePastPilotMm']},
                    'gripMm': st['gripMm'], 'options': opts,
                    'recommended': rec['spec'] if rec else None, 'movingClearance': moving,
                    'holes': [rnd(x[0]['center']) for x in jt['holes']]})
        print('joint', st['entryPart'], '->', st['intoPart'], rnd(st['seat']), 'rec', rec and rec['spec'], flush=True)
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', default='all')
    ap.add_argument('--parts', nargs='*')
    ap.add_argument('--sensitivity', action='store_true',
                    help='diagonal sweeps and circularity > 0.70; writes *-sens.json in the work cache only')
    a = ap.parse_args()
    if a.sensitivity:
        TAG = '-sens'
    g, parts, assembled, printed = guide_parts()
    if a.parts:
        printed = [p for p in printed if p in a.parts]
    print(len(assembled), 'assembled,', len(printed), 'printed:', ' '.join(printed), flush=True)
    if a.stage in ('detect', 'all'):
        detect = stage_detect(printed, a.sensitivity)
    else:
        detect = json.loads((WORK / f'detect{TAG}.json').read_text())
        detect = {k: v for k, v in detect.items() if k in printed}
    if a.stage in ('probe', 'all'):
        probe = stage_probe(assembled, detect)
    else:
        probe = json.loads((WORK / f'probe{TAG}.json').read_text())
        probe = [h for h in probe if h['part'] in printed]
    sg, su = guide_screws(g), upstream_screws()
    holes, dropped, joints, parent = stage_classify(probe, sg, su, printed)
    jdump(WORK / f'classify{TAG}.json', {'holes': [hole_summary(h) for h in holes], 'dropped': dropped})
    from collections import Counter
    counts = Counter(h['class'] for h in holes)
    print(counts)
    if not TAG:
        jdump(OUT, {'problem': 'P5', 'generated': time.strftime('%Y-%m-%d'), 'guideData': str(GUIDE_DATA),
                    'counts': dict(counts), 'printedParts': printed,
                    'missingScrewCandidates': [hole_summary(h) for h in holes if h['class'] == 'b'],
                    'holes': [hole_summary(h) for h in holes], 'dropped': dropped})
