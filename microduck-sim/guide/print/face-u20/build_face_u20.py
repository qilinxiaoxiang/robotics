"""Face panel and eye trim for the Innomaker U20CAM-720P USB camera (D-023, 2026-10-22).

The 32 x 32 mm UVC board screws to four bosses on the back of the white face; its M12 lens passes through the eye
opening and the black eye trim, bored out to BORE_D for the lens front ring. The camera's own 4-core cable leaves the
board-edge connector on the BACK of the PCB (that edge faces +y, robot left, so the cable leaves sideways: under the board there are only 3.8 mm to the lower shell). It runs
whole over the jaw motor ID15 to the left-rear head exit, which the jaw support and the lower shell reprint opens to dia 11
(print/neck-exit-20261023/, Shawn 2026-10-23: "能不能把脖子那个洞搞大一点呢 别转杜邦线了"), leaves the head there with the nine head
wires, and is cut to length and soldered at the saddle front to the right-angle USB-C OTG pigtail that plugs into the A7Z.

Camera numbers (source and status, see checks.json 'cameraModel'): board 32 x 32, four dia 2.2 holes on a 28 mm square
(user manual: size, hole count and diameter; pitch measured on the manual's board photo, 920 / 32.8 px per mm), M12
lens on a two-ear holder with 18 mm ear-hole spacing (manual). HOLDER_H, LENS_H and RING_D are read off Innomaker's
product renders (front elevation 720P-3.jpg, 43.8 px per mm) and are the numbers to confirm with calipers on the arm's
U20CAM before printing: they set the boss length and the trim bore.

Regenerates every output in this folder from the current world STLs in ../world/:
  face_panel_u20.stl, eye_trim_u20.stl, camera_u20cam.stl    (robot frame, mm, x forward, y left, z up)
  face_panel_u20-print.stl, eye_trim_u20-print.stl             (V1.8 print poses from release-V1.8/manifest-V1.8.json)
  checks.json and render-*.png

Run through the bounded runner:
  python3 ../../../build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py \
      --max-mib 2500 --seconds 300 --wait-lock-seconds 600 -- /tmp/microduck-cad-venv/bin/python build_face_u20.py
"""
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
WORLD = HERE.parent / 'world'
MANIFEST = HERE.parent / 'release-V1.8' / 'manifest-V1.8.json'
# the slot-free audio cap (V1.30 cap source; the A7Z cap's rails and end slots go away with D-023)
CAP_NEW = HERE.parent / 'world' / 'head_cap.stl'      # the V1.17 cap as printed (D-022: its rails stay empty; no cap reprint)
IA_CACHE = Path(os.environ.get('IA_CACHE', '/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/ia-cache'))   # the print gate's solid cache (ia_lib.CACHE): head parts that have no file in print/world

# ---------------------------------------------------------------- camera data
PCB = 32.0
PCB_T = 1.6
HOLE_PITCH = 28.0
HOLE_D = 2.2
HOLDER_W = 15.0        # square lens-holder block (manual photo, scaled by the 32 mm board)
EAR_SPAN = 20.0        # the two ears along the holder's long axis (ear holes 18 mm apart, manual 'lens seat spacing')
EAR_H = 5.0            # ear width across (modelled as a 20 x 5 box)
HOLDER_H = 5.5         # holder block top above the PCB front         (render estimate; confirm with calipers)
LENS_H = 15.4          # lens front above the PCB front               (render estimate; confirm with calipers)
KNURL_D = 13.2         # knurled lens barrel                          (render estimate)
RING_D = 15.1          # front ring of the lens, the widest part      (render estimate; confirm with calipers)
RING_H = 4.5           # height of that ring below the lens front
BACK_LAYER = 1.5       # components on the back of the PCB
CONN_W, CONN_D, CONN_H = 10.0, 4.5, 3.0   # cable connector on the BACK at the bottom edge (install photo in the case manual)
CABLE_D = 4.0          # the camera's own round cable (assumed; the manual gives only the length, 1 m)
FOV_H, FOV_D = 102.0, 120.0               # manual
FOV_V = math.degrees(2 * math.atan(math.tan(math.radians(FOV_H / 2)) * 9 / 16))   # 16:9 sensor, about 69.6
PUPIL_R = 1.0

# ---------------------------------------------------------------- face geometry (V1.8)
FACE_BACK = 80.1
FACE_FRONT = 81.4
TRIM_FRONT = 89.4
BOSS_R = 2.4
PILOT_D = 1.7
PILOT_DEPTH = 5.0      # blind pilot from the boss top
FACE_GAP = 2.2         # holder block top to the face back (the ear tips then stay 0.6 mm behind the trim screw heads)
SCREW_HEAD_H = 1.6
BORE_D = 16.2          # new eye bore in the face and the trim (lens ring 15.1 + 0.55 radial; printed holes come out about 0.2 smaller)
CORNER_LEN, TRIM_LEN = 6.0, 6.0
WORLD_PARTS = ['head_bottom', 'jaw_frame', 'amplifier', 'speaker']
CACHE_PARTS = ['jaw_support', 'head_yaw_link', 'motor15', 'motor13', 'motor14', 'touch_pad_l1', 'touch_pad_l2', 'touch_xiao']   # from the gate cache; the cable lies over ID15 under the left touch pads, the leads pass the XIAO
HEAD_PARTS = WORLD_PARTS + CACHE_PARTS


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def box(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return trimesh.creation.box(extents=hi - lo, transform=trimesh.transformations.translation_matrix((lo + hi) / 2))


def xcyl(r, x0, x1, y, z, sections=64):
    c = trimesh.creation.cylinder(radius=r, height=x1 - x0, sections=sections)
    c.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [0, 1, 0]))
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
    keep = np.all(tri.max(1) >= lo - pad, 1) & np.all(tri.min(1) <= hi + pad, 1)
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


def mesh_mesh_dist(a, b, lo, hi, pad=12.0):
    """Minimum distance between two meshes near the box lo..hi (surface samples of a against b)."""
    ca = crop(a, np.asarray(lo, float), np.asarray(hi, float), pad)
    cb = crop(b, np.asarray(lo, float), np.asarray(hi, float), pad)
    if ca is None or cb is None:
        return float('inf')
    P = np.vstack([ca.vertices, trimesh.sample.sample_surface(ca, 40000, seed=3)[0]])
    d = np.inf
    for k in range(0, len(P), 250):     # small batches: closest_point holds points x candidate triangles (the 2026-10-23 full-length cable needed > 6 GB at 2000)
        _, dd, _ = trimesh.proximity.closest_point(cb, P[k:k + 250])
        d = min(d, dd.min())
    return float(d)


# ---------------------------------------------------------------- load
SRC = {'face_panel': 'face_panel-v18', 'eye_trim': 'eye_trim-v18'}   # the printed V1.8 parts; world/face_panel.stl and eye_trim.stl are this build's output
W = {n: trimesh.load(WORLD / f'{SRC.get(n, n)}.stl', force='mesh') for n in ['face_panel', 'eye_trim'] + WORLD_PARTS}
for n in CACHE_PARTS:
    z = np.load(IA_CACHE / f'solid-{n}.npz', allow_pickle=False)
    W[n] = trimesh.Trimesh(z['v'], z['f'], process=False)
W['head_cap_new'] = trimesh.load(CAP_NEW, force='mesh')
face18, trim18 = W['face_panel'], W['eye_trim']
checks = {'_doc': 'face-u20 checks; robot frame mm (x forward, y left, z up). Regenerate with build_face_u20.py.',
          'sources': {f'world/{SRC.get(n, n)}.stl': sha(WORLD / f'{SRC.get(n, n)}.stl') for n in ['face_panel', 'eye_trim'] + WORLD_PARTS},
          'cacheSolids': {n: str(IA_CACHE / f'solid-{n}.npz') for n in CACHE_PARTS}}
checks['sources'][str(CAP_NEW.relative_to(HERE.parents[1]))] = sha(CAP_NEW)

# axis: the V1.8 eye opening centre (same as face-a7z: y -0.09, z 131.114)
eye_loop = None
for d in face18.section(plane_origin=[80.75, 0, 0], plane_normal=[1, 0, 0]).discrete:
    if 10 < np.ptp(d[:, 1]) < 20:
        eye_loop = d
eye_c = (eye_loop.min(0) + eye_loop.max(0)) / 2
AY, AZ = float(eye_c[1]), float(eye_c[2])
checks['axis'] = {'eyeOpeningCentre_face_x80.75': [round(AY, 3), round(AZ, 3)],
                  'eyeOpeningRadiusV18': round(float(np.ptp(eye_loop[:, 1]) / 2), 3), 'used': [round(AY, 3), round(AZ, 3)]}

# ---------------------------------------------------------------- camera placement
PCB_FRONT = FACE_BACK - FACE_GAP - HOLDER_H        # 73.6
PCB_BACK = PCB_FRONT - PCB_T                       # 72.0
LENS_FRONT = PCB_FRONT + LENS_H                    # 89.0
h = PCB / 2
pcb_lo, pcb_hi = np.array([PCB_BACK, AY - h, AZ - h]), np.array([PCB_FRONT, AY + h, AZ + h])
corners = [(AY + sy * HOLE_PITCH / 2, AZ + sz * HOLE_PITCH / 2) for sy in (-1, 1) for sz in (-1, 1)]
comp = {
    'pcb': (pcb_lo, pcb_hi),
    'holder': (np.array([PCB_FRONT, AY - HOLDER_W / 2, AZ - HOLDER_W / 2]),
               np.array([PCB_FRONT + HOLDER_H, AY + HOLDER_W / 2, AZ + HOLDER_W / 2])),
    'holder_ears': (np.array([PCB_FRONT, AY - EAR_H / 2, AZ - EAR_SPAN / 2]),
                    np.array([PCB_FRONT + HOLDER_H, AY + EAR_H / 2, AZ + EAR_SPAN / 2])),
    'lens_knurl': (np.array([PCB_FRONT + HOLDER_H, AY - KNURL_D / 2, AZ - KNURL_D / 2]),
                   np.array([LENS_FRONT - RING_H, AY + KNURL_D / 2, AZ + KNURL_D / 2])),
    'lens_ring': (np.array([LENS_FRONT - RING_H, AY - RING_D / 2, AZ - RING_D / 2]),
                  np.array([LENS_FRONT, AY + RING_D / 2, AZ + RING_D / 2])),
    'connector_back': (np.array([PCB_BACK - CONN_H, AY + h - CONN_D, AZ - CONN_W / 2]),
                       np.array([PCB_BACK, AY + h, AZ + CONN_W / 2])),
}
bl_lo, bl_hi = np.array([PCB_BACK - BACK_LAYER, AY - h, AZ - h]), np.array([PCB_BACK, AY + h, AZ + h])
comp['back_layer'] = (bl_lo, bl_hi)
corner_cut = [box([bl_lo[0] - 1, y - 2, z - 2], [PCB_BACK + 0.01, y + 2, z + 2]) for y, z in corners]
pcb_m = diff(box(pcb_lo, pcb_hi), [xcyl(HOLE_D / 2, PCB_BACK - 1, PCB_FRONT + 1, y, z) for y, z in corners])
back_m = diff(box(bl_lo, bl_hi + np.array([0.01, 0, 0])), corner_cut)
camera = union([pcb_m, back_m,
                box(comp['holder'][0] - [0.01, 0, 0], comp['holder'][1]),
                box(comp['holder_ears'][0] - [0.01, 0, 0], comp['holder_ears'][1]),
                xcyl(KNURL_D / 2, PCB_FRONT + HOLDER_H - 0.01, LENS_FRONT - RING_H + 0.01, AY, AZ),
                xcyl(RING_D / 2, LENS_FRONT - RING_H, LENS_FRONT, AY, AZ),
                box(comp['connector_back'][0], comp['connector_back'][1] + [0.01, 0, 0])])
camera.export(HERE / 'camera_u20cam.stl')
# the camera's own cable inside the head: out of the connector to +y (robot left), up over the jaw support front wall and
# along x over the left half of ID15 to x 26; from there content/routes.json cam_usb carries it to the dia 11 left-rear
# exit, down the neck and to the pigtail splice at the saddle (this stub is for the pictures and the near-field clearance).
CABLE_PTS = [np.array([PCB_BACK - CONN_H / 2, AY + h, AZ]), np.array([62.0, 18.0, 134.0]), np.array([54.0, 20.0, 137.0]),
             np.array([48.0, 24.0, 137.0]), np.array([45.0, 26.0, 137.0]),   # out of the connector's +y edge, up over the jaw support front wall (free radius >= 4.7 there, scratchpad free_map 2026-10-22)
             np.array([26.0, 26.0, 137.0])]   # along x over the left half of the ID15 case (top 128.6), under the left touch pads (l1 bottom 141.5 at y 31; free radius 5.7..7.3 along this line); ends at x 26, where the two left touch-pad leads (18..22.5, 27.6..28.5, 139.5) turn to the XIAO


def tube(pts, d):
    return union([trimesh.creation.capsule(radius=d / 2, height=float(np.linalg.norm(b - a)))
                  .apply_transform(trimesh.geometry.align_vectors([0, 0, 1], (b - a) / np.linalg.norm(b - a)))
                  .apply_translation((a + b) / 2) for a, b in zip(pts[:-1], pts[1:])])


cable = tube(CABLE_PTS, CABLE_D)
cable.export(HERE / 'camera_cable_stub.stl')

# screws
trim_holes = [(-0.18, 120.6), (-0.18, 141.6)]
screws = {}
for i, (y, z) in enumerate(corners):
    screws[f'camera_corner_{i + 1}'] = dict(y=y, z=z, len=CORNER_LEN, head_x=(PCB_BACK - SCREW_HEAD_H, PCB_BACK),
                                            shank_x=(PCB_BACK, PCB_BACK + CORNER_LEN))
for i, (y, z) in enumerate(trim_holes):
    screws[f'trim_{"lower" if i == 0 else "upper"}'] = dict(y=y, z=z, len=TRIM_LEN, head_x=(FACE_BACK - SCREW_HEAD_H, FACE_BACK),
                                                            shank_x=(FACE_BACK, FACE_BACK + TRIM_LEN))

# ---------------------------------------------------------------- face panel U20
cut = box([70.0, AY - 20, AZ - 20], [FACE_BACK, AY + 20, AZ + 20])      # V1.8 camera lands and pegs
face = diff(face18, [cut])
removed = float(face18.volume - face.volume)
PILOT_END = PCB_FRONT + PILOT_DEPTH                                      # 78.6; boss floor to the face back 1.5
bosses = [xcyl(BOSS_R, PCB_FRONT, FACE_BACK + 0.4, y, z) for y, z in corners]
face = union([face] + bosses)
face = diff(face, [xcyl(PILOT_D / 2, PCB_FRONT - 1.0, PILOT_END, y, z, 32) for y, z in corners])
# The V1.8 face has three key pockets through its 1.3 mm front skin for the eye trim's back tabs: two 2.5 x 3.3 wedges at
# (AY -/+ 7.7, AZ - 4.5) and a pair of 0.5 mm pits at (AY -/+ 1.4, AZ + 8.5). The dia 16.2 bore cuts into the two side
# pockets (0.35 mm left between pocket and bore), so they are filled before the bore and the trim loses its two side tabs;
# the top key pair stays as in V1.17 (its 1.05 mm wall printed, release-V1.30 manifest thinWallAllowances).
KEY_FILL = [box([FACE_BACK, AY + min(sgn * 5.8, sgn * 9.6), AZ - 7.0], [FACE_FRONT, AY + max(sgn * 5.8, sgn * 9.6), AZ - 2.2]) for sgn in (-1.0, 1.0)]
face = union([face] + KEY_FILL)
bore_face = xcyl(BORE_D / 2, FACE_BACK - 1.5, FACE_FRONT + 0.5, AY, AZ, 96)
face_before_bore = face.copy()
face = diff(face, [bore_face])
bored_face = float(face_before_bore.volume - face.volume)
face.export(HERE / 'face_panel_u20.stl')

# ---------------------------------------------------------------- eye trim U20: V1.8 trim bored to BORE_D
bore_trim = xcyl(BORE_D / 2, FACE_BACK - 1.0, TRIM_FRONT + 0.5, AY, AZ, 96)
KEY_CUT = [box([FACE_BACK - 1.0, AY + min(sgn * 5.8, sgn * 9.6), AZ - 7.0], [FACE_FRONT, AY + max(sgn * 5.8, sgn * 9.6), AZ - 2.2]) for sgn in (-1.0, 1.0)]   # the two side tabs (x 80.0..81.4, back of the ring at FACE_FRONT) whose face pockets are filled above
trim = diff(trim18, [bore_trim] + KEY_CUT)
bored_trim = float(trim18.volume - trim.volume)
trim.export(HERE / 'eye_trim_u20.stl')
# remaining trim walls around the bore, by section
walls = {}
for x in (82.0, 85.0, 87.0, 88.0, 88.8):
    s = trim.section(plane_origin=[x, 0, 0], plane_normal=[1, 0, 0])
    rs = sorted({(round(float(np.hypot(d[:, 1] - AY, d[:, 2] - AZ).min()), 2), round(float(np.hypot(d[:, 1] - AY, d[:, 2] - AZ).max()), 2)) for d in s.discrete})
    walls[f'x{x}'] = rs
checks['trimSectionsRadii'] = walls

# ---------------------------------------------------------------- print poses
man = json.loads(MANIFEST.read_text())
pose = {p['key']: np.array(p['sourceToPrint']) for p in man['parts'] if p['key'] in ('face_panel', 'eye_trim')}
prints = {}
for key, mesh, out in [('face_panel', face, 'face_panel_u20-print.stl'), ('eye_trim', trim, 'eye_trim_u20-print.stl')]:
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

    prints[key] = {'file': out, 'minZ': round(float(m.bounds[0, 2]), 4), 'bedContactMm2': bed(m), 'v18BedContactMm2': bed(ref),
                   'overhangOver45degMm2': overhang(m), 'v18OverhangOver45degMm2': overhang(ref),
                   'heightMm': round(float(m.bounds[1, 2] - m.bounds[0, 2]), 2)}


def mesh_info(m, path):
    return {'file': path, 'watertight': bool(m.is_watertight), 'volumeMm3': round(float(m.volume), 2),
            'bounds': np.round(m.bounds, 3).tolist(), 'sha256': sha(HERE / path)}


checks['meshes'] = {'face_panel_u20': mesh_info(face, 'face_panel_u20.stl'), 'eye_trim_u20': mesh_info(trim, 'eye_trim_u20.stl'),
                    'camera_u20cam': mesh_info(camera, 'camera_u20cam.stl'),
                    'face_panel_v18_volumeMm3': round(float(face18.volume), 2), 'eye_trim_v18_volumeMm3': round(float(trim18.volume), 2),
                    'face_removed_v18_lands_pegs_mm3': round(removed, 2), 'face_boredMm3': round(bored_face, 2),
                    'trim_boredMm3': round(bored_trim, 2)}
checks['printPoses'] = prints

# front shape: unchanged outside the bore (ray cast from the front on a 1 mm grid)
gy, gz = np.meshgrid(np.arange(-43, 43.5, 1.0), np.arange(111, 154.5, 1.0))
O = np.c_[np.full(gy.size, 120.0), gy.ravel(), gz.ravel()]
D = np.tile([-1.0, 0, 0], (len(O), 1))


def first_hit(m):
    loc, idx, _ = m.ray.intersects_location(O, D, multiple_hits=False)
    out = np.full(len(O), np.nan)
    out[idx] = loc[:, 0]
    return out


rho = np.hypot(O[:, 1] - AY, O[:, 2] - AZ)
outside = rho > BORE_D / 2 + 0.6
fa, fb = first_hit(face), first_hit(face18)
both = ~np.isnan(fa) & ~np.isnan(fb) & outside
ta, tb = first_hit(trim), first_hit(trim18)
tboth = ~np.isnan(ta) & ~np.isnan(tb) & outside
checks['frontUnchangedOutsideBore'] = {
    'face_raysOnGrid1mm': int(both.sum()), 'face_maxFrontDeviationMm': float(np.nanmax(np.abs(fa[both] - fb[both]))),
    'face_hitMaskSameOutsideBore': bool(np.array_equal(np.isnan(fa)[outside], np.isnan(fb)[outside])),
    'trim_raysOnGrid1mm': int(tboth.sum()), 'trim_maxFrontDeviationMm': float(np.nanmax(np.abs(ta[tboth] - tb[tboth]))),
    'trim_hitMaskSameOutsideBore': bool(np.array_equal(np.isnan(ta)[outside], np.isnan(tb)[outside]))}

# ---------------------------------------------------------------- optics: cone clearance, and how far back the lens may sit
mat = {'face_panel_u20': face, 'eye_trim_u20': trim, 'head_cap_new': W['head_cap_new'], 'head_bottom': W['head_bottom'],
       'jaw_frame': W['jaw_frame']}


def cone_check(lens_front, fov_d=FOV_D):
    tanD = math.tan(math.radians(fov_d / 2))
    out = {}
    for name, m in mat.items():
        c = crop(m, np.array([lens_front, AY - 60, AZ - 60]), np.array([lens_front + 60, AY + 60, AZ + 60]), 0)
        if c is None:
            continue
        P = np.vstack([c.vertices, trimesh.sample.sample_surface(c, 200000, seed=1)[0]])
        a = P[:, 0] - lens_front
        r = np.hypot(P[:, 1] - AY, P[:, 2] - AZ)
        sel = a > 1e-6
        if not sel.any():
            continue
        a, r, P = a[sel], r[sel], P[sel]
        radial = r - (PUPIL_R + a * tanD)
        normal = radial * math.cos(math.radians(fov_d / 2))
        ang = np.degrees(np.arctan2(r - PUPIL_R, a)) - fov_d / 2
        i = int(np.argmin(normal))
        ty, tz = math.tan(math.radians(FOV_V / 2)), math.tan(math.radians(FOV_H / 2))
        inside_rect = (np.abs(P[:, 1] - AY) - PUPIL_R <= a * ty) & (np.abs(P[:, 2] - AZ) - PUPIL_R <= a * tz)
        out[name] = {'minNormalClearanceMm': round(float(normal.min()), 3), 'minRadialClearanceMm': round(float(radial.min()), 3),
                     'minAngularMarginDeg': round(float(ang.min()), 2), 'closestPoint': np.round(P[i], 2).tolist(),
                     'pointsInsideRectangularField': int(inside_rect.sum())}
    return out


cone = cone_check(LENS_FRONT)
sens = {}
for lh in np.arange(9.0, 18.1, 1.0):
    c = cone_check(PCB_FRONT + lh)
    sens[f'LENS_H {lh:.0f}'] = {'lensFrontX': round(PCB_FRONT + lh, 2), 'minNormalClearanceMm': round(min(v['minNormalClearanceMm'] for v in c.values()), 3),
                               'clipped': any(v['minNormalClearanceMm'] < 0 for v in c.values())}
checks['optics'] = {
    'lensAxis_yz': [round(AY, 3), round(AZ, 3)], 'lensFrontX': round(LENS_FRONT, 3), 'trimFrontX': TRIM_FRONT,
    'lensFrontBehindTrimFrontMm': round(TRIM_FRONT - LENS_FRONT, 3),
    'fov': {'horizontal': FOV_H, 'vertical': round(FOV_V, 1), 'diagonal': FOV_D, 'imageLongAxis': 'robot z: the connector edge faces +y (robot left), so the 1280 px axis is vertical; rotate the frame 90 deg in software'},
    'coneHalfAngleDeg': FOV_D / 2, 'pupilRadiusMm': PUPIL_R,
    'method': 'circular cone of the 120 deg diagonal from a 1.0 mm pupil disc at the lens front; clearance of every vertex and '
              '200k surface samples of each part in front of the lens. Negative = clipped. The 102 x 69.6 field lies inside it.',
    'perPart': cone, 'clipped': any(v['minNormalClearanceMm'] < 0 for v in cone.values()),
    'sensitivityToLensHeight': sens}

# ---------------------------------------------------------------- clearances
clear = {}
head = {n: W[n] for n in HEAD_PARTS}
head['head_cap_new'] = W['head_cap_new']
others = dict(head)
others['face_panel_u20'] = face
others['eye_trim_u20'] = trim
for k, (lo, hi) in comp.items():
    clear[k] = {n: round(box_mesh_dist(lo, hi, m), 3) for n, m in others.items()}
for n, m in others.items():
    v = inter_vol(camera, m)
    clear.setdefault('_intersectionVolumeCameraMm3', {})[n] = None if v is None else round(v, 4)
for s, d in screws.items():
    lo = np.array([d['head_x'][0], d['y'] - 2.0, d['z'] - 2.0])
    hi = np.array([d['head_x'][1], d['y'] + 2.0, d['z'] + 2.0])
    row = {n: round(box_mesh_dist(lo, hi, m), 3) for n, m in head.items()}
    for k in ('holder', 'holder_ears', 'connector_back', 'pcb'):
        row[k] = round(box_box_dist((lo, hi), comp[k]), 3)
    if s.startswith('trim'):
        row['pcb_front_gap'] = round(d['head_x'][0] - PCB_FRONT, 3)
    clear[f'head_of_{s}'] = row
for n, m in head.items():
    v = inter_vol(face, m)
    clear.setdefault('_intersectionVolumeFaceU20Mm3', {})[n] = None if v is None else round(v, 4)
    v18 = inter_vol(face18, m)
    clear.setdefault('_intersectionVolumeFaceV18Mm3', {})[n] = None if v18 is None else round(v18, 4)
for j, (y, z) in enumerate(corners):
    lo, hi = np.array([PCB_FRONT, y - BOSS_R, z - BOSS_R]), np.array([FACE_BACK, y + BOSS_R, z + BOSS_R])
    clear[f'boss_{j + 1}'] = {n: round(box_mesh_dist(lo, hi, m), 3) for n, m in head.items()}
    clear[f'boss_{j + 1}']['holder_ears'] = round(box_box_dist((lo, hi), comp['holder_ears']), 3)
clear['cable_stub'] = {n: round(mesh_mesh_dist(cable, m, cable.bounds[0], cable.bounds[1]), 3) for n, m in others.items()}
clear['lens_ring_vs_bore'] = {'radialMm': round((BORE_D - RING_D) / 2, 3), 'trimBoreD': BORE_D, 'ringD': RING_D}
clear['holder_top_to_face_back'] = round(FACE_BACK - (PCB_FRONT + HOLDER_H), 3)
mins = {}
for k, row in clear.items():
    if k.startswith('_') or not isinstance(row, dict):
        continue
    for n, v in row.items():
        if isinstance(v, (int, float)):
            mins[f'{k} vs {n}'] = v
checks['clearances'] = {'note': 'Minimum distances in mm (0.25 mm sampling). Camera parts modelled as boxes and cylinders. '
                                'Expected designed contacts: PCB front on the four boss tops (distance 0).',
                        'table': clear, 'smallest12': dict(sorted(mins.items(), key=lambda kv: kv[1])[:12])}

# face-on: vertical insertion from +40 mm (rigid camera parts, bosses and screw heads swept along z)
sweep = {}
rigid = {k: comp[k] for k in ('pcb', 'holder', 'holder_ears', 'lens_ring', 'connector_back', 'back_layer')}
for j, (y, z) in enumerate(corners):
    rigid[f'boss_{j + 1}'] = (np.array([PCB_FRONT, y - BOSS_R, z - BOSS_R]), np.array([FACE_BACK, y + BOSS_R, z + BOSS_R]))
for s, d in screws.items():
    rigid[f'head_{s}'] = (np.array([d['head_x'][0], d['y'] - 2, d['z'] - 2]), np.array([d['head_x'][1], d['y'] + 2, d['z'] + 2]))
for k, (lo, hi) in rigid.items():
    sweep[k] = {n: round(box_mesh_dist(lo, hi + np.array([0, 0, 40.0]), W[n]), 3) for n in ('head_bottom', 'jaw_frame', 'jaw_support')}
checks['faceOnInsertion'] = {'note': 'Each rigid box swept straight down from +40 mm to the installed pose; min distance to the parts already in the head.',
                             'sweptMinDistance': sweep}

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
rows = []
for s, d in screws.items():
    tip = d['shank_x'][1]
    if s.startswith('camera'):
        rows.append({'screw': s, 'type': f'M2 x {d["len"]:.0f} self-tapping', 'at_yz': [round(d['y'], 2), round(d['z'], 2)],
                     'from': 'behind the camera (head on the PCB back)', 'passes': f'camera PCB plated corner hole x {PCB_BACK:.1f}..{PCB_FRONT:.1f}',
                     'threadsInto': f'face corner boss, 1.7 mm blind pilot x {PCB_FRONT:.1f}..{PILOT_END:.1f}',
                     'threadEngagementMm': round(min(tip, PILOT_END) - PCB_FRONT, 2), 'tipX': round(tip, 2),
                     'pilotFloorToFaceBackMm': round(FACE_BACK - PILOT_END, 2),
                     'materialInFrontOfTipMm': round(face_front_hit[s] - tip, 2), 'headX': [round(v, 2) for v in d['head_x']]})
    else:
        rows.append({'screw': s, 'type': f'M2 x {d["len"]:.0f} self-tapping', 'at_yz': [d['y'], d['z']],
                     'from': 'the back of the face, before the camera goes on', 'passes': f'face plate 2.2 mm hole x {FACE_BACK:.1f}..{FACE_FRONT:.1f}',
                     'threadsInto': 'V1.8 eye-trim 1.7 mm pilot x 81.3..87.0', 'threadEngagementMm': round(tip - FACE_FRONT, 2),
                     'tipX': round(tip, 2), 'materialInFrontOfTipMm': round(max(tloc[s]) - tip, 2) if tloc[s] else None,
                     'headX': [round(v, 2) for v in d['head_x']], 'headToPcbFrontGapMm': round(d['head_x'][0] - PCB_FRONT, 2),
                     'headToHolderBlockMm': round(box_box_dist((np.array([d['head_x'][0], d['y'] - 2, d['z'] - 2]), np.array([d['head_x'][1], d['y'] + 2, d['z'] + 2])), comp['holder']), 2)})
checks['screws'] = {'rows': rows}
checks['printability'] = {'bossWallMm': round(BOSS_R - PILOT_D / 2, 2), 'bossLengthMm': round(FACE_BACK - PCB_FRONT, 2),
                          'pilotFloorMm': round(FACE_BACK - PILOT_END, 2), 'minimumWallRule': 1.2,
                          'pass': BOSS_R - PILOT_D / 2 >= 1.2 and FACE_BACK - PILOT_END >= 1.2,
                          'poses': 'same sourceToPrint matrices as release-V1.8/manifest-V1.8.json (face: front on the bed, bosses up; trim: as V1.8)'}
checks['placement'] = {'pcbFrontX': round(PCB_FRONT, 3), 'pcbBackX': round(PCB_BACK, 3), 'backComponentsToX': round(PCB_BACK - BACK_LAYER, 3),
                       'holderTopX': round(PCB_FRONT + HOLDER_H, 3), 'lensFrontX': round(LENS_FRONT, 3),
                       'connector': 'on the PCB back at the +y edge (robot left); the cable leaves its +y edge, rises over the jaw support front wall and lies along x over the left half of the jaw motor ID15 to x 26 (CABLE_PTS); guide/content/routes.json cam_usb carries it on through the dia 11 left-rear exit and down the neck with the nine head wires to the pigtail splice at the saddle (D-023)',
                       'connectorBox': [np.round(v, 2).tolist() for v in comp['connector_back']],
                       'cornerHoles_yz': [[round(y, 2), round(z, 2)] for y, z in corners], 'boreD': BORE_D}
checks['cameraModel'] = {
    'fromManual': {'board': '32 x 32 mm', 'holes': '4, dia 2.2', 'lens': 'M12, lens seat spacing 18 mm', 'fov': 'D 120, H 102', 'cable': '1 m', 'imageOrientation': 'portrait on the robot (connector edge to +y): 102 deg vertical, 69.6 deg horizontal',
                   'source': 'INNO-MAKER/U20CAM-720P UserManual-v1.0.pdf (GitHub), page 3'},
    'measuredOnPhotos': {'holePitchMm': HOLE_PITCH, 'how': 'manual page-1 board photo: hole centres 920 px apart, board 1050 px = 32 mm'},
    'estimatedFromRenders': {'HOLDER_H': HOLDER_H, 'LENS_H': LENS_H, 'KNURL_D': KNURL_D, 'RING_D': RING_D, 'RING_H': RING_H,
                             'how': 'inno-maker.com product render 720P-3.jpg (front elevation), 43.8 px per mm from the 32 mm board'},
    'assumed': {'CONN': [CONN_W, CONN_D, CONN_H], 'CABLE_D': CABLE_D, 'BACK_LAYER': BACK_LAYER, 'EAR_SPAN': EAR_SPAN, 'EAR_H': EAR_H},
    'toConfirmWithCalipers': ['LENS_H: PCB front face to the lens front (sets the boss length only through FACE_GAP; the optics table says how far back the lens may sit)',
                              'HOLDER_H: PCB front face to the top of the square holder block (must stay behind the face back: boss length = FACE_GAP + HOLDER_H)',
                              'RING_D: widest diameter of the lens (must pass the BORE_D bore)']}


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


fig, ax = plt.subplots(figsize=(9, 7))
for d in sec(face, [FACE_BACK + 0.6, 0, 0], [1, 0, 0]):
    ax.fill(-d[:, 1], d[:, 2], color='#e9e9e9', ec='#999', lw=0.6)
for d in sec(face, [(PCB_FRONT + FACE_BACK) / 2, 0, 0], [1, 0, 0]):
    ax.fill(-d[:, 1], d[:, 2], color='#bbbbbb', ec='#555', lw=0.8)


def rect(lo, hi, **kw):
    ax.add_patch(Rectangle((-hi[1], lo[2]), hi[1] - lo[1], hi[2] - lo[2], **kw))


rect(*comp['pcb'], fc='#2a6f3a', ec='k', alpha=0.55, lw=1)
rect(*comp['holder'], fc='none', ec='#c9a400', lw=1.2, ls='--')
rect(*comp['holder_ears'], fc='none', ec='#c9a400', lw=1.0, ls='--')
ax.add_patch(Circle((-AY, AZ), RING_D / 2, fc='none', ec='#c9a400', lw=1.2))
ax.add_patch(Circle((-AY, AZ), BORE_D / 2, fc='none', ec='k', lw=0.8, ls=':'))
rect(*comp['connector_back'], fc='#f0f0f0', ec='k', lw=1)
for y, z in corners:
    ax.add_patch(Circle((-y, z), 2.0, fc='#444', ec='k'))
for s in ('trim_lower', 'trim_upper'):
    ax.add_patch(Circle((-screws[s]['y'], screws[s]['z']), 2.0, fc='none', ec='#0055cc', lw=1.2, ls=':'))
ax.annotate('cable out of the back-side\nconnector towards +y (robot left)', (-(AY + h) - 2, AZ), (-40, AZ - 22), fontsize=8, arrowprops=dict(arrowstyle='->'))
ax.text(-AY, AZ - 24, f'camera from behind: 4 x M2 x {CORNER_LEN:.0f} at the corners (grey) into {FACE_BACK - PCB_FRONT:.1f} mm bosses\n'
        f'dotted blue: 2 x M2 x 6 trim screws between the bosses; dotted black: eye bore dia {BORE_D}', ha='center', fontsize=8)
ax.set_xlim(-45, 30)
ax.set_ylim(106, 157)
ax.set_aspect('equal')
ax.set_xlabel('-y (mm)  [viewer left = robot +Y]')
ax.set_ylabel('z (mm)')
ax.set_title('Face U20, back view with the U20CAM-720P (PCB transparent)')
fig.tight_layout()
fig.savefig(HERE / 'render-back.png', dpi=130)
plt.close(fig)

fig, axs = plt.subplots(1, 2, figsize=(14, 7))
cols = {'face_panel_u20': ('#cfcfcf', face), 'eye_trim_u20': ('#333333', trim), 'head_cap_new': ('#f4b183', W['head_cap_new']),
        'head_bottom': ('#ffe08a', W['head_bottom']), 'jaw_frame': ('#ffd27a', W['jaw_frame']), 'jaw_support': ('#ff9f40', W['jaw_support']), 'motor15': ('#777777', W['motor15'])}
tanD = math.tan(math.radians(FOV_D / 2))
for ax, (o, nrm, ix, title) in zip(axs, [([0, AY, 0], [0, 1, 0], (0, 2), f'section y = {AY:.2f} (x-z)'),
                                         ([0, 0, AZ], [0, 0, 1], (0, 1), f'section z = {AZ:.2f} (x-y)')]):
    for n, (c, m) in cols.items():
        for d in sec(m, o, nrm):
            ax.fill(d[:, ix[0]], d[:, ix[1]], color=c, ec='k', lw=0.4, alpha=0.9)
    for d in sec(camera, o, nrm):
        ax.fill(d[:, ix[0]], d[:, ix[1]], color='#2a6f3a', ec='k', lw=0.4, alpha=0.8)
    for d in sec(cable, o, nrm):
        ax.fill(d[:, ix[0]], d[:, ix[1]], color='#00838f', ec='k', lw=0.4, alpha=0.8)
    for d in sec(trim18, o, nrm):
        ax.plot(d[:, ix[0]], d[:, ix[1]], color='red', lw=0.5, ls=':')
    c0 = AZ if ix[1] == 2 else AY
    L = 12
    for sgn in (-1, 1):
        ax.plot([LENS_FRONT, LENS_FRONT + L], [c0 + sgn * PUPIL_R, c0 + sgn * (PUPIL_R + L * tanD)], 'b-', lw=0.9)
    ax.set_aspect('equal')
    ax.set_xlim(44, 100)
    ax.set_ylim(c0 - 30, c0 + 30) if ix[1] == 2 else ax.set_ylim(-30, 30)
    ax.set_title(title + '\nblue: 120 deg cone; red dotted: V1.8 trim bore')
    ax.set_xlabel('x (mm)')
    ax.grid(alpha=0.25)
o = cone['eye_trim_u20']
axs[0].text(45, AZ - 28, f'PCB front x {PCB_FRONT:.1f}, holder top {PCB_FRONT + HOLDER_H:.1f} (face back {FACE_BACK}), lens front {LENS_FRONT:.1f} (trim front {TRIM_FRONT})\n'
            f'cone clearance to trim {o["minNormalClearanceMm"]:.2f} mm; bore dia {BORE_D} for the dia {RING_D} lens ring', fontsize=8)
fig.tight_layout()
fig.savefig(HERE / 'render-section.png', dpi=120)
plt.close(fig)
print(json.dumps(_fin({k: checks[k] for k in ('optics', 'screws', 'trimSectionsRadii', 'frontUnchangedOutsideBore', 'faceOnInsertion')}), indent=1)[:9000])
print('smallest', json.dumps(checks['clearances']['smallest12'], indent=1))
print('meshes', json.dumps(checks['meshes'], indent=1))
