"""Repeat all baseline perturbations, 4V cases and an explicit five-second stop."""
from pathlib import Path
import concurrent.futures
import copy
import json
import subprocess
import sys
import numpy as np
from run_mass_regression import jobs, base, S, grade

P=Path(__file__).resolve().parent
base.update(delay_compensation='none',predict_heading=False)
for c in jobs:
    c.update(delay_compensation='none',predict_heading=False)
configs=[]
for original in jobs:
    c=copy.deepcopy(original)
    c.update(name=c['name'].replace('phase1-','phase1-candidate-'),kp=275,
        policy_blend_s=0,keep_walk_policy_on_stop=True,stop_hold_s=5,heading_hold_on_stop=True)
    configs.append(c)
for old in [0,60,120]:
    c=copy.deepcopy(base)
    c.update(name=f'phase1-candidate-old{old}-voltage400',remove_old_battery_kg=old/1000,
        voltage=4.0,kp=275,policy_blend_s=0,keep_walk_policy_on_stop=True,stop_hold_s=5,heading_hold_on_stop=True)
    configs.append(c)

for old in [0,60,120]:
    c=copy.deepcopy(base)
    c.update(name=f'phase1-candidate-old{old}-voltage525',remove_old_battery_kg=old/1000,
        voltage=5.25,kp=275,policy_blend_s=0,keep_walk_policy_on_stop=True,stop_hold_s=5,heading_hold_on_stop=True)
    configs.append(c)

def run(c):
    cp=S/(c['name']+'.config.json');out=S/(c['name']+'.json')
    cp.write_text(json.dumps(c,indent=2)+'\n')
    proc=subprocess.run([sys.executable,str(P/'evaluate_phase1.py'),str(cp),'--output',str(out)],capture_output=True,text=True)
    (S/(c['name']+'.log')).write_text(proc.stdout+proc.stderr)
    if proc.returncode:
        return {'error':proc.stderr,'walking_gate_pass':False,'config':c}
    raw=json.loads(out.read_text());result=grade(raw,c)
    tail=[r for r in raw['rows'] if r['time']>=27]
    if len(tail)>1:
        xy=np.array([[r['x'],r['y']] for r in tail])
        result['last3s_stop_net_drift_m']=float(np.linalg.norm(xy[-1]-xy[0]))
        result['last3s_stop_max_excursion_m']=float(np.linalg.norm(xy-xy[0],axis=1).max())
        result['stop_settle_pass']=result['last3s_stop_max_excursion_m']<=.02
    else:
        result['stop_settle_pass']=False
    result['phase1_gait_and_stop_pass']=bool(result['walking_gate_pass'] and result['stop_settle_pass'])
    moving=[r['motor_current_sum_proxy_a'] for r in raw['rows'] if 3<=r['time']<=25]
    result['walking_mean_summed_current_proxy_a']=float(np.mean(moving)) if moving else None
    print(c['name'],result['walking_gate_pass'],result['phase1_gait_and_stop_pass'],result['max_tilt_deg'],result.get('last3s_stop_max_excursion_m'),flush=True)
    return result

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(run,configs))
    report={'count':len(results),'gait_passed':sum(bool(r.get('walking_gate_pass')) for r in results),
        'gait_and_stop_passed':sum(bool(r.get('phase1_gait_and_stop_pass')) for r in results),
        'gate':'Original30s gait gate retained. Additional zero velocity command at25s using same walk policy; maximum planar excursion <=20mm over27–30s.',
        'scope':'Mass/COM sensitivity; closed jaw, no object, no flexible tether force or actual DC supply/current measurement.',
        'cases':results}
    (S/'candidate-regression.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'}))
