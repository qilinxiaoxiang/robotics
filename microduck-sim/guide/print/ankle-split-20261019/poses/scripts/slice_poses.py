#!/usr/bin/env python3
"""Natively slice selected split-ankle poses, one part per plate, through the unmodified release pipeline v2 (the V1.22
pipeline: release_pipeline_v2.py prepare / slice, the plate profiles of manifest-V1.22.json, R1 brim per part).

    /tmp/microduck-cad-venv/bin/python slice_poses.py PLAN.json [--machines Bambu Elegoo] [--only KEY/SLUG ...]

PLAN.json rows: {"key", "slug", "name", "candidate"} where candidate is a candidate name in screen.json (a pose in the
PRINT-STL frame). The study manifest references the LOCAL STL (STL/*-local.stl) with the composed matrix
local -> print = normalise(candidate.sourceToPrint @ localToPrintStl), so the pipeline checks exactly the matrix that
poses.json hands to the parent. Every job runs under run_bounded_cad.py (exclusive lock, 10 minute cap); a busy lock
(exit 75) is retried. Outputs: slices/<key>/<slug>/ (manifest.json, run/, readback-<Machine>.json, faces-<Machine>.json,
*.log, *-resource.json). The driver itself loads one mesh per row (to compose the matrix); no slicing in-process.
"""
import argparse, hashlib, json, math, subprocess, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent; POSES = HERE.parent
SIM = Path('/Users/xiangzheng/code/robotics/microduck-sim')
PIPE = SIM / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009/release_pipeline_v2.py'
GUARD = SIM / 'build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py'
STUDY = SIM / 'guide/print/orientation-study'
ANKLE = SIM / 'build-pack-20260913/redesign-20260913/ankle-redesign-20261007'
PY = '/tmp/microduck-cad-venv/bin/python'
BUDGET = {'prepare': (1024, 180), 'slice': (1536, 300), 'readback': (1024, 300), 'faces': (1024, 300)}
sys.path.insert(0, str(STUDY)); sys.dont_write_bytecode = True
from orientation_check import load_mesh, normalise  # noqa: E402


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def guarded(tag, run, argv, tries=6):
    mib, sec = BUDGET[tag.split('-')[0]]
    report = run / f'{tag}-resource.json'
    cmd = ['/opt/homebrew/bin/python3', str(GUARD), '--max-mib', str(mib), '--seconds', str(sec), '--wait-lock-seconds', '60',
           '--report', str(report), '--', *argv]
    for attempt in range(tries):
        with (run / f'{tag}.log').open('a') as log:
            log.write(f'# attempt {attempt + 1} {time.strftime("%Y-%m-%dT%H:%M:%S")}\n'); log.flush()
            code = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT).returncode
        if code != 75:
            return code
        time.sleep(20)
    return 75


def manifest_for(row, cand, l2p, screen_part, template):
    L = np.array(l2p['localToPrintStl'], float)
    T = np.array(cand['sourceToPrint'], float) @ L
    m = load_mesh(l2p['localStl'])
    T = normalise(m, T)
    p = m.copy(); p.apply_transform(T)
    contact = float(p.area_faces[p.triangles[:, :, 2].max(1) <= 0.01].sum())
    assert abs(contact - cand['contactMm2']) < 0.5, (row['key'], contact, cand['contactMm2'])
    color = next(x['color'] for x in template['parts'] if x['key'] == row['key'])
    part = dict(key=row['key'], color=color, quantity=1, decision='addition', replacesStockIds=[],
                path=l2p['localStl'], sha256=l2p['localSha256'], sourceToPrint=T.tolist(),
                flatContact={'minimumAreaMm2': max(0.01, math.floor(min(contact * 0.95, contact - 0.1) * 100) / 100)},
                sourceFrame='ankle-redesign-20261007 local frame (motor shaft = Z; mm)',
                poseName=row['name'], screenCandidate=cand['name'],
                changeReason=f"ORIENTATION STUDY: {row['key']} posed as '{row['name']}' (screen candidate '{cand['name']}')",
                incrementalEvidence={'path': str(ANKLE / 'print-review.json'), 'sha256': sha(ANKLE / 'print-review.json')})
    slug = ''.join(c if c.isalnum() else '-' for c in row['slug'])
    return dict(schemaVersion=1, releaseKind='incremental', version=f"STUDY-{row['key']}-{slug}"[:80], prototype=True,
                prototypeScope=f"ORIENTATION STUDY ONLY, NOT A RELEASE: {row['key']} posed as '{row['name']}'.",
                baselineStock=template['baselineStock'], profiles=template['profiles'], parts=[part]), dict(
                    localToPrint=T.tolist(), contactMm2=round(contact, 2), heightMm=round(float(p.extents[2]), 2),
                    footprintMm=[round(float(x), 2) for x in p.extents[:2]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan', type=Path)
    ap.add_argument('--machines', nargs='+', default=['Bambu', 'Elegoo'])
    ap.add_argument('--only', nargs='*')
    args = ap.parse_args()
    plan = json.loads(args.plan.read_text())
    screen = {p['key']: p for p in json.loads((POSES / 'screen.json').read_text())['parts']}
    l2p_all = json.loads((POSES / 'local-to-printstl.json').read_text())
    template = json.loads((POSES / 'manifest-screen.json').read_text())
    for row in plan:
        tag = f"{row['key']}/{row['slug']}"
        if args.only and tag not in args.only and row['key'] not in args.only:
            continue
        run = POSES / 'slices' / row['key'] / row['slug']
        run.mkdir(parents=True, exist_ok=True)
        prep = run / 'run' / 'preparation.json'
        if not prep.exists():
            cand = next(c for c in screen[row['key']]['candidates'] if c['name'] == row['candidate'])
            manifest, pose = manifest_for(row, cand, l2p_all[row['key']], screen[row['key']], template)
            (run / 'manifest.json').write_text(json.dumps(manifest, indent=1) + '\n')
            (run / 'pose.json').write_text(json.dumps(dict(row, **pose), indent=1) + '\n')
            code = guarded('prepare', run, [PY, str(PIPE), 'prepare', str(run / 'manifest.json'), str(run / 'run')])
            if code:
                print(tag, 'prepare failed', code, file=sys.stderr); continue
        color = json.loads(prep.read_text())['parts'][0]['color']
        for machine in args.machines:
            native = run / 'run' / 'native' / f'{color}_{machine}' / 'result.json'
            if not native.exists():
                code = guarded(f'slice-{machine}', run, [PY, str(PIPE), 'slice', str(prep), color, machine])
                if code:
                    print(tag, machine, 'slice failed', code, file=sys.stderr); continue
            rb = run / f'readback-{machine}.json'
            if not rb.exists():
                code = guarded(f'readback-{machine}', run, [PY, str(STUDY / 'scripts/slice_readback.py'), str(run / 'run'), color, machine, str(rb)])
                if code:
                    print(tag, machine, 'readback failed', code, file=sys.stderr); continue
            fc = run / f'faces-{machine}.json'
            if not fc.exists():
                code = guarded(f'faces-{machine}', run, [PY, str(HERE / 'face_support.py'), str(run / 'run'), color, machine, str(fc)])
                if code:
                    print(tag, machine, 'faces failed', code, file=sys.stderr); continue
            r = json.loads(rb.read_text()); f = json.loads(fc.read_text())
            print(f"{tag} {machine}: {r['etaMinutes']} min, {r['headerGrams']} g, support {r['supportGrams']} g / {f['supportExtrusionTotalMm']} mm, "
                  f"first layer {[round(x['model_area_mm2']) for x in r['firstLayer']]} mm2, brim {f['brim']['objects']}", flush=True)
            for name, s in f['faceSets'].items():
                if s['must'] and (s['touchedMm2'] > 0 or s.get('supportInsideMm', 0) > 0):
                    print(f"    MUST {name}: touched {s['touchedMm2']} mm2 of {s['areaMm2']}, inside {s.get('supportInsideMm', 0)} mm")


if __name__ == '__main__':
    main()
