"""Reproducible uncertainty and disturbance sweeps, on CPU, without robot access."""
from pathlib import Path
import argparse,concurrent.futures,copy,json,subprocess,sys

P=Path(__file__).resolve().parent

def grade(r,config):
    r=copy.deepcopy(r);r.pop('rows',None)
    r['walking_gate_pass']=(not r['fell'] and not r['warnings'] and r['nonfoot_ground_contact_samples']==0
        and r['mean_forward_velocity_m_s'] is not None and r['mean_forward_velocity_m_s']>=.03
        and r['max_tilt_deg']<=30 and r['duration_completed_s']>=config['duration'])
    if config.get('heading_hold'):
        heading=r.get('max_abs_heading_deviation_deg')
        r['walking_gate_pass'] &= heading is not None and heading<=30
    return r

def execute(config):
    name=config['name'];config_path=P/f'{name}.config.json';out=P/f'{name}.json'
    config_path.write_text(json.dumps(config,indent=2))
    proc=subprocess.run([sys.executable,str(P/'evaluate.py'),str(config_path),'--output',str(out)],capture_output=True,text=True)
    (P/f'{name}.log').write_text(proc.stdout+proc.stderr)
    if proc.returncode:return {'name':name,'error':proc.stderr}
    return grade(json.loads(out.read_text()),config)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--heading',action='store_true');args=ap.parse_args()
    base=json.loads((P/'compact-prototype.config.json').read_text());base['duration']=30
    configs=[]
    for old in [0,60,120]:
        for head in [15,30,45]:
            for battery in [37,57,77]:
                c=copy.deepcopy(base);c['name']=f'compact-old{old}-head{head}-battery{battery}'
                c['remove_old_battery_kg']=old/1000;c['mass_parts'][0]['mass_kg']=head/1000
                if battery!=57:c['mass_parts'].append(dict(body='trunk_base',mass_kg=(battery-57)/1000,
                   position_m=[-.0376,0,-.004],dimensions_m=[.022,.034,.063]))
                configs.append(c)
    perturbations={'voltage475':{'voltage':4.75},'voltage525':{'voltage':5.25},
                  'floor06':{'friction':.6},'floor12':{'friction':1.2},
                  'sensor20':{'sensor_delay_ticks':1},'sensor40':{'sensor_delay_ticks':2},
                  'action40':{'action_delay_ticks':2},'push':{'push':[.15,.05]},
                  'joint-noise':{'joint_noise':.03,'seed':9}}
    for old in [0,60,120]:
        for label,update in perturbations.items():
            c=copy.deepcopy(base);c.update(update);c['remove_old_battery_kg']=old/1000
            c['name']=f'compact-perturb-old{old}-{label}';configs.append(c)
    if args.heading:
        for c in configs:c.update(heading_hold=True,name=c['name'].replace('compact-','heading-suite-',1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(execute,configs))
    report={'gate':'30 s completed; no fall; no MuJoCo warning; no non-foot ground contact; mean x velocity >= 0.03 m/s; max trunk tilt <= 30 degrees.',
            'caveat':'Hardware parameters with uncertainty are swept; none of these runs measures real motor current, friction, voltage sag, battery weight, or controller latency.',
            'cases':results}
    if args.heading:report['gate']+=' Heading deviation <= 30 degrees; heading feedback uses the same delayed measurement age as other sensors.'
    (P/('heading-suite-summary.json' if args.heading else 'compact-suite-summary.json')).write_text(json.dumps(report,indent=2))
    print(json.dumps({'count':len(results),'gate_pass':sum(r.get('walking_gate_pass',False) for r in results),
       'failures':[dict(name=r.get('config',{}).get('name'),**{k:r.get(k) for k in ['error','fell','mean_forward_velocity_m_s','max_abs_heading_deviation_deg','max_tilt_deg']}) for r in results if not r.get('walking_gate_pass',False)]},indent=2))
