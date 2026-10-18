"""Synthetic gate tests. These are not robot measurements."""
import copy
import json
from pathlib import Path
from calculate import calculate
from check_power_measurements import evaluate,PHASES
from probe_servos import decode

def run():
    root=Path(__file__).resolve().parent
    inputs=json.loads((root/'power_inputs.json').read_text());b=calculate(inputs)
    assert not b['scenarios'][-1]['within_regulator_graph_screen']
    assert not b['scenarios'][-2]['within_7p5a_input_design_all_assessed_points']
    assert all(x['meets_project_4p5v_margin'] for x in b['revised_individual_injection_voltage_sensitivity'])
    assert any(not x['meets_project_4p5v_margin'] for x in b['rejected_two_servo_daisy_power_voltage_sensitivity'])
    older_tolerance=copy.deepcopy(inputs);older_tolerance['servo']['output_accuracy_fraction']=.04
    old_voltage=calculate(older_tolerance)['revised_individual_injection_voltage_sensitivity']
    assert all(abs(new['motor_v_at_regulator_tolerance_floor']-old['motor_v_at_regulator_tolerance_floor']-.05)<1e-9
               for new,old in zip(b['revised_individual_injection_voltage_sensitivity'],old_voltage))
    undersized=copy.deepcopy(inputs);undersized['servo']['regulator_typical_a']=7
    assert not calculate(undersized)['scenarios'][-2]['within_regulator_graph_screen']
    assert evaluate({})['status']=='NOT_MEASURED_OR_INCOMPLETE'
    assert decode({'present_current_raw':65535,'present_voltage_raw':50,'operating_mode':3})['present_current_a']==-.001
    assert not decode({'operating_mode':3})['current_limit_register_applies_to_mode']
    assert decode({'operating_mode':5})['current_limit_register_applies_to_mode']
    row=dict(pi_min_v=4.9,pi_max_v=5.1,servo_min_v=4.7,servo_max_v=5.1,cell_min_v=3.6,cell_max_v=4.2,
        battery_max_c=35,plastic_near_regulator_max_c=35,regulator_max_c=50,servo_max_c=45,wire_connector_max_c=35,
        battery_continuous_a=5,logic_continuous_a=1.5,max_group_continuous_a=1.5,audio_continuous_a=.25,reset_or_bus_fault=False,
        all_15_servo_endpoints_checked=True,peak_battery_a=7,peak_servo_rail_a=9,peak_duration_ms=10,waveform_sample_rate_hz=1000000)
    good={'evidence':'physical_measurement','instruments':['SYNTHETIC TEST ONLY'],'phases':{p:row.copy() for p in PHASES}}
    assert evaluate(good)['status']=='PASS_DECLARED_MEASUREMENTS'
    bad=copy.deepcopy(good);bad['phases']['walk_camera_audio_10min']['pi_min_v']=4.6
    assert evaluate(bad)['status']=='FAIL'
    incomplete=copy.deepcopy(good);del incomplete['phases']['controlled_obstruction']
    assert evaluate(incomplete)['status']=='NOT_MEASURED_OR_INCOMPLETE'
    nan_case=copy.deepcopy(good);nan_case['phases']['logic_boot']['pi_min_v']=float('nan')
    assert evaluate(nan_case)['status']=='NOT_MEASURED_OR_INCOMPLETE'
    bool_case=copy.deepcopy(good);bool_case['phases']['logic_boot']['audio_continuous_a']=True
    assert evaluate(bool_case)['status']=='NOT_MEASURED_OR_INCOMPLETE'
    fault=copy.deepcopy(good);fault['phases']['supported_start']['reset_or_bus_fault']=True
    assert evaluate(fault)['status']=='FAIL'
    out={'synthetic_tests_passed':16,'physical_robot_tests':0,'scope':'budget contradiction, regulator tolerance sensitivity and undersized-current rejection, improved injection wiring, missing/nonfinite/bool measurement rejection, undervoltage/bus fault rejection, signed register decoding, mode-dependent current limit'}
    (root/'design-checks.json').write_text(json.dumps(out,indent=2)+'\n')
    template={'evidence':'not_measured','instruments':[],'phases':{p:{k:None for k in row} for p in PHASES}}
    (root/'measurements-template.json').write_text(json.dumps(template,indent=2)+'\n')
    (root/'electrical-acceptance-current.json').write_text(json.dumps(evaluate(template),indent=2)+'\n')
    print('16 synthetic design/gate checks passed. No physical robot tests.')

if __name__=='__main__':run()
