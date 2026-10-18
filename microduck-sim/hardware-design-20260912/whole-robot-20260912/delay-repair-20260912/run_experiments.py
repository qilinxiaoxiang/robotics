"""Bounded CPU experiments against unchanged frozen final-suite configurations."""
from pathlib import Path
import concurrent.futures,copy,json,subprocess,sys,argparse,time
P=Path(__file__).resolve().parent;FROZEN=P.parent/'dynamics'
sys.path.insert(0,str(FROZEN));from run_compact_suite import grade

def run_job(job):
    tag,config=job;out=P/(tag+'.json');cp=P/(tag+'.config.json')
    cp.write_text(json.dumps(config,indent=2)+'\n')
    p=subprocess.run([sys.executable,str(P/'evaluate_delay.py'),str(cp),'--output',str(out)],capture_output=True,text=True)
    (P/(tag+'.log')).write_text(p.stdout+p.stderr)
    if p.returncode:return {'tag':tag,'error':p.stderr,'walking_gate_pass':False}
    raw=json.loads(out.read_text());r=grade(raw,config);r['tag']=tag
    print(json.dumps({k:r.get(k) for k in ['tag','walking_gate_pass','fell','fall_time_s','mean_forward_velocity_m_s','max_tilt_deg','max_abs_heading_deviation_deg']}),flush=True)
    return r

def run(jobs,label):
    started=time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run_job,jobs))
    report={'label':label,'count':len(results),'pass':sum(r.get('walking_gate_pass',False) for r in results),'wall_seconds':time.time()-started,
       'gate_unchanged_from':str(FROZEN/'run_compact_suite.py'),'cases':results}
    (P/(label+'-summary.json')).write_text(json.dumps(report,indent=2)+'\n');return report

def base(old):return json.loads((FROZEN/f'final-perturb-batteryremove{old}-sensor40.config.json').read_text())
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['baseline','scan']);a=ap.parse_args();jobs=[]
    if a.mode=='baseline':
        for old in [0,60,120]:
            c=base(old);c['trace_signals']=True;jobs.append((f'replay-old{old}-sensor40',c))
    else:
        for old in [0,60,120]:
            for frac in [0,.5,1]:
                for kp in [150,200,250]:
                    c=base(old);c.update(kp=kp,delay_compensation='constant_velocity' if frac else 'none',prediction_fraction=frac)
                    jobs.append((f'scan-old{old}-pred{frac}-kp{kp}',c))
    r=run(jobs,a.mode);print(json.dumps({'count':r['count'],'pass':r['pass'],'wall_seconds':r['wall_seconds']}))
