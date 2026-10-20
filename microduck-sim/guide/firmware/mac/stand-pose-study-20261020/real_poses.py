"""Real-robot poses used as sim inputs (read from the archived walk_wired logs, q in walk_brain.NAMES order, model rad).

1. start_7deg: the last monitor-mode row before the 2026-10-18 run 1018d stand entry (IMU pitch 7.1 deg forward), the
   start from which the STAND ramp fell within about 1.5 s.
2. stand61_mean: mean q of walk-mode stand61 ticks at zero command with the trunk upright (gb z < -0.99), run 1019f
   (A7Z, 2026-10-19), as the coordinator specified; and its left/right symmetrised version.
Writes real_poses.json.
"""
import gzip, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
sys.path.insert(0, MAC); sys.path.insert(0, os.path.join(MAC, '..', 'pi'))
from stand_pose import NEUTRAL_POSE
from walk_brain import NAMES  # noqa: E402  (run with ~/.venvs/microduck-dyn/bin/python)


def rows(f):
    return [json.loads(l) for l in gzip.open(f)]


def pitch(gb):
    return math.degrees(math.atan2(gb[0], -gb[2]))


out = {'names': NAMES}
r = rows(os.path.join(MAC, 'robot-runs-20261018/duck_wired_log_1018d.jsonl.gz'))
i = next(k for k, x in enumerate(r) if x['mode'] == 'stand')
pre = r[i - 1]
out['start_7deg'] = dict(source='robot-runs-20261018/duck_wired_log_1018d.jsonl.gz row %d (last monitor row before stand)' % (i - 1),
                         imu_pitch_deg=round(pitch(pre['gb']), 2), q=dict(zip(NAMES, pre['q'])))
r = rows(os.path.join(MAC, 'robot-runs-20261019-a7z/duck_wired_log_1019f.jsonl.gz'))
sel = [x for x in r if x['mode'] == 'walk' and x.get('policy', None) in (None, 'stand') and x['gb'][2] < -0.99
       and x.get('action') is not None and (x.get('cmd') or {}).get('vx', 0) == 0 and not x.get('missing')]
# policy name is in info only when a policy ran; walk ticks at zero command before stepping are stand61
sel = [x for x in sel if x.get('policy', 'stand') == 'stand']
mean = {n: sum(x['q'][k] for x in sel) / len(sel) for k, n in enumerate(NAMES)}
delta = {n: round(mean[n] - NEUTRAL_POSE[n], 4) for n in NAMES}
sym = {}
for n in NAMES:
    if n.startswith('right_') or n.startswith('left_'):
        j = n.split('_', 1)[1]
        # mirrored joints: pitch/knee/ankle and roll flip sign between sides in NEUTRAL; yaw also mirrored
        dr, dl = delta['right_' + j], delta['left_' + j]
        avg = (dr - dl) / 2  # right delta and minus left delta describe the same motion
        sym[n] = round(avg if n.startswith('right_') else -avg, 4)
    else:
        sym[n] = delta[n]
out['stand61_mean_1019f'] = dict(ticks=len(sel), delta_from_neutral=delta, symmetrised_delta=sym,
                                 imu_pitch_deg_mean=round(sum(pitch(x['gb']) for x in sel) / len(sel), 2))
json.dump(out, open(os.path.join(HERE, 'real_poses.json'), 'w'), indent=1)
print(json.dumps(out, indent=1))
