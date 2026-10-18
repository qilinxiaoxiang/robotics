"""Reconstruct the measured Pi <-> Mac control timeline from the Mac-side walk log.

Input: link-log-last3000.jsonl, the last 3000 rows of /tmp/duck_walk_log.jsonl copied 2026-10-14 01:10 EDT.
Row fields used: t (Mac receive time, time.time()), pi_t (Pi time.time() when the state packet was packed, right
after the joint read), read_ms (Pi joint sync_read duration), imu_age (Pi perf_counter age of the IMU snapshot at
packing; host-receipt based, BNO085 internal latency not included).

Pi loop (guide/firmware/pi/pi_bridge.py): drain UDP commands -> sync_write goals -> sync_read joints -> pack/send.
Mac loop (guide/firmware/mac/walk_brain.py): every received state -> policy -> command packet back.

Per state i (Pi clock; the two clocks are treated as equal because min(rx_lag) = 0.16 ms over the window, so the
offset is below that and is absorbed as transit):
  joint sample   s_j[i] = pi_t[i] - read_ms[i]/2           (bridge stamps the middle of the read)
  imu sample     s_i[i] = pi_t[i] - imu_age[i]
  Mac receive    r[i]   = t[i]
  Mac send       r[i] + 1 ms                               (assumption: ONNX + packing)
  Pi arrival     a[i]   = r[i] + 1 ms + back[i]            back[i]: return one-way latency, drawn without
                                                           replacement from the measured forward rx_lag set
                                                           (assumption: symmetric Wi-Fi path), rng seed 0
  Pi write times W[k]   = pi_t[k] - read_ms[k]             (goals are written immediately before the read)
  Pi drain times D[k]   = W[k] - 1 ms                      (assumption: sync_write takes ~1 ms)
A command is applied at the first W[k] whose D[k] >= a[i]; if several arrive before one drain, only the newest is
applied (pi_bridge keeps the highest sequence). Applied age = W[k] - s_j[i] (what pi_bridge reports as
applied_age). Between writes the goal in force is held; the age of the goal in force at time T is T - s_j[i*].
"""
from pathlib import Path
import json
import numpy as np

HERE = Path(__file__).resolve().parent
COMPUTE_S = 0.001
WRITE_S = 0.001


def build(path=HERE / 'link-log-last3000.jsonl', rx_lag_cap_s=None):
    """rx_lag_cap_s: counterfactual link with each one-way latency clipped at this value (Wi-Fi bursts removed);
    Mac receive times become pi_t + min(rx_lag, cap) and the return latency is clipped the same way."""
    rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    t = np.array([r['t'] for r in rows]); pi_t = np.array([r['pi_t'] for r in rows])
    read = np.array([r['read_ms'] for r in rows]) / 1000; imu_age = np.array([r['imu_age'] for r in rows])
    rx_lag = t - pi_t
    if rx_lag_cap_s is not None:
        rx_lag = np.minimum(rx_lag, rx_lag_cap_s); t = pi_t + rx_lag
    s_j = pi_t - read / 2; s_i = pi_t - imu_age
    back = np.random.default_rng(0).permutation(rx_lag)
    arrive = t + COMPUTE_S + back
    W = pi_t - read; D = W - WRITE_S
    order = np.argsort(D)
    applied_at = np.full(len(rows), np.nan)
    k = 0
    Ds, Ws = D[order], W[order]
    # for each command, first drain at or after its arrival
    idx = np.searchsorted(Ds, arrive, side='left')
    best = {}
    for i, j in enumerate(idx):
        if j < len(Ds) and (j not in best or i > best[j]):
            best[j] = i
    for j, i in best.items():
        applied_at[i] = Ws[j]
    applied = ~np.isnan(applied_at)
    applied_age = applied_at - s_j
    return dict(t0=float(pi_t[0]), s_j=s_j, s_i=s_i, r=t, applied_at=applied_at, applied=applied,
                applied_age=applied_age, rx_lag=rx_lag, read=read, imu_age=imu_age, pi_t=pi_t,
                n=len(rows))


def goal_age_series(tl, start, duration, dt=0.02):
    """Age of the goal in force at each 20 ms tick, joint and IMU, plus walk_brain's predicted age
    (median of the last 50 applied ages reported back by the Pi up to that time)."""
    ia = np.where(tl['applied'])[0]
    at = tl['applied_at'][ia]
    o = np.argsort(at); ia, at = ia[o], at[o]
    out = []
    for k in range(int(round(duration / dt))):
        T = start + k * dt
        j = np.searchsorted(at, T, side='right') - 1
        i = ia[j]
        past = tl['applied_age'][ia[max(0, j - 49):j + 1]]
        out.append(dict(joint_age=float(T - tl['s_j'][i]), imu_age=float(T - tl['s_i'][i]),
                        predicted_joint_age=float(np.median(past)),
                        predicted_imu_age=float(np.median(past) + tl['imu_age'][i])))
    return out


def stats(x):
    x = np.asarray(x, float)
    return {k: round(float(v) * 1000, 2) for k, v in
            zip(['p5_ms', 'p50_ms', 'p95_ms', 'p99_ms', 'max_ms'], np.percentile(x, [5, 50, 95, 99, 100]))}


if __name__ == '__main__':
    tl = build()
    span = tl['pi_t'][-1] - tl['pi_t'][0]
    rep = dict(rows=tl['n'], span_s=round(float(span), 2), method=__doc__,
               mac_receive_interval=stats(np.diff(tl['r'])), pi_send_interval=stats(np.diff(tl['pi_t'])),
               joint_read=stats(tl['read']), imu_age_at_send=stats(tl['imu_age']), rx_lag=stats(tl['rx_lag']),
               fraction_commands_applied=round(float(tl['applied'].mean()), 3),
               applied_joint_age=stats(tl['applied_age'][tl['applied']]))
    series = goal_age_series(tl, tl['pi_t'][0] + 1.0, span - 2.0)
    rep['goal_in_force_joint_age_20ms_ticks'] = stats([s['joint_age'] for s in series])
    rep['goal_in_force_imu_age_20ms_ticks'] = stats([s['imu_age'] for s in series])
    rep['walk_brain_predicted_joint_age'] = stats([s['predicted_joint_age'] for s in series])
    rep['fraction_ticks_walk_brain_would_hold_MAX_AGE_40ms'] = round(float(np.mean(
        [max(s['predicted_joint_age'], s['predicted_imu_age']) > 0.040 for s in series])), 3)
    (HERE / 'link-timeline-summary.json').write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps({k: v for k, v in rep.items() if k != 'method'}, indent=1))
