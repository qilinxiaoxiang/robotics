"""1018d: what the 'bursts from +26 s (possibly a touch)' look like in gyro, gravity and head error vs goal."""
import gzip, json, math, statistics as st, sys
LOG = '/Users/xiangzheng/code/robotics/microduck-sim/guide/firmware/mac/robot-runs-20261018/duck_wired_log_1018d.jsonl.gz'
T0 = 1792359594.268300   # walk_t0_1018f (second walk)
ORDER = ['left_hip_yaw','left_hip_roll','left_hip_pitch','left_knee','left_ankle','neck_pitch','head_pitch','head_yaw','head_roll',
         'right_hip_yaw','right_hip_roll','right_hip_pitch','right_knee','right_ankle']
DEF = {'right_hip_yaw':0.0,'right_hip_roll':0.0873,'right_hip_pitch':0.4579,'right_knee':0.0049,'right_ankle':-0.4530,
       'left_hip_yaw':0.0,'left_hip_roll':-0.0873,'left_hip_pitch':-0.4579,'left_knee':-0.0049,'left_ankle':0.4530,
       'neck_pitch':0.3491,'head_pitch':0.3491,'head_yaw':0.0,'head_roll':0.0}
rows = [json.loads(l) for l in gzip.open(LOG, 'rt')]
rows = [r for r in rows if 0 <= r['t'] - T0 <= 41]
print('rows in window', len(rows), 'keys acc?', 'acc' in rows[0])
# per-second bins: gyro norm std, gb x/y mean, head joint error (q - (default+action)) mean abs, action max on head
prev_goal = None
bins = {}
for r in rows:
    s = int(r['t'] - T0)
    b = bins.setdefault(s, dict(g=[], gbx=[], gby=[], herr={n: [] for n in ORDER[5:9]}, amax=[], hact={n: [] for n in ORDER[5:9]}, policy=set(), mode=set()))
    g = r['gyro_body']; b['g'].append(math.sqrt(sum(x*x for x in g)))
    b['gbx'].append(r['gb'][0]); b['gby'].append(r['gb'][1])
    b['mode'].add(r['mode']); b['policy'].add(r.get('policy'))
    if r.get('action') is not None:
        a = r['action']; b['amax'].append(max(abs(x) for x in a))
        for k, n in enumerate(ORDER):
            if n in b['herr']:
                b['hact'][n].append(a[k])
        if prev_goal is not None:  # error of this tick's position against the goal sent last tick
            for k, n in enumerate(ORDER):
                if n in b['herr']:
                    b['herr'][n].append(r['q'][k] - prev_goal[k])
        prev_goal = [DEF[n] + a[k] for k, n in enumerate(ORDER)]
for s in sorted(bins):
    b = bins[s]
    he = {n: (round(st.mean(abs(x) for x in v), 3) if v else None) for n, v in b['herr'].items()}
    ha = {n: (round(max(abs(x) for x in v), 2) if v else None) for n, v in b['hact'].items()}
    print(f"+{s:2d}s mode={'/'.join(sorted(b['mode']))} pol={'/'.join(str(p) for p in b['policy'])} gyro|.|mean={st.mean(b['g']):.3f} max={max(b['g']):.2f} "
          f"gbx={st.mean(b['gbx']):+.3f} gby={st.mean(b['gby']):+.3f} amax={max(b['amax']) if b['amax'] else None} "
          f"herr(neck_p,head_p,yaw,roll)={[he[n] for n in ORDER[5:9]]} hact_max={[ha[n] for n in ORDER[5:9]]}")
# the ticks with the largest gyro in +20..+34 s
cand = sorted([r for r in rows if 20 <= r['t'] - T0 <= 34], key=lambda r: -math.sqrt(sum(x*x for x in r['gyro_body'])))[:8]
print('largest gyro ticks in +20..+34:')
for r in cand:
    print(f"  +{r['t']-T0:6.2f}s gyro={r['gyro_body']} gb={r['gb']} q_head={[r['q'][k] for k in range(5,9)]} act_head={[round(r['action'][k],3) if r.get('action') else None for k in range(5,9)]}")
