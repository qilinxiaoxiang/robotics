"""Write the V1.32 incremental release manifest of D-025 (ears and mouth speaker, print/ears-mouth-20261023/, Shawn 2026-10-23:
"按 A 耳朵位做，扬声器挪到嘴上方"): the head cap with two ears and no speaker collar and the mouth speaker box (White), and the
lower head shell with six floor ports (Yellow). One plate per colour. The White plate also carries everything still unprinted
(Shawn 2026-10-23: "除了白色打印盘 其他3个颜色我都已经打了"): the V1.30 White plate (U20 face panel, saddle body and lid) in its
V1.30 poses. The cap replaces the printed V1.17 A7Z cap (stock slot 4), the shell the printed V1.30 shell (slot 12, which can
instead be drilled with ears-mouth-20261023/drill-template/drill-template.pdf); the speaker box is an addition and the V1.9
speaker retainer is retired.

Poses (guide/print/orientation-study/PRINT-ORIENTATION-PRACTICE.md):
- head_cap in the V1.17 cap pose (release-V1.17 head_cap_a7z.sourceToPrint, roof on the bed) with its outer brim and support
  blocker: the new cap is the V1.17 cap with the collar removed, the roof filled back to the V1.8 roof inside the collar box and
  material changed only near the ears, so the crown strip and tip angle carry over.
- speaker_box upright, the box bottom (wall bottoms and base slab, world z 112.3) on the bed, no brim: the duct roof (17.5 mm span,
  1.1 mm over the bed) and the chamber top are bridges; a support blocker fills the chamber and duct inside so no support is
  printed where it could not be pulled out.
- head_bottom in the V1.8 pose (floor on the bed) with the V1.30 support blockers; the six ports go straight through the floor.
- face_panel, saddle_body, saddle_lid: the V1.30 rows unchanged (same files, same poses).
Wall check: a FAIL region of the cap and the shell is accepted only where the printed part, posed the same way, already fails at the
same place and the surface there is unchanged (old_allowances, as V1.30).

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np, trimesh
HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent; SIM = PRINT.parent.parent
sys.path.insert(0, str(SIM / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'))
import wall_check  # noqa: E402
V130 = PRINT / 'release-V1.30/manifest-V1.30.json'; V117 = PRINT / 'release-V1.17/manifest-V1.17.json'
EM = PRINT / 'ears-mouth-20261023'; WORLD = PRINT / 'world'
m130 = json.loads(V130.read_text()); m117 = json.loads(V117.read_text())
cap_row = next(r for r in m117['parts'] if r['key'] == 'head_cap_a7z'); hb_row = next(r for r in m130['parts'] if r['key'] == 'head_bottom')
cap_checks = json.loads((EM / 'head-cap/checks.json').read_text()); spk_checks = json.loads((EM / 'speaker-box/checks.json').read_text())
yel_checks = json.loads((EM / 'yellow-reprint/checks.json').read_text())


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p): return {'path': str(Path(p).resolve()), 'sha256': sha(p)}
def blocker(path, machines, reason): return dict(path=str(path), sha256=sha(path), machines=machines, reason=reason)


# Speaker-box support blocker: the chamber and duct inside (speaker-box/build_speaker_box.py), 0.2 mm in from the walls, and the
# speaker window through the mounting plate (OrcaSlicer put tree support under the 15 mm window top, which bridges), world frame.
P = spk_checks['params']; W = P['wall']; x_plate1 = P['xBack'] + P['speaker'][2] + P['tape'] + P['plate']
lo = np.array([x_plate1 - P['plate'] - 0.2, P['ductY'][0] + 0.2, P['floorTop'] + P['tape'] + 0.05]); hi = np.array([P['ductEnd'] - 0.2, P['ductY'][1] - 0.2, P['top'] - W - 0.2])
SPK_BLOCK = REL / 'blockers/speaker-box-duct-world.stl'
trimesh.creation.box(extents=hi - lo, transform=trimesh.transformations.translation_matrix((lo + hi) / 2)).export(SPK_BLOCK)

CAP_CHANGE = ('D-025 (Shawn 2026-10-23: "耳朵感觉应该放在更像耳朵的地方 扬声器可以考虑放在嘴巴上面"; "按 A 耳朵位做"): two INMP441 microphones '
              'for sound direction (two ears plus head turning). On each side wall at x 60.5, z 133 (mid height, just behind the face) a dia '
              f'{cap_checks["params"]["holeD"] if "holeD" in cap_checks.get("params", {}) else 1.6} sound hole along the wall normal and a horseshoe locator '
              '(ID 14.0, wall 1.2, open 120 deg at the top for the wires) for the round dia 13.4 board on a 1 mm foam ring; the unused A7Z board-rail '
              'fin and block beside each ear are cut back to the wall. The speaker leaves the roof for the mouth speaker box: the collar is removed '
              'and the roof inside the collar box is the V1.8 roof again (grille holes filled); the two amplifier posts stay. Everything else is the V1.17 cap.')
SPK_CHANGE = ('D-025 (Shawn 2026-10-23: "扬声器可以考虑放在嘴巴上面 这样声音张嘴出来"; "单独打印扬声器盒"): the CMS-30204-18SP speaker stands on '
              'the yellow floor behind the camera, face forward, taped (1 mm foam loop) to the back of a plate with a 15 x 24 window; a closed chamber '
              'in front turns the sound down into a flat open-bottom duct (inside 17.5 x 2.1 mm) along the floor under the camera to the six ports '
              f'over the lower jaw. The box stands on 1 mm foam tape that seals the duct and holds it. {spk_checks["volumeMm3"]} mm3, '
              f'{spk_checks["massG_PLA"]} g.')
HB_CHANGE = ('D-025: six dia 2.5 port holes through the floor over the lower jaw at x 64/68/72, y -7/+1 (0.3 mm above the jaw top with the '
             'beak closed), under the speaker-box duct, so the speaker sounds out when the beak opens. Nothing else changed from V1.30. The '
             'printed V1.30 shell can be drilled to the same holes instead (ears-mouth-20261023/drill-template/drill-template.pdf).')

ROWS = {
    'head_cap': dict(color='White', T=np.array(cap_row['sourceToPrint']), stock=['4'], minimum=93.0, name='V1.17 pose, roof on the bed',
                     olds=[(PRINT / 'a7z-head/head_cap_a7z-world.stl', np.array(cap_row['sourceToPrint']), 'V1.17 A7Z cap (printed 2026-10-15)'),
                           (WORLD / 'head_cap-v18.stl', np.array(cap_row['sourceToPrint']), 'V1.8 cap roof (printed 2026-10-12; same robot frame, posed as V1.17)')],
                     origin='V1.17 cap pose (release-V1.17 head_cap_a7z.sourceToPrint, roof on the bed) applied to the robot-frame V1.32 cap; the crown strip carries over.',
                     objectSettings=cap_row['objectSettings'], objectSettingsReason=cap_row['objectSettingsReason'],
                     supersedes='head_cap_a7z (V1.17, white, printed): the roof speaker collar and grille, no ears',
                     change=CAP_CHANGE, evidence=[EM / 'head-cap/checks.json', EM / 'head-cap/build_head_cap.py', EM / 'ears-mouth.png'],
                     blockers=cap_row.get('supportBlockers', []), allow='old'),
    'speaker_box': dict(color='White', T=np.eye(4), stock=[], decision='addition', minimum=150.0, name='upright, box bottom on the bed',
                        origin=(f'Robot frame dropped to the bed: the wall bottoms and the base slab (world z {P["floorTop"] + P["tape"]}) are the first layer '
                                f'({spk_checks["tapeFootAreaMm2"]} mm2); the duct roof and the chamber top print as bridges.'),
                        objectSettings={'brim_type': 'no_brim'},
                        objectSettingsReason='R1: 32.7 mm tall on a 214 mm2 footprint spread over 22.6 x 22.8 mm; a brim would leave a lip on the foam-tape faces.',
                        supersedes='nothing (new part); the V1.9 speaker retainer is retired',
                        change=SPK_CHANGE, evidence=[EM / 'speaker-box/checks.json', EM / 'speaker-box/build_speaker_box.py', EM / 'ears-mouth.png'],
                        blockers=[blocker(SPK_BLOCK, ['Bambu', 'Elegoo'], 'Chamber and duct inside of the speaker box (0.2 mm in from the walls) and the speaker window through the plate: no support where it could not be pulled out; the duct roof and the chamber top bridge. World coordinates.')],
                        allow=[]),
    'head_bottom': dict(color='Yellow', T=np.array(hb_row['sourceToPrint']), stock=['12'], minimum=200.0, name='V1.8 pose, floor on the bed',
                        olds=[(PRINT / 'neck-exit-20261023/head_bottom_exit.stl', np.array(hb_row['sourceToPrint']), 'V1.30 lower head shell (printed 2026-10-23)')],
                        origin='V1.8 lower-shell pose (release-V1.30 head_bottom.sourceToPrint, floor on the bed) applied to the robot-frame V1.32 shell.',
                        objectSettings=None, objectSettingsReason=None,
                        supersedes='head_bottom (V1.30, yellow, printed): no floor ports; it can be drilled instead of reprinted',
                        change=HB_CHANGE, evidence=[EM / 'yellow-reprint/checks.json', EM / 'yellow-reprint/build_yellow_ports.py', EM / 'drill-template/drill-template.pdf'],
                        blockers=hb_row['supportBlockers'], allow='old'),
}


def pose(stl, T):
    k = trimesh.load(stl, force='mesh', process=False); k.apply_transform(T); k.apply_translation([0, 0, -k.bounds[0, 2]]); return k


def old_allowances(key, k, row):
    """As release-V1.30/scripts/make_manifest.py, with one or more printed reference parts in the same pose (row['olds']): a FAIL region
    is accepted where a reference already has thin samples at the same place (a FAIL region overlapping the bbox within 0.5 mm, or
    raw thin samples within 1 mm of it) and the thin samples inside the region that are off every reference surface (> 0.001 mm) add up to
    less than MIN_REGION_MM2. The cap needs two references: outside the collar box it is the V1.17 cap, inside it the V1.8 roof."""
    refs = []
    for stl, T, label in row['olds']:
        om = pose(stl, T); mo = wall_check.measure(om)
        refs.append(dict(mesh=om, label=label, fails=[g for g in wall_check.check(om.copy(), (), key)['regions'] if g['status'] == 'FAIL'],
                         thin=mo['points'][mo['smoothed'] < wall_check.MIN_WALL_MM - wall_check.MEASURE_TOL_MM]))
    meas = wall_check.measure(k); thin = meas['smoothed'] < wall_check.MIN_WALL_MM - wall_check.MEASURE_TOL_MM; tp = meas['points'][thin]
    dist = np.min([np.concatenate([trimesh.proximity.closest_point(rf['mesh'], tp[i:i + 250])[1] for i in range(0, len(tp), 250)]) for rf in refs], axis=0)
    off = dist > 1e-3
    out, new = [], []
    for g in [g for g in wall_check.check(k.copy(), (), key)['regions'] if g['status'] == 'FAIL']:
        lo, hi = np.array(g['bbox'])
        hits = []
        for rf in refs:
            mf = [o for o in rf['fails'] if np.all(np.array(o['bbox'][0]) < hi + 0.5) and np.all(np.array(o['bbox'][1]) > lo - 0.5)]
            nraw = int(np.all((rf['thin'] >= lo - 1.0) & (rf['thin'] <= hi + 1.0), axis=1).sum())   # raw thin samples within 1 mm (one sample pitch)
            if mf or nraw:
                hits.append(f'{rf["label"]}: {len(mf)} FAIL regions there' + (f' ({min(o["minMm"] for o in mf)} mm sampled)' if mf else '') + f', {nraw} thin samples')
        inside = np.all((tp >= lo - 1e-6) & (tp <= hi + 1e-6), axis=1)
        moved = round(float((inside & off).sum() * meas['areaPerSampleMm2']), 2)
        if hits and moved < wall_check.MIN_REGION_MM2:
            out.append(dict(bbox=[(lo - 0.05).round(3).tolist(), (hi + 0.05).round(3).tolist()], minMm=round(g['minMm'] - 0.005, 3),
                            reason=(f'unchanged printed surface: {int(inside.sum())} thin samples, {moved} mm2 of them off every reference surface (>0.001 mm); '
                                    f'{"; ".join(hits)}; {g["minMm"]} mm now, {g["areaMm2"]} mm2')))
        else:
            new.append(dict(g, refHits=hits, offRefSurfaceMm2=moved))
    assert not new, (key, 'new thin walls', new)
    return out


parts = []; pl = {}
for key, row in ROWS.items():
    stl = WORLD / f'{key}.stl'
    k = pose(stl, row['T'])
    if row['allow'] == 'old':
        row['allow'] = old_allowances(key, k, row)
    pstl = REL / f'run-inputs/{key}-print.stl'; pstl.parent.mkdir(exist_ok=True); k.export(pstl)
    area = float(k.area_faces[np.max(np.abs(k.triangles[:, :, 2]), axis=1) <= .01].sum()); size = (k.bounds[1] - k.bounds[0]).round(2).tolist()
    assert area >= row['minimum'], (key, area)
    regs = [g for g in wall_check.check(k.copy(), row['allow'], key)['regions'] if g['status'] == 'FAIL']
    assert not regs, (key, regs)
    r = dict(key=key, color=row['color'], quantity=1, decision=row.get('decision', 'replacement'), replacesStockIds=row['stock'],
             path=str(stl), sha256=sha(stl), sourceFrame='robot frame (mm, x forward, y left, z up; guide world at HOME)', sourceToPrint=row['T'].tolist(),
             flatContact={'minimumAreaMm2': row['minimum']}, poseName=row['name'], poseOrigin=row['origin'],
             poseCheck=dict(printStl=ref(pstl), bedContactMm2=round(area, 2), printSizeMm=size, registrationMaxDeviationMm=0.0,
                            note='world STL in the row pose, dropped to the bed'),
             changeReason=row['change'], supersedes=row['supersedes'],
             incrementalEvidence=ref(row['evidence'][0]), evidenceAlso=[ref(e) for e in row['evidence'][1:]], thinWallAllowances=row['allow'])
    if row.get('blockers'):
        r['supportBlockers'] = row['blockers']
    if row['objectSettings']:
        r['objectSettings'] = row['objectSettings']; r['objectSettingsReason'] = row['objectSettingsReason']
    parts.append(r); pl.setdefault(row['color'], []).append((key, k.bounds.copy()))
    print(key, 'contact', round(area, 1), 'size', size, 'allowances', len(row['allow']))
# Everything else unprinted: the V1.30 White rows (face panel, saddle body, saddle lid), same files and poses.
for p in m130['parts']:
    if p['color'] == 'White':
        assert sha(p['path']) == p['sha256'], (p['key'], 'world file changed since V1.30')
        p = dict(p, changeReason=p['changeReason'] + ' Carried unprinted from V1.30 (same file, same pose).')
        k = pose(p['path'], np.array(p['sourceToPrint'])); parts.append(p); pl['White'].append((p['key'], k.bounds.copy()))
        print(p['key'], 'carried from V1.30')
# White plate in two rows inside the pipeline's 18-238 mm bed area (the cap brim is 4 mm): cap and saddle body at the back; face panel,
# saddle lid and speaker box at the front. Yellow: the shell centred.
GAP = 10.0
def row_place(items, yc):
    width = sum(b[1, 0] - b[0, 0] for _, b in items) + GAP * (len(items) - 1); x = 128.0 - width / 2; out = []
    assert width <= 210, width
    for key, b in items:
        out.append(dict(key=key, copy=1, translation=[round(x - b[0, 0], 4), round(yc - (b[0, 1] + b[1, 1]) / 2, 4), 0.0])); x += b[1, 0] - b[0, 0] + GAP
    return out
wb = dict(pl['White']); back = [(k, wb[k]) for k in ('head_cap', 'saddle_body')]; front = [(k, wb[k]) for k in ('face_panel', 'saddle_lid', 'speaker_box')]
hb = max(b[1, 1] - b[0, 1] for _, b in back); hf = max(b[1, 1] - b[0, 1] for _, b in front); top = 128.0 + (hb + GAP + hf) / 2
placements = dict(White=row_place(back, top - hb / 2) + row_place(front, top - hb - GAP - hf / 2),
                  Yellow=row_place(pl['Yellow'], 128.0))
m = dict(m130)
m.update(parts=parts, placements=placements, version='V1.32',
         processOverrides={k: v for k, v in m130['processOverrides'].items() if k.startswith('White_')},
         processOverrideReason=('V1.17 White overrides kept (3 support interface layers at 0.15 spacing, 0.2 top z, interface 40 mm/s, bridge 30 mm/s, support '
                                'ironing, 0.2 first layer): the cap prints roof-down on tree support as V1.17, the saddle body on tree support as V1.30, the face and '
                                'the speaker box flat without support. Yellow: the donor profile as is (as V1.30).'),
         retiredParts=[{'part': 'head_cap_a7z', 'printed': 'V1.17 (White)', 'reason': 'replaced by the V1.32 cap with two ears and no speaker collar; keep as a spare'},
                       {'part': 'head_bottom', 'printed': 'V1.30 (Yellow)', 'reason': 'replaced by the V1.32 shell with six floor ports, or drilled with the paper template and kept'},
                       {'part': 'speaker_retainer_v19', 'printed': 'V1.9 (Orange)', 'reason': 'the speaker moved to the mouth speaker box (D-025); its two M2 x 6 go back to stock'}],
         prototypeScope=('V1.32 delta package (D-025, ears and mouth speaker): one White plate with the head cap (two ears, no speaker collar), the mouth '
                         'speaker box, and the still unprinted V1.30 White parts (U20 face panel, A7Z roof saddle body and lid); one Yellow plate with the '
                         'lower head shell with six floor ports (or drill the printed V1.30 shell with the paper template and skip the Yellow plate). '
                         'The V1.30 White files are superseded by this White plate.'),
         knownFitBoundary=('INMP441 board size (dia 13.4, PCB 1.0, chip 4.72 x 3.76 x 1.0) is read from the seller photos, not a measured unit; the locator '
                           'ID 14.0 leaves 0.3 mm. The speaker-box duct is 2.1 mm high, its acoustics untested; the box seal relies on 1 mm foam tape on the '
                           'floor. The cap edits keep the V1.17 crown strip; printed sizes not measured.'))
m['deliveryContract'] = dict(m130['deliveryContract'], colors=['White', 'Yellow'], filesPerColor=2, fileCount=4,
                             baseline='printed releases through V1.31 (the V1.30 White plate was not printed and is carried here)',
                             supersedes=['the unprinted V1.30 White plate', 'the V1.17 A7Z head cap', 'the V1.30 lower head shell (or drill it)', 'the V1.9 speaker retainer'])
(REL / 'manifest-V1.32.json').write_text(json.dumps(m, indent=1, ensure_ascii=False)); print('ok', [p['key'] for p in parts], placements)
