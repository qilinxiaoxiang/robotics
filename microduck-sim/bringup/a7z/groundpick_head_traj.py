"""Neck and head joint trajectory of the pickup bend (D-027: groundpick61, Pollen's ground-pick policy, the motion the
open-beak bend builds on), from the as-built MuJoCo dry run of walk_brain (guide/firmware/mac/brain_sim_check.py: stand61,
groundpick from 3 s to the lowest phase 0.4, 2 s hold, rise). Writes groundpick-head-traj.json (deg, per 20 ms tick);
head_sweep_v2.py measures the head wire span over it.   python3 groundpick_head_traj.py"""
import json, os, subprocess, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAC = HERE.parents[1] / 'guide' / 'firmware' / 'mac'
PY = os.path.expanduser('~/.venvs/microduck-dyn/bin/python')
ARGS = ['--model', 'asbuilt', '--walk-at', '100', '--gp-at', '3', '--gp-phase', '0.4', '--gp-hold-s', '2']
NAMES = ('neck_pitch', 'head_pitch', 'head_yaw', 'head_roll')
COL = {'head_pitch': 10, 'neck_pitch': 11, 'head_yaw': 12, 'head_roll': 13}   # walk_brain.NAMES order of the tick-log q

with tempfile.TemporaryDirectory() as td:
    log = Path(td) / 'gp.jsonl'
    r = subprocess.run([PY, 'brain_sim_check.py', *ARGS, '--tick-log', str(log)], cwd=MAC, capture_output=True, text=True, timeout=600)
    if r.returncode:
        raise SystemExit(r.stderr[-2000:])
    summary = json.loads(next(l for l in r.stdout.splitlines() if l.startswith('{')))
    rows = [json.loads(l) for l in log.read_text().splitlines()]
traj = [[round(row['t'], 2)] + [round(float(row['q'][COL[n]]) * 57.29578, 1) for n in NAMES]
        for row in rows if row.get('mode') == 'groundpick' and row.get('q')]
gp = summary['groundpick']
out = {'source': 'bringup/a7z/groundpick_head_traj.py', 'command': 'brain_sim_check.py ' + ' '.join(ARGS), 'columns': ['t', *NAMES],
       'fell': summary['fell_at'], 'maxTiltDeg': gp['max_tilt'], 'lowest': {n: round(gp['pose_at_min'][n] * 57.29578, 1) for n in NAMES},
       'traj': traj}
(HERE / 'groundpick-head-traj.json').write_text(json.dumps(out) + '\n')
print(len(traj), 'ticks; lowest', out['lowest'], 'fell', out['fell'])
