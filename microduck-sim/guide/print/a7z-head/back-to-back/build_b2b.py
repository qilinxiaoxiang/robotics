"""Candidate (not released): Radxa Cubie A7Z back to back with the camera, Radxa Heatsink 6530B behind it.

Pose: the board stands vertical (normal along -x), turned so its component side, SoC and 40-pin header face the rear and the
header runs along the top edge; the underside (CSI socket, microSD) faces the camera. Rear (component) face at x = XC, top
edge at z = ZTOP, pin-1 end at y = +32.5 as today. Fit sweep and the choice of XC: ../../../firmware/mac/
investigation-20261021/cooling/flip-6530b/README.md.

6530B envelope (Radxa product page: 65 x 30 x 11.5 mm, four CM2x4x4 screws into the heatsink through the board holes;
shape from Radxa's photos): body over the whole board except the header strip, corner legs over the header strip ends,
blower fan at the pin-1 end with its inlet facing away from the board. Dimensions to be re-measured on the part.

Mounting: three ears printed with the head cap reach from the side walls into the gap in front of the board, at the two
top holes and the bottom -Y hole. An M2 x 8 goes from the front through the ear and the board into the heatsink's own
thread (2.4 mm bite, the same as Radxa's CM2x4x4 through a 1.6 mm board). The bottom +Y hole takes Radxa's own CM2x4x4
from the board underside and no ear: the camera socket and its ribbon sit right above it. The cap prints roof down, so the
top ears are filled up into the roof and the bottom ear carries a 45 degree rib in front of the microSD card; none of
them prints on support. The old rails behind the board are cut back to the heatsink keep-out. The cap wire clip
(clip_cap) is dropped: the bundle now reaches the rear-facing header directly and no longer crosses the board's top edge.
Radxa's close-up of the fan connection shows the heatsink end over the pin-1 corner open towards the board end, so the
antenna plug and the fan lead leave the +Y end; the fan lead loops outside that end.

Board frame: s from the pin-1 end (mm), d from the header edge (mm, now downward), h above the PCB underside towards the
component side (mm, now rearward). Outputs (this folder): head_cap_b2b-world.stl, parts/*.stl, checks.json.
"""
import base64
import json
import math
import os
import sys
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
GUIDE = HERE.parents[2]
RUN = HERE / os.environ.get('B2B_RUN', '.')
OUT = RUN / 'parts'
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HERE.parent))
import build_a7z_head as A          # TOP / BOTTOM component boxes, HOLES, T (measured on Radxa's photos)

# Top edge 1.5 mm below the fit sweep's 144.6: the heatsink's corner fin blocks sit in the roof's inner corner curve, and
# z 143.1 with 0.6 mm round those two blocks leaves 1.32 mm of shell behind them while the board, heatsink and the PCIe
# socket keep 1.82, 1.72 and 0.64 mm above the head floor (height trade: README.md).
XC, ZTOP, Y1, T = 68.0, float(os.environ.get('B2B_ZTOP', 143.1)), 32.5, A.T
LEG_CLEAR = 0.6
SLIDE_CLEAR = 0.5                                              # round the corner blocks along their slide only
SLIDE = 2.0                                                    # behind final while lowered: the microSD card (1.5 mm proud) clears the ear pad by 0.5
EAR_T, EAR_RELIEF, EAR_PAD_R, EAR_H = 4.0, 1.3, 2.9, 8.0      # ear thickness, relief over underside SMD, pad radius, height
EAR_HOLES = {(3.5, 3.5): 'roof', (61.5, 3.5): 'roof', (61.5, 26.5): 'rib'}    # (s, d) -> how the ear prints without support
KIT_SCREW_HOLE = (3.5, 26.5)                                   # Radxa CM2x4x4 from the underside, no ear
RIB_X0 = 72.1                                                  # bottom ear rib starts in front of the microSD keep-out
CLOSE_POST = ((75.5, 39.5), 4.5)                               # head_bottom post under each side boss (top z 114.3), keep-out
SCREW_L, SCREW_HEAD = 8.0, (1.9, 1.6)                          # M2 x 8 cap head: radius, height
CLEAR_HOLE = 1.2                                               # M2 clearance hole radius in the ear
HS = dict(h=11.5, body_d=(6.0, 30.0), leg_s=((0.0, 7.0), (58.0, 65.0)), fan_s=(4.0, 27.0), fan_d=(7.0, 29.0), fan_gap=3.0)
JAW_PIVOT, JAW_AXIS, JAW_HI = np.array([26.1, 0.0, 118.6146]), np.array([0.0, 1.0, 0.0]), 27.0
# Air ducts (duct_concept.py): the rear is the cool side, the heatsink's fin tips and the front are the hot side.
# Shroud insert: a separate flat-printed plate behind the non-fan half of the fins, slid up into two rails on the right
# cheek after the Dupont plugs are on (they go onto the rear-facing header from behind, so a plate fixed in the cap
# would block them), held from below by the head floor when the head closes. Its rib along y 2.3..3.5 keeps the plenum
# off the fan inlet.
INSERT_X = (47.8, 49.0)                  # 2.5 mm behind the plug housings (x 51.5), 0.9 in front of jaw_support (x 46.9)
INSERT_Y1, FAN_RIB_Y, FAN_RIB_X1, FAN_RIB_TOP = 2.3, (2.3, 3.5), 56.0, 137.1
INSERT_GAP = 0.85                        # grown by 14 shifted copies: at least 0.5 mm in every direction
RAIL = dict(x=((46.4, 47.6), (49.2, 50.4)), z=(133.5, 140.5), depth=3.0)   # 0.2 mm each side of the insert edge; above
# the intake slots, below the R1 pad (z 141.5), the top 3 mm chamfered at 45 degrees (prints roof down)
PAD_GAP = 1.5                            # duct walls and the insert stay this far under the touch pads: foil runs over them
# Fixed in the cap: a left baffle behind the fan lead, an upper baffle over the plugs and the heatsink's +Y leg, and a
# short wall over the plugs at the fan rib's y, so hot air above the board cannot run back to the fan inlet.
LEFT_BAFFLE = dict(x=(55.8, 57.0), y0=35.0)        # x clear of the M pad (x <= 54.1) plus PAD_GAP: reaches the roof
UPPER_Z, F2 = 144.6, dict(x=(49.5, 57.0), y=(2.3, 3.5), z0=146.0)   # F2 leaves a 2.9 mm wire pass over the plug tops;
# under the M pad its top falls at 45 degrees from the baffle (x 55.8), so it prints from the baffle without support
SLOT_W, SLOT_RIB = 1.6, 1.2
EXHAUST_SLOTS = [(57.5 + i * (SLOT_W + SLOT_RIB), 117.0, 135.0) for i in range(4)]          # (x0, z0, z1), both cheeks
INTAKE_SLOTS = [(37.5, 121.5, 133.0), (40.3, 118.5, 133.0), (43.1, 116.5, 133.0), (45.9, 116.5, 133.0)]   # rim rises rearward


def w(s, d, h):
    """Board frame -> robot frame for the back-to-back pose."""
    return np.array([XC + T - h, Y1 - s, ZTOP - d], dtype=float)


def obox(s0, s1, d0, d1, h0, h1):
    c = np.array([w(s, d, h) for s in (s0, s1) for d in (d0, d1) for h in (h0, h1)])
    lo, hi = c.min(0), c.max(0)
    b = trimesh.creation.box(extents=hi - lo); b.apply_translation((lo + hi) / 2)
    return b


def cyl_x(y, z, x0, x1, r):
    return trimesh.creation.cylinder(radius=r, segment=[[x0, y, z], [x1, y, z]], sections=48)


def U(ms):
    return trimesh.boolean.union(ms, engine='manifold')


def guide_parts():
    d = json.loads((GUIDE / 'data/guide-data.json').read_text())
    out = {}
    for p in d['parts']:
        k = p['key']
        if k == 'pi' or k.startswith('head_pi_') or k in ('camera_ribbon', 'antenna_coax', 'antenna_ipex', 'clip_cap'):
            continue
        b = p['bounds']; lo, hi = b if isinstance(b[0], list) else (b[:3], b[3:])
        if not (hi[0] > -35 and lo[0] < 95 and hi[1] > -48 and lo[1] < 48 and hi[2] > 95 and lo[2] < 162):
            continue
        V = np.frombuffer(base64.b64decode(p['positionB64']), dtype=np.float32).reshape(-1, 3)
        I = np.frombuffer(base64.b64decode(p['indexB64']), dtype=np.uint32).reshape(-1, 3) if p.get('indexB64') else np.arange(len(V)).reshape(-1, 3)
        out[k] = trimesh.Trimesh(V.astype(float), I, process=True)
    # The camera mesh carries the first part of its ribbon on the V1.17 route (back to x 70 along y 33); the ribbon is
    # rerouted here (camera_ribbon_b2b), so only the rigid camera (board, lens, connector: |y| <= 17, x >= 72) is fixed.
    out['camera_board'] = out['camera_board'].intersection(trimesh.creation.box(bounds=[[72.0, -17.0, 100.0], [95.0, 17.0, 160.0]]),
                                                           engine='manifold')
    return out


def board_parts():
    p = {}
    pcb = obox(0, 65, 0, 30, 0, T)
    holes = [cyl_x(Y1 - s, ZTOP - d, XC - 1, XC + T + 1, 1.375) for s, d in A.HOLES]
    p['a7z_pcb'] = pcb.difference(U(holes), engine='manifold')
    for k, (s0, s1, d0, d1, hh) in A.TOP.items():
        p['a7z_' + k] = obox(s0, s1, d0, d1, T, T + hh)
    for k, (s0, s1, d0, d1, hh) in A.BOTTOM.items():
        p['a7z_' + k] = obox(s0, s1, d0, d1, -hh, 0)
    p['a7z_header'] = obox(7.0, 59.0, 0.0, 5.0, T, T + 8.5)                       # 2 x 20 pins, 8.5 mm above the board
    p['dupont_plugs'] = obox(7.0, 59.0, 0.0, 5.0, T + 2.5, T + 17.0)             # plug housings plus the wire bend
    p['header_tails'] = obox(7.6, 57.4, 0.0, 5.0, -2.0, 0.0)                     # solder tails: pins at s 8.37..56.63, +-0.75
    p['fan_lead_loop'] = obox(-1.5, 0.0, 7.0, 24.0, T, T + HS['h'])              # fan lead tucked along the end into J6
    r0, r1 = ZTOP - A.RIB_D[1], ZTOP - A.RIB_D[0]                               # 12 mm ribbon centred on the CSI socket
    p['camera_ribbon_b2b'] = U([trimesh.creation.box(bounds=[[70.6, 33.0, r0], [78.0, 33.3, r1]]),      # back from the camera
                                trimesh.creation.box(bounds=[[70.3, 31.5, r0], [70.6, 33.3, r1]])])     # turn into the socket
    s_, d_ = KIT_SCREW_HOLE
    p['kit_screw_head'] = cyl_x(Y1 - s_, ZTOP - d_, XC + T, XC + T + 1.6, 1.9)
    # 6530B
    b0, b1 = HS['body_d']
    hs = [obox(0, 65, b0, b1, T, T + HS['h'])] + [obox(s0, s1, 0, b0, T, T + HS['h']) for s0, s1 in HS['leg_s']]
    p['heatsink_6530b'] = U(hs)
    p['_hs_body'], p['_hs_leg0'], p['_hs_leg1'] = hs
    p['fan_inlet_zone'] = obox(HS['fan_s'][0], HS['fan_s'][1], HS['fan_d'][0], HS['fan_d'][1], T + HS['h'], T + HS['h'] + HS['fan_gap'])
    return p


def ears(cap):
    """One ear per EAR_HOLES entry: a 4 mm plate in front of the board from the edge of its pad to the side wall, its
    board-facing side relieved 1.3 mm except a 2.9 mm radius pad round the hole, with a 2.4 mm clearance hole. A top ear is
    filled from its plate up to the roof; the bottom ear gets a 45 degree rib from the plate's inner end up to the wall,
    in front of the microSD keep-out. Everything is clipped to the cap's convex hull so nothing pokes out of the shell."""
    hull = inset_hull(cap, 0.6)                          # stays inside the real outer surface, still bonds into the shell
    out, screws, info = [], [], []
    for (s, d), kind in EAR_HOLES.items():
        y, z = Y1 - s, ZTOP - d
        sgn = 1.0 if y > 0 else -1.0
        x_front = XC + T                                  # board underside (front face)
        xm = x_front + EAR_T / 2
        loc, _, _ = cap.ray.intersects_location([[xm, 0.0, z]], [[0, sgn, 0]], multiple_hits=True)
        wall = min(loc[:, 1] * sgn) * sgn                    # first cap surface outward from the centre line
        inner = y - sgn * EAR_PAD_R
        y0, y1 = sorted((inner, wall + sgn * 3.0))
        xa, xb = x_front + EAR_RELIEF, x_front + EAR_T
        # Top ears start at the pad edge below the hole, above the camera ribbon's new line (ribbon centred on the CSI
        # socket, top z = ZTOP - 9.15). The bottom ear starts at its pad edge, 2.4 mm above the head_bottom floor (z 111.3)
        # and 0.9 mm above its rim step at the wall (z 112.8); the closing-screw post under the side boss (z <= 114.3) is
        # cut out of it below.
        z0, z1 = (z - EAR_PAD_R, cap.bounds[1][2]) if kind == 'roof' else (z - EAR_PAD_R, z + EAR_H / 2)
        body = [trimesh.creation.box(bounds=[[xa, y0, z0], [xb, y1, z1]])]
        if kind == 'rib':
            L = abs(wall - inner) + 3.0
            tri = np.array([[inner, z + EAR_H / 2], [inner + sgn * L, z + EAR_H / 2], [inner + sgn * L, z + EAR_H / 2 + L]])
            prof = trimesh.path.polygons.Polygon(tri if sgn > 0 else tri[::-1])
            rib = trimesh.creation.extrude_polygon(prof, xb - RIB_X0)          # in (y, z), extruded along +local z
            M = np.array([[0, 0, 1, RIB_X0], [1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]], float)   # local (y, z, x) -> world
            rib.apply_transform(M)
            body.append(rib)
        pad = cyl_x(y, z, x_front, xa + 0.2, EAR_PAD_R)
        ear = U(body + [pad]).intersection(hull, engine='manifold')
        ear = ear.difference(cyl_x(y, z, x_front - 1, x_front + EAR_T + 1, CLEAR_HOLE), engine='manifold')
        if kind == 'rib':
            post = trimesh.creation.cylinder(radius=CLOSE_POST[1], segment=[[CLOSE_POST[0][0], sgn * CLOSE_POST[0][1], 110.0],
                                                                             [CLOSE_POST[0][0], sgn * CLOSE_POST[0][1], 115.3]])
            ear = ear.difference(post, engine='manifold')
        out.append(ear)
        head = cyl_x(y, z, xb, xb + SCREW_HEAD[1], SCREW_HEAD[0])
        shank = cyl_x(y, z, xb - SCREW_L, xb, 0.95)
        screws.append(U([head, shank]))
        info.append({'hole_s_d': [s, d], 'kind': kind, 'y': round(y, 2), 'z': round(z, 2), 'wall_y': round(float(wall), 2),
                     'arm_length_mm': round(abs(wall - inner), 2), 'screw_tip_x': round(xb - SCREW_L, 2),
                     'thread_bite_mm': round(XC - (xb - SCREW_L), 2)})
    return out, screws, info


def rounded_grow(m, g):
    """Every point within g of a convex part: the hull of a sphere at each vertex (a box grown with round edges)."""
    sph = trimesh.creation.icosphere(subdivisions=2, radius=g / math.cos(math.radians(20)))   # faceted sphere covers g
    pts = (m.vertices[:, None, :] + sph.vertices[None, :, :]).reshape(-1, 3)
    return trimesh.convex.convex_hull(pts)


def inset_hull(m, t):
    """The cap's convex hull moved inward by t on every face: material outside it is the shell (or nearer the outside)."""
    from scipy.spatial import HalfspaceIntersection
    h = m.convex_hull
    hs = np.hstack([h.face_normals, -(np.einsum('ij,ij->i', h.face_normals, h.triangles[:, 0])[:, None] - t)])
    pts = np.unique(np.round(HalfspaceIntersection(hs, h.centroid).intersections, 2), axis=0)   # merge near-duplicates
    out = trimesh.convex.convex_hull(pts)
    assert out.is_volume
    return out


def old_rails(cap):
    """The two V1.9/V1.17 board rails: vertical webs at each board end, from the side wall in to |y| 26, with the old Pi
    pilots. In this pose nothing rests on them. Everything of the cap in that zone more than 2.5 mm inside the hull goes;
    the shell (about 2 mm) stays whole."""
    zone = [trimesh.creation.box(bounds=[[48.0, 23.0, 112.0], [69.6, 50.0, 152.0]]),
            trimesh.creation.box(bounds=[[48.0, -50.0, 112.0], [69.6, -23.0, 152.0]])]
    return U(zone).intersection(inset_hull(cap, 2.5), engine='manifold')


def coax_route():
    """Antenna cable from the IPEX plug on the rear face out of the +Y board end, up past the fan lead, over the top edge
    above the heatsink leg and forward to the antenna's cable end on the roof (build_a7z_head.py antenna sheet)."""
    zi = ZTOP - A.IPEX_C[1]
    pts = np.array([[65.8, Y1 - A.IPEX_C[0], zi], [65.8, 34.0, zi], [65.8, 34.0, ZTOP - 5.0], [65.8, 31.0, ZTOP + 0.9],
                    [66.5, 22.0, ZTOP + 1.6], [70.5, 20.5, 150.9]])
    segs = [trimesh.creation.cylinder(radius=0.55, segment=[a, b], sections=16) for a, b in zip(pts[:-1], pts[1:])]
    segs += [trimesh.creation.icosphere(radius=0.55, subdivisions=1).apply_translation(q) for q in pts[1:-1]]
    return U(segs), float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())


def wall_checks(cap, new_cap, keep_u, ear_list):
    """Thickness behind every face the keep-out cut made, holes through the outer shell, ear material outside the shell."""
    out = {}
    pts, fi = trimesh.sample.sample_surface_even(new_cap, 80000)
    on_cut = trimesh.proximity.closest_point(keep_u, pts)[1] < 0.02
    p, n = pts[on_cut], new_cap.face_normals[fi[on_cut]]
    loc, ri, _ = new_cap.ray.intersects_location(p - n * 0.02, -n, multiple_hits=False)
    th = np.full(len(p), np.inf); th[ri] = np.linalg.norm(loc - p[ri], axis=1)
    hull = cap.convex_hull
    shell = trimesh.proximity.closest_point(hull, p)[1]          # cut face to the outside of the cap
    thin = shell < 1.2
    out['cutFaceSamples'] = int(len(p)); out['shellBehindCutMin_mm'] = round(float(shell.min()), 2)
    out['shellBehindCutBelow1p2'] = int(thin.sum()); out['shellThinWhere'] = np.round(p[thin][:12], 1).tolist()
    feather = th < 0.6                                             # where a cut plane meets a curved inner wall
    out['featherEdgeSamples'] = int(feather.sum())
    q, qf = trimesh.sample.sample_surface_even(cap, 120000)
    gone = keep_u.contains(q)
    outer = trimesh.proximity.closest_point(hull, q[gone])[1] < 0.3
    out['removedSurfaceSamples'] = int(gone.sum()); out['outerShellBreaches'] = int(outer.sum())
    out['breachWhere'] = np.round(q[gone][outer][:12], 1).tolist()
    esc = 0; tot = 0
    for e in ear_list:
        ep = e.sample(3000); tot += len(ep)
        sg = np.sign(ep[:, 1:2]); dirs = [np.hstack([np.zeros_like(sg), sg, np.zeros_like(sg)]), np.tile([0, 0, 1.0], (len(ep), 1))]
        inside = np.ones(len(ep), bool)
        for dv in dirs:
            inside &= cap.ray.intersects_any(ep, dv)
        esc += int((~inside).sum()); escp = ep[~inside] if esc else np.zeros((0, 3))
        if len(escp): out.setdefault('earOutsideWhere', []).extend(np.round(escp[:6], 1).tolist())
    out['earSamples'] = tot; out['earSamplesOutsideShell'] = esc
    rem = cap.difference(new_cap, engine='manifold')
    out['removedPieces'] = [{'volume_mm3': round(float(b.volume), 1), 'bounds': np.round(b.bounds, 1).tolist()}
                            for b in sorted(rem.split(only_watertight=False), key=lambda b: -b.volume) if b.volume > 2.0]
    return out


def assembly_path(new_cap, bp, screws):
    """Board + heatsink (one unit, kit screw in, no plugs yet) go into the cap upside down on the bench: lowered along the cap's axis
    SLIDE behind the final pose, then slid forward onto the ear pads. Each step is checked against the new cap; then a
    straight driver line from each M2 x 8 head forward out of the face opening (the face panel goes on last)."""
    keys = ('heatsink_6530b', 'a7z_pcb', 'header_tails', 'fan_lead_loop', 'kit_screw_head', 'a7z_header')  # plugs go on after
    unit = U([bp[k] for k in keys] + [bp['a7z_' + k] for k in A.BOTTOM])
    worst = []
    for dz in np.arange(-36.0, 0.01, 2.0):
        m = unit.copy(); m.apply_translation([-SLIDE, 0, dz]); worst.append(['lower', float(dz), gap(m, new_cap)])
    for dx in np.arange(-SLIDE, 0.01, 0.5):
        m = unit.copy(); m.apply_translation([dx, 0, 0]); worst.append(['slide', float(dx), gap(m, new_cap)])
    driver = []
    for sc in screws:
        c = sc.bounds.mean(0); c[0] = sc.bounds[1][0]
        hit = new_cap.ray.intersects_any([c + [0.05, 0, 0]], [[1.0, 0, 0]])[0]
        driver.append({'y': round(float(c[1]), 1), 'z': round(float(c[2]), 1), 'blocked': bool(hit)})
    return {'minGapLowering_mm': min(w[2] for w in worst if w[0] == 'lower'),
            'minGapSlide_mm': min(w[2] for w in worst if w[0] == 'slide' and w[1] < -0.01),
            'steps': worst, 'driverLines': driver}


def gap(a, b):
    """Negative overlap volume (mm3) if the two solids overlap, else the minimum surface distance (mm, sampled). Guide
    meshes that are not closed solids are tested by points: b's vertices inside a, a's samples inside b if b is closed."""
    if a.is_volume and b.is_volume:
        i = trimesh.boolean.intersection([a, b], engine='manifold')
        if not i.is_empty and i.volume > 1e-3:
            return -round(float(i.volume), 3)
    else:
        bv = b.vertices[np.all((b.vertices > a.bounds[0] - 0.1) & (b.vertices < a.bounds[1] + 0.1), axis=1)]
        if len(bv) and a.contains(bv).any():
            return -1.0                                         # overlap, volume unknown
        if b.is_watertight and b.contains(a.sample(3000)).any():
            return -1.0
    pts = np.vstack([a.sample(4000), a.vertices])
    return round(float(trimesh.proximity.closest_point(b, pts)[1].min()), 2)


PADS = ('touch_pad_m', 'touch_pad_l1', 'touch_pad_r1', 'touch_pad_l2', 'touch_pad_r2')


def pad_zone(cap):
    """Where foil goes: everything within PAD_GAP of the cap's inner surface (the pads are 0.1 mm tape on it) inside each
    pad's outline grown by PAD_GAP. Walls and the insert stay out, so the foil runs over them."""
    near = grow(cap, PAD_GAP + 0.2)
    boxes = [trimesh.creation.box(bounds=[solid(k).bounds[0] - PAD_GAP, solid(k).bounds[1] + PAD_GAP]) for k in PADS]
    return near.intersection(U(boxes), engine='manifold')


def grow_dense(m, g, step=0.5):
    """grow() for thin sheets (the touch pads, 0.1 mm): copies on a grid of shifts inside radius g, so no gaps."""
    r = np.arange(-g, g + 1e-6, step)
    sh = [np.array(v) for v in np.array(np.meshgrid(r, r, r)).T.reshape(-1, 3) if np.linalg.norm(v) <= g + 1e-6]
    return U([m.copy().apply_translation(v) for v in sh])


def grow(m, g):
    """m grown by about g on every side: the union of 14 shifted copies (axes and diagonals). Fine for clearances."""
    dirs = [d for d in np.vstack([np.eye(3), -np.eye(3), np.array(np.meshgrid(*[[-1, 1]] * 3)).T.reshape(-1, 3) / math.sqrt(3)])]
    return U([m.copy().apply_translation(g * d) for d in dirs] + [m])


def solid(key):
    sys.path.insert(0, str(GUIDE / 'content' / 'interference-audit'))
    from ia_lib import load_solid
    v, f = load_solid(key)
    return trimesh.Trimesh(v, f, process=False)


def slot_cuts():
    """Through-wall slot boxes on both cheeks: exhaust beside the heatsink ends, intake behind the shroud."""
    boxes, info = [], []
    for kind, slots in (('exhaust', EXHAUST_SLOTS), ('intake', INTAKE_SLOTS)):
        for x0, z0, z1 in slots:
            for sgn in (1.0, -1.0):
                y0, y1 = sorted((sgn * 33.0, sgn * 50.0))
                boxes.append(trimesh.creation.box(bounds=[[x0, y0, z0], [x0 + SLOT_W, y1, z1]]))
                info.append({'kind': kind, 'side': '+y' if sgn > 0 else '-y', 'x': [x0, x0 + SLOT_W], 'z': [z0, z1],
                             'open_mm2': round(SLOT_W * (z1 - z0), 1)})
    return boxes, info


def fixed_duct_walls(cap):
    """Duct walls printed with the cap (roof down: each hangs from the roof or a wall, bottoms face the bed side up)."""
    hull = inset_hull(cap, 0.6)
    top = cap.bounds[1][2] + 1
    parts = {
        'left_baffle': trimesh.creation.box(bounds=[[LEFT_BAFFLE['x'][0], LEFT_BAFFLE['y0'], 100.0], [LEFT_BAFFLE['x'][1], 50.0, top]]),
        'upper_baffle': trimesh.creation.box(bounds=[[LEFT_BAFFLE['x'][0], F2['y'][1], UPPER_Z], [LEFT_BAFFLE['x'][1], 50.0, top]]),
        'plug_wall': trimesh.creation.box(bounds=[[F2['x'][0], F2['y'][0], F2['z0']], [F2['x'][1], F2['y'][1], top]]),
    }
    crop = cap.intersection(trimesh.creation.box(bounds=[[44.0, -50.0, 128.0], [52.0, -20.0, 146.0]]), engine='manifold')
    near_wall = grow(crop, RAIL['depth'])                 # within 3 mm of the right cheek's inner surface
    loc, _, _ = cap.ray.intersects_location([[np.mean(RAIL['x'][0]), 0.0, RAIL['z'][1]]], [[0, -1.0, 0]])
    y_top = float(max(loc[:, 1]))                         # inner wall at the rail top
    for i, (x0, x1) in enumerate(RAIL['x']):           # rails on the right cheek, either side of the insert edge
        b = trimesh.creation.box(bounds=[[x0, -50.0, RAIL['z'][0]], [x1, -20.0, RAIL['z'][1]]]).intersection(near_wall, engine='manifold')
        n = -np.array([0.0, 1.0, 1.0]) / math.sqrt(2)      # keep y + z <= y_top + z_top: 45 degree top, no overhang
        parts[f'rail_{i}'] = trimesh.intersections.slice_mesh_plane(b, n, [0.0, y_top, RAIL['z'][1]], cap=True)
    n = np.array([1.0, 0.0, -1.0]) / math.sqrt(2)          # plug wall: keep x - z >= x0 - z0 (45 degree top under the pad)
    m_pad = solid('touch_pad_m')
    parts['plug_wall'] = trimesh.intersections.slice_mesh_plane(parts['plug_wall'], n, [LEFT_BAFFLE['x'][0], 0.0,
                                                                m_pad.bounds[0][2] - PAD_GAP], cap=True)
    pads = pad_zone(cap)
    out = {}
    for k, b in parts.items():
        out[k] = b.intersection(hull, engine='manifold').difference(pads, engine='manifold')
    return out


def shroud_insert(cap, unit_parts):
    """The separate shroud insert: plate INSERT_X from the right wall to y INSERT_Y1, roof to floor, 0.5 mm off the
    cap, head floor, jaw_support and clip_head (a notch open at the bottom lets clip_head rise into it as the head
    closes), plus the fan rib. Printed flat on its rear face."""
    plate = trimesh.creation.box(bounds=[[INSERT_X[0], -50.0, 100.0], [INSERT_X[1], INSERT_Y1, 165.0]])
    rib = trimesh.creation.box(bounds=[[INSERT_X[0], FAN_RIB_Y[0], 100.0], [FAN_RIB_X1, FAN_RIB_Y[1], FAN_RIB_TOP]])
    body = U([plate, rib])
    keep = [grow(cap, INSERT_GAP), grow(solid('head_bottom'), INSERT_GAP), grow(solid('jaw_support'), INSERT_GAP)]
    # clip_head rises into place as the head closes: cut its shadow (grown, swept down), plus the wire channel between
    # its post and tab (y -26..-17.6), so a bundle through the clip is not pinched. Elsewhere the insert stays whole.
    clip = grow(solid('clip_head'), INSERT_GAP)
    keep.append(U([clip.copy().apply_translation([0, 0, -dz]) for dz in np.arange(0.0, 20.01, 1.0)]))
    keep.append(trimesh.creation.box(bounds=[[INSERT_X[0] - 1, -26.0, 90.0], [INSERT_X[1] + 1, -17.6, 124.9]]))
    keep += [grow(m, INSERT_GAP) for m in unit_parts]
    keep.append(pad_zone(cap))
    keep.append(trimesh.creation.box(bounds=[[40.0, -50.0, 90.0], [60.0, 10.0, 111.8]]))   # nothing below the head floor
    body = body.difference(U(keep), engine='manifold')
    pieces = body.split(only_watertight=False)
    ref = np.array([[INSERT_X[0] + 0.6, -10.0, 128.0]])
    ins = [p for p in pieces if p.contains(ref)[0]]
    assert ins, 'insert reference point lost'
    return ins[0]


def overhangs(m, region_boxes, limit=45.0):
    """Faces of m inside the given boxes that face the bed side down when the cap prints roof down (robot +z steeper
    than limit from vertical): their area in mm2 per box."""
    n = m.face_normals; c = m.triangles_center; a = m.area_faces
    bad = n[:, 2] > math.cos(math.radians(limit))
    out = {}
    for k, b in region_boxes.items():
        lo, hi = b.bounds
        inb = np.all((c > lo - 0.05) & (c < hi + 0.05), axis=1)
        out[k] = {'area_mm2': round(float(a[bad & inb].sum()), 2), 'widest_mm': None}
    return out


def tick(label, _t=[None]):
    import time
    now = time.time()
    if _t[0] is not None:
        print(f'[{label}] {now - _t[0]:.1f} s', file=sys.stderr, flush=True)
    _t[0] = now


def duct_checks(new_cap, insert, walls, wall_info, slot_info, bp, world):
    tick('duct checks start')
    out = {'walls': wall_info, 'slots': slot_info}
    out['slotOpen_mm2'] = {k: round(sum(si['open_mm2'] for si in slot_info if si['kind'] == k and si['side'] == side), 1)
                           for k in ('exhaust', 'intake') for side in ('+y',)}
    out['slotRemovedPerSlot_mm3'] = [min(si['removed_mm3'] for si in slot_info), max(si['removed_mm3'] for si in slot_info)]
    out['insert'] = {'volume_mm3': round(float(insert.volume), 1), 'bounds': np.round(insert.bounds, 1).tolist(),
                     'bodies': int(insert.body_count), 'is_volume': bool(insert.is_volume)}
    # clearances at final pose
    fixed = {k: m for k, m in world.items() if k not in ('jaw_frame',)}
    near = lambda a, b: np.all(a.bounds[0] < b.bounds[1] + 3) and np.all(b.bounds[0] < a.bounds[1] + 3)
    row = {}
    for o, om in list(fixed.items()) + [('head_cap(new)', new_cap)] + [(k, bp[k]) for k in ('heatsink_6530b', 'dupont_plugs', 'fan_lead_loop', 'a7z_header', 'a7z_pcb')]:
        if near(insert, om):
            row[o] = gap(insert, om)
    out['insertPairs'] = dict(sorted(row.items(), key=lambda t: t[1])[:8])
    wu = U(list(walls.values()))
    row = {}
    for o, om in list(fixed.items()) + [(k, bp[k]) for k in ('heatsink_6530b', 'dupont_plugs', 'fan_lead_loop', 'a7z_header', 'a7z_pcb')]:
        if near(wu, om):
            row[o] = gap(wu, om)
    out['wallPairs'] = dict(sorted(row.items(), key=lambda t: t[1])[:8])
    # Dupont plugs pushed onto the rear-facing header from 8 mm behind, insert not yet in
    out['plugInsertMinGap_mm'] = min(gap(bp['dupont_plugs'].copy().apply_translation([-dx, 0, 0]), new_cap) for dx in np.arange(0, 8.01, 2.0))
    # Insert slid up into its rails (cap roof down) after the plugs: against the cap and the board unit with plugs
    unit = U([bp[k] for k in ('heatsink_6530b', 'a7z_pcb', 'dupont_plugs', 'fan_lead_loop', 'a7z_header')])
    steps = []
    for dz in (-44.0, -33.0, -22.0, -11.0, -5.0, -2.0, 0.0):
        m = insert.copy(); m.apply_translation([0, 0, dz])
        steps.append([float(dz), gap(m, new_cap), gap(m, unit)])
    tick('insert path')
    out['insertPath'] = {'minGapCap_mm': min(s_[1] for s_ in steps), 'minGapUnit_mm': min(s_[2] for s_ in steps), 'steps': steps}
    # The head closes: head_bottom with jaw_support, clip_head and the jaw servo rise into the cap around the insert
    # head_bottom itself is only below the insert (its floor gap is the final-pose pair); the parts that rise past it:
    grp = {k: solid(k) for k in ('jaw_support', 'clip_head')}
    out['headCloseMinGapToInsert_mm'] = {k: min(gap(insert, m.copy().apply_translation([0, 0, -dz])) for dz in (0.0, 5.0, 10.0, 20.0, 30.0))
                                         for k, m in grp.items()}
    tick('close')
    # Jaw opening against the insert and the walls
    jaw = world['jaw_frame']; jm_ = []
    iw = U([insert, wu])
    for a in (0.0, 9.0, 18.0, 27.0):
        jm = jaw.copy(); jm.apply_transform(trimesh.transformations.rotation_matrix(math.radians(a), JAW_AXIS, JAW_PIVOT))
        jm_.append([float(a), gap(jm, iw)])
    out['jawSweepInsertWalls'] = jm_
    tick('jaw')
    # Neck servo and speaker cables drawn in the guide
    gd = json.loads((GUIDE / 'data/guide-data.json').read_text())
    worst = (99.0, '')
    for c in gd.get('cables', []):
        if not str(c.get('id', '')).startswith(('dxl-', 'spk-')):
            continue
        pts = np.array(c['path'], float)
        seg = np.concatenate([np.linspace(a, b, max(2, int(np.linalg.norm(b - a) / 0.5))) for a, b in zip(pts[:-1], pts[1:])])
        r = float(c.get('radius') or 0.9)
        for k, m in (('insert', insert), ('walls', wu)):
            d = float(trimesh.proximity.closest_point(m, seg)[1].min()) - r
            if d < worst[0]:
                worst = (round(d, 2), f"{c['id']} vs {k}")
    out['cableMinGap_mm'] = worst
    # Print: faces that look down at the bed side (cap prints roof down) in the new walls and round the slots
    regions = {k: trimesh.creation.box(bounds=m.bounds) for k, m in walls.items() if m.volume > 0}
    for i, si in enumerate(slot_info[:2]):
        pass
    out['capOverhangs'] = overhangs(new_cap, regions)
    # Insert prints flat on its rear face (x = INSERT_X[0]): faces looking down in -x steeper than 45 degrees
    n = insert.face_normals; a = insert.area_faces; c = insert.triangles_center
    down = (n[:, 0] < -math.cos(math.radians(45))) & (c[:, 0] > INSERT_X[0] + 0.05)
    out['insertOverhang_mm2'] = round(float(a[down].sum()), 2)
    return out


def main():
    tick('start')
    cap = trimesh.load(GUIDE / 'print/a7z-head/head_cap_a7z-world.stl')
    assert cap.is_volume
    world = guide_parts()
    world.pop('head_cap')
    bp = board_parts()
    # Keep-out cut from the cap: heatsink, fan inlet, board, header plugs and the underside parts, each grown 1 mm.
    keep = []
    keep.append(rounded_grow(bp['_hs_body'], 1.0))
    for k in ('_hs_leg0', '_hs_leg1'):              # corner blocks: also their 2 mm slide onto the ear pads (assembly_path)
        swept = trimesh.convex.convex_hull(np.vstack([bp[k].vertices, bp[k].vertices - [SLIDE, 0, 0]]))
        keep += [rounded_grow(bp[k], LEG_CLEAR), rounded_grow(swept, SLIDE_CLEAR)]
    for k in ('fan_inlet_zone', 'a7z_pcb', 'dupont_plugs', 'a7z_header', 'header_tails', 'fan_lead_loop'):
        lo, hi = bp[k].bounds
        g = 0.5 if k in ('dupont_plugs', 'fan_lead_loop') else 1.0          # wires give; rigid parts get 1 mm
        keep.append(trimesh.creation.box(bounds=[lo - g, hi + g]))
    for k in list(A.BOTTOM):
        lo, hi = bp['a7z_' + k].bounds
        keep.append(trimesh.creation.box(bounds=[lo - 1.0, hi + 1.0]))
    keep_part_u = U(keep)                           # the parts' keep-outs (duct walls are cut by these only)
    keep.append(old_rails(cap))
    keep_u = U(keep)
    cut = cap.difference(keep_u, engine='manifold')
    removed = cap.volume - cut.volume
    ear_list, screws, ear_info = ears(cut)
    # Duct walls fixed in the cap, clear of the keep-outs, the head floor and the board unit's whole insertion path.
    unit_pieces = [bp[k] for k in ('_hs_body', '_hs_leg0', '_hs_leg1', 'a7z_pcb', 'header_tails', 'fan_lead_loop',
                                   'kit_screw_head', 'a7z_header')] + [bp['a7z_' + k] for k in A.BOTTOM]
    env = []
    for m in unit_pieces:
        v = m.convex_hull.vertices
        env.append(rounded_grow(trimesh.convex.convex_hull(np.vstack([v + [-SLIDE, 0, -40.0], v + [-SLIDE, 0, 0]])), 0.5))
        env.append(rounded_grow(trimesh.convex.convex_hull(np.vstack([v + [-SLIDE, 0, 0], v])), 0.5))
    env_u = U(env)
    hb_grown = grow(solid('head_bottom'), 0.85)               # at least 0.5 mm after the 14-copy grow
    walls_raw = fixed_duct_walls(cut)
    walls, wall_info = {}, {}
    for k, m in walls_raw.items():
        mm = m.difference(U([keep_part_u, env_u, hb_grown]), engine='manifold')
        walls[k] = mm
        wall_info[k] = {'volume_mm3': round(float(mm.volume), 1), 'carved_mm3': round(float(m.volume - mm.volume), 1),
                        'bounds': np.round(mm.bounds, 1).tolist() if mm.volume > 0 else None}
    slot_boxes, slot_info = slot_cuts()
    pre = U([cut] + ear_list + list(walls.values()))
    new_cap = pre.difference(U(slot_boxes), engine='manifold')
    for b, si in zip(slot_boxes, slot_info):
        si['removed_mm3'] = round(float(pre.intersection(b, engine='manifold').volume), 1)
    assert new_cap.is_volume, 'new cap is not a closed solid'
    # The shroud insert, sized against the cap without its rails (the rails sit 0.2 mm off its faces).
    no_rails = U([cut] + ear_list + [m for k, m in walls.items() if not k.startswith('rail')])
    tick('walls+slots')
    insert = shroud_insert(no_rails, [bp[k] for k in ('_hs_body', '_hs_leg0', '_hs_leg1', 'fan_lead_loop')])
    insert.export(RUN / 'shroud_insert-world.stl')
    tick('insert')
    U(list(walls.values())).export(RUN / 'duct_walls_only.stl')
    new_cap.export(RUN / 'head_cap_b2b-world.stl')
    for k, m in bp.items():
        if not k.startswith('_'):
            m.export(OUT / f'{k}.stl')
    U(screws).export(OUT / 'ear_screws_m2x8.stl')
    U(ear_list).export(RUN / 'ears_only.stl')                # the ears alone, for colouring in renders (part of the cap)
    res = {'pose': {'rear_face_x': XC, 'top_edge_z': ZTOP, 'pin1_end_y': Y1}, 'capVolume_mm3': round(new_cap.volume, 1),
           'capRemoved_mm3': round(removed, 1), 'capBodies': int(new_cap.body_count), 'ears': ear_info, 'pairs': {}}
    # Clearance of every new part against every fixed guide part in the head (and the new cap).
    newp = {k: bp[k] for k in ('heatsink_6530b', 'fan_inlet_zone', 'a7z_pcb', 'dupont_plugs', 'header_tails', 'fan_lead_loop',
                               'kit_screw_head', 'camera_ribbon_b2b')}
    newp.update({'a7z_' + k: bp['a7z_' + k] for k in A.BOTTOM})
    newp['ear_screws'] = U(screws)
    newp['ears'] = U(ear_list)
    coax, coax_len = coax_route(); newp['antenna_coax'] = coax
    coax.export(OUT / 'antenna_coax_b2b.stl')
    res['coaxLength_mm'] = round(coax_len, 1); res['coaxLimit_mm'] = 50.0
    tick('pre-walls')
    res['walls'] = wall_checks(cap, new_cap, keep_u, ear_list)
    tick('wall checks')
    cs = coax.sample(6000); cin = new_cap.contains(cs)
    res['coaxInsideCapSamples'] = int(cin.sum()); res['coaxClashWhere'] = np.round(cs[cin][:8], 1).tolist()
    for k, m in newp.items():
        row = {}
        for o, om in list(world.items()) + [('head_cap(new)', new_cap)]:
            if k in ('ear_screws', 'ears') and o == 'head_cap(new)':
                continue
            if np.all(m.bounds[0] < om.bounds[1] + 3) and np.all(om.bounds[0] < m.bounds[1] + 3):
                row[o] = gap(m, om)
        res['pairs'][k] = dict(sorted(row.items(), key=lambda t: t[1])[:6])
    tick('pairs')
    res['assembly'] = assembly_path(new_cap, bp, screws)
    tick('assembly')
    res['ducts'] = duct_checks(new_cap, insert, walls, wall_info, slot_info, bp, world)
    # Jaw opening 0..27 deg against the moved board, heatsink and ears.
    jaw = world['jaw_frame']; moved = U([bp['heatsink_6530b'], bp['a7z_pcb']] + ear_list)
    jmin = []
    for a in np.arange(0.0, JAW_HI + 0.01, 3.0):
        T4 = trimesh.transformations.rotation_matrix(math.radians(a), JAW_AXIS, JAW_PIVOT)
        jm = jaw.copy(); jm.apply_transform(T4)
        jmin.append([float(a), gap(jm, moved)])
    res['jawSweep_deg_gap'] = jmin
    (RUN / 'checks.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
