# SPDX-License-Identifier: MIT
"""Measured torso mounting; body axes are forward X, left Y and up Z.

The frozen driver reports sensor-to-world quaternions (w,x,y,z). This module
derives body-to-sensor rotation, so body_to_world = sensor_to_world * mount.
No default mounting rotation is accepted for the physical torso clamp.
"""
import hashlib
import json
import math
import numpy as np

POSES = ('upright', 'forward', 'left', 'right', 'back', 'upright_return', 'head_lowered')


def unit(v, size):
    a = np.asarray(v, dtype=float)
    if a.shape != (size,) or not np.all(np.isfinite(a)) or np.linalg.norm(a) < 1e-8:
        raise ValueError('Missing or invalid IMU vector')
    return a / np.linalg.norm(a)


def conjugate(q):
    w, x, y, z = unit(q, 4)
    return np.array([w, -x, -y, -z])


def multiply(a, b):
    w, x, y, z = a
    W, X, Y, Z = b
    return np.array([w*W-x*X-y*Y-z*Z, w*X+x*W+y*Z-z*Y,
                     w*Y-x*Z+y*W+z*X, w*Z+x*Y-y*X+z*W])


def rotate(q, v):
    q = unit(q, 4)
    return multiply(multiply(q, [0, *v]), conjugate(q))[1:]


def gravity_sensor(q):
    return rotate(conjugate(q), [0, 0, -1])


def angle_between(a, b):
    return math.degrees(math.acos(float(np.clip(np.dot(unit(a, 3), unit(b, 3)), -1, 1))))


def summarize(samples):
    """Require a stationary window with distinct, fresh quaternion reports."""
    if len(samples) < 25:
        raise ValueError('Need at least 25 distinct quaternion reports per held pose')
    ts = np.array([s['timestamp_s'] for s in samples], dtype=float)
    if not np.all(np.isfinite(ts)) or np.any(np.diff(ts) <= 0) or ts[-1]-ts[0] < .5:
        raise ValueError('IMU pose window has repeated/out-of-order or too few fresh reports')
    gs = []
    for s in samples:
        age = float(s['age_s'])
        gyro = np.asarray(s['gyro'], dtype=float)
        q = np.asarray(s['quat'], dtype=float)
        if not s['valid'] or not math.isfinite(age) or not 0 <= age <= .1:
            raise ValueError('IMU report invalid or older than 100 ms')
        if q.shape != (4,) or not .9 <= np.linalg.norm(q) <= 1.1:
            raise ValueError('Invalid quaternion norm')
        if gyro.shape != (3,) or not np.all(np.isfinite(gyro)) or np.linalg.norm(gyro) > .10:
            raise ValueError('Hold the entire torso still during capture')
        gs.append(gravity_sensor(q))
    mean = unit(np.mean(gs, axis=0), 3)
    spread = max(angle_between(g, mean) for g in gs)
    if spread > 2:
        raise ValueError('Held pose moved by more than 2 degrees')
    return {'gravity_sensor': mean.tolist(), 'spread_deg': spread, 'samples': samples}


def matrix_quaternion(m):
    # Symmetric eigenproblem, robust near 180-degree mounting rotations.
    m = np.asarray(m)
    k = np.array([
        [m[0,0]-m[1,1]-m[2,2], m[1,0]+m[0,1], m[2,0]+m[0,2], m[2,1]-m[1,2]],
        [m[1,0]+m[0,1], m[1,1]-m[0,0]-m[2,2], m[2,1]+m[1,2], m[0,2]-m[2,0]],
        [m[2,0]+m[0,2], m[2,1]+m[1,2], m[2,2]-m[0,0]-m[1,1], m[1,0]-m[0,1]],
        [m[2,1]-m[1,2], m[0,2]-m[2,0], m[1,0]-m[0,1], np.trace(m)]]) / 3
    _, vectors = np.linalg.eigh(k)
    x, y, z, w = vectors[:, -1]
    q = np.array([w, x, y, z])
    return -q if w < 0 else q


def lean(gravity):
    x, y, z = unit(gravity, 3)
    return {'forward_deg': math.degrees(math.atan2(x, -z)),
            'left_deg': math.degrees(math.atan2(y, -z)),
            'tilt_deg': math.degrees(math.acos(float(np.clip(-z, -1, 1))))}


def solve(captures):
    if set(captures) != set(POSES):
        raise ValueError('Complete all seven physical torso pose checks')
    windows = {name: summarize(captures[name]) for name in POSES}
    gravity = {name: np.array(w['gravity_sensor']) for name, w in windows.items()}
    forward_angle = angle_between(gravity['upright'], gravity['forward'])
    if not 10 <= forward_angle <= 35:
        raise ValueError('Tilt the whole torso forward by 10–35 degrees before holding still')
    z = -gravity['upright']
    x = unit(gravity['forward'] - np.dot(gravity['forward'], z)*z, 3)
    y = unit(np.cross(z, x), 3)
    x = np.cross(y, z)
    rotation = np.column_stack([x, y, z])
    mount = matrix_quaternion(rotation)
    values = {name: lean(rotation.T @ g) for name, g in gravity.items()}
    for name in ('upright', 'upright_return', 'head_lowered'):
        if values[name]['tilt_deg'] > 3:
            raise ValueError(name + ': torso reference moved, sensor is loose, or sensor follows the head')
    for name, axis, sign in (('forward','forward_deg',1), ('back','forward_deg',-1),
                             ('left','left_deg',1), ('right','left_deg',-1)):
        cross_axis = 'left_deg' if axis == 'forward_deg' else 'forward_deg'
        if not 10 <= sign*values[name][axis] <= 35 or abs(values[name][cross_axis]) > 5:
            raise ValueError(name + ': wrong direction or excessive sideways lean; repeat with whole torso')
    return mount.tolist(), values


def create_record(captures, bus, addr):
    if bus != 1 or addr not in (0x4A, 0x4B):
        raise ValueError('Phase 1 expects BNO085 on I2C bus 1 at 0x4A (or DI-selected 0x4B)')
    q, checks = solve(captures)
    record = {'schema': 1, 'body_to_sensor_wxyz': q, 'i2c_bus': bus, 'i2c_address': addr,
              'body_axes': 'X forward; Y left; Z up', 'captures': captures, 'checks_deg': checks}
    record['sha256'] = record_hash(record)
    return record


def record_hash(record):
    return hashlib.sha256(json.dumps({k: v for k, v in record.items() if k != 'sha256'},
                                    sort_keys=True, allow_nan=False).encode()).hexdigest()


def validate_record(record):
    if not isinstance(record, dict) or record.get('schema') != 1:
        raise ValueError('Run the no-motor imu_calibrate.py calibrate procedure first')
    if record.get('sha256') != record_hash(record):
        raise ValueError('IMU calibration evidence changed; repeat the guided measurement')
    q, _ = solve(record['captures'])
    saved = unit(record['body_to_sensor_wxyz'], 4)
    if abs(float(np.dot(q, saved))) < 1-1e-10:
        raise ValueError('Saved IMU rotation disagrees with measured pose evidence')
    if record['i2c_bus'] != 1 or record['i2c_address'] not in (0x4A, 0x4B):
        raise ValueError('Unexpected calibrated IMU connection')
    return tuple(saved)


def apply_mount(record):
    """Update every frozen import alias; no upstream file is edited."""
    q = validate_record(record)
    import constants
    import imu_reader
    import moves.walk
    constants.IMU_MOUNT_QUAT = q
    imu_reader.IMU_MOUNT_QUAT = q
    moves.walk.IMU_MOUNT_QUAT = q
    return q
