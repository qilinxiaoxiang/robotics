import json,sys,math,datetime
import numpy as np
sys.path.insert(0,'.')
import walk_brain as wb
rows=[json.loads(l) for l in open(sys.argv[1])]
tod=lambda t: datetime.datetime.fromtimestamp(t).strftime('%H:%M:%S')
ys=np.degrees(np.unwrap([wb.yaw_of(wb.body_quat(r['quat'])) for r in rows]))
N=wb.NAMES; ids={n:i for i,n in enumerate(N)}
J=['right_hip_yaw','left_hip_yaw','right_hip_roll','left_hip_roll']
T=0.088  # deg per tick
print(len(rows[0]['goal_tick']), len(rows[0]['pos_tick']))
for s in range(0,len(rows)-50,50):
    w=rows[s:s+50]; c=w[0].get('cmd') or {}
    if c.get('mode')!='walk' or not c.get('vtheta') or c.get('vx'): continue
    g=np.array([[r['goal_tick'][str(k)] for k in range(1,15)] for r in w],float); p=np.array([r['pos_tick'] for r in w],float)
    rate=(ys[s+49]-ys[s])/(w[-1]['t']-w[0]['t'])
    out=[]
    for n in J:
        i=ids[n]
        out.append(f"{n.replace('_hip','')}: goal sd {g[:,i].std()*T:4.1f} pos sd {p[:,i].std()*T:4.1f} err mean {(g[:,i]-p[:,i]).mean()*T:+5.1f}")
    print(tod(w[0]['t']), f"vth {c['vtheta']:+.1f} rate {rate:+6.1f} deg/s |", ' | '.join(out))
