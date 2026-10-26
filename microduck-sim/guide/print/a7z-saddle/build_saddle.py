"""MicroDuck A7Z saddle V2 (D-028, 2026-10-25; D-022 saddle V1.29 superseded). The Radxa Cubie A7Z with the Radxa Heatsink 6530B
on it sits in a printed saddle on the torso roof over the V1.9 rear pack. World = guide frame, mm (x forward, y left, z up).
The approved design is DESIGN-CONTRACT.json in this directory; ../design_contract.py checks every build against it.

Geometry (all numbers here, build.json repeats them):
- Saddle body: plan outline x -45..-5 (board rear edge x -41.7: the USB-C sockets overhang it by 1.6 and must clear the rear wall inner face x -43.4 on the straight drop, 0.1 mm), |y| <= 34.4 (board 65 + 0.3 a side + 1.6 walls), corner r 3; walls 1.6; floor 1.6 (normal
  offset) following the shell roof and pack 0.3 above them (ray-cast height map, dilated one cell). Floor cut x -21..-5, |y| <= 16
  over the torso roof opening (IMU, J12 UART and 5 V leads come up here); it still runs out under the front wall foot (slot 32 wide,
  z roof..46.5) because the ID12 neck servo cable and the IMU plug pass there; the head wires come from the neck straight OVER the front wall, whose top is lowered to z 63.0 over |y| <= 28
  (1 mm above the antenna strip top 62, 1.1 below the Dupont housing tops 64.1), into the open header strip (Shawn 2026-10-25:
  "上面下来的杜邦线 不需要从鞍座的下面绕上去吧").
- Board turned 180 deg from V1.29: component side up, USB-C ①, USB-C ② and micro HDMI edge at the REAR (socket faces 1.7 inside
  the rear wall's outer face, one window y -29..26.5 z 47.8..58 over all three (exhaust slots 2 mm above it) so the plug overmoulds enter it, plugged from behind), 40-pin header at the FRONT edge
  (x -19.2..-14.2 housings), pin 1 at +y (robot left). PCB underside z 48.0.
- Tray: a 1.4 mm printed plate (z 45.5..46.9) under the board with four dia 6 bosses up to the PCB at the board holes; the board +
  6530B unit is screwed to it from BELOW on the bench (M2 x 6 up through a 1.0 deep counterbore, the board, into the heatsink's
  threaded bosses: the 6530B's own screws occupy the board holes, so nothing screws down into posts any more). The tray is cut
  out under the sockets and open over the floor cut (|y| <= 16, x > -22) so the torso wires pass under the board to the front
  drop gap. It rests on four short posts and is located by the walls; the lid clamps the heatsink.
- 6530B (65 x 30 x 11.5, estimated internals from photos, measure on the part): base block d 6..30 from PCB top + 3.1 (SoC 1.6 +
  pad 1.5) to + 11.5, four dia 5 bosses on the board holes, blower dia 24 at the pin-1 (+y) end; intake upward.
- Lid over the heatsink only: plate z 65.8..67.4 (walls end at 65.8: the side lid screws at z 63.5 need 1.2 mm of wall above
  their clearance holes and 1.2 mm of boss under their pilots over the heatsink top 61.2) for x -45..-19.6, lip 2.2 deep inside the three closed walls, two pressing bars on
  the fin block (rear and front edges, right half) plus a pad at the left rear corner; grille over the blower; two M2 x 6 side
  screws into bosses under the plate. The header strip (x -19.6..-5) is OPEN: no lid over the Dupont housings.
- Antenna AC019 (42 x 12) on the front wall inner face, feed end at the left (y 31 -> -11), 13 mm from the heatsink aluminium.
  The +y wall bulges 2 mm outward from beside the IPEX socket to the front wall (x -35..-6, z 46..59): the board edge is 0.3 from the
  wall elsewhere, so the 1.13 mm pigtail runs forward in this 2.3 mm channel outside the board edge to the antenna feed end.
- Exhaust: five 3 x 10 slots in the -y wall (fin end), two in the rear wall above the ports, two in the front wall right of the
  antenna. microSD card notch through the -y wall at the card's end: card width + 3 each side in x, z 44.5..50.5 (it joins the two
  exhaust slots above it). The A7Z card socket is a friction (push-pull) socket, not push-push (Shawn 2026-10-25: "这个插槽不是弹簧
  插槽"): the inserted card ends 2 mm past the board edge, flush with the wall's outer face, and is pinched out with tweezers
  through the notch (2.5 mm free above the card, 2 mm below).
- Fixing: the two V2.0 shell-to-pack roof screws (-21.5, +-20) M2 x 10 through the saddle floor on flat seats (driven before the
  tray goes in; heads top about 44.85, tray bottom 45.5).
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

T = 1.6; CLR = 0.3
X0, X1, HW, R_PLAN = -45.0, -5.0, 34.4, 3.0
ZU = 48.0                                          # PCB underside (tray bosses top); roof-screw heads top about 44.85 under the tray (45.5)
TRAY = dict(z0=45.5, z1=46.9, boss_r=3.0, cbore_r=2.1, cbore_d=1.0, hole_r=1.1, notch_x=-22.0, notch_hy=16.0)
BOARD = dict(xr=-41.7, yl=32.5, z_under=ZU)      # (s, d, h) -> (xr + 30 - d, yl - s, z_under + h): header edge d 0 at the front, pin 1 (s 0) at +y
HOLES = [(3.5, 3.5), (3.5, 26.5), (61.5, 3.5), (61.5, 26.5)]
ROOF_SCREWS = [(-21.5, 20.0), (-21.5, -20.0)]      # V2.0 shells S-shell_pack-01/02, M2 x 10 (seat z 43.25)
TRAY_POSTS = [(-30.0, 29.5), (-30.0, -29.5), (-40.0, 0.0), (-24.5, 0.0)]   # dia 5, floor to the tray bottom; clear of the roof screws and the board-hole screw heads
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
LID = dict(x1=-19.6, z0=65.8, z1=67.4, lip=2.2, bar_w=2.0, pad=dict(x=(-43.0, -40.5), y=(28.0, 32.0)))
LID_SCREWS = dict(x=-31.0, z=63.5, boss=dict(x=(-33.5, -28.5), y_in=29.0), pilot_r=0.8, clear_r=1.1)
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
    for x, y in TRAY_POSTS:
        adds.append(cyl_z(x, y, 30.0, TRAY['z0'], 2.5) ^ above_top)
    seat_top = float(np.nanmax(zt[((xs[:, None] - ROOF_SCREWS[0][0]) ** 2 + (ys[None, :] - abs(ROOF_SCREWS[0][1])) ** 2 <= 3.2 ** 2) | ((xs[:, None] - ROOF_SCREWS[1][0]) ** 2 + (ys[None, :] + abs(ROOF_SCREWS[1][1])) ** 2 <= 3.2 ** 2)])) + 0.2
    for x, y in ROOF_SCREWS:
        adds.append(cyl_z(x, y, 30.0, seat_top, 3.0) ^ above_top)
    body = P.union([body] + adds)
    cuts = []
    for x, y in ROOF_SCREWS:
        cuts.append(cyl_z(x, y, 20.0, 50.0, 1.1))
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
        cuts.append(cyl_y(LID_SCREWS['x'], min(sgn * (HW + 1), sgn * (HW - T - 0.5)), max(sgn * (HW + 1), sgn * (HW - T - 0.5)), LID_SCREWS['z'], LID_SCREWS['clear_r']))
    ft = FRONT_TOP; cuts.append(P.box((X1 - T - 1, -ft['hy'], ft['z']), (X1 + 1, ft['hy'], 80.0)))              # front wall top lowered over the header strip (head wires come over it)
    body = body - P.union(cuts)
    # tray
    hx = hole_xy()
    tray_plan = sbox(BOARD['xr'] - 0.3, -HW + T + 0.15, BOARD['xr'] + 30.0 + 0.3, HW - T - 0.15)
    notch = sbox(TRAY['notch_x'], -TRAY['notch_hy'], X1, TRAY['notch_hy'])
    from shapely.ops import unary_union
    # plate plan: minus the notch and the underside-part cut-outs (0.8 clear), then a 1.2 mm morphological opening so no strip
    # of plate thinner than 1.2 mm is left between two cut-outs or between a cut-out and the plate edge (wall check)
    part_cuts = [sbox(parts[n].bounds[0, 0] - 0.8, parts[n].bounds[0, 1] - 0.8, parts[n].bounds[1, 0] + 0.8, parts[n].bounds[1, 1] + 0.8)
                 for n in ('microsd_socket', 'microsd_card', 'csi_connector', 'pcie_fpc', 'uboot_button')]
    plate = tray_plan.difference(notch).difference(unary_union(part_cuts)).buffer(-0.6, join_style=2).buffer(0.6, join_style=2)
    tray = prism(plate, TRAY['z0'], TRAY['z1'])
    tray = tray + P.union([cyl_z(x, y, TRAY['z0'], ZU, TRAY['boss_r']) for x, y in hx])
    tcuts = [cyl_z(x, y, TRAY['z0'] - 1, ZU + 1, TRAY['hole_r']) for x, y in hx] + [cyl_z(x, y, TRAY['z0'] - 1, TRAY['z0'] + TRAY['cbore_d'], TRAY['cbore_r']) for x, y in hx]
    tray = tray - P.union(tcuts)
    # lid: plate over the heatsink, lip inside the three closed walls, pressing bars, left-rear pad, screw bosses; minus grille and pilots
    lid_plan = rr_poly(X0, LID['x1'], -HW, HW, R_PLAN).intersection(sbox(X0 - 1, -HW - 1, LID['x1'], HW + 1))
    lip_o = rr_poly(X0 + T + 0.15, LID['x1'], -HW + T + 0.15, HW - T - 0.15, max(R_PLAN - T, 0.5))
    lip_i = rr_poly(X0 + T + 0.15 + 1.4, LID['x1'] + 1.0, -HW + T + 0.15 + 1.4, HW - T - 0.15 - 1.4, 0.5)
    lid = prism(lid_plan, LID['z0'], LID['z1']) + (prism(lip_o, LID['z0'] - LID['lip'], LID['z0'] + 0.01) - prism(lip_i, LID['z0'] - LID['lip'] - 1, LID['z0'] + 1.0))
    hs_top = ZU + 1.6 + HS['top_h']
    hs_x0, hs_x1 = float(bw(0, HS['d'][1], 0)[0]), float(bw(0, HS['d'][0], 0)[0])        # rear..front of the fin block
    fan_y = float(bw(HS['fan_s'], 0, 0)[1])
    pk = [P.box((hs_x0, -31.0, hs_top), (hs_x0 + LID['bar_w'], fan_y - HS['fan_r'] - 1.0, LID['z0'] + 0.01)),             # rear bar, right of the blower
          P.box((min(hs_x1, LID['x1']) - LID['bar_w'], -31.0, hs_top), (min(hs_x1, LID['x1']), fan_y - HS['fan_r'] - 1.0, LID['z0'] + 0.01)),   # front bar (inside the lid plate)
          P.box((LID['pad']['x'][0], LID['pad']['y'][0], hs_top), (LID['pad']['x'][1], LID['pad']['y'][1], LID['z0'] + 0.01))]   # left-rear corner pad (verify on the part)
    b = LID_SCREWS['boss']
    for sgn in (1, -1):
        y_lo, y_hi = sorted((sgn * b['y_in'], sgn * (HW - T - 0.15)))
        pk.append(P.box((b['x'][0], y_lo, hs_top + 0.3), (b['x'][1], y_hi, LID['z0'] + 0.01)))
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
    for name, man in (('saddle_body', body), ('saddle_lid', lid), ('saddle_tray', tray)):
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
    chk = {'body_lid': ov(body, lid), 'body_tray': ov(body, tray), 'lid_tray': ov(lid, tray)}
    for name, man in env.items():
        chk[f'body_{name}'] = ov(body, man); chk[f'lid_{name}'] = ov(lid, man); chk[f'tray_{name}'] = ov(tray, man)
    pcb = P.mesh_to_m(parts['a7z_pcb']); chk['body_pcb'] = ov(body, pcb); chk['lid_pcb'] = ov(lid, pcb); chk['tray_pcb'] = ov(tray, pcb)
    for n in ('soc_a733', 'ram', 'wifi_module_fcu760k', 'usb_c_otg_dp', 'usb_c_power', 'micro_hdmi', 'microsd_card', 'microsd_socket', 'csi_connector', 'pcie_fpc', 'uboot_button', 'fan_connector', 'ipex_socket'):
        pm = P.mesh_to_m(parts[n]); chk[f'body_{n}'] = ov(body, pm); chk[f'tray_{n}'] = ov(tray, pm)
    smd = P.mesh_to_m(parts['underside_smd']) - P.union([cyl_z(x, y, 40.0, 50.0, 3.2) for x, y in hx])
    chk['tray_underside_smd_outside_hole_keepouts'] = ov(tray, smd); chk['body_underside_smd'] = ov(body, P.mesh_to_m(parts['underside_smd']))
    chk['heatsink_dupont'] = ov(env['heatsink_6530b'], env['dupont_housings'])
    head_top = seat_top + 1.6
    chk['roof_screw_seat_top_z'] = round(seat_top, 2); chk['roof_screw_head_top_z'] = round(head_top, 2)
    chk['gap_roof_screw_head_to_tray_mm'] = round(TRAY['z0'] - head_top, 2)
    chk['floor_top_max_under_tray_z'] = round(float(np.nanmax(zt[(xs[:, None] >= BOARD['xr'] - 0.3) & (xs[:, None] <= BOARD['xr'] + 30.3) & (np.abs(ys[None, :]) <= HW - T)])), 2)
    chk['gap_floor_top_to_tray_mm'] = round(TRAY['z0'] - chk['floor_top_max_under_tray_z'], 2)
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
            robot[n] = ov(body + tray + lid, P.mesh_to_m(trimesh.load(str(f), force='mesh')))
    BP = MS / 'guide/print/back-plate'
    for n in ('rear_frame', 'rear_lid'):
        robot[n] = ov(body + env['usb_c_plug'], P.mesh_to_m(trimesh.load(str(BP / f'{n}-world.stl'), force='mesh')))
    for n in ('battery_backpack_frame', 'battery_backpack_cap'):
        f = BP / 'battery-backpack-20261015' / f'{n}-world.stl'
        if f.exists():
            robot[n] = ov(env['usb_c_plug'], P.mesh_to_m(trimesh.load(str(f), force='mesh')))
    chk['body_vs_robot_overlap_mm3'] = robot
    screws = [dict(id=f'SD-board-{i + 1:02d}', spec='M2 x 6 TAP, from below', center=[round(x, 2), round(y, 2), round(TRAY['z0'], 2)], axis=[0, 0, 1], through=['saddle_tray boss', 'A7Z board hole'], into='6530B threaded boss') for i, (x, y) in enumerate(hx)]
    screws += [dict(id=f'S-shell_pack-{i + 1:02d}', spec='M2 x 10 TAP', center=[x, y, 44.0], axis=[0, 0, -1], through=['saddle_body', 'shell'], into='rear_pack shoulder bar', note='driven before the tray goes in') for i, (x, y) in enumerate(ROOF_SCREWS)]
    screws += [dict(id=f'SD-lid-{i + 1:02d}', spec='M2 x 6 TAP', center=[LID_SCREWS['x'], round(sgn * HW, 2), LID_SCREWS['z']], axis=[0, -sgn, 0], through=['saddle_body wall'], into='saddle_lid boss') for i, sgn in enumerate((1, -1))]
    R = dict(params=dict(T=T, CLR=CLR, ZU=ZU, X0=X0, X1=X1, HW=HW, R_PLAN=R_PLAN, TRAY=TRAY, FRONT_TOP=FRONT_TOP, CARD_NOTCH=CARD_NOTCH, BOARD=BOARD, HOLES=HOLES, HOLES_XY=hx, ROOF_SCREWS=ROOF_SCREWS, TRAY_POSTS=TRAY_POSTS, FLOOR_CUT=FLOOR_CUT,
                         SOC=SOC, HS=HS, DUPONT=DUPONT, PORT_WIN=PORT_WIN, SIDE_SLOTS=SIDE_SLOTS, REAR_SLOTS=REAR_SLOTS, FRONT_SLOTS=FRONT_SLOTS, BULGE=BULGE, ANT=ANT, LID=LID, LID_SCREWS=LID_SCREWS, GRILLE=GRILLE, PLUG=PLUG),
             parts=out, checks=chk, screws=screws,
             estimatedFromPhotos=['HS (6530B base height, fin block depth d 6..30, blower position and diameter): measure on the part before release', 'LID pad at the left-rear corner assumes fin material beside the blower'],
             thinWallAllowances=dict(saddle_body=[dict(bbox=[[X0 - 0.1, -HW - 0.1, 26.0], [X0 + 2.0, HW + 0.1, 38.0]], minMm=0.1, reason='rear wall foot: vertical outer face meeting the shell roof seat that falls about 1.2 mm per mm towards the rear'),
                                                  dict(bbox=[[X0 - 0.1, HW - 4.0, 26.0], [X1 + 0.1, HW + BULGE['out'] + 0.1, 38.0]], minMm=0.1, reason='+y wall foot on the shell flank edge: wedge where the side wall meets the sloping roof edge'),
                                                  dict(bbox=[[X0 - 0.1, -HW - 0.1, 26.0], [X1 + 0.1, -HW + 4.0, 38.0]], minMm=0.1, reason='-y wall foot on the shell flank edge: same wedge')]),
             roof=dict(z_at_centre=float(np.nanmax(Z)), z_min_under_floor=float(np.nanmin(Zf)), z_under_roof_screws=round(seat_top - 0.2 - T - CLR, 2), grid_step=STEP))
    (OUT / 'build.json').write_text(json.dumps(R, indent=1) + '\n')
    pins = {n: [round(float(bw(DUPONT['s'][0] + ((n - 1) // 2) * 2.54, DUPONT['rows_d'][0] if n % 2 == 0 else DUPONT['rows_d'][1], 1.6 + 8.5)[k]), 3) for k in range(3)] for n in range(1, 41)}
    (OUT / 'pins.json').write_text(json.dumps(dict(frame='guide world mm (x forward, y left, z up)', pinTop=pins, housingBounds=out['dupont_housings']['bounds'],
                                                   fanConnectorJ6=out['fan_connector']['bounds'], floorCut=dict(x=[FLOOR_CUT['x0'], FLOOR_CUT['x1']], y=[-FLOOR_CUT['hy'], FLOOR_CUT['hy']], zBelowBoard=ZU),
                                                   boardFrontEdgeX=BOARD['xr'] + 30.0, frontWallInnerX=X1 - T, heatsink=out['heatsink_6530b']['bounds'], lidUndersideZ=LID['z0'], headerStripOpen=True), indent=1) + '\n')
    print(json.dumps(dict(parts={k: v for k, v in out.items() if k.startswith('saddle')}, checks=chk), indent=1))


if __name__ == '__main__':
    build()
