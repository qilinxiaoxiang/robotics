# SPDX-License-Identifier: MIT
"""Foreground Phase1 launcher. Hardware opens only inside an explicit subcommand."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import queue
import signal
import sys
import threading
import time

HERE=Path(__file__).resolve().parent

def verify_bundle():
    lock=json.loads((HERE/'bundle-lock.json').read_text())
    for name,digest in lock['files'].items():
        # Calibration and logs intentionally live outside frozen source manifest.
        if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=digest:
            raise RuntimeError('Bundle changed: '+name+'; rebuild and retest before hardware use')
    sys.path.insert(0,str(HERE/'community/src'))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['check','configure','capture','accept-calibration','run'])
    p.add_argument('--port',default='auto');p.add_argument('--calibration',type=Path,default=HERE/'calibration.json')
    p.add_argument('--name',choices=['ready','lower','carry','jaw-open','jaw-closed'])
    p.add_argument('--supported',action='store_true',help='The operator has attached a physical support fixture')
    p.add_argument('--evidence',help='Physical checks performed, or log/video file reference; required to accept calibration')
    p.add_argument('--max-seconds',type=float,default=120)
    a=p.parse_args()
    verify_bundle()
    from core import Session, Stop, extend_jaw, finite, NAMES, ORDER_IDS, IDS, validate_calibration, calibration_hash, restore_motion_profiles
    from robot_controller import RobotController
    from rustypot import Xl330PyController
    from torso_imu import install_reader
    install_reader()
    if a.command=='check':
        for name in ('sync_write_profile_velocity','sync_read_profile_velocity','sync_write_profile_acceleration','sync_read_profile_acceleration'):
            if not hasattr(Xl330PyController,name): raise RuntimeError('Missing rustypot method '+name)
        for name in ['sync_write_goal_position', 'sync_read_present_position', 'sync_read_present_velocity', 'sync_read_present_current', 'sync_read_torque_enable', 'sync_write_torque_enable', 'sync_write_bus_watchdog', 'sync_read_bus_watchdog', 'sync_read_present_input_voltage', 'sync_write_goal_current', 'sync_write_operating_mode', 'sync_write_current_limit', 'sync_read_model_number', 'sync_read_operating_mode', 'read_operating_mode', 'read_current_limit', 'read_goal_current', 'sync_read_shutdown', 'sync_write_shutdown', 'sync_read_startup_configuration', 'sync_write_startup_configuration', 'sync_read_drive_mode', 'sync_write_drive_mode', 'sync_read_hardware_error_status', 'sync_write_position_p_gain', 'sync_write_min_voltage_limit', 'sync_write_max_voltage_limit', 'sync_read_min_voltage_limit', 'sync_read_max_voltage_limit']:
            if not hasattr(Xl330PyController,name): raise RuntimeError('Missing rustypot method '+name)
        from policy import Phase1Walk
        model=Phase1Walk()
        print(json.dumps({'status':'offline_dependency_model_check_passed',
                          'policies':list(model._sessions), 'hardware_opened':False}))
        return
    c=json.loads(a.calibration.read_text())
    if a.command=='accept-calibration':
        validate_calibration(c,require_confirmed=False)
        if not a.evidence: p.error('Record physical direction, clearance, endpoint voltage and supported pose checks in --evidence')
        c['physical_calibration_confirmed']=True;c['physical_calibration_evidence']=a.evidence
        c['calibration_sha256']=calibration_hash(c)
        a.calibration.write_text(json.dumps(c,indent=2)+'\n');return
    if a.command in ('capture','configure') and not a.supported:
        p.error('These commands turn all torque off; attach support and pass --supported')
    if a.command=='capture' and not a.name:p.error('--name is required')
    if a.command=='run':
        validate_calibration(c)
        if not 1<=a.max_seconds<=600:p.error('--max-seconds must be 1..600')
    # Check community's existing process marker as well as our advisory lock.
    oldpid=Path('/tmp/microduck_scheduler.pid')
    if oldpid.exists():
        try:
            old=int(oldpid.read_text().strip());os.kill(old,0)
        except (ValueError,ProcessLookupError):pass
        else:raise RuntimeError('An existing community controller owns the motor bus')
    lock=open('/tmp/microduck_phase1.lock','w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    oldpid.write_text(str(os.getpid()))
    raw=None;session=None;log=None
    def signal_stop(signum,frame):raise Stop('Process termination signal '+str(signum))
    for sig in (signal.SIGTERM,signal.SIGHUP,signal.SIGINT):signal.signal(sig,signal_stop)
    try:
        # 30ms serial timeout per transaction; actual loop timing is checked independently.
        raw=extend_jaw(RobotController(serial_port=a.port,timeout=.03))
        raw.sync_write_torque_enable(IDS,[False]*15)
        if any(raw._controller.sync_read_torque_enable(IDS)):raise Stop('Torque-off readback failed')
        if list(raw._controller.sync_read_model_number(IDS)) != [1200]*15:raise Stop('Require all15 XL330-M288-T IDs1..15 before configuration or capture')
        if a.command=='configure':
            # Only this explicit, torque-off commissioning command changes persistent settings.
            raw._controller.sync_write_operating_mode(IDS,[3]*14+[5])
            raw._controller.sync_write_min_voltage_limit(IDS,[37]*15)
            raw._controller.sync_write_max_voltage_limit(IDS,[60]*15)
            old_shutdown=raw._controller.sync_read_shutdown(IDS)
            raw._controller.sync_write_shutdown(IDS,[int(x)|0x35 for x in old_shutdown])
            raw._controller.sync_write_startup_configuration(IDS,[0]*15)
            raw._controller.sync_write_drive_mode(IDS,[0]*15)
            raw._controller.sync_write_operating_mode([15],[5])
            raw._controller.sync_write_current_limit([15],[c['jaw']['current_limit_ma']])
            raw._controller.sync_write_goal_current([15],[c['jaw']['goal_current_ma']])
            actual={'mode':raw._controller.read_operating_mode(15),
                    'current_limit_ma':raw._controller.read_current_limit(15),
                    'goal_current_ma':raw._controller.read_goal_current(15)}
            if actual != {'mode':5,'current_limit_ma':c['jaw']['current_limit_ma'],'goal_current_ma':c['jaw']['goal_current_ma']}:
                raise Stop('Jaw configuration readback failed: '+repr(actual))
            if list(raw._controller.sync_read_operating_mode(IDS)) != [3]*14+[5]:raise Stop('Operating mode readback failed')
            if list(raw._controller.sync_read_min_voltage_limit(IDS)) != [37]*15 or list(raw._controller.sync_read_max_voltage_limit(IDS)) != [60]*15:raise Stop('Voltage limit readback failed')
            if any(int(x)&0x35!=0x35 for x in raw._controller.sync_read_shutdown(IDS)):raise Stop('Voltage shutdown readback failed')
            if any(raw._controller.sync_read_drive_mode(IDS)) or any(raw._controller.sync_read_startup_configuration(IDS)):raise Stop('Drive/startup configuration readback failed')
            restore_motion_profiles(raw._controller)
            print(json.dumps(actual));return
        if a.command=='capture':
            print('Torque is OFF. Keep the body supported. Position the joints gently, then press Enter.',file=sys.stderr)
            input()
            pose=dict(zip(NAMES,finite(raw.sync_read_present_position(ORDER_IDS),15)))
            if a.name.startswith('jaw-'):c['jaw'][a.name[4:]+'_rad']=pose['jaw']
            else:c['poses'][a.name]=pose
            c['physical_calibration_confirmed']=False
            a.calibration.write_text(json.dumps(c,indent=2)+'\n')
            print(json.dumps({'captured':a.name,'pose_rad':pose}));return
        deadline=time.monotonic()+2
        while time.monotonic()<deadline and raw.get_imu_status().get('valid') is not True:time.sleep(.01)
        session=Session(raw,c,supported=a.supported,max_seconds=a.max_seconds)
        inbox=queue.Queue(maxsize=16)
        def reader():
            try:
                for line in sys.stdin:
                    inbox.put(json.loads(line),timeout=.1)
            except Exception as e:
                try:inbox.put_nowait({'error':repr(e)})
                except queue.Full:pass
            finally:
                try:inbox.put_nowait(None)
                except queue.Full:pass
        threading.Thread(target=reader,daemon=True).start()
        next_tick=time.monotonic();last_report=0
        log=HERE/('session-'+str(time.time_ns())+'.jsonl')
        with log.open('w') as out:
            while True:
                try:
                    for _ in range(16):
                        packet=inbox.get_nowait()
                        if packet is None:raise Stop('Mac input stream closed')
                        session.packet(packet)
                except queue.Empty:pass
                report=session.tick()
                if time.monotonic()-last_report>.5:
                    last_report=time.monotonic();report['time']=last_report
                    print(json.dumps(report),flush=True);out.write(json.dumps(report)+'\n');out.flush()
                next_tick+=.02
                time.sleep(max(0,next_tick-time.monotonic()))
    except BaseException as exc:
        if session is not None:session.off(str(exc))
        raise
    finally:
        if session is not None:session.off('Launcher exit')
        if raw is not None:
            try:
                raw.sync_write_torque_enable(IDS,[False]*15)
                if any(raw._controller.sync_read_torque_enable(IDS)):
                    print('TORQUE OFF NOT CONFIRMED. Support robot and unplug the external5V motor barrel connector.',file=sys.stderr)
            except Exception as e:
                print('TORQUE OFF FAILED. Support robot and unplug the external5V motor barrel connector: '+repr(e),file=sys.stderr)
            try:raw.shutdown()
            except Exception:pass
        if log is not None and session is not None:
            with log.open('a') as out:
                out.write(json.dumps({'final':True,'stop_reason':session.reason,'torque_off_bus_error':session.last_off_error,'events':session.events})+'\n')
        if oldpid.exists() and oldpid.read_text().strip()==str(os.getpid()):oldpid.unlink()
        lock.close()

if __name__=='__main__':
    try:main()
    except Exception as e:
        print('STOP: '+str(e),file=sys.stderr)
        raise SystemExit(2)
