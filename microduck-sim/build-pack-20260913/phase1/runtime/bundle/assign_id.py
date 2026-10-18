# SPDX-License-Identifier: MIT
"""Assign one physically isolated XL330 a unique ID and 1Mbps bus rate."""
import argparse
import gc
import fcntl
from pathlib import Path
import glob
import json
import os
import time
from rustypot import Xl330PyController


def ports():
    candidates=glob.glob('/dev/cu.usbmodem*')+glob.glob('/dev/serial/by-id/usb-ROBOTIS_OpenRB-150_*')+glob.glob('/dev/ttyACM*')
    result={}
    for p in candidates:result.setdefault(os.path.realpath(p),p)
    return sorted(result.values())


def assign(port,new_id,*,initial_baud=57600,factory=Xl330PyController):
    if type(new_id) is not int or not 1<=new_id<=15:raise ValueError('Phase1 ID must be1..15')
    if initial_baud not in (57600,1000000):raise ValueError('Initial baud must be57600(factory) or1000000(already configured)')
    wire=factory(serial_port=port,baudrate=initial_baud,timeout=.01)
    found=[]
    for i in range(253):
        try:model=int(wire.read_model_number(i))
        except RuntimeError:continue
        found.append((i,model))
    if len(found)!=1 or found[0][1]!=1200:
        raise RuntimeError('Require exactly one responding XL330-M288-T: '+repr(found))
    old=found[0][0]
    wire.sync_write_torque_enable([old],[False])
    if wire.read_torque_enable(old):raise RuntimeError('Torque-off readback failed')
    if old!=new_id:
        wire.sync_write_id([old],[new_id])
        time.sleep(.03)
    if wire.read_id(new_id)!=new_id or wire.read_model_number(new_id)!=1200:
        raise RuntimeError('New ID readback failed; keep this servo isolated')
    wire.sync_write_baud_rate([new_id],[3])  # Official baud register value3 =1,000,000 bps.
    time.sleep(.03)
    del wire
    gc.collect()  # Release the serial port before reopening it at the new bus rate.
    final=factory(serial_port=port,baudrate=1000000,timeout=.03)
    if final.read_id(new_id)!=new_id or final.read_model_number(new_id)!=1200 or final.read_baud_rate(new_id)!=3:
        raise RuntimeError('1Mbps readback failed; keep this servo isolated')
    final.sync_write_torque_enable([new_id],[False])
    if final.read_torque_enable(new_id):raise RuntimeError('Final torque-off readback failed')
    return {'servo_id':new_id,'model_number':1200,'baudrate':1000000,'torque_enabled':False,
            'physical_action':'Label this servo with its ID, disconnect motor power, then replace it with the next isolated servo.'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--list-ports',action='store_true');p.add_argument('--port',default='auto')
    p.add_argument('--new-id',type=int);p.add_argument('--initial-baud',type=int,default=57600)
    p.add_argument('--one-servo-connected',action='store_true')
    a=p.parse_args()
    if a.list_ports:print(json.dumps(ports(),indent=2));return
    if a.new_id is None or not a.one_servo_connected:p.error('Connect exactly ONE physical servo and pass --new-id N --one-servo-connected')
    port=a.port
    if port=='auto':
        candidates=ports()
        if len(candidates)!=1:p.error('Require one OpenRB port; choose the exact --port from --list-ports')
        port=candidates[0]
    marker=Path('/tmp/microduck_scheduler.pid')
    if marker.exists():
        try:os.kill(int(marker.read_text().strip()),0)
        except (ValueError,ProcessLookupError):pass
        else:p.error('Stop the running motor controller before assigning IDs')
    with open('/tmp/microduck_phase1.lock','w') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        marker.write_text(str(os.getpid()))
        try:print(json.dumps(assign(port,a.new_id,initial_baud=a.initial_baud),indent=2))
        finally:
            if marker.exists() and marker.read_text().strip()==str(os.getpid()):marker.unlink()

if __name__=='__main__':main()
