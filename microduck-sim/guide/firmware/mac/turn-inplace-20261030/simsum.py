import json,sys,glob,os,math
import numpy as np
S=sys.argv[1]
for f in sorted(glob.glob(S+'/sim_*.jsonl')):
    if 'smoke' in f: continue
    rows=[json.loads(l) for l in open(f)]
    summ=json.load(open(f[:-1])) if os.path.exists(f[:-1]) else {}
    t=np.array([r['t'] for r in rows]); gz=np.array([r['gyro_body'][2] for r in rows])
    m=(t>=3)&(t<28)
    per=[]
    for s in range(3,28):
        k=(t>=s)&(t<s+1)
        per.append(math.degrees(gz[k].mean()) if k.any() else float('nan'))
    tu=[r.get('turn') for r in rows if r.get('turn') is not None]
    print(os.path.basename(f)[4:-6].ljust(24), f"fell {summ.get('fell_at')}  yaw {summ.get('yaw_walk_deg')} deg  first4s {np.nanmean(per[:4]):+5.1f}/s  last10s {np.nanmean(per[-10:]):+5.1f}/s  turn mean {summ.get('turn_mean')}  head {summ.get('head')}")
    print('   per s:', ' '.join(f"{p:+.0f}" for p in per))
