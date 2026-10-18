"""Candidate head_cap: Pi seat moved back DX mm (robot -x).

Edit, all exact manifold3d Booleans on the released V1.6 cap (guide/print/world/head_cap.stl):
  1. remove both Pi side rails and the two former OpenRB front bosses (material outside the original community shell);
  2. add the two rails from their source STLs translated by [-DX, 0, 0], clipped under the outer roof exactly as
     union_cap.py did for V1.5;
  3. trim only the +y rail (the one in front of the jaw_support face at x 52.3) to x >= X_TRIM.
Everything outside these features is untouched; the script proves it with an XOR outside the edit boxes.
Writes candidate files into OUT (argv[1]) and build-report.json.
"""
import json, sys, os
from pathlib import Path
import numpy as np, trimesh
sys.path.insert(0, os.path.dirname(__file__))
from vc import *

DX = float(os.environ.get('DX', '4.6'))
X_TRIM = float(os.environ.get('X_TRIM', '52.8'))
OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
rep = {'DX': DX, 'X_TRIM': X_TRIM}

cap_tm = trimesh.load(CAP_V16, force='mesh', process=False)
C = to_mf(trimesh.load(CAP_V16, force='mesh'))
base_tm = trimesh.load(BASE_SHELL, force='mesh'); B = to_mf(base_tm)
R = [to_mf(trimesh.load(p, force='mesh')) for p in RAILS]
R_tm = [trimesh.load(p, force='mesh') for p in RAILS]
BO = [to_mf(trimesh.load(BOSSES[i], force='mesh')) for i in (0, 2)]
assert C.status() == mf.Error.NoError and B.status() == mf.Error.NoError
rep['inputs'] = {str(p): sha(p) for p in [CAP_V16, CAP_V16_STL, BASE_SHELL] + RAILS + [BOSSES[0], BOSSES[2]]}

# 1. old feature material outside the base shell, measured; removed by replacing the cap inside a box around each
#    feature with the original community shell (inside these boxes the released cap is exactly shell + feature)
old_rails = [(C ^ r) - B for r in R]
old_bosses = [(C ^ b) - B for b in BO]
FEATURE_BOXES = {'rail_-y': ([55.0, -32.7, 113.0], [65.5, -25.3, 160.0]), 'rail_+y': ([55.0, 25.3, 113.0], [65.5, 32.7, 160.0]),
                 'boss_-y': ([56.8, -13.1, 141.0], [63.1, -7.4, 160.0]), 'boss_+y': ([56.8, 7.4, 141.0], [63.1, 13.1, 160.0])}
rep['featureBoxes'] = FEATURE_BOXES
C1 = C
for lo, hi in FEATURE_BOXES.values():
    Bx = box(lo, hi)
    C1 = union([C1 - Bx, B ^ Bx])
rep['removedFeatureVolumesMm3'] = {'rail_-y': old_rails[0].volume(), 'rail_+y': old_rails[1].volume(),
                                   'formerOpenRB_boss_-y': old_bosses[0].volume(), 'formerOpenRB_boss_+y': old_bosses[1].volume()}
# check: inside each feature box the stripped cap equals the base shell
chk = {}
for name, src in [('rail_-y', R[0]), ('rail_+y', R[1]), ('boss_-y', BO[0]), ('boss_+y', BO[1])]:
    bb = bbox(src); Bx = box(bb[0] - 1, bb[1] + 1)
    chk[name] = round(((C1 ^ Bx) - (B ^ Bx)).volume() + ((B ^ Bx) - (C1 ^ Bx)).volume(), 5)
rep['strippedEqualsBaseInFeatureBoxXorMm3'] = chk

# 2. shifted rails, clipped under the outer roof like union_cap.py (limit = lowest outer-roof hit over the rail top - 0.1)
def roof_clip(Rm, Rt):
    b = np.array(Rm.bounding_box()).reshape(2, 3)
    V = np.asarray(Rt.vertices)
    pts = V[V[:, 2] > b[1, 2] - 0.001]
    xy = np.unique(pts[:, :2], axis=0)
    ray = np.column_stack([xy, np.full(len(xy), 200.0)])
    loc, ind, _ = base_tm.ray.intersects_location(ray, np.tile([0, 0, -1.0], (len(ray), 1)), multiple_hits=True)
    outer = {}
    for q, i in zip(loc, ind):
        outer[int(i)] = max(outer.get(int(i), -1e10), q[2])
    assert len(outer) == len(ray)
    limit = min(outer.values()) - 0.1
    below = mf.Manifold.cube([300, 300, limit], False).translate([-150, -150, 0])
    return Rm ^ below, limit, (Rm - (Rm ^ below)).volume()

new_rails, clip_info = [], {}
for i, (Rm, Rt) in enumerate(zip(R, R_tm)):
    Rs = tr(Rm, [-DX, 0, 0]); Rts = Rt.copy(); Rts.apply_translation([-DX, 0, 0])
    Rc, limit, cut = roof_clip(Rs, Rts)
    clip_info[f'rail{i}'] = {'roofLimitZ': limit, 'clippedAboveRoofMm3': cut}
    if i == 1:  # +y rail: trim to x >= X_TRIM (jaw_support face at x 52.3 is behind it)
        keep = box([X_TRIM, -100, 0], [200, 100, 300])
        before = Rc.volume(); Rc = Rc ^ keep; clip_info['rail1']['trimmedMm3'] = before - Rc.volume()
    new_rails.append(Rc)
# also verify the original clip reproduces the released rails (same rule, DX = 0)
orig_clip = {f'rail{i}': roof_clip(R[i], R_tm[i])[1] for i in range(2)}
rep['roofClip'] = clip_info; rep['originalRoofLimitZ'] = orig_clip
C2 = union([C1] + new_rails)
assert C2.status() == mf.Error.NoError
pieces = C2.decompose()
real = [p for p in pieces if p.volume() > 0.01]
rep['booleanPieces'] = len(pieces); rep['degeneratePiecesDroppedVolumeMm3'] = float(sum(p.volume() for p in pieces if p.volume() <= 0.01))
assert len(real) == 1, [p.volume() for p in real]
C2 = real[0]
rep['bodies'] = len(C2.decompose()); rep['genus'] = C2.genus(); rep['genusV16'] = C.genus()
rep['volumeV16Mm3'] = C.volume(); rep['volumeCandidateMm3'] = C2.volume()
removed = C - C2; added = C2 - C
rep['removedMm3'] = removed.volume(); rep['addedMm3'] = added.volume(); rep['netMm3'] = C2.volume() - C.volume()
rep['removedBodies'] = [{'volumeMm3': round(p.volume(), 3), 'bounds': bbox(p).round(3).tolist()} for p in removed.decompose() if p.volume() > 1e-4]
rep['addedBodies'] = [{'volumeMm3': round(p.volume(), 3), 'bounds': bbox(p).round(3).tolist()} for p in added.decompose() if p.volume() > 1e-4]
# unchanged outside the edit boxes (rails old/new, bosses), incl. notch, hood, posts, rim
edit_boxes = []
for M in [R[0], R[1], tr(R[0], [-DX, 0, 0]), tr(R[1], [-DX, 0, 0]), BO[0], BO[1]]:
    bb = bbox(M); edit_boxes.append(box(bb[0] - 0.5, bb[1] + 0.5))
E = union(edit_boxes)
xor_out = ((C - C2) - E).volume() + ((C2 - C) - E).volume()
rep['xorOutsideEditBoxesMm3'] = xor_out
rep['editBoxesBounds'] = [bbox(b).round(3).tolist() for b in edit_boxes]

out_tm = mf_to_tm(C2)
world = OUT / 'head_cap-pi-shift-world.stl'
world.write_text(trimesh.exchange.stl.export_stl_ascii(out_tm))
back = trimesh.load(world, force='mesh')
rep['worldReadback'] = {'watertight': bool(back.is_watertight), 'windingConsistent': bool(back.is_winding_consistent),
                        'volume': float(back.volume), 'bodies': len(back.split(only_watertight=False)),
                        'bounds': back.bounds.round(4).tolist(), 'boundsV16': cap_tm.bounds.round(4).tolist()}

# 3. print frame: same rigid transform as the released stl/head_cap.stl, then the V1.6 sourceToPrint
stl_tm = trimesh.load(CAP_V16_STL, force='mesh', process=False)
Wv = np.asarray(cap_tm.vertices); Sv = np.asarray(stl_tm.vertices)
rep['worldVsStlVertexCounts'] = [len(Wv), len(Sv)]
def kabsch(A_, B_):
    ca, cb = A_.mean(0), B_.mean(0); H = (A_ - ca).T @ (B_ - cb); U, Sg, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T)); Rr = Vt.T @ np.diag([1, 1, d]) @ U.T; return Rr, cb - Rr @ ca
if len(Wv) == len(Sv):
    Rr, t = kabsch(Wv, Sv)
    res = np.linalg.norm(Wv @ Rr.T + t - Sv, axis=1)
else:
    # vertex orders differ: register with ICP from the bounding-box initial guess
    M0, _, _ = trimesh.registration.icp(Wv[::5], stl_tm, max_iterations=200, threshold=1e-9, scale=False, reflection=False)
    Rr, t = M0[:3, :3], M0[:3, 3]
    res = trimesh.proximity.closest_point(stl_tm, Wv @ Rr.T + t)[1]
W2S = np.eye(4); W2S[:3, :3] = Rr; W2S[:3, 3] = t
rep['worldToStlFrame'] = W2S.tolist(); rep['worldToStlResidualMm'] = {'max': float(res.max()), 'mean': float(res.mean())}
man = json.load(open(ROOT / 'guide/print/release-V1.6-final/final-V1.6.json'))
S2P = np.array(next(p for p in man['parts'] if p['key'] == 'head_cap')['sourceToPrint'])
rep['sourceToPrint'] = S2P.tolist()
W2P = S2P @ W2S; rep['worldToFlatPrint'] = W2P.tolist()
s_tm = out_tm.copy(); s_tm.apply_transform(W2S)
p_tm = out_tm.copy(); p_tm.apply_transform(W2P)
(OUT / 'head_cap-pi-shift-stlframe.stl').write_text(trimesh.exchange.stl.export_stl_ascii(s_tm))
(OUT / 'head_cap-pi-shift-print.stl').write_text(trimesh.exchange.stl.export_stl_ascii(p_tm))
# released flat pose for comparison
rel_p = stl_tm.copy(); rel_p.apply_transform(S2P)
def flat_area(m):
    return float(m.area_faces[(m.face_normals[:, 2] < -0.99) & (m.triangles[:, :, 2].max(axis=1) < m.bounds[0, 2] + 0.02)].sum())
rep['printPose'] = {'candidateMinZ': float(p_tm.bounds[0, 2]), 'releasedMinZ': float(rel_p.bounds[0, 2]),
                    'candidateFlatAreaMm2': flat_area(p_tm), 'releasedFlatAreaMm2': flat_area(rel_p),
                    'candidateBounds': p_tm.bounds.round(3).tolist(), 'releasedBounds': rel_p.bounds.round(3).tolist()}
# trimmed face orientation in the print pose (overhang check): world normal (-1,0,0) of the x = X_TRIM face
n_print = W2P[:3, :3] @ np.array([-1.0, 0, 0])
rep['trimFaceNormalInPrint'] = n_print.round(4).tolist()
rep['trimFaceAngleFromPrintDownDeg'] = float(np.degrees(np.arccos(np.clip(-n_print[2], -1, 1))))

# 4. Bambu support blocker for the +y upper Pi pilot: same file frame test, shifted copy
blk_path = Path(next(p for p in man['parts'] if p['key'] == 'head_cap')['supportBlockers'][0]['path'])
blk = trimesh.load(blk_path, force='mesh')
pil_world = np.array([65.935 - 1.55 * 0.984808, 29.0, 139.895 + 1.55 * 0.173648])  # pilot mouth on the rail face (fasteners.json E-pi-04)
cand = {}
for name, M in [('stlFrame', W2S), ('flatPrint', W2P)]:
    q = M[:3, :3] @ pil_world + M[:3, 3]
    cand[name] = {'pilotMouth': q.round(3).tolist(), 'insideBlockerBounds': bool(np.all(q >= blk.bounds[0] - 1) and np.all(q <= blk.bounds[1] + 1))}
rep['supportBlocker'] = {'path': str(blk_path), 'sha256': sha(blk_path), 'bounds': blk.bounds.round(3).tolist(), 'frameTest': cand}
frame = next((k for k, v in cand.items() if v['insideBlockerBounds']), None)
if frame:
    M = W2S if frame == 'stlFrame' else W2P
    T = M @ np.array([[1, 0, 0, -DX], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.0]]) @ np.linalg.inv(M)
    b2 = blk.copy(); b2.apply_transform(T)
    (OUT / 'pi-positive-y-upper-hole-support-blocker-shifted.stl').write_text(trimesh.exchange.stl.export_stl_ascii(b2))
    rep['supportBlocker']['frame'] = frame; rep['supportBlocker']['shiftTransform'] = T.tolist()
for f in ['head_cap-pi-shift-world.stl', 'head_cap-pi-shift-stlframe.stl', 'head_cap-pi-shift-print.stl', 'pi-positive-y-upper-hole-support-blocker-shifted.stl']:
    if (OUT / f).exists():
        rep.setdefault('outputs', {})[f] = sha(OUT / f)
json.dump(rep, open(OUT / 'build-report.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in rep.items() if k not in ('inputs', 'editBoxesBounds')}, indent=1))
