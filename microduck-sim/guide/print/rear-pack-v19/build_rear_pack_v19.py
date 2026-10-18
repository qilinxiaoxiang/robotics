"""V1.9 candidate of the MicroDuck rear pack (source of truth for the next incremental print set; V1.8 stays in ../rear-pack).
Changes from V1.8: (4) the BNO085 is screwed to a rib (two M2 x 4 through its rear corner holes) instead of an edge slot, shelf
and zip tie; (2) the T-head outline is grown 0.4 mm and its two shoulders are thickened 3 mm towards the back, so the printed
V1.8 side shells seat on the pack (shell roof on the top edge, the shell's inner rib pair under the shoulder); (5) the DFR1202 front
lips and corner feet are removed, so the OpenRB-150 slides straight in and out from behind (+x / -x) with the shells on and only
the cover off (Shawn, 2026-10-13: the board must not need the side shells off).
Outputs go to this folder: rear_pack-world.stl, rear_pack_cover-world.stl, build.json, features.json.
World frame = guide frame (mm, x forward, y left, z up). Every feature is listed in FEATURES with its purpose.
Usage: build_rear_pack.py [chamfer_cx chamfer_cz]   (lower-front corner chamfer of the OpenRB bay, default 0 0 = none)
"""
import sys, json
from pathlib import Path
import numpy as np
import manifold3d as m3
from shapely.geometry import Polygon, box as sbox
from shapely.ops import unary_union
from shapely.affinity import translate
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'rear-pack'))
import pack_lib as P  # noqa: E402
OUTDIR = Path(__file__).resolve().parent

CH_CX, CH_CZ = (float(sys.argv[1]), float(sys.argv[2])) if len(sys.argv) > 2 else (0.0, 0.0)

# ------------------------------------------------------------------ parameters (all mm, world frame)
PL = dict(x0=-21.0, x1=-19.0, half_w=21.3, z_bot=-40.0, bay_half_w=15.3, bay_z_bot=-44.0, r_bot=1.5,
          ear_half_w=27.2, ear_z=32.0, notch_half_w=6.0, notch_z=32.7, notch_r=1.0)
TOP_EDGE = [(-27.2, 36.43), (-26.7, 37.2), (-26.0, 37.55), (-25.0, 37.8), (-20.0, 38.1), (-15.0, 38.36), (-11.4, 38.55), (-6.0, 38.8),
            (6.0, 38.8), (11.4, 38.55), (15.0, 38.36), (20.0, 38.1), (25.0, 37.8), (26.0, 37.55), (26.7, 37.2), (27.2, 36.43)]
# original head top edge (39.4 at the centre falling to 38.25 at |y| 25.5), symmetrised and lowered to sit 0.6 mm under the
# shells' rear-top edge measured in the plate slab (shell underside z 39.44 at |y| 6 .. 38.42 at |y| 25 .. 37.7 at |y| 27).
# V1.9 grows this whole head outline (ear underside, ear tip, top edge) by HEAD['grow'] before the notch is cut.
HEAD = dict(grow=0.4, bar_x0=-24.0, bar_x1=-21.0, bar_y_in=15.3, bar_z0=31.6, bar_top_drop=0.05)
# Shell seat (proposal 2, approved 2026-10-13). The printed V1.8 shells have, at x -24.5..-19.5 and |y| 22.0..29.3, an inner rib
# pair (ribs x -24.5..-23.2 and -20.8..-19.5, tops z 30.42 left / 30.51 right, slot floor z 22.4 between them). V1.8 left the shell
# roof 0.59 mm above the head and the 2 mm ear covered only the front rib. grow 0.4 brings the plate top edge to 0.19 mm under the
# left shell roof (0.31 right) and the ear tip to |y| 27.6; the bars thicken each shoulder over x -24..-21 (bar_x1 overlaps the plate)
# so it covers the slot and most of the rear rib. The roof drops about 0.1 mm from x -21 to x -24 (measured on both shells), so
# the bars' top edge sits bar_top_drop lower than the plate's: smallest swept-section gap 0.154 mm left / 0.269 mm right.
# Bars stop at |y| 15.3 (the bay wall's outer face) so the OpenRB terminal room and the cable rows behind the notch stay open;
# below z 31.6 (the grown ear underside) they would enter the shells' rib slot.
WALL = dict(y_in=13.6, y_out=15.3, x0=-37.0, z_top=28.5)                # OpenRB bay side walls (inner face 13.6 = driver room)
RIB = dict(y_in=13.6, y_out=15.3, x0=-45.0, x1=-37.0)                   # DFR channel ribs (same faces, continuous outside)
BOT = dict(z0=-44.0, z1=-42.8, x0=-45.0, x1=-20.0)                      # bottom wall (1.2 thick: driver room under lower pads)
USB_OPEN = ((-31.4, -7.3), (-23.9, 6.7))
TETHER_OPEN = ((-44.5, -3.0), (-39.5, 3.0))
WINDOW = dict(x0=-31.9, x1=-25.2, z0=-29.0, z1=-16.5)                   # +y wall window: neck DXL plug (z -27.75..-17.75) with 1.25 mm all round
PAD = dict(r=2.5, x0=-24.8, x1=-21.0, pilot_r=0.8, pilot_x1=-19.6)
# V1.8 DFR lips (x -37..-36, |y| 11.9..13.6, z -3.5..18) and corner feet (x -45..-38.5, |y| 10.3..13.6, z -7.3..-3) are removed in
# V1.9: they sat inside the OpenRB's rear insertion shadow (PCB edge to |y| 13.0) and were the only parts of the robot in it with
# the shells on (straight +x sweep: feet hit from 20 to 4 mm out, lips from 12 to 10 mm). The DFR1202 is not fitted
# (power-diagram/README.md); the channel stays empty and open.
POST = dict(y_out=18.6, x0=-45.0, x1=-40.0, x_taper_end=-36.7, z0=-40.0, chamfer=3.3, pilot_r=0.8, pilot_depth=4.8,
            holes=[(16.1, 26.0), (16.1, -36.5), (-16.1, 26.0), (-16.1, -36.5)])   # chamfer: 45-degree underside from (|y| 15.3, z -40) to (18.6, -36.7)
IMU = dict(y0=-5.5, y1=-2.27, prof=[(-19.5, 2.2), (-13.0, 8.7), (-13.0, 31.0), (-19.5, 31.0)],
           bosses=[(-15.46, 8.04), (-15.46, 28.36)], pilot_r=0.8)
# BNO085 rib on the plate front face: x -19..-13, y -5.5..-2.27 (board back face at -2.265), z 31 down to a 45-degree underside that
# ends 0.2 above the torso base plate top (z 2) at the plate. Two dia 1.6 through pilots on the board's rear corner holes
# (x -15.46, z 8.04 / 28.36): M2 x 4 through the 1.6 mm PCB leaves 2.4 mm of shank in the rib. x1 -13.0 keeps the rib clear of the
# right hip link dxl-5-4 behind the board; the profile starts at x -19.5 to overlap the plate.
WEB_CUT = ((-18.3, -6.4, 22.0), (-13.0, 6.4, 28.0))                     # original upper tab web removed (IMU board passes)
TAB_LOW = ((-21.0, -14.5, -6.0), (-13.5, 14.5, -0.5))
TAB_UP = ((-21.0, -14.5, 22.5), (-13.5, 14.5, 27.5))
COVER = dict(x0=-47.0, x1=-45.0, half_w=18.6, low_half_w=15.3, low_z=-40.0, z0=-44.0, z1=29.5, r_edge=1.0, hole_r=1.1,
             lip=((-45.0, -13.2, 27.3), (-37.5, 13.2, 28.5)))


def rounded(poly, r):
    return poly.buffer(-r, join_style=1).buffer(r, join_style=1)


def head_outline():
    """V1.8 T-head (ears from ear_z, TOP_EDGE, r1 corners) grown by HEAD['grow'] (round joins)."""
    p = PL
    head = Polygon([(-p['ear_half_w'], p['ear_z'])] + TOP_EDGE + [(p['ear_half_w'], p['ear_z'])])
    return rounded(head, 1.0).buffer(HEAD['grow'], join_style=1)


def notch_outline():
    p = PL
    return rounded(sbox(-p['notch_half_w'], p['notch_z'], p['notch_half_w'], 45.0), p['notch_r'])


def plate_outline():
    p = PL
    body = rounded(sbox(-p['half_w'], p['z_bot'], p['half_w'], 33.0), p['r_bot'])
    bay_front = sbox(-p['bay_half_w'], p['bay_z_bot'], p['bay_half_w'], -38.0)
    return unary_union([body, head_outline(), bay_front]).difference(notch_outline()).simplify(0.02)


def bar_outline():
    """Shoulder bar section in (y, z): the grown head with its top edge lowered bar_top_drop, for |y| >= bar_y_in and z >= bar_z0."""
    g = head_outline()
    lowered = translate(g, 0.0, -HEAD['bar_top_drop'])
    side = unary_union([sbox(HEAD['bar_y_in'], HEAD['bar_z0'], 40.0, 50.0), sbox(-40.0, HEAD['bar_z0'], -HEAD['bar_y_in'], 50.0)])
    return g.intersection(lowered).intersection(side).simplify(0.02)


def build_body():
    parts = []
    parts.append(P.extrude_yz(plate_outline(), PL['x0'], PL['x1']))
    # shoulder bars behind the T-head (shell seat), overlapping the plate by 0.5 mm so they fuse
    parts.append(P.extrude_yz(bar_outline(), HEAD['bar_x0'], HEAD['bar_x1'] + 0.5))
    # original hip-yaw screw tabs, taken from the current power_support solid
    ps = P.solid_m('power_support')
    parts.append(ps ^ P.box(*TAB_LOW))
    parts.append((ps ^ P.box(*TAB_UP)) - P.box(*WEB_CUT))
    # OpenRB standoff pads
    for (y, z) in P.openrb_holes_world():
        parts.append(P.cyl_x(PAD['r'], PAD['x0'], PAD['x1'] + 0.5, y, z))
    # bay side walls + channel ribs (one continuous outer face), bottom wall
    for s in (1, -1):
        parts.append(P.box((RIB['x0'], min(s * WALL['y_in'], s * WALL['y_out']), BOT['z0']),
                           (PL['x0'] + 0.5, max(s * WALL['y_in'], s * WALL['y_out']), WALL['z_top'])))
    parts.append(P.box((BOT['x0'], -WALL['y_out'], BOT['z0']), (BOT['x1'], WALL['y_out'], BOT['z1'])))
    # rear corner posts for the cover screws (full height, flush with cover width, 45 deg taper back to the rib face)
    for s in (1, -1):
        plan = Polygon([(POST['x0'], s * RIB['y_in']), (POST['x0'], s * POST['y_out']), (POST['x1'], s * POST['y_out']),
                        (POST['x_taper_end'], s * RIB['y_out']), (POST['x_taper_end'], s * RIB['y_in'])])
        prof = Polygon([(s * (RIB['y_in'] - 1), POST['z0']), (s * WALL['y_out'], POST['z0']), (s * POST['y_out'], POST['z0'] + POST['chamfer']),
                        (s * (POST['y_out'] + 1), POST['z0'] + POST['chamfer']), (s * (POST['y_out'] + 1), WALL['z_top'] + 1), (s * (RIB['y_in'] - 1), WALL['z_top'] + 1)]).buffer(0)
        parts.append(P.extrude_xy(plan, POST['z0'] - 1, WALL['z_top']) ^ P.extrude_yz(prof, POST['x0'] - 1, POST['x_taper_end'] + 1))
    # IMU rib (profile in x,z extruded along y from y0 to y1)
    im = IMU
    rib = m3.CrossSection(P.polys_from_shapely(Polygon(im['prof'])), m3.FillRule.EvenOdd).extrude(im['y1'] - im['y0'])
    parts.append(rib.transform(np.array([[1.0, 0, 0, 0], [0, 0, 1.0, im['y0']], [0, 1.0, 0, 0]])))
    body = P.union(parts)
    # openings and pilots
    cuts = [P.box((USB_OPEN[0][0], USB_OPEN[0][1], BOT['z0'] - 1), (USB_OPEN[1][0], USB_OPEN[1][1], BOT['z1'] + 1)),
            P.box((TETHER_OPEN[0][0], TETHER_OPEN[0][1], BOT['z0'] - 1), (TETHER_OPEN[1][0], TETHER_OPEN[1][1], BOT['z1'] + 1)),
            P.box((WINDOW['x0'], WALL['y_in'] - 1, WINDOW['z0']), (WINDOW['x1'], POST['y_out'] + 1, WINDOW['z1']))]
    for (y, z) in P.openrb_holes_world():
        cuts.append(P.cyl_x(PAD['pilot_r'], PAD['x0'] - 1, PAD['pilot_x1'], y, z))
    for (y, z) in POST['holes']:
        cuts.append(P.cyl_x(POST['pilot_r'], POST['x0'] - 1, POST['x0'] + POST['pilot_depth'], y, z))
    for (x, z) in IMU['bosses']:
        cuts.append(P.cyl_y(IMU['pilot_r'], IMU['y0'] - 1, IMU['y1'] + 1, x, z))
    if CH_CX > 0 and CH_CZ > 0:   # lower-front corner chamfer (plane through (x1-cx, z_bot) and (x1, z_bot+cz)), full width
        tri = Polygon([(PL['x1'] + 1, BOT['z0'] - 1), (PL['x1'] - CH_CX - 1 * CH_CX / CH_CZ, BOT['z0'] - 1), (PL['x1'] + 1, BOT['z0'] + CH_CZ + 1 * CH_CZ / CH_CX)])
        tri = Polygon([(PL['x1'] - CH_CX, BOT['z0']), (PL['x1'], BOT['z0'] + CH_CZ), (PL['x1'] + 2, BOT['z0'] + CH_CZ + 2 * CH_CZ / CH_CX),
                       (PL['x1'] + 2, BOT['z0'] - 2), (PL['x1'] - CH_CX - 2 * CH_CX / CH_CZ, BOT['z0'] - 2)])
        cs = m3.CrossSection(P.polys_from_shapely(tri), m3.FillRule.EvenOdd).extrude(2 * WALL['y_out'] + 2)   # local (x, z, w)
        T = np.array([[1.0, 0, 0, 0], [0, 0, 1.0, -WALL['y_out'] - 1], [0, 1.0, 0, 0]])
        cuts.append(cs.transform(T))
    return body - P.union(cuts)


def build_cover():
    c = COVER
    hw, lw, lz, ch = c['half_w'], c['low_half_w'], c['low_z'], POST['chamfer']
    base = Polygon([(-lw, c['z0']), (lw, c['z0']), (lw, lz), (hw, lz + ch), (hw, c['z1']), (-hw, c['z1']), (-hw, lz + ch), (-lw, lz)])
    top_round = unary_union([rounded(sbox(-hw, c['z1'] - 8.0, hw, c['z1']), 1.5), sbox(-hw - 1, c['z0'] - 1, hw + 1, c['z1'] - 4.0)])
    outline = base.intersection(top_round)
    plate = P.extrude_yz(outline.buffer(0).simplify(0.02), c['x0'], c['x1'])
    # vertical outer edge rounding on the back edges (cutters over-extended past the faces)
    from shapely.geometry import Point
    for s in (1, -1):
        for hw, z0, z1 in ((c['half_w'], c['low_z'], c['z1']), (c['low_half_w'], c['z0'], c['low_z'])):
            sq = sbox(c['x0'] - 1, min(s * (hw - c['r_edge']), s * (hw + 1)), c['x0'] + c['r_edge'], max(s * (hw - c['r_edge']), s * (hw + 1)))
            corner = sq.difference(Point(c['x0'] + c['r_edge'], s * (hw - c['r_edge'])).buffer(c['r_edge'], 32))
            plate = plate - P.extrude_xy(corner, z0 - (1 if z0 == c['z0'] else 0), z1 + (1 if z1 == c['z1'] else 0))
    cover = plate + P.box(*c['lip'])
    for (y, z) in POST['holes']:
        cover = cover - P.cyl_x(c['hole_r'], c['x0'] - 1, c['x1'] + 1, y, z)
    return cover


FEATURES = {
 'body': [
  {'id': 'plate', 'what': 'front plate x -21..-19, |y|<=21.3 from z -40 up (bottom corners r1.5), T-head = the V1.8 head (ears |y|<=27.2 from z 32, top edge 38.8 at the notch .. 36.43 at the ear corners, r1 corners) grown 0.4 mm all round: ears |y|<=27.6 from z 31.6, top edge 39.2 at the notch', 'purpose': 'replaces the original power-support plate; carries the four hip-yaw case screw tabs; back wall of the hip-yaw motors; its top edge carries the printed V1.8 shell roofs (0.19 mm under the left roof, 0.31 mm under the right)'},
  {'id': 'shoulder_bars', 'what': 'two bars x -24..-21 behind the T-head, section = the grown head for |y| >= 15.3 and z >= 31.6 with the top edge 0.05 lower than the plate (the shell roof drops about 0.1 mm towards the back)', 'purpose': 'shell seat: the printed V1.8 shells rest their roof on the bars (0.15 mm left, 0.27 mm right) and their inner rib pair (x -24.5..-19.5, tops z 30.4) sits under the bars, so the rear half of each shell can neither sag nor lift more than the rib gap; the bars stop at |y| 15.3 to keep the terminal room and the notch cable rows open'},
  {'id': 'bay_front', 'what': 'plate continues down to z -44 for |y|<=15.3', 'purpose': 'closes the front of the OpenRB bay; its lower part is the chamferable face (see checks.json freeToChamfer)'},
  {'id': 'head_notch', 'what': 'top-centre notch y +-6 down to z 32.7, r1 corners (12 wide x 6.1 deep)', 'purpose': 'cable pass-over from the bay to the head/IMU plug, as on the original head'},
  {'id': 'tabs_lower', 'what': 'original lower screw lugs and web (power_support cut in x -21..-13.5, |y|<=14.5, z -6..-0.5)', 'purpose': 'hip-yaw case screws S10-case-069 / S05-case-074 pass exactly as now'},
  {'id': 'tabs_upper', 'what': 'original upper screw lugs and gussets (power_support cut in z 22.5..27.5), thin centre web removed for |y|<=6.4', 'purpose': 'hip-yaw case screws S10-case-072 / S05-case-076 pass exactly as now; the web is removed so the IMU board can pass through'},
  {'id': 'openrb_pads', 'what': 'four dia 5 pads on the plate rear face x -24.8..-21 at the OpenRB hole positions, dia 1.6 pilots to x -19.6', 'purpose': 'OpenRB-150 standoffs; M2x6 self-tapping screws from the component side (1.6 PCB + 3.8 pad + 0.6 plate)'},
  {'id': 'side_walls', 'what': 'walls y +-(13.6..15.3), x -45..-21, z -44..28.5 (bay and DFR channel share one outer face)', 'purpose': 'sides of the OpenRB bay and of the DFR1202 channel; inner face at 13.6 leaves a dia 6 driver room over the OpenRB screws'},
  {'id': 'bottom_wall', 'what': 'z -44..-42.8, x -45..-19, |y|<=15.3', 'purpose': 'floor of the pack and print bed face; 1.2 thick so the dia 6 driver reaches the lower OpenRB screws'},
  {'id': 'usb_opening', 'what': 'bottom-wall cut x -31.4..-23.9, y -7.3..6.7', 'purpose': 'USB-C plug room (bench use)'},
  {'id': 'tether_opening', 'what': 'bottom-wall cut x -44.5..-39.5, y +-3', 'purpose': '20 V battery tether enters the DFR channel'},
  {'id': 'neck_window', 'what': '+y wall cut x -31.9..-25.2, z -29..-16.5 (6.7 x 12.5)', 'purpose': 'neck DXL plug on the +y side port (plug room z -27.75..-17.75 with 1.25 mm all round); link N leaves the pack through it'},
  {'id': 'cover_posts', 'what': 'two corner blocks x -45..-40 (45-degree taper to the wall face at x -36.7), |y| 13.6..18.6, z -40..28.5 with a 45-degree underside from (|y| 15.3, z -40) to (18.6, -36.7), dia 1.6 pilots 4.8 deep at (+-16.1, 26.0) and (+-16.1, -36.5) (M2 x 6 through the 2 mm cover ends 0.8 before the pilot bottom)', 'purpose': 'four M2x6 tapping screws hold the rear cover; blocks are flush with the cover width so the cover closes flush; nothing wider than the bay sits below z -40; the sloped underside prints without support'},
  {'id': 'imu_rib', 'what': 'rib x -19..-13, y -5.5..-2.27, z up to 31 with a 45-degree underside from (x -13, z 8.7) to (x -19.5, z 2.2); two dia 1.6 through pilots along y at (x -15.46, z 8.04) and (x -15.46, z 28.36)', 'purpose': 'BNO085 mount: the board back rests on the rib face and two M2 x 4 through its rear corner holes hold it (screwed on the bench before the pack goes in); the front holes stay empty because a rib reaching them would cross the right hip link dxl-5-4 and overhang the torso base'},
 ],
 'cover': [
  {'id': 'cover_plate', 'what': '2 mm plate x -47..-45, |y|<=18.6 for z -36.7..29.5, 45-degree lower-outer corners down to |y|<=15.3 at z -40, |y|<=15.3 for z -44..-40, top corners r1.5, back vertical edges r1', 'purpose': 'closes the DFR channel and the bay from behind; outline follows the body (posts above z -40 with their sloped undersides, bay width below)'},
  {'id': 'cover_lip', 'what': 'inward lip x -45..-37.5, |y|<=13.2, z 27.3..28.5', 'purpose': 'holds the DFR1202 down (0.3 above the board top)'},
  {'id': 'cover_holes', 'what': 'four dia 2.2 clearance holes at (+-16.1, 26.0) and (+-16.1, -36.5)', 'purpose': 'M2x6 tapping screws into the body posts (dia 4 pan heads seat on the flat back face)'},
 ],
 'retired_by_this_part': P.RETIRED,
 'removed_from_v18': [
  {'id': 'dfr_lips', 'what': 'V1.8: x -37..-36, |y| 11.9..13.6, z -3.5..18 (DFR1202 front stops)', 'why': 'inside the OpenRB-150 rear insertion shadow (PCB edges reach |y| 12.4 / 13.0); with them gone the board slides straight in and out along x from behind with both shells on (check_v19_board_rear.json). The DFR1202 is not fitted (bringup/build/power-diagram/README.md).'},
  {'id': 'dfr_feet', 'what': 'V1.8: two 45-degree feet x -45..-38.5, |y| 10.3..13.6, z -7.3..-3 (DFR1202 rests)', 'why': 'same: the feet were the first contact of a straight rear insertion (from 20 mm out to 4 mm out). A converter brought back into the channel would need its own removable hold-down and must come out before the board.'},
 ],
}

if __name__ == '__main__':
    body = build_body(); cover = build_cover()
    bm = P.clean_mesh(body); cm = P.clean_mesh(cover)
    bm.export(OUTDIR / 'rear_pack-world.stl'); cm.export(OUTDIR / 'rear_pack_cover-world.stl')
    info = {}
    for name, man, mesh in (('body', body, bm), ('cover', cover, cm)):
        info[name] = dict(status=str(man.status()), genus=int(man.genus()), volume_mm3=round(float(man.volume()), 2),
                          area_mm2=round(float(man.surface_area()), 2), tris=int(len(mesh.faces)), watertight=bool(mesh.is_watertight),
                          winding_consistent=bool(mesh.is_winding_consistent), bodies=int(len(mesh.split(only_watertight=False))),
                          bounds=np.round(mesh.bounds, 3).tolist())
    info['chamfer_lower_front'] = {'cx': CH_CX, 'cz': CH_CZ}
    info['params'] = dict(PL=PL, TOP_EDGE=TOP_EDGE, HEAD=HEAD, WALL=WALL, RIB=RIB, BOT=BOT, USB_OPEN=USB_OPEN, TETHER_OPEN=TETHER_OPEN, WINDOW=WINDOW,
                          PAD=PAD, POST=POST, IMU=IMU, WEB_CUT=WEB_CUT, TAB_LOW=TAB_LOW, TAB_UP=TAB_UP, COVER=COVER,
                          openrb_holes_yz=P.openrb_holes_world())
    P.jdump(info, OUTDIR / 'build.json')
    P.jdump(FEATURES, OUTDIR / 'features.json')
    print(json.dumps({k: v for k, v in info.items() if k in ('body', 'cover')}, indent=1))
