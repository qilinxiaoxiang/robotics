#!/usr/bin/env python3
"""Whole-source power and independent logic/motor path sensitivities; no physical test."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent

def screen(logic_a=1.0,motor_a=4.0,logic_m=.5):
    copper=json.loads((P.parent/'power/power_inputs.json').read_text())['wiring']['copper_ohm_m_at20C']
    factor=1+.00393*(40-20)
    def loop(gauge,length):return 2*length*copper[str(gauge)]*factor
    # Joint/contact/fuse drops are bounded design assumptions requiring actual readback.
    floor=5*.99-.020
    motor_r=loop(16,.5)+loop(16,.1)+8*.005+.100/10
    group_r=loop(20,.15)+4*.005+.131/3
    servo_r=loop(22,.1)+2*.020
    logic_r=loop(20,logic_m)+4*.005+2*.020+.131/3
    motor_v=floor-motor_a*motor_r-2.25*group_r-1.3*servo_r
    logic_v=floor-logic_a*logic_r
    total=logic_a+motor_a
    cases=[]
    for eta in [.90,.85]:
        input_power=5.05*total/eta
        # Conservative voltage drop at source-nameplate current including terminal/joint allowance.
        input_drop=2.5*(loop(16,.15)+.020)
        vin=12-input_drop
        required_input_a=input_power/vin
        cases.append(dict(assumed_efficiency=eta,required_input_w=input_power,input_lead_drop_upper_v=input_drop,converter_input_lower_v=vin,required_source_a=required_input_a,within_2p5a=required_input_a<=2.5))
    return dict(revision='phase1-single-source-r2',problem_ids=['P5','P6'],hardware_tests=0,
        evidence_kind='static sensitivity under explicitly unmeasured current, joint, contact and fuse assumptions',
        selected_source='Existing PB1033MI, one port at 12V/2.5A; Adafruit5991; DFR1202 common5V',
        total_output_a=total,logic_a=logic_a,motor_a=motor_a,wire_temperature_c=40,
        source_output_floor_v=floor,source_output_upper_v=5.05+.020,
        motor_main_loop_ohm=motor_r,group_loop_ohm=group_r,servo_loop_ohm=servo_r,logic_loop_ohm=logic_r,
        worst_group_a=2.25,worst_servo_a=1.3,motor_endpoint_lower_v=motor_v,logic_endpoint_lower_v=logic_v,
        efficiency_sensitivities=cases,within_whole_source_screen=total<=5 and all(x['within_2p5a'] for x in cases),
        logic_voltage_screen=logic_v>=4.75,motor_voltage_screen=motor_v>=4.0,
        exclusions=['Actual bank negotiation, transient protection and measured available output','Actual gait source current including jaw and logic','Regenerative peaks, shared-source ripple and Pi resets','Regulator thermal performance on the actual fixture','Actual hot fuse/contact/joint resistance and tether disturbance'],
        required_measurement='Simultaneous endpoint/current/thermal test, then actual walk-stop-pickup. No capacity or performance guarantee from this screen.')

if __name__=='__main__':
    result=screen()
    assert result['logic_voltage_screen'] and result['motor_voltage_screen'] and result['within_whole_source_screen'],result
    assert not screen(logic_m=3)['logic_voltage_screen']
    assert not screen(motor_a=6)['within_whole_source_screen']
    (P/'power-screen.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
