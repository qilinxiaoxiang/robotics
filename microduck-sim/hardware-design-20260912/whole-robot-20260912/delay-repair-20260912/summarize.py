from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent;F=P.parent/'dynamics'
original=json.loads((F/'final-suite-summary.json').read_text());repair=json.loads((P/'repaired-original45-summary.json').read_text());grid=json.loads((P/'delay-seed-grid36-summary.json').read_text());legacy=json.loads((P/'legacy-predictor3-summary.json').read_text())
index={r['config']['name']:r for r in original['cases']}
for r in repair['cases']:
 c=r['config'].copy()
 for k in ['delay_compensation','prediction_fraction','predict_heading']:c.pop(k)
 assert c==index[c['name']]['config'],c['name']
frozen=json.loads((P/'frozen-inputs-sha256.json').read_text());assert all(hashlib.sha256(Path(f).read_bytes()).hexdigest()==h for f,h in frozen.items())
def group(rows):
 return {'count':len(rows),'pass':sum(r['walking_gate_pass'] for r in rows),'falls':sum(r.get('fell',False) for r in rows),
  'max_tilt_deg':max(r['max_tilt_deg'] for r in rows),'max_heading_deviation_deg':max(r['max_abs_heading_deviation_deg'] for r in rows if r.get('max_abs_heading_deviation_deg') is not None),
  'world_x_mean_speed_range_m_s':[min(r['mean_forward_velocity_m_s'] for r in rows if r.get('mean_forward_velocity_m_s') is not None),max(r['mean_forward_velocity_m_s'] for r in rows if r.get('mean_forward_velocity_m_s') is not None)]}
result={'date_local':'2026-09-12 EDT','original45':group(original['cases']),'repaired_original45':group(repair['cases']),
 'original_config_fields_unchanged_except_predictor':True,'original_files_sha256_unchanged':True,
 'predictor_config':{'delay_compensation':'constant_velocity','prediction_fraction':1.,'predict_heading':True},
 'unchanged_controls':{'kp':200,'voltage_nominal_v':5,'action_delay_ms':20,'forward_command_m_s':.3,'heading_gain':2,'heading_rate_limit_rad_s':.8},
 'delay_grid':{str(ms):group([r for r in grid['cases'] if r['config'].get('sensor_delay_ticks',0)*20==ms]) for ms in [0,20,40,60]},
 'grid_seed_contract':'seed 0 nominal initial pose; seeds 9 and 42 add independent N(0,0.03 rad) initial-joint perturbations. No sensor-noise perturbation in this extra grid.',
 'legacy_state_prediction_without_heading':group(legacy['cases']),
 'failures_retained':[{'tag':r['tag'],'fall_time_s':r.get('fall_time_s'),'max_tilt_deg':r.get('max_tilt_deg'),'heading_deviation_deg':r.get('max_abs_heading_deviation_deg')} for r in grid['cases'] if not r['walking_gate_pass']],
 'scope':'Fixed-latency CPU simulation. Sample age known from injected FIFO; real hardware age is not established. Runtime entry defaults off when unknown.'}
(P/'results-summary.json').write_text(json.dumps(result,indent=2)+'\n')
(P/'candidate.json').write_text(json.dumps(result['predictor_config'],indent=2)+'\n')
(P/'experiment-files-sha256.json').write_text(json.dumps({str(x.relative_to(P)):hashlib.sha256(x.read_bytes()).hexdigest() for x in P.glob('*.py')},indent=2)+'\n')
print(json.dumps(result,indent=2))
