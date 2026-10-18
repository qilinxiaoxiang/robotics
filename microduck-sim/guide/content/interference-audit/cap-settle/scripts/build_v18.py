"""Candidate head_cap V1.8: Pi seat moved DX mm back (robot -x) and DZ mm up (robot +z), for a 2x20 IDC socket.

Same edit as the released V1.7 (verify-cap/scripts/build_candidate.py), applied to the printed V1.6 cap:
  1. remove both Pi side rails and the two former OpenRB front bosses (inside fixed feature boxes the cap is replaced
     by the original community shell);
  2. add both rails from their source STLs translated by [-DX, 0, DZ], clipped 0.1 mm under the outer roof like
     union_cap.py;
  3. trim only the +y rail (in front of the jaw_support face at x 52.3) to x >= X_TRIM;
  4. NECK_WEB=1: thicken the trimmed +y rail neck forwards, into the empty space between the rail column and the Pi
     PCB back face (y 27.4..30.6, from inside the lower boss at z 121.5 up to z 131, front face NECK_CLEAR mm behind
     the PCB back plane, then a 5 mm taper back into the column so the print overhang stays under 10 degrees).
Everything outside the edit boxes is untouched (XOR proof). Print frame: the released world->stl rigid transform
(Kabsch on the V1.6 world/stl pair) and the release sourceToPrint. The Bambu support blocker for the +y upper Pi
pilot is moved with the seat.
Usage: DX=3.1 DZ=2.0 X_TRIM=54.4 build_v18.py <stl_outdir>   writes STLs there and ../candidate-build-<tag>.json
"""
import json, sys, os
from pathlib import Path
import numpy as np, trimesh
sys.path.insert(0, os.path.dirname(__file__))
from cs_lib import sha, to_mf, mf_to_tm, bbox, tr, union, box, ROOT, OUT, CAP_V16, CAP_V16_SHA, mf, solids, A

RD = ROOT / 'build-pack-20260913/redesign-20260913'
FI = RD / 'workflow-review-20261009/enclosed-wiring-repair/power-sensor/head-controller-study/final-integration-20261009'
BASE_SHELL = RD / 'head-redesign-20261008/curved-head/community-curved-head-world.stl'
RAILS = [FI / 'pi-roof-side-rail-0.stl', FI / 'pi-roof-side-rail-1.stl']
BOSSES = [FI / f'controller-roof-boss-{i}.stl' for i in (0, 2)]
CAP_V16_STL = CAP_V16.parent / 'stl-head_cap.stl'
CAP_V16_STL_SHA = 'f59be5c4fb60385dd654f6ea45aa26329f9f0c8e7f0cda480f10066140fe807f'
EXPECT = {str(BASE_SHELL): 'a4b8a357b466d5d131710ffa5a7ef36ff5e2182410e6074eaeeb03b1846a7b61',
          str(RAILS[0]): 'f786211d8269d9af41a89470c2d9ead7826b0e0bb6fdf9c2d681dffc39f2e4cc',
          str(RAILS[1]): '48e53ae8174fa424767141200f1025ca3453ead4e020ac77eb4a2b27f77ea1b7',
          str(BOSSES[0]): '249ae09d2e63afffc07436c0d62d37165503427868b113a89bbd234c2b67be7f',
          str(BOSSES[1]): '3bf2366474356762cd0c0c59c8cb5b48a56c5cfcb5d7530e36f3097102c15151'}

DX = float(os.environ.get('DX', '3.1')); DZ = float(os.environ.get('DZ', '2.0'))
X_TRIM = float(os.environ.get('X_TRIM', '54.4'))
NECK_WEB = os.environ.get('NECK_WEB', '0') == '1'; NECK_CLEAR = float(os.environ.get('NECK_CLEAR', '0.8'))
SHIFT = np.array([-DX, 0.0, DZ])
STL_OUT = Path(sys.argv[1]); STL_OUT.mkdir(parents=True, exist_ok=True)
TAG = os.environ.get('TAG', f'dx{DX}-dz{DZ}')
rep = {'DX': DX, 'DZ': DZ, 'X_TRIM': X_TRIM, 'NECK_WEB': NECK_WEB, 'NECK_CLEAR': NECK_CLEAR, 'seatShiftRobotFrameMm': SHIFT.tolist()}

assert sha(CAP_V16) == CAP_V16_SHA and sha(CAP_V16_STL) == CAP_V16_STL_SHA
for p, h in EXPECT.items():
    assert sha(p) == h, p
rep['inputs'] = {str(CAP_V16): CAP_V16_SHA, str(CAP_V16_STL): CAP_V16_STL_SHA, **EXPECT}

cap_tm = trimesh.load(CAP_V16, force='mesh', process=False)
C = to_mf(trimesh.load(CAP_V16, force='mesh'))
base_tm = trimesh.load(BASE_SHELL, force='mesh'); B = to_mf(base_tm)
R = [to_mf(trimesh.load(p, force='mesh')) for p in RAILS]
R_tm = [trimesh.load(p, force='mesh') for p in RAILS]
BO = [to_mf(trimesh.load(p, force='mesh')) for p in BOSSES]
assert C.status() == mf.Error.NoError and B.status() == mf.Error.NoError

FEATURE_BOXES = {'rail_-y': ([55.0, -32.7, 113.0], [65.5, -25.3, 160.0]), 'rail_+y': ([55.0, 25.3, 113.0], [65.5, 32.7, 160.0]),
                 'boss_-y': ([56.8, -13.1, 141.0], [63.1, -7.4, 160.0]), 'boss_+y': ([56.8, 7.4, 141.0], [63.1, 13.1, 160.0])}
rep['featureBoxes'] = FEATURE_BOXES
C1 = C
for lo, hi in FEATURE_BOXES.values():
    Bx = box(lo, hi)
    C1 = union([C1 - Bx, B ^ Bx])
chk = {}
for name, src in [('rail_-y', R[0]), ('rail_+y', R[1]), ('boss_-y', BO[0]), ('boss_+y', BO[1])]:
    bb = bbox(src); Bx = box(bb[0] - 1, bb[1] + 1)
    chk[name] = round(((C1 ^ Bx) - (B ^ Bx)).volume() + ((B ^ Bx) - (C1 ^ Bx)).volume(), 5)
rep['strippedEqualsBaseInFeatureBoxXorMm3'] = chk


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
    Rs = tr(Rm, SHIFT); Rts = Rt.copy(); Rts.apply_translation(SHIFT)
    Rc, limit, cut = roof_clip(Rs, Rts)
    clip_info[f'rail{i}'] = {'roofLimitZ': limit, 'clippedAboveRoofMm3': cut}
    if i == 1:
        keep = box([X_TRIM, -100, 0], [200, 100, 300])
        before = Rc.volume(); Rc = Rc ^ keep; clip_info['rail1']['trimmedMm3'] = before - Rc.volume()
    new_rails.append(Rc)
if NECK_WEB:
    pcb = mf_to_tm(tr(solids(['pi'])[0]['pi'], SHIFT))
    s_back = float((np.asarray(pcb.vertices) @ A).min()); s_web = s_back - NECK_CLEAR
    ca, sa = A[0], -A[2]
    xs = lambda z: (s_web + z * sa) / ca                      # x of the plane A.p = s_web at height z
    Y0, Y1, Z0, Z1, Z2 = 27.4, 30.6, 121.5, 131.0, 136.0
    col_back = lambda z: 53.35 + 0.17633 * (z - 123.5) + (3.3 - DX)   # untrimmed column back face (rail1 source, shifted)
    pts1 = [[x, y, z] for z in (Z0, Z1) for y in (Y0, Y1) for x in (X_TRIM, xs(z))]
    pts2 = [[x, y, Z1] for y in (Y0, Y1) for x in (X_TRIM, xs(Z1))] + \
           [[x, y, Z2] for y in (Y0, Y1) for x in (max(X_TRIM, col_back(Z2)), col_back(Z2) + 2.03)]
    web = union([mf.Manifold.hull_points(np.array(pts1)), mf.Manifold.hull_points(np.array(pts2))])
    rail1_before = new_rails[1].volume()
    new_rails[1] = union([new_rails[1], web])
    taper_dx = xs(Z1) - (col_back(Z2) + 2.03)
    clip_info['neckWeb'] = {'pcbBackPlaneS': s_back, 'webFrontPlaneS': s_web, 'clearanceToPcbBackMm': NECK_CLEAR,
                            'yRange': [Y0, Y1], 'zRange': [Z0, Z2], 'frontXAtZ': {str(z): round(xs(z), 3) for z in (Z0, 124.0, Z1)},
                            'addedToRailMm3': new_rails[1].volume() - rail1_before,
                            'taperOverhangFromVerticalDeg': float(np.degrees(np.arctan2(taper_dx, Z2 - Z1)))}
rep['roofClip'] = clip_info
rep['originalRoofLimitZ'] = {f'rail{i}': roof_clip(R[i], R_tm[i])[1] for i in range(2)}
C2 = union([C1] + new_rails)
assert C2.status() == mf.Error.NoError
pieces = C2.decompose()
real = [p for p in pieces if p.volume() > 0.01]
rep['booleanPieces'] = len(pieces)
rep['degeneratePiecesDroppedVolumeMm3'] = float(sum(p.volume() for p in pieces if p.volume() <= 0.01))
assert len(real) == 1, [p.volume() for p in real]
C2 = real[0]
rep['bodies'] = len(C2.decompose()); rep['genus'] = C2.genus(); rep['genusV16'] = C.genus()
rep['volumeV16Mm3'] = C.volume(); rep['volumeCandidateMm3'] = C2.volume()
removed = C - C2; added = C2 - C
rep['removedMm3'] = removed.volume(); rep['addedMm3'] = added.volume()
rep['addedBodies'] = [{'volumeMm3': round(p.volume(), 3), 'bounds': bbox(p).round(3).tolist()} for p in added.decompose() if p.volume() > 1e-4]
rep['removedBodies'] = [{'volumeMm3': round(p.volume(), 3), 'bounds': bbox(p).round(3).tolist()} for p in removed.decompose() if p.volume() > 1e-4]
edit_boxes = []
for M in [R[0], R[1], tr(R[0], SHIFT), tr(R[1], SHIFT), BO[0], BO[1]]:
    bb = bbox(M); edit_boxes.append(box(bb[0] - 0.5, bb[1] + 0.5))
E = union(edit_boxes)
rep['xorOutsideEditBoxesMm3'] = ((C - C2) - E).volume() + ((C2 - C) - E).volume()
rep['editBoxesBounds'] = [bbox(b).round(3).tolist() for b in edit_boxes]

out_tm = mf_to_tm(C2)
name = 'head_cap-idc-seat'
world = STL_OUT / f'{name}-world.stl'
world.write_text(trimesh.exchange.stl.export_stl_ascii(out_tm))
back = trimesh.load(world, force='mesh')
rep['worldReadback'] = {'watertight': bool(back.is_watertight), 'windingConsistent': bool(back.is_winding_consistent),
                        'volume': float(back.volume), 'bodies': len(back.split(only_watertight=False)),
                        'bounds': back.bounds.round(4).tolist(), 'boundsV16': cap_tm.bounds.round(4).tolist()}

stl_tm = trimesh.load(CAP_V16_STL, force='mesh', process=False)
Wv = np.asarray(cap_tm.vertices); Sv = np.asarray(stl_tm.vertices)
assert len(Wv) == len(Sv)
ca, cb = Wv.mean(0), Sv.mean(0); Hm = (Wv - ca).T @ (Sv - cb); U, Sg, Vt = np.linalg.svd(Hm)
d = np.sign(np.linalg.det(Vt.T @ U.T)); Rr = Vt.T @ np.diag([1, 1, d]) @ U.T; t = cb - Rr @ ca
res = np.linalg.norm(Wv @ Rr.T + t - Sv, axis=1)
W2S = np.eye(4); W2S[:3, :3] = Rr; W2S[:3, 3] = t
rep['worldToStlFrame'] = W2S.tolist(); rep['worldToStlResidualMm'] = {'max': float(res.max()), 'mean': float(res.mean())}
man16 = json.load(open(ROOT / 'guide/print/release-V1.6-final/final-V1.6.json'))
man17 = json.load(open(ROOT / 'guide/print/release-V1.7/manifest-V1.7.json'))
S2P = np.array(next(p for p in man16['parts'] if p['key'] == 'head_cap')['sourceToPrint'])
S2P17 = np.array(next(p for p in man17['parts'] if p['key'] == 'head_cap')['sourceToPrint'])
rep['sourceToPrint'] = S2P.tolist(); rep['sourceToPrintSameInV17'] = bool(np.allclose(S2P, S2P17))
W2P = S2P @ W2S; rep['worldToFlatPrint'] = W2P.tolist()
s_tm = out_tm.copy(); s_tm.apply_transform(W2S)
p_tm = out_tm.copy(); p_tm.apply_transform(W2P)
(STL_OUT / f'{name}-stlframe.stl').write_text(trimesh.exchange.stl.export_stl_ascii(s_tm))
(STL_OUT / f'{name}-print.stl').write_text(trimesh.exchange.stl.export_stl_ascii(p_tm))
rel_p = stl_tm.copy(); rel_p.apply_transform(S2P)


def flat_area(m):
    return float(m.area_faces[(m.face_normals[:, 2] < -0.99) & (m.triangles[:, :, 2].max(axis=1) < m.bounds[0, 2] + 0.02)].sum())


rep['printPose'] = {'candidateMinZ': float(p_tm.bounds[0, 2]), 'releasedMinZ': float(rel_p.bounds[0, 2]),
                    'candidateFlatAreaMm2': flat_area(p_tm), 'releasedFlatAreaMm2': flat_area(rel_p),
                    'candidateBounds': p_tm.bounds.round(3).tolist(), 'releasedBounds': rel_p.bounds.round(3).tolist()}
n_print = W2P[:3, :3] @ np.array([-1.0, 0, 0])
rep['trimFaceAngleFromPrintDownDeg'] = float(np.degrees(np.arccos(np.clip(-n_print[2], -1, 1))))

blk_path = Path(next(p for p in man16['parts'] if p['key'] == 'head_cap')['supportBlockers'][0]['path'])
blk = trimesh.load(blk_path, force='mesh')
pil_world = np.array([65.935 - 1.55 * 0.984808, 29.0, 139.895 + 1.55 * 0.173648])  # V1.6 +y upper pilot mouth
q16 = W2S[:3, :3] @ pil_world + W2S[:3, 3]
rep['supportBlocker'] = {'source': str(blk_path), 'sha256': sha(blk_path),
                         'v16PilotMouthInStlFrame': q16.round(3).tolist(),
                         'v16PilotInsideBlockerBounds': bool(np.all(q16 >= blk.bounds[0] - 1) and np.all(q16 <= blk.bounds[1] + 1))}
T = W2S @ np.array([[1, 0, 0, SHIFT[0]], [0, 1, 0, 0], [0, 0, 1, SHIFT[2]], [0, 0, 0, 1.0]]) @ np.linalg.inv(W2S)
b2 = blk.copy(); b2.apply_transform(T)
(STL_OUT / 'pi-positive-y-upper-hole-support-blocker-idc-seat.stl').write_text(trimesh.exchange.stl.export_stl_ascii(b2))
q = W2S[:3, :3] @ (pil_world + SHIFT) + W2S[:3, 3]
rep['supportBlocker'].update({'shiftTransformStlFrame': T.tolist(), 'movedPilotMouthInStlFrame': q.round(3).tolist(),
                              'movedPilotInsideMovedBlockerBounds': bool(np.all(q >= b2.bounds[0] - 1) and np.all(q <= b2.bounds[1] + 1))})
rep['outputs'] = {f.name: sha(f) for f in sorted(STL_OUT.glob('*.stl'))}
json.dump(rep, open(OUT / f'candidate-build-{TAG}.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in rep.items() if k not in ('inputs', 'editBoxesBounds', 'worldToStlFrame', 'worldToFlatPrint', 'sourceToPrint')}, indent=1))
