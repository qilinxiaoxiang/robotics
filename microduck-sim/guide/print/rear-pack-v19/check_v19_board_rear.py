"""OpenRB-150 in and out from behind with both side shells on and only the pack cover off (Shawn, 2026-10-13).

Exact manifold3d booleans on the guide audit solid cache (same cache and 0.5 mm step as ../rear-pack/check_assembly.py).
Scene: the V1.9 pack body from this folder, the printed V1.8 side shells, every other non-retired guide part at its final
pose (motors, base, legs, neck), the BNO085 on its rib, and the cable tubes of the guide (guide-data.json, polyline with the
drawn radius). The cover is off. Writes check_v19_board_rear.json.

1. board_rear_path: the board moves along +x from 40 mm behind its seat (front face at x -62.4, behind the shells' rear edge
   x -46.4 and the pack's rear edge x -45) to the seat. Removal is the same path reversed. Cables that end on the board
   (links R and L in the centre ports, link N in the +Y side port, the supply pair and the Pi lead under J4, the UART pair
   soldered into J12) are unplugged or loosened before removal and dressed after insertion; they are reported separately.
2. screw_drivers: a straight shaft along +x to each of the four M2 x 6 heads (head top x -28.4); largest diameter that
   clears the board's own components, the pack, the shells and every other part.
3. access: with the shells on and the cover off, from behind: the J4 screwdriver, the J4 wire entry from above, the JP1 cap,
   the J12 pads, the two centre-port plugs (+x), and the +Y side-port plug through the wall window (-y).
"""
import json, sys, time
from pathlib import Path
import numpy as np
import manifold3d as m3

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'rear-pack'))
import pack_lib as P  # noqa: E402
import ia_lib  # noqa: E402

t0 = time.time()
GUIDE = HERE.parents[1]
bm = P.load_stl(HERE / 'rear_pack-world.stl'); BODY = P.mesh_to_m(bm)
orb = P.openrb_mesh(); ORB = P.mesh_to_m(orb)
imu = P.imu_mesh(); IMU = P.mesh_to_m(imu)
man = ia_lib.manifest()
SHELLS = ('shell_left', 'shell_right')
ON_BOARD = {'uart', 'supply', 'pi-trunk', 'dxl-r5', 'dxl-l10', 'dxl-n12'}

solids = [('rear_pack', BODY, bm.bounds), ('imu_board', IMU, imu.bounds)]
for k, rec in man.items():
    if k in P.RETIRED or k in P.SELF_KEYS:
        continue
    solids.append((k, P.solid_m(k), np.array(rec['bounds'])))


def tube(path, r):
    pts = [np.asarray(p, float) for p in path]
    segs = []
    for a, b in zip(pts[:-1], pts[1:]):
        sa = m3.Manifold.sphere(r, 16).translate(a.tolist()); sb = m3.Manifold.sphere(r, 16).translate(b.tolist())
        segs.append(m3.Manifold.batch_hull([sa, sb]))
    return P.union(segs), (np.min(pts, 0) - r, np.max(pts, 0) + r)


gd = json.loads((GUIDE / 'data/guide-data.json').read_text())
cables = []
for c in gd['cables']:
    tm, tb = tube(c['path'], float(c.get('radius') or 0.9))
    cables.append((c['id'], tm, tb))


def near(b1, b2, pad):
    return bool(np.all(np.asarray(b1[0]) - pad <= np.asarray(b2[1])) and np.all(np.asarray(b1[1]) + pad >= np.asarray(b2[0])))


def sweep(mover, mbounds, offsets, obstacles, gap_search=5.0):
    rows = []
    per = {}
    for off in offsets:
        off = np.asarray(off, float)
        mv = mover.translate(off.tolist()); mb = (mbounds[0] + off, mbounds[1] + off)
        hits = {}
        for k, om, ob in obstacles:
            if not near(mb, ob, gap_search):
                continue
            v = float((mv ^ om).volume())
            g = float(mv.min_gap(om, gap_search))
            if v > 1e-6:
                hits[k] = round(v, 4)
            p = per.setdefault(k, dict(minGapMm=gap_search, atOffset=None, maxOverlapMm3=0.0))
            if g < p['minGapMm']:
                p.update(minGapMm=round(g, 4), atOffset=off.round(2).tolist())
            p['maxOverlapMm3'] = max(p['maxOverlapMm3'], round(v, 4))
        rows.append(dict(offset=off.round(2).tolist(), overlaps=hits))
    return rows, per


res = {'scene': 'V1.9 pack body (this folder), shells on, cover off, all non-retired guide parts at final pose, BNO085 on its rib, guide cable tubes',
       'packBodySha256': __import__('hashlib').sha256((HERE / 'rear_pack-world.stl').read_bytes()).hexdigest()}

# ---------------------------------------------------------------- 1. board path from behind
offs = [(-40.0 + 0.5 * i, 0.0, 0.0) for i in range(81)]
rows, per = sweep(ORB, orb.bounds, offs, solids)
coll = [r for r in rows if r['overlaps']]
fixed = {k: v for k, v in per.items()}
# the board seats on the four pads (designed contact at offset 0): the path clearance is taken before the seat
rows_pre, per_pre = sweep(ORB, orb.bounds, [o for o in offs if o[0] <= -0.5], [s for s in solids if s[0] == 'rear_pack'])
# side clearance along the path: the pack without the four pads (the pads are the end stop straight ahead)
pads = P.union([P.cyl_x(2.6, -24.81, -20.5, y, z) for (y, z) in P.openrb_holes_world()])
rows_side, per_side = sweep(ORB, orb.bounds, offs, [('rear_pack_without_pads', BODY - pads, bm.bounds)])
cab_free = [c for c in cables if c[0] not in ON_BOARD]
cab_on = [c for c in cables if c[0] in ON_BOARD]
crows, cper = sweep(ORB, orb.bounds, offs, cab_free)
orows, oper = sweep(ORB, orb.bounds, offs, cab_on, gap_search=1.0)
on_board_cross = {}
for r in orows:
    for k, v in r['overlaps'].items():
        d = on_board_cross.setdefault(k, dict(firstOffset=r['offset'][0], lastOffset=r['offset'][0], maxOverlapMm3=0.0))
        d['lastOffset'] = r['offset'][0]; d['maxOverlapMm3'] = max(d['maxOverlapMm3'], v)
res['board_rear_path'] = dict(
    path='straight +x, 40 mm to 0 in 0.5 mm steps (81 poses); removal = reverse',
    collisionSteps=len(coll), collisions=coll[:10],
    perObstacle=dict(sorted(per.items(), key=lambda kv: kv[1]['minGapMm'])[:12]),
    packBodyBeforeSeat=per_pre.get('rear_pack'),
    packSideClearance=dict(per_side.get('rear_pack_without_pads', {}), note='walls, floor, posts, plate: everything but the pads the board seats on'),
    shells={k: per.get(k) for k in SHELLS},
    cablesNotOnBoard=dict(collisionSteps=sum(1 for r in crows if r['overlaps']), nearest=dict(sorted(cper.items(), key=lambda kv: kv[1]['minGapMm'])[:5])),
    cablesEndingOnBoard=dict(note='these end on the board: unplug (R, L, N), loosen J4 (supply, Pi lead) and lead them out of the rear opening before the board comes out; the UART pair is soldered to J12 and travels with the board',
                             crossingTheSweep=on_board_cross),
    passRigid=len(coll) == 0, passCablesNotOnBoard=all(not r['overlaps'] for r in crows))
print('board path', res['board_rear_path']['collisionSteps'], res['board_rear_path']['packBodyBeforeSeat'], res['board_rear_path']['shells'], flush=True)

# ---------------------------------------------------------------- 2. screw drivers along +x, shells on
drv = {}
others = [s for s in solids]
for (y, z) in P.openrb_holes_world():
    row = {}
    best = None
    for dia in (6.0, 5.5, 5.0, 4.5, 4.0, 3.5, 3.0):
        cyl = P.cyl_x(dia / 2, -100.0, -28.4, y, z, seg=64)
        cb = (np.array([-100.0, y - dia, z - dia]), np.array([-28.4, y + dia, z + dia]))
        hits = {}
        v = float((cyl ^ ORB).volume())
        if v > 1e-6:
            hits['openrb_board (own components)'] = round(v, 4)
        for k, om, ob in others:
            if near(cb, ob, 0.5):
                vv = float((cyl ^ om).volume())
                if vv > 1e-6:
                    hits[k] = round(vv, 4)
        row[f'dia{dia:g}'] = hits
        if not hits and best is None:
            best = dia
    cyl = P.cyl_x(best / 2, -100.0, -28.4, y, z, seg=64) if best else None
    gaps = {}
    if cyl is not None:
        gaps['openrb_board'] = round(float(cyl.min_gap(ORB, 3.0)), 4)
        for k in ('rear_pack',) + SHELLS:
            om = dict((s[0], s[1]) for s in solids)[k]
            gaps[k] = round(float(cyl.min_gap(om, 3.0)), 4)
    drv[f'y{y}_z{z}'] = dict(headTopX=-28.4, largestClearShaftDiaMm=best, gapsAtThatDia=gaps, overlapsByDia=row,
                             reachFromRobotRearMm=round(-28.4 - (-46.4), 1))
    print('driver', y, z, best, gaps, flush=True)
res['screw_drivers'] = drv

# ---------------------------------------------------------------- 3. access with shells on, cover off
acc = {}


def clear_box(name, lo, hi, note):
    b = P.box(lo, hi); bb = (np.array(lo), np.array(hi))
    hits = {}; gaps = {}
    for k, om, ob in solids + cables:
        if near(bb, ob, 1.0):
            v = float((b ^ om).volume())
            if v > 1e-6:
                hits[k] = round(v, 4)
            g = float(b.min_gap(om, 1.0))
            if g < 1.0:
                gaps[k] = round(g, 3)
    acc[name] = dict(box=[list(lo), list(hi)], note=note, overlaps=hits, gapsUnder1mm=gaps, pass_=not any(k in hits for k in ('rear_pack',) + SHELLS))
    print('access', name, hits, flush=True)


for yy in (-2.0, 1.5):
    cyl = P.cyl_x(1.5, -100.0, -34.73, yy, 20.38, seg=48)
    hits = {}
    for k, om, ob in solids + cables:
        v = float((cyl ^ om).volume())
        if v > 1e-6:
            hits[k] = round(v, 4)
    acc[f'j4_screw_y{yy}'] = dict(tool='flat screwdriver, dia 3 shaft along +x to the screw at x -34.73, z 20.38', overlaps=hits,
                                  pass_=not hits)
    print('access j4 screw', yy, hits, flush=True)
clear_box('j4_wire_entry_from_above', (-34.7, -4.7, 24.9), (-22.4, 4.8, 32.9), 'room above J4 where the supply pair and Pi lead go under the screws (cables in it are the ones that go there)')
clear_box('j4_hand_room_behind', (-70.0, -4.7, 24.9), (-34.7, 4.8, 31.3), 'fingers bringing the wires to J4 from behind, up to the shells\' rear roof (lowest shell point over the bay behind the board: z 31.39 left, 31.66 right)')
free = {}
for k in SHELLS:
    I = dict((s_[0], s_[1]) for s_ in solids)[k] ^ P.box((-34.7, -4.7, 24.9), (-22.4, 4.8, 60.0))
    free[k] = None if I.is_empty() else round(float(I.bounding_box()[2]), 2)
acc['j4_free_height_above'] = dict(j4TopZ=24.89, shellUndersideZ=free, freeMm=round(min(v for v in free.values() if v) - 24.89, 2))
clear_box('jp1_cap_and_j12_room', (-70.0, -7.8, 8.9), (-35.0, 1.0, 12.7), 'JP1 header pins (x -34.99, y -5.95/-3.41/-0.87, z 10.79) with the cap pulled along -x; the J12 pads and the UART pair start beside it (uart route start y -2, z 11)')
for nm, room in (('centre_ports_plugs', P.ROOM_LEG_PLUGS),):
    rows, per = sweep(P.box(*room), room, [(-25.0 + 0.5 * i, 0.0, 0.0) for i in range(51)], solids)
    acc[nm] = dict(path='plug room x -42.45..-32.45, y -4.3..3.6, z -27.75..-17.75 along +x from 25 mm behind',
                   collisionSteps=sum(1 for r in rows if r['overlaps']), firstCollisions=[r for r in rows if r['overlaps']][:3],
                   nearest=dict(sorted(per.items(), key=lambda kv: kv[1]['minGapMm'])[:4]))
    print('access', nm, acc[nm]['collisionSteps'], flush=True)
room = P.ROOM_NECK_PLUG
rows, per = sweep(P.box(*room), room, [(0.0, 25.0 - 0.5 * i, 0.0) for i in range(51)], solids)
acc['side_port_plug_plus_y'] = dict(path='plug room x -30.65..-26.45, y 12.4..22.4, z -27.75..-17.75 along -y from 25 mm out, through the +Y wall window',
                                    collisionSteps=sum(1 for r in rows if r['overlaps']), firstCollisions=[r for r in rows if r['overlaps']][:3],
                                    nearest=dict(sorted(per.items(), key=lambda kv: kv[1]['minGapMm'])[:4]))
print('access side port', acc['side_port_plug_plus_y']['collisionSteps'], flush=True)
res['access_shells_on_cover_off'] = acc
res['elapsed_s'] = round(time.time() - t0, 1)
P.jdump(res, HERE / 'check_v19_board_rear.json')
print('DONE', res['elapsed_s'])
