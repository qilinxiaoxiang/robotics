"""Run existing gait evaluator with Phase 1 mass and unchanged walking gate."""
from pathlib import Path
import concurrent.futures
import copy
import json
import subprocess
import sys
import time

P = Path(__file__).resolve().parent
S = P / 'simulation'
OLD = P.parents[1] / 'hardware-design-20260912/whole-robot-20260912'
sys.path.insert(0, str(OLD / 'dynamics'))
from run_compact_suite import grade

base = json.loads((OLD / 'delay-repair-20260912/repair-final-batteryremove60-headremove15.config.json').read_text())
base.update(mass_manifest=str(S / 'mass-manifest.json'), geometry_manifest=str(S / 'geometry-manifest.json'))
variants = {'baseline':{}, 'voltage475':{'voltage':4.75}, 'floor06':{'friction':.6},
    'sensor40':{'sensor_delay_ticks':2}, 'action40':{'action_delay_ticks':2},
    'push':{'push':[.15,.05]}, 'joint-noise':{'joint_noise':.03,'seed':9},
    'extra-wire20':{'extra_trunk_kg':.02}, 'extra-wire40':{'extra_trunk_kg':.04}}
jobs = []
for old in [0,60,120]:
    for name, changes in variants.items():
        c = copy.deepcopy(base)
        changes = copy.deepcopy(changes)
        wire = changes.pop('extra_trunk_kg',0)
        c.update(changes, remove_old_battery_kg=old/1000, name=f'phase1-old{old}-{name}')
        if wire:
            c['mass_parts'].append({'id':'additional-harness-uncertainty','body':'trunk_base','mass_kg':wire,'position_m':[-.03,0,-.015],'dimensions_m':[.05,.05,.06]})
        jobs.append(c)

def run(c):
    cp = S / (c['name'] + '.config.json')
    out = cp.with_name(c['name'] + '.json')
    cp.write_text(json.dumps(c,indent=2) + '\n')
    r = subprocess.run([sys.executable,str(OLD / 'delay-repair-20260912/evaluate_delay.py'),str(cp),'--output',str(out)],capture_output=True,text=True)
    cp.with_suffix('.log').write_text(r.stdout+r.stderr)
    if r.returncode:
        result = {'name':c['name'],'walking_gate_pass':False,'error':r.stderr}
    else:
        result = grade(json.loads(out.read_text()), c)
    print(json.dumps({'name':c['name'],'pass':result.get('walking_gate_pass'),'tilt':result.get('max_tilt_deg'),'velocity':result.get('mean_forward_velocity_m_s'),'error':result.get('error')}),flush=True)
    return result

if __name__ == '__main__':
    started = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run,jobs))
    report = {'cases':results,'count':len(results),'passed':sum(bool(x.get('walking_gate_pass')) for x in results),'seconds':time.time()-started,
        'gate':'Unchanged 30 s gait gate: no fall, no MuJoCo warning, no non-foot ground contact, mean x speed >=0.03 m/s, maximum tilt <=30 degrees, heading deviation <=30 degrees in existing scoring window.',
        'scope':'Phase 1 mass/COM sensitivity with original 14-action gait policy. The retained jaw is closed. No object, tether forces, physical current measurement, or pickup acceptance.'}
    (S / 'mass-regression.json').write_text(json.dumps(report,indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k!='cases'}))
