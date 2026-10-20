#!/usr/bin/env python3
"""Natively slice candidate print poses of the four two-half ankle parts, one part per plate, through the unmodified release
pipeline v2 (prepare / slice with the V1.22 plate profiles and the R1 brim per part), then read each slice back
(orientation-study slice_readback.py) and project its support onto the functional faces (face_support.py, faces.py).

    /tmp/microduck-cad-venv/bin/python slice_poses.py [--machines Bambu Elegoo] [--only KEY/SLUG ...]

Candidates are named by the local axis that faces the bed (local z = shaft, y = up). Every job runs under
run_bounded_cad.py (exclusive lock, 10 minute cap); a busy lock (exit 75) is retried. Outputs: ../slices/<key>/<slug>/.
"""
import argparse, hashlib, json, math, subprocess, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent; POSES = HERE.parent; HALVES = POSES.parent
SIM = Path('/Users/xiangzheng/code/robotics/microduck-sim')
PIPE = SIM / 'build-pack-20260913/redesign-20260913/printing/13-RELEASE-PIPELINE-20261009/release_pipeline_v2.py'
GUARD = SIM / 'build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py'
STUDY = SIM / 'guide/print/orientation-study'
TEMPLATE = SIM / 'guide/print/ankle-split-20261019/poses/manifest-screen.json'   # V1.22 baseline stock and plate profiles
PY = '/tmp/microduck-cad-venv/bin/python'
BUDGET = {'prepare': (1024, 180), 'slice': (1536, 300), 'readback': (1024, 300), 'faces': (1024, 300)}
sys.path.insert(0, str(STUDY)); sys.dont_write_bytecode = True
from orientation_check import load_mesh, normalise  # noqa: E402

# local axis facing the bed -> rotation local -> print (print z up)
DOWN = {'+x': [[0, 0, 1], [0, 1, 0], [-1, 0, 0]], '-x': [[0, 0, -1], [0, 1, 0], [1, 0, 0]],
        '+y': [[1, 0, 0], [0, 0, 1], [0, -1, 0]], '-y': [[1, 0, 0], [0, 0, -1], [0, 1, 0]],
        '+z': [[1, 0, 0], [0, -1, 0], [0, 0, -1]], '-z': [[1, 0, 0], [0, 1, 0], [0, 0, 1]]}
# Screened by bed contact and the MUST faces (faces.py): the outer half's motor face and the inner half's capture lip face
# down when the cut face is on the bed (+z / -z); the plate exteriors are 7 deg off the shaft and on the outer half the four
# output screw seats would face down 2-3 mm above the bed; the foot block underside (-y) has no flat face (the prepare
# check finds no planar contact). So the candidates stand on a side end (+-x).
PLAN = [(k, d) for k in ('left_outer', 'left_inner') for d in ('+x', '-x')]
# 'heel': the inner half on its stock heel chamfer (make_halves.HEEL_N, 55 mm2), the shaft flat and the teardrop roof of the
# pocket pointing up; added after the +-x and -z inner rows put support inside the d15 pocket.
HEEL_N = (-0.8700, 0.4930)


def rotation(key, down):
    if down != 'heel':
        return np.array(DOWN[down], float)
    sign = 1 if key.startswith('left') else -1
    n = np.array([sign * HEEL_N[0], HEEL_N[1]]); n /= np.linalg.norm(n)
    a = -np.pi / 2 - np.arctan2(n[1], n[0])               # turn n onto local -y about the shaft
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    return np.array(DOWN['-y'], float) @ Rz


def slug_of(down):
    return 'heel-down' if down == 'heel' else ('p' if down[0] == '+' else 'm') + down[1] + '-down'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def guarded(tag, run, argv, tries=8):
    mib, sec = BUDGET[tag.split('-')[0]]
    report = run / f'{tag}-resource.json'
    cmd = ['/opt/homebrew/bin/python3', str(GUARD), '--max-mib', str(mib), '--seconds', str(sec), '--wait-lock-seconds', '60', '--report', str(report), '--', *argv]
    for attempt in range(tries):
        with (run / f'{tag}.log').open('a') as log:
            log.write(f'# attempt {attempt + 1} {time.strftime("%Y-%m-%dT%H:%M:%S")}\n'); log.flush()
            code = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT).returncode
        if code != 75:
            return code
        time.sleep(20)
    return 75


def manifest_for(key, down, template):
    side, kind = key.split('_'); stl = HALVES / 'STL' / f'{side}-{kind}-local.stl'
    m = load_mesh(stl); T = np.eye(4); T[:3, :3] = rotation(key, down); T = normalise(m, T)
    p = m.copy(); p.apply_transform(T)
    contact = float(p.area_faces[p.triangles[:, :, 2].max(1) <= 0.01].sum())
    part = dict(key=f'ankle_{kind}_{side}', color='Orange', quantity=1, decision='addition', replacesStockIds=[],
                path=str(stl), sha256=sha(stl), sourceToPrint=T.tolist(),
                flatContact={'minimumAreaMm2': max(0.01, math.floor(min(contact * 0.95, contact - 0.1) * 100) / 100)},
                sourceFrame='ankle-halves-20261020 local frame (motor shaft = Z, up = Y; mm)', poseName=f'local {down} down',
                changeReason=f'ORIENTATION STUDY: {key} with local {down} on the bed',
                incrementalEvidence={'path': str(HALVES / 'halves-check.json'), 'sha256': sha(HALVES / 'halves-check.json')})
    man = dict(schemaVersion=1, releaseKind='incremental', version=f'STUDY-{key}-{slug_of(down)}', prototype=True,
               prototypeScope=f'ORIENTATION STUDY ONLY, NOT A RELEASE: {key} with local {down} on the bed.',
               baselineStock=template['baselineStock'], profiles=template['profiles'], parts=[part])
    return man, dict(key=key, down=down, sourceToPrint=T.tolist(), localStl=dict(path=str(stl), sha256=sha(stl)), contactMm2=round(contact, 2),
                     heightMm=round(float(p.extents[2]), 2), footprintMm=[round(float(x), 2) for x in p.extents[:2]])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--machines', nargs='+', default=['Bambu', 'Elegoo']); ap.add_argument('--only', nargs='*')
    ap.add_argument('--plan', nargs='*', help='extra KEY/DOWN rows, e.g. right_outer/-x'); a = ap.parse_args()
    template = json.loads(TEMPLATE.read_text())
    plan = PLAN + [tuple(r.split('/')) for r in (a.plan or [])]
    for key, down in plan:
        slug = slug_of(down); tag = f'{key}/{slug}'
        if a.only and tag not in a.only and key not in a.only:
            continue
        run = POSES / 'slices' / key / slug; run.mkdir(parents=True, exist_ok=True)
        prep = run / 'run' / 'preparation.json'
        if not prep.exists():
            man, pose = manifest_for(key, down, template)
            (run / 'manifest.json').write_text(json.dumps(man, indent=1) + '\n'); (run / 'pose.json').write_text(json.dumps(pose, indent=1) + '\n')
            code = guarded('prepare', run, [PY, str(PIPE), 'prepare', str(run / 'manifest.json'), str(run / 'run')])
            if code:
                print(tag, 'prepare failed', code, flush=True); continue
        for machine in a.machines:
            if not (run / 'run' / 'native' / f'Orange_{machine}' / 'result.json').exists():
                code = guarded(f'slice-{machine}', run, [PY, str(PIPE), 'slice', str(prep), 'Orange', machine])
                if code:
                    print(tag, machine, 'slice failed', code, flush=True); continue
            rb = run / f'readback-{machine}.json'
            if not rb.exists() and guarded(f'readback-{machine}', run, [PY, str(STUDY / 'scripts/slice_readback.py'), str(run / 'run'), 'Orange', machine, str(rb)]):
                print(tag, machine, 'readback failed', flush=True); continue
            fc = run / f'faces-{machine}.json'
            if not fc.exists() and guarded(f'faces-{machine}', run, [PY, str(HERE / 'face_support.py'), str(run / 'run'), 'Orange', machine, str(fc)]):
                print(tag, machine, 'faces failed', flush=True); continue
            r = json.loads(rb.read_text()); f = json.loads(fc.read_text())
            print(f"{tag} {machine}: {r['etaMinutes']} min, {r['headerGrams']} g, support {r['supportGrams']} g / {f['supportExtrusionTotalMm']} mm, "
                  f"first layer {[round(x['model_area_mm2']) for x in r['firstLayer']]} mm2, brim {f['brim']['passed']}", flush=True)
            for name, s in f['faceSets'].items():
                if s['must'] and (s['touchedMm2'] > 0 or s.get('supportInsideMm', 0) > 0):
                    print(f"    MUST {name}: touched {s['touchedMm2']} mm2 of {s['areaMm2']}, inside {s.get('supportInsideMm', 0)} mm", flush=True)
                elif s['touchedMm2'] > 0:
                    print(f"    report {name}: touched {s['touchedMm2']} mm2 of {s['areaMm2']}", flush=True)


if __name__ == '__main__':
    main()
