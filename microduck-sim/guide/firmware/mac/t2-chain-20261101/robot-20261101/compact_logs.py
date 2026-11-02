"""Merge the local brain log slices into spins_compact.jsonl: only the rows from 2 s before to 3 s after each commanded in-place
spin, only the fields the spin and fall analysis read. Raw logs stay on the A7Z (~/duck-logs)."""
import glob, json, pathlib
R = pathlib.Path('t2-chain-20261101/robot-20261101')
rows = {}
for f in sorted(R.glob('brain_*.jsonl')):
    for l in open(f):
        if l.startswith('{'):
            try: r = json.loads(l)
            except ValueError: continue
            if r.get('gb') and r.get('gyro_body') and r.get('q'):
                c = r.get('cmd') or {}
                rows[r['t']] = dict(t=round(r['t'], 3), mode=r.get('mode'), policy=r.get('policy'), vx=c.get('vx'), vth=c.get('vtheta'), turn=r.get('turn'),
                                    gb=[round(x, 3) for x in r['gb']], gyro=[round(x, 3) for x in r['gyro_body']],
                                    hy=[round(r['q'][4], 3), round(r['q'][9], 3)], head=[round(r['q'][10], 3), round(r['q'][11], 3), round(r['q'][12], 3)])
T = sorted(rows)
spin = [t for t in T if rows[t]['vx'] == 0 and abs(rows[t]['vth'] or 0) > 0.05]
keep, i = [], 0
for t in T:
    while i < len(spin) and spin[i] < t - 3: i += 1
    if i < len(spin) and spin[i] - 2 <= t: keep.append(t)
with open(R / 'spins_compact.jsonl', 'w') as f:
    for t in keep: f.write(json.dumps(rows[t], separators=(',', ':')) + '\n')
print(len(T), 'rows,', len(keep), 'kept')
