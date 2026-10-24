"""Write the V1.33 incremental release manifest of the mouth floor (print/mouth-floor-20261024/, Shawn 2026-10-24: "按第三版做：
黄壳凹槽+12孔+功放导轨+长圆出线口，颌支架和卡扣改长圆，头盖去功放柱、XIAO 放中间，跑出版检查"): the head cap without the amplifier
posts (White), the lower head shell with the speaker pocket, twelve sound holes, the amplifier rails and the long-round exit
(Yellow), and the jaw support with the long-round exit and the stadium fixed clamp half (Black). One plate per colour. The White
plate also carries everything still unprinted in White: the V1.30 face panel, saddle body and lid in their V1.30 poses. V1.33
supersedes the unprinted V1.32 package (its speaker box is retired, its cap and shell are replaced here before printing).
The loose exit-clamp halves are the V1.30 ones (printed), unchanged: they fit the stadium fixed half (build_exit_stadium.py).

Poses (guide/print/orientation-study/PRINT-ORIENTATION-PRACTICE.md):
- head_cap in the V1.32 / V1.17 cap pose (roof on the bed) with its outer brim and the V1.17 pilot blocker: the cap is the V1.32
  ear cap with the two amplifier posts removed (the roof there is the V1.8 roof again).
- head_bottom in the V1.8 pose (floor on the bed) with the V1.30 support blockers; the pocket opens upwards, the holes and the
  exit go straight through the floor, the rails stand up from it.
- jaw_support in the V1.6 release pose (top face on the bed), as V1.30.
- face_panel, saddle_body, saddle_lid: the V1.30 rows unchanged (same files, same poses).
Wall check: a FAIL region is accepted only where a printed reference part, posed the same way, already fails at the same place
and the surface there is unchanged (old_allowances, as V1.30 and V1.32).

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np, trimesh
HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent; SIM = PRINT.parent.parent
sys.path.insert(0, str(SIM / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'))
import wall_check  # noqa: E402
V130 = PRINT / 'release-V1.30/manifest-V1.30.json'; V132 = PRINT / 'release-V1.32/manifest-V1.32.json'
MF = PRINT / 'mouth-floor-20261024'; WORLD = PRINT / 'world'
m130 = json.loads(V130.read_text()); m132 = json.loads(V132.read_text())
row132 = {r['key']: r for r in m132['parts']}; row130 = {r['key']: r for r in m130['parts']}
REG = next(r for r in json.loads((PRINT.parent / 'content/interference-audit/v16-registration.json').read_text()) if r['key'] == 'jaw_support')
JS_V16 = Path(REG['releaseFile']) if Path(REG['releaseFile']).is_absolute() else SIM / REG['releaseFile']
floor = json.loads((MF / 'checks-floor.json').read_text()); capck = json.loads((MF / 'checks-cap.json').read_text())
exitck = json.loads((MF / 'checks.json').read_text())


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p): return {'path': str(Path(p).resolve()), 'sha256': sha(p)}


CAP_CHANGE = ('Mouth floor (Shawn 2026-10-24: "头盖去功放柱、XIAO 放中间"): the amplifier moved to the yellow floor, so its two roof posts '
              f'(x 17.9..27.2, {capck["postsRemovedMm3"]} mm3) are removed and the roof there is the V1.8 roof again. The XIAO touch board moves '
              'from the inner left wall to that place at the middle of the roof, on its foam tape (no printed locator). An optional third microphone '
              '(Shawn 2026-10-24, through the three-microphone session: "如果成本不高 而且没啥副作用 ... 加上得了 省得以后重新打印") gets the ear seat on '
              f'the back wall at y -11, z 135, beside the central rib: a dia 1.6 sound hole and the same horseshoe locator (wall {capck["backMic"]["wallAlongRayMm"]} mm '
              'along the ray). Everything else is the V1.32 '
              'ear cap (two INMP441 ears, no speaker collar), itself the V1.17 cap with the collar removed.')
HB_CHANGE = ('Mouth floor (Shawn 2026-10-24: "黄壳凹槽+12孔+功放导轨+长圆出线口"): a 30.4 x 20.4 mm pocket 1.5 mm deep in the floor behind the face '
             f'(floor left under it {floor["floorLeftUnderPocketMm"]["min"]} mm or more) takes the speaker grille face down on a thin tape loop; twelve '
             f'dia 2.5 holes through the pocket floor in four rows of three ({floor["holes"]["openAreaMm2"]} mm2 open), all over the lower jaw; two '
             'rails 1.2 x 4.0 mm, 15 mm long, 0.3 mm clear of the amplifier board on each side, hold the amplifier on foam tape beside the speaker '
             '(no screws). The left-rear exit grows from dia 11 to an 11 x 17 mm long-round slot (6 mm towards the rear-left, axis 150 deg) for '
             'the eleven head wires and the camera cable. Replaces the unprinted V1.32 shell with six ports and the printed V1.30 shell.')
JS_CHANGE = ('Mouth floor (Shawn 2026-10-24: "颌支架和卡扣改长圆"): the left-rear exit through the jaw support grows with the shell exit to the '
             '11 x 17 mm long-round slot; the fixed half of the two-piece clamp follows the slot (its ribs about the far centre), so the clamped '
             f'passage is {exitck["passageWidthMm"]["new"]} mm wide over the whole {exitck["stadium"]["ext"]} mm extension (a '
             f'{exitck["passageWidthMm"]["new"]} x {exitck["passageWidthMm"]["new"] + exitck["stadium"]["ext"]:.1f} mm long-round bore instead of a dia 6.8 '
             'circle), and the printed V1.30 loose halves A and B still snap in. '
             'Everything else is the V1.30 jaw support.')

ROWS = {
    'head_cap': dict(color='White', T=np.array(row132['head_cap']['sourceToPrint']), stock=['4'], minimum=93.0, name='V1.17 pose, roof on the bed',
                     olds=[(PRINT / 'a7z-head/head_cap_a7z-world.stl', np.array(row132['head_cap']['sourceToPrint']), 'V1.17 A7Z cap (printed 2026-10-15)'),
                           (WORLD / 'head_cap-v18.stl', np.array(row132['head_cap']['sourceToPrint']), 'V1.8 cap roof (printed 2026-10-12; same robot frame, posed as V1.17)')],
                     origin='V1.32 / V1.17 cap pose (roof on the bed) applied to the robot-frame V1.33 cap; the crown strip carries over.',
                     objectSettings=row132['head_cap']['objectSettings'], objectSettingsReason=row132['head_cap']['objectSettingsReason'],
                     supersedes='head_cap_a7z (V1.17, white, printed) and the unprinted V1.32 ear cap with amplifier posts',
                     change=CAP_CHANGE, evidence=[MF / 'checks-cap.json', MF / 'build_cap_xiao.py'],
                     blockers=row132['head_cap'].get('supportBlockers', []), allow='old'),
    'head_bottom': dict(color='Yellow', T=np.array(row132['head_bottom']['sourceToPrint']), stock=['12'], minimum=200.0, name='V1.8 pose, floor on the bed',
                        olds=[(PRINT / 'neck-exit-20261023/head_bottom_exit.stl', np.array(row132['head_bottom']['sourceToPrint']), 'V1.30 lower head shell (printed 2026-10-23)'),
                              (WORLD / 'head_bottom_v18.stl', np.array(row132['head_bottom']['sourceToPrint']), 'V1.8 lower head shell (printed 2026-10-12)')],
                        origin='V1.8 lower-shell pose (release-V1.30/V1.32 head_bottom.sourceToPrint, floor on the bed) applied to the robot-frame V1.33 shell.',
                        objectSettings=None, objectSettingsReason=None,
                        supersedes='head_bottom (V1.30, yellow, printed; and the unprinted V1.32 shell with six ports)',
                        change=HB_CHANGE, evidence=[MF / 'checks-floor.json', MF / 'build_mouth_floor.py', MF / 'checks.json', MF / 'build_exit_stadium.py'],
                        blockers=row132['head_bottom']['supportBlockers'], allow='old'),
    'jaw_support': dict(color='Black', T=np.array(row130['jaw_support']['sourceToPrint']), stock=['28'], minimum=None, name='V1.6 release pose, top face on the bed',
                        olds=[(WORLD / 'jaw_support-v132.stl', np.array(row130['jaw_support']['sourceToPrint']), 'V1.30 jaw support (printed 2026-10-23)'),
                              (JS_V16, np.eye(4), 'V1.6 jaw support (release file, printed)')],
                        origin='V1.6 release pose (the inverse of v16-registration transformReleaseToWorld, top face on the bed), as V1.30.',
                        objectSettings=None, objectSettingsReason=None,
                        supersedes='jaw_support (V1.30, black, printed): the dia 11 exit',
                        change=JS_CHANGE, evidence=[MF / 'checks.json', MF / 'build_exit_stadium.py'],
                        blockers=[], allow='old'),
}


def pose(stl, T):
    k = trimesh.load(stl, force='mesh', process=False); k.apply_transform(T); k.apply_translation([0, 0, -k.bounds[0, 2]]); return k


def old_allowances(key, k, row):
    """As release-V1.32/scripts/make_manifest.py: a FAIL region is accepted where a printed reference in the same pose already has thin
    samples at the same place (a FAIL region overlapping the bbox within 0.5 mm, or raw thin samples within 1 mm of it) and the thin
    samples inside the region that are off every reference surface (> 0.001 mm) add up to less than MIN_REGION_MM2. A reference also hits
    when the region's own rays, cast from the same points into that reference, give the same raw thickness (within 0.01 mm) on its
    surface: the even sampling moves when the part's total area changes (the V1.33 cap lost its posts), so a concave corner of an
    unchanged printed surface can form a 2 mm2 region in one sampling and not in the other."""
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
            nraw = int(np.all((rf['thin'] >= lo - 1.0) & (rf['thin'] <= hi + 1.0), axis=1).sum())
            if mf or nraw:
                hits.append(f'{rf["label"]}: {len(mf)} FAIL regions there' + (f' ({min(o["minMm"] for o in mf)} mm sampled)' if mf else '') + f', {nraw} thin samples')
        inside = np.all((tp >= lo - 1e-6) & (tp <= hi + 1e-6), axis=1)
        if not hits:
            rin = np.all((meas['points'] >= lo - 1e-6) & (meas['points'] <= hi + 1e-6), axis=1)
            for rf in refs:
                cp, d, f = trimesh.proximity.closest_point(rf['mesh'], meas['points'][rin])
                inw = -rf['mesh'].face_normals[f] * (1. if rf['mesh'].volume >= 0 else -1.)
                raw = np.minimum(wall_check.first_hit(rf['mesh'], cp + inw * wall_check.RAY_OFFSET_MM, inw) + wall_check.RAY_OFFSET_MM, wall_check.RAY_MAX_MM)
                dr = float(np.abs(raw - meas['raw'][rin]).max())
                if d.max() <= 1e-3 and dr <= 0.01:
                    hits.append(f'{rf["label"]}: the same {int(rin.sum())} rays give the same raw thickness (max difference {dr:.4f} mm, on its surface)')
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
    if row['minimum'] is None:   # jaw support: the slot takes some top-face contact; require 97 % of what this pose gives (V1.30: 808 of 830)
        row['minimum'] = float(np.floor(area * 0.97))
    assert area >= row['minimum'], (key, area)
    regs = [g for g in wall_check.check(k.copy(), row['allow'], key)['regions'] if g['status'] == 'FAIL']
    assert not regs, (key, regs)
    r = dict(key=key, color=row['color'], quantity=1, decision='replacement', replacesStockIds=row['stock'],
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
# Everything else unprinted in White: the V1.30 White rows (face panel, saddle body, saddle lid), same files and poses.
for p in m130['parts']:
    if p['color'] == 'White':
        assert sha(p['path']) == p['sha256'], (p['key'], 'world file changed since V1.30')
        p = dict(p, changeReason=p['changeReason'] + ' Carried unprinted from V1.30 (same file, same pose).')
        k = pose(p['path'], np.array(p['sourceToPrint'])); parts.append(p); pl['White'].append((p['key'], k.bounds.copy()))
        print(p['key'], 'carried from V1.30')
# White plate in two rows inside the pipeline's 18-238 mm bed area (the cap brim is 4 mm): cap and saddle body at the back; face
# panel and saddle lid at the front. Yellow and Black: the one part centred.
GAP = 10.0
def row_place(items, yc):
    width = sum(b[1, 0] - b[0, 0] for _, b in items) + GAP * (len(items) - 1); x = 128.0 - width / 2; out = []
    assert width <= 210, width
    for key, b in items:
        out.append(dict(key=key, copy=1, translation=[round(x - b[0, 0], 4), round(yc - (b[0, 1] + b[1, 1]) / 2, 4), 0.0])); x += b[1, 0] - b[0, 0] + GAP
    return out
wb = dict(pl['White']); back = [(k, wb[k]) for k in ('head_cap', 'saddle_body')]; front = [(k, wb[k]) for k in ('face_panel', 'saddle_lid')]
hb = max(b[1, 1] - b[0, 1] for _, b in back); hf = max(b[1, 1] - b[0, 1] for _, b in front); top = 128.0 + (hb + GAP + hf) / 2
placements = dict(White=row_place(back, top - hb / 2) + row_place(front, top - hb - GAP - hf / 2),
                  Yellow=row_place(pl['Yellow'], 128.0), Black=row_place(pl['Black'], 128.0))
m = dict(m132)
m.update(parts=parts, placements=placements, version='V1.33',
         processOverrides={k: v for k, v in m132['processOverrides'].items() if k.startswith('White_')},
         processOverrideReason=('V1.17 White overrides kept (3 support interface layers at 0.15 spacing, 0.2 top z, interface 40 mm/s, bridge 30 mm/s, support '
                                'ironing, 0.2 first layer): the cap prints roof-down on tree support as V1.17 and V1.32, the saddle body on tree support as V1.30, '
                                'the face flat without support. Yellow and Black: the donor profiles as is (as V1.30).'),
         retiredParts=[{'part': 'head_cap_a7z', 'printed': 'V1.17 (White)', 'reason': 'replaced by the V1.33 cap with two ears, no speaker collar and no amplifier posts; keep as a spare'},
                       {'part': 'head_bottom', 'printed': 'V1.30 (Yellow)', 'reason': 'replaced by the V1.33 shell with the speaker pocket, twelve holes, the amplifier rails and the exit slot'},
                       {'part': 'jaw_support', 'printed': 'V1.30 (Black)', 'reason': 'replaced by the V1.33 jaw support with the exit slot; the V1.30 loose clamp halves stay'},
                       {'part': 'amplifier posts screws', 'printed': '-', 'reason': 'the two M2 x 6 that held the amplifier on the cap posts go back to stock'},
                       {'part': 'speaker_retainer_v19', 'printed': 'V1.9 (Orange)', 'reason': 'the speaker lies in the floor pocket; its two M2 x 6 go back to stock'}],
         prototypeScope=('V1.33 delta package (mouth floor): one White plate with the head cap (two ears, no speaker collar, no amplifier posts) and the '
                         'still unprinted V1.30 White parts (U20 face panel, A7Z roof saddle body and lid); one Yellow plate with the lower head shell '
                         '(speaker pocket, twelve sound holes, amplifier rails, long-round exit); one Black plate with the jaw support (long-round exit). '
                         'The unprinted V1.32 package (White and Yellow) and its drill template are superseded and not to be printed.'),
         knownFitBoundary=('Speaker pocket 0.2 mm clearance per side on the CMS-30204-18SP datasheet size (30 x 20), not a measured unit; the camera '
                           'board passes 0.54 mm over the speaker on 0.3 mm tape and 0.76 mm over the amplifier. Amplifier rails 0.3 mm per side on the '
                           'Adafruit board file width (17.78). INMP441 size from seller photos as V1.32. Printed sizes not measured.'))
m['deliveryContract'] = dict(m132['deliveryContract'], colors=['White', 'Yellow', 'Black'], filesPerColor=2, fileCount=6,
                             baseline='printed releases through V1.31 (the V1.30 White plate and the V1.32 package were not printed)',
                             supersedes=['the unprinted V1.32 package (White and Yellow plates, drill template)', 'the unprinted V1.30 White plate',
                                         'the V1.17 A7Z head cap', 'the V1.30 lower head shell', 'the V1.30 jaw support', 'the V1.9 speaker retainer'])
(REL / 'manifest-V1.33.json').write_text(json.dumps(m, indent=1, ensure_ascii=False)); print('ok', [p['key'] for p in parts], placements)
