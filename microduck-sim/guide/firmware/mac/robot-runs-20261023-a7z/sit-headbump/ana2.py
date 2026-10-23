import json, math
N=["r_ank","r_knee","r_hipP","r_hipR","r_hipY","l_ank","l_knee","l_hipP","l_hipR","l_hipY","headP","neckP","headY","headR"]
O=["l_hipY","l_hipR","l_hipP","l_knee","l_ank","neckP","headP","headY","headR","r_hipY","r_hipR","r_hipP","r_knee","r_ank"]
rows=[json.loads(l) for l in open('sit-region.jsonl') if l.startswith('{')]
eps=[];cur=None
for i,r in enumerate(rows):
    if r['mode']=='sit':
        if cur is None: cur=[i,i]
        cur[1]=i
    elif cur: eps.append(cur);cur=None
def P(r): g=r['gb']; return math.degrees(math.atan2(g[0],-g[2]))
def q(r,n): return r['q'][N.index(n)]
def a(r,n): return r['action'][O.index(n)] if r['action'] else float('nan')
show=["l_knee","r_knee","l_hipP","r_hipP","l_ank","r_ank","neckP","headP"]
for k,(s,b) in enumerate(eps):
    rs=next(i for i in range(s,b+1) if rows[i]['cmd'].get('mode')!='sit')
    t0=rows[rs]['t']
    print(f"\nEP{k} sit start {rows[s]['t']-t0:+.2f}s rel. rise")
    for i in list(range(rs-60, rs, 20))+list(range(rs, min(b+30,len(rows)), 4)):
        r=rows[i]
        print(f" {r['t']-t0:+5.2f} {r['mode'][:4]} pitch {P(r):+5.1f} gyY {r['gyro_body'][1]:+5.2f} | "+" ".join(f"{n} {q(r,n):+.2f}/{a(r,n):+.2f}" for n in show)+f" | ma {r.get('legs_ma')}")
