"""Final frozen geometry and distributed masses, with the selected heading controller."""
from pathlib import Path
import argparse,concurrent.futures,copy,json
from run_compact_suite import execute,grade
P=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--reuse-recorded',action='store_true',help='Recover a summary-only failure with unchanged frozen simulator inputs; otherwise rerun.')
args=ap.parse_args()
jobs=[]
for old_battery in [0,60,120]:
    for old_head in [0,15,30]:
        c=json.loads((P/f'full-oldbattery{old_battery}-oldelectronics{old_head}.config.json').read_text())
        c.update(name=f'final-batteryremove{old_battery}-headremove{old_head}',heading_gain=2,heading_rate_limit=.8)
        jobs.append(c)
    base=copy.deepcopy(jobs[-2])
    variants={'voltage475':{'voltage':4.75},'voltage525':{'voltage':5.25},
       'floor06':{'friction':.6},'floor12':{'friction':1.2},'sensor20':{'sensor_delay_ticks':1},
       'sensor40':{'sensor_delay_ticks':2},'push':{'push':[.15,.05]},'joint-noise':{'joint_noise':.03,'seed':9},
       'imu1deg':{'sensor_delay_ticks':1,'imu_noise_deg':1,'gyro_noise_rad_s':.02,'seed':42},
       'imu3deg':{'sensor_delay_ticks':1,'imu_noise_deg':3,'gyro_noise_rad_s':.02,'seed':42}}
    for label,change in variants.items():
        c=copy.deepcopy(base);c.update(change);c['name']=f'final-perturb-batteryremove{old_battery}-{label}';jobs.append(c)
    for new_battery_g in [37,77]:
        c=copy.deepcopy(base);c['name']=f'final-batteryremove{old_battery}-batteryweight{new_battery_g}'
        c['mass_parts'].append(dict(id='new-battery-tolerance',body='trunk_base',mass_kg=(new_battery_g-57)/1000,
          position_m=[-.0376,0,-.004],dimensions_m=[.022,.034,.063]))
        jobs.append(c)
def run_case(config):
    path=P/(config['name']+'.json')
    if args.reuse_recorded and path.exists():
        previous=json.loads(path.read_text())
        if previous['config']==config:return grade(previous,config)
    return execute(config)
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run_case,jobs))
report={'geometry':'full-geometry.json','mass':'full-mass-base.json',
   'gate':'30 seconds completed; no fall; no non-foot floor contact; no solver warnings; mean world-x speed >= 0.03 m/s; max tilt <=30 deg; heading deviation during 3–28s <=30 deg.',
   'heading_controller':{'gain':2,'rate_limit_rad_s':.8},'cases':results}
(P/'final-suite-summary.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'count':len(results),'pass':sum(r.get('walking_gate_pass',False) for r in results),
    'failures':[{'name':r.get('config',{}).get('name',r.get('name')),**{k:r.get(k) for k in ['error','fell','mean_forward_velocity_m_s','max_abs_heading_deviation_deg','max_tilt_deg']}} for r in results if not r.get('walking_gate_pass',False)]},indent=2))
