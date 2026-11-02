"""Timeline of the 2026-11-01 T2 pick and the fall after it, from the brain log slice."""
import json, math, sys
rows=[json.loads(l) for l in open(sys.argv[1]) if l.startswith('{')]
t0=1793584883.6
print('keys', sorted(rows[-1].keys()))
last=None
for r in rows:
    t=r['t']-t0
    if t<-1: continue
    if int(t*5)==last and r['mode']==(prev or {}).get('mode'): prev=r; continue
    last=int(t*5); prev=r
    g=r['gb']; tilt=math.degrees(math.atan2(math.hypot(g[0],g[1]),-g[2]))
    a=max(abs(x) for x in r['action']) if r.get('action') else 0
    gy=r.get('gyro_body') or [0,0,0]
    print(f"{t:6.2f} {r['mode']:8s} tilt {tilt:5.1f} g {g[0]:+.2f} {g[1]:+.2f} gyro {math.hypot(*gy):5.2f} amax {a:5.2f} kp {str(r.get('kp'))[:8]:8s} sp {str(r.get('sp_phase'))[:5]:5s} jaw {str(r.get('jaw_deg',r.get('jaw_open')))[:5]} hold {r.get('jaw_holding')} cur {str(r.get('jaw_ma',''))[:6]} miss {len(r.get('missing') or [])} late {r.get('late')} fresh {r.get('fresh')} age {r.get('imu_age',0):.3f} imu_ok {r.get('imu_valid')}")
