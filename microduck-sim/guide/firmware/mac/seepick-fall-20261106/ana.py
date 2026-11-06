import json,math,sys
rows=[json.loads(l) for l in open("log_tail.jsonl") if l.startswith("{")]
rows=[r for r in rows if 't' in r]
T0=1793999030.0
names=None
for r in rows:
    t=r['t']-T0
    if -1.5<t<3.4:
        g=r.get('gb') or [0,0,0]
        a=r.get('action') or []
        am=max(range(len(a)),key=lambda i:abs(a[i])) if a else -1
        c=r.get('cmd') or {}
        print(f"{t:6.2f} {r.get('mode'):6} pol {str(r.get('policy'))[:6]} cmd vx{c.get('vx')} vt{c.get('vtheta')} head{c.get('head')} g[{g[0]:+.2f} {g[1]:+.2f} {g[2]:+.2f}] gyro {[round(x,1) for x in (r.get('gyro_body') or [])]} amax {a[am] if a else 0:+.2f}@{am} cur {sum(r.get('cur_ma') or [0]):.0f} late {r.get('late')}")
