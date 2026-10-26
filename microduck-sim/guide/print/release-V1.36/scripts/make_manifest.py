"""Write the V1.36 incremental release manifest (Shawn 2026-10-25: "出一个黄色打印件好了"): the lower head shell of D-026 addendum 2,
one Yellow plate. The speaker pocket (racetrack outline, D-026 addendum) and its twelve sound holes sit 4.5 mm further forward so
the lower jaw covers the whole rim of every hole, and the two amplifier rails are gone (print/mouth-floor-20261024/build_mouth_floor.py,
checks-floor.json). Replaces the printed V1.33 shell.

Pose: the V1.33 row unchanged (V1.8 pose, floor on the bed, the V1.30 support blockers); the pocket opens upwards and the holes go
straight through the floor. Wall check: a FAIL region is accepted only where a printed reference part, posed the same way, already
fails at the same place and the surface there is unchanged (old_allowances of release-V1.33/scripts/make_manifest.py); the
references are the printed V1.33 and V1.30 shells and the V1.8 shell.

    /tmp/microduck-cad-venv/bin/python scripts/make_manifest.py
"""
import hashlib, json, sys
from pathlib import Path
import numpy as np, trimesh
HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent; SIM = PRINT.parent.parent
sys.path.insert(0, str(SIM / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009'))
import wall_check  # noqa: E402
V133 = PRINT / 'release-V1.33/manifest-V1.33.json'; V135 = PRINT / 'release-V1.35/manifest-V1.35.json'
MF = PRINT / 'mouth-floor-20261024'; WORLD = PRINT / 'world'
m133 = json.loads(V133.read_text()); m135 = json.loads(V135.read_text())
row133 = next(r for r in m133['parts'] if r['key'] == 'head_bottom')
floor = json.loads((MF / 'checks-floor.json').read_text())
T = np.array(row133['sourceToPrint'])


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p): return {'path': str(Path(p).resolve()), 'sha256': sha(p)}


def pose(stl, T):
    k = trimesh.load(stl, force='mesh', process=False); k.apply_transform(T); k.apply_translation([0, 0, -k.bounds[0, 2]]); return k


def old_allowances(key, k, olds):
    """release-V1.33/scripts/make_manifest.py old_allowances, unchanged."""
    refs = []
    for stl, Tr, label in olds:
        om = pose(stl, Tr); mo = wall_check.measure(om)
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


HB_CHANGE = ('D-026 addendum 2 (Shawn 2026-10-25: "发声孔没法被下颚完全盖住 … 移到贴住前面板的位置", "把功放的限位去掉 我想贴哪里就贴哪里"): '
             'the speaker pocket, in the speaker\'s racetrack outline plus 0.2 mm (D-026 addendum; the V1.33 print had a 30.4 x 20.4 rectangle), '
             f'and its twelve dia 2.5 holes move 4.5 mm forward to centre x {floor["params"]["SPK_X"]}: the whole rim of every hole is over the lower '
             f'jaw (on V1.33 the front row was partly off it); {floor["pocketToFaceSlotWallMm"]["min"]} mm of floor between the pocket and the face '
             f'slot; floor left under the pocket {floor["floorLeftUnderPocketMm"]["min"]} mm or more. The two amplifier rails are removed; the '
             'amplifier is taped on the flat floor. The exit slot and everything else are the V1.33 shell.')
olds = [(PRINT / 'release-V1.33/run-inputs/head_bottom-print.stl', np.eye(4), 'V1.33 lower head shell (printed 2026-10-24)'),
        (PRINT / 'neck-exit-20261023/head_bottom_exit.stl', T, 'V1.30 lower head shell (printed 2026-10-23)'),
        (WORLD / 'head_bottom_v18.stl', T, 'V1.8 lower head shell (printed 2026-10-12)')]
stl = WORLD / 'head_bottom.stl'
assert sha(stl) == floor['sha256']['head_bottom_mouth-world'] or sha(stl) == sha(MF / 'head_bottom_mouth-world.stl'), 'world shell is not the floor build output'
k = pose(stl, T)
allow = old_allowances('head_bottom', k, olds)
pstl = REL / 'run-inputs/head_bottom-print.stl'; pstl.parent.mkdir(exist_ok=True); k.export(pstl)
area = float(k.area_faces[np.max(np.abs(k.triangles[:, :, 2]), axis=1) <= .01].sum()); size = (k.bounds[1] - k.bounds[0]).round(2).tolist()
assert area >= 200.0, area
regs = [g for g in wall_check.check(k.copy(), allow, 'head_bottom')['regions'] if g['status'] == 'FAIL']
assert not regs, regs
row = dict(key='head_bottom', color='Yellow', quantity=1, decision='replacement', replacesStockIds=row133['replacesStockIds'],
           path=str(stl), sha256=sha(stl), sourceFrame=row133['sourceFrame'], sourceToPrint=T.tolist(),
           flatContact={'minimumAreaMm2': 200.0}, poseName=row133['poseName'], poseOrigin='V1.33 row pose unchanged (V1.8 lower-shell pose, floor on the bed).',
           poseCheck=dict(printStl=ref(pstl), bedContactMm2=round(area, 2), printSizeMm=size, registrationMaxDeviationMm=0.0,
                          note='world STL in the row pose, dropped to the bed'),
           changeReason=HB_CHANGE, supersedes='head_bottom (V1.33, yellow, printed)',
           incrementalEvidence=ref(MF / 'checks-floor.json'),
           evidenceAlso=[ref(MF / 'build_mouth_floor.py'), ref(MF / 'checks.json'), ref(MF / 'build_exit_stadium.py')],
           thinWallAllowances=allow, supportBlockers=row133['supportBlockers'])
b = k.bounds
placements = dict(Yellow=[dict(key='head_bottom', copy=1, translation=[round(128.0 - (b[0, 0] + b[1, 0]) / 2, 4), round(128.0 - (b[0, 1] + b[1, 1]) / 2, 4), 0.0])])
print('head_bottom contact', round(area, 1), 'size', size, 'allowances', len(allow))
m = dict(m135)
m.update(parts=[row], placements=placements, version='V1.36', processOverrides={},
         processOverrideReason='Yellow: the donor profiles as is (as V1.30 and V1.33).',
         retiredParts=[{'part': 'head_bottom', 'printed': 'V1.33 (Yellow)', 'reason': 'replaced by the V1.36 shell: speaker pocket and holes 4.5 mm forward, no amplifier rails; the V1.33 shell still works as a spare'}],
         prototypeScope=('V1.36 delta package: one Yellow plate with the lower head shell (speaker pocket and twelve holes 4.5 mm forward, racetrack '
                         'pocket, no amplifier rails, the V1.33 long-round exit).'),
         knownFitBoundary=('Speaker pocket 0.2 mm clearance per side on the CMS-30204-18SP datasheet outline (30 x 20, R 10 ends), not a measured unit; '
                           'the camera board passes 0.58 mm over the speaker on 0.3 mm tape. Amplifier placed by hand on foam tape: the modelled spot '
                           'clears the face by 0.35 mm and the camera board by 0.76 mm, and it may slide up to 4 mm back. Printed sizes not measured.'))
m.pop('deferred', None)
m['deliveryContract'] = dict(m135['deliveryContract'], colors=['Yellow'], filesPerColor=2, fileCount=2, baseline='printed releases through V1.34',
                             status='INCREMENTAL_REPLACEMENT', supersedes=['head_bottom of V1.33 (printed, Yellow)'])
(REL / 'manifest-V1.36.json').write_text(json.dumps(m, indent=1, ensure_ascii=False)); print('ok', placements)
