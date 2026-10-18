"""Build the MicroDuck rear pack: orange body (rear_pack-world.stl) + black rear cover (rear_pack_cover-world.stl).
World frame = guide frame (mm, x forward, y left, z up). Every feature is listed in FEATURES with its purpose.
Usage: build_rear_pack.py [chamfer_cx chamfer_cz]   (lower-front corner chamfer of the OpenRB bay, default 0 0 = none)
"""
import sys, json
import numpy as np
import manifold3d as m3
from shapely.geometry import Polygon, box as sbox
from shapely.ops import unary_union
import pack_lib as P

CH_CX, CH_CZ = (float(sys.argv[1]), float(sys.argv[2])) if len(sys.argv) > 2 else (0.0, 0.0)

# ------------------------------------------------------------------ parameters (all mm, world frame)
PL = dict(x0=-21.0, x1=-19.0, half_w=21.3, z_bot=-40.0, bay_half_w=15.3, bay_z_bot=-44.0, r_bot=1.5,
          ear_half_w=27.2, ear_z=32.0, notch_half_w=6.0, notch_z=32.7, notch_r=1.0)
TOP_EDGE = [(-27.2, 36.43), (-26.7, 37.2), (-26.0, 37.55), (-25.0, 37.8), (-20.0, 38.1), (-15.0, 38.36), (-11.4, 38.55), (-6.0, 38.8),
            (6.0, 38.8), (11.4, 38.55), (15.0, 38.36), (20.0, 38.1), (25.0, 37.8), (26.0, 37.55), (26.7, 37.2), (27.2, 36.43)]
# original head top edge (39.4 at the centre falling to 38.25 at |y| 25.5), symmetrised and lowered to sit 0.6 mm under the
# shells' rear-top edge measured in the plate slab (shell underside z 39.44 at |y| 6 .. 38.42 at |y| 25 .. 37.7 at |y| 27)
WALL = dict(y_in=13.6, y_out=15.3, x0=-37.0, z_top=28.5)                # OpenRB bay side walls (inner face 13.6 = driver room)
RIB = dict(y_in=13.6, y_out=15.3, x0=-45.0, x1=-37.0)                   # DFR channel ribs (same faces, continuous outside)
BOT = dict(z0=-44.0, z1=-42.8, x0=-45.0, x1=-20.0)                      # bottom wall (1.2 thick: driver room under lower pads)
USB_OPEN = ((-31.4, -7.3), (-23.9, 6.7))
TETHER_OPEN = ((-44.5, -3.0), (-39.5, 3.0))
WINDOW = dict(x0=-31.9, x1=-25.2, z0=-29.0, z1=-16.5)                   # +y wall window: neck DXL plug (z -27.75..-17.75) with 1.25 mm all round
PAD = dict(r=2.5, x0=-24.8, x1=-21.0, pilot_r=0.8, pilot_x1=-19.6)
LIP = dict(x0=-37.0, x1=-36.0, y_in=11.9, z0=-3.5, z1=18.0)             # DFR front stops (end below the upper driver path; start outside the OpenRB's tall components |y|<=11.64)
FOOT = [(10.3, -3.0), (13.6, -3.0), (13.6, -7.3), (10.3, -4.0)]         # DFR corner foot section (y,z), 45 deg underside
FOOT_X = (-45.0, -38.5)                                                  # feet stop 1.5 before the channel front so the OpenRB drop-in (x offset -3) clears them
POST = dict(y_out=18.6, x0=-45.0, x1=-40.0, x_taper_end=-36.7, z0=-40.0, chamfer=3.3, pilot_r=0.8, pilot_depth=4.8,
            holes=[(16.1, 26.0), (16.1, -36.5), (-16.1, 26.0), (-16.1, -36.5)])   # chamfer: 45-degree underside from (|y| 15.3, z -40) to (18.6, -36.7)
IMU = dict(fin_x0=-19.0, fin_x1=-15.0, fin_z0=4.3, fin_z1=31.5, fin_neg=(-3.5, -2.45), fin_pos=(-0.5, 0.5),
           shelf=((-19.0, -4.6, 4.3), (-14.3, 4.6, 5.5)), slots=[(-17.3, 2.6, -14.8, 3.9), (-17.3, -3.9, -14.8, -2.6)],
           gusset=[(-19.0, 2.2), (-16.8, 4.4), (-19.0, 4.4)])   # 45-degree root gusset under the shelf (x,z), overlaps the shelf by 0.1, stays 0.2 above the base plate top z 2
WEB_CUT = ((-18.3, -6.4, 22.0), (-13.0, 6.4, 28.0))                     # original upper tab web removed (IMU board passes)
TAB_LOW = ((-21.0, -14.5, -6.0), (-13.5, 14.5, -0.5))
TAB_UP = ((-21.0, -14.5, 22.5), (-13.5, 14.5, 27.5))
COVER = dict(x0=-47.0, x1=-45.0, half_w=18.6, low_half_w=15.3, low_z=-40.0, z0=-44.0, z1=29.5, r_edge=1.0, hole_r=1.1,
             lip=((-45.0, -13.2, 27.3), (-37.5, 13.2, 28.5)))


def rounded(poly, r):
    return poly.buffer(-r, join_style=1).buffer(r, join_style=1)


def plate_outline():
    p = PL
    body = rounded(sbox(-p['half_w'], p['z_bot'], p['half_w'], 33.0), p['r_bot'])
    head = Polygon([(-p['ear_half_w'], p['ear_z'])] + TOP_EDGE + [(p['ear_half_w'], p['ear_z'])])
    head = rounded(head, 1.0)
    bay_front = sbox(-p['bay_half_w'], p['bay_z_bot'], p['bay_half_w'], -38.0)
    notch = rounded(sbox(-p['notch_half_w'], p['notch_z'], p['notch_half_w'], 45.0), p['notch_r'])
    return unary_union([body, head, bay_front]).difference(notch).simplify(0.02)


def build_body():
    parts = []
    parts.append(P.extrude_yz(plate_outline(), PL['x0'], PL['x1']))
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
    # DFR front lips and corner feet
    for s in (1, -1):
        parts.append(P.box((LIP['x0'], min(s * LIP['y_in'], s * (RIB['y_in'] + 0.3)), LIP['z0']),
                           (LIP['x1'], max(s * LIP['y_in'], s * (RIB['y_in'] + 0.3)), LIP['z1'])))
        parts.append(P.extrude_yz(Polygon([(s * y, z) for y, z in FOOT]).buffer(0), FOOT_X[0], FOOT_X[1]))
    # rear corner posts for the cover screws (full height, flush with cover width, 45 deg taper back to the rib face)
    for s in (1, -1):
        plan = Polygon([(POST['x0'], s * RIB['y_in']), (POST['x0'], s * POST['y_out']), (POST['x1'], s * POST['y_out']),
                        (POST['x_taper_end'], s * RIB['y_out']), (POST['x_taper_end'], s * RIB['y_in'])])
        prof = Polygon([(s * (RIB['y_in'] - 1), POST['z0']), (s * WALL['y_out'], POST['z0']), (s * POST['y_out'], POST['z0'] + POST['chamfer']),
                        (s * (POST['y_out'] + 1), POST['z0'] + POST['chamfer']), (s * (POST['y_out'] + 1), WALL['z_top'] + 1), (s * (RIB['y_in'] - 1), WALL['z_top'] + 1)]).buffer(0)
        parts.append(P.extrude_xy(plan, POST['z0'] - 1, WALL['z_top']) ^ P.extrude_yz(prof, POST['x0'] - 1, POST['x_taper_end'] + 1))
    # IMU holder: two fins (edge slot) + shelf with tie slots
    im = IMU
    parts.append(P.box((im['fin_x0'], im['fin_neg'][0], im['fin_z0']), (im['fin_x1'], im['fin_neg'][1], im['fin_z1'])))
    parts.append(P.box((im['fin_x0'], im['fin_pos'][0], im['fin_z0']), (im['fin_x1'], im['fin_pos'][1], im['fin_z1'])))
    shelf = P.box(*im['shelf'])
    g = Polygon(im['gusset']); gcs = m3.CrossSection(P.polys_from_shapely(g), m3.FillRule.EvenOdd).extrude(im['shelf'][1][1] - im['shelf'][0][1])
    shelf = shelf + gcs.transform(np.array([[1.0, 0, 0, 0], [0, 0, 1.0, im['shelf'][0][1]], [0, 1.0, 0, 0]]))
    for (xa, ya, xb, yb) in im['slots']:
        shelf = shelf - P.box((xa, ya, im['shelf'][0][2] - 1), (xb, yb, im['shelf'][1][2] + 1))
    parts.append(shelf)
    body = P.union(parts)
    # openings and pilots
    cuts = [P.box((USB_OPEN[0][0], USB_OPEN[0][1], BOT['z0'] - 1), (USB_OPEN[1][0], USB_OPEN[1][1], BOT['z1'] + 1)),
            P.box((TETHER_OPEN[0][0], TETHER_OPEN[0][1], BOT['z0'] - 1), (TETHER_OPEN[1][0], TETHER_OPEN[1][1], BOT['z1'] + 1)),
            P.box((WINDOW['x0'], WALL['y_in'] - 1, WINDOW['z0']), (WINDOW['x1'], POST['y_out'] + 1, WINDOW['z1']))]
    for (y, z) in P.openrb_holes_world():
        cuts.append(P.cyl_x(PAD['pilot_r'], PAD['x0'] - 1, PAD['pilot_x1'], y, z))
    for (y, z) in POST['holes']:
        cuts.append(P.cyl_x(POST['pilot_r'], POST['x0'] - 1, POST['x0'] + POST['pilot_depth'], y, z))
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
  {'id': 'plate', 'what': 'front plate x -21..-19, |y|<=21.3 from z -40 to 32 (bottom corners r1.5), T-head |y|<=27.2 from z 32 with the original top edge lowered 0.6 mm under the shell edge (38.8 at the notch, 36.43 at the ear corners)', 'purpose': 'replaces the original power-support plate; carries the four hip-yaw case screw tabs; back wall of the hip-yaw motors'},
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
  {'id': 'dfr_lips', 'what': 'x -37..-36, |y| 11.9..13.6, z -3.5..18', 'purpose': 'front stops of the DFR1202 (board drops in from above and rests against them); end at z 18 so the dia 6 driver to the upper OpenRB screws passes; start at |y| 11.9 so the OpenRB drop-in path (tall components to |y| 11.64) clears them'},
  {'id': 'dfr_feet', 'what': 'two 45-degree feet along x -45..-38.5 at the channel bottom corners, top at z -3, |y| 10.3..13.6', 'purpose': 'DFR1202 rests on them (pads down); corner location keeps the three pads free; they stop at x -38.5 so the OpenRB drop-in path clears them'},
  {'id': 'cover_posts', 'what': 'two corner blocks x -45..-40 (45-degree taper to the wall face at x -36.7), |y| 13.6..18.6, z -40..28.5 with a 45-degree underside from (|y| 15.3, z -40) to (18.6, -36.7), dia 1.6 pilots 4.8 deep at (+-16.1, 26.0) and (+-16.1, -36.5) (M2 x 6 through the 2 mm cover ends 0.8 before the pilot bottom)', 'purpose': 'four M2x6 tapping screws hold the rear cover; blocks are flush with the cover width so the cover closes flush; nothing wider than the bay sits below z -40; the sloped underside prints without support'},
  {'id': 'imu_fins', 'what': 'two fins x -19..-15, y -3.5..-2.45 and -0.5..0.5, z 4.3..31.5', 'purpose': 'edge slot for the BNO085 PCB rear edge (3 mm engagement, 0.19 clearance per side, 1 mm board-to-plate)'},
  {'id': 'imu_shelf', 'what': 'shelf x -19..-14.3, y +-4.6, z 4.3..5.5 with a 45-degree root gusset down to z 2.2 and two tie slots |y| 2.6..3.9 at x -17.3..-14.8', 'purpose': 'board bottom edge seat; one zip tie through the slots, under the shelf and over the board top at x about -16 holds the board in the slot'},
 ],
 'cover': [
  {'id': 'cover_plate', 'what': '2 mm plate x -47..-45, |y|<=18.6 for z -36.7..29.5, 45-degree lower-outer corners down to |y|<=15.3 at z -40, |y|<=15.3 for z -44..-40, top corners r1.5, back vertical edges r1', 'purpose': 'closes the DFR channel and the bay from behind; outline follows the body (posts above z -40 with their sloped undersides, bay width below)'},
  {'id': 'cover_lip', 'what': 'inward lip x -45..-37.5, |y|<=13.2, z 27.3..28.5', 'purpose': 'holds the DFR1202 down (0.3 above the board top)'},
  {'id': 'cover_holes', 'what': 'four dia 2.2 clearance holes at (+-16.1, 26.0) and (+-16.1, -36.5)', 'purpose': 'M2x6 tapping screws into the body posts (dia 4 pan heads seat on the flat back face)'},
 ],
 'retired_by_this_part': P.RETIRED,
}

if __name__ == '__main__':
    body = build_body(); cover = build_cover()
    bm = P.clean_mesh(body); cm = P.clean_mesh(cover)
    bm.export(P.OUT / 'rear_pack-world.stl'); cm.export(P.OUT / 'rear_pack_cover-world.stl')
    info = {}
    for name, man, mesh in (('body', body, bm), ('cover', cover, cm)):
        info[name] = dict(status=str(man.status()), genus=int(man.genus()), volume_mm3=round(float(man.volume()), 2),
                          area_mm2=round(float(man.surface_area()), 2), tris=int(len(mesh.faces)), watertight=bool(mesh.is_watertight),
                          winding_consistent=bool(mesh.is_winding_consistent), bodies=int(len(mesh.split(only_watertight=False))),
                          bounds=np.round(mesh.bounds, 3).tolist())
    info['chamfer_lower_front'] = {'cx': CH_CX, 'cz': CH_CZ}
    info['params'] = dict(PL=PL, TOP_EDGE=TOP_EDGE, WALL=WALL, RIB=RIB, BOT=BOT, USB_OPEN=USB_OPEN, TETHER_OPEN=TETHER_OPEN, WINDOW=WINDOW,
                          PAD=PAD, LIP=LIP, FOOT=FOOT, FOOT_X=FOOT_X, POST=POST, IMU=IMU, WEB_CUT=WEB_CUT, TAB_LOW=TAB_LOW, TAB_UP=TAB_UP, COVER=COVER,
                          openrb_holes_yz=P.openrb_holes_world())
    P.jdump(info, P.OUT / 'build.json')
    P.jdump(FEATURES, P.OUT / 'features.json')
    print(json.dumps({k: v for k, v in info.items() if k in ('body', 'cover')}, indent=1))
