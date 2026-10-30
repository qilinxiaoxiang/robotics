import json,sys,datetime,math
import numpy as np
sys.path.insert(0,'.')
import walk_brain as wb
tod=lambda t: datetime.datetime.fromtimestamp(t).strftime('%H:%M:%S')
pts=[]
for fn in sys.argv[1:]:
    rows=[json.loads(l) for l in open(fn)]
    ys=np.degrees(np.unwrap([wb.yaw_of(wb.body_quat(r['quat'])) for r in rows]))
    for s in range(0,len(rows)-50,50):
        w=rows[s:s+50]; c=w[0].get('cmd') or {}
        if c.get('mode')!='walk' or not c.get('vtheta') or c.get('vx') or any((x.get('cmd') or {}).get('vtheta')!=c['vtheta'] for x in w): continue
        a=np.array([x['action'] for x in w if x.get('action') and len(x['action'])==14])
        if len(a)<40: continue
        jumps=(np.abs(np.diff(a,axis=0))>0.5).any(axis=1).sum()/((w[-1]['t']-w[0]['t']))
        tilt=max(math.degrees(math.acos(min(1,-x['gb'][2]))) for x in w)
        rate=(ys[s+49]-ys[s])/(w[-1]['t']-w[0]['t'])*np.sign(c['vtheta'])
        hc=w[-1].get('head_cmd'); hp=hc[1] if hc else 0.0
        pts.append((rate,jumps,tilt,hp)); print(tod(w[0]['t']),f"want-dir rate {rate:+6.1f}  jumps {jumps:5.1f}/s  max tilt {tilt:4.1f}  head_pitch delta {hp:+.2f}")
p=np.array(pts)
for name,m in [('head default',np.abs(p[:,3])<0.05),('head commanded',np.abs(p[:,3])>=0.05)]:
    if m.sum(): print(name, 'n',m.sum(),'rate',round(p[m,0].mean(),1),'jumps',round(p[m,1].mean(),1),'tilt',round(p[m,2].mean(),1))
st=p[:,0]<5; print('stalled secs (rate<5): jumps',round(p[st,1].mean(),1),'tilt',round(p[st,2].mean(),1),'| turning secs: jumps',round(p[~st,1].mean(),1),'tilt',round(p[~st,2].mean(),1))
print('corr(rate, jumps)',round(np.corrcoef(p[:,0],p[:,1])[0,1],2))
