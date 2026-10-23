"""D-023 left-rear head exit (Shawn 2026-10-23: "按这个做：重打颌支架和头底板放大左后出口").

The head wires leave the head at its left rear beside the jaw servo ID15. Today that passage is 6.4 mm: ID15 on one side,
the jaw support's left-rear corner walls and the head floor's ring wall on the other, with the M2.6 screw that holds the
jaw support's left-rear pad (H-jaw_support-01, at x 6.6, y 19) in the middle. This script opens a vertical dia 11 exit
there (PASSAGE) through both printed parts, removes the old screw seat (boss in the head floor, hole in the pad) and puts
a new seat on the pad's strip along the back of ID15 (NEW_SEAT): a dia 6 boss with a dia 2.2 M2.6 pilot in the head floor,
standing on the floor plane, and a dia 6.4 pad with a dia 2.8 clearance hole in the jaw support. Everything else of the
two parts is unchanged.

Inputs (robot frame, mm, guide world at HOME):
  head_bottom: guide/print/world/head_bottom.stl (the V1.8 lower head shell, printed Yellow)
  jaw_support: the V1.6 black release print file, registered to the world by v16-registration.json (printed Black)
Outputs here: head_bottom_exit.stl, jaw_support_exit.stl (world), *-print.stl (V1.8 / V1.6 print poses), checks.json.
    /tmp/microduck-cad-venv/bin/python build_neck_exit.py   (under run_bounded_cad.py)"""
import hashlib, json, math, sys, resource
from pathlib import Path
import numpy as np, trimesh
from shapely.geometry import Point, Polygon
HERE = Path(__file__).resolve().parent; GUIDE = HERE.parents[1]; WORLD = GUIDE / 'print/world'
CACHE = Path('/private/tmp/claude-501/-Users-xiangzheng-code-robotics/92b86901-7748-4ca5-958b-34f6db4ff94e/scratchpad/ia-cache')
REG = [r for r in json.loads((GUIDE / 'content/interference-audit/v16-registration.json').read_text()) if r['key'] == 'jaw_support'][0]
V18 = json.loads((GUIDE / 'print/release-V1.8/manifest-V1.8.json').read_text())
HB_T = np.array(next(r for r in V18['parts'] if r['key'] == 'head_bottom')['sourceToPrint'])
JS_T = np.linalg.inv(np.array(REG['transformReleaseToWorld']))

PASSAGE = dict(c=(10.0, 18.5), r=5.5)          # dia 11, vertical; ID15 (x >= 16.6 for y >= 14) 1.1 mm off its +x edge
OLD_SEAT = (6.6, 19.0)                          # H-jaw_support-01, removed (inside the passage)
NEW_SEAT = (11.6, 30.2)                         # on the pad strip behind ID15, on the head floor's ring wall
BOSS_R, PILOT_R, MOUTH_R = 3.0, 1.1, 1.4        # as the old seat: outer r 3.05..3.35, pilot r 1.1, mouth r 1.4 over the top 0.3
PAD_R, CLEAR_R = 3.2, 1.4                       # jaw support pad around the new hole; clearance hole as the old one (r 1.35..1.4)


def mem(t): print(t, round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20), 'MiB', flush=True)


# plan shapes (x, y) cut so no wall end thinner than 1.2 mm remains at the exit; the ring-wall cut ends square to the wall (x + y = 36.5)
RING_STUB = ((3.0, 21.0), (12.0, 21.0), (12.0, 24.5), (6.5, 30.0), (3.0, 30.0))
RIB_STUB = ((4.0, 13.2), (8.6, 17.0))
WALL_STUB_Y15 = ((4.6, 14.0), (12.0, 16.2))
WALL_STUB_DIAG = ((13.0, 18.0), (15.0, 21.8))
PLATE_STEP = ((4.6, 13.5), (8.0, 17.5))           # plate strip between its y 14.45 edge and the exit circle
# cable-tie window through the L-corner wall beside the exit (wall x 3.17..4.81, y 9.6..16.1, up to z 124.3): a 2.5 mm tie goes
# round the bundle, through the window and round the wall's free end, so a pull from the neck stops at the head and not at the plugs
TIE_WINDOW = ((2.8, 12.8), (5.2, 14.4)); TIE_Z = (116.0, 119.2)
RIGHT_WALL_END = ((14.0, 17.5), (17.0, 21.2))     # the x 15..16.3 wall and the plate under it end square at y 21.2, clear of the exit circle


def prism(pts, z0, z1):
    m = trimesh.creation.extrude_polygon(Polygon(pts), z1 - z0); m.apply_translation([0, 0, z0]); return m


def box3(xy, z0, z1):
    (x0, y0), (x1, y1) = xy
    b = trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0]); b.apply_translation([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2]); return b


def zcyl(r, x, y, z0, z1, n=72):
    c = trimesh.creation.cylinder(radius=r, height=z1 - z0, sections=n); c.apply_translation([x, y, (z0 + z1) / 2]); return c


def union(ms): return trimesh.boolean.union(ms, engine='manifold')
def diff(a, bs): return trimesh.boolean.difference([a] + list(bs), engine='manifold')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sec(m, z):
    s = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1]); g = Polygon()
    if s is None: return g
    for e in s.discrete:
        if len(e) >= 4:
            p = Polygon(e[:, :2]).buffer(0)
            if not p.is_empty: g = g.symmetric_difference(p)
    return g


hb = trimesh.load(WORLD / 'head_bottom.stl', force='mesh')
js = trimesh.load(REG['releaseFile'], force='mesh'); js.apply_transform(np.array(REG['transformReleaseToWorld']))
assert hb.is_volume and js.is_volume

mem('loaded')
# levels read off the parts
floor_bottom = float(hb.bounds[0, 2])
def ray_hits(m, x, y):
    loc, _, _ = m.ray.intersects_location([[x, y, 200.0]], [[0, 0, -1.0]])
    return sorted(loc[:, 2].tolist(), reverse=True)


old_boss_top = ray_hits(hb, OLD_SEAT[0] + 2.0, OLD_SEAT[1])[0]                    # top face of the old boss ring
hits_js = ray_hits(js, OLD_SEAT[0] - 2.0, OLD_SEAT[1] - 2.5)
plate_bot, plate_top = float(js.bounds[0, 2]), max(z for z in hits_js if z < 116.0)
floor_top = ray_hits(hb, 0.0, 20.0)[0]
print('floor bottom', round(floor_bottom, 2), 'floor top', round(floor_top, 2), 'old boss top', round(old_boss_top, 2), 'plate', round(plate_bot, 2), round(plate_top, 2))

mem('levels')
# ---------------------------------------------------------------- head floor
cx, cy = PASSAGE['c']
hb_cut = [zcyl(PASSAGE['r'], cx, cy, floor_bottom - 1.0, old_boss_top + 1.0),
          zcyl(BOSS_R + 0.45, *OLD_SEAT, floor_top - 0.02, old_boss_top + 1.0),          # the whole old boss above the floor plate
          prism(RING_STUB, floor_top - 0.02, old_boss_top + 1.0),                           # ring-wall end between the exit and the old boss
          box3(RIB_STUB, floor_top - 0.02, old_boss_top + 1.0)]                          # the short wall from the old boss to the y 12.5 rib
hb_new = diff(hb, hb_cut)
nx, ny = NEW_SEAT
boss = zcyl(BOSS_R, nx, ny, floor_bottom - 1.5, old_boss_top)                            # cut back to the bed plane below
hb_new = union([hb_new, boss])
hb_new = diff(hb_new, [zcyl(PILOT_R, nx, ny, floor_top + 0.5, old_boss_top + 1.0, 32), zcyl(MOUTH_R, nx, ny, old_boss_top - 0.3, old_boss_top + 1.0, 32)])

mem('head floor done')
# ---------------------------------------------------------------- jaw support
js_new = diff(js, [zcyl(PASSAGE['r'], cx, cy, plate_bot - 1.0, js.bounds[1, 2] + 1.0),
                   box3(WALL_STUB_Y15, plate_top, js.bounds[1, 2] + 1.0),                     # end of the y 15 wall left by the exit
                   box3(WALL_STUB_DIAG, plate_top, js.bounds[1, 2] + 1.0),                    # end of the diagonal wall left by the exit
                   box3(RIGHT_WALL_END, plate_bot - 1.0, js.bounds[1, 2] + 1.0),
                   box3(PLATE_STEP, plate_bot - 1.0, plate_top + 0.5),
                   box3(TIE_WINDOW, *TIE_Z)])
js_new = union([js_new, zcyl(PAD_R, nx, ny, plate_bot, plate_top)])
js_new = diff(js_new, [zcyl(CLEAR_R, nx, ny, plate_bot - 1.0, plate_top + 1.0, 32)])

mem('jaw support done')
# the boss stands on the bed: in the V1.8 print pose everything below the original bed plane is cut off, then mapped back
hb_p0 = hb.copy(); hb_p0.apply_transform(HB_T); BED = float(hb_p0.bounds[0, 2])
hb_p = hb_new.copy(); hb_p.apply_transform(HB_T)
lo, hi = hb_p.bounds; below = trimesh.creation.box(extents=[hi[0] - lo[0] + 20, hi[1] - lo[1] + 20, 10.0])
below.apply_translation([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, BED - 5.0])
hb_p = diff(hb_p, [below]); hb_new = hb_p.copy(); hb_new.apply_transform(np.linalg.inv(HB_T))
hb_p.apply_translation([0, 0, -BED]); hb_p0.apply_translation([0, 0, -BED])
for name, m in (('head_bottom_exit', hb_new), ('jaw_support_exit', js_new)):
    assert m.is_volume, name
    m.export(HERE / f'{name}.stl')
hb_p.export(HERE / 'head_bottom_exit-print.stl')
js_p = js_new.copy(); js_p.apply_transform(JS_T); js_p.apply_translation([0, 0, -js_p.bounds[0, 2]]); js_p.export(HERE / 'jaw_support_exit-print.stl')

mem('exported')
# ---------------------------------------------------------------- checks
def cache(k):
    z = np.load(CACHE / f'solid-{k}.npz'); return trimesh.Trimesh(z['v'], z['f'], process=False)


OTHERS = ['motor15', 'motor14', 'motor13', 'head_yaw_link', 'touch_xiao', 'neck_pitch', 'head_roll_ring_a', 'head_roll_ring_b', 'neck_pitch_ring', 'jaw_frame', 'speaker', 'amplifier']
O = {k: cache(k) for k in OTHERS}
def inter(a, b):
    try:
        r = trimesh.boolean.intersection([a, b], engine='manifold'); return round(float(r.volume), 3) if len(r.faces) else 0.0
    except Exception as e:
        return str(e)


def mind(a, b, n=1500):
    pts, _ = trimesh.sample.sample_surface(a, n, seed=1)
    return round(float(np.abs(trimesh.proximity.ProximityQuery(b).signed_distance(pts)).min()), 2)


mem('caches loaded')
feat = {'new_boss': boss, 'new_pad': zcyl(PAD_R, nx, ny, plate_bot, plate_top), 'screw_head': zcyl(2.5, nx, ny, plate_top + 0.15, plate_top + 2.0)}
clear = {f: {k: mind(m, O[k]) for k in OTHERS} for f, m in feat.items()}
inter_new = {k: {'head_bottom_exit': inter(hb_new, O[k]), 'jaw_support_exit': inter(js_new, O[k])} for k in OTHERS}
inter_old = {k: {'head_bottom': inter(hb, O[k]), 'jaw_support': inter(js, O[k])} for k in OTHERS}
inter_pair = {'new': inter(hb_new, js_new), 'old': inter(hb, js)}
screw_head_vs_js = mind(feat['screw_head'], js_new)
# vertical passage free diameter through both parts and their neighbours (z floor .. top of the jaw support)
def column(m_list, c, z0, z1):
    best = 1e9
    for z in np.arange(z0, z1, 1.0):
        for m in m_list:
            g = sec(m, z)
            if g.is_empty: continue
            best = min(best, 0.0 if g.contains(Point(*c)) else g.distance(Point(*c)))
    return round(2 * best, 2)


mem('clearances done')
col_new = column([hb_new, js_new] + [O[k] for k in ('motor15', 'motor14', 'motor13', 'head_yaw_link', 'touch_xiao')], PASSAGE['c'], floor_bottom + 0.2, float(js.bounds[1, 2]))
col_old = column([hb, js] + [O[k] for k in ('motor15', 'motor14', 'motor13', 'head_yaw_link', 'touch_xiao')], (13.6, 13.0), floor_bottom + 0.2, float(js.bounds[1, 2]))
mem('columns done')
bodies = {'head_bottom_exit': len(hb_new.split(only_watertight=False)), 'jaw_support_exit': len(js_new.split(only_watertight=False)),
          'head_bottom': len(hb.split(only_watertight=False)), 'jaw_support': len(js.split(only_watertight=False))}
# bed contact in the print poses
def contact(m): return round(float(m.area_faces[np.max(np.abs(m.triangles[:, :, 2]), axis=1) <= 0.01].sum()), 1)
out = dict(
    params=dict(PASSAGE=PASSAGE, OLD_SEAT=OLD_SEAT, NEW_SEAT=NEW_SEAT, BOSS_R=BOSS_R, PILOT_R=PILOT_R, MOUTH_R=MOUTH_R, PAD_R=PAD_R, CLEAR_R=CLEAR_R,
                floorBottom=round(floor_bottom, 3), floorTop=round(floor_top, 3), oldBossTop=round(old_boss_top, 3), plate=[round(plate_bot, 3), round(plate_top, 3)]),
    passageDiaMm=dict(new=col_new, old_at_13_6_13=col_old),
    volumesMm3=dict(head_bottom=round(hb.volume, 1), head_bottom_exit=round(hb_new.volume, 1), jaw_support=round(js.volume, 1), jaw_support_exit=round(js_new.volume, 1)),
    bodies=bodies, newFeatureClearanceMm=clear, screwHeadToJawSupportWallsMm=screw_head_vs_js,
    intersectionWithNeighboursMm3=dict(new=inter_new, old=inter_old), headBottomJawSupportOverlapMm3=inter_pair,
    printPoses=dict(head_bottom=dict(file='head_bottom_exit-print.stl', heightMm=round(float(hb_p.bounds[1, 2]), 2), bedContactMm2=contact(hb_p), v18BedContactMm2=contact(hb_p0), minZ=round(float(hb_p.bounds[0, 2]), 4), pose='V1.8 head_bottom.sourceToPrint'),
                    jaw_support=dict(file='jaw_support_exit-print.stl', heightMm=round(float(js_p.bounds[1, 2]), 2), bedContactMm2=contact(js_p), pose='V1.6 release print pose (inverse of v16-registration transformReleaseToWorld)')),
    sha256={n: sha(HERE / n) for n in ('head_bottom_exit.stl', 'jaw_support_exit.stl', 'head_bottom_exit-print.stl', 'jaw_support_exit-print.stl')})
sys.path.insert(0, str(GUIDE.parent / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'))
import wall_check  # noqa: E402
ZONE_W = [((cx - 9.5, cy - 9.5), (cx + 9.5, cy + 9.5)), ((nx - 5.0, ny - 5.0), (nx + 5.0, ny + 5.0))]   # world plan boxes around the changes
def zone_regions(mprint, T, key):
    Ti = np.linalg.inv(T); res = []
    for g in wall_check.check(mprint.copy(), (), key)['regions']:
        if g['status'] != 'FAIL': continue
        lo, hi = np.array(g['bbox'])
        corners = np.array([[x, y, z, 1] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]) @ Ti.T
        wlo, whi = corners[:, :3].min(0), corners[:, :3].max(0)
        inz = any(wlo[0] < b[1][0] and whi[0] > b[0][0] and wlo[1] < b[1][1] and whi[1] > b[0][1] for b in ZONE_W)
        res.append(dict(g, worldBbox=[wlo.round(2).tolist(), whi.round(2).tolist()], inChangeZone=bool(inz)))
    return res
Thb = HB_T.copy(); Thb[2, 3] -= BED
js_p0 = js.copy(); js_p0.apply_transform(JS_T); Tjs = JS_T.copy(); Tjs[2, 3] -= float(js_p0.bounds[0, 2]); js_p0.apply_translation([0, 0, -js_p0.bounds[0, 2]])
out['wallCheck'] = {'head_bottom': zone_regions(hb_p, Thb, 'head_bottom'), 'jaw_support': zone_regions(js_p, Tjs, 'jaw_support'),
                    'head_bottom_v18': zone_regions(hb_p0, Thb, 'head_bottom'), 'jaw_support_v16': zone_regions(js_p0, Tjs, 'jaw_support')}
for k in ('head_bottom', 'jaw_support'):
    bad = [g for g in out['wallCheck'][k] if g['inChangeZone']]
    print('wall check', k, 'FAIL regions in the change zone:', [(g['minMm'], g['areaMm2'], g['worldBbox']) for g in bad])
(HERE / 'checks.json').write_text(json.dumps(out, indent=1) + '\n')
print(json.dumps({k: out[k] for k in ('passageDiaMm', 'volumesMm3', 'bodies', 'screwHeadToJawSupportWallsMm', 'headBottomJawSupportOverlapMm3', 'printPoses')}, indent=1))
print('clearances', json.dumps(clear))
