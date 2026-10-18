#!/usr/bin/env python3
"""Read-only sensor dependency preflight. Never opens camera, I2C or motors."""
import importlib.util,json,platform,struct,sys
from pathlib import Path

def assess(model,machine,bits,modules):
    zero1='Zero W' in model and 'Zero 2' not in model
    zero2='Zero 2 W' in model
    pi3='3 Model B' in model
    known=zero1 or zero2 or pi3
    errors=[]
    if not known:errors.append('Target Pi identity not established')
    if zero1 and (bits!=32 or machine != 'armv6l'):
        errors.append('First-generation Zero W requires a 32-bit ARMv6-compatible userland; verify the actual OS image')
    if (zero2 or pi3) and not (bits in (32,64) and machine in ('armv7l','armv8l','aarch64')):
        errors.append('Expected a supported ARM userland for this board')
    for name in ('picamera2','libcamera','numpy'):
        if not modules.get(name):errors.append('Missing sensor dependency: '+name)
    return {'softwarePreflightPassed':not errors,'boardModel':model,'machine':machine,'pointerBits':bits,'modulesPresent':modules,'errors':errors,'hardwareOpened':False,'captureStreamingOrTimingValidated':False,'motorControlEnabled':False}

def main():
    f=Path('/proc/device-tree/model');model=f.read_bytes().decode(errors='replace').strip('\0') if f.exists() else 'Not a Raspberry Pi device tree'
    modules={n:importlib.util.find_spec(n) is not None for n in ('picamera2','libcamera','numpy')}
    result=assess(model,platform.machine(),struct.calcsize('P')*8,modules)
    print(json.dumps(result,indent=2));return 0 if result['softwarePreflightPassed'] else 2
if __name__=='__main__':raise SystemExit(main())
