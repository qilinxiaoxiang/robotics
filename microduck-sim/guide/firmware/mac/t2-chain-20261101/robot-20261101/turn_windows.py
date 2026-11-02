"""Integrated yaw and head pose through every commanded in-place spin in a brain log slice."""
import json, math, sys
rows = []
for l in open(sys.argv[1]):
    if l.startswith('{'):
        try: rows.append(json.loads(l))
        except ValueError: pass
print(len(rows), 'rows', list(rows[0].keys())[:30])
print('cmd', rows[-1].get('cmd'))
segs, cur = [], None
for r in rows:
    c = r.get('cmd') or {}
    spin = c.get('vx', 0) == 0 and abs(c.get('vtheta') or 0) > 0.05 and r.get('policy') == 'walk'
    if spin and cur is None: cur = [r]
    elif spin: cur.append(r)
    elif cur: segs.append(cur); cur = None
for s in segs:
    yaw = 0.0
    hp = []
    for a, b in zip(s, s[1:]):
        yaw += math.degrees((b.get('gyro_body') or [0,0,0])[2]) * (b['t'] - a['t'])
        hp.append(b['q'][10])
    T = s[-1]['t'] - s[0]['t']
    c = s[0]['cmd']
    if T < 0.3: continue
    print(f"t {s[0]['t']:.1f} dur {T:.2f} vth {c.get('vtheta'):+.2f} head_cmd {c.get('head_pitch')} yaw {yaw:+.1f} deg rate {yaw/T:+.1f} deg/s head_pitch max {max(hp):.2f}")
