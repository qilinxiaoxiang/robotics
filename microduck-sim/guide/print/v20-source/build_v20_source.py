"""V2.0 source: torso side shells screwed down onto the V1.9 rear pack, and the jaw frame without its unused pivot hole.

Shawn, 2026-10-13: the rear cross screw (27 mm deep tunnel) is too hard to drive; fix each shell to the rear pack instead, and
remove the hole in the passive jaw arm. Both go into V2.0. The V1.9 rear pack is being printed and stays unchanged.

Inputs are the audit solid cache (world = guide frame, mm, x forward, y left, z up): shell_left / shell_right (printed 10/1
shells), rear_pack (V1.9), jaw_frame (V1.8, lower lip merged). Changes:
 (1) Shell-to-pack screws. One vertical M2 x 6 per shell, down through the shell roof into the pack's shoulder bar
     (bar + plate solid x -23.9..-19.1, from z 31.6 to the bar top). Axis x -21.5, y +-20. Shell: dia 2.2 clearance hole and a
     dia 4.4 counterbore 1.0 mm deep. Pack: no change to the print; the dia 1.6 pilot is drilled through the shell hole.
 (2) Cross tunnels filled. Both shells' x -38, z 35 tunnels (bores, clearance hole and pilot) are filled flush with the outer
     skin, so no hole shows outside and no unused tube stays open. The 0.9 mm seam between the shells stays open.
 (3) Horn-screw counterbores dia 4.4 x 2.0 on S12-horn-026..032 (carried from ../shells-v19-source, Shawn's next-reprint item):
     those seven become M2 x 4. S12-horn-025 keeps its flat seat (V1.9 torso wire clip under its head).
 (4) Jaw frame: the dia 2.0 hole on the pivot axis in the passive (-y) arm is filled. Nothing uses it.
Writes shell_left_v20-world.stl, shell_right_v20-world.stl, jaw_frame_v20-world.stl and v20-source.json here.
Run under the bounded CAD runner.
"""
import sys, json, hashlib, time
from pathlib import Path
import numpy as np
import trimesh
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'rear-pack'))
import pack_lib as P  # noqa: E402
import ia_lib  # noqa: E402
from cables import spline_samples  # noqa: E402

t0 = time.time()
G = HERE.parent.parent
V19 = json.load(open(HERE.parent / 'shells-v19-source' / 'shells-v19-source.json'))
fast = {f['id']: f for f in json.load(open(G / 'content' / 'fasteners.json'))['screws']}
data = json.load(open(G / 'data' / 'guide-data.json'))
man = ia_lib.manifest()
KEYS = ('shell_left', 'shell_right', 'rear_pack', 'jaw_frame')
res = {'inputs': {k: dict(path=str(ia_lib.solid_path(k)), sha256=hashlib.sha256(ia_lib.solid_path(k).read_bytes()).hexdigest(),
                          volumeMm3=round(float(P.solid_mesh(k).volume), 2)) for k in KEYS}}
SL_mesh, SR_mesh, PK_mesh, JF_mesh = (P.solid_mesh(k) for k in KEYS)
SL, SR, PK, JF = (P.mesh_to_m(m) for m in (SL_mesh, SR_mesh, PK_mesh, JF_mesh))

present = set()
for s in data['steps']:
    present |= set(s.get('show', [])) | set(s.get('add', []))
present -= set(P.RETIRED)
cab_samples = []
for c in data['cables']:
    x, _ = spline_samples(np.array(c['path'], float)); cab_samples.append((c['id'], float(c.get('radius') or 0.9), x))


def ray_hits(mesh, o, d):
    loc, _, _ = mesh.ray.intersects_location(np.array([o], float), np.array([d], float), multiple_hits=True)
    if not len(loc):
        return np.array([])
    return np.sort(np.linalg.norm(loc - np.array(o), axis=1))


def others(solid, lo, hi, skip=(), within=3.0):
    """Every final-pose guide part that overlaps the solid or comes within `within` mm of it."""
    out = {}
    for k in sorted(present):
        if k not in man or k in skip:
            continue
        b = np.array(man[k]['bounds'])
        if np.any(b[0] > hi + within) or np.any(b[1] < lo - within):
            continue
        S = P.solid_m(k)
        v = float((solid ^ S).volume()); g = float(solid.min_gap(S, within))
        if v > 1e-4 or g < within:
            out[k] = dict(overlapMm3=round(v, 4), gapMm=round(g, 3))
    return out


def cable_exact(solid):
    mesh = P.from_m(solid); best = (99.0, None, None)
    for cid, r, x in cab_samples:
        near = np.linalg.norm(x - mesh.centroid, axis=1) < 40.0
        if not near.any():
            continue
        _, d, _ = trimesh.proximity.closest_point(mesh, x[near])
        k = int(np.argmin(d))
        if d[k] - r < best[0]:
            best = (round(float(d[k] - r), 2), cid, np.round(x[near][k], 1).tolist())
    return best


# ---------------------------------------------------------------- (1) shell-to-pack screws
SX = -21.5
HEAD_D, HEAD_H, LEAD, PILOT_R, CB_R, CB_DEPTH, CLEAR_R = 4.0, 1.6, 0.3, 0.8, 2.2, 1.0, 1.1
SCREW_L = 6.0
res['packScrews'] = {}
cuts = {'shell_left': [], 'shell_right': []}
pilots = []
screws = {}
for key, sy in (('shell_left', 20.0), ('shell_right', -20.0)):
    mesh = SL_mesh if key == 'shell_left' else SR_mesh
    # roof top and underside along the axis and on the counterbore rim (r 2.2)
    tops, unders = [], []
    for ang in [None] + list(np.linspace(0, 2 * np.pi, 16, endpoint=False)):
        off = np.zeros(3) if ang is None else np.array([np.cos(ang), np.sin(ang), 0.0]) * CB_R
        h = ray_hits(mesh, np.array([SX, sy, 80.0]) + off, [0, 0, -1])
        tops.append(80.0 - h[0]); unders.append(80.0 - h[1])
    z_top_axis, z_top_max, z_top_min = tops[0], max(tops), min(tops)
    z_under = max(unders)
    hp = ray_hits(PK_mesh, [SX, sy, 80.0], [0, 0, -1])
    bar_top, bar_bot = 80.0 - hp[0], 80.0 - hp[1]
    seat = z_top_max - CB_DEPTH                      # counterbore floor = head seat (flat), measured from the highest rim point
    tip = seat - SCREW_L
    in_bar = bar_top - tip
    eng = in_bar - LEAD
    pilot_bot = tip - 0.5
    cb = P.cyl_z(CB_R, seat, z_top_max + 5.0, SX, sy)
    hole = P.cyl_z(CLEAR_R, z_under - 1.0, seat + 0.01, SX, sy)
    cuts[key] += [cb, hole]
    pilot = P.cyl_z(PILOT_R, pilot_bot, bar_top + 0.5, SX, sy)
    pilots.append(pilot)
    head = P.cyl_z(HEAD_D / 2, seat, seat + HEAD_H, SX, sy)
    shank = P.cyl_z(1.0, tip, seat, SX, sy)
    screws[key] = (head, shank)
    # pilot walls in the bar along x (the bar is narrow in x)
    xs = np.arange(-26.0, -17.0, 0.02)
    zc = (bar_top + tip) / 2
    inside = PK_mesh.contains(np.c_[xs, np.full_like(xs, sy), np.full_like(xs, zc)])
    bx0, bx1 = float(xs[inside].min()), float(xs[inside].max())
    res['packScrews'][key] = dict(
        spec=f'M2 x {SCREW_L:g} TAP, pan head dia {HEAD_D} x {HEAD_H} assumed', axis=[0, 0, -1], center=[SX, sy, round(seat, 3)],
        roofTopZ=dict(onAxis=round(z_top_axis, 3), rimMax=round(z_top_max, 3), rimMin=round(z_top_min, 3)), roofUndersideZ=round(z_under, 3),
        counterbore=f'dia {2 * CB_R:g}, floor at z {seat:.2f} ({CB_DEPTH} mm below the highest rim point)',
        roofLeftUnderHeadMm=round(seat - z_under, 3), headTopAboveRoofMm=round(seat + HEAD_H - z_top_max, 3),
        gapRoofToPackMm=round(z_under - bar_top, 3), packBarTopZ=round(bar_top, 3), packBarBottomZ=round(bar_bot, 3),
        tipZ=round(tip, 3), shankInBarMm=round(in_bar, 3), engagementMm=round(eng, 3), tipAboveBarBottomMm=round(tip - bar_bot, 3),
        barAlongX=[round(bx0, 2), round(bx1, 2)], pilotWallMm=dict(rear=round(SX - PILOT_R - bx0, 2), front=round(bx1 - SX - PILOT_R, 2)),
        pilotDrill=dict(dia=2 * PILOT_R, bottomZ=round(pilot_bot, 2), depthFromRimMaxMm=round(z_top_max - pilot_bot, 2),
                        depthFromCounterboreFloorMm=round(seat - pilot_bot, 2)))
    print(key, res['packScrews'][key], flush=True)

# ---------------------------------------------------------------- (2) cross tunnels filled flush
X0, Z0 = V19['axis']['x'], V19['axis']['z']
FILL_R = 2.6                                      # 2.45 left 14 micro-gaps against the left bore wall (genus 20)
seamL, seamR = V19['seamAtCrossHole']['leftShellInnerFaceY'], V19['seamAtCrossHole']['rightShellInnerFaceY']


def local_hull(mesh, y0, y1):
    """Convex hull of the shell inside a box around the tunnel: on the convex outer skin it never rises above the skin."""
    box = P.box([X0 - 6, min(y0, y1), Z0 - 6], [X0 + 6, max(y0, y1), Z0 + 6])
    part = P.from_m(P.mesh_to_m(mesh) ^ box)
    hull = part.convex_hull
    # shrink 0.05 % about a point on the axis 15 mm in from the seam (about 0.008 mm at the skin): a hull face lying exactly
    # on a skin triangle leaves open edges after the union
    c = np.array([X0, np.sign(y0 + y1) * 15.0, Z0])
    return P.mesh_to_m(trimesh.Trimesh(c + (hull.vertices - c) * 0.9995, hull.faces, process=False))


fills = {}
for key, mesh, y0, y1 in (('shell_left', SL_mesh, seamL, 40.0), ('shell_right', SR_mesh, -40.0, seamR)):
    cyl = P.cyl_y(FILL_R, min(y0, y1), max(y0, y1), X0, Z0)
    fills[key] = cyl ^ local_hull(mesh, y0, y1)

# ---------------------------------------------------------------- (3) horn-screw counterbores (as ../shells-v19-source)
CB_IDS = ['S12-horn-026', 'S12-horn-027', 'S12-horn-028', 'S12-horn-029', 'S12-horn-030', 'S12-horn-031', 'S12-horn-032']
HCB_R, HCB_DEPTH = 2.2, 2.0
res['hornCounterbores'] = {}
for sid in CB_IDS:
    f = fast[sid]; c = np.array(f['center'], float); a = np.array(f['axis'], float)
    y0 = c[1] - a[1] * 3.0; y1 = c[1] + a[1] * HCB_DEPTH
    cuts[f['throughPart']].append(P.cyl_y(HCB_R, min(y0, y1), max(y0, y1), c[0], c[2]))
    res['hornCounterbores'][sid] = dict(throughPart=f['throughPart'], counterbore=f'dia {2 * HCB_R:g} x {HCB_DEPTH:g} from the seat',
                                        screw='M2 x 4 (was M2 x 6); thread engagement unchanged', engagementMm=f['engagementMm'])

new = {}
for key, base in (('shell_left', SL), ('shell_right', SR)):
    new[key] = (base + fills[key]) - P.union(cuts[key])

# fill check: added material only inside the tunnel, never above the printed outer skin
res['tunnelFill'] = {}
for key, base, mesh in (('shell_left', SL, SL_mesh), ('shell_right', SR, SR_mesh)):
    added = new[key] - base
    # flush cap: the cap is the shell's own local convex hull, shrunk 0.008 mm, so on the convex back it cannot stand above
    # the skin; png/tunnel-fill-sections.png shows the printed and V2.0 sections through the mouth.
    res['tunnelFill'][key] = dict(addedMm3=round(float(added.volume()), 2), fillRadiusMm=FILL_R,
                                  addedBoundsY=np.round(P.from_m(added).bounds[:, 1], 2).tolist() if added.volume() > 0 else None,
                                  capCheck='png/tunnel-fill-sections.png (black printed, red V2.0)',
                                  addedVsOtherParts=others(added, *P.from_m(added).bounds, skip=('shell_left', 'shell_right'), within=0.5),
                                  seamLeftOpen=f'fill stops at the shell inner face (y {seamL if key == "shell_left" else seamR})')
    print(key, 'fill', res['tunnelFill'][key], flush=True)
res['tunnelFill']['seamGapAfterMm'] = round(float(new['shell_left'].min_gap(new['shell_right'], 3.0)), 3)
res['tunnelFill']['seamGapBeforeMm'] = round(float(SL.min_gap(SR, 3.0)), 3)

# ---------------------------------------------------------------- screws, pilot and drivers against everything
res['packScrewChecks'] = {}
for key in ('shell_left', 'shell_right'):
    head, shank = screws[key]
    scr = head + shank
    b = P.from_m(scr).bounds
    sy = 20.0 if key == 'shell_left' else -20.0
    row = dict(headVsNewShellMm3=round(float((head ^ new[key]).volume()), 4),
               shankVsNewShellMm3=round(float((shank ^ new[key]).volume()), 4),
               threadInPackMm3=round(float((shank ^ PK).volume()), 3),
               otherParts=others(scr, b[0], b[1], skip=(key, 'rear_pack')),
               nearestCable=cable_exact(scr))
    pil = pilots[0 if key == 'shell_left' else 1]
    pb = P.from_m(pil).bounds
    row['pilotOtherParts'] = others(pil, pb[0], pb[1], skip=(key, 'rear_pack'))
    row['pilotNearestCable'] = cable_exact(pil)
    seat = res['packScrews'][key]['center'][2]
    for dia in (5.0, 8.0):
        shaft = P.cyl_z(dia / 2, seat + HEAD_H, seat + 60.0, SX, sy)
        sb = P.from_m(shaft).bounds
        row[f'driverDia{dia:g}x60'] = dict(newShellOverlapMm3=round(float((shaft ^ new[key]).volume()), 4),
                                          otherParts=others(shaft, sb[0], sb[1], skip=(key,), within=0.5))
    # clear height straight above the head in the final pose (any part)
    up = 999.0; who = None
    for k in sorted(present):
        if k not in man or k == key:
            continue
        hh = ray_hits(P.solid_mesh(k), [SX, sy, seat + HEAD_H], [0, 0, 1])
        if len(hh) and hh[0] < up:
            up, who = float(hh[0]), k
    row['clearAboveHeadFinalPoseMm'] = dict(mm=round(up, 1), firstPart=who)
    res['packScrewChecks'][key] = row
    print(key, 'checks', row, flush=True)

# ---------------------------------------------------------------- new shells against every other part (final pose)
res['shellPairs'] = {}
for key, base in (('shell_left', SL), ('shell_right', SR)):
    b = P.from_m(new[key]).bounds
    now = others(new[key], b[0], b[1], skip=(key,), within=0.0)
    was = others(base, b[0], b[1], skip=(key,), within=0.0)
    res['shellPairs'][key] = dict(overlapsNow={k: v['overlapMm3'] for k, v in now.items() if v['overlapMm3'] > 1e-4},
                                  overlapsPrinted={k: v['overlapMm3'] for k, v in was.items() if v['overlapMm3'] > 1e-4})

# ---------------------------------------------------------------- (4) jaw frame: fill the passive-arm pivot hole
JX, JZ = 26.1, 118.61
probe = []
for yy in np.arange(-46.0, -35.0, 0.05):
    inner = JF_mesh.contains([[JX, yy, JZ]])[0]
    ring = all(JF_mesh.contains([[JX + 1.4 * np.cos(a), yy, JZ + 1.4 * np.sin(a)]])[0] for a in np.linspace(0, 2 * np.pi, 8, endpoint=False))
    probe.append((round(float(yy), 2), bool(inner), bool(ring)))
hole_ys = [y for y, inner, ring in probe if not inner and ring]
hy0, hy1 = min(hole_ys), max(hole_ys)
tip_face = -20.0 - float(np.median([ray_hits(JF_mesh, [JX + 1.6 * np.cos(a), -20.0, JZ + 1.6 * np.sin(a)], [0, -1, 0])[0]
                                     for a in np.linspace(0, 2 * np.pi, 8, endpoint=False)]))
jbox = P.box([JX - 4, hy0 - 3, JZ - 4], [JX + 4, tip_face, JZ + 4])
jhull = P.mesh_to_m(P.from_m(JF ^ jbox).convex_hull)
jfill = P.cyl_y(1.15, hy0 - 0.5, tip_face, JX, JZ) ^ jhull
JF_new = JF + jfill
jadded = JF_new - JF
jb = P.from_m(jadded).bounds
# outside the ring of material around the hole the jaw must be unchanged: compare first hits along y on the r 1.4..3 ring
res['jawHole'] = dict(axis=[JX, 'y', JZ], holeSpanY=[hy0, hy1], holeLengthMm=round(hy1 - hy0 + 0.05, 2),
                      ringMaterialAllAlongHole=all(ring for y, inner, ring in probe if hy0 <= y <= hy1),
                      addedMm3=round(float(jadded.volume()), 3), addedBounds=np.round(jb, 2).tolist(),
                      addedOutsideOldBoundsMm=round(float(max(0.0, (JF_mesh.bounds[0] - jb[0]).max(), (jb[1] - JF_mesh.bounds[1]).max())), 3),
                      addedVsOtherParts=others(jadded, jb[0], jb[1], skip=('jaw_frame',), within=0.5),
                      hitsAfterAlongAxis=[round(float(h), 2) for h in ray_hits(P.from_m(JF_new), [JX, -60.0, JZ], [0, 1, 0])[:4]])
# end faces: the fill must stop at the arm's outer face and the boss tip, flush
for side, o, d in (('outerFace', [JX, -60.0, JZ], [0, 1, 0]), ('bossTip', [JX, -20.0, JZ], [0, -1, 0])):
    before = [ray_hits(JF_mesh, [o[0] + 1.6 * np.cos(a), o[1], o[2] + 1.6 * np.sin(a)], d) for a in np.linspace(0, 2 * np.pi, 8, endpoint=False)]
    after = ray_hits(P.from_m(JF_new), o, d)
    res['jawHole'][side] = dict(faceAroundHoleMm=[round(float(b[0]), 3) for b in before if len(b)], fillFaceMm=round(float(after[0]), 3) if len(after) else None)
print('jaw', res['jawHole'], flush=True)

# ---------------------------------------------------------------- outputs
out = {}
for name, m in (('shell_left_v20-world.stl', new['shell_left']), ('shell_right_v20-world.stl', new['shell_right']),
                ('jaw_frame_v20-world.stl', JF_new)):
    mesh = P.clean_mesh(m)
    parts = mesh.split(only_watertight=False)
    dropped = [round(float(abs(q.volume)), 4) for q in parts if abs(q.volume) < 0.01]
    if dropped:                                      # zero-volume slivers left by the flush cap at the tunnel rim
        mesh = trimesh.util.concatenate([q for q in parts if abs(q.volume) >= 0.01])
    mesh.export(HERE / name)
    out[name] = dict(sha256=hashlib.sha256((HERE / name).read_bytes()).hexdigest(), tris=int(len(mesh.faces)), watertight=bool(mesh.is_watertight),
                     bodies=int(len(mesh.split(only_watertight=False))), droppedSliversMm3=dropped, volumeMm3=round(float(m.volume()), 2),
                     genus=int(m.genus()))
res['outputs'] = out
res['volumes'] = dict(shell_left=dict(printed=round(float(SL.volume()), 2), v20=round(float(new['shell_left'].volume()), 2)),
                      shell_right=dict(printed=round(float(SR.volume()), 2), v20=round(float(new['shell_right'].volume()), 2)),
                      jaw_frame=dict(printed=round(float(JF.volume()), 2), v20=round(float(JF_new.volume()), 2)))
res['elapsed_s'] = round(time.time() - t0, 1)
P.jdump(res, HERE / 'v20-source.json')
print(json.dumps({k: res[k] for k in ('outputs', 'volumes', 'shellPairs', 'elapsed_s')}, indent=1, default=str))
