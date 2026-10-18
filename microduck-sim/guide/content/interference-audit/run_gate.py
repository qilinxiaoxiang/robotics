#!/usr/bin/env python3
"""MicroDuck print gate in one command (robotics/AGENTS.md): build_solids, pairs, steps_audit, cables under the bounded
runner, then a receipt that binds the results to the guide data they audited.

Pass criteria:
  solids   every audit solid closed;
  pairs    every final-pose pair deeper than 0.1 mm is an intended contact (pair_classes.pair_class == 'c');
  steps    0 parts drawn before they are present, 0 path collisions;
  cables   every finding is at a cable end (inside its terminal or housing), 0 mid-route penetration.
The receipt records the sha256 of guide/data/guide-data.json and of every guide/print/world STL; verify_current_design.py
rejects it when either has changed since. Each job is limited to 10 minutes by the runner.

Usage: /tmp/microduck-cad-venv/bin/python run_gate.py [--skip-run]   (--skip-run re-evaluates the existing outputs)
Writes gate-receipt.json next to this file; exit 0 only when every criterion passes.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

from pair_classes import pair_class

HERE = Path(__file__).resolve().parent
GUIDE = HERE.parent.parent
SIM = GUIDE.parent
RUNNER = SIM / 'build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py'
RUNS = HERE / 'gate-runs'
# build_solids recomputes every solid when ia_lib changes (about 2.3 GB peak); the other three stay under 1.5 GB.
# steps_audit.py peaks at about 1560 MiB RSS on an idle machine (2026-10-15, 158 parts, 73 steps); the 1280-1345 MiB
# seen earlier were measured under memory pressure, where compressed pages do not count as RSS.
JOBS = [('build_solids.py', 2560), ('pairs.py', 1536), ('steps_audit.py', 2000), ('cables.py', 1536)]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def inputs() -> dict:
    return {'guideData': sha(GUIDE / 'data/guide-data.json'),
            'world': {p.name: sha(p) for p in sorted((GUIDE / 'print/world').glob('*.stl'))}}


def run(script: str, mib: int) -> dict:
    RUNS.mkdir(exist_ok=True)
    report = RUNS / f'{script[:-3]}.json'
    cmd = [sys.executable, str(RUNNER), '--max-mib', str(mib), '--seconds', '600', '--wait-lock-seconds', '60',
           '--report', str(report), '--', sys.executable, script]
    for attempt in range(20):  # exit 75: lock or memory busy; the runner names the holder on stderr
        p = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
        if p.returncode != 75:
            break
        print(p.stderr.strip().splitlines()[-1] if p.stderr.strip() else 'busy', file=sys.stderr)
        time.sleep(5)
    r = json.loads(report.read_text()) if report.exists() else {}
    return {'script': script, 'exitCode': p.returncode, 'elapsedSeconds': r.get('elapsedSeconds'),
            'peakMiB': r.get('peakSampledTreeRssMiB'), 'stoppedByGuard': r.get('stoppedByGuard'),
            'tail': (p.stdout + p.stderr).strip().splitlines()[-3:] if p.returncode else []}


def evaluate() -> dict:
    J = lambda f: json.loads((HERE / f).read_text())
    solids, pairs, steps, cables = J('solids-report.json'), J('pairs-raw.json'), J('steps-raw.json'), J('cables-raw.json')
    deep = [r for r in pairs['pairs'] if r.get('depthMm', 0.0) > 0.1]
    unclassified = [{'a': r['a'], 'b': r['b'], 'depthMm': r['depthMm'], 'volumeMm3': round(r['volumeMm3'], 3)}
                    for r in deep if pair_class(r['a'], r['b'])[0] != 'c']
    premature = sum(len(s.get('drawnButNotPresent') or []) for s in steps['steps'])
    collisions = sum(len(s.get('pathCollisions') or []) for s in steps['steps'])
    mid = [f for f in cables['findings'] if not f.get('atEnd')]
    checks = {
        'solids': {'parts': solids['parts'], 'closed': solids['closed'], 'notClosed': solids['notClosed'],
                   'passed': solids['closed'] == solids['parts'] and not solids['notClosed']},
        'pairs': {'candidates': pairs['candidatePairs'], 'deeperThan0.1': len(deep), 'unclassified': unclassified,
                  'passed': not unclassified},
        'steps': {'steps': len(steps['steps']), 'drawnBeforePresent': premature, 'pathCollisions': collisions,
                  'passed': premature == 0 and collisions == 0},
        'cables': {'cables': len(cables['coverage']), 'findings': len(cables['findings']),
                   'midRoute': [{'cable': f['cable'], 'part': f['part'], 'depthMm': f['depthMm']} for f in mid],
                   'passed': not mid},
    }
    return checks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--skip-run', action='store_true')
    args = ap.parse_args()
    before = inputs()
    jobs = []
    if not args.skip_run:
        for script, mib in JOBS:
            jobs.append(run(script, mib))
            print(json.dumps(jobs[-1]), flush=True)
            if jobs[-1]['exitCode']:
                break
    checks = evaluate() if all(j['exitCode'] == 0 for j in jobs) else {}
    after = inputs()
    passed = bool(checks) and all(c['passed'] for c in checks.values()) and before == after
    receipt = {'checkedAt': datetime.datetime.now().astimezone().isoformat(timespec='seconds'),
               'passed': passed, 'ranJobs': not args.skip_run, 'jobs': jobs, 'checks': checks,
               'inputs': after, 'inputsStableDuringRun': before == after,
               'guideRevision': json.loads((GUIDE / 'data/guide-data.json').read_text()).get('revision')}
    (HERE / 'gate-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: receipt[k] for k in ('passed', 'guideRevision', 'inputsStableDuringRun')}
                     | {k: v['passed'] for k, v in checks.items()}))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
