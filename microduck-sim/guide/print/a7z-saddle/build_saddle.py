"""MicroDuck A7Z saddle (D-022, 2026-10-22): the Radxa Cubie A7Z leaves the head and sits in a printed saddle on the torso
roof over the V1.9 rear pack, with a 15x15x5 copper heatsink and a 30x30x8 5 V fan. World = guide frame, mm (x forward,
y left, z up). Concept, balance and head-sweep evidence: ../a7z-slice-20261022/.

Geometry (all numbers here, build.json repeats them):
- Saddle body: plan outline x -45..-5 (rear wall just in front of the rear box front plate at x -47..-45), |y| <= 34.4
  (board 65 + 0.3 a side + 1.6 walls), corner r 3 (the board's corners are inside); walls 1.6; floor 1.6 (normal offset) following the shell roof and pack 0.3 above them (ray-cast
  height map, dilated one cell); outside the shell the nearest shell height, so the wall bottoms follow the roof edge. Floor cut x -21..-5, |y| <= 16 over the
  torso roof opening (IMU, J12 UART and 5 V leads come up here; the neck bundle leaves the opening in front of the saddle).
- Board: component side up, header edge at the rear (x -42.8, 0.6 off the inner wall), USB-C/HDMI edge at the front (x -12.8), pin-1 end at -y
  (y -32.5..32.5), PCB underside z 47.0 on four dia 5 posts (Pi Zero hole pattern 58 x 23), M2 x 4 into dia 1.6 pilots.
  Straight Dupont housings on the 40-pin header stand 14.5 mm above the PCB (z 63.1); the fan sits above them.
- Fan 30x30x8 in a pocket under the lid (z 64.4..72.4) at x -36.8..-6.8, y -16.4..13.6: over the copper, clear of the Dupont
  housings (x <= -37.1) so their wires leave upward behind the fan and run round its sides to the floor cut; lid grille above it is
  the intake; exhaust: five 3 x 10 slots in each side wall and two in each front-wall half (z 50..60).
- Copper 15x15x5 on the A733 with a 0.5 mm pad (z 50.7..55.7). Fan to copper 8.7 mm.
- Lid: 1.6 plate z 72.4..74 with a 1.4 mm lip inside the walls (z 70.4..72.4); two M2 x 6 side screws through the walls
  into lip bosses at x -27, z 69.2.
- Fixing: the two V2.0 shell-to-pack roof screws (-21.5, +-20) become M2 x 10 through the saddle floor (dia 2.2 holes) on
  flat seats; their heads (top about 45.1) clear the microSD socket (45.5) and the underside parts (46.0).
- Antenna AC019 (42 x 12) on the rear wall inner face, z 49.5..61.5, behind the Dupont housings; coax to the IPEX at the pin-1 end.
- microSD card slot through the +y wall at the card's end (x -33.6..-21.6, z 45..47.5). USB-C right-angle plug passage
  in the front wall (D-023: y 2.7..26.2, z 46..56.6, for the CableCreation 90-degree OTG plug whose 21.8 mm body lies along +y
  and sticks 10.5 mm out of the wall), camera cable from its +y end forward to the neck bundle.
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
ZU = 47.0                                         # PCB underside; roof-screw heads (top about 45.1) clear the microSD socket (45.5)
Z_LID0, Z_LID1 = ZU + 25.4, ZU + 27.0             # lid plate 72.4..74; the fan top is flush with the lid underside
BOARD = dict(x0=-42.8, y0=-32.5, z_under=ZU)    # (s, d, h) -> (y0 + s, x0 + d, z_under + h)
HOLES = [(3.5, 3.5), (3.5, 26.5), (61.5, 3.5), (61.5, 26.5)]
POST_R, POST_PILOT_R, POST_PILOT_D = 2.5, 0.8, 2.6
ROOF_SCREWS = [(-21.5, 20.0), (-21.5, -20.0)]     # V2.0 shells S-shell_pack-01/02, M2 x 6 -> M2 x 10 (seat z 43.25, 4.9 mm in the bar)
FLOOR_CUT = dict(x0=-21.0, x1=X1, hy=16.0)             # the shell roof opening is x >= -20, |y| <= 15 (ray cast); cut faces 0.5 off the step. The cut runs out through the front wall foot: the neck bundle (audio, touch, camera USB) leaves the roof opening forward to the neck under the wall, slot 32 wide from the shell roof (z 42 at x -5) to z 46.5; the wall above it is a bridge printed on support
SOC = dict(s=(20.4, 35.8), d=(10.0, 25.3), top_h=3.2)
HS = dict(size=15.0, pad=0.5, h=5.0)
FAN = dict(size=30.0, t=8.0, hub_r=13.0, cx=-21.8, cy=-1.4, z0=ZU + 17.4, hole_pitch=24.0)   # x -36.8..-6.8: clear of the housings (x <= -37.1), so the Dupont wires leave upward behind it; copper fully under it
DUPONT = dict(h=14.5, rows_d=(2.23, 4.77), s=(8.37, 56.63), half=1.27)
SIDE_SLOTS = dict(xs=[-40.0, -34.0, -28.0, -22.0, -16.0], w=3.0, z=(ZU + 3.0, ZU + 13.0))
FRONT_SLOTS = dict(ys=[-26.0, -20.0], w=3.0, z=(ZU + 3.0, ZU + 13.0))   # D-023: the V1.29 +y pair (17, 23) lies inside the plug notch and is gone
CARD_SLOT = dict(x=(-33.6, -21.6), z=(ZU - 2.0, ZU + 0.5))
PLUG_NOTCH = dict(y=(2.7, 26.2), z=(ZU - 1.0, ZU + 9.6))      # D-023: CableCreation 90-degree USB-C body (21.8 along the port's wide axis = y, about 8 thick) +0.8 / +0.75 clearance, leg towards +y: the head bundle comes down the left (+y) side of the neck as built; merges with the floor cut below the board
LID_SCREWS = dict(x=-27.0, z=Z_LID0 - 3.2, boss=dict(x=(-29.5, -24.5), y_in=28.8, z=(Z_LID0 - 6.9, Z_LID0)), pilot_r=0.8, clear_r=1.1)
GRILLE = dict(xs=[-35.0, -31.0, -27.0, -23.0, -19.0, -15.0, -11.0], w=2.0, y=(-14.5, 11.5))
ANT = dict(y=(-21.0, 21.0), z=(ZU + 2.5, ZU + 14.5), t=0.3)   # rear wall inner face, behind the Dupont housings: wall to housing 1.56 mm, 1.26 over the strip, the 1.13 mm IPEX pigtail runs in it from the strip's -y end past the housings (|y| > 25.4) to the IPEX socket
STEP = 0.5


def rr_poly(x0, x1, y0, y1, r):
    return sbox(x0, y0, x1, y1).buffer(-r).buffer(r, resolution=24) if r > 0 else sbox(x0, y0, x1, y1)


def prism(poly, z0, z1):
    return P.extrude_xy(poly, z0, z1)


def cyl_z(x, y, z0, z1, r, n=48):
    return m3.Manifold.cylinder(z1 - z0, r, r, n).translate([x, y, z0])


def cyl_y(x, y0, y1, z, r, n=32):
    c = m3.Manifold.cylinder(y1 - y0, r, r, n)                       # along +z
    return c.rotate([-90.0, 0.0, 0.0]).translate([x, y0, z])        # z -> +y


def roof_map():
    """Shell roof height z(x, y) by ray cast from above, 0.5 mm grid over the saddle plan; nan where there is no shell."""
    sh = trimesh.util.concatenate([trimesh.load(str(WORLD / f'{n}.stl'), force='mesh') for n in ('shell_left', 'shell_right', 'rear_pack')])
    xs = np.arange(X0 - 1.0, X1 + 1.0 + 1e-9, STEP); ys = np.arange(-HW - 1.0, HW + 1.0 + 1e-9, STEP)
    X, Y = np.meshgrid(xs, ys, indexing='ij')
    o = np.c_[X.ravel(), Y.ravel(), np.full(X.size, 90.0)]; dv = np.tile([0.0, 0.0, -1.0], (len(o), 1))
    loc, idx, _ = sh.ray.intersects_location(o, dv, multiple_hits=False)
    Z = np.full(X.size, np.nan); Z[idx] = loc[:, 2]; Z = Z.reshape(X.shape)
    # one-cell dilation (max over the 3x3 neighbourhood, nan-aware) so the floor never undercuts a slope between samples
    Zp = np.pad(Z, 1, constant_values=np.nan); Zd = Z.copy()
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            Zd = np.fmax(Zd, Zp[1 + di:1 + di + Z.shape[0], 1 + dj:1 + dj + Z.shape[1]])
    Z = Zd
    # fill the two roof-screw counterbores with the ring median so the floor does not dip into them
    for sx, sy in ROOF_SCREWS:
        d2 = (X - sx) ** 2 + (Y - sy) ** 2; ring = (d2 > 3.2 ** 2) & (d2 < 4.5 ** 2) & ~np.isnan(Z)
        Z[d2 <= 3.2 ** 2] = np.nanmedian(Z[ring])
    return xs, ys, Z


def offset_up(xs, ys, zb, t):
    """Upper offset surface of the height map zb by distance t (max over the disc |d| <= t of zb(x + d) + sqrt(t^2 - |d|^2)),
    so the slab between zb and the result is at least t thick normal to the surface, on slopes and steps alike."""
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
    """Closed solid between two height maps on a rectangular grid (zb < zt everywhere)."""
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
    # sides: j = 0 and j = ny-1 edges along i; i = 0 and i = nx-1 edges along j
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
    return np.array([BOARD['x0'] + d, BOARD['y0'] + s, BOARD['z_under'] + h])


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
        v = np.c_[BOARD['x0'] + d, BOARD['y0'] + s, BOARD['z_under'] + h]
        parts[n] = trimesh.Trimesh(v, m.faces.copy(), process=False)
        if parts[n].volume < 0:
            parts[n].invert()
    return parts


def build():
    xs, ys, Z = roof_map()
    nan = np.isnan(Z)                                                        # no shell or pack under this column (outside the
    _, idx = ndimage.distance_transform_edt(nan, return_indices=True)       # flank, the roof opening): take the nearest hit
    Zf = Z[idx[0], idx[1]]                                                   # height, so the floor and wall bottoms follow the
    assert not np.isnan(Zf).any()                                            # shell's edge profile without a step
    zb = Zf + CLR; zt = offset_up(xs, ys, zb, T)                             # floor bottom (shell + clearance) / top (1.6 normal offset)
    plan = rr_poly(X0, X1, -HW, HW, R_PLAN); inner = rr_poly(X0 + T, X1 - T, -HW + T, HW - T, max(R_PLAN - T, 0.5))
    above_floor = heightfield_solid(xs, ys, zb, np.full_like(zb, 95.0))      # everything from the floor bottom up
    above_top = heightfield_solid(xs, ys, zt, np.full_like(zt, 95.0))        # everything from the floor top up (cavity)
    shell_outer = prism(plan, 20.0, Z_LID0) ^ above_floor
    cavity = prism(inner, 20.0, 95.0) ^ above_top
    body = shell_outer - cavity
    # posts and roof-screw seats on the floor top
    adds = []
    for s, d in HOLES:
        x, y = BOARD['x0'] + d, BOARD['y0'] + s
        adds.append(cyl_z(x, y, 30.0, BOARD['z_under'], POST_R) ^ above_top)
    seat_top = float(np.nanmax(zt[((xs[:, None] - ROOF_SCREWS[0][0]) ** 2 + (ys[None, :] - abs(ROOF_SCREWS[0][1])) ** 2 <= 3.2 ** 2) | ((xs[:, None] - ROOF_SCREWS[1][0]) ** 2 + (ys[None, :] + abs(ROOF_SCREWS[1][1])) ** 2 <= 3.2 ** 2)])) + 0.2
    for x, y in ROOF_SCREWS:
        adds.append(cyl_z(x, y, 30.0, seat_top, 3.0) ^ above_top)            # flat seat for the M2 x 10 head on the domed floor
    b = LID_SCREWS['boss']
    body = P.union([body] + adds)
    cuts = []
    for s, d in HOLES:
        x, y = BOARD['x0'] + d, BOARD['y0'] + s
        cuts.append(cyl_z(x, y, BOARD['z_under'] - POST_PILOT_D, BOARD['z_under'] + 1.0, POST_PILOT_R))
    for x, y in ROOF_SCREWS:
        cuts.append(cyl_z(x, y, 20.0, 50.0, 1.1))
    fc = FLOOR_CUT; cuts.append(P.box((fc['x0'], -fc['hy'], 20.0), (fc['x1'] + 1.0, fc['hy'], BOARD['z_under'] - 0.5)))
    for x in SIDE_SLOTS['xs']:
        for sgn in (1, -1):
            cuts.append(P.box((x, min(sgn * (HW + 1), sgn * (HW - T - 1)), SIDE_SLOTS['z'][0]), (x + SIDE_SLOTS['w'], max(sgn * (HW + 1), sgn * (HW - T - 1)), SIDE_SLOTS['z'][1])))
    for y in FRONT_SLOTS['ys']:
        cuts.append(P.box((X1 - T - 1, y, FRONT_SLOTS['z'][0]), (X1 + 1, y + FRONT_SLOTS['w'], FRONT_SLOTS['z'][1])))
    cuts.append(P.box((CARD_SLOT['x'][0], HW - T - 1, CARD_SLOT['z'][0]), (CARD_SLOT['x'][1], HW + 1, CARD_SLOT['z'][1])))
    cuts.append(P.box((X1 - T - 1, PLUG_NOTCH['y'][0], PLUG_NOTCH['z'][0]), (X1 + 1, PLUG_NOTCH['y'][1], PLUG_NOTCH['z'][1])))
    for sgn in (1, -1):
        cuts.append(cyl_y(LID_SCREWS['x'], min(sgn * (HW + 1), sgn * (HW - T - 0.5)), max(sgn * (HW + 1), sgn * (HW - T - 0.5)), LID_SCREWS['z'], LID_SCREWS['clear_r']))
    body = body - P.union(cuts)
    # lid: plate + lip + fan pocket + lip bosses, minus grille and side screw pilots
    lip_o = rr_poly(X0 + T + 0.15, X1 - T - 0.15, -HW + T + 0.15, HW - T - 0.15, max(R_PLAN - T, 0.5))
    lip_i = rr_poly(X0 + T + 0.15 + 1.4, X1 - T - 0.15 - 1.4, -HW + T + 0.15 + 1.4, HW - T - 0.15 - 1.4, 0.5)
    lid = prism(plan, Z_LID0, Z_LID1) + (prism(lip_o, Z_LID0 - 2.0, Z_LID0 + 0.01) - prism(lip_i, Z_LID0 - 3.0, Z_LID0 + 1.0))
    fx0, fx1 = FAN['cx'] - FAN['size'] / 2, FAN['cx'] + FAN['size'] / 2; fy0, fy1 = FAN['cy'] - FAN['size'] / 2, FAN['cy'] + FAN['size'] / 2
    g = 0.2; pk = []
    for (px, py, sx, sy) in ((fx1 + g, fy0 - g, 1, -1), (fx1 + g, fy1 + g, 1, 1), (fx0 - g, fy0 - g, -1, -1), (fx0 - g, fy1 + g, -1, 1)):
        # L corner outside the fan corner (px, py); (sx, sy) point away from the fan. Bar A: 1.6 thick along x outside the
        # fan's x face, 6 long inward along y; bar B: 1.6 thick along y outside the y face, 6 long inward along x. Both from
        # the fan bottom to the lid, plus a 0.6 snap lip under the fan corner. The rear corners get bar B only: the Dupont
        # wires rise behind the fan there (pins 7-12 at y -16.5..-10); a 3 mm rear stop between the pin 12 and pin 17
        # housings (y -8.5..-5.5) holds the fan at the back instead.
        if sx > 0:                                                                 # front corners: the front wall (0.2 away) is the x stop; snap lip only
            pk.append(P.box((px - 0.6, min(py, py - sy * 0.6), FAN['z0'] - 0.6), (px, max(py, py - sy * 0.6), FAN['z0'] - 0.1)))
        pk.append(P.box((min(px, px - sx * 6.0), min(py, py + sy * 1.6), FAN['z0'] - 0.6), (max(px, px - sx * 6.0), max(py, py + sy * 1.6), Z_LID0 + 0.01)))
    pk.append(P.box((fx0 - g - 1.6, -8.5, FAN['z0'] - 0.6), (fx0 - g, -5.5, Z_LID0 + 0.01)))              # rear stop
    pk.append(P.box((fx0 - g, -8.5, FAN['z0'] - 0.6), (fx0 - g + 0.6, -5.5, FAN['z0'] - 0.1)))           # its snap lip
    for sgn in (1, -1):
        y_lo, y_hi = sorted((sgn * b['y_in'], sgn * (HW - T - 0.15)))
        pk.append(P.box((b['x'][0], y_lo, b['z'][0]), (b['x'][1], y_hi, Z_LID0 + 0.01)))
    lid = lid + P.union(pk)
    gc = [P.box((x, GRILLE['y'][0], Z_LID0 - 1), (x + GRILLE['w'], GRILLE['y'][1], Z_LID1 + 1)) for x in GRILLE['xs']]
    gc.append(P.box((X1 - T - 0.15 - 1.5, fy0 - 1.0, Z_LID0 - 2.1), (X1, fy1 + 1.0, Z_LID0 - 0.01)))    # front lip notched over the fan
    for sgn in (1, -1):
        gc.append(cyl_y(LID_SCREWS['x'], min(sgn * (HW + 1), sgn * (b['y_in'] - 0.5)), max(sgn * (HW + 1), sgn * (b['y_in'] - 0.5)), LID_SCREWS['z'], LID_SCREWS['pilot_r']))
    lid = lid - P.union(gc)
    # body lip bosses were added to the body (walls); the lid lip bosses sit above them: remove the overlap from the body side
    # bought parts and envelopes
    parts = board_parts()
    soc_top = BOARD['z_under'] + SOC['top_h']
    cx, cy = BOARD['x0'] + np.mean(SOC['d']), BOARD['y0'] + np.mean(SOC['s'])
    hs = HS['size'] / 2
    env = {'heatsink': P.box((cx - hs, cy - hs, soc_top + HS['pad']), (cx + hs, cy + hs, soc_top + HS['pad'] + HS['h'])),
           'thermal_pad': P.box((cx - hs, cy - hs, soc_top), (cx + hs, cy + hs, soc_top + HS['pad'])),
           'fan': P.box((fx0, fy0, FAN['z0']), (fx1, fy1, FAN['z0'] + FAN['t'])),
           'dupont_housings': P.box((BOARD['x0'] + DUPONT['rows_d'][0] - DUPONT['half'], BOARD['y0'] + DUPONT['s'][0] - DUPONT['half'], BOARD['z_under'] + 1.6),
                                    (BOARD['x0'] + DUPONT['rows_d'][1] + DUPONT['half'], BOARD['y0'] + DUPONT['s'][1] + DUPONT['half'], BOARD['z_under'] + 1.6 + DUPONT['h'])),
           'antenna': P.box((X0 + T, ANT['y'][0], ANT['z'][0]), (X0 + T + ANT['t'], ANT['y'][1], ANT['z'][1])),
           'usb_c_plug': P.box((BOARD['x0'] + 30.0 + 1.6, BOARD['y0'] + 36.0, BOARD['z_under'] + 0.85), (X1 + 11.6, BOARD['y0'] + 57.8, BOARD['z_under'] + 8.85))}   # D-023: CableCreation B0194WSKOM 90-degree plug body, 17.8 along x from the socket face (the socket shells end 1.6 beyond the board edge, x -11.2; the tongue inside the socket is not modelled, the mated socket pair is classed in pair_classes.py), so 11.6 beyond the wall, 21.8 along +y from 1.1 below the tongue's -y edge (y 3.5 to 25.3), about 8 thick; the pigtail leaves at the +y end, where the head bundle comes down the left side of the neck
    fan_hub = cyl_z(FAN['cx'], FAN['cy'], FAN['z0'] - 0.01, FAN['z0'] + FAN['t'] + 0.01, FAN['hub_r'])
    out = {}
    for name, man in (('saddle_body', body), ('saddle_lid', lid)):
        mesh = stl_clean.clean(P.from_m(man)); mesh.export(OUT / f'{name}-world.stl')   # sliver triangles and pinch edges resolved: the release pipeline needs trimesh-watertight after vertex dedup
        pieces = [q for q in mesh.split(only_watertight=False) if abs(q.volume) > 0.05]
        out[name] = dict(watertight=bool(mesh.is_watertight), bodies=len(pieces), volume_mm3=round(float(mesh.volume), 1), bounds=np.round(mesh.bounds, 2).tolist())
    for name, man in env.items():
        mesh = P.from_m(man); mesh.export(OUT / f'{name}-world.stl'); out[name] = dict(bounds=np.round(mesh.bounds, 2).tolist())
    for name, mesh in parts.items():
        mesh.export(OUT / f'{name}-world.stl'); out[name] = dict(bounds=np.round(mesh.bounds, 2).tolist(), watertight=bool(mesh.is_watertight))
    # fit checks: saddle parts against each other, the bought parts and the robot at HOME (guide world parts, rear box)
    def ov(a, b):
        i = a ^ b; v = float(i.volume())
        return round(v, 3) if v <= 0 else dict(mm3=round(v, 3), bounds=np.round(P.from_m(i).bounds, 2).tolist())
    chk = {'body_lid': ov(body, lid)}
    for name, man in env.items():
        chk[f'body_{name}'] = ov(body, man); chk[f'lid_{name}'] = ov(lid, man)
    pcb = P.mesh_to_m(parts['a7z_pcb']); chk['body_pcb'] = ov(body, pcb); chk['lid_pcb'] = ov(lid, pcb)
    for n in ('soc_a733', 'ram', 'usb_c_otg_dp', 'usb_c_power', 'micro_hdmi', 'microsd_card', 'microsd_socket', 'csi_connector', 'pcie_fpc', 'uboot_button', 'fan_connector', 'ipex_socket'):
        chk[f'body_{n}'] = ov(body, P.mesh_to_m(parts[n]))
    smd = P.mesh_to_m(parts['underside_smd']) - P.union([cyl_z(BOARD['x0'] + d, BOARD['y0'] + s, 40.0, 50.0, 3.2) for s, d in HOLES])
    chk['body_underside_smd_outside_hole_keepouts'] = ov(body, smd)
    chk['fan_dupont'] = ov(env['fan'], env['dupont_housings']); chk['fanhub_heatsink'] = ov(fan_hub, env['heatsink'])
    chk['gap_fan_to_heatsink_mm'] = round(FAN['z0'] - (soc_top + HS['pad'] + HS['h']), 2)
    chk['gap_fan_to_dupont_mm'] = round(FAN['z0'] - (BOARD['z_under'] + 1.6 + DUPONT['h']), 2)
    head_top = seat_top + 1.6                                                 # ISO 7045 M2 pan head k max 1.6
    chk['roof_screw_seat_top_z'] = round(seat_top, 2); chk['roof_screw_head_top_z'] = round(head_top, 2)
    chk['gap_roof_screw_head_to_microsd_socket_mm'] = round(float(parts['microsd_socket'].bounds[0, 2]) - head_top, 2)
    chk['gap_roof_screw_head_to_underside_smd_mm'] = round(float(parts['underside_smd'].bounds[0, 2]) - head_top, 2)
    robot = {}
    for n in ('shell_left', 'shell_right', 'rear_pack', 'head_bottom', 'head_cap', 'jaw_frame', 'imu_board', 'openrb-board-upright', 'clip_torso', 'neck_pitch_ring'):
        f = WORLD / f'{n}.stl'
        if f.exists():
            robot[n] = ov(body, P.mesh_to_m(trimesh.load(str(f), force='mesh')))
    BP = MS / 'guide/print/back-plate'
    for n in ('rear_frame', 'rear_lid'):
        robot[n] = ov(body, P.mesh_to_m(trimesh.load(str(BP / f'{n}-world.stl'), force='mesh')))
    chk['body_vs_robot_overlap_mm3'] = robot
    # screws (world): board M2 x 4 down the posts; roof M2 x 10; lid M2 x 6 sideways
    screws = [dict(id=f'SD-board-{i + 1:02d}', spec='M2 x 4 TAP', center=[round(BOARD['x0'] + d, 2), round(BOARD['y0'] + s, 2), round(BOARD['z_under'] + 1.6, 2)], axis=[0, 0, -1], into='saddle_body post') for i, (s, d) in enumerate(HOLES)]
    screws += [dict(id=f'S-shell_pack-{i + 1:02d}', spec='M2 x 10 TAP (was M2 x 6)', center=[x, y, 44.0], axis=[0, 0, -1], through=['saddle_body', 'shell'], into='rear_pack shoulder bar') for i, (x, y) in enumerate(ROOF_SCREWS)]
    screws += [dict(id=f'SD-lid-{i + 1:02d}', spec='M2 x 6 TAP', center=[LID_SCREWS['x'], round(sgn * HW, 2), LID_SCREWS['z']], axis=[0, -sgn, 0], through=['saddle_body wall'], into='saddle_lid lip boss') for i, sgn in enumerate((1, -1))]
    R = dict(params=dict(T=T, CLR=CLR, ZU=ZU, X0=X0, X1=X1, HW=HW, R_PLAN=R_PLAN, Z_LID0=Z_LID0, Z_LID1=Z_LID1, BOARD=BOARD, HOLES=HOLES, ROOF_SCREWS=ROOF_SCREWS, FLOOR_CUT=FLOOR_CUT,
                         SOC=SOC, HS=HS, FAN=FAN, DUPONT=DUPONT, SIDE_SLOTS=SIDE_SLOTS, FRONT_SLOTS=FRONT_SLOTS, CARD_SLOT=CARD_SLOT, PLUG_NOTCH=PLUG_NOTCH, LID_SCREWS=LID_SCREWS, GRILLE=GRILLE, ANT=ANT),
             parts=out, checks=chk, screws=screws,
             # wall_check.py allowances (release part rows): the wall feet are wedges where a vertical outer face meets the
             # shell's sloping roof seat (rear slope about 50 deg, flank edges); a seated part cannot be thicker there.
             thinWallAllowances=dict(saddle_body=[dict(bbox=[[X0 - 0.1, -HW - 0.1, 26.0], [X0 + 2.0, HW + 0.1, 38.0]], minMm=0.1, reason='rear wall foot: vertical outer face meeting the shell roof seat that falls about 1.2 mm per mm towards the rear (shell z 35 at x -45, 38 at x -42); the seat follows the shell, so the foot is a wedge by geometry'),
                                                  dict(bbox=[[X0 - 0.1, HW - 4.0, 26.0], [X1 + 0.1, HW + 0.1, 38.0]], minMm=0.1, reason='+y wall foot on the shell flank edge: same wedge where the side wall meets the sloping roof edge'),
                                                  dict(bbox=[[X0 - 0.1, -HW - 0.1, 26.0], [X1 + 0.1, -HW + 4.0, 38.0]], minMm=0.1, reason='-y wall foot on the shell flank edge: same wedge where the side wall meets the sloping roof edge')]),
             roof=dict(z_at_centre=float(np.nanmax(Z)), z_min_under_floor=float(np.nanmin(Zf)), z_under_roof_screws=round(seat_top - 0.2 - T - CLR, 2), grid_step=STEP))
    (OUT / 'build.json').write_text(json.dumps(R, indent=1) + '\n')
    # header pins in the saddle pose (world, mm): pin n -> top of the pin (PCB top + 8.5: 2.5 plastic + 6 pin); even pins on
    # the edge row (d 2.23, nearer the rear wall), odd pins on the inner row (d 4.77); pin 1 at the -y end
    pins = {n: [round(BOARD['x0'] + (DUPONT['rows_d'][0] if n % 2 == 0 else DUPONT['rows_d'][1]), 3), round(BOARD['y0'] + DUPONT['s'][0] + ((n - 1) // 2) * 2.54, 3), round(BOARD['z_under'] + 1.6 + 8.5, 2)] for n in range(1, 41)}
    (OUT / 'pins.json').write_text(json.dumps(dict(frame='guide world mm (x forward, y left, z up)', pinTop=pins, housingBounds=out['dupont_housings']['bounds'],
                                                   fanConnectorJ6=out['fan_connector']['bounds'], floorCut=dict(x=[FLOOR_CUT['x0'], FLOOR_CUT['x1']], y=[-FLOOR_CUT['hy'], FLOOR_CUT['hy']], zBelowBoard=BOARD['z_under']),
                                                   boardFrontEdgeX=BOARD['x0'] + 30.0, frontWallInnerX=X1 - T, fan=out['fan']['bounds'], lidUndersideZ=Z_LID0), indent=1) + '\n')
    print(json.dumps(dict(parts={k: v for k, v in out.items() if k.startswith('saddle')}, checks=chk), indent=1))


if __name__ == '__main__':
    build()
