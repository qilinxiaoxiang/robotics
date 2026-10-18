"""Pack-channel study for layout G (renders + numbers only, 2026-10-14).
Measures the as-built V1.8 pack (rear_pack-v18) interior, places the 5991 inside the pack channel in both orientations,
tests the USB-C plug exit (13 x 7.5 overmold, 25 long) against the pack, shells, legs and every manifest part, measures
the side-shell gap beside the pack, tests side-window wires running forward past the shell rear edge, and checks the
tether hole and the lower pack section. World = guide frame (mm). Writes pack_study.json and the G 5991/plug STLs."""
import sys, json
from pathlib import Path
import numpy as np, trimesh
HERE = Path(__file__).resolve().parent; DD = HERE.parent; PRINT = DD.parent.parent
sys.path.insert(0, str(PRINT / 'rear-pack')); sys.path.insert(0, str(DD))
import pack_lib as P, ia_lib
import shellkit as K
V18 = P.load_stl(P.WORLD / 'rear_pack-v18.stl'); ORB = P.openrb_mesh()
V18m, ORBm = P.mesh_to_m(V18), P.mesh_to_m(ORB)
man = ia_lib.manifest(); SKIP = set(P.RETIRED) | set(P.SELF_KEYS) | {'rear_pack_cover', 'rear_pack', 'rear_frame', 'rear_lid', 'xl4015_left', 'xl4015_right', 'pd5991'}
G = lambda a, b, s=30.0: round(float(a.min_gap(b, s)), 3)
out = {}

# ---------------------------------------------------------------- 1. pack interior
def free(p):
    p = np.atleast_2d(p); return ~(V18.contains(p) | ORB.contains(p))
orb_face = {}
for zb in ((-18.0, 4.0), (-3.0, 27.0)):
    v = ORB.vertices[(np.abs(ORB.vertices[:, 1]) < 15) & (ORB.vertices[:, 2] > zb[0]) & (ORB.vertices[:, 2] < zb[1])]
    orb_face[f'z {zb[0]}..{zb[1]}'] = round(float(v[:, 0].min()), 2) if len(v) else None
out['openrbRearFaceX'] = orb_face
rows = []
for z in np.arange(-42, 28.1, 2.0):
    r = dict(z=float(z))
    for x in (-44.5, -42.0, -39.0, -37.0):
        ys = np.arange(0, 22, 0.1); f = free(np.c_[np.full_like(ys, x), ys, np.full_like(ys, z)]); fm = free(np.c_[np.full_like(ys, x), -ys, np.full_like(ys, z)])
        r[f'x{x}'] = [round(float(-ys[np.argmin(fm)] if not fm.all() else -22), 1), round(float(ys[np.argmin(f)] if not f.all() else 22), 1)]
    xs = np.arange(-45, -30, 0.1); f = free(np.c_[xs, np.zeros_like(xs), np.full_like(xs, z)])
    r['freeXatY0'] = round(float(xs[np.argmin(f)] if not f.all() else -30), 1)
    rows.append(r)
out['channelFreeYbyZ'] = dict(note='free y interval [-y, +y] from y 0 outward at each x (pack v18 + OpenRB solid); freeXatY0 = first solid x going +x from x -45 at y 0', rows=rows)
# tether hole and floor
tz = np.arange(-47, -38, 0.25); tet = {}
for (x, y) in ((-42.0, 0.0), (-44.0, 2.5), (-40.0, -2.5), (-42.0, 5.0)):
    f = free(np.c_[np.full_like(tz, x), np.full_like(tz, y), tz]); tet[f'({x},{y})'] = 'open through the floor' if f.all() else 'solid at z ' + str(round(float(tz[np.argmin(f)]), 2))
out['tetherHoleProbe'] = tet
fl = []
for x in np.arange(-44.5, -35, 1.0):
    zz = np.arange(-46, -20, 0.25); f = free(np.c_[np.full_like(zz, x), np.zeros_like(zz), zz]); fl.append([float(x), round(float(zz[np.argmax(f)]), 2)])
out['floorTopZatY0'] = fl

print('STAGE', '---------------------- 2.', flush=True)
# ---------------------------------------------------------------- 2. 5991 in the pack, long axis along y
PCB = (20.32, 27.813, 1.6); PARTS = dict(usbc=((5.69, 21.606), (14.63, 28.956), 3.3), term=((6.76, 0.21), (13.76, 7.21), 8.5))
xb = orb_face['z -18.0..4.0'] - 0.5 - 1.5               # PCB back face: trimmed pins 1.5 long, 0.5 to the OpenRB
T = -17.75 + 0.5 + 20.32                                 # PCB top: bottom edge 0.5 above the leg-plug room (z -17.75)
def pw(u, v, w):                                         # u -> -z, v -> -y (USB-C edge to -y), w -> -x (components toward the box)
    return np.array([xb - w, PCB[1] / 2 - v, T - u])
def pbox(a, b, w0, w1):
    A, B = pw(a[0], a[1], w0), pw(b[0], b[1], w1); return np.minimum(A, B), np.maximum(A, B)
bx = {'pcb': pbox((0, 0), PCB[:2], 0, 1.6)}
for k, (a, b, h) in PARTS.items():
    bx[k] = pbox(a, b, 1.6, 1.6 + h)
front = float(min(lo[0] for lo, hi in bx.values()))
sock = bx['usbc']; sc = (sock[0] + sock[1]) / 2; sy = float(sock[0][1])
plug = P.box((sc[0] - 3.75, sy - 25.0, sc[2] - 6.5), (sc[0] + 3.75, sy, sc[2] + 6.5))
pd = P.union([P.box(lo, hi) for lo, hi in bx.values()])
trimesh.util.concatenate([trimesh.creation.box(extents=hi - lo, transform=trimesh.transformations.translation_matrix((lo + hi) / 2)) for lo, hi in bx.values()]).export(HERE / 'pd5991_G-world.stl')
P.from_m(plug).export(HERE / 'usbc_plug_G-world.stl')
prow = {}
for k, rec in man.items():
    if k in SKIP:
        continue
    lo, hi = np.array(rec['bounds'])
    if np.all(lo - 30 <= [sc[0] + 3.75, sy, sc[2] + 6.5]) and np.all(hi + 30 >= [sc[0] - 3.75, sy - 25, sc[2] - 6.5]):
        prow[k] = G(plug, P.solid_m(k))
prow['openrb-board-upright'] = G(plug, ORBm); prow['rear_pack-v18 (as built: side wall in the way)'] = G(plug, V18m)
pdrow = {'rear_pack-v18 (as built)': dict(gap=G(pd, V18m, 10), overlapMm3=round(float((pd ^ V18m).volume()), 2)), 'openrb': G(pd, ORBm, 10)}
lp = P.box(*P.ROOM_LEG_PLUGS); pdrow['legPlugRoom'] = G(pd, lp, 10)
# what of the as-built pack the 5991 needs removed (overlap bounding box)
ov = pd ^ V18m; ovb = P.from_m(ov).bounds.round(2).tolist() if ov.volume() > 1e-3 else None
plug_ov = plug ^ V18m; pob = P.from_m(plug_ov).bounds.round(2).tolist() if plug_ov.volume() > 1e-3 else None
out['pd5991InPack_longAxisY'] = dict(
    pcbBackX=round(xb, 2), componentFrontX=round(front, 2), pcbZ=[round(T - PCB[0], 2), round(T, 2)], pcbY=[-13.91, 13.91],
    channelDepthNeeded=round(orb_face['z -18.0..4.0'] - (front - 0.5), 2), frontPlateInnerFaceMovesTo=round(front - 0.5, 2),
    usbcPoints='-y (socket face y %.2f, centre x %.2f z %.2f)' % (sy, sc[0], sc[2]), terminalFaces='+y (entry face y 13.70, z %.2f..%.2f)' % (bx['term'][0][2], bx['term'][1][2]),
    plugBox=P.from_m(plug).bounds.round(2).tolist(), plugGapsHOME=dict(sorted(prow.items(), key=lambda kv: kv[1])),
    pd5991Gaps=pdrow, pd5991OverlapWithAsBuiltPackBounds=ovb, plugOverlapWithAsBuiltPackBounds=pob,
    note='pose: shells, hips and thighs are torso-fixed in HOME and STAND (STAND moves only the ankles and the neck/head), so these gaps hold at both poses')
print('STAGE', '---------------------- 3.', flush=True)
# ---------------------------------------------------------------- 3. long axis vertical
Tv = 3.07 + 7.5                                           # same channel, 27.8 along z: bottom 0.5 above the leg plugs -> top
zbot = -17.25; ztop = zbot + 27.813
up = P.box((sc[0] - 3.75, -6.5, ztop + 1.14), (sc[0] + 3.75, 6.5, ztop + 1.14 + 25)); dn_z = zbot - 1.14 - 25
vr = {}
for k, rec in man.items():
    if k in SKIP:
        continue
    lo, hi = np.array(rec['bounds'])
    if np.all(lo - 10 <= [sc[0] + 3.75, 6.5, ztop + 26.2]) and np.all(hi + 10 >= [sc[0] - 3.75, -6.5, ztop]):
        g_ = G(up, P.solid_m(k), 10)
        if g_ < 10:
            vr[k] = g_
vr['openrb-board-upright'] = G(up, ORBm, 10); vr['rear_pack-v18'] = G(up, V18m, 10)
out['pd5991InPack_longAxisVertical'] = dict(pcbZ=[zbot, round(ztop, 2)], width=20.32,
    usbcUp=dict(plugBox=P.from_m(up).bounds.round(2).tolist(), gaps=dict(sorted(vr.items(), key=lambda kv: kv[1]))),
    usbcDown=dict(plugBottomZ=round(dn_z, 2), packFloorZ=-44.0, verdict='plug body ends at z -43.4 inside the pack (0.6 above the floor) after crossing the leg-plug room (y -4.3..3.6, z -27.75..-17.75); the cable can only leave through the floor, i.e. under the crotch: not allowed'))
print('STAGE', '---------------------- 4.', flush=True)
# ---------------------------------------------------------------- 4. shells beside the pack
SH = {k: P.solid_mesh(k) for k in ('shell_left', 'shell_right')}
def first_hit(mesh, o, d, far=60.0):
    loc, ri, _ = mesh.ray.intersects_location(o, d, multiple_hits=True)
    out_ = np.full(len(o), far)
    for L, i in zip(loc, ri):
        t = float(np.dot(L - o[i], d[i]))
        if 1e-6 < t < out_[i]:
            out_[i] = t
    return out_
sg = []
for x in np.arange(-48.0, -36.9, 1.0):
    r = dict(x=float(x))
    for k, m in SH.items():
        s_ = 1 if k == 'shell_left' else -1; zz = np.arange(-20, 45, 0.5)
        o = np.c_[np.full_like(zz, x), np.full_like(zz, s_ * 14.0), zz]; d = np.tile([0.0, s_, 0.0], (len(zz), 1))
        hit = first_hit(m, o, d, 40.0); ok = hit < 40.0
        if ok.any():
            iy = 14.0 + hit[ok]; r[k] = dict(zMin=round(float(zz[ok][0]), 1), innerAbsYatZmin=round(float(iy[0]), 2), innerAbsYmin=round(float(iy.min()), 2),
                                             gapFromPackSide18p6=round(float(iy.min()) - 18.6, 2))
        else:
            r[k] = None
    sg.append(r)
out['shellBesidePack_x48to37'] = dict(note='shells exist only above zMin; below it the pack side is open air down to the legs', rows=sg)
print('STAGE', '---------------------- 5.', flush=True)
# ---------------------------------------------------------------- 5. side-window wires forward past the shell rear edge
SHm = {k: P.solid_m(k) for k in SH}
legs = [k for k, rec in man.items() if k not in SKIP and rec.get('module') in ('left-leg', 'right-leg')]
LG = P.union([P.solid_m(k) for k in legs]) if legs else None
fw = []
for s in (1, -1):
    for z in np.arange(-6.0, 36.1, 2.0):
        for yw in (32.95, 33.5):
            path = np.array([[-62.0, s * yw, z], [-30.0, s * yw, z]]); t = K.tube(path, 0.9)
            r = dict(side='+y' if s > 0 else '-y', z=float(z), wireAbsY=yw, shellGap=min(G(t, m, 10) for m in SHm.values()), legGap=G(t, LG, 10) if LG else None)
            inward = K.tube(np.array([[-41.0, s * yw, z], [-41.0, s * 19.5, z]]), 0.9)
            r['inwardAt_x-41_to_packSide'] = dict(shellGap=min(G(inward, m, 10) for m in SHm.values()), packGap=G(inward, V18m, 10))
            fw.append(r)
out['sideWindowForwardRuns'] = dict(note='straight Dia 1.8 wire from x -62 to -30 just outside the box side (|y| 32.95 / 33.5), and an inward branch at x -41 to the pack side |y| 19.5',
                                    rows=fw)
print('STAGE', 'P.jdump(out', flush=True)
P.jdump(out, HERE / 'pack_study.json')
print(json.dumps({k: out[k] for k in ('openrbRearFaceX', 'tetherHoleProbe', 'floorTopZatY0', 'pd5991InPack_longAxisY', 'pd5991InPack_longAxisVertical')}, indent=0)[:7000])
