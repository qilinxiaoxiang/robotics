"""Next-version SOURCE of the two torso side shells (not in the V1.9 print set; the printed V1.8 shells stay on the robot).

Changes to the printed shells (audit solid cache shell_left / shell_right = the 10/1 community shells, world = guide frame, mm):
 (1) left shell: the rear cross tunnel at x -38, z 34.96 bored to dia 4.4 from its floor (y 2.05) to the outer mouth, so an M2 pan
     head (dia 4.0) reaches the floor and one M2 x 6 joins the shells through the right shell's dia 1.6 pilot;
 (3) horn-screw counterbores dia 4.4 x 2.0 deep on S12-horn-026..032 (3 on the right shell into the ID12 idler, 4 on the left
     shell into the ID12 horn). S12-horn-025 (right shell, x 20, z 32.5) keeps its flat seat: the V1.9 neck-route wire clip sits
     under that head.
It also measures what the guide needs for the printed V1.8 left shell: the tunnel profile (bore diameter, wall, floor, mouth),
the right-shell pilot, the cross-screw stack for M2 x 6 and M2 x 8, the no-drill M2 x 12 socket-head option, cable distances and
driver reach. Writes shell_left_v19_source-world.stl, shell_right_v19_source-world.stl and shells-v19-source.json here.
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
X0, Z0 = -38.0, 34.96                          # cross-hole axis (along y), from the unscrewed-hole audit; re-fitted below
BORE_R, FLOOR_Y = 2.2, 2.05
CB_R, CB_DEPTH = 2.2, 2.0
CB_IDS = ['S12-horn-026', 'S12-horn-027', 'S12-horn-028', 'S12-horn-029', 'S12-horn-030', 'S12-horn-031', 'S12-horn-032']
KEEP_FLAT = ['S12-horn-025']
fast = {f['id']: f for f in json.load(open(G / 'content' / 'fasteners.json'))['screws']}
data = json.load(open(G / 'data' / 'guide-data.json'))
man = ia_lib.manifest()
SL_mesh, SR_mesh = P.solid_mesh('shell_left'), P.solid_mesh('shell_right')
SL, SR = P.mesh_to_m(SL_mesh), P.mesh_to_m(SR_mesh)
res = {'inputs': {k: dict(path=str(ia_lib.solid_path(k)), sha256=hashlib.sha256(ia_lib.solid_path(k).read_bytes()).hexdigest())
                  for k in ('shell_left', 'shell_right')}}


def ray_hits(mesh, o, d):
    loc, _, _ = mesh.ray.intersects_location(np.array([o], float), np.array([d], float), multiple_hits=True)
    if not len(loc):
        return np.array([])
    return np.sort(np.linalg.norm(loc - np.array(o), axis=1))


# ---------------------------------------------------------------- axis fit in the clearance / pilot sections
def fit_centre(mesh, y, r_guess):
    pts = []
    for a in np.linspace(0, 2 * np.pi, 24, endpoint=False):
        d = np.array([np.cos(a), 0.0, np.sin(a)])
        h = ray_hits(mesh, [X0, y, Z0], d)
        if len(h):
            pts.append(np.array([X0, y, Z0]) + d * h[0])
    pts = np.array(pts)
    A = np.c_[2 * pts[:, 0], 2 * pts[:, 2], np.ones(len(pts))]
    b = pts[:, 0] ** 2 + pts[:, 2] ** 2
    cx, cz, c = np.linalg.lstsq(A, b, rcond=None)[0]
    return float(cx), float(cz), float(np.sqrt(c + cx ** 2 + cz ** 2))


fits = {'leftClearance_y1.0': fit_centre(SL_mesh, 1.0, 1.1), 'rightPilot_y-3.0': fit_centre(SR_mesh, -3.0, 0.8),
        'leftBore_y5.0': fit_centre(SL_mesh, 5.0, 1.8), 'rightBore_y-10.0': fit_centre(SR_mesh, -10.0, 1.6)}
res['axisFit'] = {k: dict(x=round(v[0], 3), z=round(v[1], 3), radius=round(v[2], 3)) for k, v in fits.items()}
X0 = round(float(np.mean([v[0] for v in fits.values()])), 3); Z0 = round(float(np.mean([v[1] for v in fits.values()])), 3)
res['axis'] = dict(x=X0, z=Z0, direction=[0, 1, 0])


# ---------------------------------------------------------------- profile along the axis (radial rays every 0.1 mm)
def profile(mesh, ys, n_ang=24):
    rows = []
    for y in ys:
        inner, outer = [], []
        for a in np.linspace(0, 2 * np.pi, n_ang, endpoint=False):
            d = np.array([np.cos(a), 0.0, np.sin(a)])
            h = ray_hits(mesh, [X0, y, Z0], d)
            inner.append(h[0] if len(h) else np.inf); outer.append(h[1] if len(h) > 1 else np.inf)
        rows.append((float(y), float(np.min(inner)), float(np.max(inner)), float(np.min(outer))))
    return rows


ysL = np.round(np.arange(-1.0, 31.01, 0.1), 2); ysR = np.round(np.arange(-31.0, 0.01, 0.1), 2)
profL = profile(SL_mesh, ysL); profR = profile(SR_mesh, ysR)
# floor: first y (going +y from the clearance hole) where the bore radius exceeds 1.5; mouth: last y with material all round
inL = np.array([r[1] for r in profL]); inLmax = np.array([r[2] for r in profL])
mouth_first = float(ysL[inL < BORE_R + 0.3].max())          # outermost section where material still lies inside the dia 4.4 circle
mouth_y = float(ysL[inLmax < BORE_R + 0.3].max())           # outermost section with a complete ring inside the dia 4.4 circle
clear = [r for r in profL if r[1] < 1.3]
floor_meas = float(max(r[0] for r in clear if r[0] < 5.0)) + 0.1   # first 0.1 mm section past the dia 2.2 clearance hole
floor_y = FLOOR_Y                                            # bore start = head seat (design value; floor_meas checks it)
left_start = float(ysL[np.isfinite(inL) & (inL < 1.3)].min())


def summarise(prof, y0, y1):
    sel = [r for r in prof if y0 <= r[0] <= y1 and np.isfinite(r[1])]
    return [dict(y=round(r[0], 2), boreDiaMin=round(2 * r[1], 3), boreDiaMax=round(2 * r[2], 3), outerRadiusMin=round(r[3], 3)) for r in sel]


res['leftTunnel'] = dict(clearanceHoleFromY=round(left_start, 2), floorMeasuredY=round(floor_meas, 2), floorUsedY=floor_y,
                         mouthCompleteRingY=round(mouth_y, 2), mouthFirstContactY=round(mouth_first, 2),
                         depthMouthToFloorMm=dict(fromCompleteRing=round(mouth_y - floor_y, 2), fromFirstContact=round(mouth_first - floor_y, 2)),
                         profileEvery1mm=summarise(profL, -1.0, 31.0)[::10])
# wall left after boring dia D from the floor to the mouth = min outer radius - D/2 over y in [floor, mouth]
walls = {}
for D in (4.2, 4.4, 4.5):
    sel = [r for r in profL if floor_y <= r[0] <= mouth_y - 1.0 and np.isfinite(r[3])]
    w = [(r[3] - D / 2, r[0]) for r in sel]
    walls[f'dia{D:g}'] = dict(minWallMm=round(min(w)[0], 3), atY=round(min(w)[1], 2))
res['leftTunnel']['wallAfterBore'] = walls
# existing bore: smallest diameter vs y between floor and mouth (what a head must pass)
bore = [(r[0], 2 * r[1]) for r in profL if floor_y <= r[0] <= mouth_y]
res['leftTunnel']['existingBoreDia'] = dict(atFloor=round(bore[0][1], 3), atMouth=round(bore[-1][1], 3),
                                            minAlong=round(min(b[1] for b in bore), 3))
# right shell: pilot (radius < 1.0) span and its own outer tunnel
inR = np.array([r[1] for r in profR])
pil = [r[0] for r in profR if r[1] < 1.0]
res['rightPilot'] = dict(entryY=round(max(pil), 2), endY=round(min(pil), 2), lengthMm=round(max(pil) - min(pil), 2),
                         diaMin=round(2 * min(r[1] for r in profR if r[1] < 1.0), 3),
                         beyondPilot=summarise(profR, min(pil) - 3.0, min(pil) - 0.1)[::5],
                         note='y decreases into the right shell; beyond endY the right shell has its own open tapered bore to its outer face')
res['rightTunnel'] = dict(profileEvery1mm=summarise(profR, -31.0, 0.0)[::10])
seam = dict(leftShellInnerFaceY=round(left_start, 2), rightShellInnerFaceY=round(max(pil), 2), gapMm=round(left_start - max(pil), 2))
res['seamAtCrossHole'] = seam


# per-angle wall after boring, against the printed wall at the same angle (0 deg = +x forward, 90 = +z up). Drilling only removes
# material where the printed bore radius is below the drill radius; the wall after drilling is outer radius - max(printed, drill).
ANG = np.linspace(0, 2 * np.pi, 36, endpoint=False)
prof = []          # (y, angle deg, printed bore radius, outer radius)
rim = []
for a in ANG:
    d = np.array([np.cos(a), 0.0, np.sin(a)])
    last = None
    for y in np.arange(floor_y, mouth_first + 0.05, 0.1):
        h = ray_hits(SL_mesh, [X0, y, Z0], d)
        if len(h) >= 2 and h[0] < BORE_R + 0.3:
            last = y
            prof.append((float(y), float(np.degrees(a)), float(h[0]), float(h[1])))
    rim.append((round(float(np.degrees(a))), round(float(last), 2) if last is not None else None))
wall_rows = {}
for D in (4.2, 4.4, 4.5):
    rD = D / 2
    rows = [(o - max(b, rD), o - b, max(0.0, rD - b), y, ang) for (y, ang, b, o) in prof]
    cut = [r for r in rows if r[2] > 0.01]                 # drilling removes material here
    m = min(cut)
    thin_by_drill = sorted({round(r[3], 1) for r in cut if r[0] < 0.9})
    thin_printed = sorted({round(r[3], 1) for r in rows if r[1] < 0.9})
    wall_rows[f'dia{D:g}'] = dict(
        minWallWhereDrillCuts=dict(mm=round(m[0], 3), printedWallThereMm=round(m[1], 3), removedMm=round(m[2], 3), y=round(m[3], 2), angleDeg=round(m[4])),
        drillCutsUpToY=round(max(r[3] for r in cut), 2),
        drillLeavesBelow0_9mm=dict(fromY=thin_by_drill[0], toY=thin_by_drill[-1], count=sum(1 for r in cut if r[0] < 0.9)) if thin_by_drill else None,
        printedWallAlreadyBelow0_9mm=dict(fromY=thin_printed[0], toY=thin_printed[-1]) if thin_printed else None,
        drillThinsSoundWallBelow0_9mm=[dict(y=round(r[3], 2), angleDeg=round(r[4]), wallAfterMm=round(r[0], 3), printedWallMm=round(r[1], 3))
                                       for r in cut if r[0] < 0.9 and r[1] >= 0.9],
        maxRemovedMm=dict(yUpTo25=round(max([r[2] for r in cut if r[3] <= 25.0] or [0.0]), 3),
                          y25toMouth=round(max([r[2] for r in cut if r[3] > 25.0] or [0.0]), 3)))
res['leftTunnel']['wallPerAngle'] = wall_rows
res['leftTunnel']['mouthRimYPerAngle'] = rim

# ---------------------------------------------------------------- cross screw stacks (head on the floor, shank along -y)
def screw_m(seat_y, L, head_d=4.0, head_h=1.5):
    head = P.cyl_y(head_d / 2, seat_y, seat_y + head_h, X0, Z0)
    shank = P.cyl_y(1.0, seat_y - L, seat_y, X0, Z0)
    return head, shank


entry, pend = res['rightPilot']['entryY'], res['rightPilot']['endY']
present = set()
for s in data['steps']:
    present |= set(s.get('show', [])) | set(s.get('add', []))
present -= set(P.RETIRED)


def final_pose(parts_m, lo, hi, skip=()):
    out = {}
    for k in sorted(present):
        if k not in man or k in skip:
            continue
        b = np.array(man[k]['bounds'])
        if np.any(b[0] > hi + 3) or np.any(b[1] < lo - 3):
            continue
        S = P.solid_m(k)
        v = float((parts_m ^ S).volume()); g = float(parts_m.min_gap(S, 3.0))
        if v > 1e-4 or g < 3.0:
            out[k] = dict(overlapMm3=round(v, 4), gapMm=round(g, 3))
    return out


SLb = SL - P.cyl_y(BORE_R, floor_y, mouth_first + 3.0, X0, Z0)
cab_samples = []
for c in data['cables']:
    x, _ = spline_samples(np.array(c['path'], float)); cab_samples.append((c['id'], float(c.get('radius') or 0.9), x))


def cable_near(seg0, seg1, r_body):
    """Smallest surface gap from every cable tube to a cylinder of radius r_body on the segment seg0-seg1 (along y)."""
    best = (99.0, None)
    for cid, r, x in cab_samples:
        y = np.clip(x[:, 1], min(seg0, seg1), max(seg0, seg1))
        d = np.sqrt((x[:, 0] - X0) ** 2 + (x[:, 2] - Z0) ** 2 + (x[:, 1] - y) ** 2) - r - r_body
        k = int(np.argmin(d))
        if d[k] < best[0]:
            best = (round(float(d[k]), 2), cid, np.round(x[k], 1).tolist())
    return best


def cable_exact(solid):
    """Smallest surface gap from every cable tube (drawn spline) to the given solid (exact closest point on its mesh)."""
    mesh = P.from_m(solid); best = (99.0, None, None)
    for cid, r, x in cab_samples:
        near = np.linalg.norm(x - mesh.centroid, axis=1) < 25.0
        if not near.any():
            continue
        _, d, _ = trimesh.proximity.closest_point(mesh, x[near])
        k = int(np.argmin(d))
        if d[k] - r < best[0]:
            best = (round(float(d[k] - r), 2), cid, np.round(x[near][k], 1).tolist())
    return best


res['crossScrew'] = {}
for L in (6.0, 8.0):
    head, shank = screw_m(floor_y, L)
    tip = floor_y - L
    in_pilot = max(0.0, entry - max(tip, pend))
    lead = 0.3
    eng = max(0.0, in_pilot - (lead if tip > pend else 0.0))
    scr = head + shank
    lo = np.array([X0 - 2.5, tip - 1, Z0 - 2.5]); hi = np.array([X0 + 2.5, floor_y + 2, Z0 + 2.5])
    row = dict(spec=f'M2 x {L:g} TAP (pan head dia 4.0 x 1.5 assumed)', headSeatY=floor_y, tipY=round(tip, 2),
               shankInRightPilotMm=round(in_pilot, 2), engagementMm=round(eng, 2),
               tipBeyondPilotEndMm=round(pend - tip, 2) if tip < pend else None, tipShortOfPilotEndMm=round(tip - pend, 2) if tip >= pend else None,
               leftClearanceHole=dict(fromY=round(left_start, 2), toY=floor_y),
               headVsBoredLeftMm3=round(float((head ^ SLb).volume()), 4), shankVsBoredLeftMm3=round(float((shank ^ SLb).volume()), 4),
               headVsPrintedLeftMm3=round(float((head ^ SL).volume()), 4),
               threadVolumeInRightMm3=round(float((shank ^ SR).volume()), 3),
               otherParts=final_pose(scr, lo, hi, skip=('shell_left', 'shell_right')),
               nearestCable=cable_near(tip, floor_y + 1.5, 2.0), nearestCableExact=cable_exact(scr))
    res['crossScrew'][f'M2x{L:g}'] = row
    print('cross screw', L, row, flush=True)
# driver corridor from the head top to 60 mm outside the mouth (shaft dia 4 and 3)
res['crossDriver'] = {}
for dia in (4.0, 3.0):
    shaft = P.cyl_y(dia / 2, floor_y + 1.5, mouth_y + 60.0, X0, Z0)
    lo = np.array([X0 - 3, floor_y, Z0 - 3]); hi = np.array([X0 + 3, mouth_y + 60, Z0 + 3])
    res['crossDriver'][f'dia{dia:g}'] = dict(boredLeftOverlapMm3=round(float((shaft ^ SLb).volume()), 4),
                                             boredLeftGapMm=round(float(shaft.min_gap(SLb, 2.0)), 3),
                                             printedLeftOverlapMm3=round(float((shaft ^ SL).volume()), 3),
                                             otherParts=final_pose(shaft, lo, hi, skip=('shell_left',)),
                                             reachFromMouthToHeadTopMm=round(mouth_y - (floor_y + 1.5), 2),
                                             nearestCable=cable_near(floor_y + 1.5, mouth_y + 60.0, dia / 2))

# ---------------------------------------------------------------- no-drill option: M2 x 12 socket head (dia 3.8 x 2.0) in the taper
nd = {}
for head_d in (3.8, 3.7, 3.9):
    # the head stops at the first section (coming down from the mouth) whose smallest bore diameter is below head_d
    stop = None
    for y, dmin in sorted(bore, key=lambda t: -t[0]):
        if dmin < head_d:
            stop = y; break
    nd[f'headDia{head_d:g}'] = dict(headStopsAtY=round(stop, 2) if stop is not None else None)
    for L in (12.0, 16.0):
        tip = stop - L
        in_pilot = max(0.0, entry - max(tip, pend))
        nd[f'headDia{head_d:g}'][f'M2x{L:g}'] = dict(tipY=round(tip, 2), shankInRightPilotMm=round(in_pilot, 2),
                                                     engagementMm=round(max(0.0, in_pilot - (0.3 if tip > pend else 0.0)), 2))
taper = np.polyfit([b[0] for b in bore], [b[1] for b in bore], 1)
nd['boreTaperMmPerMm'] = round(float(taper[0]), 4)
nd['headPositionShiftPer0.1mmBoreErrorMm'] = round(0.1 / float(taper[0]), 2)
nd['wedgeHalfAngleDeg'] = round(float(np.degrees(np.arctan(taper[0] / 2))), 2)
nd['note'] = ('head dia 3.8 is the ISO 4762 M2 nominal; 3.7 and 3.9 bracket real heads and print error. The head seats on the tapered '
              'wall (wedge), not on a shoulder.')
res['noDrillSocketHead'] = nd

# ---------------------------------------------------------------- (3) counterbores
res['counterbores'] = {}
cuts_L, cuts_R = [], []
for sid in CB_IDS + KEEP_FLAT:
    f = fast[sid]; c = np.array(f['center'], float); a = np.array(f['axis'], float)
    mesh = SL_mesh if f['throughPart'] == 'shell_left' else SR_mesh
    # shell thickness along the axis at the head edge radius 2.1 (where the counterbore floor will be) and at the hole wall
    th = []
    for ang in np.linspace(0, 2 * np.pi, 12, endpoint=False):
        off = np.array([np.cos(ang), 0, np.sin(ang)]) * 2.1
        h = ray_hits(mesh, c - a * 3.0 + off, a)
        if len(h) >= 2:
            th.append((h[0] - 3.0, h[1] - 3.0))      # entry/exit measured from the nominal seat point
    entry_off = float(np.median([t[0] for t in th])); exit_off = float(np.median([t[1] for t in th]))
    row = dict(throughPart=f['throughPart'], seat=c.tolist(), axis=a.tolist(), surfaceOffsetFromSeatMm=round(entry_off, 3),
               shellThicknessAtR2_1Mm=round(exit_off - entry_off, 3), intoPart=f['intoPart'], engagementNowMm=f['engagementMm'])
    if sid in CB_IDS:
        y0 = c[1] - a[1] * 3.0; y1 = c[1] + a[1] * CB_DEPTH
        cut = P.cyl_y(CB_R, min(y0, y1), max(y0, y1), c[0], c[2])
        (cuts_L if f['throughPart'] == 'shell_left' else cuts_R).append(cut)
        row.update(counterbore=f'dia {2 * CB_R:g} x {CB_DEPTH:g} deep from the seat', leftUnderHeadMm=round(exit_off - entry_off - CB_DEPTH, 3),
                   screwIfAdopted='M2 x 4 (same thread engagement as M2 x 6 today: the head drops 2.0 mm)')
    else:
        row['counterbore'] = 'none (flat seat kept: V1.9 neck-route wire clip under the head)'
    res['counterbores'][sid] = row
SLn = SLb - P.union(cuts_L); SRn = SR - P.union(cuts_R)
res['volumes'] = dict(left_removedByTunnelMm3=round(float((SL - SLb).volume()), 2),
                      left_removedByCounterboresMm3=round(float((SLb - SLn).volume()), 2),
                      right_removedByCounterboresMm3=round(float((SR - SRn).volume()), 2),
                      leftV18Mm3=round(float(SL.volume()), 2), leftSourceMm3=round(float(SLn.volume()), 2),
                      rightV18Mm3=round(float(SR.volume()), 2), rightSourceMm3=round(float(SRn.volume()), 2))
# counterbores against neighbours (the cut only removes material; check the head in its new seat against the other parts)
res['counterboreHeads'] = {}
for sid in CB_IDS:
    f = fast[sid]; c = np.array(f['center'], float); a = np.array(f['axis'], float)
    seat = c + a * CB_DEPTH
    y0, y1 = sorted([seat[1], seat[1] - a[1] * 1.5])
    head = P.cyl_y(2.0, y0, y1, c[0], c[2])
    shell = SLn if f['throughPart'] == 'shell_left' else SRn
    res['counterboreHeads'][sid] = dict(newSeat=np.round(seat, 3).tolist(), headVsSourceShellMm3=round(float((head ^ shell).volume()), 4),
                                        headTopBelowOuterSurfaceMm=round(CB_DEPTH - 1.5, 2))
out = {}
for name, m in (('shell_left_v19_source-world.stl', SLn), ('shell_right_v19_source-world.stl', SRn)):
    mesh = P.clean_mesh(m)
    mesh.export(HERE / name)
    out[name] = dict(sha256=hashlib.sha256((HERE / name).read_bytes()).hexdigest(), tris=int(len(mesh.faces)), watertight=bool(mesh.is_watertight),
                     bodies=int(len(mesh.split(only_watertight=False))), volumeMm3=round(float(m.volume()), 2), genus=int(m.genus()))
res['outputs'] = out
res['elapsed_s'] = round(time.time() - t0, 1)
P.jdump(res, HERE / 'shells-v19-source.json')
print(json.dumps({k: v for k, v in res.items() if k not in ('leftTunnel', 'rightTunnel')}, indent=1, default=str))
print(json.dumps(res['leftTunnel'], default=str))
