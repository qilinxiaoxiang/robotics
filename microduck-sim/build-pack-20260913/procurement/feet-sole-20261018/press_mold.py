"""Press mold for gluing a bike inner tube sole onto the printed MicroDuck foot with E6000.

The foot (taken off the robot), the glued rubber and the mold are screwed shut with a printed lid until the glue cures
(24-72 h); the mold holds the rubber on the curved edge, where slow E6000 cannot hold it alone, and the glue edge sets the
trim line. Nothing else is needed: no weights, no clamps (Shawn, 2026-10-24).

Geometry, foot STL frame (flat bottom at z = 0), foot seated on a rubber stack of thickness T:
  cavity    the foot bottom offset outward by T along the normal (lower envelope of spheres, as in hotglue_mold.py);
            over the flat one plane at z = -T, the curve lowered by FLAT_BAND so the floor has no step
  top       the cavity ends at the plane z = H_TOP. The rim lies on the offset surface, T from the foot, so the rubber
            passes it without being pinched and the excess leaves over the open top. Depth is set by the rubber under
            the clamp, never by a rim stop (a stop would hold the foot off the rubber).
  gauge     dry, without rubber, the foot drops T and lands on the flat floor; the mold top then crosses the foot at
            H_TOP + T = GLUE_EDGE. A pencil run flat on the mold top marks that line: glue the foot only below it.
  tabs      four locating tabs C_TAB outside the foot outline, wide enough for the rubber flap that rides up the side
  label     raised L or R on a strip at the heel end, top of the letter towards the toe
  posts     four POST mm square posts at the block corners up to POST_TOP, each with a PILOT_D pilot for an M2 x 10 TAP
  lid       flat top at Z_TOP; its underside is the top of the slip-fit foot (as fitted on the robot) lowered by SQUEEZE
            wherever that top is above H_BEAR (the rim and the toe block, right over the curved edge), H_BEAR over the
            socket, and POST_TOP outside the foot. Screwed down until it sits on the posts, it pushes the foot SQUEEZE
            below the nominal seat, so the 0.7-0.8 mm tube plus glue in the 0.70 mm cavity is pressed by at least SQUEEZE.
            LID_AT_POST mm thick at the posts: an M2 x 10 goes 10 - LID_AT_POST mm into the post. Printed top down.

Tube (Shawn, 2026-10-24, calipers): 0.7 mm between the moulded ribs, 0.8 mm on a rib. T = 0.70: the smooth inner
face goes to the foot (the tube's curl then wraps the long sides) and the ribbed outer face to the floor, where the
ribs meet the cavity wall and take the extra squeeze. A rigid cavity slightly thinner than the stack
squeezes the slopes harder than the flat (a vertical lift d opens a slope of tilt a by only d cos a), which is where
the rubber must be held.

  /tmp/microduck-cad-venv/bin/python press_mold.py   -> press-mold-{left,right}.stl, press-lid-{left,right}.stl, press-mold-check.json
"""
import json
from pathlib import Path

import numpy as np
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path as MplPath
from matplotlib.textpath import TextPath
from scipy import ndimage
from scipy.spatial import cKDTree

import hotglue_mold as hg
import trimesh
import manifold3d

HERE = Path(__file__).resolve().parent
STEP = hg.STEP

T = 0.70          # mm rubber stack along the normal (tube between ribs)
GLUE_EDGE = 4.5   # mm above the flat: glue and sole edge, on a ~75 deg side wall (3.0 left the edge on a 55 deg slope; 6.0
                  # needs 6.7 mm of dart per corner). Sim floor contacts reach 1.6 mm.
H_TOP = GLUE_EDGE - T
FLAT_BAND = 0.12  # mm, one layer
C_TAB = 1.5       # mm foot outline -> tab: the 0.8 mm flap plus play
TAB_W, TAB_D, H_TAB = 10.0, 3.0, 8.0
BASE, MARGIN = 3.0, 3.0
POST, PILOT_D, PILOT_DEPTH = 8.0, 1.6, 8.0   # mm; 1.6 mm pilot = the M2 TAP pilot used in the printed robot parts
CLEAR_D = 2.4      # mm lid hole for M2
SQUEEZE = 0.10     # mm the lid pushes the foot below the nominal seat
H_BEAR = 12.0      # mm: the lid presses only on foot top above this (rim 14-16, toe block 16-18.4; the socket is lower)
LID_OVER = 5.0     # mm lid over the highest point of the foot
LID_AT_POST = 4.0  # mm lid thickness on the posts
FIN_MIN = 2.4      # mm narrowest downward lid feature kept
KEY_SHIFT = 8.0    # mm the keyed heel post sits in from its corner
LID_LETTER_H, LID_LETTER_DEPTH = 10.0, 0.6   # mm side letter engraved in the lid top
SLIP = HERE / ".." / ".." / ".." / "guide" / "print" / "foot-slipfit-20261019"
SLIP_FEET = {"left": SLIP / "foot-left-slipfit.stl", "right": SLIP / "foot-right-slipfit.stl"}
LABEL_X, LETTER_H, LETTER_RISE, LABEL_CLEAR = 7.0, 6.5, 0.6, 0.8


def build(side):
    tris = hg.load_tris(hg.FEET[side])
    lo, hi = tris.reshape(-1, 3).min(0), tris.reshape(-1, 3).max(0)
    pad = C_TAB + TAB_D + MARGIN
    xs = np.arange(lo[0] - pad - LABEL_X, hi[0] + pad + 1e-9, STEP); ys = np.arange(lo[1] - pad, hi[1] + pad + 1e-9, STEP)
    low = hg.height_map(tris, xs, ys)
    foot = ~np.isnan(low)
    dist_out = ndimage.distance_transform_edt(~foot) * STEP
    zoff = hg.offset_down(low, T)
    # one plane where the offset lies within a layer of it (the flat's 0.1 mm print waviness), the exact offset on the
    # curve: lowering the whole curve by the band (hotglue_mold.py) opens it to 0.77-0.82 mm, looser than the tube
    floor = np.where(zoff < -T + FLAT_BAND, -T, zoff)
    cavity = ndimage.binary_fill_holes(np.isfinite(floor) & (floor < H_TOP))
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    S = np.full(low.shape, H_TOP)
    S[cavity] = floor[cavity]
    flat = foot & (low < 0.1)
    cx, cy = (X[flat].min() + X[flat].max()) / 2, (Y[flat].min() + Y[flat].max()) / 2
    band = (dist_out >= C_TAB) & (dist_out <= C_TAB + TAB_D)
    tabs = band & ((np.abs(Y - cy) <= TAB_W / 2) | (np.abs(X - cx) <= TAB_W / 2))
    S[tabs] = H_TAB
    # letter, as in hotglue_mold.py
    tp = TextPath((0, 0), side[0].upper(), size=1.0, prop=FontProperties(family="DejaVu Sans", weight="bold"))
    v = tp.vertices; lo_t, hi_t = v.min(0), v.max(0); k = LETTER_H / (hi_t[1] - lo_t[1])
    lx = (xs[0] + LABEL_CLEAR + lo[0] - C_TAB - TAB_D - LABEL_CLEAR) / 2
    u = (v[:, 0] - (lo_t[0] + hi_t[0]) / 2) * k; w = (v[:, 1] - (lo_t[1] + hi_t[1]) / 2) * k
    letter = MplPath(np.stack([lx + w, cy - u], 1), tp.codes).contains_points(np.stack([X.ravel(), Y.ravel()], 1)).reshape(X.shape)
    near = ndimage.binary_dilation(letter, iterations=int(np.ceil(LABEL_CLEAR / STEP)))
    assert letter.any() and (S[near] == H_TOP).all() and not (near & (foot | tabs)).any(), (side, "letter off the free top")
    S[letter] = H_TOP + LETTER_RISE
    zbot = S.min() - BASE

    # lid: top of the slip-fit foot (the foot on the robot; identical to FEET below 4 mm), seen from above
    st = hg.load_tris(SLIP_FEET[side]).copy(); st[:, :, 2] *= -1
    top = -hg.height_map(st, xs, ys)
    has_top = ~np.isnan(top)
    Z_TOP = float(np.nanmax(top)) - SQUEEZE + LID_OVER
    POST_TOP = Z_TOP - LID_AT_POST
    U = np.full(low.shape, POST_TOP)
    U[has_top] = np.maximum(top[has_top] - SQUEEZE, H_BEAR)
    # grey closing: drop every downward lid fin narrower than FIN_MIN (the foot top has slots; a lid copying them grows
    # 0.04-0.75 mm fins that fail the 1.2 mm wall check). Closing only raises U, so it never cuts into the foot.
    r = int(round(FIN_MIN / 2 / STEP)); g = np.arange(-r, r + 1)
    U = ndimage.grey_closing(U, footprint=(g[:, None] ** 2 + g[None, :] ** 2) <= r * r)
    assert U.max() <= POST_TOP + 1e-9
    # posts at the block corners
    # centres half a grid cell off the nodes: a hole vertex on a 0.2 mm grid line leaves zero-area faces in the STL
    pc = [(x, y) for x in (xs[0] + POST / 2 + STEP / 2, xs[-1] - POST / 2 - STEP / 2) for y in (ys[0] + POST / 2 + STEP / 2, ys[-1] - POST / 2 - STEP / 2)]
    # key: the heel post on the +y side (left) or -y side (right) moves KEY_SHIFT towards the middle, so a lid fits only its
    # own mold and only one way round (a rotated or mirrored lid finds no hole over that post)
    k = 1 if side == "left" else 0
    pc[k] = (pc[k][0], pc[k][1] - np.sign(pc[k][1]) * KEY_SHIFT)
    post = np.zeros_like(foot)
    for px, py in pc:
        post |= (np.abs(X - px) <= POST / 2) & (np.abs(Y - py) <= POST / 2)
    assert not (post & (tabs | near | (dist_out < C_TAB + 0.6))).any(), (side, "post on a tab, the letter or the 2.1 mm flap room")
    assert (S[post] == H_TOP).all()   # posts stand on the plain top; they are solid boxes added below, not height-field cells

    # checks: seated on the rubber (foot frame as is) and dry (foot lowered by T)
    gap = np.where(foot, low - S, np.inf)
    tree = cKDTree(np.stack([X[foot], Y[foot], low[foot]], 1))
    dn, _ = tree.query(np.stack([X[cavity], Y[cavity], S[cavity]], 1))
    rim = cavity & ~ndimage.binary_erosion(cavity)
    dn_rim, _ = tree.query(np.stack([X[rim], Y[rim], S[rim]], 1))
    dry_gap = np.where(foot, low - T - S, np.inf)
    dry_touch = foot & (dry_gap < 0.02)
    tab_room = dist_out[tabs].min()
    check = dict(
        side=side, stl=hg.FEET[side].name, T_mm=T, glue_edge_mm=GLUE_EDGE, top_plane_mm=H_TOP,
        seated=dict(interference_cells=int((gap < -1e-6).sum()), min_vertical_gap_mm=round(float(gap[foot].min()), 3),
                    normal_gap_mm=dict(p1=round(float(np.percentile(dn, 1)), 3), p50=round(float(np.percentile(dn, 50)), 3),
                                       p99=round(float(np.percentile(dn, 99)), 3)),
                    rim_normal_gap_mm=dict(min=round(float(dn_rim.min()), 3), p50=round(float(np.median(dn_rim)), 3))),
        dry=dict(interference_cells=int((dry_gap < -1e-6).sum()), touch_cells=int(dry_touch.sum()),
                 touch_height_mm=[round(float(low[dry_touch].min()), 2), round(float(low[dry_touch].max()), 2)],
                 pencil_line_mm=GLUE_EDGE),
        flat_floor_levels=int(np.unique(np.round(S[cavity & flat], 3)).size),
        cavity_area_mm2=round(float(cavity.sum() * STEP * STEP), 1),
        tab_clearance_mm=round(float(tab_room), 2), tab_top_mm=H_TAB,
        block_mm=[round(float(xs[-1] - xs[0]), 1), round(float(ys[-1] - ys[0]), 1), round(float(POST_TOP - zbot), 1)],
    )
    # lid against the foot pushed SQUEEZE below the nominal seat: touches, never cuts in; where it bears
    lid_gap = np.where(has_top, U - (top - SQUEEZE), np.inf)
    bear = has_top & (lid_gap < 0.02)
    flap = foot & (dist_out <= 0) | ((dist_out > 0) & (dist_out <= C_TAB))
    check["lid"] = dict(
        squeeze_mm=SQUEEZE, top_mm=round(Z_TOP, 2), post_top_mm=round(POST_TOP, 2), bear_above_mm=H_BEAR,
        interference_cells=int((lid_gap < -1e-6).sum()), bearing_area_mm2=round(float(bear.sum() * STEP * STEP), 1),
        bearing_height_mm=[round(float(top[bear].min()), 2), round(float(top[bear].max()), 2)],
        min_underside_mm=round(float(U.min()), 2), min_underside_over_tabs_mm=round(float(U[tabs].min()), 2),
        min_underside_outside_foot_mm=round(float(U[~foot].min()), 2),
        screw=dict(spec="M2 x 10 TAP", lid_at_post_mm=LID_AT_POST, into_post_mm=round(10 - LID_AT_POST, 1), pilot_depth_mm=PILOT_DEPTH,
                   pilot_d_mm=PILOT_D, lid_hole_d_mm=CLEAR_D, posts_xy_mm=[[round(a, 2), round(b, 2)] for a, b in pc]),
        lid_thickness_mm=[round(float((Z_TOP - U).min()), 2), round(float((Z_TOP - U).max()), 2)],
    )
    assert check["lid"]["interference_cells"] == 0 and 10 - LID_AT_POST <= PILOT_DEPTH - 1.0

    def cut_holes(path, centres, z0, z1, d, boxes=(), trim_z=None, engrave=None):
        m = trimesh.load(path, force="mesh")
        solid = manifold3d.Manifold(manifold3d.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
        for (x, y), (b0, b1) in boxes:   # solid posts: one flat top face, so the pilot does not slice height-field cells
            solid = solid + manifold3d.Manifold.cube((POST, POST, b1 - b0)).translate((x - POST / 2, y - POST / 2, b0))
        # A cylinder vertex within float32 rounding of a 0.2 mm grid edge leaves zero-area faces in the STL, so take the
        # first odd segment count whose export reads back closed the way release_pipeline_v2.load_mesh reads it
        for seg in (41, 43, 37, 47, 39, 45):
            base = solid
            for x, y in centres:
                base = base - manifold3d.Manifold.cylinder(z1 - z0, d / 2, d / 2, seg).translate((x, y, z0))
            if trim_z is not None:   # through holes: cut the fan-triangulated bottom away, manifold re-triangulates the face
                base = base.trim_by_plane((0.0, 0.0, 1.0), trim_z)
            if engrave is not None:
                base = base - engrave
            o = base.to_mesh()
            trimesh.Trimesh(np.asarray(o.vert_properties)[:, :3], np.asarray(o.tri_verts), process=True).export(path)
            r = trimesh.load(path, force="mesh", process=False)
            v, inv = np.unique(r.vertices, axis=0, return_inverse=True)
            r = trimesh.Trimesh(v, inv[r.faces], process=False)
            if r.is_watertight and r.is_winding_consistent:
                return base.num_tri(), base.genus(), seg
        raise AssertionError(f"{path} not closed after export")

    out = HERE / f"press-mold-{side}.stl"
    hg.write_heightfield_stl(out, xs, ys, S, zbot)
    check["triangles"], check["genus"], check["hole_segments"] = cut_holes(out, pc, POST_TOP - PILOT_DEPTH, POST_TOP + 1, PILOT_D,
                                                   boxes=[(c, (zbot + 1.0, POST_TOP)) for c in pc])
    # lid in its print pose, top face down: rotated 180 deg about x, (x, y, z) -> (x, -y, Z_TOP - z)
    lid = HERE / f"press-lid-{side}.stl"
    hg.write_heightfield_stl(lid, xs, -ys[::-1], (Z_TOP - U)[:, ::-1], -1.0)
    # L or R engraved in the lid top, reading like the mold letter seen from above (top of the letter to the toe), so the
    # assembly-frame glyph (x, y) maps to the print frame (x, -y) on the bed face
    tp = TextPath((0, 0), side[0].upper(), size=1.0, prop=FontProperties(family="DejaVu Sans", weight="bold"))
    kk = LID_LETTER_H / (tp.vertices[:, 1].max() - tp.vertices[:, 1].min())
    c0 = (tp.vertices.min(0) + tp.vertices.max(0)) / 2
    polys = []
    for poly in tp.to_polygons():
        u, w = (poly[:, 0] - c0[0]) * kk, (poly[:, 1] - c0[1]) * kk
        polys.append(np.stack([lx + w, -(cy - u)], 1))
    glyph = manifold3d.CrossSection(polys, manifold3d.FillRule.EvenOdd).extrude(LID_LETTER_DEPTH + 0.1).translate((0, 0, -0.1))
    check["lid"]["triangles"], check["lid"]["genus"], check["lid"]["hole_segments"] = cut_holes(
        lid, [(x, -y) for x, y in pc], -2, Z_TOP - U.min() + 1, CLEAR_D, trim_z=0.0, engrave=glyph)
    check["lid"]["key"] = dict(shifted_post_xy_mm=[round(pc[k][0], 2), round(pc[k][1], 2)], shift_mm=KEY_SHIFT,
                               letter=side[0].upper(), letter_h_mm=LID_LETTER_H, depth_mm=LID_LETTER_DEPTH)
    check["lid"]["print_pose"] = "top face on the bed: assembly (x, y, z) -> print (x, -y, %.3f - z)" % Z_TOP
    np.savez_compressed(HERE / f"press-mold-{side}-maps.npz", xs=xs, ys=ys, S=S, low=low, U=U, top=top)
    return check


if __name__ == "__main__":
    res = [build(s) for s in ("left", "right")]
    (HERE / "press-mold-check.json").write_text(json.dumps(res, indent=1) + "\n")
    print(json.dumps(res, indent=1))
