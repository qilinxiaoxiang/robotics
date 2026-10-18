"""Checks 1-4: manifold/volumes, hip-yaw screw interface fidelity vs the current power_support, board/room clearance, guide-part clearance.
Writes check_fit.json."""
import json, time
import numpy as np, trimesh
import manifold3d as m3
import pack_lib as P
import pso_lib as L

t0 = time.time()
OUT = P.OUT
bm = P.load_stl(OUT / 'rear_pack-world.stl')
cm = P.load_stl(OUT / 'rear_pack_cover-world.stl')
B = P.mesh_to_m(bm); C = P.mesh_to_m(cm)
res = {'stlBody': str(OUT / 'rear_pack-world.stl'), 'stlCover': str(OUT / 'rear_pack_cover-world.stl')}

# ---------------------------------------------------------------- 1 manifold
res['manifold'] = {}
for name, mesh, man in (('body', bm, B), ('cover', cm, C)):
    res['manifold'][name] = dict(watertight=bool(mesh.is_watertight), windingConsistent=bool(mesh.is_winding_consistent),
                                 manifoldStatus=str(man.status()), bodies=int(len(mesh.split(only_watertight=False))), genus=int(man.genus()),
                                 volumeMm3=round(float(man.volume()), 2), areaMm2=round(float(man.surface_area()), 2), tris=int(len(mesh.faces)),
                                 bounds=np.round(mesh.bounds, 3).tolist(), euler=int(mesh.euler_number))
res['manifold']['coverBodyOverlapMm3'] = round(float((B ^ C).volume()), 4)
res['manifold']['coverBodyGapMm'] = round(float(B.min_gap(C, 5.0)), 4)
print('manifold', json.dumps(res['manifold']), flush=True)

# ---------------------------------------------------------------- 2 interface fidelity (four hip-yaw case screws)
PS = P.solid_m('power_support'); ps_mesh = P.solid_mesh('power_support')
SCREWS = [dict(id='S10-case-069', yc=9.5, z_seat=-3.094, axis=+1, zr=(-6.0, 1.0), head=(-4.6, -3.094), lug=(-6.0, -0.5), fid=(-19.0, -13.5)),
          dict(id='S05-case-074', yc=-9.5, z_seat=-3.094, axis=+1, zr=(-6.0, 1.0), head=(-4.6, -3.094), lug=(-6.0, -0.5), fid=(-19.0, -13.5)),
          dict(id='S10-case-072', yc=9.5, z_seat=25.049, axis=-1, zr=(21.0, 28.0), head=(25.049, 26.55), lug=(22.5, 27.5), fid=(-19.0, -13.5)),
          dict(id='S05-case-076', yc=-9.5, z_seat=25.049, axis=-1, zr=(21.0, 28.0), head=(25.049, 26.55), lug=(22.5, 27.5), fid=(-19.0, -13.5))]


def probe_z(mesh, x, y, z_from, z_to):
    """First surface hit of a ray from (x,y,z_from) toward z_to; returns z or None."""
    d = np.sign(z_to - z_from)
    loc, _, _ = mesh.ray.intersects_location(np.array([[x, y, z_from]]), np.array([[0, 0, d]]), multiple_hits=True)
    if len(loc) == 0:
        return None
    zs = loc[:, 2]; zs = zs[(zs - z_from) * d >= 0]
    if len(zs) == 0:
        return None
    return float(zs[np.argmin(np.abs(zs - z_from))])


def hole_dia(mesh, x, y, z):
    ds = []
    for a in np.linspace(0, 2 * np.pi, 16, endpoint=False):
        dirv = np.array([[np.cos(a), np.sin(a), 0.0]])
        loc, _, _ = mesh.ray.intersects_location(np.array([[x, y, z]]), dirv, multiple_hits=True)
        if len(loc):
            ds.append(float(np.min(np.linalg.norm(loc - np.array([x, y, z]), axis=1))))
    return (round(2 * min(ds), 3), round(2 * max(ds), 3)) if ds else None


fid = []
for s in SCREWS:
    xc = -16.5; yc = s['yc']; sgn = np.sign(yc)
    bx_full = P.box((s['fid'][0], min(sgn * 4.5, sgn * 14.5), s['lug'][0]), (s['fid'][1], max(sgn * 4.5, sgn * 14.5), s['lug'][1]))
    bx_lug = P.box((s['fid'][0], min(sgn * 6.6, sgn * 14.5), s['lug'][0]), (s['fid'][1], max(sgn * 6.6, sgn * 14.5), s['lug'][1]))
    out = dict(id=s['id'], centerXY=[xc, yc], seatZ=s['z_seat'])
    for nm, bx in (('fidelityBox_y4.5_14.5', bx_full), ('fidelityBox_y6.6_14.5', bx_lug)):
        a = B ^ bx; b = PS ^ bx
        out[nm] = dict(box=np.round(P.from_m(bx).bounds, 2).tolist(), bodyVolMm3=round(float(a.volume()), 3), psVolMm3=round(float(b.volume()), 3),
                       xorVolMm3=round(float(((a - b) + (b - a)).volume()), 4))
    # seat faces (ray probes around the hole at r 1.7)
    zmid = -2.2 if s['axis'] > 0 else 24.2      # mid-height of the lug
    seats = {}
    for mesh, nm in ((bm, 'body'), (ps_mesh, 'ps')):
        tops = []; bots = []
        for a in np.linspace(0, 2 * np.pi, 8, endpoint=False):
            px, py = xc + 1.7 * np.cos(a), yc + 1.7 * np.sin(a)
            tops.append(probe_z(mesh, px, py, s['lug'][1] + 2, s['lug'][0] - 2)); bots.append(probe_z(mesh, px, py, s['lug'][0] - 2, s['lug'][1] + 2))
        tops = [t for t in tops if t is not None]; bots = [b for b in bots if b is not None]
        seats[nm] = dict(topFaceZ=[round(min(tops), 3), round(max(tops), 3)] if tops else None, bottomFaceZ=[round(min(bots), 3), round(max(bots), 3)] if bots else None,
                         holeDiaMinMax=hole_dia(mesh, xc, yc, zmid))
    out['seatFaces'] = seats
    # screw shank and head pass
    shank = P.cyl_z(1.25, s['zr'][0], s['zr'][1], xc, yc); head = P.cyl_z(2.0, s['head'][0], s['head'][1], xc, yc)
    out['shankDia2.5_overlapMm3'] = dict(body=round(float((B ^ shank).volume()), 4), ps=round(float((PS ^ shank).volume()), 4))
    out['headDia4_overlapMm3'] = dict(body=round(float((B ^ head).volume()), 4), ps=round(float((PS ^ head).volume()), 4))
    fid.append(out)
res['interfaceFidelity'] = fid
# tab-region clearance to the parts the tabs touch, body vs power_support (same boxes)
TB =P.union([P.box((-21.0, -14.5, -6.0), (-13.5, 14.5, -0.5)), P.box((-21.0, -14.5, 22.5), (-13.5, 14.5, 27.5))])
res['tabNeighbourGaps'] = {}
for k in ('motor10', 'motor5', 'torso_base', 'ring10_torso', 'ring5_torso'):
    pm = P.solid_m(k)
    res['tabNeighbourGaps'][k] = dict(bodyTabs=round(float((B ^ TB).min_gap(pm, 6.0)), 4), psTabs=round(float((PS ^ TB).min_gap(pm, 6.0)), 4),
                                      bodyWhole=round(float(B.min_gap(pm, 6.0)), 4), bodyOverlapMm3=round(float((B ^ pm).volume()), 4))
print('fidelity', json.dumps(fid, indent=0)[:1500], flush=True)
print('tabNeighbourGaps', res['tabNeighbourGaps'], flush=True)

# ---------------------------------------------------------------- 3 boards and rooms
orb = P.mesh_to_m(P.openrb_mesh()); imu = P.mesh_to_m(P.imu_mesh())
items = {'openrb_model': orb, 'imu_model': imu, 'dfr_box': P.box(*P.DFR_BOX), 'dfr_pad_room': P.box(*P.DFR_PAD_ROOM),
         'room_leg_plugs': P.box(*P.ROOM_LEG_PLUGS), 'room_neck_plug': P.box(*P.ROOM_NECK_PLUG), 'room_terminal': P.box(*P.ROOM_TERMINAL),
         'room_usb': P.box(*P.ROOM_USB), 'room_imu_plug_top': P.box(*P.ROOM_IMU_PLUG_TOP), 'room_imu_socket_top': P.box(*P.ROOM_IMU_SOCKET_TOP),
         'openrb_body_box': P.box((-35.0, -13.0, -42.0), (-22.4, 12.4, 24.9))}
res['boardsAndRooms'] = {}
for nm, it in items.items():
    res['boardsAndRooms'][nm] = {}
    for pn, man in (('body', B), ('cover', C)):
        res['boardsAndRooms'][nm][pn] = dict(overlapMm3=round(float((man ^ it).volume()), 4), gapMm=round(float(man.min_gap(it, 10.0)), 4))
# IMU slot clearance without the shelf seat contact; OpenRB screw heads on the component side
shelf = P.box((-19.5, -4.7, 4.2), (-11.4, 4.7, 5.6))
res['boardsAndRooms']['imu_model_slotOnly'] = dict(gapMm=round(float((B - shelf).min_gap(imu, 10.0)), 4))
heads = P.union([P.cyl_x(2.0, -28.4, -26.4, y, z) for (y, z) in P.openrb_holes_world()])
res['boardsAndRooms']['openrb_screwHeads_dia4_x-28.4..-26.4'] = dict(overlapWithOpenrbModelMm3=round(float((heads ^ orb).volume()), 4),
                                                                   overlapWithBodyMm3=round(float((heads ^ B).volume()), 4))
# pad-to-PCB: pads end at x -21.0 .. -24.8; PCB back face from the model
print('boards/rooms', json.dumps(res['boardsAndRooms']), flush=True)

# ---------------------------------------------------------------- 4 every guide part except retired
legs = set()
for sd in L.SIDE.values():
    for b, ks in sd['parts'].items():
        legs.update(ks)
man = P.manifest = __import__('ia_lib').manifest()
rows = []
for k, rec in sorted(man.items()):
    if k in P.RETIRED or k in P.SELF_KEYS:
        continue
    lo, hi = np.array(rec['bounds'])
    near_b = np.all(lo - 8 <= bm.bounds[1]) and np.all(hi + 8 >= bm.bounds[0])
    near_c = np.all(lo - 8 <= cm.bounds[1]) and np.all(hi + 8 >= cm.bounds[0])
    if not (near_b or near_c):
        rows.append(dict(key=k, module=rec.get('module'), bodyGapMm='>8', coverGapMm='>8', leg=k in legs)); continue
    pm = P.solid_m(k)
    row = dict(key=k, module=rec.get('module'), leg=k in legs, closed=rec.get('closed'))
    row['bodyOverlapMm3'] = round(float((B ^ pm).volume()), 4) if near_b else 0.0
    row['bodyGapMm'] = round(float(B.min_gap(pm, 8.0)), 4) if near_b else '>8'
    row['coverOverlapMm3'] = round(float((C ^ pm).volume()), 4) if near_c else 0.0
    row['coverGapMm'] = round(float(C.min_gap(pm, 8.0)), 4) if near_c else '>8'
    rows.append(row)
    print(k, row, flush=True)
res['guideParts'] = rows
close = [r for r in rows if isinstance(r['bodyGapMm'], float) and r['bodyGapMm'] < 2.0 or isinstance(r['coverGapMm'], float) and r['coverGapMm'] < 2.0]
res['guidePartsUnder2mm'] = close
res['guidePartsOverlap'] = [r for r in rows if r.get('bodyOverlapMm3', 0) > 0 or r.get('coverOverlapMm3', 0) > 0]
res['elapsed_s'] = round(time.time() - t0, 1)
P.jdump(res, OUT / 'check_fit.json')
print('DONE', res['elapsed_s'], 'under2mm:', [(r['key'], r['bodyGapMm'], r['coverGapMm']) for r in close], 'overlaps:', [(r['key'], r['bodyOverlapMm3'], r['coverOverlapMm3']) for r in res['guidePartsOverlap']])
