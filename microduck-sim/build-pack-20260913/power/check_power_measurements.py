#!/usr/bin/env python3
"""Evaluate measured summaries, never substitutes simulated or assumed numbers.

This gate covers declared instruments and points only. It cannot prove probe
placement, calibration, waveform bandwidth, harness assembly or test execution.
Python stdlib only; no hardware access.
"""
import argparse
import json
import math
from pathlib import Path

PHASES=['logic_boot','idle_torque_off','supported_start','stand_10min','walk_camera_audio_10min','controlled_obstruction']

def finite_number(value):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value)

def evaluate(data):
    failures=[];missing=[]
    if data.get('evidence')!='physical_measurement':missing.append('physical_measurement evidence')
    if not data.get('instruments'):missing.append('instruments/probe points')
    phases=data.get('phases',{})
    for name in PHASES:
        p=phases.get(name)
        if not isinstance(p,dict):missing.append(name);continue
        limits={'pi_min_v':('min',4.8),'pi_max_v':('max',5.25),
            'servo_min_v':('min',4.5),'servo_max_v':('max',5.5),
            'cell_min_v':('min',3.3),'cell_max_v':('max',4.2),
            'battery_max_c':('max',45),'plastic_near_regulator_max_c':('max',45),
            'regulator_max_c':('max',70),'servo_max_c':('max',60),
            'wire_connector_max_c':('max',45)}
        for k,(direction,bound) in limits.items():
            v=p.get(k)
            if not finite_number(v):missing.append(f'{name}.{k}')
            elif (direction=='min' and v<bound) or (direction=='max' and v>bound):failures.append(f'{name}.{k}={v}; {direction} {bound}')
        for k,bound in [('battery_continuous_a',7.5),('logic_continuous_a',2.5),('max_group_continuous_a',2.25),('audio_continuous_a',.375)]:
            v=p.get(k)
            if not finite_number(v):missing.append(f'{name}.{k}')
            elif not 0 <= v <= bound:failures.append(f'{name}.{k}={v}; expected 0..{bound}')
        if p.get('reset_or_bus_fault') is True:failures.append(f'{name}: reset or bus fault reported')
        elif p.get('reset_or_bus_fault') is not False:missing.append(f'{name}.reset_or_bus_fault must explicitly be false')
        if p.get('all_15_servo_endpoints_checked') is not True:missing.append(f'{name}.all_15_servo_endpoints_checked')
        for k in ['peak_battery_a','peak_servo_rail_a','peak_duration_ms','waveform_sample_rate_hz']:
            if not finite_number(p.get(k)):missing.append(f'{name}.{k}')
            elif p[k] < 0:failures.append(f'{name}.{k}: expected nonnegative magnitude/duration')
        if finite_number(p.get('waveform_sample_rate_hz')) and p['waveform_sample_rate_hz']<100_000:
            failures.append(f'{name}: waveform sample rate below 100kSa/s; cannot clear transient gate')
    return {'status':'FAIL' if failures else 'NOT_MEASURED_OR_INCOMPLETE' if missing else 'PASS_DECLARED_MEASUREMENTS',
       'failures':failures,'missing':missing,'automatic_hardware_acceptance':False,
       'scope':'Engineering screening thresholds, not a manufacturer certification. Assess measured peak pulse width/energy against regulator/fuse and actual stop response separately.'}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('measurements');ap.add_argument('--output');a=ap.parse_args()
    result=evaluate(json.loads(Path(a.measurements).read_text()))
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if a.output:Path(a.output).write_text(text)
    print(text,end='')
    raise SystemExit(0 if result['status']=='PASS_DECLARED_MEASUREMENTS' else 2)
