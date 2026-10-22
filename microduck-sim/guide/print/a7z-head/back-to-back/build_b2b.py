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
    """Board + heatsink (one unit, kit screw in) go into the cap upside down on the bench: lowered along the cap's axis
    SLIDE behind the final pose, then slid forward onto the ear pads. Each step is checked against the new cap; then a
    straight driver line from each M2 x 8 head forward out of the face opening (the face panel goes on last)."""
    keys = ('heatsink_6530b', 'a7z_pcb', 'dupont_plugs', 'header_tails', 'fan_lead_loop', 'kit_screw_head', 'a7z_header')
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


def main():
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
    keep.append(old_rails(cap))
    keep_u = U(keep)
    cut = cap.difference(keep_u, engine='manifold')
    removed = cap.volume - cut.volume
    ear_list, screws, ear_info = ears(cut)
    new_cap = U([cut] + ear_list)
    assert new_cap.is_volume, 'new cap is not a closed solid'
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
    res['walls'] = wall_checks(cap, new_cap, keep_u, ear_list)
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
    res['assembly'] = assembly_path(new_cap, bp, screws)
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
