# SPDX-License-Identifier: MIT
"""Sensor-only torso calibration. This module never imports motor control."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import time
from phase1 import HERE, verify_bundle

PROMPTS = {
 'upright': 'Support the rigid TORSO upright: rear clamp cover vertical, its top edge level, beak pointing forward. Keep the head raised.',
 'forward': 'Tilt the WHOLE torso forward 15–25 degrees: beak end moves DOWN, tail end UP. Keep left/right edges level. Hold still.',
 'left': 'Return upright, then tilt the whole torso LEFT 15–25 degrees: duck\'s LEFT side DOWN, RIGHT side UP. Beak direction unchanged. Hold still.',
 'right': 'Return upright, then tilt the whole torso RIGHT 15–25 degrees: duck\'s RIGHT side DOWN, LEFT side UP. Hold still.',
 'back': 'Return upright, then tilt the whole torso BACK 15–25 degrees: beak end UP, tail end DOWN. Hold still.',
 'upright_return': 'Return the torso to the same physically level upright reference. Keep the head raised. Hold still.',
 'head_lowered': 'Keep the TORSO fixed at that upright reference. Gently lower only the head by about20 degrees and keep it there. Do not force a joint. Hold still.'}


def capture(reader, seconds=1.5, clock=time.perf_counter, sleep=time.sleep):
    from imu_mount import summarize
    samples = []
    last = None
    started = clock()
    while clock()-started < seconds:
        snap = reader.get_latest()
        now = clock()
        if snap.timestamp_s != last:
            samples.append({'timestamp_s': snap.timestamp_s, 'age_s': now-snap.timestamp_s,
                            'quat': list(snap.quat), 'gyro': list(snap.gyro), 'valid': snap.valid})
            last = snap.timestamp_s
        sleep(.005)
    summarize(samples)
    return samples


def calibrate(reader, ask=input, collect=capture):
    from imu_mount import POSES, create_record
    captures = {}
    for pose in POSES:
        ask(PROMPTS[pose] + '\nPress Enter only after it is still; keep holding for 1.5 seconds. ')
        captures[pose] = collect(reader)
        print('Captured ' + pose, flush=True)
    status = reader.get_status()
    return create_record(captures, int(status['bus']), int(status['addr']))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['calibrate', 'check'])
    p.add_argument('--motor-power-disconnected', action='store_true', required=True,
                   help='Physical external 5V motor barrel plug is unplugged; Pi/IMU remain powered')
    p.add_argument('--calibration', type=Path, default=HERE/'calibration.json')
    p.add_argument('--seconds', type=float, default=60)
    a = p.parse_args()
    if not 1 <= a.seconds <= 300:
        p.error('--seconds must be 1..300')
    verify_bundle()
    from torso_imu import TorsoIMUReader
    from imu_mount import validate_record, lean, rotate, conjugate, gravity_sensor
    c = json.loads(a.calibration.read_text())
    q = validate_record(c.get('imu_mount')) if a.command == 'check' else None
    # Share the runtime's lock and respect the community daemon marker.
    marker = Path('/tmp/microduck_scheduler.pid')
    if marker.exists():
        try:
            os.kill(int(marker.read_text().strip()), 0)
        except (ValueError, ProcessLookupError):
            pass
        else:
            raise RuntimeError('Stop the active controller before opening the IMU')
    with open('/tmp/microduck_phase1.lock', 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        marker.write_text(str(os.getpid()))
        reader = None
        try:
            reader = TorsoIMUReader(i2c_bus=1, frequency_hz=50.)
            reader.start()
            deadline = time.perf_counter()+5
            while time.perf_counter() < deadline:
                status = reader.get_status()
                if status['valid'] and status['age_s'] <= .1:
                    break
                time.sleep(.01)
            else:
                raise RuntimeError('No fresh quaternion and gyro within5s; check I2C wiring/configuration')
            status = reader.get_status()
            if status['bus'] != 1 or status['addr'] not in (0x4A, 0x4B):
                raise RuntimeError('Unexpected IMU connection for the Phase1 wiring')
            print(f"BNO085: /dev/i2c-{status['bus']}, address0x{status['addr']:02X}; motor port NEVER opened.")
            if a.command == 'calibrate':
                c['imu_mount'] = calibrate(reader)
                c['physical_calibration_confirmed'] = False
                c['physical_supported_gait_ready'] = False
                c['physical_supported_walk_passed'] = False
                c['physical_directional_gait_passed'] = False
                a.calibration.write_text(json.dumps(c, indent=2, allow_nan=False)+'\n')
                print(json.dumps({'result': 'measured_torso_axes_passed',
                                  'checks_deg': c['imu_mount']['checks_deg'],
                                  'body_to_sensor_wxyz': c['imu_mount']['body_to_sensor_wxyz']}))
                print('Restore the head to ready. Check the saved axes before motor commissioning.')
            else:
                if (status['bus'], status['addr']) != (c['imu_mount']['i2c_bus'], c['imu_mount']['i2c_address']):
                    raise RuntimeError('IMU bus/address differs from measured calibration')
                deadline = time.perf_counter()+a.seconds
                print('Positive FORWARD = beak end down. Positive LEFT = duck\'s left side down. Angles in degrees.')
                while time.perf_counter() < deadline:
                    status = reader.get_status()
                    if not status['valid'] or status['age_s'] > .1:
                        raise RuntimeError('IMU stale or invalid; do not enable motors')
                    values = lean(rotate(conjugate(q), gravity_sensor(reader.get_latest().quat)))
                    print(json.dumps(values), flush=True)
                    time.sleep(.2)
        finally:
            try:
                if reader is not None:
                    reader.stop()
            finally:
                if marker.exists() and marker.read_text().strip() == str(os.getpid()):
                    marker.unlink()


if __name__ == '__main__':
    try:
        main()
    except (Exception, KeyboardInterrupt) as exc:
        print('IMU CHECK STOPPED: '+str(exc))
        raise SystemExit(2)
