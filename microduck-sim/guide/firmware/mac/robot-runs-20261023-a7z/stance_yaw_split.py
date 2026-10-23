import json, math, sys
sys.path.insert(0,'.')
sys.path.insert(0, '../veer-20261022')
from veer_check import yaw_rate, R_LEG, L_LEG
rows=[json.loads(l) for l in open(sys.argv[1]) if l.strip()]
t0=rows[0]['t']
# carried? 74-85 s into walk 2
w=[r for r in rows if r.get('mode')=='walk']
seg2t0=None
prev=None; phases=[]; cur=None
for r in rows:
    if r.get('mode')!='walk' or not r.get('cur_ma') or (r.get('cmd') or {}).get('vx',0)<=0: 
        if cur: phases.append(cur); cur=None
        prev=None; continue
    cu=r['cur_ma']; rs=sum(abs(cu[i]) for i in R_LEG); ls=sum(abs(cu[i]) for i in L_LEG)
    sd='R' if rs>1.5*ls else 'L' if ls>1.5*rs else 'B'
    if cur is None or cur['side']!=sd:
        if cur: phases.append(cur)
        cur={'side':sd,'rows':[]}
    cur['rows'].append(r)
if cur: phases.append(cur)
import collections
agg=collections.defaultdict(lambda:[0,0,0,0.0])
for p in phases:
    rs=p['rows']
    if len(rs)<4 or p['side']=='B': continue
    yaw=0
    for a,c in zip(rs,rs[1:]):
        dt=c['t']-a['t']; wr=yaw_rate(a)
        if wr is not None and dt<0.1: yaw+=wr*dt
    i=4 if p['side']=='R' else 9
    dh=rs[-1]['q'][i]-rs[0]['q'][i]
    g=agg[p['side']]; g[0]+=1; g[1]+=math.degrees(yaw); g[2]+=math.degrees(dh); g[3]+=rs[-1]['t']-rs[0]['t']
for s,g in agg.items():
    print(f"{s} stance: {g[0]} phases, {g[3]:.1f} s total, trunk yaw sum {g[1]:+.0f} deg, stance hip-yaw joint change sum {g[2]:+.0f} deg, mean phase {g[3]/g[0]*1000:.0f} ms")
# carried check walk2 74-85s
s2=[r for r in rows if r.get('mode')=='walk' and r['t']-t0>69+70 and r['t']-t0<69+90]
for r in s2[::50]:
    print(f"{r['t']-t0:6.1f} gb {[round(x,2) for x in r['gb']]} legs_ma {r.get('legs_ma')} cmd {r.get('cmd')} policy {r.get('policy')}")
print('--- goal vs present on stance hip yaw')
TD=2*math.pi/4096
for side,i in (('L',9),('R',4)):
    # sign: tick -> q
    xs=[(r['pos_tick'][i], r['q'][i]) for r in rows if r.get('pos_tick')]
    s=1 if (xs[-1][1]-xs[0][1])*(xs[-1][0]-xs[0][0])>=0 else -1
    dp=dg=0; n=0; errs=[]
    for p in phases:
        if p['side']!=side or len(p['rows'])<4: continue
        a,b=p['rows'][0],p['rows'][-1]
        if not a.get('goal_tick') or not b.get('goal_tick'): continue
        k=str(i+1)
        dp+=s*(b['pos_tick'][i]-a['pos_tick'][i])*TD; dg+=s*(b['goal_tick'][k]-a['goal_tick'][k])*TD; n+=1
        errs+= [s*(r['pos_tick'][i]-r['goal_tick'][k])*TD for r in p['rows'] if r.get('goal_tick')]
    print(f"{side} hip yaw over {n} stance phases: present moved {math.degrees(dp):+.0f} deg, goal moved {math.degrees(dg):+.0f} deg, mean present-goal {math.degrees(sum(errs)/len(errs)):+.1f} deg")
