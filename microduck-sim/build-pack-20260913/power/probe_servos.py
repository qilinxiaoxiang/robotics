#!/usr/bin/env python3
"""Read-only XL330 commissioning snapshot. Never writes a register or torque.

Use with robot supported, controller application stopped, on the Pi after wiring
has passed the voltage/polarity tests. Requires dynamixel-sdk; not used on any
physical robot during this design review. Sequential snapshot is NOT a peak
current instrument and must not share the serial device with the walk process.
"""
import argparse
import json
import time

REGISTERS={'model_number':(0,2),'operating_mode':(11,1),'temperature_limit_c':(31,1),
 'maximum_voltage_raw':(32,2),'minimum_voltage_raw':(34,2),'pwm_limit_raw':(36,2),
 'current_limit_ma':(38,2),'startup_configuration':(60,1),'shutdown_mask':(63,1),
 'torque_enabled':(64,1),'hardware_error':(70,1),'position_p_gain':(84,2),
 'bus_watchdog_raw':(98,1),'goal_current_ma':(102,2),'present_current_raw':(126,2),
 'present_voltage_raw':(144,2),'present_temperature_c':(146,1)}

def decode(raw):
    d=dict(raw)
    n=d.get('present_current_raw')
    if n is not None:d['present_current_a']=(n-65536 if n>=32768 else n)*.001
    for label in ('present','maximum','minimum'):
        n=d.get(label+'_voltage_raw')
        if n is not None:d[label+'_voltage_v']=n*.1
    d['current_limit_register_applies_to_mode']=d.get('operating_mode') in (0,5)
    d['warning']=('Mode 3/4 uses position/PWM control. Current Limit is not a guaranteed per-motor cap here.'
        if d.get('operating_mode') in (3,4) else None)
    return d

def snapshot(packet,port,ids,comm_success=0):
    records=[]
    for motor_id in ids:
        raw={};errors=[]
        for name,(address,width) in REGISTERS.items():
            val,comm,error=getattr(packet,f'read{width}ByteTxRx')(port,motor_id,address)
            if comm!=comm_success or error:errors.append({'field':name,'comm':comm,'device_error':error})
            else:raw[name]=val
        records.append({'id':motor_id,'host_receipt_monotonic_s':time.monotonic(),**decode(raw),'read_errors':errors})
    return {'read_only':True,'measurement_kind':'sequential_DYNAMIXEL_register_snapshot',
        'peak_current_measurement':False,'hardware_power_acceptance':False,
        'motor_count_requested':len(ids),'records':records}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--port',required=True);ap.add_argument('--baudrate',type=int,default=1_000_000)
    ap.add_argument('--ids',default=','.join(str(i) for i in range(1,16)))
    ap.add_argument('--output',required=True)
    args=ap.parse_args();ids=[int(i) for i in args.ids.split(',')]
    if len(ids)!=len(set(ids)) or any(i<0 or i>252 for i in ids):ap.error('Unique motor IDs 0..252 required')
    from dynamixel_sdk import PortHandler,PacketHandler,COMM_SUCCESS
    port=PortHandler(args.port)
    if not port.openPort():raise SystemExit('Could not open serial port; no writes performed')
    try:
        if not port.setBaudRate(args.baudrate):raise SystemExit('Could not set host serial baudrate')
        result=snapshot(PacketHandler(2.0),port,ids,COMM_SUCCESS)
        from pathlib import Path
        Path(args.output).write_text(json.dumps(result,indent=2)+'\n')
        raise SystemExit(2 if any(x['read_errors'] for x in result['records']) else 0)
    finally:port.closePort()
