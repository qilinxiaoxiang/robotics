"""Battery hatch V3 for the battery-on-cap backpack, after the V1.40 hatch failed on the bench (2026-11-01): lead notches too
narrow for the XT30 male, the outside flap let the hatch pull off backwards, the wedge held nothing. Nothing thin or flexible
beyond the V1.40 flap (Shawn: PLA leaf springs and tongues are too fragile on a moving robot).

    /tmp/microduck-cad-venv/bin/python build_quickswap_v2.py BATTERY_BACKPACK_DIR

Writes build-v2/: battery_backpack_{frame,cap}-world.stl, battery_hatch-world.stl, *-print.stl and build.json. Robot frame, mm,
x forward, y left, z up. Frame unchanged from V1.40. The hatch is the V1.40 roof plate and rounded corner (|y| <= 15.85) plus:
- front: two fixed tabs whose lips sit 1.0 under the frame roof edge (hinge), front gap 0.2, front top edge chamfered;
- rear lift retention: the V1.40 outside flap (y +-14, 1.2 thick, bump 1.2 into the centre slot y +-6.3, z 18.8..21.6);
- pull-back stop: two ears of the roof plate (z 41.8..43) in pockets cut through the cap roof at |y| 16..24.5; the ear rear
  faces sit 0.15 in front of the pocket rear faces. Inside hooks and tongues were rejected (binding, fragile).
- a rigid hold-down block 0.3 above the nominal battery top (foam tape if needed);
- one lead exit window through the plate, open to the rear top, sized for the XT30 male and the JST-XH balance plug.
"""
import json, sys
from pathlib import Path
import numpy as np, trimesh, manifold3d as mf

HERE = Path(__file__).resolve().parent
BP = Path(sys.argv[1]); OUT = HERE / 'build-v2'; OUT.mkdir(exist_ok=True)
PIPE = HERE.parents[2] / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'
sys.path.insert(0, str(PIPE)); import wall_check as W  # noqa: E402

def load(p): m = trimesh.load(p, force='mesh', process=True); m.merge_vertices(); return m
def to_mf(m): return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
def to_tm(M): g = M.to_mesh(); return trimesh.Trimesh(np.asarray(g.vert_properties)[:, :3], np.asarray(g.tri_verts), process=True)
def box(lo, hi): lo, hi = np.array(lo, float), np.array(hi, float); return mf.Manifold.cube(tuple(hi - lo)).translate(tuple(lo))
def poly(P):
    P = np.array(P, float)
    if mf.CrossSection([P.tolist()]).area() <= 0: P = P[::-1]     # manifold drops clockwise outlines
    return mf.CrossSection([P.tolist()])
def prism_y(pts_xz, y0, y1):
    """Prism along y from an (x, z) polygon."""
    return mf.Manifold.extrude(poly(pts_xz), y1 - y0).rotate((90, 0, 0)).translate((0, y1, 0))
def _prism_x(pts_yz, x0, x1):
    """Prism along x from a (y, z) polygon."""
    m = mf.Manifold.extrude(poly(pts_yz), x1 - x0)                 # (y, z) in the sketch plane, extruded along +z
    T = np.array([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]], float)  # sketch (u, v, w) -> world (x = w + x0, y = u, z = v)
    return m.transform(T.tolist())
U = lambda ms: mf.Manifold.batch_boolean(list(ms), mf.OpType.Add)
r3 = lambda v: round(float(v), 3)
strain = lambda t, d, L: 3 * t * d / (2 * L * L)

# battery seat and box numbers from cmu/hardware/battery-redesign/build_cap_cradle.py
BAT_LO, BAT_HI = np.array([-74.05, -15.5, -22.51]), np.array([-62.05, 15.5, 34.49])
CAP_IN, CAP_OUT, BAR_BACK, ROOF_IN, TOP = -74.35, -75.55, -61.75, 41.80, 43.0
OPEN_Y, OPEN_YW = 16.0, 24.5                    # cut half-widths: over the battery (frame and cap), over the cap rear (cap only)
CAP_FRONT = -68.15                              # the cap roof ends here, the frame roof starts
Z_WALL = 37.0                                   # the cap back wall is straight (x -75.55) up to here
SKEW = 0.023                                    # keep new faces off the cap's facet planes (V1.40 pinched-edge lesson)
CL = 0.15
HY, HYW = OPEN_Y - CL, OPEN_YW - CL - 0.017
FRONT_GAP = 0.2
HX1 = BAR_BACK - FRONT_GAP
PIVOT = np.array([BAR_BACK, 0.0, ROOF_IN])
SWING_DESIGN_DEG = 24.0                         # the front top chamfer is cut for this swing (removal tilt 22-24 deg)
LIP_Z = (40.2, ROOF_IN - 0.2)
TAB_POST_X = (HX1 - 1.2, HX1); TAB_LIP_X = (HX1, HX1 + 1.2)                   # lips 1.0 under the roof edge
TAB_Y = [(-12.5, -7.5), (5.5, 10.5)]
# Lead exit window. EXIT_SIDE -1: the window is on the -y (main lead) side; Shawn may move it to the other side (+1), the
# hold-down block should then mirror. The -y edge keeps a 1.2 mm rail so the front strip carrying a hinge tab is
# held at both ends (spec asked for an open edge at -15.85).
EXIT_SIDE = -1
EXIT_X = (-72.0, -63.4)   # rear starts where the rounded corner reaches the roof (no knife edge); front leaves a 1.45 mm hinge strip
EXIT_Y_IN, EXIT_Y_OUT = 3.0, HY - 1.2
WIN_Y = (-EXIT_Y_OUT, EXIT_Y_IN) if EXIT_SIDE < 0 else (-EXIT_Y_IN, EXIT_Y_OUT)
WIN_REAR_Z0 = 38.6 + 0.037                     # just above the flap root (V1.40 NOTCH_Z0 38.6); 39.6 left a 0.60 mm inner wedge
LEADS_X = -68.05
XT30 = (5.2, 10.2, 26.0); JST = (6.0, 8.0, 4.5)   # x, y, z of the plug boxes (narrow side along x)
# Rear flap, exactly V1.40
FLAP_T, FLAP_Y, FLAP_Z0 = 1.2, 14.0, 18.0
BUMP = dict(depth=1.2, y=6.0, z=(19.0, 21.4), lead_in=1.2)
SLOT = dict(y=6.3, z=(18.8, 21.6))
RELEASE_MM = BUMP['depth'] + 0.1
# Pull-back stop: two ears of the roof plate (plate thickness) in pockets cut through the cap roof. The ears stop at the
# frame roof's rear face (x -68.15) less 0.15, since the frame is unchanged; the pocket's front is that frame face.
EAR_X = (-69.85, CAP_FRONT - CL); EAR_Y = (HY - 0.35, 19.5); EAR_Z = (40.65, TOP)   # 4 mm stubs (Shawn 2026-11-01: 有必要做这么长吗 看起来很脆弱);   # down to 0.15 above the pocket floor: the domed roof leaves only ~0.75 mm above z 41.8 at |y| 20
POCKET_X = (-70.0, CAP_FRONT); POCKET_Y = (OPEN_Y - 0.1, 19.7); POCKET_Z = (40.5, TOP + 0.1)
# Rigid hold-down block (like Michael's roof tab), 0.3 above the nominal battery top
HOLD_X = (-73.0, -63.0); HOLD_Y = (5.0, 13.0); HOLD_Z0 = BAT_HI[2] + 0.3   # x -73.5 grazed the back wall at 10 deg of swing

def flap_strain(y_bump):
    L = (Z_WALL + CL) - FLAP_Z0; x = (Z_WALL + CL) - np.mean(BUMP['z'])
    return y_bump * 3 * FLAP_T * L / (x * x * (3 * L - x)), L, x

def overlap(a, b): return float((a ^ b).volume())

def stl_closed(path):
    m = trimesh.load(path, force='mesh', process=False)
    v, inv = np.unique(m.vertices, axis=0, return_inverse=True); m = trimesh.Trimesh(v, inv.reshape(-1)[m.faces], process=False)
    return bool(m.is_watertight and m.is_winding_consistent)

def cyl_y(c_xz, r, y0, y1, n=96):
    return mf.Manifold.cylinder(y1 - y0, r, r, n).rotate((-90, 0, 0)).translate((c_xz[0], y0, c_xz[1]))

def main():
    frame0 = to_mf(load(BP / 'stl/battery_backpack_frame-world.stl'))
    cap0 = to_mf(load(BP / 'stl/battery_backpack_cap-world.stl'))
    bars = to_mf(load(BP / 'stl/battery_backpack_bar-world.stl'))
    env = {n: to_mf(load(BP / f'envelopes/{f}')) for n, f in
           (('switch', 'switch_swann-world.stl'), ('dfr1202', 'dfr1202-world.stl'), ('dfr pads', 'dfr_pads-world.stl'))}
    pack = to_mf(load(BP / 'mating/rear_pack.stl'))
    hull = to_mf(trimesh.util.concatenate([to_tm(frame0), to_tm(cap0)]).convex_hull)

    CUT_IN = box((CAP_IN, -OPEN_Y, BAT_HI[2] + 0.1), (BAR_BACK, OPEN_Y, TOP + 1))
    CUT_REAR = box((CAP_OUT - 1, -OPEN_Y, Z_WALL), (CAP_IN + 0.01, OPEN_Y, TOP + 1))      # V1.40: rounded corner over |y| < 16
    pockets = U([box((POCKET_X[0], POCKET_Y[0], POCKET_Z[0]), (POCKET_X[1], POCKET_Y[1], POCKET_Z[1])),
                 box((POCKET_X[0], -POCKET_Y[1], POCKET_Z[0]), (POCKET_X[1], -POCKET_Y[0], POCKET_Z[1]))])
    slots = box((CAP_OUT - 0.1, -SLOT['y'], SLOT['z'][0]), (CAP_IN + 0.1, SLOT['y'], SLOT['z'][1]))
    frame = frame0 - CUT_IN
    cap = cap0 - CUT_IN - CUT_REAR - pockets - slots

    # hatch body: V1.40 corner and plate over |y| <= 15.85, plus the two ears in the roof pockets
    corner = cap0 ^ box((CAP_OUT - 1, -HY, Z_WALL + CL), (CAP_FRONT, HY, TOP + 1))
    plate = box((CAP_IN, -HY, ROOF_IN - SKEW), (HX1, HY, TOP)) ^ hull
    plate_deep = box((-72.6, -HY, 40.6 - SKEW), (-68.0, HY, TOP)) ^ hull     # the cap's old roof lead openings, filled
    ears = U([box((EAR_X[0], EAR_Y[0], EAR_Z[0]), (EAR_X[1], EAR_Y[1], EAR_Z[1])),
              box((EAR_X[0], -EAR_Y[1], EAR_Z[0]), (EAR_X[1], -EAR_Y[0], EAR_Z[1]))]) ^ hull
    body = corner + plate + plate_deep + ears
    # ear fronts: keep every ear point farther from the hinge than the frame roof's rear corner (+0.15)
    r_sh = np.hypot(BAR_BACK - CAP_FRONT, TOP - ROOF_IN) + CL
    sides = box((-80, HY + 0.01, 30), (-60, 30, 50)) + box((-80, -30, 30), (-60, -HY - 0.01, 50))
    body = body - (cyl_y((PIVOT[0], PIVOT[2] + SKEW), r_sh, -30, 30) ^ sides)
    # front top chamfer: points with h > (FRONT_GAP + a) cot(SWING) would enter the frame roof edge
    c = 1 / np.tan(np.radians(SWING_DESIGN_DEG))
    zc = lambda x: ROOF_IN + c * (BAR_BACK - x)                              # chamfer plane through the hinge-swept limit
    xa, xb = HX1 + 0.05, BAR_BACK - (TOP + 0.2 - ROOF_IN) / c
    body = body - prism_y([(xa, zc(xa)), (xa, TOP + 0.2), (xb, TOP + 0.2)], -HY - 1, HY + 1)
    # the window runs back through the rounded corner above z 39.6 (open to the rear top, like the V1.40 notches), so the
    # curved shell never meets the window face in a knife edge; below 39.6 the corner and the flap root stay
    window = box((EXIT_X[0], WIN_Y[0], 25.0), (EXIT_X[1], WIN_Y[1], TOP + 1)) + box((CAP_OUT - 2, WIN_Y[0], WIN_REAR_Z0), (EXIT_X[0] + 0.5, WIN_Y[1], TOP + 1))
    body = body - window
    tabs = U([box((TAB_POST_X[0], a, LIP_Z[0]), (TAB_POST_X[1], b, ROOF_IN + 0.01)) for a, b in TAB_Y]
             + [box((TAB_LIP_X[0], a, LIP_Z[0]), (TAB_LIP_X[1], b, LIP_Z[1])) for a, b in TAB_Y])
    flap = U([box((CAP_OUT - FLAP_T, -FLAP_Y, FLAP_Z0), (CAP_OUT, FLAP_Y, Z_WALL + 1.6)),
              box((CAP_OUT - FLAP_T, -FLAP_Y, Z_WALL + CL), (CAP_OUT + 0.6, FLAP_Y, Z_WALL + 1.6))])   # root joins the curved corner
    bz0, bz1 = BUMP['z']
    bumps = prism_y([(CAP_OUT - 0.05, bz0), (CAP_OUT + BUMP['depth'], bz0 + BUMP['lead_in']), (CAP_OUT + BUMP['depth'], bz1),
                     (CAP_OUT - 0.05, bz1)], -BUMP['y'], BUMP['y'])
    hold = box((HOLD_X[0], HOLD_Y[0], HOLD_Z0), (HOLD_X[1], HOLD_Y[1], ROOF_IN + 0.37))
    hatch_free = body + tabs + hold + flap      # flap bump removed (flap held out)
    hatch = hatch_free + bumps
    battery = box(BAT_LO, BAT_HI)
    fixed = {'frame': frame, 'cap': cap, 'bars': bars, 'rear pack': pack, **env}

    ck = {}
    ck['solids'] = {n: dict(bodies=len(M.decompose()), status=str(M.status()), volume_cm3=r3(M.volume() / 1000))
                    for n, M in (('frame', frame), ('cap', cap), ('hatch', hatch))}
    ck['removed_cm3'] = dict(frame=r3((frame0.volume() - frame.volume()) / 1000), cap=r3((cap0.volume() - cap.volume()) / 1000))
    ck['closed_overlap_mm3'] = {n: r3(overlap(hatch, M)) for n, M in fixed.items()}
    ck['closed_overlap_mm3']['battery'] = r3(overlap(hatch, battery))
    ck['hold_down_gap_to_battery_top_mm'] = r3(HOLD_Z0 - BAT_HI[2])
    ck['bump_in_slot_overlap_mm3'] = r3(overlap(bumps, cap))
    ck['cap_cuts_mm'] = [[[CAP_IN, -OPEN_Y, 34.59], [BAR_BACK, OPEN_Y, 44.0]], [[CAP_OUT - 1, -OPEN_Y, Z_WALL], [CAP_IN + 0.01, OPEN_Y, 44.0]],
                         [[CAP_OUT - 0.1, -SLOT['y'], SLOT['z'][0]], [CAP_IN + 0.1, SLOT['y'], SLOT['z'][1]]],
                         [[POCKET_X[0], POCKET_Y[0], POCKET_Z[0]], [POCKET_X[1], POCKET_Y[1], POCKET_Z[1]]],
                         [[POCKET_X[0], -POCKET_Y[1], POCKET_Z[0]], [POCKET_X[1], -POCKET_Y[0], POCKET_Z[1]]]]   # every cut in the team cap, for make_manifest V1.41
    ck['ears'] = dict(x=[r3(v) for v in EAR_X], y=[r3(v) for v in EAR_Y], z=[r3(v) for v in EAR_Z],
                      pocket_x=POCKET_X, pocket_y=POCKET_Y, pocket_z=POCKET_Z, rear_gap_mm=r3(EAR_X[0] - POCKET_X[0]),
                      ear_volume_mm3=r3(ears.volume()))
    ck['tab_lip_engagement_mm'] = r3(TAB_LIP_X[1] - BAR_BACK)
    def posed(M, deg, back=0.0, up_=0.0):
        return M.translate(tuple(-PIVOT)).rotate((0, deg, 0)).translate(tuple(PIVOT)).translate((-back, 0, up_))
    up = 1 if to_tm(posed(box((CAP_IN, -1, ROOF_IN), (CAP_IN + 1, 1, TOP)), 10)).bounds[0, 2] > ROOF_IN else -1
    swing = {}
    for deg in (0, 1, 2, 4, 6, 8, 10, 12, 15, 18, 20, 22, 24):
        P = posed(hatch_free, up * deg)
        swing[deg] = {n: r3(v) for n, F in fixed.items() if (v := overlap(P, F)) > 0.01}
        swing[deg]['ears_vs_cap'] = r3(overlap(posed(ears, up * deg), cap))
    ck['hatch_swing_overlaps_mm3 (hatch_free: flap bump removed)'] = swing
    ck['removal_tilt_then_pull_back_overlaps_mm3 (flap out)'] = {
        f'{d}deg_back{b}': {n: r3(v) for n, F in fixed.items() if (v := overlap(posed(hatch_free, up * d, b), F)) > 0.01}
        for d in (15, 18, 22, 24) for b in (0.5, 1.0, 1.5)}
    ck['pull_back_stop_overlap_mm3 (closed, translated -x, flap bump removed; >0 = ears stop it)'] = {
        b: dict(hatch_vs_cap=r3(overlap(hatch_free.translate((-b, 0, 0)), cap)), ears_vs_cap=r3(overlap(ears.translate((-b, 0, 0)), cap)))
        for b in (0.25, 0.5, 1.0)}
    ck['pull_back_free_travel_mm'] = dict(ear_to_pocket_rear=r3(EAR_X[0] - POCKET_X[0]), front_lip_engagement=r3(TAB_LIP_X[1] - BAR_BACK))
    yc = EXIT_SIDE * 8.0
    def plug_sweep(dims):
        dx, dy, dz = dims
        return r3(max(overlap(box((LEADS_X - dx / 2, yc - dy / 2, BAT_HI[2] + h), (LEADS_X + dx / 2, yc + dy / 2, BAT_HI[2] + h + dz)), hatch)
                      for h in np.arange(0, 12.1, 0.5)))
    ck['xt30_pass_through_overlap_mm3'] = plug_sweep(XT30)
    ck['jst_pass_through_overlap_mm3'] = plug_sweep(JST)
    ck['window'] = dict(x=EXIT_X, y=[r3(v) for v in WIN_Y], size_mm=[r3(EXIT_X[1] - EXIT_X[0]), r3(WIN_Y[1] - WIN_Y[0])], EXIT_SIDE=EXIT_SIDE)
    bat_tab = battery + box((BAT_HI[0], -4, BAT_LO[2]), (BAT_HI[0] + 0.1, 4, BAT_HI[2]))
    ck['battery_lift_max_overlap_mm3'] = {n: r3(max(overlap(bat_tab.translate((0, 0, dz)), M) for dz in np.arange(0, 70.1, 2.5)))
                                         for n, M in fixed.items()}
    eps, L, x = flap_strain(RELEASE_MM)
    ck['flap'] = dict(thickness_mm=FLAP_T, length_mm=r3(L), root_to_bump_mm=r3(x), release_pull_mm=RELEASE_MM,
                      root_strain_pct=round(100 * eps, 2), bump_depth_mm=BUMP['depth'], slot=SLOT, retention_face='square (90 deg)')
    ck['hold_down'] = dict(x=HOLD_X, y=HOLD_Y, bottom_z=r3(HOLD_Z0), vs_window_overlap_mm3=r3(overlap(hold, window)))
    ck['shoulder_radius_from_hinge_mm'] = r3(r_sh)
    ck['hatch_mass_g'] = r3(hatch.volume() / 1000 * 1.24)

    poses = {'back_down': np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]], float)}
    def to_print(M, R):
        m = to_tm(M); T = np.eye(4); T[:3, :3] = R; m.apply_transform(T); m.apply_translation(-m.bounds[0]); return m, T
    def overhang(pm):
        n = pm.face_normals; zmin = pm.triangles[:, :, 2].min(axis=1)
        bad = (n[:, 2] < -np.cos(np.radians(45))) & (zmin > 0.2)
        return round(float(pm.area_faces[bad].sum()), 1)
    ck['hatch_print_overhang_over_45deg_mm2'] = overhang(to_print(hatch, poses['back_down'])[0])
    hatch_pose = 'back_down'
    Rb = poses['back_down']
    cuts = [(np.array(lo) - 3, np.array(hi) + 3) for lo, hi in (((CAP_IN, -OPEN_Y, BAT_HI[2]), (BAR_BACK, OPEN_Y, TOP)),
            ((POCKET_X[0], -POCKET_Y[1], POCKET_Z[0]), (POCKET_X[1], POCKET_Y[1], TOP)),
            ((CAP_OUT, -SLOT['y'], SLOT['z'][0]), (CAP_IN, SLOT['y'], SLOT['z'][1])))]
    def regions(pm, name): return [{k: r[k] for k in ('bbox', 'minMm', 'areaMm2', 'status') if k in r} for r in W.check(pm, (), name)['regions']]
    out = {}
    for name, M, M0, R in (('battery_backpack_frame', frame, frame0, Rb), ('battery_backpack_cap', cap, cap0, Rb),
                           ('battery_hatch', hatch, None, poses[hatch_pose])):
        to_tm(M).export(OUT / f'{name}-world.stl')
        pm, T = to_print(M, R); pm.export(OUT / f'{name}-print.stl')
        assert stl_closed(OUT / f'{name}-world.stl'), f'{name}: world STL not closed after export'
        bed = float(pm.area_faces[np.max(np.abs(pm.triangles[:, :, 2]), axis=1) <= .01].sum())
        now = [r for r in regions(pm, name) if r.get('status') == 'FAIL']
        new = now
        if M0 is not None:
            pm0, _ = to_print(M0, R)
            shift = (to_tm(M).bounds[0] - to_tm(M0).bounds[0]) @ R.T
            before = [r for r in regions(pm0, name) if r.get('status') == 'FAIL']
            cb = [np.mean(np.array(r['bbox']), axis=0) - shift for r in before]
            new = [r for r in now if not any(np.linalg.norm(np.mean(np.array(r['bbox']), axis=0) - c) < 2.0 for c in cb)]
            def world_c(r):
                w = R.T @ (np.mean(np.array(r['bbox']), axis=0) + to_tm(M).apply_transform(T).bounds[0])
                return w if any(np.all(w >= lo) and np.all(w <= hi) for lo, hi in cuts) else None
            new = [dict(r, worldCentre=[round(float(v), 2) for v in w]) for r in new if (w := world_c(r)) is not None]
        else:
            new = [dict(r, worldCentre=[round(float(v), 2) for v in R.T @ (np.mean(np.array(r['bbox']), axis=0)
                                        + to_tm(M).apply_transform(T).bounds[0])]) for r in now]
        out[name] = dict(pose='back_down' if R is Rb else hatch_pose, print_height_mm=r3(pm.bounds[1, 2]), bed_contact_mm2=round(bed, 1),
                         source_to_print=T.tolist(), thin_regions=len(now), new_thin_regions=new, world_stl_closed=True,
                         print_stl_closed=stl_closed(OUT / f'{name}-print.stl'))
    ck['print'] = out
    # extra meshes for the review sheet
    to_tm(ears).export(OUT / 'aux_ears-world.stl'); to_tm(hold).export(OUT / 'aux_hold-world.stl'); to_tm(flap + bumps).export(OUT / 'aux_flap-world.stl')
    (OUT / 'build.json').write_text(json.dumps(ck, indent=1, ensure_ascii=False, default=float))
    print(json.dumps(ck, indent=1, ensure_ascii=False, default=float))

main()
