"""Native readback of one Orange slice for the head_cap pose comparison.
Usage: review_cap_pose.py RUN_DIR MACHINE OUT.json
Reads RUN_DIR/preparation.json and RUN_DIR/native/Orange_MACHINE/sliced.3mf (read-only).
Reports: ETA, grams, native first layer (release pipeline parser), total support extrusion on the cap, support touching
functional features (feature list reproduced read-only from 14-HEAD-TRIAL functional-review/audit_holes.py), notch tie
slots and 6.7 mm cable-passage core (same tests as release-V1.6/scripts/cap_support_contacts.py), and support outside
the cap's convex hull (proxy for scars on the outer dome; inference, not a surface-contact proof)."""
import sys, json, re, math, numpy as np, trimesh
from pathlib import Path
sys.dont_write_bytecode = True
sys.path.insert(0, '/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009')
import release_pipeline as r
RUN, MACHINE, OUT = Path(sys.argv[1]).resolve(), sys.argv[2], sys.argv[3]
B = Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913')
F = B / 'workflow-review-20261009/enclosed-wiring-repair/power-sensor/head-controller-study/final-integration-20261009'
rep = json.load(open('/Users/xiangzheng/code/robotics/microduck-sim/guide/print/release-V1.6/evidence/cap-notch-report-snapshot.json'))
W2P = np.array(rep['worldToPrint']['matrix4x4'])

def tf(p, t, vector=False): t = np.array(t); return (t[:3, :3] @ np.array(p)) + (0 if vector else t[:3, 3])
feats = []
def add(name, p, a, lo, hi, rad): feats.append(dict(name=name, o=np.array(p, float), a=np.array(a, float) / np.linalg.norm(a), lo=lo, hi=hi, r=rad))
for m in json.load(open(F / 'integrated-rigid-package.json'))['mountFeatures'][:4]: add(m['key'], m['seat'], m['axis'], .15, 4.7, .85)
pm = json.load(open(F / 'custom-harness-package.json'))['piCurrentWorldDelta']
for i, row in enumerate(json.load(open(F / 'pi-mount-roof-rays.json'))['rows']):
    for j, x in enumerate((47.5, 70.5)): add(f'pi-pilot-{i}-{j}', tf([x, row['sourceY'], 125.9], pm), tf([0, 0, 1], pm, True), .55, 4.6, .85)
for i, x in enumerate((5, 45)): add(f'speaker-pilot-{i}', [x, -21.5, 136.45], [0, 0, 1], .15, 3.1, 1.05)
for i, x in enumerate((32.3499993896, 19.6499993896)): add(f'amp-pilot-{i}', [x, 17.287000885, 134.0849994], [0, 0, 1], .15, 7.0, 1.05)
body = json.load(open(B.parents[1] / 'hardware-design-20260912/whole-robot-20260912/assembly/body-transforms.json'))['zero_joint_body_transforms']['jaw_soft']
fast = next(x for x in json.load(open(B / 'assembly-fasteners.json'))['connections'] if x['id'] == 'head_cap_closure')
for i, p in enumerate(fast['hole_centers_mm']): add(f'cap-closure-{i}', tf(p, body), tf(fast['axis'], body, True), 3.2, 7.6, fast['pilot_diameter_mm'] / 2)

prep = r.read(RUN / 'preparation.json'); row = next(x for x in prep['rows'] if x['color'] == 'Orange' and x['machine'] == MACHINE)
part = next(p for p in prep['parts'] if p['key'] == 'head_cap'); S = np.array(part['sourceToPrint'])
t = np.array(next(p['translation'] for p in row['placements'] if p['key'] == 'head_cap')) + [0, 0, part['dropToBedMm']]
plate2world = np.linalg.inv(W2P) @ np.linalg.inv(S)
cap = trimesh.load(part['source']['path'], force='mesh'); cap.apply_transform(np.linalg.inv(W2P))  # robot frame
hull = cap.convex_hull; Hn, Hd = hull.face_normals, np.einsum('ij,ij->i', hull.face_normals, hull.triangles[:, 0])
capbox = np.array(row['modelBounds'][[p['key'] for p in row['placements']].index('head_cap')])
L = rep['localFrame']; n_, u_, b_, o_ = (np.array(L[k]) for k in ('n_outwardWallNormal', 't_wallTangent', 'b_upAlongWall', 'originWorld'))

arch = RUN / f'native/Orange_{MACHINE}/sliced.3mf'; g, cfg, _ = r.native_payload(arch)
res = r.read(RUN / f'native/Orange_{MACHINE}/result.json'); assert r.digest(g) == res['gcodeSha256']
off = list(map(float, cfg.get('extruder_offset', ['0x0'])[0].split('x'))) if MACHINE == 'Bambu' else [0., 0.]
xyz = [0., 0., 0.]; kind = ''; relative = True; e = 0.; width = .42; height = .2
P = []; capSupportLen = 0.; capSupportE = 0.; ifaceLen = 0.; supportLayers = set()
for line in g.decode().splitlines():
    if line.startswith(('; FEATURE:', ';TYPE:')): kind = line.split(':', 1)[1].strip().lower()
    elif line.startswith((';WIDTH:', '; LINE_WIDTH:')): width = float(line.split(':', 1)[1])
    elif line.startswith((';HEIGHT:', '; LAYER_HEIGHT:')): height = float(line.split(':', 1)[1])
    elif line.startswith('M83'): relative = True
    elif line.startswith('M82'): relative = False
    elif line.startswith('G92 '):
        m_ = re.search(r'E([-+\d.]+)', line)
        if m_: e = float(m_[1])
    if not re.match(r'^G[0123] ', line): continue
    v = {k: float(q) for k, q in re.findall(r'([XYZEIJ])([-+]?\d*\.?\d+)', line.split(';')[0])}
    end = [v.get(k, xyz[i]) for i, k in enumerate('XYZ')]; de = v.get('E', 0) if relative else v.get('E', e) - e
    if 'E' in v: e = v['E'] if not relative else e + v['E']
    if de > 0 and 'support' in kind and end[:2] != xyz[:2]:
        pts2 = [(xyz[0], xyz[1]), (end[0], end[1])]
        if line.startswith(('G2 ', 'G3 ')) and ('I' in v or 'J' in v):
            cx, cy = xyz[0] + v.get('I', 0), xyz[1] + v.get('J', 0); rr = math.hypot(xyz[0] - cx, xyz[1] - cy)
            a0 = math.atan2(xyz[1] - cy, xyz[0] - cx); a1 = math.atan2(end[1] - cy, end[0] - cx); sg = 1 if line.startswith('G3') else -1
            span = ((a1 - a0) * sg) % (2 * math.pi) or 2 * math.pi; nn = max(2, int(span * rr / .5))
            pts2 = [(cx + rr * math.cos(a0 + sg * span * i / nn), cy + rr * math.sin(a0 + sg * span * i / nn)) for i in range(nn + 1)]
        for (x0, y0), (x1, y1) in zip(pts2, pts2[1:]):
            seg = math.hypot(x1 - x0, y1 - y0); k = max(1, int(seg / .5))
            mid = [(x0 + x1) / 2 + off[0], (y0 + y1) / 2 + off[1]]
            if capbox[0][0] - 8 <= mid[0] <= capbox[1][0] + 8 and capbox[0][1] - 8 <= mid[1] <= capbox[1][1] + 8:
                capSupportLen += seg; supportLayers.add(round(end[2], 2))
                if 'interface' in kind: ifaceLen += seg
                for f in np.linspace(0, 1, k + 1): P.append([x0 + f * (x1 - x0) + off[0], y0 + f * (y1 - y0) + off[1], end[2] - height / 2, width, height])
        if capbox[0][0] - 8 <= end[0] + off[0] <= capbox[1][0] + 8 and capbox[0][1] - 8 <= end[1] + off[1] <= capbox[1][1] + 8: capSupportE += de
    xyz = end
P = np.array(P); Pw = (plate2world @ np.c_[P[:, :3] - t, np.ones(len(P))].T).T[:, :3]; bead = np.hypot(P[:, 3] / 2, P[:, 4] / 2) + .012
feat = {}
for f in feats:
    d = Pw - f['o']; ax = d @ f['a']; rad = np.linalg.norm(d - np.outer(ax, f['a']), axis=1); inr = (ax >= f['lo']) & (ax <= f['hi'])
    feat[f['name']] = dict(supportCore=int((inr & (rad < f['r'] - bead)).sum()), supportPotential=int((inr & (rad < f['r'] + bead)).sum()),
                           within2mmOfBoreMouth=int(((ax >= f['lo'] - 2) & (ax <= f['hi'] + 2) & (rad < f['r'] + 2)).sum()))
loc = np.c_[(Pw - o_) @ n_, (Pw - o_) @ u_, (Pw - o_) @ b_]
slots = sum(int(((abs(loc[:, 1] - cu) <= 2.0) & (loc[:, 0] >= 0.8) & (loc[:, 0] <= 4.2) & (Pw[:, 2] > 119.0) & (Pw[:, 2] < 123.5)).sum()) for cu in (-4.4, 4.4))
core = int(((loc[:, 0] > -6) & (loc[:, 0] < 5.6) & (np.abs(loc[:, 1] + 1.0) < 3.4) & (np.abs(loc[:, 2] - 0.5) < 3.4)).sum())
nearNotch = int(((np.abs(loc[:, 0]) < 8) & (np.abs(loc[:, 1]) < 10) & (np.abs(loc[:, 2]) < 10)).sum())
sd = (Pw @ Hn.T - Hd).max(axis=1)  # >0 outside convex hull
exterior = sd > 0.6; extTouch = exterior & (sd < 1.5)
first, foot = r.first_layer(g, r.bound(row['project']), MACHINE)
secs = r.time_seconds(g, MACHINE); mins = math.ceil(secs / 60)
gr = float(re.search(r'total filament weight \[g\]\s*:\s*([\d.]+)' if MACHINE == 'Bambu' else r'total filament used \[g\]\s*=\s*([\d.]+)', g.decode())[1])
out = dict(run=str(RUN), machine=MACHINE, archive=r.ref(arch), gcodeSha256=res['gcodeSha256'], capSource=part['source'], sourceToPrint=S.tolist(),
           estimatedSeconds=secs, filenameTime=(f'{mins // 60}h' if mins >= 60 else '') + f'{mins % 60}m', filamentGrams=gr,
           nativeFirstLayer=first, footprintInsideBed=foot['insideBed'], minPairGapMm=min([p['conservativeGapMm'] for p in foot['pairs']] or [99]),
           capSupport=dict(pathLengthMm=round(capSupportLen, 0), interfacePathLengthMm=round(ifaceLen, 0), filamentMm=round(capSupportE, 0), layers=len(supportLayers),
                           samplePoints=len(P), outsideConvexHullPoints=int(exterior.sum()), outsideHullWithin1p5mmOfHullPoints=int(extTouch.sum()),
                           outsideHullWorldZRange=[round(float(Pw[exterior, 2].min()), 1), round(float(Pw[exterior, 2].max()), 1)] if exterior.any() else None),
           features=feat, notch=dict(inTieSlots=slots, inCablePassageCore=core, pointsWithin10mmOfNotchOrigin=nearNotch))
json.dump(out, open(OUT, 'w'), indent=1)
print(MACHINE, out['filenameTime'], secs, 's', gr, 'g', 'firstLayer', [(x['name'], round(x['model_area_mm2'], 1), x['modelIslands'], round(x['support_area_mm2'], 1)) for x in first])
print(' capSupport', out['capSupport']); print(' notch', out['notch'], 'minGap', round(out['minPairGapMm'], 2), 'inBed', foot['insideBed'])
print(' features core/potential/near:', {k: (v['supportCore'], v['supportPotential'], v['within2mmOfBoreMouth']) for k, v in feat.items()})
