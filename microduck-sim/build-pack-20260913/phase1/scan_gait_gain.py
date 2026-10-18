"""Finite 24-case scan after the Phase 1 mass regression exposed falls."""
from pathlib import Path
import concurrent.futures
import copy
import json
from run_mass_regression import base, run, S

jobs=[]
for old in [0,60,120]:
    for delay in [0,2]:
        for kp in [100,150]:
            for speed in [.15,.3]:
                c=copy.deepcopy(base)
                c.update(name=f'phase1-scan-old{old}-delay{delay}-kp{kp}-speed{speed}',
                    remove_old_battery_kg=old/1000,sensor_delay_ticks=delay,kp=kp,command=[speed,0,0])
                jobs.append(c)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(run,jobs))
(S/'gain-scan.json').write_text(json.dumps({'count':len(results),'passed':sum(bool(r.get('walking_gate_pass')) for r in results),'cases':results},indent=2)+'\n')
for kp in [100,150]:
    for speed in [.15,.3]:
        rr=[r for r in results if r.get('config',{}).get('kp')==kp and r.get('config',{}).get('command',[None])[0]==speed]
        print(kp,speed,sum(bool(r.get('walking_gate_pass')) for r in rr),len(rr))
