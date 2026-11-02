"""What the robot was doing in the 3 s before a camera drop: acceleration, gyro, head and neck, jaw, command."""
import json, math, sys
path, T = sys.argv[1], float(sys.argv[2])
rows = []
for l in open(path):
    if l.startswith('{'):
        try:
            r = json.loads(l)
            if T-3 <= r['t'] <= T+0.5: rows.append(r)
        except ValueError: pass
print(len(rows), 'rows', 'keys acc', 'acc' in rows[0])
last = None
for r in rows:
    k = int((r['t']-T)*4)
    if k == last: continue
    last = k
    a = r.get('acc') or [0,0,0]; g = r.get('gyro_body') or [0,0,0]; q = r['q']; c = r.get('cmd') or {}
    print(f"{r['t']-T:+5.2f} acc {math.sqrt(sum(x*x for x in a)):5.1f} gyro {math.degrees(math.sqrt(sum(x*x for x in g))):5.0f} head yaw {q[12]:+.2f} pitch {q[10]:+.2f} neck {q[11]:+.2f} roll {q[13]:+.2f} vth {c.get('vtheta')} vx {c.get('vx')} bat {r.get('battery_dv')} late {r.get('late')}")
