"""Verify a head_cap V1.8 candidate (Pi seat shifted by [-DX, 0, DZ], 2x20 IDC socket on the header).

A  final pose: candidate cap, moved Pi group, IDC socket, Pi screw heads, speaker and amplifier against the fixed head
   parts and against each other (exact distances).
B  cap-on descent [0, 0, 40]: the candidate's added material (rails) sampled every 0.25 mm (overlap and exact gap; the
   true minimum is at most 0.125 mm below the sampled one); each Pi part and the socket as exact convex sweeps.
C  side effects: Pi screws (M2 x 6 / M2 x 4) engagement and tips, rail sections, roof joints, added material inside
   the cap hull, notch region unchanged, CSI ribbon length, microSD side gap, USB-edge roof gap; the same numbers for
   the printed V1.6 and the released V1.7 for comparison.
Usage: DX=.. DZ=.. X_TRIM=.. HS=10.6,11.0 verify_v18.py <candidate-world.stl>   writes ../verify-v18-<tag>.json
"""
import json, sys, os, math, time, resource
sys.path.insert(0, os.path.dirname(__file__))
from cs_lib import *

T0 = time.time()
def prog(msg):
    print(f'[{time.time()-T0:7.1f}s {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20:5.0f}MiB] {msg}', flush=True)

RD = ROOT / 'build-pack-20260913/redesign-20260913'
FI = RD / 'workflow-review-20261009/enclosed-wiring-repair/power-sensor/head-controller-study/final-integration-20261009'
BASE_SHELL = RD / 'head-redesign-20261008/curved-head/community-curved-head-world.stl'
RAILS = [FI / 'pi-roof-side-rail-0.stl', FI / 'pi-roof-side-rail-1.stl']
DX = float(os.environ['DX']); DZ = float(os.environ['DZ']); X_TRIM = float(os.environ['X_TRIM'])
HS = [float(h) for h in os.environ.get('HS', '10.6,11.0').split(',')]
TAG = os.environ.get('TAG', f'dx{DX}-dz{DZ}')
CAND = Path(sys.argv[1])
SHIFT = np.array([-DX, 0.0, DZ])
rep = {'DX': DX, 'DZ': DZ, 'X_TRIM': X_TRIM, 'candidate': str(CAND), 'candidateSha256': sha(CAND), 'socketHeights': HS}

S, prov = solids(None)
rep['solidProvenance'] = prov
FX = [k for k in FIXED if k in S]
FB = {k: bbox(S[k]) for k in FX}
C16 = load_cap(CAP_V16, CAP_V16_SHA); C17 = load_cap(CAP_V17, CAP_V17_SHA)
Ct = trimesh.load(CAND, force='mesh'); C2 = to_mf(Ct)
assert C2.status() == mf.Error.NoError
pi_keys = sorted(k for k in S if k == 'pi' or (k.startswith('head_pi') and 'receiving' not in k and 'header_pin' not in k))
pin_keys = sorted(k for k in S if k.startswith('head_pi_zero_w_header_pin_'))
RIDE = [k for k in SPEAKER + ['amplifier'] if k in S]
fas = json.load(open(ROOT / 'guide/content/fasteners.json'))['screws']
SEATS16 = {}
heads16 = {}
for s_ in fas:
    if s_['id'].startswith('E-pi'):
        c = np.array(s_['center']) + np.array([4.6, 0, 0])   # fasteners.json holds the V1.7 seats
        SEATS16[s_['id']] = (c, np.array(s_['axis'], float), s_)
        cyl = trimesh.creation.cylinder(radius=s_['headDiameterMm'] / 2, segment=[c, c - s_['headHeightMm'] * np.array(s_['axis'])], sections=32)
        heads16[s_['id']] = to_mf(cyl)
EVEN_C, ODD_C = 0.5 * sum(T_LOW), 0.5 * sum(T_HIGH)


def socket(H, d):
    body = local_hull((S_BASE_TOP, S_BASE_TOP + H), (-27.8, 27.8), (EVEN_C - 1.85, ODD_C + 1.85), d)
    key = local_hull((S_BASE_TOP, S_BASE_TOP + H), (-1.9, 1.9), (ODD_C + 1.85, ODD_C + 3.35), d)
    return union([body, key])


def near_fixed(M, search):
    b = bbox(M)
    out = []
    for k in FX:
        dd = np.maximum(0, np.maximum(b[0] - FB[k][1], FB[k][0] - b[1]))
        if np.linalg.norm(dd) < search:
            out.append(k)
    return out


def gaps_to(M, keys, search=6.0, pool=None):
    pool = pool or S
    out = {}
    for k in keys:
        g = gap(M, pool[k], search)
        if g < search:
            out[k] = round(g, 3)
    return dict(sorted(out.items(), key=lambda kv: kv[1]))


prog('loaded')
# ---------------- A. final pose
A_ = {}
added = C2 - C16
removed = C16 - C2
A_['capOverlapWithFixedMm3'] = {lab: round(sum(overlap(cap, S[k]) for k in FX), 4) for lab, cap in [('V1.6', C16), ('candidate', C2)]}
A_['addedMaterialGapToFixed'] = gaps_to(added, near_fixed(added, 6.0))
pig = {}
for k in pi_keys:
    M = tr(S[k], SHIFT)
    g = gaps_to(M, near_fixed(M, 6.0))
    if g:
        pig[k] = next(iter(g.items()))
A_['movedPiPartsGapToFixed'] = dict(sorted(pig.items(), key=lambda kv: kv[1][1]))
pic = {}
for k in pi_keys + pin_keys:
    M = tr(S[k], SHIFT)
    pic[k] = {'overlapMm3': round(overlap(M, C2), 4), 'gapMm': round(gap(M, C2, 6.0), 3)}
A_['movedPiPartsVsCandidateCap'] = {k: v for k, v in pic.items() if v['gapMm'] < 6.0}
A_['screwHeadsVsCandidateCap'] = {n: round(gap(tr(M, SHIFT), C2, 6.0), 3) for n, M in heads16.items()}
A_['rideAlongVsMovedPi'] = {k: round(min(gap(S[k], tr(S[p], SHIFT), 6.0) for p in pi_keys), 3) for k in RIDE}
soc = {}
for H in HS:
    Sk = socket(H, SHIFT)
    soc[str(H)] = {'toFixed': gaps_to(Sk, near_fixed(Sk, 6.0)), 'toCandidateCap': round(gap(Sk, C2, 6.0), 3),
                   'toScrewHeads': {n: round(gap(Sk, tr(M, SHIFT), 6.0), 3) for n, M in heads16.items()},
                   'toPiComponents': gaps_to(Sk, [k for k in pi_keys if 'header' not in k and 'solder' not in k],
                                             pool={k: tr(S[k], SHIFT) for k in pi_keys}),
                   'toRideAlong': gaps_to(Sk, RIDE)}
A_['socketFinalPose'] = soc
rep['A_finalPose'] = A_
prog('A done')

# ---------------- B. descent
B_ = {}
cand_keys = near_fixed(tr(union([added, tr(added, [0, 0, 40])]), [0, 0, 0]), 6.0)
base = {k: overlap(added, S[k]) for k in cand_keys}
worst, at, ming, ming_at, ming_part = 0.0, None, 99.0, None, None
for h in np.arange(0.0, 40.0 + 1e-9, 0.25):
    Mh = tr(added, [0, 0, float(h)])
    for k in near_fixed(Mh, 4.0):
        v = overlap(Mh, S[k]) - base.get(k, 0.0)
        if v > worst:
            worst, at = v, (float(h), k)
        g = gap(Mh, S[k], 4.0)
        if g < ming:
            ming, ming_at, ming_part = g, float(h), k
B_['addedMaterialSampled0.25mm'] = {'maxExcessOverlapMm3': round(worst, 4), 'at': at, 'minGapMm': round(ming, 3),
                                    'minGapAtHeightMm': ming_at, 'minGapPart': ming_part,
                                    'note': 'sampled; the exact minimum along the descent is at most 0.125 mm lower'}
prog('B added done')
sw = {}
for k in pi_keys + pin_keys:
    Hh = sweep(mf.Manifold.hull(tr(S[k], SHIFT)))
    g = gaps_to(Hh, near_fixed(Hh, 8.0), 8.0)
    if g:
        sw[k] = next(iter(g.items()))
B_['piPartsExactConvexSweep'] = dict(sorted(sw.items(), key=lambda kv: kv[1][1])[:12])
B_['screwHeadsExactSweep'] = {n: next(iter(gaps_to(sweep(tr(M, SHIFT)), FX, 8.0).items()), None) for n, M in heads16.items()}
ssw = {}
for H in HS:
    pieces = [local_hull((S_BASE_TOP, S_BASE_TOP + H), (-27.8, 27.8), (EVEN_C - 1.85, ODD_C + 1.85), SHIFT),
              local_hull((S_BASE_TOP, S_BASE_TOP + H), (-1.9, 1.9), (ODD_C + 1.85, ODD_C + 3.35), SHIFT)]
    allg = {}
    for Pc in pieces:
        Hh = sweep(Pc)
        for k, v in gaps_to(Hh, near_fixed(Hh, 8.0), 8.0).items():
            allg[k] = min(v, allg.get(k, 99))
    ssw[str(H)] = dict(sorted(allg.items(), key=lambda kv: kv[1]))
B_['socketExactSweepPerFixedPart'] = ssw
rep['B_descent'] = B_
prog('B done')

# ---------------- C. side effects
Cx = {}
C16_tm = trimesh.load(CAP_V16, force='mesh'); C17_tm = trimesh.load(CAP_V17, force='mesh')
VERS = [('V1.6', C16_tm, np.zeros(3)), ('V1.7', C17_tm, np.array([-4.6, 0, 0])), ('candidate', Ct, SHIFT)]


def material_along(capmesh, p0, ax, s0, s1, r=0.95):
    e1 = np.cross(ax, [0, 1, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(ax, e1)
    lens = []
    for kk in range(12):
        th = 2 * math.pi * kk / 12; o = p0 + r * (math.cos(th) * e1 + math.sin(th) * e2)
        ss = np.linspace(s0, s1, int((s1 - s0) / 0.02) + 1)
        Pp = o[None, :] + ss[:, None] * ax[None, :]
        inside = np.concatenate([capmesh.contains(Pp[j:j + 100]) for j in range(0, len(Pp), 100)])
        lens.append(float(inside.sum() * 0.02))
    return min(lens), max(lens)


screws = {}
for sid, (c, ax, s_) in SEATS16.items():
    row = {}
    for lab, cm, d in VERS:
        p0 = c + d
        lo_, hi_ = material_along(cm, p0, ax, 1.55, 8.0)
        r = {'railMaterialAlongAxisFrom1.55mm': [round(lo_, 2), round(hi_, 2)]}
        for L in (6.0, 4.0):
            seg = trimesh.creation.cylinder(radius=1.0, segment=[p0, p0 + L * ax], sections=24)
            Ms = to_mf(seg); tip = p0 + L * ax
            r[f'M2x{L:.0f}'] = {'tipXYZ': rnd(tip.tolist(), 3), 'engagementMinMm': round(material_along(cm, p0, ax, 1.55, L)[0], 2),
                                'tipGapToFixed': next(iter(gaps_to(Ms, near_fixed(Ms, 4.0), 4.0).items()), None),
                                'tipInsideCap': bool(cm.contains([tip])[0])}
        row[lab] = r
    screws[f'{sid} ({s_["spec"]})'] = row
Cx['screws'] = screws
prog('C1 done')

import shapely.geometry as sg
def rail_sections(cap_tm, ylo, yhi, xlo, xhi, zs):
    out = {}
    for z in zs:
        sec = cap_tm.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if sec is None:
            continue
        pl, _ = sec.to_2D(to_2D=trimesh.transformations.translation_matrix([0, 0, -z]))
        win = sg.box(xlo, ylo, xhi, yhi); area, xs = 0.0, []
        for poly in pl.polygons_full:
            g = poly.intersection(win)
            if not g.is_empty and g.area > 0:
                area += g.area; xs.append((g.bounds[0], g.bounds[2]))
        if area > 0:
            out[f'{z:.1f}'] = {'areaMm2': round(area, 2), 'xRange': [round(min(a for a, b in xs), 2), round(max(b for a, b in xs), 2)]}
    return out


secs = {}
for lab, cm, d in VERS:
    zs = [115.0 + d[2] + k for k in (0, 2.5, 5, 7, 9, 11, 13, 17, 21, 25, 29, 31)]
    secs[lab] = {'rail -y': rail_sections(cm, -32.3, -25.7, 49.0, 66.0 + d[0] + 0.5, zs),
                 'rail +y': rail_sections(cm, 25.7, 32.3, 49.0, 66.0 + d[0] + 0.5, zs)}
Cx['railSectionsInYBand'] = secs
prog('C2 done')

base_tm = trimesh.load(BASE_SHELL, force='mesh'); Bm = to_mf(base_tm)
Cx['addedMaterialOutsideShellHullMm3'] = round((added - mf.Manifold.hull(Bm)).volume(), 4)
Cx['addedMaterialOutsideV16CapHullMm3'] = round((added - mf.Manifold.hull(C16)).volume(), 4)
Cx['addedMaterialBounds'] = bbox(added).round(3).tolist()
Cx['removedMaterialMm3'] = round(removed.volume(), 3); Cx['addedMaterialMm3'] = round(added.volume(), 3)
def proj_area(M):
    m = mf_to_tm(M)
    if len(m.faces) == 0:
        return 0.0
    return float((m.area_faces * np.clip(m.face_normals[:, 2], 0, None)).sum())
joints = {}
for i, side in enumerate(['-y', '+y']):
    Rm = to_mf(trimesh.load(RAILS[i], force='mesh'))
    zone = box([40, -40 if side == '-y' else 20, 140], [75, -20 if side == '-y' else 40, 160])
    joints[f'rail {side}'] = {lab: {'railInRoofZoneOverlapWithShellMm3': round(((cm_ ^ zone) ^ Bm).volume(), 3)}
                              for lab, cm_ in [('V1.6', C16), ('candidate', C2)]}
    joints[f'rail {side}']['candidate addedJointFootprintMm2'] = round(proj_area((added ^ zone) ^ Bm), 2)
Cx['roofJoint'] = joints
Nb = box([-34.5, 7.0, 110.0], [-19.0, 30.0, 124.0])
Cx['notchRegionXorMm3'] = round(((C16 ^ Nb) - (C2 ^ Nb)).volume() + ((C2 ^ Nb) - (C16 ^ Nb)).volume(), 6)
cam_end = np.array([73.0, -3.0, 131.0]); pi_end = np.array([69.0, -31.0, 128.0])
Cx['csi'] = {lab: round(float(np.linalg.norm(pi_end + d - cam_end)), 2) for lab, _, d in VERS}
Cx['csi']['note'] = 'straight distance from the camera connector to the Pi CSI connector (routes.json head_csi end points); ribbon 200 mm'


def first_hit(mesh, o, dvec):
    loc, idx_, _ = mesh.ray.intersects_location(np.array([o]), np.array([dvec]), multiple_hits=True)
    if len(loc) == 0:
        return None
    return float(np.min(np.linalg.norm(loc - o, axis=1)))


sd, usb = {}, {}
ub = bbox(S['head_pi_component_bottom-usb-edge-context'])
for lab, cm, d in VERS:
    rows = {}
    for t in (120.0, 125.0, 128.7, 132.0, 137.0):
        o = 41.5 * A + 32.5 * EY + t * CT + d
        rows[f't{t}'] = round(first_hit(cm, o, [0, 1.0, 0]) or -1, 2)
    sd[lab] = rows
    gaps = []
    for x in np.linspace(ub[0, 0], ub[1, 0], 5):
        for y in np.linspace(ub[0, 1], ub[1, 1], 7):
            o = np.array([x, y, ub[1, 2]]) + d
            g = first_hit(cm, o, [0, 0, 1.0]); gaps.append(g if g is not None else 99)
    usb[lab] = {'minRoofGapAboveUsbEdgeMm': round(min(gaps), 2), 'maxMm': round(max(gaps), 2)}
Cx['microSdSideGapAlongPlusY'] = sd
Cx['usbEdgeRoofGap'] = usb
Cx['note'] = 'The PCB sits on the rails, so its gap to the cap is zero by design; component gaps are in A_finalPose.'
rep['C_sideEffects'] = Cx
prog('C done')
json.dump(rnd(rep, 4), open(OUT / f'verify-v18-{TAG}.json', 'w'), indent=1)
prog('done')
