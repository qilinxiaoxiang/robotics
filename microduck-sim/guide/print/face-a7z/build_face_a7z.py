"""Face panel and eye trim for the Radxa Camera 13M 214 (IMX214) on the Cubie A7Z head.

Regenerates every output in this folder from the current world STLs in ../world/:
  face_panel_a7z.stl, eye_trim_a7z.stl, camera_13m214.stl   (robot frame, mm, x forward, y left, z up)
  face_panel_a7z-print.stl, eye_trim_a7z-print.stl          (V1.8 print poses from release-V1.8/manifest-V1.8.json)
  checks.json and render-*.png

Run through the bounded runner:
  python3 ../../../build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py \
      --max-mib 2500 --seconds 300 --wait-lock-seconds 600 -- /tmp/microduck-cad-venv/bin/python build_face_a7z.py
"""
import hashlib
import json
import math
import shutil
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
WORLD = HERE.parent / 'world'
MANIFEST = HERE.parent / 'release-V1.8' / 'manifest-V1.8.json'

# ---------------------------------------------------------------- camera data (Radxa drawing, photos)
PCB = 32.0            # +-0.2
PCB_T = 1.6
HOLE_PITCH = 28.0     # plated corner holes
HOLE_D = 2.2          # modelled for M2
SMALL_PITCH = 20.0    # two unplated holes on the centreline, parallel to the connector edge
SMALL_D = 1.8         # measured on the drawing (about 1.8 mm): too small for M2, not used
HOLDER = 8.5
HOLDER_H = 6.38       # holder top above PCB front face
BACK_LAYER = 1.5      # component height on the back
# The 31-pin FPC connector sits on the LENS side at one edge (Radxa product photos camera-13m-214-view.png and
# camera-13m-214-cubie-a7z.png). Box per the brief: 14 along the edge, 4 deep, 2 high.
CONN_W, CONN_D, CONN_H = 14.0, 4.0, 2.0
CONN_GAP = 0.3        # connector top to face back
RIBBON_W, RIBBON_T = 12.0, 0.3
RIBBON_X0 = 0.3       # ribbon underside above PCB front where it leaves the connector
RIBBON_TURN_Y = 33.0  # ribbon folds back towards the board here (cap boss inner face is at y 35.06..35.41)
RIBBON_BACK_X = 70.0  # end of the modelled stub after the fold
FOV_H, FOV_V, FOV_D = 66.2, 51.6, 78.4
PUPIL_R = 1.0         # entrance-pupil radius assumed for the cone apex (f/2.2 lens about 0.8; 1.0 for margin)

# ---------------------------------------------------------------- face geometry (V1.8, measured below)
FACE_BACK = 80.1
FACE_FRONT = 81.4
BOSS_R = 2.4
PILOT_D = 1.7
SKIN = 1.2            # material left in front of each blind pilot (minimum wall)
SCREW_HEAD_H = 1.6    # pan-head M2 self-tapping, conservative

# board space (A7Z behind the camera)
BOARD_BOX = np.array([[-1e3, -32.5, 114.8], [74.5, 32.5, 144.6]])
HEAD_PARTS = ['head_cap', 'head_bottom', 'jaw_frame', 'clip_cap', 'clip_head', 'amplifier', 'speaker']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def box(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return trimesh.creation.box(extents=hi - lo, transform=trimesh.transformations.translation_matrix((lo + hi) / 2))


def xcyl(r, x0, x1, y, z, sections=48):
    c = trimesh.creation.cylinder(radius=r, height=x1 - x0, sections=sections)
    T = trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0])
    c.apply_transform(T)
    c.apply_translation([(x0 + x1) / 2, y, z])
    return c


def union(ms):
    return trimesh.boolean.union(ms, engine='manifold')


def diff(a, bs):
    return trimesh.boolean.difference([a] + list(bs), engine='manifold')


def inter_vol(a, b):
    if not (a.is_watertight and b.is_watertight):
        return None
    try:
        r = trimesh.boolean.intersection([a, b], engine='manifold')
        return float(r.volume) if len(r.faces) else 0.0
    except Exception:
        return None


def point_box_dist(P, lo, hi):
    d = np.maximum(np.maximum(lo - P, P - hi), 0)
    return np.linalg.norm(d, axis=1)


def box_box_dist(a, b):
    d = np.maximum(np.maximum(a[0] - b[1], b[0] - a[1]), 0)
    return float(np.linalg.norm(d))


def crop(mesh, lo, hi, pad):
    tri = mesh.triangles
    tlo, thi = tri.min(1), tri.max(1)
    keep = np.all(thi >= lo - pad, 1) & np.all(tlo <= hi + pad, 1)
    if not keep.any():
        return None
    m = trimesh.Trimesh(mesh.vertices, mesh.faces[keep], process=False)
    m.remove_unreferenced_vertices()
    return m


def box_edge_samples(lo, hi, step=0.25):
    pts = []
    C = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    for i in range(8):
        for j in range(i + 1, 8):
            if np.count_nonzero(np.abs(C[i] - C[j]) > 1e-9) == 1:
                n = max(2, int(np.linalg.norm(C[j] - C[i]) / step) + 1)
                pts.append(np.linspace(C[i], C[j], n))
    return np.vstack(pts)


def box_mesh_dist(lo, hi, mesh, pad=12.0):
    """Minimum distance between an axis-aligned box and a mesh: mesh vertices plus dense surface samples against
    the box (exact point-box), and box edge samples against the mesh surface."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    c = crop(mesh, lo, hi, pad)
    if c is None:
        return float('inf')
    n = int(min(300000, max(2000, c.area * 25)))
    P = np.vstack([c.vertices, trimesh.sample.sample_surface(c, n, seed=2)[0]])
    d1 = point_box_dist(P, lo, hi).min()
    E = box_edge_samples(lo, hi)
    d2 = np.inf
    for k in range(0, len(E), 1500):
        _, dd, _ = trimesh.proximity.closest_point(c, E[k:k + 1500])
        d2 = min(d2, dd.min())
    return float(min(d1, d2))


# ---------------------------------------------------------------- load
# The V1.8 face and the CM3 camera this build starts from; world/face_panel.stl and world/camera_board.stl are now its output.
SRC = {'camera_board': 'camera_board-cm3', 'face_panel': 'face_panel-v18'}
W = {n: trimesh.load(WORLD / f'{SRC.get(n, n)}.stl') for n in ['camera_board', 'face_panel', 'eye_trim'] + HEAD_PARTS}
face18, trim18, cm3 = W['face_panel'], W['eye_trim'], W['camera_board']
checks = {'_doc': 'face-a7z checks; robot frame mm (x forward, y left, z up). Regenerate with build_face_a7z.py.',
          'sources': {f'world/{SRC.get(n, n)}.stl': sha(WORLD / f'{SRC.get(n, n)}.stl') for n in W},
          'assumptions': {}}

# axis: eye opening of the face, CM3 lens, trim bore
lens_v = cm3.vertices[cm3.vertices[:, 0] > 85.0]
cm3_lens_c = (lens_v.min(0) + lens_v.max(0)) / 2
eye_loop = None
for d in face18.section(plane_origin=[80.75, 0, 0], plane_normal=[1, 0, 0]).discrete:
    if 10 < np.ptp(d[:, 1]) < 20:
        eye_loop = d
eye_c = (eye_loop.min(0) + eye_loop.max(0)) / 2
bore = []
for d in trim18.section(plane_origin=[86.0, 0, 0], plane_normal=[1, 0, 0]).discrete:
    bore.append(d)
bore = [d for d in bore if 10 < np.ptp(d[:, 1]) < 20][0]
bore_c = (bore.min(0) + bore.max(0)) / 2
AY, AZ = float(eye_c[1]), float(eye_c[2])
CM3_LENS_FRONT = float(cm3.bounds[1, 0])
checks['axis'] = {
    'eyeOpeningCentre_face_x80.75': [round(AY, 3), round(AZ, 3)],
    'eyeOpeningRadius': round(float(np.ptp(eye_loop[:, 1]) / 2), 3),
    'trimBoreCentre_x86': [round(float(bore_c[1]), 3), round(float(bore_c[2]), 3)],
    'trimBoreRadius_x86': round(float(np.ptp(bore[:, 1]) / 2), 3),
    'cm3LensCentre': [round(float(cm3_lens_c[1]), 3), round(float(cm3_lens_c[2]), 3)],
    'cm3LensFrontX': round(CM3_LENS_FRONT, 3),
    'used': [round(AY, 3), round(AZ, 3)],
}

# ---------------------------------------------------------------- camera placement
PCB_FRONT = FACE_BACK - CONN_H - CONN_GAP          # 77.8
PCB_BACK = PCB_FRONT - PCB_T                       # 76.2
LENS_FRONT = PCB_FRONT + HOLDER_H                  # 84.18
h = PCB / 2
# connector edge faces +Y
pcb_lo, pcb_hi = np.array([PCB_BACK, AY - h, AZ - h]), np.array([PCB_FRONT, AY + h, AZ + h])
corners = [(AY + sy * HOLE_PITCH / 2, AZ + sz * HOLE_PITCH / 2) for sy in (-1, 1) for sz in (-1, 1)]
smalls = [(AY, AZ + s * SMALL_PITCH / 2) for s in (-1, 1)]
comp = {
    'pcb': (pcb_lo, pcb_hi),
    'lens_holder': (np.array([PCB_FRONT, AY - HOLDER / 2, AZ - HOLDER / 2]),
                    np.array([LENS_FRONT, AY + HOLDER / 2, AZ + HOLDER / 2])),
    'connector_front': (np.array([PCB_FRONT, AY + h - CONN_D, AZ - CONN_W / 2]),
                        np.array([PCB_FRONT + CONN_H, AY + h, AZ + CONN_W / 2])),
    'ribbon_flat': (np.array([PCB_FRONT + RIBBON_X0, AY + h - CONN_D + 1.0, AZ - RIBBON_W / 2]),
                    np.array([PCB_FRONT + RIBBON_X0 + RIBBON_T, RIBBON_TURN_Y + RIBBON_T, AZ + RIBBON_W / 2])),
    'ribbon_fold': (np.array([RIBBON_BACK_X, RIBBON_TURN_Y, AZ - RIBBON_W / 2]),
                    np.array([PCB_FRONT + RIBBON_X0 + RIBBON_T, RIBBON_TURN_Y + RIBBON_T, AZ + RIBBON_W / 2])),
}
# back components: only the corner at the connector edge (+Y) and the top, 0.7-13.5 mm from the connector edge and
# 0-12.8 mm from the top edge on Radxa's back photo (a7z-head/sources/camera-13m-214-view.png), plus 1 mm all round;
# the rest of the back, in front of the A7Z header, is bare board.
bl_lo, bl_hi = np.array([PCB_BACK - BACK_LAYER, AY + h - 14.5, AZ + h - 13.8]), np.array([PCB_BACK, AY + h, AZ + h])
comp['back_layer'] = (bl_lo, bl_hi)
corner_cut = [box([bl_lo[0] - 1, y - 2, z - 2], [PCB_BACK + 0.01, y + 2, z + 2]) for y, z in corners]

pcb_m = diff(box(pcb_lo, pcb_hi), [xcyl(HOLE_D / 2, PCB_BACK - 1, PCB_FRONT + 1, y, z) for y, z in corners] +
             [xcyl(SMALL_D / 2, PCB_BACK - 1, PCB_FRONT + 1, y, z) for y, z in smalls])
back_m = diff(box(bl_lo, bl_hi + np.array([0.01, 0, 0])), corner_cut)
cam_parts = {'pcb': pcb_m, 'back_layer': back_m}
for k in ['lens_holder', 'connector_front', 'ribbon_flat', 'ribbon_fold']:
    lo, hi = comp[k]
    cam_parts[k] = box(lo, hi)
camera = union([cam_parts['pcb'], back_m,
                box(comp['lens_holder'][0] - [0.01, 0, 0], comp['lens_holder'][1]),
                box(comp['connector_front'][0] - [0.01, 0, 0], comp['connector_front'][1]),
                box(*comp['ribbon_flat']), box(*comp['ribbon_fold'])])
camera.export(HERE / 'camera_13m214.stl')

# screws
CORNER_LEN, TRIM_LEN = 4.0, 6.0
trim_holes = [(-0.18, 120.6), (-0.18, 141.6)]     # V1.8 face holes and eye-trim pilots (v18-sources.json)
screws = {}
for i, (y, z) in enumerate(corners):
    screws[f'camera_corner_{i + 1}'] = dict(y=y, z=z, len=CORNER_LEN, head_x=(PCB_BACK - SCREW_HEAD_H, PCB_BACK),
                                            shank_x=(PCB_BACK, PCB_BACK + CORNER_LEN))
for i, (y, z) in enumerate(trim_holes):
    screws[f'trim_{"lower" if i == 0 else "upper"}'] = dict(y=y, z=z, len=TRIM_LEN,
                                                            head_x=(FACE_BACK - SCREW_HEAD_H, FACE_BACK),
                                                            shank_x=(FACE_BACK, FACE_BACK + TRIM_LEN))

# ---------------------------------------------------------------- face panel A7Z
# 1. remove the V1.8 camera lands and pegs (everything of the face behind x 80.1 in the camera area)
cut = box([70.0, AY - 20, AZ - 20], [FACE_BACK, AY + 20, AZ + 20])
face = diff(face18, [cut])
removed = float(face18.volume - face.volume)
# 2. four corner bosses with blind 1.7 mm pilots
PILOT_END = FACE_FRONT - SKIN                         # 80.2
bosses = [xcyl(BOSS_R, PCB_FRONT, FACE_BACK + 0.4, y, z) for y, z in corners]
face = union([face] + bosses)
face = diff(face, [xcyl(PILOT_D / 2, PCB_FRONT - 1.0, PILOT_END, y, z, 32) for y, z in corners])
face.export(HERE / 'face_panel_a7z.stl')

# ---------------------------------------------------------------- eye trim: unchanged V1.8 part
shutil.copyfile(WORLD / 'eye_trim.stl', HERE / 'eye_trim_a7z.stl')
trim = trimesh.load(HERE / 'eye_trim_a7z.stl')

# ---------------------------------------------------------------- print poses
man = json.loads(MANIFEST.read_text())
pose = {p['key']: np.array(p['sourceToPrint']) for p in man['parts'] if p['key'] in ('face_panel', 'eye_trim')}
prints = {}
for key, mesh, out in [('face_panel', face, 'face_panel_a7z-print.stl'), ('eye_trim', trim, 'eye_trim_a7z-print.stl')]:
    m = mesh.copy()
    m.apply_transform(pose[key])
    m.export(HERE / out)
    ref = (face18 if key == 'face_panel' else trim18).copy()
    ref.apply_transform(pose[key])

    def overhang(mm):
        n, a, c = mm.face_normals, mm.area_faces, mm.triangles_center
        sel = (n[:, 2] < -math.cos(math.radians(45))) & (c[:, 2] > 0.05)
        return round(float(a[sel].sum()), 2)

    def bed(mm):
        n, a, c = mm.face_normals, mm.area_faces, mm.triangles_center
        return round(float(a[(n[:, 2] < -0.999) & (c[:, 2] < 0.05)].sum()), 1)

    prints[key] = {'file': out, 'minZ': round(float(m.bounds[0, 2]), 4), 'bedContactMm2': bed(m),
                   'overhangOver45degMm2': overhang(m), 'v18OverhangOver45degMm2': overhang(ref),
                   'v18BedContactMm2': bed(ref), 'heightMm': round(float(m.bounds[1, 2] - m.bounds[0, 2]), 2)}

# ---------------------------------------------------------------- checks: meshes
def mesh_info(m, path):
    return {'file': path, 'watertight': bool(m.is_watertight), 'volumeMm3': round(float(m.volume), 2),
            'bounds': np.round(m.bounds, 3).tolist(), 'sha256': sha(HERE / path)}

checks['meshes'] = {'face_panel_a7z': mesh_info(face, 'face_panel_a7z.stl'),
                    'eye_trim_a7z': mesh_info(trim, 'eye_trim_a7z.stl'),
                    'camera_13m214': mesh_info(camera, 'camera_13m214.stl'),
                    'face_panel_v18_volumeMm3': round(float(face18.volume), 2),
                    'face_removed_v18_lands_pegs_mm3': round(removed, 2),
                    'eye_trim_identical_to_v18': sha(HERE / 'eye_trim_a7z.stl') == sha(WORLD / 'eye_trim.stl')}
checks['printPoses'] = prints

# front shape unchanged: compare face front (x > 80.1) and trim by ray casting from the front on a grid
gy, gz = np.meshgrid(np.arange(-43, 43.5, 1.0), np.arange(111, 154.5, 1.0))
O = np.c_[np.full(gy.size, 120.0), gy.ravel(), gz.ravel()]
D = np.tile([-1.0, 0, 0], (len(O), 1))


def first_hit(m):
    loc, idx, _ = m.ray.intersects_location(O, D, multiple_hits=False)
    out = np.full(len(O), np.nan)
    out[idx] = loc[:, 0]
    return out


fa, fb = first_hit(face), first_hit(face18)
both = ~np.isnan(fa) & ~np.isnan(fb)
checks['frontUnchanged'] = {'face_raysOnGrid1mm': int(both.sum()),
                            'face_maxFrontDeviationMm': float(np.nanmax(np.abs(fa[both] - fb[both]))),
                            'face_hitMaskSame': bool(np.array_equal(np.isnan(fa), np.isnan(fb))),
                            'eye_trim': 'byte-identical copy of world/eye_trim.stl'}

# ---------------------------------------------------------------- optics: cone clearance
tanD = math.tan(math.radians(FOV_D / 2))
mat = {'face_panel_a7z': face, 'eye_trim_a7z': trim, 'head_cap': W['head_cap'], 'head_bottom': W['head_bottom'],
       'jaw_frame': W['jaw_frame']}
cone = {}
for name, m in mat.items():
    c = crop(m, np.array([LENS_FRONT, AY - 60, AZ - 60]), np.array([LENS_FRONT + 60, AY + 60, AZ + 60]), 0)
    if c is None:
        continue
    P = np.vstack([c.vertices, trimesh.sample.sample_surface(c, 200000, seed=1)[0]])
    a = P[:, 0] - LENS_FRONT
    rho = np.hypot(P[:, 1] - AY, P[:, 2] - AZ)
    sel = a > 1e-6
    a, rho, P = a[sel], rho[sel], P[sel]
    radial = rho - (PUPIL_R + a * tanD)
    normal = radial * math.cos(math.radians(FOV_D / 2))
    ang = np.degrees(np.arctan2(rho - PUPIL_R, a)) - FOV_D / 2
    i = int(np.argmin(normal))
    # rectangular field (portrait in the world: H 66.2 along z, V 51.6 along y)
    ty, tz = math.tan(math.radians(FOV_V / 2)), math.tan(math.radians(FOV_H / 2))
    inside_rect = (np.abs(P[:, 1] - AY) - PUPIL_R <= a * ty) & (np.abs(P[:, 2] - AZ) - PUPIL_R <= a * tz)
    cone[name] = {'minNormalClearanceMm': round(float(normal.min()), 3),
                  'minRadialClearanceMm': round(float(radial.min()), 3),
                  'minAngularMarginDeg': round(float(ang.min()), 2),
                  'closestPoint': np.round(P[i], 2).tolist(),
                  'pointsInsideRectangularField': int(inside_rect.sum())}
checks['optics'] = {
    'lensAxis_yz': [round(AY, 3), round(AZ, 3)], 'lensFrontX': round(LENS_FRONT, 3),
    'cm3LensFrontX': round(CM3_LENS_FRONT, 3), 'lensFrontBehindCm3Mm': round(CM3_LENS_FRONT - LENS_FRONT, 3),
    'coneHalfAngleDeg': FOV_D / 2, 'pupilRadiusMm': PUPIL_R,
    'method': 'circular cone of the 78.4 deg diagonal from a 1.0 mm pupil disc at the lens front; clearance '
              'of every vertex and 200k surface samples of each part in front of the lens. Negative = clipped. '
              'The rectangular field (66.2 x 51.6, turned portrait) lies inside this cone.',
    'perPart': cone,
    'clipped': any(v['minNormalClearanceMm'] < 0 for v in cone.values()),
    'imageRotation': 'connector edge = image bottom, now on robot +Y: the image comes out turned 90 deg; '
                     'rotate it 90 deg clockwise for an upright view (check with one frame).',
}

# ---------------------------------------------------------------- clearances
clear = {}
head = {n: W[n] for n in HEAD_PARTS}
others = dict(head)
others['face_panel_a7z'] = face
others['eye_trim_a7z'] = trim
for k, (lo, hi) in comp.items():
    row = {}
    for n, m in others.items():
        row[n] = round(box_mesh_dist(lo, hi, m), 3)
    row['board_space_box'] = round(box_box_dist((lo, hi), BOARD_BOX), 3)
    clear[k] = row
# designed contact: PCB front on the four boss tops
for n, m in others.items():
    v = inter_vol(camera, m)
    clear.setdefault('_intersectionVolumeCameraMm3', {})[n] = None if v is None else round(v, 4)
# screw heads
for s, d in screws.items():
    lo = np.array([d['head_x'][0], d['y'] - 2.0, d['z'] - 2.0])
    hi = np.array([d['head_x'][1], d['y'] + 2.0, d['z'] + 2.0])
    row = {n: round(box_mesh_dist(lo, hi, m), 3) for n, m in head.items()}
    row['board_space_box'] = round(box_box_dist((lo, hi), BOARD_BOX), 3)
    for k in ('lens_holder', 'connector_front', 'ribbon_flat'):
        row[k] = round(box_box_dist((lo, hi), comp[k]), 3)
    if s.startswith('trim'):
        row['pcb_front_gap'] = round(d['head_x'][0] - PCB_FRONT, 3)
    clear[f'head_of_{s}'] = row
# face bosses against the head parts
for n, m in head.items():
    v = inter_vol(face, m)
    clear.setdefault('_intersectionVolumeFaceA7zMm3', {})[n] = None if v is None else round(v, 4)
    v18 = inter_vol(face18, m)
    clear.setdefault('_intersectionVolumeFaceV18Mm3', {})[n] = None if v18 is None else round(v18, 4)
for j, (y, z) in enumerate(corners):
    lo, hi = np.array([PCB_FRONT, y - BOSS_R, z - BOSS_R]), np.array([FACE_BACK, y + BOSS_R, z + BOSS_R])
    clear[f'boss_{j + 1}'] = {n: round(box_mesh_dist(lo, hi, m), 3) for n, m in head.items()}
    clear[f'boss_{j + 1}']['ribbon_flat'] = round(box_box_dist((lo, hi), comp['ribbon_flat']), 3)
    clear[f'boss_{j + 1}']['connector_front'] = round(box_box_dist((lo, hi), comp['connector_front']), 3)
mins = {}
for k, row in clear.items():
    if k.startswith('_'):
        continue
    for n, v in row.items():
        if isinstance(v, (int, float)):
            mins[f'{k} vs {n}'] = v
checks['clearances'] = {'note': 'Minimum distances in mm (0.25 mm sampling). Camera parts modelled as boxes. '
                                'Board space = x < 74.5, y -32.5..32.5, z 114.8..144.6. '
                                'Expected designed contacts: PCB front on the four boss tops (distance 0).',
                        'table': clear,
                        'smallest10': dict(sorted(mins.items(), key=lambda kv: kv[1])[:10])}

# exit band (connector width plus ribbon) free of face/trim material
band_lo = np.array([PCB_FRONT, AY + h - CONN_D, AZ - CONN_W / 2])
band_hi = np.array([FACE_BACK - 0.01, RIBBON_TURN_Y, AZ + CONN_W / 2])
checks['ribbonExitBand'] = {'box': [band_lo.round(2).tolist(), band_hi.round(2).tolist()],
                            'faceDistanceMm': round(box_mesh_dist(band_lo, band_hi, face), 3),
                            'trimDistanceMm': round(box_mesh_dist(band_lo, band_hi, trim), 3),
                            'capDistanceAtFoldMm': clear['ribbon_fold']['head_cap']}

# face-on: vertical insertion from +40 mm (rigid camera boxes and bosses swept along z)
sweep = {}
rigid = {k: comp[k] for k in ('pcb', 'lens_holder', 'connector_front', 'back_layer')}
for j, (y, z) in enumerate(corners):
    rigid[f'boss_{j + 1}'] = (np.array([PCB_FRONT, y - BOSS_R, z - BOSS_R]), np.array([FACE_BACK, y + BOSS_R, z + BOSS_R]))
for s, d in screws.items():
    rigid[f'head_{s}'] = (np.array([d['head_x'][0], d['y'] - 2, d['z'] - 2]), np.array([d['head_x'][1], d['y'] + 2, d['z'] + 2]))
for k, (lo, hi) in rigid.items():
    hi2 = hi + np.array([0, 0, 40.0])
    sweep[k] = {n: round(box_mesh_dist(lo, hi2, W[n]), 3) for n in ('head_bottom', 'jaw_frame', 'clip_head')}
cm3_sweep = {}
cl, ch = cm3.bounds
cm3_sweep = {n: round(box_mesh_dist(cl, ch + [0, 0, 40], W[n]), 3) for n in ('head_bottom', 'jaw_frame', 'clip_head')}
checks['faceOnInsertion'] = {'note': 'Each rigid box swept straight down from +40 mm to the installed pose; min distance '
                                     'to the parts already in the head. CM3 bounding box swept the same way for comparison.',
                             'sweptMinDistance': sweep, 'cm3BoundingBoxSweep': cm3_sweep}

# ---------------------------------------------------------------- screws
face_front_hit = {}
for s, d in screws.items():
    loc, _, _ = face.ray.intersects_location([[120, d['y'], d['z']]], [[-1, 0, 0]])
    face_front_hit[s] = float(loc[:, 0].max()) if len(loc) else None
tloc = {}
for s in ('trim_lower', 'trim_upper'):
    d = screws[s]
    loc, _, _ = trim.ray.intersects_location([[120, d['y'], d['z']]], [[-1, 0, 0]])
    tloc[s] = sorted(loc[:, 0].tolist())
screw_rows = []
for s, d in screws.items():
    tip = d['shank_x'][1]
    if s.startswith('camera'):
        screw_rows.append({
            'screw': s, 'type': f'M2 x {d["len"]:.0f} self-tapping', 'at_yz': [round(d['y'], 2), round(d['z'], 2)],
            'from': 'behind the camera (head on the PCB back pad)',
            'passes': f'camera PCB plated corner hole x {PCB_BACK:.1f}..{PCB_FRONT:.1f}',
            'threadsInto': f'face corner boss, 1.7 mm blind pilot x {PCB_FRONT:.1f}..{PILOT_END:.1f}',
            'threadEngagementMm': round(min(tip, PILOT_END) - PCB_FRONT, 2),
            'tipX': round(tip, 2), 'materialInFrontOfTipMm': round(face_front_hit[s] - tip, 2),
            'headX': [round(v, 2) for v in d['head_x']]})
    else:
        screw_rows.append({
            'screw': s, 'type': f'M2 x {d["len"]:.0f} self-tapping', 'at_yz': [d['y'], d['z']],
            'from': 'the back of the face, before the camera goes on (head between face and camera PCB)',
            'passes': f'face plate 2.2 mm hole x {FACE_BACK:.1f}..{FACE_FRONT:.1f}',
            'threadsInto': 'V1.8 eye-trim 1.7 mm pilot x 81.3..87.0',
            'threadEngagementMm': round(tip - FACE_FRONT, 2),
            'tipX': round(tip, 2), 'pilotEndX': 87.0,
            'materialInFrontOfTipMm': round(max(tloc[s]) - tip, 2) if tloc[s] else None,
            'headX': [round(v, 2) for v in d['head_x']],
            'headToPcbFrontGapMm': round(d['head_x'][0] - PCB_FRONT, 2)})
checks['screws'] = {'rows': screw_rows,
                    'requirementThread3p5mm': {
                        'camera_corner': False, 'trim': True,
                        'why': f'The corner holes lie at radius {math.hypot(14, 14):.1f} mm from the lens axis, outside '
                               f'the eye trim (radius 15), so they land on the 1.3 mm face plate. Everything in front of '
                               f'the PCB is boss {FACE_BACK - PCB_FRONT:.1f} + plate {FACE_FRONT - FACE_BACK:.1f} = '
                               f'{FACE_FRONT - PCB_FRONT:.1f} mm; leaving {SKIN} mm in front of the tip gives '
                               f'{PILOT_END - PCB_FRONT:.1f} mm of thread. The PCB cannot move further back (board space) '
                               f'and the face front must not change.'}}

# walls
checks['printability'] = {
    'bossWallMm': round(BOSS_R - PILOT_D / 2, 2), 'pilotFloorSkinMm': SKIN,
    'faceFrontHitAtCorners': {k: round(v, 3) for k, v in face_front_hit.items() if k.startswith('camera')},
    'minimumWallRule': 1.2, 'pass': BOSS_R - PILOT_D / 2 >= 1.2 and SKIN >= 1.2,
    'poses': 'same sourceToPrint matrices as release-V1.8/manifest-V1.8.json (face: front on the bed, bosses up; '
             'trim unchanged)'}

checks['placement'] = {'pcbFrontX': round(PCB_FRONT, 3), 'pcbBackX': round(PCB_BACK, 3),
                       'backComponentsToX': round(PCB_BACK - BACK_LAYER, 3),
                       'connectorOnLensSide': True, 'connectorEdge': '+Y',
                       'connectorBox': [np.round(v, 2).tolist() for v in comp['connector_front']],
                       'cornerHoles_yz': [[round(y, 2), round(z, 2)] for y, z in corners],
                       'smallHoles_yz_unused': [[round(y, 2), round(z, 2)] for y, z in smalls]}
checks['assumptions'] = {
    'connectorSide': 'lens side, per the two Radxa photos (the brief said back side; the photos show the connector '
                     'next to the lens and the ribbon plugged on that side). Height modelled 2.0 mm (typical 0.3 mm '
                     'flip-lock parts are 0.9 to 1.2 mm).',
    'smallHoleDiameter': 'about 1.8 mm measured on the Radxa drawing (corner holes about 2.0 mm): too small for M2.',
    'pupilRadius': PUPIL_R, 'screwHeadHeight': SCREW_HEAD_H,
    'backLayer': 'full PCB footprint, 1.5 mm, less 4 x 4 mm squares at the corner holes for the screw heads'}

def _fin(o):
    if isinstance(o, dict):
        return {k: _fin(v) for k, v in o.items()}
    if isinstance(o, list):
        return [_fin(v) for v in o]
    if isinstance(o, float) and math.isinf(o):
        return '>12 (nothing within 12 mm)'
    return o


(HERE / 'checks.json').write_text(json.dumps(_fin(checks), indent=1))

# ---------------------------------------------------------------- renders
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle


def sec(m, o, n):
    s = m.section(plane_origin=o, plane_normal=n)
    return [] if s is None else s.discrete


# 1. back of the face with camera, seen from behind (looking +x): robot left (+Y) is on the viewer's left.
fig, ax = plt.subplots(figsize=(9, 7))
for d in sec(face, [FACE_BACK + 0.6, 0, 0], [1, 0, 0]):
    ax.fill(-d[:, 1], d[:, 2], color='#e9e9e9', ec='#999', lw=0.6)
for d in sec(face, [(PCB_FRONT + FACE_BACK) / 2, 0, 0], [1, 0, 0]):
    ax.fill(-d[:, 1], d[:, 2], color='#bbbbbb', ec='#555', lw=0.8)


def rect(lo, hi, **kw):
    ax.add_patch(Rectangle((-hi[1], lo[2]), hi[1] - lo[1], hi[2] - lo[2], **kw))


rect(*comp['pcb'], fc='#2a6f3a', ec='k', alpha=0.55, lw=1)
rect(*comp['lens_holder'], fc='none', ec='#c9a400', lw=1.2, ls='--')
rect(*comp['connector_front'], fc='#b0b0b0', ec='k', lw=1, alpha=0.9)
rect(*comp['ribbon_flat'], fc='#e08a1e', ec='#a05a00', alpha=0.75)
for y, z in corners:
    ax.add_patch(Circle((-y, z), 2.0, fc='#444', ec='k'))
for s in ('trim_lower', 'trim_upper'):
    ax.add_patch(Circle((-screws[s]['y'], screws[s]['z']), 2.0, fc='none', ec='#0055cc', lw=1.2, ls=':'))
for y, z in smalls:
    ax.add_patch(Circle((-y, z), SMALL_D / 2, fc='white', ec='k', lw=0.6))
ax.add_patch(Rectangle((-39.4, AZ - 8), 4.1, 16, fc='#f4b183', ec='#c55a11', alpha=0.5))
ax.text(-37.3, AZ + 9, 'cap boss\n(y 35.1+)', ha='center', fontsize=7)
ax.annotate('ribbon to +Y (robot left),\nfolds back at y 33', (-(RIBBON_TURN_Y - 2), AZ), (-31, AZ + 14),
            fontsize=8, arrowprops=dict(arrowstyle='->'))
ax.text(-AY, AZ - 19.5, 'camera from behind: 4 x M2 x 4 at the corners (grey)\n'
        'dotted blue: 2 x M2 x 6 trim screws under the PCB', ha='center', fontsize=8)
ax.set_xlim(-45, 22)
ax.set_ylim(108, 157)
ax.set_aspect('equal')
ax.set_xlabel('-y (mm)  [viewer left = robot +Y]')
ax.set_ylabel('z (mm)')
ax.set_title('Face A7Z, back view with Camera 13M 214 (PCB transparent)')
fig.tight_layout()
fig.savefig(HERE / 'render-back.png', dpi=130)
plt.close(fig)

# 2. section through the lens axis (x-z at y = axis) with the 78.4 deg cone, and x-y at z = axis
fig, axs = plt.subplots(1, 2, figsize=(14, 7))
cols = {'face_panel_a7z': ('#cfcfcf', face), 'eye_trim_a7z': ('#333333', trim), 'head_cap': ('#f4b183', W['head_cap']),
        'head_bottom': ('#ffe08a', W['head_bottom']), 'jaw_frame': ('#ffd27a', W['jaw_frame'])}
for ax, (o, nrm, ix, title) in zip(axs, [([0, AY, 0], [0, 1, 0], (0, 2), f'section y = {AY:.2f} (x-z)'),
                                         ([0, 0, AZ], [0, 0, 1], (0, 1), f'section z = {AZ:.2f} (x-y)')]):
    for n, (c, m) in cols.items():
        for d in sec(m, o, nrm):
            ax.fill(d[:, ix[0]], d[:, ix[1]], color=c, ec='k', lw=0.4, alpha=0.9)
    for d in sec(camera, o, nrm):
        ax.fill(d[:, ix[0]], d[:, ix[1]], color='#2a6f3a', ec='k', lw=0.4, alpha=0.8)
    for d in sec(cm3, o, nrm):
        ax.plot(d[:, ix[0]], d[:, ix[1]], color='red', lw=0.5, ls=':')
    c0 = AZ if ix[1] == 2 else AY
    L = 14
    for sgn in (-1, 1):
        ax.plot([LENS_FRONT, LENS_FRONT + L], [c0 + sgn * PUPIL_R, c0 + sgn * (PUPIL_R + L * tanD)], 'b-', lw=0.9)
    ax.axvline(CM3_LENS_FRONT, color='red', lw=0.5, ls='--')
    ax.set_aspect('equal')
    ax.set_xlim(66, 96)
    ax.set_ylim(c0 - 25, c0 + 25) if ix[1] == 2 else ax.set_ylim(-25, 42)
    ax.set_title(title + '\nblue: 78.4 deg cone; red dotted: V1.8 CM3; red dashed: CM3 lens front')
    ax.set_xlabel('x (mm)')
    ax.grid(alpha=0.25)
o = checks['optics']['perPart']['eye_trim_a7z']
axs[0].text(67, AZ - 23, f'lens front x {LENS_FRONT:.2f} ({CM3_LENS_FRONT - LENS_FRONT:.2f} behind CM3)\n'
            f'cone clearance to trim {o["minNormalClearanceMm"]:.2f} mm', fontsize=8)
fig.tight_layout()
fig.savefig(HERE / 'render-section.png', dpi=120)
plt.close(fig)

# 3. ribbon exit: x-y section at the ribbon mid-height with the cap boss and the board space
fig, ax = plt.subplots(figsize=(9, 7))
for n, c in [('head_cap', '#f4b183'), ('head_bottom', '#ffe08a'), ('clip_cap', '#ff9f40')]:
    for d in sec(W[n], [0, 0, AZ], [0, 0, 1]):
        ax.fill(d[:, 0], d[:, 1], color=c, ec='k', lw=0.4)
for d in sec(face, [0, 0, AZ + 4], [0, 0, 1]):
    ax.fill(d[:, 0], d[:, 1], color='#cfcfcf', ec='k', lw=0.4)
for d in sec(trim, [0, 0, AZ + 4], [0, 0, 1]):
    ax.fill(d[:, 0], d[:, 1], color='#333', ec='k', lw=0.4)
for d in sec(camera, [0, 0, AZ + 4], [0, 0, 1]):
    ax.fill(d[:, 0], d[:, 1], color='#2a6f3a', ec='k', lw=0.4, alpha=0.85)
for k in ('ribbon_flat', 'ribbon_fold'):
    lo, hi = comp[k]
    ax.add_patch(Rectangle((lo[0], lo[1]), hi[0] - lo[0], hi[1] - lo[1], fc='#e08a1e', ec='#a05a00'))
ax.add_patch(Rectangle((50, -32.5), 24.5, 65, fc='none', ec='purple', ls='--', lw=1))
ax.text(51, 30, 'A7Z board space\n(x < 74.5)', color='purple', fontsize=8, va='top')
ax.set_xlim(48, 96)
ax.set_ylim(-20, 45)
ax.set_aspect('equal')
ax.grid(alpha=0.25)
ax.set_xlabel('x (mm)')
ax.set_ylabel('y (mm)  [+Y = robot left]')
ax.set_title(f'Ribbon exit, section z = {AZ + 4:.1f} (ribbon band z {AZ - 6:.1f}..{AZ + 6:.1f})\n'
             f'cap boss clearance at the fold {clear["ribbon_fold"]["head_cap"]:.2f} mm')
fig.tight_layout()
fig.savefig(HERE / 'render-ribbon.png', dpi=130)
plt.close(fig)
print(json.dumps({k: checks[k] for k in ('axis', 'optics', 'screws')}, indent=1)[:6000])
print('smallest', json.dumps(checks['clearances']['smallest10'], indent=1))
