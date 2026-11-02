"""All of 2026-11-01: creeps measured on the robot, where the T2 sim holds by offset, in-place spins."""
import glob, json, math, re, statistics as st, collections
R = 't2-chain-20261101/robot-20261101/'; S = 't2-chain-20261101/results/'

print('== creeps: dx asked -> what the next aim saw')
ev = []
for f in sorted(glob.glob(R + 't2run*.out')):
    prev = None
    for l in open(f):
        m = re.search(r'align -> burst: dx ([+-][\d.]+) cm', l)
        if m: prev = float(m[1]); continue
        m = re.search(r'burst -> aim: creep done: (.*)', l)
        if m and prev is not None:
            x = re.search(r'at x ([\d.]+)', m[1])
            ev.append((f[-10:-4], prev, float(x[1]) if x else None)); prev = None
for e in ev: print(' ', e[0], 'asked %+.1f cm' % e[1], '->', 'x %.3f, dx now %+.1f' % (e[2], (e[2] - .087) * 100) if e[2] else 'under the picture')
print(' ', sum(e[2] is None for e in ev), 'of', len(ev), 'lost the ball under the picture')

print('== sim T2 spx-b_1800 held by start offset (cm)')
b = collections.defaultdict(lambda: [0, 0, 0])
for n in ('matrix', 'plugged', 'plugged_trainmu', 'control', 'battery'):
    for f in glob.glob(S + n + '.jsonl'):
        for l in open(f):
            r = json.loads(l)
            if r.get('c') != 'spx-b_1800' or r.get('dx') is None: continue
            k = (round(r['dx'] * 100), round(r['dy'] * 100)); b[k][0] += 1
            b[k][1] += bool(r.get('train') or r.get('end')); b[k][2] += bool(r.get('fell'))
for k in sorted(b): print('  dx %+3d dy %+3d n %3d held %3d fell %d' % (*k, *b[k]))

print('== in-place spins')
rows = [json.loads(l) for l in open(R + 'spins_compact.jsonl')]
i, out = 0, []
while i < len(rows):
    r = rows[i]
    if not (r['vx'] == 0 and abs(r['vth'] or 0) > 0.05 and r['policy'] == 'walk'): i += 1; continue
    j = i
    while j + 1 < len(rows) and rows[j + 1]['vth'] and rows[j + 1]['t'] - rows[j]['t'] < .2: j += 1
    s = rows[i:j + 1]; dur = s[-1]['t'] - s[0]['t']
    if dur >= 1:
        ang = 0.
        for a, b2 in zip(s, s[1:]):
            n = math.sqrt(sum(x * x for x in a['gb'])) or 1
            ang += sum(g * x for g, x in zip(a['gyro'], a['gb'])) / n * (b2['t'] - a['t'])
        out.append(dict(t=s[0]['t'], d=1 if s[0]['vth'] > 0 else -1, dur=dur, deg=math.degrees(ang), turn=s[len(s) // 2].get('turn'),
                        tilt=max(math.degrees(math.acos(max(-1, min(1, -x['gb'][2] / (math.sqrt(sum(y * y for y in x['gb'])) or 1))))) for x in s)))
    i = j + 1
for d, name in ((1, 'cmd +'), (-1, 'cmd -')):
    o = [x for x in out if x['d'] == d]
    if o:
        print(' ', name, 'n', len(o), 'median dur %.1f s, net %.0f deg, rate %.0f deg/s, |rate| range %.0f..%.0f, max tilt %.0f' % (st.median(x['dur'] for x in o), st.median(x['deg'] for x in o),
              st.median(x['deg'] / x['dur'] for x in o), min(abs(x['deg'] / x['dur']) for x in o), max(abs(x['deg'] / x['dur']) for x in o), max(x['tilt'] for x in o)))
for x in out: print('   %.1f d%+d %.1fs net %+.0f tilt %.0f turn %s' % (x['t'] % 100000, x['d'], x['dur'], x['deg'], x['tilt'], x['turn']))
