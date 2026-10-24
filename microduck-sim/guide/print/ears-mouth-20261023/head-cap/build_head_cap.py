"""White head cap for the D-025 ears and mouth speaker (Shawn 2026-10-23: "按 A 耳朵位做，扬声器挪到嘴上方").

Starts from the printed A7Z cap (print/world/head_cap.stl = a7z-head/head_cap_a7z-world.stl, robot frame, mm) and:
- removes the roof speaker: inside the box Q (x -16..21.3, |y| < 19.5, z > 136) the cap becomes the V1.8 cap again, so the
  speaker collar (2515 mm3) goes and the roof grille holes and the speaker pocket are filled (V1.8 roof, 1.7 mm). Q stops at
  x 21.3, 0.5 mm in front of the amplifier (x 21.8), whose roof pocket and two posts stay: the amplifier stays in the roof.
- adds two ears at option A (interface.json ears): on each side a dia 1.6 sound hole through the wall along the inner-wall
  normal at the ray hit of x 60.5, z 133, and round it a horseshoe locator for the round INMP441 board (dia 13.4): ID 14.0,
  wall 1.2, a 240 deg arc open at the top so the soldered leads leave upwards and the arc prints without support in the
  roof-down cap pose (its open part is the arc whose outside would face the bed). The board lies label side to the wall on
  a 1 mm foam ring round the port. The dead A7Z board rails of the D-022 cap cross the ear zone behind the board (x 51..65);
  over the ear disc (dia 19) and over x 48..61, z 114..151 (the whole fin at x 49.7..56 and its block at z 139) everything
  standing on the inner wall is cut away down to the wall (wall_follow_zone), so no cut fin edge is left as a sliver.

Outputs (this folder): head_cap_ears-world.stl, checks.json.

    /tmp/microduck-cad-venv/bin/python build_head_cap.py
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

Q_LO, Q_HI = (-16.0, -19.5, 136.0), (21.3, 19.5, 158.0)
HOLE_D = 1.6
RING_ID, RING_WALL = 14.0, 1.2
BOARD_D, FOAM_T, PCB_T = 13.4, 1.0, 1.0
CHIP = (4.72, 3.76, 1.0)  # INMP441 package on the back of the board (TDK datasheet), port through the board to the label side
FOAM_RING = (2.4, 5.0)    # foam ring round the port: ID, OD
RING_ROOT = -1.0          # ring starts 1.0 mm inside the wall (wall 1.7 mm) so it fuses with it
RING_OVER_PCB = 0.6       # ring top this far past the board's back face, measured at the rim
OPEN_DEG = 120            # open arc (deg) centred on robot up
CLEAR_R = 9.5             # ear zone cleared of the dead A7Z rails down to the wall: radius round the axis
RAIL_RECT = (133.0 - 151.0, 133.0 - 114.0, 48.0 - 60.5, 61.0 - 60.5)   # (u0, u1, v0, v1): the rail fin x 49.7..56 and its block, z 114..151


def man(k):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(k.vertices, np.float32), tri_verts=np.asarray(k.faces, np.uint32)))


def tri(m):
    g = m.to_mesh()
    return trimesh.Trimesh(np.asarray(g.vert_properties[:, :3], float), np.asarray(g.tri_verts), process=False)


def box(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return mf.Manifold.cube(tuple(hi - lo)).translate(tuple(lo))


def frame(a):
    """Orthonormal (u, v) in the plane normal to a, u towards robot down projected into it."""
    u = np.array([0, 0, -1.0]) - a * np.dot(a, [0, 0, -1.0]); u /= np.linalg.norm(u)
    return u, np.cross(a, u)


def wall_floor(mesh, inner, Rm, uv, wall, depth=0.1):
    """Floor height (along the axis a = Rm[:, 2], from the inner-wall hit) at local points uv: the outer-surface hit plus the
    wall thickness along the ray (normal thickness / cos of the ray to the outer face), or the real inner surface (the second hit)
    where that is nearer, less depth (mm). The floor so stays at least depth inside the material: a floor that crossed the real inner
    surface would leave pinch points that the merged STL turns into non-manifold edges."""
    a = Rm[:, 2]
    q = inner + np.column_stack([uv, np.full(len(uv), -15.0)]) @ Rm.T
    out = np.full(len(uv), np.nan)
    loc, ri, fi = mesh.ray.intersects_location(q, np.tile(a, (len(q), 1)))
    t = (loc - inner) @ a
    for k in range(len(uv)):
        s = ri == k
        if s.any():
            ts = np.sort(t[s]); m = np.argmin(t[s]); c = abs(mesh.face_normals[fi[s][m]] @ a)
            nominal = ts[0] + wall / max(c, 0.3)
            out[k] = (min(nominal, ts[1]) if len(ts) > 1 else nominal) - depth
    return np.where(np.isnan(out), np.nanmax(out), out)


def height_solid(inner, Rm, grid_uv, floor, top, shape, polar):
    """Closed solid between the floor heights and a flat top over a structured (u, v) grid; polar grids add a centre point."""
    nr, nc = shape
    V = [[*grid_uv[k], floor[k]] for k in range(len(floor))] + [[*grid_uv[k], top] for k in range(len(floor))]
    n = len(floor); F = []
    idx = lambda i, j, k: (i * nc + (j % nc if polar else j)) + k * n
    for i in range(nr - 1):
        for j in range(nc if polar else nc - 1):
            for k in (0, 1):
                q = [idx(i, j, k), idx(i + 1, j, k), idx(i + 1, j + 1, k), idx(i, j + 1, k)]
                F += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]]
    def side(ring):
        for a, b in zip(ring[:-1], ring[1:]):
            F.extend([[a, b, b + n], [a, b + n, a + n]])
    if polar:
        side([idx(nr - 1, j, 0) for j in range(nc + 1)])
        c = len(V); V += [[0, 0, floor[:nc].mean()], [0, 0, top]]
        for j in range(nc):
            F += [[c, idx(0, j, 0), idx(0, j + 1, 0)], [c + 1, idx(0, j, 1), idx(0, j + 1, 1)]]
    else:
        ring = [idx(0, j, 0) for j in range(nc)] + [idx(i, nc - 1, 0) for i in range(1, nr)] + \
               [idx(nr - 1, j, 0) for j in range(nc - 2, -1, -1)] + [idx(i, 0, 0) for i in range(nr - 2, -1, -1)]
        side(ring)
    m = trimesh.Trimesh(np.array(V) @ Rm.T + inner, F, process=True)
    trimesh.repair.fix_normals(m)
    assert m.is_watertight and m.volume > 0, 'height solid not closed'
    return man(m)


def wall_follow_zone(mesh, inner, Rm, radius, rect, top):
    """Everything standing on the inner wall over the ear disc (radius round the axis) and over a (u0, u1, v0, v1)
    rectangle of the local frame (columns of Rm: u robot down, v, a into the cavity; origin the inner-wall hit). The
    underside follows the wall (wall_floor), so the wall keeps its own thickness and no stub is left on it.
    Returns (zone, normal wall thickness at the centre)."""
    a = Rm[:, 2]
    l, _, _ = mesh.ray.intersects_location([inner - 6 * a], [a]); h = np.sort((np.asarray(l).reshape(-1, 3) - inner) @ a)
    h = h[(h > -4) & (h < 4)]; wall = float(h[1] - h[0])
    # grid lines half a step off the 96-segment ring, its open-arc edges and the 48-segment hole, so no two edges meet exactly
    rs = np.linspace(0, radius, 25)[1:]; ph = np.linspace(0, 2 * np.pi, 96, endpoint=False) + np.pi / 96
    uv = np.array([[r * np.cos(f), r * np.sin(f)] for r in rs for f in ph])
    disc = height_solid(inner, Rm, uv, wall_floor(mesh, inner, Rm, uv, wall), top, (len(rs), len(ph)), True)
    u0, u1, v0, v1 = rect
    us, vs = np.arange(u0 + 0.25, u1 + 1e-9, 0.5), np.arange(v0 + 0.25, v1 + 1e-9, 0.5)   # off the disc centre point
    uv = np.array([[uu, vv] for uu in us for vv in vs])
    # the rectangle floor sits 0.05 mm above the disc floor: two floors at the same depth cross each other where the zones
    # overlap and leave pinch points
    box_ = height_solid(inner, Rm, uv, wall_floor(mesh, inner, Rm, uv, wall, depth=0.05), top, (len(us), len(vs)), False)
    return disc + box_, wall


cap_t = trimesh.load(PRINT / 'a7z-head/head_cap_a7z-world.stl', force='mesh')   # the printed V1.17 A7Z cap
v18_t = trimesh.load(WORLD / 'head_cap-v18.stl', force='mesh')
amp_t = trimesh.load(WORLD / 'amplifier.stl', force='mesh')
cur, v18 = man(cap_t), man(v18_t)

# 1. roof speaker out, amplifier posts kept
Q = box(Q_LO, Q_HI)
posts = [c for c in (cur - v18).decompose() if c.volume() > 50 and c.bounding_box()[0] > 17 and c.bounding_box()[3] < 30]
assert len(posts) == 2, 'expected the two amplifier posts'
# The two pieces and the posts overlap by OVERLAP instead of touching face to face: touching faces leave duplicate vertices that
# turn into non-manifold edges once the STL vertices are merged (release_pipeline_v2 load_mesh rejects them).
OVERLAP = 0.05
base = (cur - Q) + (v18 ^ box(np.subtract(Q_LO, OVERLAP), np.add(Q_HI, OVERLAP)))
for p in posts:
    base = base + p.translate((0, 0, OVERLAP))      # 0.05 mm up into the roof: overlapping, not touching (the post end moves with it)

# 2. ears
ears, out, edits = [], base, Q
for side, name in ((1, 'left'), (-1, 'right')):
    pt = np.array(IFACE['ears'][name]['point'] if name in IFACE['ears'] else [60.5, side * 38.5, 133.0], float)
    o = np.array([pt[0], side * 60.0, pt[2]])
    loc, _, fi = cap_t.ray.intersects_location([o], [[0, -side, 0.0]])
    loc = np.asarray(loc).reshape(-1, 3); order = np.argsort(np.abs(loc[:, 1] - o[1]))
    outer, inner = loc[order[0]], loc[order[1]]
    near = np.linalg.norm(cap_t.triangles_center - inner, axis=1) < 4.0
    near &= cap_t.face_normals @ np.array([0, -side, 0.0]) > 0.5
    a = (cap_t.face_normals[near] * cap_t.area_faces[near, None]).sum(0); a /= np.linalg.norm(a)
    u, v = frame(a)
    Rm = np.column_stack([u, v, a])
    rect = RAIL_RECT if v[0] > 0 else (RAIL_RECT[0], RAIL_RECT[1], -RAIL_RECT[3], -RAIL_RECT[2])   # v runs along +x or -x
    zone, wall_t = wall_follow_zone(cap_t, inner, Rm, CLEAR_R, rect, 22.0)
    cleared = round((out ^ zone).volume(), 1)
    edits = edits + mf.Manifold.cylinder(19.0, CLEAR_R + 0.1, CLEAR_R + 0.1, 96).translate((0, 0, -3.0)).transform(np.hstack([Rm, inner.reshape(3, 1)]).tolist()) + \
        box((47.9, -46 if side < 0 else 15, 105.0), (61.1, -15 if side < 0 else 46, 151.1))
    out = out - zone
    cap_t2 = tri(out)
    # inner-wall height along a over the board disc and the ring footprint
    rows = []
    for r in (0, 2, 4, 6.7, RING_ID / 2, RING_ID / 2 + RING_WALL):
        for ph in np.radians(np.arange(0, 360, 15)):
            q = inner + r * (np.cos(ph) * u + np.sin(ph) * v) - 4 * a
            l2, _, _ = cap_t2.ray.intersects_location([q], [a])
            l2 = np.asarray(l2).reshape(-1, 3)
            t = (l2 - inner) @ a
            t = t[(t > -3) & (t < 3)]
            rows.append((r, float(np.degrees(ph)), float(t.max()) if len(t) else None))
    wall_disc = max(t for r, _, t in rows if r <= BOARD_D / 2 and t is not None)
    board_t = max(FOAM_T, wall_disc + 0.2)                 # board face (label side) along a from the centre wall point
    ring_rim = [t for r, _, t in rows if r >= RING_ID / 2 and t is not None]
    top = board_t + PCB_T + RING_OVER_PCB
    ring = mf.Manifold.cylinder(top - RING_ROOT, RING_ID / 2 + RING_WALL, RING_ID / 2 + RING_WALL, 96) - \
        mf.Manifold.cylinder(top - RING_ROOT + 2, RING_ID / 2, RING_ID / 2, 96).translate((0, 0, -1))
    # open arc: a wedge centred on robot up (-u) of OPEN_DEG
    hw = np.radians(OPEN_DEG / 2); R = 20.0
    poly = [(0.0, 0.0)] + [(R * np.cos(np.pi + t), R * np.sin(np.pi + t)) for t in np.linspace(-hw, hw, 13)]
    wedge = mf.Manifold.extrude(mf.CrossSection([poly]), top - RING_ROOT + 4).translate((0, 0, -2))
    ring = ring - wedge
    p0 = inner + RING_ROOT * a
    ring_w = ring.transform(np.hstack([Rm, p0.reshape(3, 1)]).tolist())
    hole = mf.Manifold.cylinder(8.0, HOLE_D / 2, HOLE_D / 2, 48).transform(np.hstack([Rm, (inner - 5.0 * a).reshape(3, 1)]).tolist())
    out = (out + ring_w) - hole
    place = lambda m, t0: m.translate((0, 0, t0)).transform(np.hstack([Rm, inner.reshape(3, 1)]).tolist())
    mic = place(mf.Manifold.cylinder(PCB_T, BOARD_D / 2, BOARD_D / 2, 64), board_t) + \
        place(box((-CHIP[0] / 2, -CHIP[1] / 2, 0), (CHIP[0] / 2, CHIP[1] / 2, CHIP[2])), board_t + PCB_T)
    foam = place(mf.Manifold.cylinder(board_t, FOAM_RING[1] / 2, FOAM_RING[1] / 2, 48) - mf.Manifold.cylinder(board_t, FOAM_RING[0] / 2, FOAM_RING[0] / 2, 48), 0.0) - out
    tri(mic).export(HERE / f'mic_{name}-world.stl'); tri(foam).export(HERE / f'mic_foam_{name}-world.stl')
    ears.append(dict(side=name, railClearedMm3=cleared, wallNormalMm=round(wall_t, 3), outerHit=np.round(outer, 3).tolist(), innerHit=np.round(inner, 3).tolist(),
                     wallAlongRayMm=round(float(np.linalg.norm(outer - inner)), 3), axisIntoCavity=np.round(a, 4).tolist(),
                     boardFaceAlongAxisMm=round(board_t, 3), wallMaxUnderBoardMm=round(wall_disc, 3),
                     ringTopAlongAxisMm=round(top, 3), ringRimWallMm=[round(min(ring_rim), 3), round(max(ring_rim), 3)],
                     ringOuterDia=RING_ID + 2 * RING_WALL, openArcDeg=OPEN_DEG, openTowards='robot up'))

out = out.simplify(0.002)      # drop the sub-micron slivers the wall-following cut floors leave; they collapse in the float32 STL
res = tri(out)
# Exactly coincident vertices left where two sheets touch (the collar-box seam, where the V1.17 and V1.8 caps share identical
# faces): each copy moves 0.0001 mm into its own solid along its vertex normal, so the merged STL stays 2-manifold.
_v = np.array(res.vertices); _, _inv, _cnt = np.unique(_v, axis=0, return_inverse=True, return_counts=True)
_dup = np.where(_cnt[_inv] > 1)[0]
_v[_dup] -= 1e-4 * res.vertex_normals[_dup]
touching_vertices_nudged = int(len(_dup))
# Sliver faces whose corners round to the same float32 STL vertex are collapsed here, so the file reads as written.
_v32, _inv32 = np.unique(_v.astype(np.float32), axis=0, return_inverse=True)
_f = _inv32[res.faces]; _keep = (_f[:, 0] != _f[:, 1]) & (_f[:, 1] != _f[:, 2]) & (_f[:, 0] != _f[:, 2])
res = trimesh.Trimesh(_v32.astype(float), _f[_keep], process=False); sliver_faces_collapsed = int((~_keep).sum())
res.export(HERE / 'head_cap_ears-world.stl')
# closed after exact vertex merging of the written STL, as release_pipeline_v2.load_mesh reads it
_m = trimesh.load(HERE / 'head_cap_ears-world.stl', force='mesh', process=False)
_v, _i = np.unique(_m.vertices, axis=0, return_inverse=True)
_m = trimesh.Trimesh(_v, _i[_m.faces], process=False)
assert _m.is_watertight and _m.is_winding_consistent, 'written cap STL is not closed after vertex merging'
parts = out.decompose()
checks = dict(
    source=dict(cap='print/a7z-head/head_cap_a7z-world.stl', v18='print/world/head_cap-v18.stl'),
    params=dict(Q=[Q_LO, Q_HI], holeDia=HOLE_D, ringId=RING_ID, ringWall=RING_WALL, foamT=FOAM_T, pcbT=PCB_T, ringRoot=RING_ROOT,
                ringOverPcb=RING_OVER_PCB, openArcDeg=OPEN_DEG),
    bodies=len(parts), watertight=bool(res.is_watertight), touchingVerticesNudged=touching_vertices_nudged, sliverFacesCollapsed=sliver_faces_collapsed, volumeMm3=round(res.volume, 1), oldVolumeMm3=round(cap_t.volume, 1),
    v18Volume=round(v18_t.volume, 1),
    ampOverlapMm3=round((out ^ man(amp_t)).volume(), 4),
    outsideEditsXorMm3=round((((out - cur) + (cur - out)) - edits).volume(), 4),
    ears=ears)
(HERE / 'checks.json').write_text(json.dumps(checks, indent=1))
print(json.dumps(checks, indent=1))
