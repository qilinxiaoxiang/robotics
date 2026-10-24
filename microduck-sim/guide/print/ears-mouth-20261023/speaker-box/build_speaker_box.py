"""Mouth speaker box for D-025 (Shawn 2026-10-23: "扬声器可以考虑放在嘴巴上面 这样声音张嘴出来"; "单独打印扬声器盒").

The CMS-30204-18SP speaker (30 x 20 x 4.0 mm, Digi-Key CMS-30204-18SP-ND) leaves the roof and stands on its short edge on
the yellow floor behind the camera, face forward (+x). Its face is taped (1 mm foam loop on the rim, as D-008) to the back
of a mounting plate with a window; in front of the plate a closed chamber turns the sound down into a flat duct that runs
along the floor under the camera to the six dia 2.5 port holes over the lower jaw (interface.json port_holes). The duct
has no bottom: the yellow floor closes it, and 1 mm foam tape under the wall bottoms seals it and holds the box. The back of
the speaker is open to the head, which serves as its back volume.

Robot frame, mm (x forward, y left, z up). Floor top z 111.3 (x 52.5..75); the box stays at x >= 52.6, in front of the
jaw support plate edge, so all of it stands on the floor. The camera board bottom is z 115.1 (x >= 65 in this y band):
the duct roof top is z 114.6.

Outputs (this folder): speaker_box-world.stl, speaker_mouth-world.stl (the speaker model in its new place, solder pads up),
speaker_tape_rim-world.stl and speaker_box_tape-world.stl (the two foam-tape loops), checks.json.

    /tmp/microduck-cad-venv/bin/python build_speaker_box.py
"""
import json
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
PRINT = HERE.parent.parent
WORLD = PRINT / 'world'
IFACE = json.loads((HERE.parent / 'interface.json').read_text())

W = 1.2                       # wall: three 0.4 mm lines
FLOOR, TAPE = 111.3, 1.0      # yellow floor top; foam tape under every wall bottom
ZB = FLOOR + TAPE             # printed bottom of the box
SPK = (30.0, 20.0, 4.0)       # speaker long, short, depth
CLR = 0.2                     # speaker clearance in its slot
YC = -3.0                     # speaker and duct centre (the ports are at y -7 and +1)
X_BACK = 53.0                 # speaker back face
X_FACE = X_BACK + SPK[2] + TAPE   # back of the mounting plate: speaker face plus the 1 mm foam loop on its rim
PLATE = 1.4
CHAMBER = 2.2                 # front chamber depth (x)
TOP = 145.0                   # box top (interface envelope)
DUCT_Y = (-11.5, 6.0)         # duct and chamber inside, y (the -y wall stays 0.6 mm inside the face panel side ledge at y -13.3)
DUCT_ROOF = 113.4             # duct roof underside: 2.1 mm high duct
DUCT_END = 74.0               # duct inside ends here (last port edge 73.25)
WIN = (15.0, 24.0, 3.0)       # window in the plate: width (y), height (z), corner radius; the foam loop on the rim stays outside it
SPK_Z0 = ZB + W               # the speaker stands on the base slab


def box(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return mf.Manifold.cube(tuple(hi - lo)).translate(tuple(lo))


def tri(m):
    g = m.to_mesh()
    return trimesh.Trimesh(np.asarray(g.vert_properties[:, :3], float), np.asarray(g.tri_verts), process=False)


def man(k):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(k.vertices, np.float32), tri_verts=np.asarray(k.faces, np.uint32)))


x_plate1 = X_FACE + PLATE
x_front0 = x_plate1 + CHAMBER
x_front1 = x_front0 + W
ys0, ys1 = YC - SPK[1] / 2 - CLR, YC + SPK[1] / 2 + CLR          # speaker slot, y
dy0, dy1 = DUCT_Y

parts = [
    box((X_BACK - 0.4, ys0 - W, ZB), (X_FACE, ys1 + W, SPK_Z0)),                       # base slab the speaker stands on
    box((X_BACK - 0.4, ys0 - W, ZB), (X_FACE, ys0, TOP - 6)),                          # side rails locating the speaker
    box((X_BACK - 0.4, ys1, ZB), (X_FACE, ys1 + W, TOP - 6)),
    box((X_FACE, ys0 - W, ZB), (x_plate1, ys1 + W, TOP)),                              # mounting plate
    box((x_plate1, dy0 - W, ZB), (x_front1, dy0, TOP)),                                # chamber side walls
    box((x_plate1, dy1, ZB), (x_front1, dy1 + W, TOP)),
    box((x_plate1, dy0 - W, TOP - W), (x_front1, dy1 + W, TOP)),                       # chamber top
    box((x_front0, dy0 - W, DUCT_ROOF), (x_front1, dy1 + W, TOP)),                     # chamber front wall, down to the duct roof
    box((x_front1, dy0 - W, ZB), (DUCT_END + W, dy0, DUCT_ROOF + W)),                  # duct side walls
    box((x_front1, dy1, ZB), (DUCT_END + W, dy1 + W, DUCT_ROOF + W)),
    box((x_front0, dy0 - W, DUCT_ROOF), (DUCT_END + W, dy1 + W, DUCT_ROOF + W)),       # duct roof
    box((DUCT_END, dy0 - W, ZB), (DUCT_END + W, dy1 + W, DUCT_ROOF + W)),              # duct end wall
]
body = parts[0]
for p in parts[1:]:
    body = body + p
# window: rounded rectangle through the plate
wy, wz, wr = WIN
zc = SPK_Z0 + SPK[0] / 2
win2d = mf.CrossSection.square((wy - 2 * wr, wz - 2 * wr), center=True).offset(wr, mf.JoinType.Round, circular_segments=48)
window = mf.Manifold.extrude(win2d, PLATE + 2).transform([[0, 0, 1, X_FACE - 1], [1, 0, 0, YC], [0, 1, 0, zc]])
body = body - window

# speaker model in its new place: the roof model's oriented box mapped to face +x, long side up, centred in the slot
spk = trimesh.load(WORLD / 'speaker.stl', force='mesh')
obb = spk.bounding_box_oriented
To = np.array(obb.primitive.transform); ext = np.array(obb.primitive.extents)
order = np.argsort(ext)[::-1]                       # long, short, thin axes of the model
A = To[:3, :3][:, order]
roof_normal = np.array([0, 0, 1.0])                 # the old face looked at the roof grille
if A[:, 2] @ roof_normal < 0:
    A[:, 2] *= -1; A[:, 1] *= -1
if A[:, 0] @ np.array([1.0, 0, 0]) < 0:              # the solder-pad end faced the amplifier (+x): it goes up
    A[:, 0] *= -1; A[:, 1] *= -1
new_axes = np.column_stack([[0, 0, 1.0], [0, 1.0, 0], [1.0, 0, 0]])   # long -> z, short -> y, face -> +x
R = new_axes @ A.T
spk_new = spk.copy(); spk_new.apply_translation(-To[:3, 3]); spk_new.apply_transform(np.vstack([np.hstack([R, [[0], [0], [0]]]), [0, 0, 0, 1]]))
c_new = np.array([0, YC, SPK_Z0 + SPK[0] / 2])
spk_new.apply_translation(c_new - spk_new.bounding_box.centroid * [0, 1, 1] + [X_FACE - TAPE - spk_new.bounds[1, 0], 0, 0])   # face (+x) on the foam

# foam tape (1 mm, as D-008): a closed loop on the speaker rim between the speaker face and the plate, and a loop under
# the wall bottoms that seals the chamber and the duct on the floor and holds the box
rim = mf.CrossSection.square((SPK[1] - 2 * 0.4 - 2 * wr, SPK[0] - 2 * 0.4 - 2 * wr), center=True).offset(wr, mf.JoinType.Round, circular_segments=48)
hole = mf.CrossSection.square((wy + 1.0 - 2 * wr, wz + 1.0 - 2 * wr), center=True).offset(wr, mf.JoinType.Round, circular_segments=48)
tape_rim = mf.Manifold.extrude(rim - hole, TAPE).transform([[0, 0, 1, X_FACE - TAPE], [1, 0, 0, YC], [0, 1, 0, zc]])
foot = mf.Manifold.extrude(body.slice(ZB + 0.05), TAPE).translate((0, 0, FLOOR))
tri(tape_rim).export(HERE / 'speaker_tape_rim-world.stl'); tri(foot).export(HERE / 'speaker_box_tape-world.stl')

res = tri(body)
res.export(HERE / 'speaker_box-world.stl')
spk_new.export(HERE / 'speaker_mouth-world.stl')
duct_area = (DUCT_ROOF - FLOOR) * (dy1 - dy0)
ports = IFACE['port_holes']['centres_xy']
checks = dict(
    params=dict(wall=W, floorTop=FLOOR, tape=TAPE, speaker=SPK, clearance=CLR, yCentre=YC, xBack=X_BACK, plate=PLATE, chamber=CHAMBER,
                top=TOP, ductY=DUCT_Y, ductRoofUnderside=DUCT_ROOF, ductEnd=DUCT_END, window=WIN),
    bodies=len(body.decompose()), watertight=bool(res.is_watertight), volumeMm3=round(res.volume, 1), massG_PLA=round(res.volume * 1.24e-3, 2),
    tapeRimMinWidthMm=round(float(min(SPK[1] - 0.8 - (wy + 1.0), SPK[0] - 0.8 - (wz + 1.0)) / 2), 2), tapeFootAreaMm2=round(foot.volume() / TAPE, 1),
    bounds=np.round(res.bounds, 2).tolist(), speakerBounds=np.round(spk_new.bounds, 2).tolist(), speakerModelExtents=np.round(ext, 2).tolist(),
    ductCrossSectionMm2=round(duct_area, 1), portAreaMm2=round(len(ports) * np.pi * 1.25 ** 2, 1),
    portsInsideDuct=all(dy0 + 1.25 <= py <= dy1 - 1.25 and x_plate1 <= px - 1.25 and px + 1.25 <= DUCT_END for px, py in ports))
(HERE / 'checks.json').write_text(json.dumps(checks, indent=1))
print(json.dumps(checks, indent=1))
