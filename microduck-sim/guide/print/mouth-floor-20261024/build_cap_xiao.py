"""White head cap for the mouth floor (Shawn 2026-10-24: "头盖去功放柱、XIAO 放中间").

Starts from the D-025 ear cap (ears-mouth-20261023/head-cap/head_cap_ears-world.stl, robot frame, mm). The amplifier moved to the
yellow floor (build_mouth_floor.py), so its two roof posts have no purpose: inside the box Q the cap becomes the V1.8 roof again
(the V1.8 roof and the ear cap's roof are the same surface there; the posts are the only difference), joined with the same 0.05 mm
overlap as the D-025 collar fill. The XIAO ESP32-S3 touch board leaves the left wall for the middle of the roof, where the amplifier
was, on its 1 mm foam tape (no printed locator, as D-013): nearer the five copper pads, and its old place beside the left-rear exit
lets the exit grow (build_exit_stadium.py). Its board stays off the M pad (x >= 42) and the L1/R1 pads (|y| >= 13).

Outputs here: head_cap_mouth-world.stl, touch_xiao_centre-world.stl, touch_xiao_tape_centre-world.stl, checks-cap.json.
    /tmp/microduck-cad-venv/bin/python build_cap_xiao.py   (under run_bounded_cad.py)"""
import hashlib, json, sys
from pathlib import Path
import manifold3d as mf
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent; PRINT = HERE.parent; WORLD = PRINT / 'world'
sys.path.insert(0, str(PRINT.parent / 'content/interference-audit'))
import ia_lib  # noqa: E402

CAP_IN = PRINT / 'ears-mouth-20261023/head-cap/head_cap_ears-world.stl'
Q_LO, Q_HI = (16.0, -14.0, 136.0), (30.0, 11.5, 158.0)     # the two amplifier posts are x 17.9..27.2, y -12.5..9.8, z 139.8..151
OVERLAP = 0.05
XIAO_C = (30.35, 0.0)                                    # board centre (x, y) on the roof
TAPE_T = 1.0


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def man(k): return mf.Manifold(mf.Mesh(vert_properties=np.asarray(k.vertices, np.float32), tri_verts=np.asarray(k.faces, np.uint32)))


def tri(m):
    g = m.to_mesh(); return trimesh.Trimesh(np.asarray(g.vert_properties[:, :3], float), np.asarray(g.tri_verts), process=False)


def box(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float); return mf.Manifold.cube(tuple(hi - lo)).translate(tuple(lo))


cap_t = trimesh.load(CAP_IN, force='mesh'); v18_t = trimesh.load(WORLD / 'head_cap-v18.stl', force='mesh')
cur, v18 = man(cap_t), man(v18_t)
extra = [c for c in (cur - v18).decompose() if c.volume() > 5]
posts = [c for c in extra if all(np.array(c.bounding_box()[:3]) > np.array(Q_LO)) and all(np.array(c.bounding_box()[3:]) < np.array(Q_HI))]
assert len(posts) == 2, [c.bounding_box() for c in extra]
other_in_q = [c for c in extra if c not in posts and (box(Q_LO, Q_HI) ^ c).volume() > 0.01]
assert not other_in_q, 'something else of the ear cap lies in Q'
Q = box(Q_LO, Q_HI)
new = (cur - Q) + (v18 ^ box(np.subtract(Q_LO, OVERLAP), np.add(Q_HI, OVERLAP)))

# ---------------------------------------------------------------- back microphone seat (optional third INMP441)
# Shawn 2026-10-24 (through the three-microphone session): "如果成本不高 而且没啥副作用 ... 加上得了 省得以后重新打印". A third
# microphone on the back wall resolves front and back without turning the head. Seat as the D-025 ears
# (ears-mouth-20261023/head-cap/build_head_cap.py): dia 1.6 sound hole along the inner-wall normal, horseshoe ID 14.0 wall 1.2 open
# 120 deg towards robot up, board label side on a 1 mm foam ring. At z 133..135 the central back rib stands 2.6 mm
# proud for |y| < 3, so the board (dia 13.4) is centred at y -11: rib edge -3, board edge -4.3. The -y side keeps it away from
# the XIAO wires. Nothing stands on the wall under the ring (checked by ray below).
BACK_YZ = (-11.0, 135.0)   # 2 mm above the ears: at z 133 the ring's lower side met the drawn ID13-14-15 servo cables (0.27 mm)
HOLE_D, RING_ID, RING_WALL, RING_ROOT, RING_OVER_PCB, OPEN_DEG = 1.6, 14.0, 1.2, -1.0, 0.6, 120
BOARD_D, FOAM_T, PCB_T, CHIP, FOAM_RING = 13.4, 1.0, 1.0, (4.72, 3.76, 1.0), (2.4, 5.0)
cap_q = tri(new)
o = np.array([10.0, *BACK_YZ])
loc, _, _ = cap_q.ray.intersects_location([o], [[-1.0, 0, 0]]); loc = np.asarray(loc).reshape(-1, 3)
loc = loc[np.argsort(o[0] - loc[:, 0])]; inner, outer = loc[0], loc[1]
nearf = (np.linalg.norm(cap_q.triangles_center - inner, axis=1) < 4.0) & (cap_q.face_normals @ np.array([1.0, 0, 0]) > 0.5)
ax = (cap_q.face_normals[nearf] * cap_q.area_faces[nearf, None]).sum(0); ax /= np.linalg.norm(ax)
bu = np.array([0, 0, -1.0]) - ax * np.dot(ax, [0, 0, -1.0]); bu /= np.linalg.norm(bu)
bv = np.cross(ax, bu); Rb = np.column_stack([bu, bv, ax])
rows = []
for r in (0, 2, 4, 6.7, RING_ID / 2, RING_ID / 2 + RING_WALL):
    for ph in np.radians(np.arange(0, 360, 15)):
        qq = inner + r * (np.cos(ph) * bu + np.sin(ph) * bv) - 4 * ax
        l2, _, _ = cap_q.ray.intersects_location([qq], [ax]); t = (np.asarray(l2).reshape(-1, 3) - inner) @ ax; t = t[(t > -3) & (t < 3)]
        rows.append((r, float(t.max()) if len(t) else None))
assert all(t is not None for _, t in rows), 'the ring footprint leaves the back wall'
wall_disc = max(t for r, t in rows if r <= BOARD_D / 2)
assert wall_disc < 1.0, ('something stands on the back wall under the board', wall_disc)
board_t = max(FOAM_T, wall_disc + 0.2); top = board_t + PCB_T + RING_OVER_PCB
ring = mf.Manifold.cylinder(top - RING_ROOT, RING_ID / 2 + RING_WALL, RING_ID / 2 + RING_WALL, 96) - \
    mf.Manifold.cylinder(top - RING_ROOT + 2, RING_ID / 2, RING_ID / 2, 96).translate((0, 0, -1))
hw = np.radians(OPEN_DEG / 2)
wedge = mf.Manifold.extrude(mf.CrossSection([[(0.0, 0.0)] + [(20 * np.cos(np.pi + t), 20 * np.sin(np.pi + t)) for t in np.linspace(-hw, hw, 13)]]),
                            top - RING_ROOT + 4).translate((0, 0, -2))
M4 = lambda p: np.hstack([Rb, np.reshape(p, (3, 1))]).tolist()
hole = mf.Manifold.cylinder(8.0, HOLE_D / 2, HOLE_D / 2, 48).transform(M4(inner - 5.0 * ax))
new = (new + (ring - wedge).transform(M4(inner + RING_ROOT * ax))) - hole
placeb = lambda m, t0: m.translate((0, 0, t0)).transform(M4(inner))
mic_b = placeb(mf.Manifold.cylinder(PCB_T, BOARD_D / 2, BOARD_D / 2, 64), board_t) + \
    placeb(box((-CHIP[0] / 2, -CHIP[1] / 2, 0), (CHIP[0] / 2, CHIP[1] / 2, CHIP[2])), board_t + PCB_T)
foam_b = placeb(mf.Manifold.cylinder(board_t, FOAM_RING[1] / 2, FOAM_RING[1] / 2, 48) - mf.Manifold.cylinder(board_t, FOAM_RING[0] / 2, FOAM_RING[0] / 2, 48), 0.0) - new
tri(mic_b).export(HERE / 'mic_back-world.stl'); tri(foam_b).export(HERE / 'mic_foam_back-world.stl')
back_seat = dict(rayYZ=BACK_YZ, innerHit=np.round(inner, 3).tolist(), outerHit=np.round(outer, 3).tolist(), wallAlongRayMm=round(float(np.linalg.norm(outer - inner)), 3),
                 axisIntoCavity=np.round(ax, 4).tolist(), tiltFromHorizontalDeg=round(float(np.degrees(np.arcsin(-ax[2]))), 1),
                 wallMaxUnderBoardMm=round(wall_disc, 3), boardFaceAlongAxisMm=round(board_t, 3), ringTopAlongAxisMm=round(top, 3),
                 boardBounds=np.round(np.array(mic_b.bounding_box()).reshape(2, 3), 2).tolist())

q = tri(new); q = trimesh.Trimesh(q.vertices.astype(np.float32).astype(float), q.faces)            # the coplanar roof seam leaves edges
new = man(q).simplify(1e-4)                                                                        # that collapse in the float32 STL;
new_t = tri(new)                                                                                   # simplify them at STL precision
assert new_t.is_volume and len(new.decompose()) == 1
new_t.export(HERE / 'head_cap_mouth-world.stl')
chk = trimesh.load(HERE / 'head_cap_mouth-world.stl', force='mesh', process=False)                 # the release pipeline's load_mesh test
uv, inv = np.unique(chk.vertices, axis=0, return_inverse=True); chk = trimesh.Trimesh(uv, inv[chk.faces], process=False)
assert chk.is_watertight and chk.is_winding_consistent, 'exported cap STL is not closed'

# ---------------------------------------------------------------- XIAO on the roof
xiao = trimesh.Trimesh(*ia_lib.load_solid('touch_xiao'), process=False)
body = max(xiao.split(only_watertight=False), key=lambda b: abs(b.volume))
tape = trimesh.load(WORLD / 'touch_xiao_tape.stl', force='mesh')
obb = body.bounding_box_oriented; To = np.array(obb.primitive.transform); ext = np.array(obb.primitive.extents)
order = np.argsort(ext)[::-1]; Ax = To[:3, :3][:, order]                     # long, short, thin axes of the board
n_t = tape.centroid - To[:3, 3]
if Ax[:, 2] @ n_t < 0:                                                      # thin axis towards the tape (the wall side)
    Ax[:, 2] *= -1; Ax[:, 1] *= -1
if np.linalg.det(Ax) < 0:                                                   # sorting the OBB axes can leave them left-handed: a
    Ax[:, 1] *= -1                                                          # mirrored board; keep the tape side, flip the short axis
# roof underside plane over the footprint (rays up from inside)
gx, gy = np.meshgrid(np.linspace(XIAO_C[0] - 10, XIAO_C[0] + 10, 9), np.linspace(XIAO_C[1] - 8.5, XIAO_C[1] + 8.5, 7))
P = np.c_[gx.ravel(), gy.ravel(), np.full(gx.size, 125.0)]
loc, ri, _ = new_t.ray.intersects_location(P, np.tile([0, 0, 1.0], (len(P), 1)))
roof = np.full(len(P), np.inf)
for p, i in zip(loc, ri): roof[i] = min(roof[i], p[2])
A = np.c_[np.ones(len(P)), P[:, :2]]; coef, *_ = np.linalg.lstsq(A, roof, rcond=None)
nrm = np.array([-coef[1], -coef[2], 1.0]); nrm /= np.linalg.norm(nrm)        # roof normal (up)
ex = np.array([1.0, 0, 0]) - nrm * nrm[0]; ex /= np.linalg.norm(ex); ey = np.cross(nrm, ex)
Bn = np.column_stack([ex, ey, nrm])                                          # board long -> x, short -> y, tape side -> up
R = Bn @ Ax.T
def place(m):
    k = m.copy(); k.apply_translation(-To[:3, 3]); k.apply_transform(np.vstack([np.c_[R, np.zeros(3)], [0, 0, 0, 1]])); return k
xiao_n, tape_n = place(xiao), place(tape)
# lift until the tape's top face is just under the roof at every footprint point
tv = tape_n.vertices
roof_at = lambda x, y: coef[0] + coef[1] * x + coef[2] * y
dz_c = roof_at(*XIAO_C) - 0.0
shift = np.array([XIAO_C[0], XIAO_C[1], 0.0]) - np.r_[tape_n.bounds.mean(0)[:2], 0]
xiao_n.apply_translation(shift); tape_n.apply_translation(shift)
gap = min(roof_at(x, y) - z for x, y, z in tape_n.vertices)
lift = gap - 0.05 + 0.0
xiao_n.apply_translation([0, 0, lift]); tape_n.apply_translation([0, 0, lift])
xiao_n.export(HERE / 'touch_xiao_centre-world.stl'); tape_n.export(HERE / 'touch_xiao_tape_centre-world.stl')


def near(a, b, pad=4.0, n=3000):
    lo, hi = a.bounds[0] - pad, a.bounds[1] + pad
    keep = np.all(b.triangles.max(1) >= lo, 1) & np.all(b.triangles.min(1) <= hi, 1)
    if not keep.any(): return f'>{pad}'
    cm = trimesh.Trimesh(b.vertices, b.faces[keep], process=False)
    Pp = np.vstack([a.vertices, trimesh.sample.sample_surface(a, n, seed=1)[0]])
    return round(float(min(trimesh.proximity.closest_point(cm, Pp[k:k + 250])[1].min() for k in range(0, len(Pp), 250))), 2)


NB = ['camera_cable_stub', 'touch_pad_l1', 'touch_pad_r1', 'touch_pad_m', 'touch_pad_l2', 'touch_pad_r2', 'motor15', 'motor13', 'head_yaw_link']
O = {}
for k in NB:
    try: O[k] = trimesh.Trimesh(*ia_lib.load_solid(k), process=False)
    except Exception:
        if (WORLD / f'{k}.stl').exists(): O[k] = trimesh.load(WORLD / f'{k}.stl', force='mesh')
O['head_cap'] = new_t
body_n = max(xiao_n.split(only_watertight=False), key=lambda b: abs(b.volume))
mic_bt = tri(mic_b); back_clear = {}
for k in json.loads((ia_lib.CACHE / 'solids-manifest.json').read_text()):       # every solid within 15 mm of the back board
    if k in ('head_cap', 'touch_xiao', 'touch_xiao_tape') or k.startswith('mic_'): continue
    v, f = ia_lib.load_solid(k)
    if np.all(v.max(0) > mic_bt.bounds[0] - 15) and np.all(v.min(0) < mic_bt.bounds[1] + 15):
        back_clear[k] = near(mic_bt, trimesh.Trimesh(v, f, process=False), pad=15.0)
back_clear['touch_xiao'] = near(mic_bt, body_n, pad=15.0)
out = dict(input=dict(path=str(CAP_IN), sha256=sha(CAP_IN)), Q=[Q_LO, Q_HI], postsRemovedMm3=[round(p.volume(), 1) for p in posts],
           volumes=dict(before=round(cur.volume(), 1), after=round(new.volume(), 1)), bodies=len(new.decompose()), isVolume=bool(new_t.is_volume),
           xiao=dict(boardBounds=np.round(body_n.bounds, 2).tolist(), boardExtents=np.round(ext[order], 2).tolist(), roofPlane=np.round(coef, 5).tolist(),
                     roofTiltDeg=round(float(np.degrees(np.arccos(nrm[2]))), 2), tapeTopGapToRoofMm=0.05,
                     clearanceMm={k: near(body_n, m) for k, m in O.items()}),
           backMic=dict(back_seat, clearanceMm=back_clear),
           sha256={n: sha(HERE / f'{n}.stl') for n in ('head_cap_mouth-world', 'touch_xiao_centre-world', 'touch_xiao_tape_centre-world', 'mic_back-world', 'mic_foam_back-world')})
(HERE / 'checks-cap.json').write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps(out, indent=1))
