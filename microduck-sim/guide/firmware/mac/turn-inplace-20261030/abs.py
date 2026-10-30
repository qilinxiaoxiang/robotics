import json,sys,math,datetime
import numpy as np
sys.path.insert(0,'.')
import walk_brain as wb
rows=[json.loads(l) for l in open(sys.argv[1])]
tod=lambda t: datetime.datetime.fromtimestamp(t).strftime('%H:%M:%S')
ys=np.degrees(np.unwrap([wb.yaw_of(wb.body_quat(r['quat'])) for r in rows]))
ys-=ys[0]
for s in range(0,len(rows)-50,50):
    w=rows[s:s+50]; c=w[0].get('cmd') or {}
    if c.get('mode')!='walk' or not c.get('vtheta'): continue
    dt=w[-1]['t']-w[0]['t']
    print(tod(w[0]['t']), f"vth {c['vtheta']:+.2f} vx {c.get('vx')}  heading {ys[s]:+6.0f} deg  rate {(ys[s+49]-ys[s])/dt:+6.1f}")
