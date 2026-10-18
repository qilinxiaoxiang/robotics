"""A/B: raw policy targets vs targets clipped to MJCF joint range, all 33 Phase1 candidate cases, same simulator build."""
import json, copy, subprocess, sys, concurrent.futures, numpy as np
from pathlib import Path
HERE=Path(__file__).resolve().parent; OUT=HERE/'out'; OUT.mkdir(exist_ok=True)
SIM=Path('/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/phase1/simulation')
PY='/Users/xiangzheng/code/robotics/microduck-sim/microduck_rl/.venv/bin/python'
def grade(r,config):
    ok=(not r['fell'] and not r['warnings'] and r['nonfoot_ground_contact_samples']==0 and r['mean_forward_velocity_m_s'] is not None
        and r['mean_forward_velocity_m_s']>=.03 and r['max_tilt_deg']<=30 and r['duration_completed_s']>=config['duration'])
    h=r.get('max_abs_heading_deviation_deg'); ok&= h is not None and h<=30
    tail=[x for x in r['rows'] if x['time']>=27]; xy=np.array([[x['x'],x['y']] for x in tail])
    exc=float(np.linalg.norm(xy-xy[0],axis=1).max()) if len(tail)>1 else None
    return dict(gait=bool(ok), stop=bool(exc is not None and exc<=.02), speed=r['mean_forward_velocity_m_s'], tilt=r['max_tilt_deg'], heading=h, fell=r['fell'], exc_mm=None if exc is None else exc*1000,
                walk_current=float(np.mean([x['motor_current_sum_proxy_a'] for x in r['rows'] if 3<=x['time']<=25])))
cases=['baseline','voltage475','voltage400','voltage525','floor06','sensor40','action40','push','joint-noise','extra-wire20','extra-wire40']
jobs=[]
for m in (0,60,120):
    for c in cases:
        cfg=json.loads((SIM/f'phase1-candidate-old{m}-{c}.config.json').read_text())
        for arm in sys.argv[1:]:
            k=copy.deepcopy(cfg); k['name']=f"{arm}-old{m}-{c}"
            if arm=='clip': k['clip_targets_to_range']=True
            jobs.append(k)
def run(k):
    cp=OUT/(k['name']+'.config.json'); out=OUT/(k['name']+'.json'); cp.write_text(json.dumps(k))
    p=subprocess.run([PY,'-I',str(HERE/'eval_clamp.py'),str(cp),'--output',str(out)],capture_output=True,text=True,env={**__import__('os').environ,'PYTHONDONTWRITEBYTECODE':'1'})
    if p.returncode: return dict(name=k['name'],error=p.stderr[-500:])
    r=json.loads(out.read_text()); g=grade(r,k); g['name']=k['name']; out.unlink(); return g
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: res=list(pool.map(run,jobs))
json.dump(res,open(OUT/('ab-'+'-'.join(sys.argv[1:])+'.json'),'w'),indent=1)
for arm in sys.argv[1:]:
    rr=[r for r in res if r['name'].startswith(arm+'-')]
    err=[r for r in rr if 'error' in r]
    ok=[r for r in rr if 'error' not in r]
    print(arm,'n',len(rr),'errors',len(err),'gait pass',sum(r['gait'] for r in ok),'gait+stop pass',sum(r['gait'] and r['stop'] for r in ok),'falls',sum(bool(r['fell']) for r in ok))
    if ok: print('  speed %.3f..%.3f tilt %.1f..%.1f heading %.1f..%.1f stop exc mm max %s current %.2f..%.2f'%(min(r['speed'] or 0 for r in ok),max(r['speed'] or 0 for r in ok),min(r['tilt'] for r in ok),max(r['tilt'] for r in ok),min(r['heading'] or 0 for r in ok),max(r['heading'] or 0 for r in ok),max((r['exc_mm'] or 0) for r in ok),min(r['walk_current'] for r in ok),max(r['walk_current'] for r in ok)))
    for r in ok:
        if not (r['gait'] and r['stop']): print('   FAIL',r)
    for r in err[:3]: print('   ERR',r)
