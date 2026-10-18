"""Reproduce purchase-stage Pi margin sensitivities; not measurements."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
x=json.loads((P/'power_inputs.json').read_text())
r20=x['wiring']['copper_ohm_m_at20C']['20']
rows=[]
for source_v in (4.85,4.95,5.):
 for amps in (.5,1.,1.5,2.25):
  for length_m in (.05,.1,.2):
   for contact_ohm in (0.,.01,.02,.05):
    for temp_c in (20,45):
     wire=2*length_m*r20*(1+.00393*(temp_c-20))
     v=source_v-amps*(wire+contact_ohm)
     rows.append(dict(source_v=source_v,pi_current_a=amps,oneway_m=length_m,
       assumed_contacts_and_solder_ohm=contact_ohm,copper_c=temp_c,pi_v=v,meets_4p8v=v>=4.8))
example=next(r for r in rows if r['source_v']==4.85 and r['pi_current_a']==2.25 and r['oneway_m']==.2 and r['assumed_contacts_and_solder_ohm']==.02 and r['copper_c']==20)
assert example['pi_v']<4.8
out=dict(evidence='calculation_only',cases=len(rows),assumptions='20AWG copper resistance from power_inputs; copper temperature coefficient .00393/K; contact values are scenarios, not manufacturer max or measurements',example_known_specification_gap=example,
 measured_servo_supervisor=dict(total_limit_a=5.,per_motor_limit_a=1.3,group_limit_a=2.25,poll_interval_s=.1,dwell_s=.2,
 minimum_input_assumption_v=6.6,logic_output_assumption_a=2.5,servo_efficiency_assumption=.8,logic_efficiency_assumption=.85,
 calculated_battery_a_excluding_wiring=(5*5/.8+5*2.5/.85)/6.6,
 warning='Not a hardware current clamp or a pack measurement; no guarantee of actual battery current or fault-stop latency'),rows=rows)
(P/'purchase-margin.json').write_text(json.dumps(out,indent=2)+'\n')
print('Pi example:',round(example['pi_v'],6),'V; 288 sensitivities; no hardware measurement.')
