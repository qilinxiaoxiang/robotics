#!/usr/bin/env python3
"""Reproduce electrical budget and audit old simulation. Python 3 stdlib only.

No device, network or source-repository writes. Scenario currents are explicitly
assumed DC rail currents; BAM torque/kt values are reported separately.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def rail_input_power(load_w, eta, vin, iq):
    # Published efficiency already includes regulator loss. Do not add iq twice.
    # The no-load floor prevents an implausibly small standby regulator loss.
    return max(load_w / eta, load_w + vin * iq)

def calculate(inputs):
    battery, servo, logic, wire = (inputs[x] for x in ('battery','servo','logic','wiring'))
    results=[]
    energy=battery['capacity_ah']*battery['nominal_v']
    for case in inputs['scenarios']:
        amps=case['servo14_a']+case['mouth_a']
        ps,pl=5*amps,5*case['logic_total_a']
        powers=[]; loss_s=[]; loss_l=[]; bat_current=[]
        for vin in (battery['assessment_low_v'],battery['nominal_v'],battery['full_v']):
            for es in servo['efficiency_range']:
                for el in logic['efficiency_range']:
                    sin=rail_input_power(ps,es,vin,servo['regulator_iq_a'])
                    lin=rail_input_power(pl,el,vin,logic['regulator_iq_a'])
                    powers.append(sin+lin);loss_s.append(sin-ps);loss_l.append(lin-pl)
                    bat_current.append((sin+lin)/vin)
        results.append({**case,'servo_total_a':amps,'servo_output_w':ps,'logic_output_w':pl,
            'battery_input_w_range':[min(powers),max(powers)],
            'battery_current_a_range':[min(bat_current),max(bat_current)],
            'servo_regulator_heat_w_range':[min(loss_s),max(loss_s)],
            'logic_regulator_heat_w_range':[min(loss_l),max(loss_l)],
            'runtime_minutes_range_if_continuous':None if not case['continuous'] else [
                60*energy*min(battery['usable_energy_fraction'])/max(powers),
                60*energy*max(battery['usable_energy_fraction'])/min(powers)],
            'within_7p5a_input_design_all_assessed_points':max(bat_current)<=battery['continuous_input_design_a'],
            'within_regulator_graph_screen':amps<=servo['regulator_typical_a'],
            'not_included':'wire/connector/fuse losses, cell sag and imbalance, regenerative transients, ageing; measured budget must replace assumptions'})
    voltage=[]
    for branch_i in (1.5,2.25,2.94):
        second_i=branch_i/2
        for contact_r in (.01,.02):
            first_r=2*wire['branch_oneway_m']*wire['copper_ohm_m_at20C']['22']+2*contact_r+wire['solder_joint_ohm_allowance']
            second_r=2*wire['second_servo_oneway_m']*wire['copper_ohm_m_at20C']['22']+2*contact_r
            # Conservative linear interpolation to rated hot fuse drop. Actual
            # fuse resistance depends on current and temperature, not guaranteed.
            fuse_drop=branch_i/3*wire['branch_fuse_hot_drop_at3a_v']
            main_drop=7.5*2*wire['main_output_oneway_m']*wire['copper_ohm_m_at20C']['16']
            drop=main_drop+branch_i*first_r+fuse_drop+second_i*second_r
            voltage.append({'branch_a':branch_i,'second_servo_a':second_i,'contact_r_ohm':contact_r,
                'calculated_far_servo_drop_v':drop,'far_servo_v_if_regulator_low_tolerance_4p8v':4.8-drop,
                'meets_project_4p5v_margin':4.8-drop>=4.5})
    revised_voltage=[]
    servo_floor=servo['rail_v']*(1-servo['output_accuracy_fraction'])
    for branch_i in (1.5,2.25,2.94):
        motor_i=branch_i/2
        for contact_r in (.01,.02):
            feed_r=2*wire['branch_oneway_m']*wire['copper_ohm_m_at20C']['20']+wire['solder_joint_ohm_allowance']
            tail_r=2*wire['individual_servo_tail_oneway_m']*wire['copper_ohm_m_at20C']['22']+2*contact_r
            drop=7.5*2*wire['main_output_oneway_m']*wire['copper_ohm_m_at20C']['16']+branch_i*feed_r+branch_i/3*wire['branch_fuse_hot_drop_at3a_v']+motor_i*tail_r
            revised_voltage.append({'group_a':branch_i,'motor_a':motor_i,'contact_r_ohm':contact_r,'calculated_drop_v':drop,'regulator_tolerance_floor_v':servo_floor,'motor_v_at_regulator_tolerance_floor':servo_floor-drop,'meets_project_4p5v_margin':servo_floor-drop>=4.5})
    pi_wire_r=2*wire['pi_oneway_m']*wire['copper_ohm_m_at20C']['20']
    return {'evidence':'design calculation, no hardware measurements','battery_nameplate_wh':energy,'scenarios':results,
        'rejected_two_servo_daisy_power_voltage_sensitivity':voltage,
        'revised_individual_injection_voltage_sensitivity':revised_voltage,
        'pi_voltage_margin':{'regulator_low_tolerance_v':4.85,'project_min_measured_v':4.8,'pi_leg_design_a':2.25,
          'available_total_path_resistance_ohm_at_low_tolerance':(.05/2.25),
          '20awg_200mm_oneway_wire_loop_r_ohm':pi_wire_r,
          'available_contact_and_joint_r_ohm':.05/2.25-pi_wire_r,
          'result':'fixed 5V +/-3% regulator plus unknown USB contacts cannot guarantee 4.8V by specifications; select/test actual board+cable or revise supply after measurement'},
        'capacitor_example':{'extra_load_a':5,'duration_s':.02,'allowed_drop_v':.25,'required_ideal_capacitance_f':5*.02/.25,
            'meaning':'0.4F ideal; small electrolytic is not a replacement for current capability'},
        'regulator_screen':{'model':servo['regulator'],'current_a':servo['regulator_typical_a'],'basis':servo.get('regulator_screen_basis'),'is_enclosure_or_transient_acceptance':False},
        'critical_failures':['all15 stall exceeds the selected regulator graph screening capacity','heavy load exceeds input fuse continuous design envelope under pessimistic efficiency','Pi 4.8V at low regulator tolerance not guaranteed','enclosure thermal resistance unknown','battery cell-level automatic cutoff not fitted'],
        'design_fix':'Rejected power-through-first-servo chain; feed each motor separately after eight group fuses. This fixes the assessed 20C wire/contact voltage-drop cases, not thermal or motion acceptance.'}

def audit_old_simulation():
    root=ROOT.parent.parent/'hardware-design-20260912/whole-robot-20260912'
    p=root/'delay-repair-20260912/repaired-original45-summary.json'
    if not p.exists(): return {'available':False,'reason':'old local results not included; budget still reproducible'}
    summary=json.loads(p.read_text());cases=[]
    for c in summary['cases']:
        src=p.parent/(c['tag']+'.json')
        if not src.exists():continue
        x=json.loads(src.read_text()); rows=x.get('rows',[])
        walk=[r['motor_current_sum_proxy_a'] for r in rows if 3<=r['time']<=28]
        cases.append({'tag':c['tag'],'peak_torque_derived_proxy_a':c['peak_summed_motor_current_proxy_a'],
            'walk_mean_torque_derived_proxy_a':sum(walk)/len(walk) if walk else None})
    return {'available':True,'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
       'old_controlled_motors':14,'actual_pack_or_load_current_measured':False,
       'formula':'sum(abs(MuJoCo actuator torque))/BAM kt',
       'limitation':'No motor PWM-to-DC-input conversion, regulator/battery electrical dynamics, cell state-of-charge or thermal solver. Does not include mouth/camera/Pi/audio/IMU/OpenRB.',
       'count':len(cases),'proxy_peak_a_range':[min(c['peak_torque_derived_proxy_a'] for c in cases),max(c['peak_torque_derived_proxy_a'] for c in cases)],
       'cases':cases}

if __name__=='__main__':
    inputs=json.loads((ROOT/'power_inputs.json').read_text())
    result=calculate(inputs)
    assert sum(map(len,inputs['wiring']['power_groups']))==15
    assert sorted(x for g in inputs['wiring']['power_groups'] for x in g)==list(range(1,16))
    assert abs(result['scenarios'][-1]['servo_total_a']-22.05)<1e-9
    assert result['scenarios'][-1]['within_regulator_graph_screen'] is False
    for filename,data in [('power-budget.json',result),('prior-simulation-electrical-audit.json',audit_old_simulation())]:
        (ROOT/filename).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print('Calculated seven scenarios, eight power groups, 15 motors. Electrical hardware acceptance: NOT MEASURED.')
