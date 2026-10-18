"""Feasibility of the converter-plate contract (2026-10-14 brief) against the measured boards, the pack, the shells and the legs.
The contract envelope is modelled as specified: cover plate (build_rear_pack.build_cover, i.e. the byte-identical V1.8/V1.9
cover with its lip) plus the box x -67..-47, |y| <= 32.05, z -36..43, side/top/bottom walls 1.2, back wall 2, open front.
Boards placed by place_components.py. Writes contract_feasibility.json."""
import sys, json, time
from pathlib import Path
import numpy as np, trimesh
import manifold3d as m3
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'rear-pack'))
import pack_lib as P
import build_rear_pack as BRP
import ia_lib
t0 = time.time()

BOX = dict(x0=-67.0, x1=-47.0, hw=32.05, z0=-36.0, z1=43.0, t_side=1.2, t_back=2.0)
b = BOX
walls = {
    'back_wall': P.box((b['x0'], -b['hw'], b['z0']), (b['x0'] + b['t_back'], b['hw'], b['z1'])),
    'side_wall_minus_y': P.box((b['x0'], -b['hw'], b['z0']), (b['x1'], -b['hw'] + b['t_side'], b['z1'])),
    'side_wall_plus_y': P.box((b['x0'], b['hw'] - b['t_side'], b['z0']), (b['x1'], b['hw'], b['z1'])),
    'top_wall': P.box((b['x0'], -b['hw'], b['z1'] - b['t_side']), (b['x1'], b['hw'], b['z1'])),
    'bottom_wall': P.box((b['x0'], -b['hw'], b['z0']), (b['x1'], b['hw'], b['z0'] + b['t_side'])),
}
cover = BRP.build_cover()
walls['cover_plate_and_lip'] = cover
ENV = P.union(list(walls.values()))


def hull_solid(mesh):
    parts = []
    for p in mesh.split(only_watertight=False):
        if len(p.vertices) >= 4 and np.ptp(p.vertices, axis=0).min() > 1e-3:
            parts.append(m3.Manifold.hull_points(np.asarray(p.vertices, float)))
    return P.union(parts)


xl = {nm: trimesh.load(str(HERE / f'xl4015_{nm}-world.stl'), force='mesh') for nm in ('lower', 'upper')}
XL = {nm: hull_solid(m) for nm, m in xl.items()}
pdm = trimesh.load(str(HERE / 'pd5991-world.stl'), force='mesh'); PD = hull_solid(pdm)
facts = json.loads((HERE / 'board_facts.json').read_text())
res = {'envelope': BOX, 'boardModel': 'convex hull of each connected body of the ROBOTIS mesh (429 bodies), unioned; 5991 = box model from the Adafruit board file'}

# ---- 1 boards against every wall of the envelope (overlap > 0 = collision; target gap >= 0.5)
r1 = {}
for nm, S in list(XL.items()) + [('pd5991', PD)]:
    r1[nm] = {w: dict(overlapMm3=round(float((S ^ W).volume()), 3), gapMm=round(float(S.min_gap(W, 3.0)), 3)) for w, W in walls.items()}
r1['lower_vs_upper'] = dict(overlapMm3=round(float((XL['lower'] ^ XL['upper']).volume()), 3), gapMm=round(float(XL['lower'].min_gap(XL['upper'], 5.0)), 3))
r1['pd5991_vs_lower'] = dict(overlapMm3=round(float((PD ^ XL['lower']).volume()), 3), gapMm=round(float(PD.min_gap(XL['lower'], 5.0)), 3),
                             overlapBounds=np.round(P.from_m(PD ^ XL['lower']).bounds, 2).tolist() if (PD ^ XL['lower']).volume() > 1e-6 else None)
r1['depthBudget'] = dict(innerDepthX=round(BOX['x1'] - (BOX['x0'] + BOX['t_back']), 3), boardStack=facts['xl4015']['stackTotal'],
                         needWith0p5EachSide=round(facts['xl4015']['stackTotal'] + 1.0, 3),
                         atContractMidPlane=dict(componentTopX=round(-51.75 - facts['xl4015']['stackFromMidPlane']['componentSide'], 3),
                                                 pinTipX=round(-51.75 + facts['xl4015']['stackFromMidPlane']['pinSide'], 3)))
r1['widthBudget'] = dict(innerWidthY=round(2 * (BOX['hw'] - BOX['t_side']), 3), pcbLength=61.7, needWith0p5EachSide=62.7)
r1['zBudget'] = dict(innerZ=[BOX['z0'] + BOX['t_side'], BOX['z1'] - BOX['t_side']], lowerBoardZ=facts['xl4015']['lower']['worldBounds'][0][2],
                     roomBelowLowerBoardZ=round(facts['xl4015']['lower']['worldBounds'][0][2] - (BOX['z0'] + BOX['t_side']), 3),
                     pd5991HeightAlongZ=round(float(pdm.bounds[1][2] - pdm.bounds[0][2]), 3),
                     note='USB-C (v = 27.8) and terminal (v = 0) sit on opposite short edges (Adafruit board file), so USB-C down / terminal up stands the 27.8 mm edge vertical')
res['1_boardsInEnvelope'] = r1
print('1', json.dumps(r1), flush=True)

# ---- 2 terminal wire entry room (entries face the board ends)
ent = 30.76
res['2_terminalWireRoom'] = dict(entryFaceAbsY=ent, sideWallInnerAbsY=BOX['hw'] - BOX['t_side'], roomMm=round(BOX['hw'] - BOX['t_side'] - ent, 3),
                                 neededMmEstimate=5.0, neededNote='22 AWG solid, insulation OD about 1.6: 1.6 straight past the entry plus a bend radius of 2 x OD (estimate)',
                                 entriesWorld={nm: [[-51.75 - (2.5 - facts['xl4015']['pcbMidLocalX']), s * 30.15, zc + dz] for s in (1, -1) for dz in (2.5, -2.5)]
                                               for nm, zc in (('lower', 0.5), ('upper', 27.9))})

# ---- 3 cover-screw driver lanes (dia 5 shaft from the head top x -48.3 back to -108) and dia 4 x 1.3 heads
r3 = {}
obst = dict(walls); obst.update({'xl4015_lower': XL['lower'], 'xl4015_upper': XL['upper'], 'pd5991': PD})
for (y, z) in BRP.POST['holes']:
    lane = P.cyl_x(2.5, -108.0, -48.3, y, z); head = P.cyl_x(2.0, -48.3, -47.0, y, z)
    row = {}
    for k, O in obst.items():
        if k == 'cover_plate_and_lip':
            continue
        v = float((lane ^ O).volume()); hv = float((head ^ O).volume())
        if v > 1e-6 or hv > 1e-6:
            row[k] = dict(laneOverlapMm3=round(v, 3), headOverlapMm3=round(hv, 3))
    r3[f'cover_screw_y{y}_z{z}'] = dict(blockedBy=row, passes=len(row) == 0)
res['3_coverScrewDriverDia5'] = r3
print('3', json.dumps(r3), flush=True)

# ---- 4 board screws: lanes from the component side (heads on the component face, bosses on the pin side) and from the pin side
r4 = {}
for nm in ('lower', 'upper'):
    own = XL[nm]; V = xl[nm].vertices
    for (_, y, z) in facts['xl4015'][nm]['holesWorld']:
        comp = P.cyl_x(2.5, -108.0, -52.6, y, z)
        pin = P.cyl_x(2.5, -50.9, 40.0, y, z)
        sel = V[V[:, 0] < -52.6]; rr = np.hypot(sel[:, 1] - y, sel[:, 2] - z)
        row = dict(componentSideOwnBoardRadiusLimit=round(float(rr.min()), 3))
        for side, L in (('componentSide', comp), ('pinSide', pin)):
            hits = {}
            for k, O in list(walls.items()) + [('xl4015_' + o, XL[o]) for o in ('lower', 'upper') if o != nm] + [('pd5991', PD)]:
                v = float((L ^ O).volume())
                if v > 1e-6:
                    hits[k] = round(v, 3)
            row[side + 'Blocks'] = hits
        r4[f'{nm}_y{y}_z{z}'] = row
res['4_boardScrewDriverDia5'] = r4
# pin-side lanes also reach the shells and pack in front of the plate
shells = {k: P.solid_m(k) for k in ('shell_left', 'shell_right')}
for key, row in r4.items():
    nm, ys, zs = key.split('_'); y = float(ys[1:]); z = float(zs[1:])
    pin = P.cyl_x(2.5, -50.9, 40.0, y, z)
    for k, S in shells.items():
        v = float((pin ^ S).volume())
        if v > 1e-6:
            row['pinSideBlocks'][k] = round(v, 3)
print('4', json.dumps(r4), flush=True)

# ---- 5 board entry into a one-piece part: share of each board's y-z silhouette behind closed plate material
from shapely.geometry import Polygon, box as sbox
from shapely.ops import unary_union
cov = P.from_m(cover)
sec = cov.section(plane_origin=[-46.0, 0, 0], plane_normal=[1, 0, 0])
plate_yz = unary_union([Polygon(p[:, [1, 2]]) for p in sec.discrete]).buffer(0) if sec is not None else None
r5 = {}
for nm in ('lower', 'upper'):
    bb = facts['xl4015'][nm]['worldBounds']; sil = sbox(bb[0][1], bb[0][2], bb[1][1], bb[1][2])
    r5[nm] = dict(silhouetteAreaMm2=round(sil.area, 1), behindPlateMm2=round(sil.intersection(plate_yz).area, 1),
                  boardLongerThanPlateOpeningSides=True)
r5['note'] = 'with the plate and the box in one print, a 61.7 mm board must pass either the plate plane (closed for |y| <= 18.6, z -44..29.5) or the back wall; the free strips beside the plate are 12.25 mm wide'
r5['bossesOutsidePlate'] = [h for nm in ('lower', 'upper') for h in facts['xl4015'][nm]['holesWorld']]
r5['bossNote'] = 'all eight hole axes sit at |y| 28.25, outside the cover outline (|y| <= 18.6): a boss "from the plate face" has no plate to stand on there'
res['5_boardEntryOnePiece'] = r5

# ---- 6 envelope (box + cover) against the packs, shells and legs at rest
r6 = {}
man = ia_lib.manifest()
legs_near = ['lower', 'right_lower', 'ring2', 'ring7']
envb = P.from_m(ENV).bounds
for k in ['shell_left', 'shell_right'] + legs_near:
    S = P.solid_m(k)
    r6[k] = dict(overlapMm3=round(float((ENV ^ S).volume()), 3), gapMm=round(float(ENV.min_gap(S, 10.0)), 3))
box_only = P.union([w for k, w in walls.items() if k != 'cover_plate_and_lip'])
for f in ('rear_pack-v18.stl', 'rear_pack.stl'):
    S = P.mesh_to_m(P.load_stl(P.WORLD / f))
    r6[f] = dict(boxOverlapMm3=round(float((box_only ^ S).volume()), 3), boxGapMm=round(float(box_only.min_gap(S, 10.0)), 3),
                 coverOverlapMm3=round(float((cover ^ S).volume()), 3), coverGapMm=round(float(cover.min_gap(S, 10.0)), 3))
orb = P.mesh_to_m(P.openrb_mesh())
r6['openrb_board'] = dict(overlapMm3=round(float((ENV ^ orb).volume()), 3), gapMm=round(float(ENV.min_gap(orb, 10.0)), 3))
for k in ('motor10', 'motor5'):
    if k in man:
        S = P.solid_m(k); r6[k] = dict(overlapMm3=round(float((ENV ^ S).volume()), 3), gapMm=round(float(ENV.min_gap(S, 10.0)), 3))
res['6_envelopeFitAtRest'] = r6
print('6', json.dumps(r6), flush=True)

res['blockers'] = []
B = res['blockers']
if r1['lower']['back_wall']['overlapMm3'] > 0 or r1['upper']['back_wall']['overlapMm3'] > 0:
    B.append('XL4015 stack is 17.86 mm (13.58 components + 1.55 PCB + 2.74 pins); at mid-plane x -51.75 the inductor reaches x %.2f, %.2f mm into the 2 mm back wall; the 18.0 mm inner depth leaves 0.07 mm per side at best (target 0.5)' % (r1['depthBudget']['atContractMidPlane']['componentTopX'], -65.0 - r1['depthBudget']['atContractMidPlane']['componentTopX']))
B.append('PCB 61.7 long in a 61.7 inner width: board-to-side-wall gap %.3f / %.3f mm (target 0.5)' % (r1['lower']['side_wall_minus_y']['gapMm'], r1['lower']['side_wall_plus_y']['gapMm']))
B.append('terminal wire entries face the board ends (+-Y): %.2f mm between entry face and side wall, about 5 mm needed' % res['2_terminalWireRoom']['roomMm'])
B.append('5991 stands %.1f mm tall with USB-C down and terminal up (opposite short edges per the Adafruit board file); %.1f mm of z below the lower board: overlap %.1f mm3' % (r1['zBudget']['pd5991HeightAlongZ'], r1['zBudget']['roomBelowLowerBoardZ'], r1['pd5991_vs_lower']['overlapMm3']))
B.append('cover screws: ' + '; '.join(f"{k}: {sorted(v['blockedBy'])}" for k, v in r3.items()))
B.append('one-piece print: boards cannot enter (plate closes |y| <= 18.6, back wall closes the rear) and the eight bosses at |y| 28.25 lie outside the plate')
res['elapsed_s'] = round(time.time() - t0, 1)
P.jdump(res, HERE / 'contract_feasibility.json')
print('BLOCKERS'); [print(' -', x) for x in B]
print('elapsed', res['elapsed_s'])
