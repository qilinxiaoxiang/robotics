#!/usr/bin/env python3
"""Natively slice selected orientation candidates, one part per plate, through the unmodified release pipeline.

    python3 scripts/slice_candidates.py PLAN.json [--machines Bambu Elegoo] [--only KEY/SLUG ...]

PLAN.json: [{"key", "slug", "name", "sourceToPrint"}]. For each row this driver writes a single-part study manifest
(version STUDY-..., never packaged), then runs release_pipeline.py prepare, release_pipeline.py slice and
slice_readback.py, each as its own job under the exclusive run_bounded_cad.py guard (no --parallel-light). The
driver itself loads no meshes. A lock held by another agent returns exit 75; the row is left for a later retry.
Outputs: slices/<key>/<slug>/ (manifest, preparation, native archives, readback-<Machine>.json, resource reports).
"""
import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
FINAL = HERE.parent / 'release-V1.6-final' / 'final-V1.6.json'
PIPE = HERE.parents[2] / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009/release_pipeline.py'
GUARD = HERE.parents[2] / 'build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py'
PY = '/tmp/microduck-cad-venv/bin/python'
BUDGET = {'prepare': (768, 120), 'slice': (1536, 300), 'readback': (1024, 300)}


def guarded(tag, run, argv):
    mib, sec = BUDGET[tag.split('-')[0]]
    report = run / f'{tag}-resource.json'
    cmd = ['python3', str(GUARD), '--max-mib', str(mib), '--seconds', str(sec), '--wait-lock-seconds', '60',
           '--report', str(report), '--', *argv]
    with (run / f'{tag}.log').open('w') as log:
        code = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT).returncode
    return code


def manifest_for(row, contact, final_path=FINAL):
    final = json.loads(final_path.read_text())
    part = json.loads(json.dumps(next(p for p in final['parts'] if p['key'] == row['key'])))
    part['sourceToPrint'] = row['sourceToPrint']
    # Intended contact for this candidate: its own measured contact within 0.01 mm, rounded down.
    # (rounded down with margin; the screen report rounds contact to 0.1 mm2).
    part['flatContact'] = {'minimumAreaMm2': max(0.01, math.floor(min(contact * 0.95, contact - 0.1) * 100) / 100)}
    part['quantity'] = 1
    for k in ('geometryEvidence', 'priorV14Source', 'compatibility'):
        part.pop(k, None)
    slug = ''.join(c if c.isalnum() else '-' for c in row['slug'])
    return dict(schemaVersion=1, releaseKind='incremental', version=f"STUDY-{row['key']}-{slug}"[:80],
                prototype=True, prototypeScope=f"ORIENTATION STUDY ONLY, NOT A RELEASE: {row['key']} posed as '{row['name']}'.",
                baselineStock=final['baselineStock'], profiles=final['profiles'], parts=[part])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan', type=Path)
    ap.add_argument('--machines', nargs='+', default=['Bambu'])
    ap.add_argument('--only', nargs='*')
    ap.add_argument('--final', type=Path, default=FINAL, help='release manifest that holds the part (default V1.6 final)')
    args = ap.parse_args()
    plan = json.loads(args.plan.read_text())
    for row in plan:
        tag = f"{row['key']}/{row['slug']}"
        if args.only and tag not in args.only and row['key'] not in args.only:
            continue
        run = HERE / 'slices' / row['key'] / row['slug']
        run.mkdir(parents=True, exist_ok=True)
        prep = run / 'run' / 'preparation.json'
        if not prep.exists():
            # The manifest is written once per preparation; preparation and native results bind its hash.
            (run / 'manifest.json').write_text(json.dumps(manifest_for(row, row['contactMm2'], args.final), indent=1) + '\n')
            code = guarded('prepare', run, [PY, str(PIPE), 'prepare', str(run / 'manifest.json'), str(run / 'run')])
            if code:
                print(tag, 'prepare failed', code, file=sys.stderr)
                continue
        color = json.loads(prep.read_text())['parts'][0]['color']
        for machine in args.machines:
            native = run / 'run' / 'native' / f'{color}_{machine}' / 'result.json'
            if not native.exists():
                code = guarded(f'slice-{machine}', run, [PY, str(PIPE), 'slice', str(prep), color, machine])
                if code:
                    print(tag, machine, 'slice failed', code, file=sys.stderr)
                    continue
            rb = run / f'readback-{machine}.json'
            if not rb.exists():
                code = guarded(f'readback-{machine}', run, [PY, str(HERE / 'scripts' / 'slice_readback.py'), str(run / 'run'), color, machine, str(rb)])
                if code:
                    print(tag, machine, 'readback failed', code, file=sys.stderr)
                    continue
            r = json.loads(rb.read_text())
            print(f"{tag} {machine}: {r['etaMinutes']} min, {r['headerGrams']} g total, support {r['supportGrams']} g, "
                  f"first layer {[round(x['model_area_mm2']) for x in r['firstLayer']]} mm2, layers {r['layers']}", flush=True)


if __name__ == '__main__':
    main()
