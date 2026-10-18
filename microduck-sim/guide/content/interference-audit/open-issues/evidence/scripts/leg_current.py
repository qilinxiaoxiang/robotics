"""Per-fuse-branch current proxy from the final 33 Phase 1 walking traces (torque / kt, BAM xl330 m6 kt)."""
import json, glob, numpy as np
KT = 0.36601349688984386  # bam.model.load_model('xl330','m6').kt
SIM = '/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/phase1/simulation/'
files = sorted(glob.glob(SIM + 'phase1-candidate-old*-*.json'))
files = [f for f in files if not f.endswith('.config.json')]
G = {'leftLeg': list(range(0, 5)), 'head4': list(range(5, 9)), 'rightLeg': list(range(9, 14))}
PAIRS = {'ID1+2': None}
out = {'files': len(files), 'kt': KT, 'cases': []}
agg = {g: {'mean': [], 'rms': [], 'peak20ms': [], 'max100ms': [], 'max1s': []} for g in G}
tot = {'mean': [], 'peak20ms': [], 'max1s': []}
def roll(x, n):
    c = np.convolve(x, np.ones(n) / n, mode='valid'); return float(c.max())
for f in files:
    d = json.load(open(f)); rows = d['rows']
    t = np.array([r['time'] for r in rows]); T = np.abs(np.array([r['torques_nm'] for r in rows])) / KT
    w = (t >= 3) & (t <= 25)
    rec = {'name': f.split('/')[-1], 'peakProxyRecorded': d.get('peak_summed_motor_current_proxy_a')}
    for g, idx in G.items():
        x = T[w][:, idx].sum(1)
        s = dict(mean=float(x.mean()), rms=float(np.sqrt((x ** 2).mean())), peak20ms=float(x.max()), max100ms=roll(x, 5), max1s=roll(x, 50))
        rec[g] = {k: round(v, 3) for k, v in s.items()}
        for k in s: agg[g][k].append(s[k])
    xs = T[w].sum(1); tot['mean'].append(float(xs.mean())); tot['peak20ms'].append(float(xs.max())); tot['max1s'].append(roll(xs, 50))
    out['cases'].append(rec)
out['summary'] = {g: {k: [round(min(v), 3), round(max(v), 3)] for k, v in a.items()} for g, a in agg.items()}
out['summary']['all14'] = {k: [round(min(v), 3), round(max(v), 3)] for k, v in tot.items()}
json.dump(out, open('leg-current.json', 'w'), indent=1)
print(json.dumps(out['summary'], indent=1))
