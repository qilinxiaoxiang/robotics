"""Hand features for one labelled touch episode (draft, 2026-10-21; proposed home .../extension-20261015-touch/gesture/).

An episode is the pad rows between a label start and end (record_touch.py), plus, when a brain tick log covers the
same wall-clock span, the IMU and head-joint rows of walk_wired.py's log (acc, gyro_body, q, action) joined by `t`.
Baselines: per-pad median of the 2 s before the start (rest), noise = its standard deviation; a pad is "on" when its
delta exceeds max(ON_K * noise, ON_MIN) (both from the recording, never library defaults: PLAN.md Software).
"""
import math
import statistics as st

PADS = ['L1', 'R1', 'L2', 'R2', 'M']
ON_K, ON_MIN = 5.0, 150.0           # counts; recheck against the per-pad bench deltas before the first training run
HEAD = (5, 6, 7, 8)                  # OBSERVATION_DOF_ORDER slots: neck_pitch, head_pitch, head_yaw, head_roll
DEFAULT_HEAD = (0.3491, 0.3491, 0.0, 0.0)
FEATURE_NAMES = ['duration_s', 'n_pads_on', 'peak_delta', 'peak_delta_2nd', 'rise_slope', 'onset_spread_s', 'order_lr_m',
                 'n_rises', 'tap_interval_s', 'sim_rise', 'acc_peak', 'gyro_peak', 'head_err_jump', 'm_share']


def episode_features(pad_rows, rest_rows, imu_rows=None):
    """pad_rows/rest_rows: [{'t', 'v': [5]}]; imu_rows: [{'t', 'acc': [3], 'gyro_body': [3], 'q': [14], 'action': [14]}]."""
    base = [st.median(r['v'][i] for r in rest_rows) for i in range(5)]
    noise = [max(1.0, st.pstdev(r['v'][i] for r in rest_rows)) for i in range(5)]
    t0, t1 = pad_rows[0]['t'], pad_rows[-1]['t']
    d = [[r['v'][i] - base[i] for i in range(5)] for r in pad_rows]
    thr = [max(ON_K * noise[i], ON_MIN) for i in range(5)]
    on = [[row[i] > thr[i] for i in range(5)] for row in d]
    onset = [next((pad_rows[k]['t'] - t0 for k in range(len(d)) if on[k][i]), None) for i in range(5)]
    peaks = sorted((max(row[i] for row in d) for i in range(5)), reverse=True)
    slope = max((d[k][i] - d[k - 1][i] for k in range(1, len(d)) for i in range(5)), default=0.0)
    n_on = sum(o is not None for o in onset)
    ons = [o for o in onset if o is not None]
    spread = (max(ons) - min(ons)) if len(ons) >= 2 else 0.0
    # stroke order L1 -> R1 -> M (or the mirror): +1 when onsets increase along that path, -1 reversed, 0 unknown
    order = 0.0
    path = [onset[0], onset[1], onset[4]]
    if all(o is not None for o in path):
        order = 1.0 if path[0] < path[1] < path[2] else -1.0 if path[0] > path[1] > path[2] else 0.0
    # taps: rises of the strongest pad through its threshold
    imax = max(range(5), key=lambda i: max(row[i] for row in d))
    rises = [k for k in range(1, len(d)) if on[k][imax] and not on[k - 1][imax]]
    gaps = [pad_rows[b]['t'] - pad_rows[a]['t'] for a, b in zip(rises, rises[1:])]
    sim = 1.0 if n_on >= 2 and spread < 0.1 else 0.0
    acc_peak = gyro_peak = head_jump = 0.0
    if imu_rows:
        acc_peak = max((abs(math.sqrt(sum(a * a for a in r['acc'])) - 9.81) for r in imu_rows if r.get('acc')), default=0.0)
        gyro_peak = max((math.sqrt(sum(g * g for g in r['gyro_body'])) for r in imu_rows), default=0.0)
        errs = []
        for r in imu_rows:
            if r.get('action') is None:
                continue
            errs.append([r['q'][j] - (DEFAULT_HEAD[n] + r['action'][j]) for n, j in enumerate(HEAD)])
        if len(errs) >= 2:  # change of the error, not the error: the standing head carries a static offset (1018d)
            head_jump = max(abs(errs[k][j] - errs[0][j]) for k in range(1, len(errs)) for j in range(4))
    m_share = (max(row[4] for row in d)) / (peaks[0] + 1.0)
    return dict(zip(FEATURE_NAMES, [t1 - t0, n_on, peaks[0], peaks[1], slope, spread, order, len(rises),
                                    st.mean(gaps) if gaps else 0.0, sim, acc_peak, gyro_peak, head_jump, m_share]))
