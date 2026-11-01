"""Tool-free battery swap for the battery-on-cap backpack (D-037): a roof opening over the battery and a snap hatch.
Starts from the current backpack in the team fork (qilinxiaoxiang/microduck_rl cmu/hardware/battery-backpack, Michael Lin's
redesign) and writes build/: battery_backpack_{frame,cap}-world.stl (opening cut), battery_hatch-world.stl, the three in
print pose (*-print.stl), and build.json with the fit, path, strain and wall checks. Robot frame, mm, x forward, y left, z up.

    uv run --with trimesh --with manifold3d --with scipy --with rtree --with networkx python build_quickswap.py BATTERY_BACKPACK_DIR

The cap's rear top edge is rounded (outer surface at x -75.05 at z 39, -73.74 at z 41) and hangs over the back 1 to 2 mm of
the battery, so the opening runs through that corner: the cap loses its roof and rounded corner over the battery down to
z 37, where its back wall is still straight. The hatch is that removed piece itself (roof plate flush at z 43, the rounded
corner down to z 37.1), 0.15 mm clear of the cut faces, plus:
- two fixed front tabs whose lips sit under the frame roof edge (the hinge);
- a 1.2 mm flap hanging down over the cap's back face with a bump that snaps into a slot in the back wall. Pull the flap's
  lower edge back 0.65 mm, lift the rear about the front tabs, pull the hatch back off the tabs;
- a wedge that holds the battery down 0.3 mm above its top, where the cradle roof tab was;
- lead notches open to the rear, so the hatch lifts off with both leads still plugged in.
The hatch prints like the cap, back face down (the flap on the bed), so the flap bends within its layers and the rounded
corner rises off the bed as on the cap.
"""
import json, sys
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf

HERE = Path(__file__).resolve().parent
BP = Path(sys.argv[1]); OUT = HERE / 'build'; OUT.mkdir(exist_ok=True)
PIPE = HERE.parents[2] / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'
sys.path.insert(0, str(PIPE)); import wall_check as W  # noqa: E402

def load(p): m = trimesh.load(p, force='mesh', process=True); m.merge_vertices(); return m
def to_mf(m): return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
def to_tm(M): g = M.to_mesh(); return trimesh.Trimesh(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts), process=True)
def box(lo, hi): lo, hi = np.array(lo, float), np.array(hi, float); return mf.Manifold.cube(tuple(hi - lo)).translate(tuple(lo))
def prism_y(pts_xz, y0, y1):
    """Prism along y from an (x, z) polygon."""
    P = np.array(pts_xz, float)
    if mf.CrossSection([P.tolist()]).area() <= 0: P = P[::-1]     # manifold drops clockwise outlines
    return mf.Manifold.extrude(mf.CrossSection([P.tolist()]), y1 - y0).rotate((90, 0, 0)).translate((0, y1, 0))
U = lambda ms: mf.Manifold.batch_boolean(list(ms), mf.OpType.Add)
r3 = lambda v: round(float(v), 3)

# battery seat and box numbers from cmu/hardware/battery-redesign/build_cap_cradle.py
BAT_LO, BAT_HI = np.array([-74.05, -15.5, -22.51]), np.array([-62.05, 15.5, 34.49])
CAP_IN, CAP_OUT, BAR_BACK, ROOF_IN, TOP = -74.35, -75.55, -61.75, 41.80, 43.0
GAP = 0.3
OPEN_Y = 16.0
Z_WALL = 37.0                                   # the cap back wall is straight (x -75.55) up to here
CUT_IN = box((CAP_IN, -OPEN_Y, BAT_HI[2] + 0.1), (BAR_BACK, OPEN_Y, TOP + 1))        # over the battery, roof tab included
CUT_REAR = box((CAP_OUT - 1, -OPEN_Y, Z_WALL), (CAP_IN + 0.01, OPEN_Y, TOP + 1))     # the rounded corner over the battery

# hatch
CL = 0.15                                       # clearance to the cut faces (sides, rear wall top)
HY = OPEN_Y - CL
FRONT_GAP = 0.4                                 # front face to the frame roof edge: lets the rear lift 18 degrees
HX1 = BAR_BACK - FRONT_GAP
LIP_Z = (40.2, ROOF_IN - 0.2)
TAB_POST_X = (HX1 - 1.2, HX1); TAB_LIP_X = (HX1, HX1 + 1.2)                   # lips 0.8 under the roof edge
TAB_Y = [(-8.0, -2.0), (4.0, 10.0)]
PIVOT = np.array([BAR_BACK, 0.0, ROOF_IN])
WEDGE = [(-70.5, ROOF_IN + 0.1), (-63.4, ROOF_IN + 0.1), (-63.4, BAT_HI[2] + GAP), (-64.4, BAT_HI[2] + GAP)]   # 45 deg rear face
WEDGE_Y = (-3.0, 6.0)
NOTCHES = {'main lead': (-11.0, -5.0), 'balance lead': (8.5, 14.5)}
NOTCH_X1, NOTCH_Z0 = -66.0, 38.6
FLAP_T, FLAP_Y, FLAP_Z0 = 1.2, 14.0, 18.0
BUMP = dict(depth=1.2, y=6.0, z=(19.0, 21.4), lead_in=1.2)                 # 45 deg lead-in below, square top; flush with the wall's inside
SLOT = dict(y=6.3, z=(18.8, 21.6))
RELEASE_MM = BUMP['depth'] + 0.1

def flap_strain(y_bump):
    """Root strain of the flap (cantilever down from z 37.1, pulled at its lower edge) when the bump moves y_bump."""
    L = (Z_WALL + CL) - FLAP_Z0; x = (Z_WALL + CL) - np.mean(BUMP['z'])
    return y_bump * 3 * FLAP_T * L / (x * x * (3 * L - x)), L, x

def overlap(a, b): return float((a ^ b).volume())

def main():
    frame0 = to_mf(load(BP / 'stl/battery_backpack_frame-world.stl'))
    cap0 = to_mf(load(BP / 'stl/battery_backpack_cap-world.stl'))
    bars = to_mf(load(BP / 'stl/battery_backpack_bar-world.stl'))
    env = {n: to_mf(load(BP / f'envelopes/{f}')) for n, f in
           (('switch', 'switch_swann-world.stl'), ('dfr1202', 'dfr1202-world.stl'), ('dfr pads', 'dfr_pads-world.stl'))}
    pack = to_mf(load(BP / 'mating/rear_pack.stl'))
    hull = to_mf(trimesh.util.concatenate([to_tm(frame0), to_tm(cap0)]).convex_hull)

    slot = box((CAP_OUT - 0.1, -SLOT['y'], SLOT['z'][0]), (CAP_IN + 0.1, SLOT['y'], SLOT['z'][1]))
    frame = frame0 - CUT_IN
    cap = cap0 - CUT_IN - CUT_REAR - slot

    # hatch: the removed corner and roof, the roof plane filled (the old lead openings) inside the box outline
    corner = cap0 ^ box((CAP_OUT - 1, -HY, Z_WALL + CL), (-68.15, HY, TOP + 1))
    plate = box((CAP_IN, -HY, ROOF_IN), (HX1, HY, TOP)) ^ hull
    plate_deep = box((-72.6, -HY, 40.6), (-68.0, HY, TOP)) ^ hull     # the old lead openings in the curved roof, filled 1.2 deep
    body = corner + plate + plate_deep
    body = body - U([box((CAP_OUT - 2, a, NOTCH_Z0), (NOTCH_X1, b, TOP + 1)) for a, b in NOTCHES.values()])
    flap = U([box((CAP_OUT - FLAP_T, -FLAP_Y, FLAP_Z0), (CAP_OUT, FLAP_Y, Z_WALL + 1.6)),
              box((CAP_OUT - FLAP_T, -FLAP_Y, Z_WALL + CL), (CAP_OUT + 0.6, FLAP_Y, Z_WALL + 1.6))])   # root joins the curved corner
    bz0, bz1 = BUMP['z']
    bump = prism_y([(CAP_OUT - 0.05, bz0), (CAP_OUT + BUMP['depth'], bz0 + BUMP['lead_in']), (CAP_OUT + BUMP['depth'], bz1), (CAP_OUT - 0.05, bz1)],
                   -BUMP['y'], BUMP['y'])
    tabs = U([box((TAB_POST_X[0], a, LIP_Z[0]), (TAB_POST_X[1], b, ROOF_IN + 0.01)) for a, b in TAB_Y]
             + [box((TAB_LIP_X[0], a, LIP_Z[0]), (TAB_LIP_X[1], b, LIP_Z[1])) for a, b in TAB_Y])
    wedge = prism_y(WEDGE, *WEDGE_Y)
    hatch_free = body + flap + tabs + wedge          # without the bump: the flap held out while the hatch swings
    hatch = hatch_free + bump
    battery = box(BAT_LO, BAT_HI)
    fixed = {'frame': frame, 'cap': cap, 'bars': bars, 'rear pack': pack, **env}

    ck = {}
    ck['solids'] = {n: dict(bodies=len(M.decompose()), status=str(M.status()),
                            volume_cm3=r3(M.volume() / 1000)) for n, M in (('frame', frame), ('cap', cap), ('hatch', hatch))}
    ck['removed_cm3'] = dict(frame=r3((frame0.volume() - frame.volume()) / 1000), cap=r3((cap0.volume() - cap.volume()) / 1000))
    ck['closed_overlap_mm3'] = {n: r3(overlap(hatch, M)) for n, M in fixed.items()}
    ck['closed_overlap_mm3']['battery'] = r3(overlap(hatch, battery))
    ck['bump_in_slot_overlap_mm3'] = r3(overlap(bump, cap))
    ck['wedge_to_battery_mm'] = r3(BAT_HI[2] + GAP - BAT_HI[2])
    def under_roof(x0, x1, y0, y1):
        probe = box((x0, y0, LIP_Z[1]), (x1, y1, TOP))
        return r3((probe ^ frame).volume() / probe.volume())
    ck['roof_over_tab_lips_fraction'] = [under_roof(BAR_BACK + 0.01, TAB_LIP_X[1], a, b) for a, b in TAB_Y]
    ck['tab_lip_engagement_mm'] = r3(TAB_LIP_X[1] - BAR_BACK)
    # battery path: straight up 70 mm with the hatch off, the Kapton pull tab (0.1 mm) on its front face
    bat_tab = battery + box((BAT_HI[0], -4, BAT_LO[2]), (BAT_HI[0] + 0.1, 4, BAT_HI[2]))
    ck['battery_lift_max_overlap_mm3'] = {n: r3(max(overlap(bat_tab.translate((0, 0, dz)), M) for dz in np.arange(0, 70.1, 2.5)))
                                         for n, M in fixed.items()}
    # hatch path: rear swung up about the frame roof edge (flap held out), then pulled 1.5 mm back off the tabs at 15 deg
    def posed(M, deg, back=0.0):
        return M.translate(tuple(-PIVOT)).rotate((0, deg, 0)).translate(tuple(PIVOT)).translate((-back, 0, 0))
    up = 1 if to_tm(posed(box((CAP_IN, -1, ROOF_IN), (CAP_IN + 1, 1, TOP)), 10)).bounds[0, 2] > ROOF_IN else -1
    swing = {}
    for deg in (0, 2, 4, 6, 8, 10, 12, 15, 18):
        M = posed(hatch_free, up * deg)
        hits = {n: r3(overlap(M, F)) for n, F in fixed.items()}
        swing[deg] = {n: v for n, v in hits.items() if v > 0.01}
    ck['hatch_swing_overlaps_mm3'] = swing
    ck['hatch_pull_back_at_15deg_overlaps_mm3'] = {b: {n: r3(overlap(posed(hatch_free, up * 15, b), F)) for n, F in fixed.items()
                                                       if overlap(posed(hatch_free, up * 15, b), F) > 0.01} for b in (0.5, 1.0, 1.5)}
    ck['rear_rise_at_15deg_mm'] = r3(13.0 * np.sin(np.radians(15)))
    eps, L, x = flap_strain(RELEASE_MM)
    ck['flap'] = dict(thickness_mm=FLAP_T, length_mm=r3(L), root_to_bump_mm=r3(x), release_pull_mm=RELEASE_MM,
                      root_strain_pct=round(100 * eps, 2), bump_depth_mm=BUMP['depth'], retention_face='square (90 deg)')
    ck['hatch_mass_g'] = r3(hatch.volume() / 1000 * 1.24)

    # print poses (x' = y, y' = z, z' = x): frame rim down, cap and hatch back face down
    R = np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], float)
    def to_print(M):
        m = to_tm(M); T = np.eye(4); T[:3, :3] = R; m.apply_transform(T); m.apply_translation(-m.bounds[0]); return m, T
    cuts = [(np.array(lo) - 3, np.array(hi) + 3) for lo, hi in (((CAP_IN, -OPEN_Y, BAT_HI[2]), (BAR_BACK, OPEN_Y, TOP)),
            ((CAP_OUT, -OPEN_Y, Z_WALL), (CAP_IN, OPEN_Y, TOP)), ((CAP_OUT, -SLOT['y'], SLOT['z'][0]), (CAP_IN, SLOT['y'], SLOT['z'][1])))]
    def cut_near(M, r):
        m = to_tm(M); T = np.eye(4); T[:3, :3] = R; m.apply_transform(T); off = m.bounds[0]
        w = R.T @ (np.mean(np.array(r['bbox']), axis=0) + off)
        return [round(float(v), 2) for v in w] if any(np.all(w >= lo) and np.all(w <= hi) for lo, hi in cuts) else None
    def regions(pm, name): return [{k: r[k] for k in ('bbox', 'minMm', 'areaMm2', 'status') if k in r} for r in W.check(pm, (), name)['regions']]
    out = {}
    for name, M, M0 in (('battery_backpack_frame', frame, frame0), ('battery_backpack_cap', cap, cap0), ('battery_hatch', hatch, None)):
        to_tm(M).export(OUT / f'{name}-world.stl')
        pm, T = to_print(M); pm.export(OUT / f'{name}-print.stl')
        bed = float(pm.area_faces[np.max(np.abs(pm.triangles[:, :, 2]), axis=1) <= .01].sum())
        now = [r for r in regions(pm, name) if r.get('status') == 'FAIL']
        new = now
        if M0 is not None:      # thin regions the built part already had are not new (same place within 2 mm, same pose)
            pm0, _ = to_print(M0)
            shift = (to_tm(M).bounds[0] - to_tm(M0).bounds[0]) @ R.T
            before = [r for r in regions(pm0, name) if r.get('status') == 'FAIL']
            cb = [np.mean(np.array(r['bbox']), axis=0) - shift for r in before]
            new = [r for r in now if not any(np.linalg.norm(np.mean(np.array(r['bbox']), axis=0) - c) < 2.0 for c in cb)]
            # a region away from every cut is the part's unchanged geometry sampled differently after the boolean
            new = [dict(r, worldCentre=near) for r in new if (near := cut_near(M, r)) is not None]
        out[name] = dict(print_height_mm=r3(pm.bounds[1, 2]), bed_contact_mm2=round(bed, 1), source_to_print=T.tolist(),
                         thin_regions=len(now), new_thin_regions=new)
    ck['print'] = out
    (OUT / 'build.json').write_text(json.dumps(ck, indent=1, ensure_ascii=False))
    print(json.dumps(ck, indent=1, ensure_ascii=False))

main()
