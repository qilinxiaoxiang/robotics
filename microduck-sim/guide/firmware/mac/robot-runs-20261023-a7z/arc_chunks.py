import json, math, sys
sys.path.insert(0, '../veer-20261022')  # run from this folder: python3 arc_chunks.py <log.jsonl>
from veer_check import yaw_rate
rows=[json.loads(l) for l in open(sys.argv[1]) if l.strip()]
t0=rows[0]['t']
def key(r):
    if r.get('mode')!='walk': return None
    c=r.get('cmd',{}); vx=c.get('vx',0); vt=c.get('vtheta',0)
    if vx<=0 and abs(vt)<1e-3: return 'idle'
    return 'L' if vt>1e-3 else 'R' if vt<-1e-3 else 'W'
chunks=[];cur=[];k0=None
for r in rows:
    k=key(r)
    if k!=k0:
        if cur and k0 not in (None,'idle'): chunks.append((k0,cur))
        cur=[];k0=k
    cur.append(r)
if cur and k0 not in (None,'idle'): chunks.append((k0,cur))
for k,c in chunks:
    d=c[-1]['t']-c[0]['t']
    if d<0.8: continue
    yaw=0;n=0;ws=[];tu=[];sat=0
    for a,b in zip(c,c[1:]):
        dt=b['t']-a['t']; w=yaw_rate(a)
        if w is None or dt>0.1: continue
        yaw+=w*dt
        if a['t']-c[0]['t']>=0.5: ws.append(math.degrees(w)); t=a.get('turn') or 0; tu.append(t); sat+=abs(t)>=1.999
    vt=c[0]['cmd'].get('vtheta',0)
    hz=(len(c)-1)/d
    print(f"{k} t {c[0]['t']-t0:6.1f} dur {d:4.1f}s vth {vt:+.2f} ({math.degrees(vt):+.0f} deg/s)  yaw {math.degrees(yaw):+5.0f} deg  rate after 0.5s {sum(ws)/max(len(ws),1):+6.1f} deg/s  turn mean {sum(tu)/max(len(tu),1):+.2f} sat {sat}/{len(tu)}  {hz:.0f} Hz")
