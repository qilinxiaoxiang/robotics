"""Mouth floor of the yellow lower head shell (Shawn 2026-10-24: "按第三版做：黄壳凹槽+12孔+功放导轨+长圆出线口").

The speaker and the amplifier both sit on the yellow floor, on one centre line (x CL) so the speaker leads run straight
(Shawn: "应该对其或者至少供电线的应该对其 也就是两个中心线"):
- speaker CMS-30204-18SP (30 x 20 x 4) face down in a pocket POCKET_DEPTH deep in the 2.7-2.9 mm floor over the lower jaw, on a
  0.3 mm foam-tape loop round its rim (the air gap in front of the grille), solder-pad end towards +y (the amplifier). The pocket
  bottom follows the floor plate (tilted 0.49 deg about y in the world), so the floor left under it is the same everywhere. Its top
  is 0.8 mm under the camera board edge (z 115.1).
- twelve dia 2.5 sound holes through the pocket bottom on a 4 x 3 grid inside the speaker rim, all over the lower jaw (the
  D-025 six ports and the drill template are retired).
- amplifier MAX98357A (Adafruit 3006, 17.78 x 19.05 board, speaker terminal at the middle of one 17.78 edge, PCB from the Adafruit
  board file) components up on 1 mm foam tape, the terminal edge towards -y (the speaker pads), between two low rails that
  locate the board edges (0.3 mm each side) and leave both ends open for the wires. No screws: the hole positions and the soldered
  wire lengths no longer have to match anything.

Input: head_bottom_exit.stl (this folder, the shell with the stadium exit, build_exit_stadium.py).
Outputs here (world frame, robot mm): head_bottom_mouth-world.stl and its V1.8 print pose head_bottom_mouth-print.stl,
speaker_floor-world.stl, amplifier_floor-world.stl, speaker_tape_floor-world.stl, amp_tape-world.stl, checks.json.
    /tmp/microduck-cad-venv/bin/python build_mouth_floor.py   (under run_bounded_cad.py)"""
import hashlib, json, math, sys
from pathlib import Path
import numpy as np, trimesh
from shapely.geometry import Point, Polygon, box as sbox

HERE = Path(__file__).resolve().parent; PRINT = HERE.parent; GUIDE = PRINT.parent; WORLD = PRINT / 'world'
sys.path.insert(0, str(GUIDE / 'content/interference-audit'))
import ia_lib  # noqa: E402

CL = 64.0                                  # shared centre line (x) of the speaker and the amplifier
SPK = (30.0, 20.0, 4.0)                    # speaker long (along y), short (along x), thick
SPK_YC = -2.0                              # speaker centre y
CLR = 0.2                                  # pocket clearance each side
POCKET_DEPTH = 1.5                         # into the floor; 1.2 mm left
POCKET_R = 1.0                             # pocket corner radius
TAPE_SPK = 0.3                             # foam loop under the speaker rim (air gap in front of the grille)
RIM_W = 1.6                                # width of that loop
HOLE_R, HOLE_SEG = 1.25, 32
HOLES = [(x, y) for x in (58.5, 62.5, 66.5, 70.5) for y in (-8.0, -2.0, 4.0)]
AMP = (17.78, 19.05)                       # board across x, along y
AMP_Y0 = 17.0                              # terminal edge of the board
AMP_CLR, RAIL_W, RAIL_H, RAIL_Y = 0.3, 1.2, 4.0, (18.0, 33.0)
TAPE_AMP = 1.0
MIN_FLOOR = 1.2


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def diff(a, bs): return trimesh.boolean.difference([a] + list(bs), engine='manifold')
def union(ms): return trimesh.boolean.union(ms, engine='manifold')


def prism(poly, z0, z1):
    m = trimesh.creation.extrude_polygon(poly, z1 - z0); m.apply_translation([0, 0, z0]); return m


def ray_down(m, pts, z=200.0):
    loc, ri, _ = m.ray.intersects_location(np.c_[pts, np.full(len(pts), z)], np.tile([0, 0, -1.0], (len(pts), 1)), multiple_hits=True)
    out = [[] for _ in pts]
    for p, i in zip(loc, ri): out[i].append(p[2])
    return [sorted(h, reverse=True) for h in out]


hb = trimesh.load(HERE / 'head_bottom_exit.stl', force='mesh'); assert hb.is_volume
# ---------------------------------------------------------------- floor plane under the pocket and the rails
px0, px1 = CL - SPK[1] / 2 - CLR, CL + SPK[1] / 2 + CLR
py0, py1 = SPK_YC - SPK[0] / 2 - CLR, SPK_YC + SPK[0] / 2 + CLR
gx, gy = np.meshgrid(np.linspace(px0 - 1, px1 + 1, 12), np.linspace(py0 - 1, py1 + 1, 16))
grid = np.c_[gx.ravel(), gy.ravel()]
tops = []; pts = []
for (x, y), h in zip(grid, ray_down(hb, grid, 116.0)):
    if len(h) >= 2 and 110.8 < h[0] < 111.8:
        tops.append(h[0]); pts.append((x, y))
pts = np.array(pts); tops = np.array(tops)
A = np.c_[np.ones(len(pts)), pts]; coef, *_ = np.linalg.lstsq(A, tops, rcond=None)      # z = a + b x + c y
fit_res = float(np.abs(A @ coef - tops).max())
SHEAR = np.array([[1, 0, 0, 0], [0, 1, 0, 0], [coef[1], coef[2], 1, coef[0]], [0, 0, 0, 1.0]])   # local z (above the floor top) -> world
def on_floor(m):
    m = m.copy(); m.apply_transform(SHEAR); return m


# ---------------------------------------------------------------- pocket, holes, rails
pocket_poly = sbox(px0, py0, px1, py1).buffer(-POCKET_R).buffer(POCKET_R, quad_segs=12)
pocket = on_floor(prism(pocket_poly, -POCKET_DEPTH, 6.0))
holes = []
for x, y in HOLES:
    c = trimesh.creation.cylinder(radius=HOLE_R, height=20.0, sections=HOLE_SEG); c.apply_translation([x, y, 105.0]); holes.append(c)
ax0, ax1 = CL - AMP[0] / 2 - AMP_CLR, CL + AMP[0] / 2 + AMP_CLR
rails = [on_floor(prism(sbox(ax0 - RAIL_W, RAIL_Y[0], ax0, RAIL_Y[1]), -0.3, RAIL_H)),
         on_floor(prism(sbox(ax1, RAIL_Y[0], ax1 + RAIL_W, RAIL_Y[1]), -0.3, RAIL_H))]
new = diff(union([hb] + rails), [pocket] + holes)
assert new.is_volume

# ---------------------------------------------------------------- speaker, amplifier, foam tapes (world models)
spk = trimesh.load(WORLD / 'speaker.stl', force='mesh')            # D-025 box pose: long axis z (pads at +z), grille face +x
assert np.allclose(spk.extents, (4.5, 20.0, 30.0), atol=0.6), spk.extents
R = np.array([[0, -1.0, 0], [0, 0, 1.0], [-1.0, 0, 0]])           # z (pad end) -> +y, face +x -> -z, y -> -x
spk_n = spk.copy(); spk_n.apply_transform(np.vstack([np.c_[R, np.zeros(3)], [0, 0, 0, 1]]))
floor_at = lambda x, y: coef[0] + coef[1] * x + coef[2] * y
z_face = floor_at(CL, SPK_YC) - POCKET_DEPTH + TAPE_SPK
c = spk_n.bounds.mean(0); spk_n.apply_translation([CL - c[0], SPK_YC - c[1], z_face - spk_n.bounds[0, 2]])
rim = sbox(CL - SPK[1] / 2, SPK_YC - SPK[0] / 2, CL + SPK[1] / 2, SPK_YC + SPK[0] / 2)
tape_spk = on_floor(prism(rim.difference(rim.buffer(-RIM_W)), -POCKET_DEPTH, -POCKET_DEPTH + TAPE_SPK))
amp = trimesh.load(WORLD / 'amplifier.stl', force='mesh')           # D-012 roof pose: board along x, terminal block at the -x end, up
Ra = np.array([[0, -1.0, 0], [1.0, 0, 0], [0, 0, 1.0]])           # +90 deg about z: the terminal end (-x) -> -y
amp_n = amp.copy(); amp_n.apply_transform(np.vstack([np.c_[Ra, np.zeros(3)], [0, 0, 0, 1]]))
pcb_lo = amp_n.bounds[0]
z_amp = floor_at(CL, AMP_Y0 + AMP[1] / 2) + TAPE_AMP
amp_n.apply_translation([CL - amp_n.bounds.mean(0)[0], AMP_Y0 - (pcb_lo[1] + 0.4), z_amp - pcb_lo[2]])   # board edge (0.4 in from the terminal overhang) at AMP_Y0
tape_amp = on_floor(prism(sbox(CL - AMP[0] / 2 + 1.0, AMP_Y0 + 1.5, CL + AMP[0] / 2 - 1.0, AMP_Y0 + AMP[1] - 1.5), 0.0, TAPE_AMP))

# ---------------------------------------------------------------- print pose: the exit builder's pose (V1.8 sourceToPrint, bed drop)
V18 = json.loads((PRINT / 'release-V1.8/manifest-V1.8.json').read_text())
HB_T = np.array(next(r for r in V18['parts'] if r['key'] == 'head_bottom')['sourceToPrint'])
ex_print = trimesh.load(HERE / 'head_bottom_exit-print.stl', force='mesh')
hb_r = hb.copy(); hb_r.apply_transform(HB_T); T = HB_T.copy(); T[2, 3] -= hb_r.bounds[0, 2]
dev = float(np.abs(trimesh.transform_points(hb.vertices, T) - ex_print.vertices).max()) if len(hb.vertices) == len(ex_print.vertices) else None
new_p = new.copy(); new_p.apply_transform(T); assert abs(new_p.bounds[0, 2]) < 1e-6, new_p.bounds

for name, m in (('head_bottom_mouth-world', new), ('head_bottom_mouth-print', new_p), ('speaker_floor-world', spk_n), ('amplifier_floor-world', amp_n),
                ('speaker_tape_floor-world', tape_spk), ('amp_tape-world', tape_amp)):
    m.export(HERE / f'{name}.stl')

# ---------------------------------------------------------------- checks
under = ray_down(new, np.array([(x, y) for x in np.linspace(px0 + 0.3, px1 - 0.3, 14) for y in np.linspace(py0 + 0.3, py1 - 0.3, 20)]), 116.0)
left = [h[0] - h[1] for h in under if len(h) >= 2]
webs = []
for i, (x, y) in enumerate(HOLES):
    for j, (u, v) in enumerate(HOLES[i + 1:]):
        webs.append(math.hypot(x - u, y - v) - 2 * HOLE_R)
hole_to_pocket_wall = min(pocket_poly.exterior.distance(Point(x, y)) - HOLE_R for x, y in HOLES)
spk_face = sbox(CL - SPK[1] / 2 + RIM_W, SPK_YC - SPK[0] / 2 + RIM_W, CL + SPK[1] / 2 - RIM_W, SPK_YC + SPK[0] / 2 - RIM_W)
holes_inside_rim = all(spk_face.buffer(-HOLE_R).contains(Point(x, y)) for x, y in HOLES)
jaw = trimesh.Trimesh(*ia_lib.load_solid('jaw_frame'), process=False)
jaw_under = [bool(len(h)) and h[0] > 105 for h in ray_down(jaw, np.array(HOLES), 108.4)]


def near(a, b, pad=4.0, n=3000):
    lo, hi = a.bounds[0] - pad, a.bounds[1] + pad
    keep = np.all(b.triangles.max(1) >= lo, 1) & np.all(b.triangles.min(1) <= hi, 1)
    if not keep.any(): return f'>{pad}'
    cm = trimesh.Trimesh(b.vertices, b.faces[keep], process=False)
    P = np.vstack([a.vertices, trimesh.sample.sample_surface(a, n, seed=1)[0]])
    return round(float(min(trimesh.proximity.closest_point(cm, P[k:k + 250])[1].min() for k in range(0, len(P), 250))), 2)


def inter(a, b):
    try:
        r = trimesh.boolean.intersection([a, b], engine='manifold'); return round(float(r.volume), 3) if len(r.faces) else 0.0
    except Exception as e:
        return str(e)


NB = ['camera_u20cam', 'camera_cable_stub', 'face_panel', 'eye_trim', 'jaw_frame', 'jaw_support', 'motor15', 'mic_left', 'mic_right', 'head_cap']
O = {k: trimesh.Trimesh(*ia_lib.load_solid(k), process=False) for k in NB}
O['jaw_support'] = trimesh.load(HERE / 'jaw_support_exit.stl', force='mesh')
items = {'speaker': spk_n, 'amplifier': amp_n, 'rail_left': rails[0], 'rail_right': rails[1]}
clear = {i: {k: near(m, O[k]) for k in NB} for i, m in items.items()}
inter_nb = {i: {k: inter(m, O[k]) for k in NB} for i, m in items.items() if i in ('speaker', 'amplifier')}
spk_vs_shell = inter(spk_n, new); amp_vs_shell = inter(amp_n, new)
amp_gap = dict(railInnerToBoardMm=AMP_CLR, boardX=[round(CL - AMP[0] / 2, 2), round(CL + AMP[0] / 2, 2)], railsX=[[round(ax0 - RAIL_W, 2), round(ax0, 2)], [round(ax1, 2), round(ax1 + RAIL_W, 2)]],
               modelBounds=np.round(amp_n.bounds, 2).tolist())
lead = dict(speakerPadEndY=round(float(spk_n.bounds[1, 1]), 2), ampBoardEdgeY=AMP_Y0, straightGapMm=round(AMP_Y0 - float(spk_n.bounds[1, 1]), 2), centreLineX=CL)
out = dict(params=dict(CL=CL, SPK=SPK, SPK_YC=SPK_YC, CLR=CLR, POCKET_DEPTH=POCKET_DEPTH, POCKET_R=POCKET_R, TAPE_SPK=TAPE_SPK, RIM_W=RIM_W, HOLE_D=2 * HOLE_R,
                       HOLES=HOLES, AMP=AMP, AMP_Y0=AMP_Y0, AMP_CLR=AMP_CLR, RAIL_W=RAIL_W, RAIL_H=RAIL_H, RAIL_Y=RAIL_Y, TAPE_AMP=TAPE_AMP),
           floorPlane=dict(z='a + b x + c y', abc=np.round(coef, 6).tolist(), maxResidualMm=round(fit_res, 4), samples=len(pts)),
           floorLeftUnderPocketMm=dict(min=round(min(left), 3), max=round(max(left), 3), samples=len(left), required=MIN_FLOOR),
           holes=dict(count=len(HOLES), minWebMm=round(min(webs), 2), minToPocketWallMm=round(hole_to_pocket_wall, 2), insideSpeakerRimTape=holes_inside_rim,
                      jawUnderEvery=all(jaw_under), openAreaMm2=round(len(HOLES) * math.pi * HOLE_R ** 2, 1)),
           speaker=dict(bounds=np.round(spk_n.bounds, 2).tolist(), topZ=round(float(spk_n.bounds[1, 2]), 2), intersectShellMm3=spk_vs_shell),
           amplifier=dict(amp_gap, intersectShellMm3=amp_vs_shell), speakerLead=lead,
           clearanceMm=clear, intersectionMm3=inter_nb,
           body=dict(isVolume=bool(new.is_volume), bodies=len(new.split(only_watertight=False)), volumeBefore=round(float(hb.volume), 1), volumeAfter=round(float(new.volume), 1)),
           printPose=dict(file='head_bottom_mouth-print.stl', exitPrintPoseMaxDevMm=dev, sizeMm=np.round(new_p.extents, 2).tolist()),
           sha256={n: sha(HERE / f'{n}.stl') for n in ('head_bottom_mouth-world', 'head_bottom_mouth-print', 'speaker_floor-world', 'amplifier_floor-world',
                                                        'speaker_tape_floor-world', 'amp_tape-world')},
           input=dict(path=str(HERE / 'head_bottom_exit.stl'), sha256=sha(HERE / 'head_bottom_exit.stl')))
(HERE / 'checks-floor.json').write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps({k: out[k] for k in ('floorPlane', 'floorLeftUnderPocketMm', 'holes', 'speaker', 'amplifier', 'speakerLead', 'body', 'printPose')}, indent=1))
print('clearance', json.dumps(clear)); print('intersections', json.dumps(inter_nb))
