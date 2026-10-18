"""Verify the candidate head_cap (Pi seat moved DX mm back) against the released V1.6 cap.

A  final pose: populated cap (cap, speaker, amplifier, shifted Pi group, shifted GPIO housing) vs the fixed head parts
B  cap-on descent [0,0,40]: V1.6 cap + speaker + amplifier sampled every 1 mm (baseline); the candidate's added
   material sampled every 0.25 mm; Pi group and housing as exact convex sweeps
C  side effects: Pi screws (M2x6 / M2x4) tips and engagement, rail sections, roof joints, CSI length, microSD side gap,
   USB-edge roof gap, bundle route clearance, plugging-after-cap free length, rear travel available today
"""
import json, sys, os, math
from pathlib import Path
import numpy as np, trimesh
sys.path.insert(0, os.path.dirname(__file__))
from vc import *

DX = float(os.environ.get('DX', '4.6'))
CAND = Path(sys.argv[1])
STAGES = os.environ.get('STAGES', 'ABC')
import resource, time
T0 = time.time()
def prog(msg):
    print(f'[{time.time()-T0:6.1f}s rss {resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/2**20:.0f}MiB] {msg}', flush=True)
rep = {'DX': DX, 'candidate': str(CAND), 'candidateSha256': sha(CAND), 'stages': STAGES}
S, prov = solids()
rep['solidProvenance'] = prov
C16 = S['head_cap']
Ct = trimesh.load(CAND, force='mesh'); C2 = to_mf(Ct)
c10, s10 = math.cos(math.radians(10)), math.sin(math.radians(10))
A = np.array([c10, 0, -s10]); EY = np.array([0, 1.0, 0]); CT = np.array([s10, 0, c10])
SHIFT = np.array([-DX, 0, 0]); UP = np.array([0, 0, 1.0])
fixed = [k for k in FIXED if k in S]
F = union([S[k] for k in fixed])
pi_keys = sorted(k for k in S if k == 'pi' or (k.startswith('head_pi') and 'receiving' not in k))
gpio = [f'head_pi_gpio_pin_{p:02d}_receiving' for p in USED_PINS]
ride = SPEAKER + ['amplifier']

def ov_parts(M, keys, tol=1e-3):
    out = {}
    for k in keys:
        v = overlap(M, S[k])
        if v > tol:
            out[k] = round(v, 4)
    return out

# ---------------- A. final pose
prog('loaded')
final = {}
if 'A' not in STAGES: final = None
for label, cap, d in ([('V1.6', C16, np.zeros(3)), ('candidate', C2, SHIFT)] if 'A' in STAGES else []):
    rows = {'cap': ov_parts(cap, fixed)}
    for k in ride:
        h = ov_parts(S[k], fixed)
        if h: rows[k] = h
    for k in pi_keys + gpio:
        h = ov_parts(tr(S[k], d), fixed)
        if h: rows[k] = h
    # internal: the cap against what it carries
    internal = {}
    for k in pi_keys + gpio + ride:
        v = overlap(cap, tr(S[k], d) if k not in ride else S[k])
        if v > 1e-3: internal[k] = round(v, 4)
    final[label] = {'againstFixed': rows, 'capAgainstCarried': internal}
rep['A_finalPose'] = final
prog('A done')

# ---------------- B. descent
def sweep_sampled(M, step, top=40.0):
    base = overlap(M, F)
    worst, at = 0.0, None
    hs = np.arange(0.0, top + 1e-9, step)
    for h in hs:
        v = overlap(tr(M, [0, 0, h]), F)
        if v - base > worst:
            worst, at = v - base, h
    res = {'finalOverlapMm3': round(base, 4), 'maxExcessMm3': round(worst, 4), 'atHeightMm': at, 'samples': len(hs), 'stepMm': step}
    if at is not None and worst > 1e-3:
        Mh = tr(M, [0, 0, at]); res['parts'] = {k: round(overlap(Mh, S[k]) - overlap(M, S[k]), 4) for k in fixed if overlap(Mh, S[k]) - overlap(M, S[k]) > 1e-3}
    return res
B = {}
if 'B' in STAGES:
  B['V1.6 cap+speaker+amplifier (0.25 mm)'] = sweep_sampled(union([C16] + [S[k] for k in ride]), 0.25)
  prog('B baseline done')
  added = C2 - C16
  B['candidate added material (0.25 mm)'] = sweep_sampled(added, 0.25)
  B['candidateAddedVolumeMm3'] = added.volume()
  prog('B added done')
def hull_sweep(keys, d):
    out = {}
    for k in keys:
        Q = tr(S[k], d) if not k.startswith('pi') else tr(S[k], d)
        Q = mf.Manifold.hull(Q); H = mf.Manifold.hull(union([Q, tr(Q, [0, 0, 40])]))
        h = ov_parts(H, fixed)
        if h: out[k] = h
    return out
if 'B' in STAGES:
  B['V1.6 Pi group + GPIO housing (exact convex sweeps)'] = hull_sweep(pi_keys + gpio, np.zeros(3))
  B['candidate Pi group + GPIO housing (exact convex sweeps)'] = hull_sweep(pi_keys + gpio, SHIFT)
rep['B_descent'] = B
prog('B done')
if 'C' not in STAGES:
    json.dump(rep, open(HERE / f'verify-DX{DX}-{STAGES}.json', 'w'), indent=1); print(json.dumps({k: v for k, v in rep.items() if k != 'solidProvenance'}, indent=1)); sys.exit(0)

# ---------------- C. side effects
Cx = {}
# C1 screws: seats from guide/content/fasteners.json E-pi-01..04 (head seat on the Pi front face), axis into the rail
seats = {'E-pi-01 (-y lower)': [61.941, -29.0, 117.245], 'E-pi-02 (+y lower)': [61.941, 29.0, 117.245],
         'E-pi-03 (-y upper)': [65.935, -29.0, 139.895], 'E-pi-04 (+y upper)': [65.935, 29.0, 139.895]}
ax = np.array([-0.984808, 0.0, 0.173648])
def screw(p0, L, r=1.0):
    seg = trimesh.creation.cylinder(radius=r, segment=[p0, p0 + L * ax], sections=24)
    return to_mf(seg)
def material_along(capmesh, p0, s0, s1, r=0.95):
    """Shortest length of cap material between s0 and s1 along the screw axis, over 12 lines at radius r (thread flank)."""
    e1 = np.cross(ax, [0, 1, 0]); e1 /= np.linalg.norm(e1); e2 = np.cross(ax, e1)
    lens = []
    for k in range(12):
        th = 2 * math.pi * k / 12; o = p0 + r * (math.cos(th) * e1 + math.sin(th) * e2)
        ss = np.linspace(s0, s1, int((s1 - s0) / 0.02) + 1)
        P = o[None, :] + ss[:, None] * ax[None, :]
        inside = np.concatenate([capmesh.contains(P[j:j + 100]) for j in range(0, len(P), 100)])
        lens.append(float(inside.sum() * 0.02))
    return min(lens), max(lens)
screws = {}
C16_tm = trimesh.load(CAP_V16, force='mesh')
for name, c in seats.items():
    c = np.array(c)
    row = {}
    for label, cap_tm, d in [('V1.6', C16_tm, np.zeros(3)), ('candidate', Ct, SHIFT)]:
        p0 = c + d
        mat_lo, mat_hi = material_along(cap_tm, p0, 1.55, 8.0)
        r = {'railMaterialAlongAxisFrom1.55mm': [round(mat_lo, 2), round(mat_hi, 2)]}
        for L in (6.0, 4.0):
            M = screw(p0, L)
            r[f'M2x{L:.0f}'] = {'tipXYZ': r3(p0 + L * ax), 'engagementMinMm': round(material_along(cap_tm, p0, 1.55, L)[0], 2),
                                 'hitsFixed': ov_parts(M, fixed, 1e-3)}
        row[label] = r
    screws[name] = row
Cx['screws'] = screws
prog('C1 done')

# C2 rail sections (cap material inside each rail's y band, behind the Pi) at z levels
def rail_sections(cap_tm, ylo, yhi, xlo, xhi):
    out = {}
    for z in [115.0, 117.5, 120.0, 122.0, 124.0, 126.0, 128.0, 132.0, 136.0, 140.0, 144.0, 146.0]:
        sec = cap_tm.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if sec is None: continue
        pl, _ = sec.to_2D(to_2D=trimesh.transformations.translation_matrix([0, 0, -z]))
        import shapely.geometry as sg
        win = sg.box(xlo, ylo, xhi, yhi)
        area, Iyy, xs = 0.0, 0.0, []
        for poly in pl.polygons_full:
            g = poly.intersection(win)
            if g.is_empty: continue
            area += g.area
            if g.area > 0:
                xs.append((g.bounds[0], g.bounds[2]))
        if area > 0:
            out[f'{z}'] = {'areaMm2': round(area, 2), 'xRange': [round(min(a for a, b in xs), 2), round(max(b for a, b in xs), 2)]}
    return out
secs = {}
for label, cap_tm, d in [('V1.6', C16_tm, 0.0), ('candidate', Ct, DX)]:
    secs[label] = {'rail -y': rail_sections(cap_tm, -32.3, -25.7, 49.0 - 0 * d, 66.0 - d + 0.5),
                   'rail +y': rail_sections(cap_tm, 25.7, 32.3, 49.0, 66.0 - d + 0.5)}
Cx['railSectionsInYBand'] = secs
prog('C2 done')

# C3 roof joint footprint of each rail: xy projection of the rail material that penetrates the original shell roof
base_tm = trimesh.load(BASE_SHELL, force='mesh'); Bm = to_mf(base_tm)
def roof_clip(Rm, Rt):
    b = bbox(Rm); V = np.asarray(Rt.vertices); pts = V[V[:, 2] > b[1, 2] - 0.001]
    xy = np.unique(pts[:, :2], axis=0); ray = np.column_stack([xy, np.full(len(xy), 200.0)])
    loc, ind, _ = base_tm.ray.intersects_location(ray, np.tile([0, 0, -1.0], (len(ray), 1)), multiple_hits=True)
    outer = {}
    for q, i in zip(loc, ind):
        outer[int(i)] = max(outer.get(int(i), -1e10), q[2])
    limit = min(outer.values()) - 0.1
    return Rm ^ mf.Manifold.cube([300, 300, limit], False).translate([-150, -150, 0]), limit
def proj_area(M):
    m = mf_to_tm(M)
    if len(m.faces) == 0: return 0.0
    n = m.face_normals[:, 2]; return float((m.area_faces * np.clip(n, 0, None)).sum())
joints = {}
X_TRIM = float(os.environ.get('X_TRIM', '52.8'))
for i, (pth, side) in enumerate(zip(RAILS, ['-y', '+y'])):
    Rt = trimesh.load(pth, force='mesh'); Rm = to_mf(Rt)
    old, lim_old = roof_clip(Rm, Rt)
    Rts = Rt.copy(); Rts.apply_translation(SHIFT); new, lim_new = roof_clip(tr(Rm, SHIFT), Rts)
    if side == '+y': new = new ^ box([X_TRIM, -100, 0], [200, 100, 300])
    joints[f'rail {side}'] = {'V1.6 jointFootprintMm2': round(proj_area(old ^ Bm), 2), 'V1.6 roofClipZ': round(lim_old, 3),
                              'candidate jointFootprintMm2': round(proj_area(new ^ Bm), 2), 'candidate roofClipZ': round(lim_new, 3),
                              'V1.6 penetrationMm3': round((old ^ Bm).volume(), 3), 'candidate penetrationMm3': round((new ^ Bm).volume(), 3)}
Cx['roofJoint'] = joints
prog('C3 done')
# C4 CSI ribbon: camera connector end to Pi connector end (guide routes.json head_csi end points)
cam_end = np.array([73.0, -3.0, 131.0]); pi_end = np.array([69.0, -31.0, 128.0])
Cx['csi'] = {'straightOldMm': round(float(np.linalg.norm(pi_end - cam_end)), 2), 'straightNewMm': round(float(np.linalg.norm(pi_end + SHIFT - cam_end)), 2),
             'routeOldMm': 28.87, 'ribbonLengthMm': 200}
Cx['csi']['changeMm'] = round(Cx['csi']['straightNewMm'] - Cx['csi']['straightOldMm'], 2)

# C5 microSD side gap (+y board edge to the cap inner wall along +y) and USB-edge roof gap, before and after
def first_hit(mesh, o, d):
    loc, idx, _ = mesh.ray.intersects_location(np.array([o]), np.array([d]), multiple_hits=True)
    if len(loc) == 0: return None
    return float(np.min(np.linalg.norm(loc - o, axis=1)))
sd = {}
for label, mesh, d in [('V1.6', C16_tm, np.zeros(3)), ('candidate', Ct, SHIFT)]:
    rows = {}
    for t in (120.0, 125.0, 128.7, 132.0, 137.0):
        o = 41.5 * A + 32.5 * EY + t * CT + d   # 0.8 mm in front of the PCB front face, at the board +y edge
        rows[f't{t}'] = {'origin': r3(o), 'gapAlongPlusY': round(first_hit(mesh, o, [0, 1.0, 0]) or -1, 2)}
    sd[label] = rows
Cx['microSdSideGap'] = sd
usb = {}
ub = bbox(S['head_pi_component_bottom-usb-edge-context'])
for label, mesh, d in [('V1.6', C16_tm, np.zeros(3)), ('candidate', Ct, SHIFT)]:
    gaps = []
    for x in np.linspace(ub[0, 0], ub[1, 0], 5):
        for y in np.linspace(ub[0, 1], ub[1, 1], 5):
            o = np.array([x, y, ub[1, 2]]) + d
            g = first_hit(mesh, o, [0, 0, 1.0]); gaps.append(g if g is not None else 99)
    usb[label] = {'minRoofGapAboveUsbEdgeMm': round(min(gaps), 2), 'maxMm': round(max(gaps), 2)}
Cx['usbEdgeRoofGap'] = usb
prog('C5 done')

# C6 bundle_head route clearance (guide routes.json), tube radius 3.37 mm (6.73 mm notch bundle), ends near the header
routes = json.load(open(ROOT / 'guide/content/routes.json'))['routes']
bh = np.array(routes['bundle_head'], float)
def sample(path, step=0.25):
    P = []
    for a, b in zip(path[:-1], path[1:]):
        n = max(2, int(np.linalg.norm(b - a) / step) + 1)
        P.append(a + (b - a) * np.linspace(0, 1, n)[:, None])
    return np.vstack(P)
def min_dist(mesh, P):
    best = np.inf
    for i in range(0, len(P), 300):
        _, d, _ = trimesh.proximity.closest_point(mesh, P[i:i + 300]); best = min(best, float(d.min()))
    return best
pig_old = mf_to_tm(union([S[k] for k in pi_keys])); pig_new = pig_old.copy(); pig_new.apply_translation(SHIFT)
bh_new = bh.copy(); bh_new[-3:] += SHIFT   # the last three waypoints run along the Pi to the header
Ps_old, Ps_new = sample(bh), sample(bh_new)
inside_old = sum(C16_tm.contains(Ps_old[j:j+100]).sum() for j in range(0, len(Ps_old), 100)); inside_new = sum(Ct.contains(Ps_new[j:j+100]).sum() for j in range(0, len(Ps_new), 100))
Cx['bundleHead'] = {'V1.6': {'minDistToCapMm': round(min_dist(C16_tm, Ps_old), 2), 'samplesInsideCap': int(inside_old), 'minDistToPiGroupMm': round(min_dist(pig_old, Ps_old), 2)},
                    'candidate (last 3 waypoints moved with the Pi)': {'minDistToCapMm': round(min_dist(Ct, Ps_new), 2), 'samplesInsideCap': int(inside_new), 'minDistToPiGroupMm': round(min_dist(pig_new, Ps_new), 2)},
                    'note': 'Centreline distance; the drawn tube radius is 0.8-1.1 mm per wire and the notch passes a 6.7 mm bundle.'}
# notch region unchanged
Nb = box([-34.5, 7.0, 110.0], [-19.0, 30.0, 124.0])
prog('C6 done')
Cx['notchRegionXorMm3'] = ((C16 ^ Nb) - (C2 ^ Nb)).volume() + ((C2 ^ Nb) - (C16 ^ Nb)).volume()

# C7 no-part-change alternatives: free length in front of each used pin tip (plug the housing after the cap), today
Ft = mf_to_tm(union([S[k] for k in CAMERA_STACK + ['head_bottom', 'jaw_frame', 'lower_pad']]))
free = {}
for p in USED_PINS:
    k = (p + 1) // 2; y = 25.4 - 2.54 * k + 1.27; t = (124.949 if p % 2 else 127.489)
    o = 49.191 * A + y * EY + t * CT
    free[p] = round(first_hit(Ft, o, A) or 99, 2)
Cx['freeLengthBeyondPinTipAlongPinAxisMm'] = free
# rear travel available to today's populated cap before the +y rail meets jaw_support (rail at z < jaw top)
r1 = mf_to_tm(C16 ^ box([50.0, 25.0, 111.0], [66.0, 33.0, 130.3]))
Cx['todayRailPlusYMinX_below_z130'] = round(float(r1.vertices[:, 0].min()), 3)
Cx['jawSupportMaxX_y20to34'] = round(float(bbox(S['jaw_support'] ^ box([40, 20, 111], [60, 34, 131]))[1, 0]), 3)
rep['C_sideEffects'] = Cx
prog('C done')
json.dump(rep, open(HERE / f'verify-DX{DX}-{STAGES}.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in rep.items() if k != 'solidProvenance'}, indent=1))
