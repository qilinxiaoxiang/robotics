import json, math, sys
sys.path.insert(0, '.')
sys.path.insert(0, '../veer-20261022')
from veer_check import yaw_rate, R_LEG, L_LEG
rows=[json.loads(l) for l in open(sys.argv[1]) if l.strip()]
segs=[];cur=None
for r in rows:
    if r.get('mode')=='walk': (cur:=cur if cur is not None else []).append(r)
    elif cur: segs.append(cur); cur=None
if cur: segs.append(cur)
t00=rows[0]['t']
for k,s in enumerate(segs):
    print(f"\n=== walk {k+1}: t {s[0]['t']-t00:.1f}-{s[-1]['t']-t00:.1f} s, {len(s)} ticks, trim {s[0].get('yaw_trim')} -> {s[-1].get('yaw_trim')}")
    yaw=x=y=0.0; b0=s[0]['t']; acc=[]; sat=0; n=0; st={'R':[0,0],'L':[0,0],'B':[0,0]}
    for a,c in zip(s,s[1:]):
        dt=c['t']-a['t']; w=yaw_rate(a)
        if w is None or dt>0.1: continue
        cmd=a.get('cmd',{}); vx=cmd.get('vx',0)
        yaw+=w*dt; x+=vx*math.cos(yaw)*dt; y+=vx*math.sin(yaw)*dt
        tu=a.get('turn') or 0; n+=1; sat+= abs(tu)>=0.999
        acc.append((a['t']-b0,vx,cmd.get('vtheta',0),tu,math.degrees(w),math.degrees(yaw),x,y))
        cu=a.get('cur_ma')
        if cu and vx>0:
            rs=sum(abs(cu[i]) for i in R_LEG); ls=sum(abs(cu[i]) for i in L_LEG)
            sd='R' if rs>1.5*ls else 'L' if ls>1.5*rs else 'B'
            st[sd][0]+=1; st[sd][1]+=math.degrees(w)
    print(f"  turn saturated at +-1.0 in {sat}/{n} ticks; net yaw {math.degrees(0)+acc[-1][5]:+.0f} deg; dead-reckoned end (cmd speed) x {acc[-1][6]:.2f} y {acc[-1][7]:+.2f} m")
    print("  stance (vx>0): "+", ".join(f"{k} {v[0]} ticks {v[1]/max(v[0],1):+.1f} deg/s" for k,v in st.items()))
    print("   t    vx  vth   turn  yawrate  yaw   x    y")
    nb=0
    for i in range(0,len(acc)):
        if acc[i][0]>=nb:
            j=[q for q in acc if nb<=q[0]<nb+0.5]
            m=lambda idx: sum(q[idx] for q in j)/len(j)
            print(f"  {nb:4.1f} {m(1):.2f} {m(2):+.2f} {m(3):+.2f} {m(4):+7.1f} {acc[i][5]:+5.0f} {acc[i][6]:.2f} {acc[i][7]:+.2f}")
            nb+=0.5
