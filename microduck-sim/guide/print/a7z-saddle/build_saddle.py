"""MicroDuck A7Z saddle V2 (D-028, 2026-10-25; D-022 saddle V1.29 superseded). The Radxa Cubie A7Z with the Radxa Heatsink 6530B
on it sits in a printed saddle on the torso roof over the V1.9 rear pack. World = guide frame, mm (x forward, y left, z up).
The approved design is DESIGN-CONTRACT.json in this directory; ../design_contract.py checks every build against it.

Geometry (all numbers here, build.json repeats them):
- Saddle body: plan outline x -45..-5 (board rear edge x -41.7: the USB-C sockets overhang it by 1.6 and must clear the rear wall inner face x -43.4 on the straight drop, 0.1 mm), |y| <= 34.4 (board 65 + 0.3 a side + 1.6 walls), corner r 3; walls 1.6; floor 1.6 (normal
  offset) following the shell roof and pack 0.5 above them (ray-cast height map, dilated one cell): the 0.5 is the 3M foam tape that
  fixes the saddle to the shell roof (V3, Shawn 2026-10-25: "我宁愿用3M的0.5mm的泡沫双面胶来固定"). Floor cut x -21..-5, |y| <= 16
  over the torso roof opening (IMU, J12 UART and 5 V leads come up here); it still runs out under the front wall foot (slot 32 wide,
  z roof..46.5) because the ID12 neck servo cable and the IMU plug pass there; the head wires come from the neck straight OVER the front wall, whose top is lowered to z 63.0 over |y| <= 28
  (1 mm above the antenna strip top 62, 1.1 below the Dupont housing tops 64.1), into the open header strip (Shawn 2026-10-25:
  "上面下来的杜邦线 不需要从鞍座的下面绕上去吧").
- Board turned 180 deg from V1.29: component side up, USB-C ①, USB-C ② and micro HDMI edge at the REAR (socket faces 1.7 inside
  the rear wall's outer face, one window y -29..26.5 z 47.8..58 over all three (exhaust slots 2 mm above it) so the plug overmoulds enter it, plugged from behind), 40-pin header at the FRONT edge
  (x -19.2..-14.2 housings), pin 1 at +y (robot left). PCB underside z 48.0.
- Board carrier = the saddle floor itself (V3; the V2 tray is gone): four dia 6.6 bosses (dia 6.0 for the top 1 mm, under the board's underside parts) rise from the floor to the PCB
  underside (z 48.0) at the board holes, each with a dia 2.2 through hole and a dia 4.2 pocket from below up to z 46.5 for the screw head.
  On the bench, saddle upside down: four M2 x 6 go up through the pockets and the board holes into the 6530B's threaded bosses
  (the 6530B's own screws occupy the board holes), so saddle + board + heatsink are one unit before it goes on the robot.
  Nothing in the saddle holds the board except these four screws; the lid does not press on anything.
- 6530B (65 x 30 x 11.5, estimated internals from photos, measure on the part): base block d 6..30 from PCB top + 3.1 (SoC 1.6 +
  pad 1.5) to + 11.5, four dia 5 bosses on the board holes, blower dia 24 at the pin-1 (+y) end; intake upward.
- Lid over the heatsink only, a COVER that touches nothing hot: plate z 66.5..68.1 (walls end at 66.5; the side lid screws at
  z 64.2 keep 1.2 mm of wall above their clearance holes and 1.3 mm of boss under their pilots; the screw bosses end 1.0 above the
  heatsink top 61.1) for x -45..-19.6, lip 2.2 deep inside the three closed walls, 5.4 mm of intake plenum between the fins and the
  grille; no pressing bars, no pads (PLA creeps against a 50-60 C heatsink; Shawn 2026-10-25). Two M2 x 6 side screws into bosses
  under the plate. The header strip (x -19.6..-5) is OPEN: no lid over the Dupont housings.
- Antenna AC019 (42 x 12) on the front wall inner face, feed end at the left (y 31 -> -11), 13 mm from the heatsink aluminium.
  The +y wall bulges 2 mm outward from beside the IPEX socket to the front wall (x -35..-6, z 46..59): the board edge is 0.3 from the
  wall elsewhere, so the 1.13 mm pigtail runs forward in this 2.3 mm channel outside the board edge to the antenna feed end.
- Exhaust: five 3 x 10 slots in the -y wall (fin end), two in the rear wall above the ports, two in the front wall right of the
  antenna. microSD card notch through the -y wall at the card's end: card width + 3 each side in x, z 44.5..50.5 (it joins the two
  exhaust slots above it). The A7Z card socket is a friction (push-pull) socket, not push-push (Shawn 2026-10-25: "这个插槽不是弹簧
  插槽"): the inserted card ends 2 mm past the board edge, flush with the wall's outer face, and is pinched out with tweezers
  through the notch (2.5 mm free above the card, 2 mm below).
- Fixing: the two V2.0 shell-to-pack roof screws (-21.5, +-20), the shells' own M2 x 6 in the shell counterbores, are driven
  into the pack bar BEFORE the saddle goes on (an M2 x 10 would run 1.6 out of the bar now that the saddle is not in the stack);
  they end up under the board, head top about 41.6, 0.35 above the roof; the saddle floor has dia 5 holes over them. The saddle + board unit is then fixed to the shell roof with 3M 0.5 mm foam double-sided tape under the
  floor along the left, right and rear edges (the 0.5 floor gap is the tape); no screw, no lug, no hole in the shells.
    /tmp/microduck-cad-venv/bin/python build_saddle.py   (bounded runner)   writes build/*-world.stl and build/build.json"""
import sys, json, math
from pathlib import Path
import numpy as np
import stl_clean, trimesh, manifold3d as m3
from scipy import ndimage
from shapely.geometry import box as sbox
HERE = Path(__file__).resolve().parent; OUT = HERE / 'build'; OUT.mkdir(exist_ok=True)
MS = HERE.parents[2]; WORLD = MS / 'guide/print/world'; HEAD = MS / 'guide/print/a7z-head'
sys.path.insert(0, str(MS / 'guide/print/rear-pack')); import pack_lib as P

T = 1.6; CLR = 0.5                               # CLR: floor to shell roof = the 3M 0.5 mm foam tape
X0, X1, HW, R_PLAN = -45.0, -5.0, 34.4, 3.0
ZU = 48.0                                          # PCB underside (floor bosses top); roof-screw heads top about 44.85 under the tray (45.5)
BOSS = dict(r=3.3, top_z=47.0, r_top=3.0, hole_r=1.1, pocket_r=2.1, pocket_top=46.5)   # floor bosses under the board holes: M2 x 6 head pocket from below (1.2 mm boss wall); r 3.0 for the top 1 mm under the board's underside parts
TAPE = dict(t=0.5, w=8.0, edges=['left', 'right', 'rear'])      # 3M foam double-sided tape under the floor (guide text; not modelled)
BOARD = dict(xr=-41.7, yl=32.5, z_under=ZU)      # (s, d, h) -> (xr + 30 - d, yl - s, z_under + h): header edge d 0 at the front, pin 1 (s 0) at +y
HOLES = [(3.5, 3.5), (3.5, 26.5), (61.5, 3.5), (61.5, 26.5)]
ROOF_SCREWS = [(-21.5, 20.0), (-21.5, -20.0)]      # V2.0 shells S-shell_pack-01/02, the shells' own M2 x 6 (counterbore in the shell roof); driven before the saddle goes on
ROOF_HOLE_R = 2.5                                  # dia 5 hole in the saddle floor over each roof-screw head (head dia 3.8 stands 0.35 above the roof)
CB_FLOOR = []                                      # shell counterbore floor z under each roof screw (ray cast in roof_map)
FLOOR_CUT = dict(x0=-21.0, x1=X1, hy=16.0)         # shell roof opening x >= -20, |y| <= 15; runs out through the front wall foot (slot 32 wide, z roof..46.5): the ID12 neck servo cable and the IMU plug pass under the wall there (gate 2026-10-25); the head wires do NOT use it any more
FRONT_TOP = dict(z=63.0, hy=28.0)                  # front wall top lowered over the header strip: head wires come over it into the housings (tops 64.1)
CARD_NOTCH = dict(dx=3.0, z=(44.5, 50.5))          # -y wall notch round the microSD card end (friction socket: the card is pinched out with tweezers)
SOC = dict(s=(20.4, 35.8), d=(10.0, 25.3), top_h=3.2)
HS = dict(d=(6.4, 30.0), base_h=3.1, top_h=11.5, boss_r=2.5, fan_r=12.0, fan_s=13.5, fan_d=18.0, pad=1.5)   # Radxa 6530B envelope (photos; measure)
DUPONT = dict(h=14.5, rows_d=(2.23, 4.77), s=(8.37, 56.63), half=1.27)
PORT_WIN = dict(ports=dict(y=(-29.0, 26.5), z=(ZU - 0.2, ZU + 10.0)))   # one rear window over USB-C ①, ② and micro HDMI: the socket faces sit 1.4 inside the wall, so every plug's overmould enters the window (1 mm round the camera plug body)
SIDE_SLOTS = dict(xs=[-41.0, -35.0, -29.0, -23.0, -17.0], w=3.0, z=(ZU + 2.0, ZU + 12.0))    # -y wall (fin end)
REAR_SLOTS = dict(ys=[-1.0, 6.0], w=3.0, z=(ZU + 12.0, ZU + 15.0))                          # rear wall, 2 mm above the port window top
FRONT_SLOTS = dict(ys=[-30.0, -22.0], w=3.0, z=(ZU + 2.0, ZU + 12.0))                       # front wall, right of the antenna
BULGE = dict(x=(-35.0, -6.0), z=(46.0, 59.0), out=2.0)                                       # +y wall outward bulge: pigtail channel from beside the IPEX socket to the front wall (board edge to wall is 0.3 elsewhere)
ANT = dict(y=(-11.0, 31.0), z=(50.0, 62.0), t=0.3)                                            # front wall inner face, feed end at +y
LID = dict(x1=-19.6, z0=66.5, z1=68.1, lip=2.2)                 # cover only: no bars, no pads
LID_SCREWS = dict(x=-31.0, z=64.2, boss=dict(x=(-33.5, -28.5), y_in=29.0, above_hs=1.0), pilot_r=0.8, clear_r=1.1)
GRILLE = dict(xs=[-42.0, -38.0, -34.0, -30.0, -26.0], w=2.0, y=(5.0, 30.0))   # the last slot would leave 0.4 mm to the lid front edge
PLUG = dict(len_x=17.8, len_y=21.8, h=8.0)         # D-023 CableCreation B0194WSKOM right-angle body; leg to +y so port ① stays free
STEP = 0.5


def rr_poly(x0, x1, y0, y1, r):
    return sbox(x0, y0, x1, y1).buffer(-r).buffer(r, resolution=24) if r > 0 else sbox(x0, y0, x1, y1)


def prism(poly, z0, z1):
    return P.extrude_xy(poly, z0, z1)


def cyl_z(x, y, z0, z1, r, n=48):
    return m3.Manifold.cylinder(z1 - z0, r, r, n).translate([x, y, z0])


def cyl_y(x, y0, y1, z, r, n=32):
    c = m3.Manifold.cylinder(y1 - y0, r, r, n)
    return c.rotate([-90.0, 0.0, 0.0]).translate([x, y0, z])


def roof_map():
    """Shell roof height z(x, y) by ray cast from above, 0.5 mm grid over the saddle plan; nan where there is no shell."""
    sh = trimesh.util.concatenate([trimesh.load(str(WORLD / f'{n}.stl'), force='mesh') for n in ('shell_left', 'shell_right', 'rear_pack')])
    xs = np.arange(X0 - 1.0, X1 + 1.0 + 1e-9, STEP); ys = np.arange(-HW - BULGE['out'] - 1.0, HW + BULGE['out'] + 1.0 + 1e-9, STEP)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    o = np.c_[X.ravel(), Y.ravel(), np.full(X.size, 90.0)]; dv = np.tile([0.0, 0.0, -1.0], (len(o), 1))
    loc, idx, _ = sh.ray.intersects_location(o, dv, multiple_hits=False)
    Z = np.full(X.size, np.nan); Z[idx] = loc[:, 2]; Z = Z.reshape(X.shape)
    Zp = np.pad(Z, 1, constant_values=np.nan); Zd = Z.copy()
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            Zd = np.fmax(Zd, Zp[1 + di:1 + di + Z.shape[0], 1 + dj:1 + dj + Z.shape[1]])
    Z = Zd
    for sx, sy in ROOF_SCREWS:
        d2 = (X - sx) ** 2 + (Y - sy) ** 2; ring = (d2 > 3.2 ** 2) & (d2 < 4.5 ** 2) & ~np.isnan(Z)
        CB_FLOOR.append(float(np.nanmedian(Z[(d2 > 1.3 ** 2) & (d2 < 1.9 ** 2)])))     # counterbore floor (the head seats here)
        Z[d2 <= 3.2 ** 2] = np.nanmedian(Z[ring])
    return xs, ys, Z


def offset_up(xs, ys, zb, t):
    k = int(np.ceil(t / STEP)); zt = zb + t
    for di in range(-k, k + 1):
        for dj in range(-k, k + 1):
            r2 = (di * STEP) ** 2 + (dj * STEP) ** 2
            if r2 > t * t or (di == 0 and dj == 0):
                continue
            sh = np.full_like(zb, -np.inf)
            si = slice(max(di, 0), zb.shape[0] + min(di, 0)); ti = slice(max(-di, 0), zb.shape[0] + min(-di, 0))
            sj = slice(max(dj, 0), zb.shape[1] + min(dj, 0)); tj = slice(max(-dj, 0), zb.shape[1] + min(-dj, 0))
            sh[ti, tj] = zb[si, sj] + np.sqrt(t * t - r2)
            zt = np.maximum(zt, sh)
    return zt


def heightfield_solid(xs, ys, zb, zt):
    nx, ny = len(xs), len(ys)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    vt = np.c_[X.ravel(), Y.ravel(), zt.ravel()]; vb = np.c_[X.ravel(), Y.ravel(), zb.ravel()]
    V = np.vstack([vt, vb]); off = nx * ny
    idx = lambda i, j: i * ny + j
    F = []
    for i in range(nx - 1):
        for j in range(ny - 1):
            a, b, c, d = idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)
            F += [[a, b, c], [a, c, d], [off + a, off + c, off + b], [off + a, off + d, off + c]]
    for i in range(nx - 1):
        a, b = idx(i, 0), idx(i + 1, 0); F += [[a, off + a, off + b], [a, off + b, b]]
        a, b = idx(i, ny - 1), idx(i + 1, ny - 1); F += [[a, b, off + b], [a, off + b, off + a]]
    for j in range(ny - 1):
        a, b = idx(0, j), idx(0, j + 1); F += [[a, b, off + b], [a, off + b, off + a]]
        a, b = idx(nx - 1, j), idx(nx - 1, j + 1); F += [[a, off + a, off + b], [a, off + b, b]]
    m = trimesh.Trimesh(V, np.array(F), process=False)
    if m.volume < 0:
        m.invert()
    return P.mesh_to_m(m)


def bw(s, d, h):
    return np.array([BOARD['xr'] + 30.0 - d, BOARD['yl'] - s, BOARD['z_under'] + h])


def bbox(s0, s1, d0, d1, h0, h1):
    lo, hi = bw(s0, d0, h0), bw(s1, d1, h1)
    return P.box(np.minimum(lo, hi), np.maximum(lo, hi))


def board_parts():
    """Bought parts in the saddle pose, from the head build's board-frame meshes (rigid remap head world -> (s, d, h) -> here)."""
    F = json.loads((HEAD / 'pi-frame-raw.json').read_text())
    N = np.array(F['n']); ES = np.array(F['es']); ED = -np.array(F['ed_inner']); C1 = np.array(F['c1'])
    ORIGIN = C1 + (34.3876 - C1 @ N) * N - 8.37 * ES - 2.23 * ED
    parts = {}
    for n in ('a7z_pcb', 'soc_a733', 'ram', 'pmic_area', 'wifi_module_fcu760k', 'usb_c_otg_dp', 'usb_c_power', 'micro_hdmi', 'fan_connector',
              'ipex_socket', 'microsd_socket', 'microsd_card', 'csi_connector', 'pcie_fpc', 'uboot_button', 'underside_smd'):
        m = trimesh.load(str(HEAD / 'a7z_parts' / f'{n}.stl'), force='mesh')
        rel = m.vertices - ORIGIN
        s, d, h = rel @ ES, rel @ ED, rel @ N
        v = np.c_[BOARD['xr'] + 30.0 - d, BOARD['yl'] - s, BOARD['z_under'] + h]
        parts[n] = trimesh.Trimesh(v, m.faces[:, ::-1].copy(), process=False)    # the (s, d) -> (x, y) map is a rotation: winding unchanged, but keep the volume check
        if parts[n].volume < 0:
            parts[n].invert()
    return parts


def hole_xy():
    return [(float(bw(s, d, 0)[0]), float(bw(s, d, 0)[1])) for s, d in HOLES]


def build():
    xs, ys, Z = roof_map()
    nan = np.isnan(Z)
    _, idx = ndimage.distance_transform_edt(nan, return_indices=True)
    Zf = Z[idx[0], idx[1]]
    assert not np.isnan(Zf).any()
    zb = Zf + CLR; zt = offset_up(xs, ys, zb, T)
    above_floor = heightfield_solid(xs, ys, zb, np.full_like(zb, 95.0))
    above_top = heightfield_solid(xs, ys, zt, np.full_like(zt, 95.0))
    # plan with the +y bulge (a rounded tab 2 mm outward beside the IPEX socket)
    plan = rr_poly(X0, X1, -HW, HW, R_PLAN).union(rr_poly(BULGE['x'][0], BULGE['x'][1], HW - 2.0, HW + BULGE['out'], 1.0))
    inner = rr_poly(X0 + T, X1 - T, -HW + T, HW - T, max(R_PLAN - T, 0.5)).union(rr_poly(BULGE['x'][0] + T, BULGE['x'][1] - T, HW - 2.0 - T, HW + BULGE['out'] - T, 0.5))
    wall_top = LID['z0']
    shell_outer = prism(plan, 20.0, wall_top) ^ above_floor
    cavity = prism(inner, 20.0, 95.0) ^ above_top
    body = shell_outer - cavity
    # the bulge is a channel only between its z limits: fill it back outside z 46..59 so the wall stays 1.6 there
    bulge_fill = (prism(rr_poly(BULGE['x'][0] + T, BULGE['x'][1] - T, HW - 2.0 - T, HW + BULGE['out'] - T, 0.5), 20.0, BULGE['z'][0]) ^ above_top) + \
                 prism(rr_poly(BULGE['x'][0] + T, BULGE['x'][1] - T, HW - 2.0 - T, HW + BULGE['out'] - T, 0.5), BULGE['z'][1], wall_top)
    body = body + (bulge_fill - prism(rr_poly(X0 + T, X1 - T, -HW + T, HW - T, 0.5), 20.0, 95.0))
    adds = []
    hx = hole_xy()
    for x, y in hx:                                                      # board-carrier bosses: floor to the PCB underside; the top 1 mm is r 3.0
        adds.append((cyl_z(x, y, 30.0, BOSS['top_z'], BOSS['r']) + cyl_z(x, y, 30.0, ZU, BOSS['r_top'])) ^ above_floor)   # (A7Z underside parts sit within 3.3 of the holes)
    body = P.union([body] + adds)
    cuts = []
    for x, y in ROOF_SCREWS:
        cuts.append(cyl_z(x, y, 20.0, 47.0, ROOF_HOLE_R))                  # dia 5 clearance over the roof-screw head (driven before the saddle; V3)
    for x, y in hx:                                                      # through hole + head pocket from below (M2 x 6 driven on the bench)
        cuts.append(cyl_z(x, y, 20.0, ZU + 1.0, BOSS['hole_r'])); cuts.append(cyl_z(x, y, 20.0, BOSS['pocket_top'], BOSS['pocket_r']))
    fc = FLOOR_CUT; cuts.append(P.box((fc['x0'], -fc['hy'], 20.0), (fc['x1'] + 1.0, fc['hy'], 46.5)))          # floor cut, running out under the front wall foot (bridge above): ID12 servo cable + IMU plug
    for x in SIDE_SLOTS['xs']:
        cuts.append(P.box((x, -HW - 1, SIDE_SLOTS['z'][0]), (x + SIDE_SLOTS['w'], -HW + T + 1, SIDE_SLOTS['z'][1])))
    for y in REAR_SLOTS['ys']:
        cuts.append(P.box((X0 - 1, y, REAR_SLOTS['z'][0]), (X0 + T + 1, y + REAR_SLOTS['w'], REAR_SLOTS['z'][1])))
    for y in FRONT_SLOTS['ys']:
        cuts.append(P.box((X1 - T - 1, y, FRONT_SLOTS['z'][0]), (X1 + 1, y + FRONT_SLOTS['w'], FRONT_SLOTS['z'][1])))
    for w in PORT_WIN.values():
        cuts.append(P.box((X0 - 1, w['y'][0], w['z'][0]), (X0 + T + 1, w['y'][1], w['z'][1])))
    parts = board_parts()
    cb = parts['microsd_card'].bounds
    cn = CARD_NOTCH; cuts.append(P.box((cb[0, 0] - cn['dx'], -HW - 1, cn['z'][0]), (cb[1, 0] + cn['dx'], -HW + T + 1, cn['z'][1])))   # card notch, -y wall (tweezers reach the card end)
    for sgn in (1, -1):
        yo = sgn * (HW + BULGE['out'] + 1)   # through the bulge tab too on +y (the wall is 3.6 thick there above the channel; a blind hole left a 1 mm skin)
        cuts.append(cyl_y(LID_SCREWS['x'], min(yo, sgn * (HW - T - 0.5)), max(yo, sgn * (HW - T - 0.5)), LID_SCREWS['z'], LID_SCREWS['clear_r']))
    ft = FRONT_TOP; cuts.append(P.box((X1 - T - 1, -ft['hy'], ft['z']), (X1 + 1, ft['hy'], 80.0)))              # front wall top lowered over the header strip (head wires come over it)
    body = body - P.union(cuts)
    # lid: a cover: plate over the heatsink, lip inside the three closed walls, two screw bosses; minus grille and pilots. Nothing touches the heatsink.
    lid_plan = rr_poly(X0, LID['x1'], -HW, HW, R_PLAN).intersection(sbox(X0 - 1, -HW - 1, LID['x1'], HW + 1))
    lip_o = rr_poly(X0 + T + 0.15, LID['x1'], -HW + T + 0.15, HW - T - 0.15, max(R_PLAN - T, 0.5))
    lip_i = rr_poly(X0 + T + 0.15 + 1.4, LID['x1'] + 1.0, -HW + T + 0.15 + 1.4, HW - T - 0.15 - 1.4, 0.5)
    lid = prism(lid_plan, LID['z0'], LID['z1']) + (prism(lip_o, LID['z0'] - LID['lip'], LID['z0'] + 0.01) - prism(lip_i, LID['z0'] - LID['lip'] - 1, LID['z0'] + 1.0))
    hs_top = ZU + 1.6 + HS['top_h']
    hs_x0, hs_x1 = float(bw(0, HS['d'][1], 0)[0]), float(bw(0, HS['d'][0], 0)[0])        # rear..front of the fin block
    fan_y = float(bw(HS['fan_s'], 0, 0)[1])
    pk = []
    b = LID_SCREWS['boss']
    for sgn in (1, -1):
        y_lo, y_hi = sorted((sgn * b['y_in'], sgn * (HW - T - 0.15)))
        pk.append(P.box((b['x'][0], y_lo, hs_top + b['above_hs']), (b['x'][1], y_hi, LID['z0'] + 0.01)))
    lid = lid + P.union(pk)
    gc = [P.box((x, GRILLE['y'][0], LID['z0'] - 1), (x + GRILLE['w'], GRILLE['y'][1], LID['z1'] + 1)) for x in GRILLE['xs']]
    for sgn in (1, -1):
        gc.append(cyl_y(LID_SCREWS['x'], min(sgn * (HW + 1), sgn * (b['y_in'] - 0.5)), max(sgn * (HW + 1), sgn * (b['y_in'] - 0.5)), LID_SCREWS['z'], LID_SCREWS['pilot_r']))
    lid = lid - P.union(gc)
    # bought parts and envelopes
    soc_top = ZU + SOC['top_h']
    hs_body = bbox(0.0, 65.0, HS['d'][0], HS['d'][1], 1.6 + HS['base_h'], 1.6 + HS['top_h'])
    hs_boss = P.union([cyl_z(x, y, ZU + 1.6, ZU + 1.6 + HS['base_h'] + 0.01, HS['boss_r']) for x, y in hx])
    fan_mark = cyl_z(float(bw(HS['fan_s'], HS['fan_d'], 0)[0]), fan_y, hs_top - 0.01, hs_top + 0.1, HS['fan_r'])
    cx, cy = float(bw(np.mean(SOC['s']), np.mean(SOC['d']), 0)[0]), float(bw(np.mean(SOC['s']), np.mean(SOC['d']), 0)[1])
    env = {'heatsink_6530b': hs_body + hs_boss + fan_mark,
           'thermal_pad_6530b': P.box((cx - 8, cy - 8, soc_top), (cx + 8, cy + 8, soc_top + HS['pad'])),
           'dupont_housings': bbox(DUPONT['s'][0] - DUPONT['half'], DUPONT['s'][1] + DUPONT['half'], DUPONT['rows_d'][0] - DUPONT['half'], DUPONT['rows_d'][1] + DUPONT['half'], 1.6, 1.6 + DUPONT['h']),
           'antenna': P.box((X1 - T - ANT['t'], ANT['y'][0], ANT['z'][0]), (X1 - T, ANT['y'][1], ANT['z'][1])),
           'usb_c_plug': None}
    otg = parts['usb_c_otg_dp'].bounds
    face_x = float(otg[0, 0])                                                   # socket face (rear)
    env['usb_c_plug'] = P.box((face_x - PLUG['len_x'], otg[0, 1] - 1.1, ZU + 0.85), (face_x, otg[0, 1] - 1.1 + PLUG['len_y'], ZU + 0.85 + PLUG['h']))
    out = {}
    for name, man in (('saddle_body', body), ('saddle_lid', lid)):
        mesh = stl_clean.clean(P.from_m(man)); mesh.export(OUT / f'{name}-world.stl')
        pieces = [q for q in mesh.split(only_watertight=False) if abs(q.volume) > 0.05]
        out[name] = dict(watertight=bool(mesh.is_watertight), bodies=len(pieces), volume_mm3=round(float(mesh.volume), 1), bounds=np.round(mesh.bounds, 2).tolist())
    for name, man in env.items():
        mesh = P.from_m(man); mesh.export(OUT / f'{name}-world.stl'); out[name] = dict(bounds=np.round(mesh.bounds, 2).tolist())
    for name, mesh in parts.items():
        mesh.export(OUT / f'{name}-world.stl'); out[name] = dict(bounds=np.round(mesh.bounds, 2).tolist(), watertight=bool(mesh.is_watertight))
    for stale in ('fan', 'heatsink', 'thermal_pad'):
        f = OUT / f'{stale}-world.stl'
        if f.exists():
            f.unlink()
    # fit checks
    def ov(a, b):
        i = a ^ b; v = float(i.volume())
        return round(v, 3) if v <= 0 else dict(mm3=round(v, 3), bounds=np.round(P.from_m(i).bounds, 2).tolist())
    chk = {'body_lid': ov(body, lid)}
    for name, man in env.items():
        chk[f'body_{name}'] = ov(body, man); chk[f'lid_{name}'] = ov(lid, man)
    pcb = P.mesh_to_m(parts['a7z_pcb']); chk['body_pcb'] = ov(body, pcb); chk['lid_pcb'] = ov(lid, pcb)
    for n in ('soc_a733', 'ram', 'wifi_module_fcu760k', 'usb_c_otg_dp', 'usb_c_power', 'micro_hdmi', 'microsd_card', 'microsd_socket', 'csi_connector', 'pcie_fpc', 'uboot_button', 'fan_connector', 'ipex_socket'):
        pm = P.mesh_to_m(parts[n]); chk[f'body_{n}'] = ov(body, pm)
    smd = P.mesh_to_m(parts['underside_smd']) - P.union([cyl_z(x, y, 40.0, 50.0, 3.2) for x, y in hx])
    chk['body_underside_smd_outside_hole_keepouts'] = ov(body, smd); chk['body_underside_smd'] = ov(body, P.mesh_to_m(parts['underside_smd']))
    chk['heatsink_dupont'] = ov(env['heatsink_6530b'], env['dupont_housings'])
    head_top = max(CB_FLOOR) + 1.6                                       # the shells' M2 x 6 head (1.6 tall) on the counterbore floor
    chk['roof_screw_counterbore_floor_z'] = [round(v, 2) for v in CB_FLOOR]; chk['roof_screw_head_top_z'] = round(head_top, 2)
    chk['floor_underside_over_roof_screws_z'] = round(float(np.nanmin(zb[((xs[:, None] - ROOF_SCREWS[0][0]) ** 2 + (ys[None, :] - 20.0) ** 2 <= 3.5 ** 2) | ((xs[:, None] - ROOF_SCREWS[1][0]) ** 2 + (ys[None, :] + 20.0) ** 2 <= 3.5 ** 2)])), 2)
    chk['gap_roof_screw_head_to_board_mm'] = round(ZU - head_top, 2)
    chk['floor_top_max_under_board_z'] = round(float(np.nanmax(zt[(xs[:, None] >= BOARD['xr'] - 0.3) & (xs[:, None] <= BOARD['xr'] + 30.3) & (np.abs(ys[None, :]) <= HW - T)])), 2)
    chk['gap_floor_top_to_board_mm'] = round(ZU - chk['floor_top_max_under_board_z'], 2)
    chk['lid_screw_boss_above_heatsink_mm'] = LID_SCREWS['boss']['above_hs']; chk['lid_plate_above_heatsink_mm'] = round(LID['z0'] - hs_top, 2)
    chk['dupont_top_above_lid_plate_mm'] = round((ZU + 1.6 + DUPONT['h']) - LID['z0'], 2)      # the housings stand in the open strip, not under the lid
    chk['lid_front_edge_to_housings_mm'] = round(float(out['dupont_housings']['bounds'][0][0]) - LID['x1'], 2)
    chk['antenna_to_heatsink_boss_mm'] = round(float(out['antenna']['bounds'][0][0]) - float(out['heatsink_6530b']['bounds'][1][0]), 2)
    chk['antenna_to_heatsink_fin_block_mm'] = round(float(out['antenna']['bounds'][0][0]) - float(P.from_m(hs_body).bounds[1][0]), 2)
    chk['port_face_inside_rear_outer_face_mm'] = round(face_x - X0, 2)
    chk['plug_bottom_over_rear_box_top43_mm'] = round(ZU + 0.85 - 43.0, 2)
    robot = {}
    for n in ('shell_left', 'shell_right', 'rear_pack', 'head_bottom', 'head_cap', 'jaw_frame', 'imu_board', 'openrb-board-upright', 'clip_torso', 'neck_pitch_ring'):
        f = WORLD / f'{n}.stl'
        if f.exists():
            robot[n] = ov(body + lid, P.mesh_to_m(trimesh.load(str(f), force='mesh')))
    BP = MS / 'guide/print/back-plate'
    for n in ('rear_frame', 'rear_lid'):
        robot[n] = ov(body + env['usb_c_plug'], P.mesh_to_m(trimesh.load(str(BP / f'{n}-world.stl'), force='mesh')))
    for n in ('battery_backpack_frame', 'battery_backpack_cap'):
        f = BP / 'battery-backpack-20261015' / f'{n}-world.stl'
        if f.exists():
            robot[n] = ov(env['usb_c_plug'], P.mesh_to_m(trimesh.load(str(f), force='mesh')))
    chk['body_vs_robot_overlap_mm3'] = robot
    screws = [dict(id=f'SD-board-{i + 1:02d}', spec='M2 x 6 TAP, from below', center=[round(x, 2), round(y, 2), BOSS['pocket_top']], axis=[0, 0, 1], through=['saddle_body floor boss', 'A7Z board hole'], into='6530B threaded boss') for i, (x, y) in enumerate(hx)]
    screws += [dict(id=f'S-shell_pack-{i + 1:02d}', spec='M2 x 6 TAP (the V2.0 shells\' own)', center=[x, y, round(head_top, 2)], axis=[0, 0, -1], through=['shell'], into='rear_pack shoulder bar', note='driven before the saddle (with the board on it) is taped onto the roof') for i, (x, y) in enumerate(ROOF_SCREWS)]
    screws += [dict(id=f'SD-lid-{i + 1:02d}', spec='M2 x 6 TAP', center=[LID_SCREWS['x'], round(sgn * HW, 2), LID_SCREWS['z']], axis=[0, -sgn, 0], through=['saddle_body wall'], into='saddle_lid boss') for i, sgn in enumerate((1, -1))]
    R = dict(params=dict(T=T, CLR=CLR, ZU=ZU, X0=X0, X1=X1, HW=HW, R_PLAN=R_PLAN, BOSS=BOSS, TAPE=TAPE, FRONT_TOP=FRONT_TOP, CARD_NOTCH=CARD_NOTCH, BOARD=BOARD, HOLES=HOLES, HOLES_XY=hx, ROOF_SCREWS=ROOF_SCREWS, FLOOR_CUT=FLOOR_CUT,
                         SOC=SOC, HS=HS, DUPONT=DUPONT, PORT_WIN=PORT_WIN, SIDE_SLOTS=SIDE_SLOTS, REAR_SLOTS=REAR_SLOTS, FRONT_SLOTS=FRONT_SLOTS, BULGE=BULGE, ANT=ANT, LID=LID, LID_SCREWS=LID_SCREWS, GRILLE=GRILLE, PLUG=PLUG),
             parts=out, checks=chk, screws=screws,
             estimatedFromPhotos=['HS (6530B base height, fin block depth d 6..30, blower position and diameter): measure on the part before release', 'lid screw bosses sit 1.0 above the estimated heatsink top 61.1'],
             thinWallAllowances=dict(saddle_body=[dict(bbox=[[X0 - 0.1, -HW - 0.1, 26.0], [X0 + 2.0, HW + 0.1, 38.0]], minMm=0.1, reason='rear wall foot: vertical outer face meeting the shell roof seat that falls about 1.2 mm per mm towards the rear'),
                                                  dict(bbox=[[X0 - 0.1, HW - 4.0, 26.0], [X1 + 0.1, HW + BULGE['out'] + 0.1, 38.0]], minMm=0.1, reason='+y wall foot on the shell flank edge: wedge where the side wall meets the sloping roof edge'),
                                                  dict(bbox=[[X0 - 0.1, -HW - 0.1, 26.0], [X1 + 0.1, -HW + 4.0, 38.0]], minMm=0.1, reason='-y wall foot on the shell flank edge: same wedge')]),
             roof=dict(z_at_centre=float(np.nanmax(Z)), z_min_under_floor=float(np.nanmin(Zf)), counterbore_floor=[round(v, 2) for v in CB_FLOOR], grid_step=STEP))
    (OUT / 'build.json').write_text(json.dumps(R, indent=1) + '\n')
    pins = {n: [round(float(bw(DUPONT['s'][0] + ((n - 1) // 2) * 2.54, DUPONT['rows_d'][0] if n % 2 == 0 else DUPONT['rows_d'][1], 1.6 + 8.5)[k]), 3) for k in range(3)] for n in range(1, 41)}
    (OUT / 'pins.json').write_text(json.dumps(dict(frame='guide world mm (x forward, y left, z up)', pinTop=pins, housingBounds=out['dupont_housings']['bounds'],
                                                   fanConnectorJ6=out['fan_connector']['bounds'], floorCut=dict(x=[FLOOR_CUT['x0'], FLOOR_CUT['x1']], y=[-FLOOR_CUT['hy'], FLOOR_CUT['hy']], zBelowBoard=ZU),
                                                   boardFrontEdgeX=BOARD['xr'] + 30.0, frontWallInnerX=X1 - T, heatsink=out['heatsink_6530b']['bounds'], lidUndersideZ=LID['z0'], headerStripOpen=True), indent=1) + '\n')
    print(json.dumps(dict(parts={k: v for k, v in out.items() if k.startswith('saddle')}, checks=chk), indent=1))


if __name__ == '__main__':
    build()
