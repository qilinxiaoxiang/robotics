"""Radxa Cubie A7Z in the MicroDuck head: board envelope model and the head cap rail relief.

The A7Z has the Pi Zero outline and hole pattern (65 x 30 mm, holes 58 x 23 mm, 3.5 mm from the edges; measured 1:1
from Radxa's placement map V1.11, sources/placement-v1.11.pdf), so it screws onto the same cap rails in the same pose
as the Pi Zero W: header along the lower edge, pins towards the face, pin 1 at the +Y end. Its underside is not flat
like the Pi's: the camera FPC connector sits on the underside at the pin-1 (+Y) end and the microSD socket on the
underside near the pin-40 (-Y) end, both between the two holes of that end, right where the V1.9 cap rails touch the
board. Component positions are measured on Radxa's official top and bottom photos (sources/a7z-top.png,
a7z-bottom.png, scale from the 65 x 30 outline); heights are conservative catalogue values.

Board frame: s = distance from the pin-1 end (mm), d = distance from the header edge (mm), h = height above the PCB
underside along the pin axis (mm). w(s, d, h) maps it to the robot frame (mm, x forward, y left, z up).

Outputs (this folder): a7z_parts/*.stl (world frame), head_cap_a7z-world.stl, checks.json, slices.png.
"""
import json
from pathlib import Path

import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
WORLD = HERE.parent / 'world'
OUT = HERE / 'a7z_parts'
OUT.mkdir(exist_ok=True)

# Pi Zero W pose in the V1.9 cap, derived from the guide-data header pins (pi-frame-raw.json): pin axis
# n = (0.9848, 0, -0.1736), so the board leans 10 degrees forward; long axis es = -y from pin 1 towards pin 39; the
# header edge is the lower edge. PCB underside at n . p = 34.3876, PCB 1.6 mm thick. Pin 1's axis is 8.37 mm from the
# +Y end and 2.23 mm from the header edge in the CAD export (the export's pin labels have the two header rows swapped;
# the envelopes are the same).
_F = json.loads((HERE / 'pi-frame-raw.json').read_text())
N = np.array(_F['n']); ES = np.array(_F['es']); ED = -np.array(_F['ed_inner'])   # ED: header edge -> port edge
_C1 = np.array(_F['c1'])
H_UNDER, T = 34.3876, 1.6
ORIGIN = _C1 + (H_UNDER - _C1 @ N) * N - 8.37 * ES - 2.23 * ED     # (s, d, h) = (0, 0, 0): pin-1 end, header edge, underside
HOLES = [(3.5, 3.5), (3.5, 26.5), (61.5, 3.5), (61.5, 26.5)]           # (s, d)


def w(s, d, h):
    return ORIGIN + s * ES + d * ED + h * N


def obox(s0, s1, d0, d1, h0, h1):
    """Oriented box in the board frame, as a convex hull of its eight world corners."""
    pts = [w(s, d, h) for s in (s0, s1) for d in (d0, d1) for h in (h0, h1)]
    return trimesh.convex.convex_hull(np.array(pts))


def box(lo, hi):
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    m = trimesh.creation.box(extents=hi - lo)
    m.apply_translation((lo + hi) / 2)
    return m


def comp(s0, s1, d0, d1, h, side):
    return obox(s0, s1, d0, d1, T, T + h) if side == 'top' else obox(s0, s1, d0, d1, -h, 0.0)


def cyl_n(s, d, h0, h1, r):
    c = trimesh.creation.cylinder(radius=r, segment=[w(s, d, h0), w(s, d, h1)], sections=48)
    return c


# Measured on the official photos (+-0.5 mm); heights conservative.
TOP = {
    'wifi_module_fcu760k': (6.5, 17.6, 7.5, 19.6, 2.3),
    'soc_a733': (20.4, 35.8, 10.0, 25.3, 1.6),
    'ram': (37.9, 48.3, 7.1, 21.9, 1.2),                # d0 kept clear of the guide's 7.0 mm header-base envelope (photo +-0.5)
    'pmic_area': (51.0, 60.0, 8.0, 21.0, 1.2),
    'micro_hdmi': (8.8, 16.0, 23.8, 31.6, 3.0),          # overhangs the port edge by 1.6 (photo); the cap clip arm crossed it
    'usb_c_otg_dp': (37.1, 46.2, 23.3, 31.6, 3.3),
    'usb_c_power': (50.0, 59.0, 23.3, 31.6, 3.3),
    'fan_connector': (0.9, 3.3, 18.4, 23.3, 3.0),
    'ipex_socket': (0.5, 3.5, 13.4, 16.4, 1.25),
}
BOTTOM = {
    'csi_connector': (1.0, 5.1, 9.8, 20.5, 2.0),          # 31-pin 0.3 mm flip-lock, latch closed; ribbon enters from the +Y end
    'microsd_socket': (51.8, 57.8, 9.8, 20.5, 1.5),
    'microsd_card': (51.8, 67.0, 10.0, 21.0, 1.5),       # card sticks out about 2 mm past the -Y end
    'pcie_fpc': (20.5, 32.5, 26.5, 31.2, 1.5),
    'uboot_button': (16.7, 18.6, 26.0, 29.3, 1.6),
}
HDMI = TOP['micro_hdmi']
IPEX_C = (2.0, 14.9)
RIB_D = (15.15 - 6.0, 15.15 + 6.0)                        # 12 mm ribbon centred on the connector


def ipex_plug():
    s, d = IPEX_C
    body = cyl_n(s, d, T, T + 2.5, 1.0)
    lead = obox(s, 3.9, d - 0.6, d + 0.6, T + 1.4, T + 2.6)   # coax leaves towards -Y along the board face (coax_tube)
    return trimesh.util.concatenate([body, lead])


def ribbon():
    """Camera FPC from the underside connector: 12 mm wide, leaves the +Y end, bends round and runs forward to the camera."""
    d0, d1 = RIB_D
    flat = obox(-1.0, 5.1, d0, d1, -1.5, -0.9)
    bend = obox(-0.9, -0.3, d0, d1, -1.5, T + 0.5)       # folded tight round the board end
    a, b = w(-0.9, d0, T + 0.5), w(-0.3, d1, T + 0.5)
    zlo, zhi = min(a[2], b[2], w(-0.9, d1, -1.5)[2]), max(a[2], b[2], w(-0.9, d0, -1.5)[2])
    run = box((min(a[0], b[0]) - 0.3, 32.8, zlo), (70.5, 33.4, zhi))
    return trimesh.util.concatenate([flat, bend, run])


ANT_X = (64.0, 75.9)          # 11.9 mm wide, between the cap clip (x <= 69.3 below it) and the face
ANT_Y = (-21.0, 21.0)         # 42 mm across the front of the roof, cable end at +Y


def antenna_sheet(cap, gap=0.05, thick=0.3):
    """AC019 FPC antenna, 42 x 11.9 x 0.3 mm, stuck to the cap roof: a sheet following the roof's inner surface."""
    xs = np.linspace(*ANT_X, 9)
    ys = np.linspace(*ANT_Y, 43)
    g = np.array([[x, y, 140.0] for x in xs for y in ys])
    loc, ri, _ = cap.ray.intersects_location(g, np.tile([0, 0, 1.0], (len(g), 1)), multiple_hits=True)
    top = np.full(len(g), np.inf)
    for p_, r_ in zip(loc, ri):
        top[r_] = min(top[r_], p_[2])
    assert np.isfinite(top).all(), 'antenna area leaves the roof'
    up = g.copy(); up[:, 2] = top - gap
    dn = g.copy(); dn[:, 2] = top - gap - thick
    nx, ny = len(xs), len(ys)
    V = np.vstack([up, dn]); F = []
    idx = lambda i, j, k: k * nx * ny + i * ny + j
    for i in range(nx - 1):
        for j in range(ny - 1):
            a, b, c, d_ = idx(i, j, 0), idx(i + 1, j, 0), idx(i + 1, j + 1, 0), idx(i, j + 1, 0)
            F += [[a, c, b], [a, d_, c]]
            a, b, c, d_ = idx(i, j, 1), idx(i + 1, j, 1), idx(i + 1, j + 1, 1), idx(i, j + 1, 1)
            F += [[a, b, c], [a, c, d_]]
    ring = [(i, 0) for i in range(nx - 1)] + [(nx - 1, j) for j in range(ny - 1)] + \
           [(i, ny - 1) for i in range(nx - 1, 0, -1)] + [(0, j) for j in range(ny - 1, 0, -1)]
    for (i0, j0), (i1, j1) in zip(ring, ring[1:] + ring[:1]):
        a, b = idx(i0, j0, 0), idx(i1, j1, 0)
        c, d_ = idx(i1, j1, 1), idx(i0, j0, 1)
        F += [[a, b, c], [a, c, d_]]
    m = trimesh.Trimesh(V, np.array(F), process=True)
    trimesh.repair.fix_normals(m)
    return m


def coax_tube(r=0.6):
    """1.13 mm coax: from the IPEX plug along the board face towards -Y, forward to just in front of the cap clip,
    straight up to the roof and onto the antenna's cable end at +Y."""
    s, d = IPEX_C
    p1 = w(3.9, d, T + 2.0)                       # the coax leaves the plug towards -Y, along the board face
    pts = [w(s, d, T + 2.0), p1, np.array([71.0, p1[1], p1[2]]), np.array([71.0, 26.0, 145.5]),
           np.array([71.0, 23.0, 149.3]), np.array([70.5, ANT_Y[1] - 0.5, 150.9])]
    pts = np.array(pts)
    L = float(np.linalg.norm(np.diff(pts, axis=0), axis=1).sum())
    segs = []
    for a, b in zip(pts[:-1], pts[1:]):
        segs.append(trimesh.creation.cylinder(radius=r, segment=[a, b], sections=12))
        sph = trimesh.creation.icosphere(subdivisions=1, radius=r); sph.apply_translation(b); segs.append(sph)
    return clean(trimesh.boolean.union(segs, engine='manifold')), L


def clean(mesh, tol=0.005):
    """Collapse sub-0.005 mm slivers so the STL (float32) reloads as a closed volume."""
    import manifold3d as m3d
    man = m3d.Manifold(m3d.Mesh(vert_properties=np.asarray(mesh.vertices, np.float32),
                                tri_verts=np.asarray(mesh.faces, np.uint32))).simplify(tol)
    out = man.to_mesh()
    return trimesh.Trimesh(np.asarray(out.vert_properties)[:, :3], np.asarray(out.tri_verts), process=True)


def main():
    parts = {}
    corners = [cyl_n(s_, d_, 0, T, 3.0) for s_ in (3.0, 62.0) for d_ in (3.0, 27.0)]
    pcb = trimesh.convex.convex_hull(np.vstack([c.vertices for c in corners]))
    holes = [cyl_n(s_, d_, -1, T + 1, 1.375) for s_, d_ in HOLES]
    parts['a7z_pcb'] = pcb.difference(trimesh.boolean.union(holes, engine='manifold'), engine='manifold')
    for k, v in TOP.items():
        parts[k] = comp(*v, 'top')
    for k, v in BOTTOM.items():
        parts[k] = comp(*v, 'bottom')
    # Low SMD parts all over the underside except the four hole keep-outs and the underside parts modelled on their own
    # (the Pi Zero underside was flat).
    keep = [cyl_n(s_, d_, -2, 0.5, 3.0) for s_, d_ in HOLES] + [obox(v[0], v[1], v[2], v[3], -2.5, 0.5) for v in BOTTOM.values()]
    parts['underside_smd'] = obox(0, 65, 0, 30, -1.0, 0.0).difference(trimesh.boolean.union(keep, engine='manifold'), engine='manifold')
    parts['ipex_plug'] = ipex_plug()
    parts['camera_ribbon_a7z_end'] = ribbon()
    for k, m in parts.items():
        m.export(OUT / f'{k}.stl')

    # ---- head cap: rail relief ----
    cap = trimesh.load(WORLD / 'head_cap-v19.stl')          # the V1.9 cap this build cuts (world/head_cap.stl is now its output)
    sd0, sd1 = RIB_D[0] - 0.5, RIB_D[1] + 0.5
    cuts = [
        # 1. Rails touch the board only on a 3.0 mm pad round each hole: relieve 1.6 mm under the rest of the board ends.
        obox(-0.3, 6.9, -0.5, 30.5, -1.6, 0.05),
        obox(58.1, 65.3, -0.5, 30.5, -1.6, 0.05),
        # 2. +Y: CSI connector and ribbon under the board, then round the board end towards the face.
        obox(-4.3, 6.1, sd0, sd1, -2.4, 0.05),
        obox(-4.3, -0.1, sd0, sd1, -2.4, T + 1.5),            # room to fold the ribbon round the board end
        # 3. -Y: microSD socket and the card sticking out of the -Y end.
        obox(58.6, 67.6, sd0, sd1, -2.4, 0.05),
    ]
    pads = [cyl_n(s_, d_, -1.7, 0.1, 3.0) for s_, d_ in HOLES]
    cut = trimesh.boolean.union(cuts, engine='manifold')
    cut = cut.difference(trimesh.boolean.union(pads, engine='manifold'), engine='manifold')
    new_cap = clean(cap.difference(cut, engine='manifold'))
    new_cap.export(HERE / 'head_cap_a7z-world.stl')
    reread = trimesh.load(HERE / 'head_cap_a7z-world.stl')
    assert reread.is_volume, 'exported cap is not a closed volume after reload'
    removed = cap.volume - new_cap.volume
    sz0, sz1 = sd0, sd1

    # ---- cap wire clip: notch the arm over the micro-HDMI overhang (0.6 mm clearance all round) ----
    clip = trimesh.load(WORLD / 'clip_cap-v19.stl')
    notch = obox(HDMI[0] - 0.6, HDMI[1] + 0.6, HDMI[2] - 0.6, HDMI[3] + 0.6, T - 0.6, T + HDMI[4] + 0.6)
    new_clip = clean(clip.difference(notch, engine='manifold'))
    new_clip.export(HERE / 'clip_cap_a7z-world.stl')
    assert trimesh.load(HERE / 'clip_cap_a7z-world.stl').is_volume
    assert new_clip.body_count == 1, 'clip notch split the clip'
    parts_checked = dict(parts)

    # ---- antenna on the cap roof and its 50 mm coax ----
    ant = antenna_sheet(new_cap)
    ant.export(OUT / 'antenna_ac019.stl')
    coax, coax_len = coax_tube()
    coax.export(OUT / 'antenna_coax.stl')
    parts_checked['antenna_ac019'] = ant
    parts_checked['antenna_coax'] = coax
    parts = parts_checked
    for k in ('antenna_ac019', 'antenna_coax'):
        assert trimesh.load(OUT / f'{k}.stl').is_volume, k

    # ---- checks ----
    others = {k: trimesh.load(WORLD / f'{k}.stl') for k in ('head_bottom', 'jaw_frame', 'clip_head', 'amplifier',
                                                            'speaker', 'speaker_retainer')}
    FACE = HERE.parent / 'face-a7z'
    for k in ('face_panel_a7z', 'eye_trim_a7z', 'camera_13m214'):
        others[k] = trimesh.load(FACE / f'{k}.stl')
    others['speaker'] = others['speaker'].convex_hull          # purchased-part mesh is open; its hull is conservative
    others['head_cap(new)'] = new_cap
    others['clip_cap(new)'] = new_clip
    res = {'removedCapVolume_mm3': round(removed, 1), 'capWatertight': bool(new_cap.is_watertight),
           'capVolume_mm3': round(new_cap.volume, 1), 'slotBandFromHeaderEdge_mm': [round(sz0, 2), round(sz1, 2)], 'pairs': {}}
    old_hits = {}
    for k, m in parts.items():
        for o, om in others.items():
            try:
                inter = trimesh.boolean.intersection([m, om], engine='manifold')
                v = float(inter.volume) if not inter.is_empty else 0.0
            except Exception as e:  # noqa: BLE001
                v = f'error {e}'
            if v and (not isinstance(v, float) or v > 1e-3):
                res['pairs'][f'{k} x {o}'] = v if isinstance(v, str) else round(v, 3)
        inter = trimesh.boolean.intersection([m, cap], engine='manifold')
        if not inter.is_empty and inter.volume > 1e-3:
            old_hits[k] = round(float(inter.volume), 3)
    res['againstUnmodifiedV19Cap'] = old_hits
    # Remaining wall beyond the +Y slot: material along +y from the slot's outer face, over the slot's (d, h) band.
    mins = []
    for d_ in np.arange(sd0 + 0.3, sd1, 0.6):
        for h_ in np.arange(-2.2, T + 1.4, 0.5):
            p0 = w(-4.4, d_, h_)
            ys = np.arange(0, 15, 0.1)
            pts = np.column_stack([np.full_like(ys, p0[0]), p0[1] + ys, np.full_like(ys, p0[2])])
            mins.append(float(new_cap.contains(pts).sum() * 0.1))
    res['plusYWallBeyondSlot_minMaterial_mm'] = round(min(mins), 2)
    for k in ('micro_hdmi', 'usb_c_otg_dp', 'usb_c_power', 'a7z_pcb', 'fan_connector', 'ipex_plug', 'wifi_module_fcu760k'):
        for o, om in (('head_cap(new)', new_cap),):
            pass
    extra = {}
    for nm, m in (('clip_cap(new) x head_cap(new)', (new_clip, new_cap)),
                  ('clip_cap(new) x antenna', (new_clip, ant)), ('clip_cap(new) x coax', (new_clip, coax))):
        i = trimesh.boolean.intersection(list(m), engine='manifold')
        extra[nm] = 0.0 if i.is_empty else round(float(i.volume), 3)
    for k in ('micro_hdmi', 'a7z_pcb', 'wifi_module_fcu760k', 'fan_connector', 'ipex_plug'):
        i = trimesh.boolean.intersection([parts[k], new_clip], engine='manifold')
        d_ = trimesh.proximity.closest_point(new_clip, parts[k].vertices)[1].min() if i.is_empty else 0.0
        extra[f'{k} x clip_cap(new) minGap_mm'] = round(float(d_), 2)
    res['clipChecks'] = extra
    res['coaxLength_mm'] = round(coax_len, 1)
    res['coaxLimit_mm'] = 50.0
    res['clip'] = {'notchBoardFrame_s_d_h': [round(v, 2) for v in (HDMI[0] - 0.6, HDMI[1] + 0.6, HDMI[2] - 0.6, HDMI[3] + 0.6, T - 0.6, T + HDMI[4] + 0.6)],
                   'volumeOld': round(clip.volume, 1), 'volumeNew': round(new_clip.volume, 1), 'bodies': int(new_clip.body_count)}
    res['frame'] = {'origin': ORIGIN.round(4).tolist(), 'es': ES.round(4).tolist(), 'ed': ED.round(4).tolist(), 'n': N.round(4).tolist()}
    (HERE / 'checks.json').write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == '__main__':
    main()
