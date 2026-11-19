import json, math, sys
import numpy as np
rows=[json.loads(l) for l in open(sys.argv[1]).read().splitlines()[1:] if l.startswith("{")]
i0=next(i for i,r in enumerate(rows) if r.get("mode")=="walk")
i1=max(i for i,r in enumerate(rows) if r.get("mode")=="walk")
print("pre mode", rows[i0-1].get("mode"), "walk ticks", i1-i0+1, "dur", rows[i1]["t"]-rows[i0]["t"])
pre=rows[i0-60:i0]
print("pre-walk gb mean", np.mean([r["gb"] for r in pre],0).round(3))
t0=rows[i0]["t"]
for r in rows[i0:i1+1:5]:
    a=np.array(r.get("action",[0]*14)); gb=r["gb"]
    tilt=math.degrees(math.acos(max(-1,min(1,-gb[2]))))
    print(f"{r['t']-t0:5.2f} pol {r.get('policy')} cmd {r.get('cmd')} fr {int(bool(r.get('fresh',1)))} miss {len(r.get('missing',[]))} loop {r['loop_ms']:5.1f} tilt {tilt:5.1f} gbx {gb[0]:+.2f} gby {gb[1]:+.2f} |a|max {abs(a).max():.2f} a_legs {np.round(a[[2,3,4,11,12,13]],2).tolist()} legs_ma {r.get('legs_ma')} v {r.get('servo_v')}")
w=rows[i0:i1+1]
dt=np.diff([r['t'] for r in w])
print("fresh frac", np.mean([bool(r.get('fresh',1)) for r in w]), "loop med", np.median([r['loop_ms'] for r in w]), "max", max(r['loop_ms'] for r in w), "dt med", np.median(dt), "dt>30ms", int((dt>0.03).sum()), "dt max", dt.max())
print("policies", {p:sum(1 for r in w if r.get('policy')==p) for p in set(r.get('policy') for r in w)})
print("imu_age med", np.median([r['imu_age'] for r in w]), "joint_age med", np.median([r['joint_age'] for r in w]), "read_ms med", np.median([r['read_ms'] for r in w]))
