import json,sys,datetime,math
import numpy as np
sys.path.insert(0,'.')
import walk_brain as wb
rows=[json.loads(l) for l in open(sys.argv[1])]
tod=lambda t: datetime.datetime.fromtimestamp(t).strftime('%H:%M:%S')
ys=np.degrees(np.unwrap([wb.yaw_of(wb.body_quat(r['quat'])) for r in rows]))
seg=[];prev=None
for i,r in enumerate(rows):
    c=r.get('cmd') or {}
    k=(r.get('mode'),c.get('mode'),c.get('vx'),c.get('vtheta'),json.dumps(c.get('head'),sort_keys=True))
    if k!=prev: seg.append([k,i]); prev=k
seg.append([None,len(rows)])
for (k,a),(_,b) in zip(seg,seg[1:]):
    rs=rows[a:b]; dt=rs[-1]['t']-rs[0]['t']
    if dt<0.8: continue
    hc=[r.get('head_cmd') for r in rs if r.get('head_cmd')]
    tu=[r.get('turn') for r in rs if r.get('turn') is not None]
    print(tod(rs[0]['t']),f"{dt:5.1f}s mode {k[0]} cmd {k[1]} vx {k[2]} vth {k[3]} head {k[4]} | yaw {ys[b-1]-ys[a]:+5.0f} deg ({(ys[b-1]-ys[a])/max(dt,1e-3):+5.1f}/s) turn {np.mean(tu) if tu else 0:+.2f} headcmd {np.round(np.mean(hc,0),2).tolist() if hc else None}")
