"""Write the V1.30 incremental release manifest of D-023: the U20 face panel (White) and the U20 eye trim (Black)
(print/face-u20/build_face_u20.py), the jaw support with the fixed half of the exit clamp and the two loose clamp halves A and
B (Black), and the lower head shell (Yellow) with the dia 11 left-rear head exit (print/neck-exit-20261023/build_neck_exit.py,
Shawn 2026-10-23). One plate per colour. Four parts replace printed parts: the V1.17 A7Z face panel (stock slot 46), the V1.8
eye trim (66), the V1.6 jaw support (28) and the V1.8 lower head shell (12); the two loose clamp halves are additions. The head
cap is not reprinted and the four V1.9 wire clips are retired unfitted.

Poses (guide/print/orientation-study/PRINT-ORIENTATION-PRACTICE.md): the V1.8 poses, unchanged.
- face_panel front on the bed, bosses up (V1.17 face_panel_a7z.sourceToPrint): 14.4 mm tall with the 13.1 mm bosses, 3086 mm2
  bed contact (the dia 16.2 eye opening takes 38 mm2 off the V1.8/V1.17 contact), 3.3 mm2 of overhang over 45 deg (the
  flare edge), no_brim (R1: flat, tip angle 88 deg; set explicitly because the White donors default to auto_brim on Bambu).
- eye_trim as V1.8 (release-V1.8 eye_trim.sourceToPrint, the V1.6 registration pose): 9.4 mm tall, 394 mm2 contact, the
  45 deg flare is the only overhang (23.7 mm2); R1 default (no brim).
- jaw_support in the V1.6 release pose (the inverse of v16-registration transformReleaseToWorld: top face on the bed), as printed
  in V1.6; head_bottom in the V1.8 pose (release-V1.8 head_bottom.sourceToPrint, floor on the bed) with the V1.8 support blockers,
  the left-rear pilot blocker moved with its seat (neck-exit-20261023/support-blockers.json).
- exit_clamp_loose_a / _b upside down, their flat top on the bed (neck-exit-20261023 LOOSE_T): the tongues and barbs grow up
  from the bed, the barb catch faces are 0.4 mm ledges.
The builds' own print files (face-u20/*-print.stl, neck-exit-20261023/*_exit-print.stl) must match the posed world STLs to 0.01 mm.
Wall check: a FAIL region of the two exit parts is accepted only where the V1.6/V1.8 part, posed the same way, already fails at the
same place and the surface there is unchanged (within 0.001 mm of the old part; allowance bbox and minMm from the current region).

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np, trimesh
HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent; SIM = PRINT.parent.parent
sys.path.insert(0, str(SIM / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'))
import wall_check  # noqa: E402
V129 = PRINT / 'release-V1.29/manifest-V1.29.json'; V117 = PRINT / 'release-V1.17/manifest-V1.17.json'; V18 = PRINT / 'release-V1.8/manifest-V1.8.json'
FACE = PRINT / 'face-u20'; WORLD = PRINT / 'world'; EXIT = PRINT / 'neck-exit-20261023'
checks = json.loads((FACE / 'checks.json').read_text())
m117 = json.loads(V117.read_text()); m18 = json.loads(V18.read_text())
face_row = next(r for r in m117['parts'] if r['key'] == 'face_panel_a7z'); trim_row = next(r for r in m18['parts'] if r['key'] == 'eye_trim')
hb_row = next(r for r in m18['parts'] if r['key'] == 'head_bottom')
REG = next(r for r in json.loads((PRINT.parent / 'content/interference-audit/v16-registration.json').read_text()) if r['key'] == 'jaw_support')
JS_OLD = Path(REG['releaseFile']) if Path(REG['releaseFile']).is_absolute() else SIM / REG['releaseFile']
exit_checks = json.loads((EXIT / 'checks.json').read_text())


def rigid(T):
    """Nearest rigid transform (SVD); the V1.6 registration fit is rigid to 1e-7 and the release pipeline requires 1e-8."""
    U, _, Vt = np.linalg.svd(T[:3, :3]); T = T.copy(); T[:3, :3] = U @ Vt; return T

NEW_BLOCK = json.loads((EXIT / 'support-blockers.json').read_text())['files']
def blocker(path, machines, reason): return dict(path=str(path), sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(), machines=machines, reason=reason)
HB_BLOCKERS = [b for b in hb_row['supportBlockers'] if 'support-pilot-1' not in b['path']] + [
    blocker(EXIT / 'support-pilot-new-world.stl', ['Bambu'], 'V1.8 support-pilot-1 hole-core exclusion moved with the left-rear seat to (11.6, 30.2), world coordinates.'),
    blocker(EXIT / 'support-pilot-new-branch-clearance-world.stl', ['Elegoo'], 'V1.8 support-pilot-1 branch-clearance exclusion moved with the left-rear seat to (11.6, 30.2), world coordinates.')]
EXIT_CHANGE = ('D-023 (Shawn 2026-10-23: "能不能把脖子那个洞搞大一点呢 别转杜邦线了"; "按这个做：重打颌支架和头底板放大左后出口"): the head wires and the U20CAM '
               'cable leave the head at its left rear. The 6.4 mm gap there (between ID15, the jaw support corner walls and the screw H-jaw_support-01) '
               f'becomes a vertical dia {2 * exit_checks["params"]["PASSAGE"]["r"]} exit at (10, 18.5) through the jaw support and the floor of the lower shell '
               f'(free bore dia {exit_checks["passageDiaMm"]["new"]} with the fixed clamp half in it); '
               'the left-rear screw seat moves to (11.6, 30.2) on the pad strip behind ID15 (4.0 mm of M2.6 thread, 5.8 mm of pilot past the tip); the wall '
               'ends beside the exit are squared off so no new wall is under 1.2 mm.')
ROWS = {
    'face_panel': dict(color='White', T=np.array(face_row['sourceToPrint']), stock=['46'], minimum=3000.0, name='V1.8 pose, front on the bed, bosses up',
                       printStl=FACE / 'face_panel_u20-print.stl',
                       origin=('V1.8/V1.17 face pose (release-V1.17 face_panel_a7z.sourceToPrint) applied to the robot-frame U20 face: front on the bed, '
                               f'the four 13.1 mm bosses up; {checks["printPoses"]["face_panel"]["heightMm"]} mm tall, 3086.4 mm2 bed contact (the dia 16.2 eye opening against dia 14.4), 3.3 mm2 of '
                               'overhang steeper than 45 deg at the flare edge (face-u20/checks.json printPoses). The result equals '
                               'face-u20/face_panel_u20-print.stl.'),
                       objectSettings={'brim_type': 'no_brim'},
                       objectSettingsReason='R1: flat on 3086 mm2, 9 mm tall, tip angle 88 deg; set explicitly because the White donors default to auto_brim on Bambu.',
                       supersedes='face_panel_a7z (V1.17, white, printed): the A7Z face with 4.0 mm bosses for the Radxa Camera 13M 214 and a dia 14.4 eye opening',
                       change=('D-023 (2026-10-22, revised 2026-10-23): the Innomaker U20CAM-720P USB camera takes the four face bosses. Its dimensions come from '
                               'the ROBOTIS OMX-F CAD (face-u20/robotis-cad/): lens front 22.0 mm in front of the board, ring dia 14.0. The bosses grow from 4.0 to '
                               '13.1 mm behind the face back (dia 4.8, pilot dia 1.7, wall 1.55) so the board sits at x 67.0 and the lens front at x 89.0, 0.4 mm '
                               'behind the trim front (Shawn 2026-10-23: "板子后移 6.6 mm"); the eye opening grows to dia 16.2, with the same 45 deg flare outside. Front face otherwise '
                               'unchanged (checks.json frontUnchangedOutsideBore). Four M2 x 6 into the bosses (C-camera-01..04), 4.4 mm of thread. '
                               'The two side key pockets for the eye-trim tabs at (AY -/+ 7.7, AZ - 4.5) are filled through the 1.3 mm front skin: the bore '
                               'cut into them, leaving 0.35 mm; the trim loses its two side tabs and the top key pair stays.'),
                       allow=[dict(bbox=[[-1.5, 6.2, -0.01], [2.0, 8.2, 1.31]], minMm=1.0,
                                   reason='the top key pits of the V1.8 face/trim pair, between the dia 16.2 bore and the upper trim-screw hole: the V1.17 face '
                                          'measures the same 1.05 mm there (2.5 mm2; release-V1.17 face printed 2026-10-15); the larger bore widens the patch '
                                          'to 8.1 mm2 at 1.05 mm without thinning it; a skin patch behind the trim ring, no load')]),
    'eye_trim': dict(color='Black', T=np.array(trim_row['sourceToPrint']), stock=['66'], minimum=374.38, name='V1.8 pose',
                     printStl=FACE / 'eye_trim_u20-print.stl',
                     origin=('V1.8 eye-trim pose (release-V1.8 eye_trim.sourceToPrint, the inverse of the V1.6 registration transformReleaseToWorld) applied to '
                             'the robot-frame U20 trim, dropped to the bed: 9.4 mm tall, 394.1 mm2 contact, the 45 deg flare the only overhang (23.7 mm2, as '
                             'V1.8). The result equals face-u20/eye_trim_u20-print.stl.'),
                     objectSettings=None, objectSettingsReason=None,
                     supersedes='eye_trim (V1.8, black, printed): bore dia 14.4, the Radxa and Pi camera lenses passed it',
                     change=('D-023 (2026-10-22): the bore behind the flare grows from dia 14.4 to 16.2 so the U20CAM M12 lens ring (dia 14.0, ROBOTIS CAD) passes '
                             'with 1.1 mm radial clearance; the two 1.7 mm trim-screw pilots and the outer shape are unchanged (face-u20/checks.json trimSectionsRadii, '
                             f'optics: {checks["optics"]["perPart"]["eye_trim_u20"]["minNormalClearanceMm"]} mm normal clearance of the 120 deg cone, no clipping). The two 1.0 mm side tabs on the back of the ring are cut '
                             'off (their face pockets are filled, see the face row); the top key pair stays.'),
                     allow=[]),
    'jaw_support': dict(color='Black', T=rigid(np.linalg.inv(np.array(REG['transformReleaseToWorld']))), stock=['28'], minimum=808.0, name='V1.6 release pose, top face on the bed',
                        printStl=EXIT / 'jaw_support_exit-print.stl', oldStl=JS_OLD, oldT=np.eye(4), old='V1.6 jaw support (release file, printed)',
                        origin=('The V1.6 release pose (inverse of v16-registration transformReleaseToWorld, top face on the bed) applied to the robot-frame V1.30 '
                                f'jaw support: {exit_checks["printPoses"]["jaw_support"]["bedContactMm2"]} mm2 of bed contact (V1.6 file: 834). The result equals '
                                'neck-exit-20261023/jaw_support_exit-print.stl.'),
                        objectSettings=None, objectSettingsReason=None,
                        supersedes='jaw_support_original (V1.6, black, printed): the left-rear screw pad at (6.6, 19) closed the corner beside ID15',
                        change=EXIT_CHANGE + (' Jaw support: the exit cut through its left-rear corner walls and plate, the pad moved with a dia 2.8 clearance hole, '
                                              'and the fixed half of the two-piece wire clamp in the exit (Shawn 2026-10-23: "卡扣按概念图"): an arc from 60 to 240 deg '
                                              'round the rear-left of the exit from the plate bottom to z 124.3, bore dia 7.8 with two 0.5 mm ribs, and at each end a '
                                              'lip over a pocket for a tongue of the loose half, with a recess for its barb. The pull from the neck goes into the jaw support.'),
                        evidence=[EXIT / 'checks.json', EXIT / 'build_neck_exit.py', EXIT / 'clip_concept.png', EXIT / 'seat-stack.json'],
                        blockers=[], allow='old'),
    'head_bottom': dict(color='Yellow', T=np.array(hb_row['sourceToPrint']), stock=['12'], minimum=200.0, name='V1.8 pose, floor on the bed',
                        printStl=EXIT / 'head_bottom_exit-print.stl', oldStl=WORLD / 'head_bottom_v18.stl', oldT=np.array(hb_row['sourceToPrint']), old='V1.8 lower head shell (printed 2026-10-12)',
                        origin=('V1.8 lower-shell pose (release-V1.8 head_bottom.sourceToPrint, floor on the bed) applied to the robot-frame V1.30 shell: '
                                f'{exit_checks["printPoses"]["head_bottom"]["bedContactMm2"]} mm2 of bed contact (V1.8: {exit_checks["printPoses"]["head_bottom"]["v18BedContactMm2"]}); '
                                'the new boss stands on the bed. The result equals neck-exit-20261023/head_bottom_exit-print.stl.'),
                        objectSettings=None, objectSettingsReason=None,
                        supersedes='head_bottom (V1.8, yellow, printed): the left-rear boss at (6.6, 19) and its ring wall closed the corner beside ID15',
                        change=EXIT_CHANGE + (' Lower shell: the exit through the floor, the old boss and the ring-wall and rib ends beside it removed, a dia 6 boss '
                                              'with a dia 2.2 pilot at the new seat standing on the bed. Everything else is the V1.8 shell.'),
                        evidence=[EXIT / 'checks.json', EXIT / 'build_neck_exit.py', EXIT / 'support-blockers.json', EXIT / 'seat-stack.json'],
                        blockers=HB_BLOCKERS, allow='old'),
}
CL = exit_checks['clamp']['params']; CX, CY = exit_checks['params']['PASSAGE']['c']
LOOSE_T = np.array([[1.0, 0, 0, -CX], [0, -1.0, 0, CY], [0, 0, -1.0, CL['zTop']], [0, 0, 0, 1.0]])   # build_neck_exit.py LOOSE_T
for v, extra in (('A', 'bore dia 7.8 with the fixed half'), ('B', 'a 0.4 mm thicker wall, bore dia 7.0, for a thinner bundle')):
    lc = exit_checks['clamp']['loose'][v]
    ROWS[f'exit_clamp_loose_{v.lower()}'] = dict(
        color='Black', T=LOOSE_T, stock=[], decision='addition', minimum=20.0, name='upside down, flat top on the bed',   # the whole flat top is 22.6 mm2; tip angle 27 deg (R1: no brim)
        world=EXIT / f'exit_clamp_loose_{v}.stl', printStl=EXIT / f'exit_clamp_loose_{v}-print.stl',
        origin=(f'Upside down (build_neck_exit.py LOOSE_T): the flat top (z {CL["zTop"]}) on the bed, tongues and barbs growing up from it; '
                f'{round(CL["zTop"] - CL["zLooseBottom"], 2)} mm tall. The result equals neck-exit-20261023/exit_clamp_loose_{v}-print.stl.'),
        objectSettings=None, objectSettingsReason=None, supersedes='nothing (new part)',
        change=(f'D-023 (Shawn 2026-10-23: "能不能打印一个? 比如一个两片式的卡扣", then "卡扣按概念图"): loose half {v} of the head-exit wire clamp, {extra}. '
                'It closes the front-right side of the exit round the camera cable and the nine head wires: it slides down from above, its two tongues '
                'drop into the pockets behind the lips of the fixed half at 60 and 240 deg, and a barb at the bottom of each tongue clicks into its lip '
                f'(0.2 mm interference; the C closes about 0.35 mm at each tongue). {lc["volumeMm3"]} mm3. Print both and fit the one that grips the bundle.'),
        evidence=[EXIT / 'checks.json', EXIT / 'build_neck_exit.py', EXIT / 'clip_concept.png'], blockers=[], allow=[])


def pose(stl, T):
    k = trimesh.load(stl, force='mesh', process=False); k.apply_transform(T); k.apply_translation([0, 0, -k.bounds[0, 2]]); return k


def old_allowances(key, k, row):
    """Allowances for the FAIL regions the old part already has at the same place (print frame, same pose) with an unchanged surface:
    the region overlaps an old FAIL region and the thin samples inside it that are more than 0.001 mm off the old part's surface add
    up to less than the wall check's minimum region (MIN_REGION_MM2). The exit cut re-meshed the whole part, so the sampled minimum of
    an unchanged region can differ from the old part's; it is recorded, not compared."""
    om = pose(row['oldStl'], row['oldT'])
    old = [g for g in wall_check.check(om.copy(), (), key)['regions'] if g['status'] == 'FAIL']
    meas = wall_check.measure(k); thin = meas['smoothed'] < wall_check.MIN_WALL_MM - wall_check.MEASURE_TOL_MM; tp = meas['points'][thin]
    off = np.concatenate([trimesh.proximity.closest_point(om, tp[i:i + 250])[1] for i in range(0, len(tp), 250)]) > 1e-3
    out, new = [], []
    for g in [g for g in wall_check.check(k.copy(), (), key)['regions'] if g['status'] == 'FAIL']:
        lo, hi = np.array(g['bbox'])
        m = [o for o in old if np.all(np.array(o['bbox'][0]) < hi + 0.5) and np.all(np.array(o['bbox'][1]) > lo - 0.5)]
        inside = np.all((tp >= lo - 1e-6) & (tp <= hi + 1e-6), axis=1)
        moved = round(float((inside & off).sum() * meas['areaPerSampleMm2']), 2)
        if m and moved < wall_check.MIN_REGION_MM2:
            out.append(dict(bbox=[(lo - 0.05).round(3).tolist(), (hi + 0.05).round(3).tolist()], minMm=round(g['minMm'] - 0.005, 3),
                            reason=(f'unchanged {row["old"]}: {int(inside.sum())} thin samples, {moved} mm2 of them off the old surface (>0.001 mm); the old '
                                    f'part fails at the same place ({min(o["minMm"] for o in m)} mm sampled there, {g["minMm"]} mm now, {g["areaMm2"]} mm2)')))
        else:
            new.append(dict(g, oldOverlap=len(m), offOldSurfaceMm2=moved))
    assert not new, (key, 'new thin walls', new)
    return out


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p): return {'path': str(Path(p).resolve()), 'sha256': sha(p)}


m = json.loads(V129.read_text()); white = m117['processOverrides']
parts = []; pl = {}
for key, row in ROWS.items():
    stl = row.get('world', WORLD / f'{key}.stl')
    k = pose(stl, row['T'])
    if row['allow'] == 'old':
        row['allow'] = old_allowances(key, k, row)
    ref_print = trimesh.load(row['printStl'], force='mesh', process=False)
    dev = float(np.abs(np.sort(k.vertices, axis=0) - np.sort(ref_print.vertices, axis=0)).max())
    assert dev < 0.01, (key, dev)
    area = float(k.area_faces[np.max(np.abs(k.triangles[:, :, 2]), axis=1) <= .01].sum()); size = (k.bounds[1] - k.bounds[0]).round(2).tolist()
    assert area >= row['minimum'], (key, area)
    regs = [g for g in wall_check.check(k.copy(), row['allow'], key)['regions'] if g['status'] == 'FAIL']
    assert not regs, (key, regs)
    r = dict(key=key, color=row['color'], quantity=1, decision=row.get('decision', 'replacement'), replacesStockIds=row['stock'],
             path=str(stl), sha256=sha(stl), sourceFrame='robot frame (mm, x forward, y left, z up; guide world at HOME)', sourceToPrint=row['T'].tolist(),
             flatContact={'minimumAreaMm2': row['minimum']}, poseName=row['name'], poseOrigin=row['origin'],
             poseCheck=dict(printStl=ref(row['printStl']), bedContactMm2=round(area, 2), printSizeMm=size, registrationMaxDeviationMm=dev,
                            note='world STL in the row pose, dropped to the bed; equals the face-u20 print file'),
             changeReason=row['change'], supersedes=row['supersedes'],
             incrementalEvidence=ref(row.get('evidence', [FACE / 'checks.json'])[0]),
             evidenceAlso=[ref(e) for e in row.get('evidence', [None, FACE / 'build_face_u20.py', FACE / 'render-back.png', FACE / 'render-section.png'])[1:]],
             thinWallAllowances=row['allow'])
    if row.get('blockers'):
        r['supportBlockers'] = row['blockers']
    if row['objectSettings']:
        r['objectSettings'] = row['objectSettings']; r['objectSettingsReason'] = row['objectSettingsReason']
    parts.append(r)
    pl.setdefault(row['color'], []).append((key, k.bounds.copy()))
    print(key, 'contact', round(area, 1), 'size', size, 'pose deviation', round(dev, 6), 'allowances', len(row['allow']))
# Still unprinted on 2026-10-23 (the V1.29 saddle, Shawn: "不用了吗"): one package for everything unprinted, so V1.30 carries the
# V1.29 saddle body and lid in their V1.29 poses. The V1.28 right link was already printed (Shawn, 10/23 evening), so it is not carried. The body is
# the D-023 build (USB-C plug notch y 2.7..26.2 for the CableCreation right-angle plug), never sliced before.
SAD = PRINT / 'a7z-saddle'
v129 = {p['key']: p for p in json.loads(V129.read_text())['parts']}
SAD_BUILD = json.loads((SAD / 'build/build.json').read_text())
for key in ('saddle_body', 'saddle_lid'):
    row = dict(v129[key]); stl = WORLD / f'{key}.stl'; T = np.array(row['sourceToPrint'])
    k = pose(stl, T); pstl = SAD / f'build/{key}-print.stl'; k.export(pstl)
    area = float(k.area_faces[np.max(np.abs(k.triangles[:, :, 2]), axis=1) <= .01].sum()); size = (k.bounds[1] - k.bounds[0]).round(2).tolist()
    assert area >= row['flatContact']['minimumAreaMm2'], (key, area)
    # thin regions re-derived on the rebuilt mesh, accepted only where V1.29 accepted one (bbox within 1 mm): the rear wall-foot wedges
    old = row['thinWallAllowances']; allow = []
    for g in [g for g in wall_check.check(k.copy(), (), key)['regions'] if g['status'] == 'FAIL']:
        lo, hi = np.array(g['bbox'])
        hit = [a for a in old if (lo > np.array(a['bbox'][0]) - 1.0).all() and (hi < np.array(a['bbox'][1]) + 1.0).all()]
        assert hit, (key, 'new thin region', g['areaMm2'], g['minMm'], g['bbox'])
        allow.append(dict(bbox=[[c - .05 for c in g['bbox'][0]], [c + .05 for c in g['bbox'][1]]], minMm=round(max(g['minMm'] - .005, 0.01), 3), reason=hit[0]['reason']))
    row['thinWallAllowances'] = allow
    changed = sha(stl) != row['sha256']
    row.update(path=str(stl), sha256=sha(stl), poseCheck=dict(row['poseCheck'], printStl=ref(pstl), bedContactMm2=round(area, 2), printSizeMm=size),
               incrementalEvidence=ref(SAD / 'build/build.json'),
               changeReason=row['changeReason'] + (' D-023 (2026-10-23): the front-wall plug notch widens to y 2.7..26.2, z up to 9.6 above the floor, '
                                                   'for the CableCreation right-angle USB-C plug (body 21.8 mm along +y), and the +y pair of front slots '
                                                   'inside it goes; first sliced in V1.30.' if changed else ' Carried from the unprinted V1.29 (same file).'))
    parts.append(row); pl.setdefault('White', []).append((key, k.bounds.copy()))
    print(key, 'carried', 'changed' if changed else 'same', 'contact', round(area, 1), 'size', size)
GAP = 10.0   # parts of one colour side by side along x, the row centred on the 256 mm plate
for color, items in pl.items():
    width = sum(b[1, 0] - b[0, 0] for _, b in items) + GAP * (len(items) - 1); x = 128.0 - width / 2; out = []
    for key, b in items:
        out.append(dict(key=key, copy=1, translation=[round(x - b[0, 0], 4), round(128.0 - (b[0, 1] + b[1, 1]) / 2, 4), 0.0])); x += b[1, 0] - b[0, 0] + GAP
    pl[color] = out
m.update(parts=parts, placements=pl, processOverrides={k: v for k, v in white.items() if k.startswith('White_')}, retiredParts=[
    {'part': 'face_panel_a7z', 'printed': 'V1.17 (White)', 'reason': 'replaced by the V1.30 U20 face panel (taller bosses, dia 16.2 eye opening); keep as a spare'},
    {'part': 'eye_trim', 'printed': 'V1.8 (Black)', 'reason': 'replaced by the V1.30 U20 eye trim (bore dia 16.2); keep as a spare'},
    {'part': 'jaw_support_original', 'printed': 'V1.6 (Black)', 'reason': 'replaced by the V1.30 jaw support with the dia 11 left-rear exit; keep as a spare'},
    {'part': 'head_bottom', 'printed': 'V1.8 (Yellow)', 'reason': 'replaced by the V1.30 lower head shell with the dia 11 left-rear exit; keep as a spare'},
    {'part': 'clip_torso, clip_bracket, clip_head (V1.9) and clip_cap_a7z (V1.17)', 'printed': 'V1.9 and V1.17 (Orange)', 'reason': 'never fitted (D-023): the head wires run free down the left side of the neck; the three screws go back to M2 x 6 / M2.6 x 6'}],
         version='V1.30',
         processOverrideReason=('V1.17 White overrides kept for the face (3 support interface layers at 0.15 spacing, 0.2 top z, interface 40 mm/s, bridge 30 mm/s, '
                                'support ironing, 0.2 first layer); the face prints flat and needs no support; the saddle body stands on tree support over its whole underside (as V1.29). Black and Yellow: donor profiles as is (as V1.8 and V1.28).'),
         prototypeScope=('V1.30 delta package (D-023): one White plate with the U20 face panel, one Black plate with the U20 eye trim, the jaw support '
                         'and the two loose halves (A, B) of the exit clamp, one Yellow plate with the lower head shell. The face and trim take the Innomaker '
                         'U20CAM-720P USB camera 13.1 mm behind the face; the jaw support and the shell open the left-rear head exit to dia 11 so the camera '
                         'cable leaves the head whole, and the jaw support carries the fixed half of the printed two-piece clamp that holds the wires there. '
                         'Four parts replace printed parts, the two loose halves are new. The head cap is not reprinted; the four V1.9 wire clips are retired unfitted. '
                         'It also carries everything still unprinted (Shawn 2026-10-23): the V1.29 A7Z roof saddle body and lid (White; the body with the D-023 '
                         'USB-C plug notch). The V1.29 folder is superseded.'),
         knownFitBoundary=('Camera dimensions come from the ROBOTIS OMX-F CAD of the same camera, not from a measured unit: lens front 22.0 mm in front of '
                           'the board, so it sits 0.4 mm behind the trim front. Boss pilots dia 1.7 for M2 x 6 (4.4 mm of thread); the trim bore dia 16.2 is '
                           '1.1 mm clear of the lens ring. The exit parts: the moved M2.6 seat and the clamp are new, not yet printed; the clamp barbs snap with '
                           '0.2 mm of interference, untested on a print; the camera cable diameter (4 mm) and the bundle size are assumed, hence the two loose '
                           'halves. Printed sizes not measured.'))
m.pop('deferred', None)
m['deliveryContract'].update(colors=['White', 'Black', 'Yellow'], filesPerColor=2, fileCount=6, baseline='printed releases through V1.28 (V1.29 was not printed and is carried here)', status='INCREMENTAL_REPRINT',
                             supersedes=['the unprinted V1.29 package', 'the V1.17 A7Z face panel', 'the V1.8 eye trim', 'the V1.6 jaw support', 'the V1.8 lower head shell', 'the four V1.9/V1.17 wire clips (never fitted)'])
(REL / 'manifest-V1.30.json').write_text(json.dumps(m, indent=1, ensure_ascii=False)); print('ok', [p['key'] for p in parts], pl)
