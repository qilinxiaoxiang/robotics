import json, sys
import numpy as np
rows=[json.loads(l) for l in open(sys.argv[1]).read().splitlines()[1:] if l.startswith("{")]
for pol_mode in ("walk",):
    w=[r for r in rows if r.get("mode")==pol_mode and r.get("action") is not None]
    a=np.array([r["action"] for r in w]); d=np.abs(np.diff(a,axis=0)).max(1)
    dur=w[-1]["t"]-w[0]["t"]
    print(pol_mode, "ticks", len(w), "dur", round(dur,2), "jumps>0.5", int((d>0.5).sum()), "per 10 s", round((d>0.5).sum()/dur*10,1), "median step", round(float(np.median(d)),3), "rms action", round(float(np.sqrt((a**2).mean())),3))
    gy=np.array([r["gyro_body"] for r in w]); print("gyro rms", np.sqrt((gy**2).mean(0)).round(2))
    ma=[r.get("legs_ma") for r in w if r.get("legs_ma") is not None]; print("legs_ma median", np.median(ma), "max", max(ma))
    print("skipped", sum(1 for r in rows if r.get("mode")=="walk" and r.get("action") is None))
