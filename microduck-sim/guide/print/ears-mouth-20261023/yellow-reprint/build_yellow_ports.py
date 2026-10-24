"""Six sound holes in the yellow lower head shell (head_bottom) above the lower jaw, reprint option for release V1.32.

The speaker sits just above the mouth; its sound leaves the head through six vertical dia 2.5 holes in the flat 2.8 mm
floor plate right above the lower jaw (interface.json `port_holes`, world frame mm, x forward, y left, z up). A paper drill
template for the same holes is made separately; both use these centres and this diameter.

Inputs:
  ../interface.json                      port_holes: centres, diameter, floor z range
  guide/print/world/head_bottom.stl      V1.30 lower shell, world frame (output of neck-exit-20261023/build_neck_exit.py)
  release-V1.30/manifest-V1.30.json      head_bottom row: sha256 of the world file, sourceToPrint, poseCheck print file
Outputs here:
  head_bottom_ports-world.stl            world frame
  head_bottom_ports-print.stl            V1.30 print pose: sourceToPrint (= V1.8 pose, floor on the bed), then the same
                                         bed drop as the V1.30 print file (neck-exit-20261023/head_bottom_exit-print.stl)
  checks.json, floor_ports.png
    /tmp/microduck-cad-venv/bin/python build_yellow_ports.py   (under run_bounded_cad.py)"""
import hashlib, json, math, sys
from pathlib import Path
import numpy as np, trimesh
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent; PRINT = HERE.parents[1]; GUIDE = PRINT.parent
IFACE = json.loads((HERE.parent / 'interface.json').read_text())['port_holes']
ROW = next(r for r in json.loads((PRINT / 'release-V1.30/manifest-V1.30.json').read_text())['parts'] if r['key'] == 'head_bottom')
WORLD_IN = Path(ROW['path']); PRINT_V130 = Path(ROW['poseCheck']['printStl']['path'])
R = IFACE['diameter_mm'] / 2; SEG = 32
CENTRES = [tuple(map(float, c)) for c in IFACE['centres_xy']]
Z_BOT, Z_TOP = float(IFACE['floor_bottom_z']), float(IFACE['floor_top_z'])
MIN_WALL = 1.2


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def diff(a, bs): return trimesh.boolean.difference([a] + list(bs), engine='manifold')
def inter(a, b): return trimesh.boolean.intersection([a, b], engine='manifold')
def vol(m): return float(m.volume) if len(m.faces) else 0.0


def zcyl(r, x, y, z0, z1, n=SEG):
    c = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=n); c.apply_translation([x, y, (z0 + z1) / 2]); return c


def ray_hits(m, x, y):
    loc, _, _ = m.ray.intersects_location([[x, y, 200.0]], [[0, 0, -1.0]])
    return sorted(np.round(loc[:, 2], 4).tolist(), reverse=True)


def sec(m, z):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1]); g = Polygon()
    if s is None: return g
    for e in s.discrete:
        if len(e) >= 4:
            p = Polygon(e[:, :2]).buffer(0)
            if not p.is_empty: g = g.symmetric_difference(p)
    return g


assert sha(WORLD_IN) == ROW['sha256'], 'world/head_bottom.stl is not the V1.30 file'
hb = trimesh.load(WORLD_IN, force='mesh'); assert hb.is_volume
# ---------------------------------------------------------------- the floor at each hole: rays at the centre and on the rim
probe = {}
for i, (x, y) in enumerate(CENTRES):
    pts = [(x, y)] + [(x + R * math.cos(a), y + R * math.sin(a)) for a in np.radians(np.arange(0, 360, 45))]
    hits = [ray_hits(hb, px, py) for px, py in pts]
    assert all(len(h) == 2 for h in hits), (i, hits)        # one plate, nothing above or below it
    top = [h[0] for h in hits]; bot = [h[1] for h in hits]
    probe[f'P{i + 1}'] = dict(centre=[x, y], topZ=[round(min(top), 3), round(max(top), 3)], bottomZ=[round(min(bot), 3), round(max(bot), 3)],
                              thicknessAtCentreMm=round(hits[0][0] - hits[0][1], 3))
z_lo = min(p['bottomZ'][0] for p in probe.values()); z_hi = max(p['topZ'][1] for p in probe.values())
# ---------------------------------------------------------------- holes: 32-segment cylinders 1 mm past both faces
CYL = [zcyl(R, x, y, z_lo - 1.0, z_hi + 1.0) for x, y in CENTRES]
new = diff(hb, CYL)
assert new.is_volume
# ---------------------------------------------------------------- print pose: the V1.30 transform, read back from its files
S2P = np.array(ROW['sourceToPrint'])
v130_print = trimesh.load(PRINT_V130, force='mesh'); assert sha(PRINT_V130) == ROW['poseCheck']['printStl']['sha256']
hb_rot = hb.copy(); hb_rot.apply_transform(S2P); drop = -float(hb_rot.bounds[0, 2])
T = S2P.copy(); T[2, 3] += drop                                   # world -> print (V1.30)
def max_dev(a_world, b_print):
    va = trimesh.transform_points(a_world.vertices, T); d, _ = cKDTree(b_print.vertices).query(va)
    d2, _ = cKDTree(va).query(b_print.vertices); return float(max(d.max(), d2.max()))
v130_dev = max_dev(hb, v130_print)
assert v130_dev < 1e-4, v130_dev
new_p = new.copy(); new_p.apply_transform(T)
assert abs(new_p.bounds[0, 2]) < 1e-6, new_p.bounds              # still on the bed: the holes do not touch the lowest points
new.export(HERE / 'head_bottom_ports-world.stl'); new_p.export(HERE / 'head_bottom_ports-print.stl')
W = trimesh.load(HERE / 'head_bottom_ports-world.stl', force='mesh'); P = trimesh.load(HERE / 'head_bottom_ports-print.stl', force='mesh')
pose_dev = max_dev(W, P)
# ---------------------------------------------------------------- volumes and symmetric difference
removed = vol(hb) - vol(new)
in_cyl = sum(vol(inter(hb, c)) for c in CYL)                     # material of the old shell inside the six cylinders
poly_area = 0.5 * SEG * R * R * math.sin(2 * math.pi / SEG)
expected_round = 6 * math.pi * R * R * 2.8
expected_poly_measured = sum(poly_area * p['thicknessAtCentreMm'] for p in probe.values())
old_minus_new = diff(hb, [new]); new_minus_old = diff(new, [hb])
removed_outside = vol(diff(old_minus_new, CYL)) if len(old_minus_new.faces) else 0.0
added = vol(new_minus_old)
# new vertices that are neither old vertices nor on a hole wall
old_tree = cKDTree(hb.vertices)
d_old, _ = old_tree.query(W.vertices)
rad = np.min([np.hypot(W.vertices[:, 0] - x, W.vertices[:, 1] - y) for x, y in CENTRES], axis=0)
on_wall = (np.abs(rad - R) < 1e-3) | (np.abs(rad - R * math.cos(math.pi / SEG)) < 1e-3) | (rad <= R + 1e-3)
stray = int(((d_old > 1e-4) & ~on_wall).sum())
# ---------------------------------------------------------------- material round each hole
def hole_ring(g, x, y):
    for poly in getattr(g, 'geoms', [g]):
        for ring in poly.interiors:
            rp = Polygon(ring)
            if rp.contains(Point(x, y)) and rp.area < 6.0: return poly, ring
    return None, None


levels_in = [round(z_lo + 0.15, 3), round((z_lo + z_hi) / 2, 3), round(z_hi - 0.15, 3)]
levels_above = [round(z_hi + d, 3) for d in (0.2, 1.0, 2.0, 4.0, 8.0)]
mat = {}
for i, (x, y) in enumerate(CENTRES):
    rec = {'inFloor': {}, 'aboveFloor': {}}
    for z in levels_in:
        g = sec(new, z); poly, ring = hole_ring(g, x, y)
        assert ring is not None, (i, z)
        hole = Polygon(ring)
        others = [poly.exterior] + [r for r in poly.interiors if not Polygon(r).equals(hole)]
        dists = sorted(((round(hole.exterior.distance(o), 3), 'other hole' if (o is not poly.exterior and Polygon(o).area < 6) else ('plate edge' if o is poly.exterior else 'other opening')) for o in others))
        non_hole = [d for d in dists if d[1] != 'other hole']
        rec['inFloor'][f'z{z}'] = dict(holeDiaFromAreaMm=round(2 * math.sqrt(hole.area / math.pi), 3), nearestEdgeMm=dists[0][0], nearestKind=dists[0][1],
                                       nearestPlateEdgeOrOpeningMm=non_hole[0][0] if non_hole else None)
    for z in levels_above:
        g = sec(new, z)
        d = round(g.distance(Point(x, y)) - R, 3) if not g.is_empty else None
        rec['aboveFloor'][f'z{z}'] = dict(holeEdgeToNearestSolidMm=d)
    rec['minInFloorMm'] = min(v['nearestEdgeMm'] for v in rec['inFloor'].values())
    mat[f'P{i + 1}'] = rec
min_web = min(r['minInFloorMm'] for r in mat.values())
# nearest wall or rib standing on the floor, measured from the hole edge at the floor top
g_above = sec(new, z_hi + 0.2)
wall_near = {f'P{i + 1}': (round(g_above.distance(Point(x, y)) - R, 3) if not g_above.is_empty else None) for i, (x, y) in enumerate(CENTRES)}
# ---------------------------------------------------------------- release wall check on the print pose, holes zone
sys.path.insert(0, str(GUIDE.parent / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'))
import wall_check  # noqa: E402
ZONE = ((min(c[0] for c in CENTRES) - 4, min(c[1] for c in CENTRES) - 4), (max(c[0] for c in CENTRES) + 4, max(c[1] for c in CENTRES) + 4))
Ti = np.linalg.inv(T)
ALLOW = wall_check.allowances(ROW)                                 # the V1.30 row's thinWallAllowances (print frame)
def zone_fail(mp):
    wc = wall_check.check(mp.copy(), ALLOW, 'head_bottom'); res = []
    for g in wc['regions']:
        lo, hi = np.array(g['bbox'])
        c = np.array([[a, b, cc, 1] for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for cc in (lo[2], hi[2])]) @ Ti.T
        wlo, whi = c[:, :3].min(0), c[:, :3].max(0)
        inz = bool(wlo[0] < ZONE[1][0] and whi[0] > ZONE[0][0] and wlo[1] < ZONE[1][1] and whi[1] > ZONE[0][1])
        res.append(dict(status=g['status'], minMm=g['minMm'], areaMm2=g['areaMm2'], worldBbox=[wlo.round(2).tolist(), whi.round(2).tolist()], inHoleZone=inz))
    return dict(passed=wc['passed'], failures=wc['failures'], regions=res, inHoleZone=[r for r in res if r['inHoleZone']])
wc_new = zone_fail(P); wc_old = zone_fail(v130_print)
# The sampler (sample_surface_even, fixed seed, capped count) draws a new point set when the surface changes, so thin regions
# of the unchanged shell regroup and their bboxes no longer sit inside the V1.30 allowance boxes. Evidence that every thin
# sample of the new part lies on the unchanged V1.30 surface, away from the hole walls:
meas = wall_check.measure(P.copy()); thin = meas['smoothed'] < wall_check.MIN_WALL_MM - wall_check.MEASURE_TOL_MM
tp = meas['points'][thin]
d_v130 = np.abs(trimesh.proximity.closest_point(v130_print, tp)[1]) if len(tp) else np.zeros(0)
tw = trimesh.transform_points(tp, Ti)
d_hole = np.min([np.hypot(tw[:, 0] - x, tw[:, 1] - y) for x, y in CENTRES], axis=0) - R if len(tp) else np.zeros(0)
hole_pts = np.min([np.hypot(trimesh.transform_points(meas['points'], Ti)[:, 0] - x, trimesh.transform_points(meas['points'], Ti)[:, 1] - y) for x, y in CENTRES], axis=0) <= R + 3.0
thin_evidence = dict(thinSamples=int(thin.sum()), thinSamplesOffV130SurfaceOver0p001Mm=int((d_v130 > 1e-3).sum()),
                     minDistanceThinSampleToHoleWallMm=round(float(d_hole.min()), 2) if len(tp) else None,
                     samplesWithin3mmOfHoleWalls=int(hole_pts.sum()),
                     minSmoothedThicknessWithin3mmOfHoleWallsMm=round(float(meas['smoothed'][hole_pts].min()), 3) if hole_pts.any() else None)
proposed = [dict(bbox=[[round(v - 0.05, 3) for v in r['bbox'][0]], [round(v + 0.05, 3) for v in r['bbox'][1]]], minMm=round(max(0.01, r['minMm'] - 0.005), 3),
                 reason=f'unchanged V1.30 lower head shell surface (sound-hole reprint resampled by the wall check): area {r["areaMm2"]} mm2, min {r["minMm"]} mm; '
                        f'{thin_evidence["thinSamplesOffV130SurfaceOver0p001Mm"]} of {thin_evidence["thinSamples"]} thin samples off the V1.30 surface')
            for r in wall_check.check(P.copy(), ALLOW, 'head_bottom')['regions'] if r['status'] == 'FAIL']
print('thin evidence', thin_evidence)
# ---------------------------------------------------------------- checks.json
bodies = len(W.split(only_watertight=False))
contact = lambda m: round(float(m.area_faces[np.max(np.abs(m.triangles[:, :, 2]), axis=1) <= 0.01].sum()), 2)
out = dict(
    interface=dict(file=str(HERE.parent / 'interface.json'), diameterMm=IFACE['diameter_mm'], centresXY=CENTRES, floorZ=[Z_BOT, Z_TOP]),
    holes=dict(segments=SEG, vertexRadiusMm=R, acrossFlatsDiaMm=round(2 * R * math.cos(math.pi / SEG), 3), cylinderZ=[round(z_lo - 1, 3), round(z_hi + 1, 3)],
               axis='world z (the floor plate is tilted 0.49 deg about y in the world; in the print pose the hole axis is 0.49 deg off the print z)'),
    floorProbe=probe,
    inputs=dict(world=dict(path=str(WORLD_IN), sha256=sha(WORLD_IN)), v130Print=dict(path=str(PRINT_V130), sha256=sha(PRINT_V130))),
    body=dict(bodies=bodies, isVolume=bool(W.is_volume), isWatertight=bool(W.is_watertight), windingConsistent=bool(W.is_winding_consistent),
              euler=int(W.euler_number), eulerBefore=int(hb.euler_number), printIsVolume=bool(P.is_volume)),
    volumesMm3=dict(before=round(vol(hb), 3), after=round(vol(W), 3), removed=round(removed, 3), oldMaterialInsideCylinders=round(in_cyl, 3),
                    expectedRoundHoles2p8=round(expected_round, 3), expectedPolygonHolesMeasuredThickness=round(expected_poly_measured, 3),
                    note='32-gon area is 0.64 % under the circle; the plate measures the thickness listed per hole in floorProbe'),
    symmetricDifference=dict(removedOutsideCylindersMm3=round(removed_outside, 6), addedMm3=round(added, 6), strayNewVerticesOffHoleWalls=stray),
    materialAroundHoles=dict(minWebInFloorMm=min_web, perHole=mat, holeEdgeToNearestWallOrRibAtFloorTopMm=wall_near,
                             thinnerThan1p2=[k for k, r in mat.items() if r['minInFloorMm'] < MIN_WALL]),
    wallCheckPrintPose=dict(allowances='manifest-V1.30 head_bottom thinWallAllowances', zoneWorldXY=ZONE, thinSampleEvidence=thin_evidence,
                            proposedAllowancesForFailingRegions=proposed,
                            new=dict(passed=wc_new['passed'], failures=wc_new['failures'], inHoleZone=wc_new['inHoleZone'], regions=wc_new['regions']),
                            v130=dict(passed=wc_old['passed'], failures=wc_old['failures'], inHoleZone=wc_old['inHoleZone'], regions=wc_old['regions'])),
    printPose=dict(file='head_bottom_ports-print.stl', transformWorldToPrint=np.round(T, 12).tolist(), bedDropMm=round(drop, 6),
                   v130TransformCheckMaxDevMm=v130_dev, printEqualsWorldUnderTransformMaxDevMm=pose_dev,
                   bedContactMm2=contact(P), v130BedContactMm2=contact(v130_print), sizeMm=np.round(P.extents, 2).tolist(), v130SizeMm=np.round(v130_print.extents, 2).tolist()),
    outputs={n: sha(HERE / n) for n in ('head_bottom_ports-world.stl', 'head_bottom_ports-print.stl')})
(HERE / 'checks.json').write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps({k: out[k] for k in ('floorProbe', 'body', 'volumesMm3', 'symmetricDifference', 'printPose')}, indent=1))
print('min web', min_web, 'wall near', wall_near, 'thin', out['materialAroundHoles']['thinnerThan1p2'])
print('wall check new passed', wc_new['passed'], wc_new['failures'], 'zone', wc_new['inHoleZone'])
print('wall check v130 passed', wc_old['passed'], wc_old['failures'], 'zone', wc_old['inHoleZone'])

# ---------------------------------------------------------------- render: whole floor section, hole close-up, 3D close-up
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


def draw(ax, g, **kw):
    for poly in getattr(g, 'geoms', [g]):
        if poly.is_empty or poly.geom_type != 'Polygon': continue
        ax.fill(*poly.exterior.xy, **kw)
        for r in poly.interiors: ax.fill(*r.xy, color='white', ec=kw.get('ec', 'k'), lw=kw.get('lw', 0.6))


fig = plt.figure(figsize=(18, 6.4), facecolor='white')
zm = levels_in[1]; g_mid = sec(new, zm); g_wall = sec(new, z_hi + 1.0)
box = Polygon([(56, -15), (80, -15), (80, 9), (56, 9)])
ax0 = fig.add_subplot(1, 3, 1)
draw(ax0, g_wall, color='#b0882a', alpha=0.5, ec='#5a4000', lw=0.4)
draw(ax0, g_mid, color='#f2c94c', alpha=0.85, ec='#7a5c00', lw=0.5)
ax0.plot(*box.exterior.xy, color='#c0392b', lw=1.2)
ax0.set_aspect('equal'); ax0.grid(alpha=0.25); ax0.set_xlabel('world x (mm, forward)'); ax0.set_ylabel('world y (mm, left)')
ax0.set_title(f'Whole lower shell: floor at z {zm} (yellow), walls at z {z_hi + 1:.1f} (brown)\nred box = close-up', fontsize=10)
ax = fig.add_subplot(1, 3, 2)
draw(ax, g_wall.intersection(box), color='#b0882a', alpha=0.5, ec='#5a4000', lw=0.6)
draw(ax, g_mid.intersection(box), color='#f2c94c', ec='#7a5c00', lw=0.8)
for i, (x, y) in enumerate(CENTRES):
    ax.annotate(f'P{i + 1}\n({x:g}, {y:g})', (x, y), xytext=(0, 13), textcoords='offset points', ha='center', fontsize=8)
ax.set_aspect('equal'); ax.set_xlim(56, 80); ax.set_ylim(-15, 9); ax.grid(alpha=0.25)
ax.set_xlabel('world x (mm, forward)'); ax.set_ylabel('world y (mm, left)')
ax.set_title(f'Close-up: 6 x dia {2 * R:g} through the {Z_TOP - Z_BOT:.1f} mm floor\nweb between holes {min_web:.2f} mm (minimum 1.2)', fontsize=10)
ax3 = fig.add_subplot(1, 3, 3, projection='3d')
lo, hi = np.array([56.0, -15.0, z_lo - 1]), np.array([80.0, 9.0, z_hi + 4])
clip = W.copy()
for o, n in (((lo[0], 0, 0), (1, 0, 0)), ((hi[0], 0, 0), (-1, 0, 0)), ((0, lo[1], 0), (0, 1, 0)), ((0, hi[1], 0), (0, -1, 0)),
             ((0, 0, lo[2]), (0, 0, 1)), ((0, 0, hi[2]), (0, 0, -1))):
    clip = clip.slice_plane(o, n)
light = np.array([0.4, -0.3, 0.85]); light /= np.linalg.norm(light)
shade = 0.35 + 0.65 * np.clip(clip.face_normals @ light, 0, 1)
ax3.add_collection3d(Poly3DCollection(clip.triangles, facecolors=np.c_[0.95 * shade, 0.79 * shade, 0.30 * shade, np.ones_like(shade)], edgecolor='none'))
ax3.set_xlim(lo[0], hi[0]); ax3.set_ylim(lo[1], hi[1]); ax3.set_zlim((lo[2] + hi[2]) / 2 - 12, (lo[2] + hi[2]) / 2 + 12)
ax3.view_init(elev=50, azim=-115); ax3.set_box_aspect((1, 1, 1))
ax3.set_xlabel('x'); ax3.set_ylabel('y'); ax3.set_zlabel('z')
ax3.set_title('head_bottom_ports-world.stl, close-up from above (inside of the head)', fontsize=10)
fig.tight_layout(); fig.savefig(HERE / 'floor_ports.png', dpi=130)
print('render', HERE / 'floor_ports.png')
