# SPDX-License-Identifier: MIT
"""Phase 1 operator-guided pickup, with an exclusive controller and bounded inputs.

Imports the actual community Observer, RobotController and frozen 61D WalkMove.
Nothing opens hardware at import. Calibration angles are in community model radians;
jaw angles are rustypot hardware radians (encoder 2048 = 0), without an invented zero.
Every goal write passes jaw_limits (copied from guide/firmware/pi): head_pitch <= 65 deg while the jaw is open, and the
jaw opening <= min(25 deg, CAD first contact - 2 deg) for the commanded and measured head pose (jaw_pose_caps.json).
"""
import math
import hashlib
import json
import time
from constants import MOTOR_TO_ID, MOTOR_SIGN, MOTOR_OFFSET
import jaw_limits
from observer import Observer, Observation
from input.input_source import UserInput
from policy import Phase1Walk, BODY_KP
from moves.move import MotorCommand, MoveState
from imu_reader import imu_quat_to_body
from imu_mount import validate_record, apply_mount

IDS = list(range(1, 16))
BODY = list(MOTOR_TO_ID)
NAMES = BODY + ['jaw']
ORDER_IDS = list(MOTOR_TO_ID.values()) + [15]
GROUPS = ((1,2),(3,4),(5,10),(6,7),(8,9),(11,12),(13,14),(15,))
HEAD = {'neck_pitch', 'head_pitch', 'head_yaw', 'head_roll'}
ACTIONS = {'heartbeat', 'arm', 'ready', 'lower', 'open', 'close', 'lift', 'pickup',
           'release', 'walk', 'forward', 'backward', 'left', 'right', 'halt', 'stop'}

class Stop(RuntimeError):
    pass


# jaw_limits converts head joints to ticks with its own sign/offset; they must match this controller's mapping.
if any((MOTOR_TO_ID[n], MOTOR_SIGN[n], MOTOR_OFFSET[n]) != (
        jaw_limits.POSE_IDS[n], jaw_limits.POSE_SIGN[n], jaw_limits.POSE_OFFSET_RAD[n]) for n in jaw_limits.POSE_JOINTS) \
        or (jaw_limits.HEAD_PITCH_ID, jaw_limits.HEAD_PITCH_SIGN, jaw_limits.HEAD_PITCH_OFFSET_RAD) != (
        MOTOR_TO_ID['head_pitch'], MOTOR_SIGN['head_pitch'], MOTOR_OFFSET['head_pitch']) or jaw_limits.JAW_ID != 15:
    raise RuntimeError('jaw_limits.json head/jaw mapping differs from the community controller mapping')
LIMIT_IDS = {jaw_limits.JAW_ID: 'jaw', **{jaw_limits.POSE_IDS[n]: n for n in jaw_limits.POSE_JOINTS}}
LIMIT_READ_IDS = [jaw_limits.POSE_IDS[n] for n in jaw_limits.POSE_JOINTS] + [jaw_limits.JAW_ID]


def finite(values, count):
    values = list(values)
    if len(values) != count or any(isinstance(x, bool) or not math.isfinite(float(x)) for x in values):
        raise Stop('Incomplete or nonfinite device data')
    return [float(x) for x in values]


def calibration_hash(c):
    keys=("poses","jaw","joint_limits_rad","servo_current_total_limit_a","latency","imu_mount")
    return hashlib.sha256(json.dumps({k:c[k] for k in keys},sort_keys=True,allow_nan=False).encode()).hexdigest()


def validate_calibration(c, require_confirmed=True):
    if c.get('schema') != 1 or c.get('physical_calibration_confirmed') is not True and require_confirmed:
        raise Stop('Complete physical calibration before enabling torque')
    try:
        validate_record(c.get('imu_mount'))
    except (ValueError, KeyError, TypeError) as exc:
        raise Stop(str(exc)) from exc
    for name in ('ready', 'lower', 'carry'):
        pose = c.get('poses', {}).get(name)
        if not isinstance(pose, dict) or set(pose) != set(NAMES):
            raise Stop('Capture all 15 positions for ready, lower and carry')
        finite(pose.values(), 15)
    if require_confirmed and c.get('calibration_sha256') != calibration_hash(c):
        raise Stop('Calibration was changed after physical acceptance')
    jaw = c['jaw']
    finite([jaw['open_rad'], jaw['closed_rad']], 2)
    if not .01 <= abs(jaw['open_rad'] - jaw['closed_rad']) <= math.radians(30):
        raise Stop('Jaw calibration must span 0.6..30 degrees, within the inspected geometry')
    for name in BODY:
        lo, hi = c['joint_limits_rad'][name]
        finite([lo, hi], 2)
        if not -math.pi <= lo < hi <= math.pi:
            raise Stop('Invalid calibrated joint limit: ' + name)
        for p in c['poses'].values():
            if not lo <= p[name] <= hi:
                raise Stop('Captured pose exceeds limits: ' + name)
        if name not in HEAD and max(p[name] for p in c['poses'].values()) - min(p[name] for p in c['poses'].values()) > .035:
            raise Stop('Pickup poses must retain the same calibrated planted-leg pose')
    for key in ('ready', 'carry'):
        if abs(c['poses'][key]['jaw'] - jaw['open_rad']) > .035:
            raise Stop('Capture ready/carry with the jaw open')
    if not 20 <= jaw['goal_current_ma'] <= 150 or not jaw['goal_current_ma'] <= jaw['current_limit_ma'] <= 200:
        raise Stop('Jaw current configuration exceeds the initial commissioning envelope')
    if not 0 < c['servo_current_total_limit_a'] <= 5:
        raise Stop('Servo current limit must be within the commissioned supply/path envelope')
    return c


def extend_jaw(raw):
    """Fix ID15 mapping on this instance only; leave community MOTOR_TO_ID untouched."""
    raw._id_to_sign[15] = 1.0
    raw._id_to_offset[15] = 0.0
    return raw


def install_goal_limits(raw, zero, measured_jaw, on_clamp=None, measured_head=None):
    """Route every goal write on this controller through the shared jaw/head limits.

    This is the last point before rustypot sends Goal Position: head_pitch <= 65 deg while the commanded or measured
    jaw opening exceeds 2 deg, and jaw opening from the calibrated closed jaw <= the pose cap for the commanded and
    measured head pose, at most 25 deg (jaw_limits.json, jaw_pose_caps.json). measured_jaw returns ID15 hardware
    radians or None; measured_head returns {neck/head joint name: model radians} or None.
    """
    write = getattr(raw, '_unlimited_sync_write_goal_position', None) or raw.sync_write_goal_position
    raw._unlimited_sync_write_goal_position = write

    def limited(ids, positions):
        ids, positions = list(ids), [float(x) for x in positions]
        named = {LIMIT_IDS[i]: x for i, x in zip(ids, positions) if i in LIMIT_IDS}
        try:
            named, clamps = jaw_limits.limit_targets(named, zero, measured_jaw(),
                                                     measured_head() if measured_head is not None else None)
        except ValueError as exc:
            raise Stop(str(exc)) from exc
        out = [named[LIMIT_IDS[i]] if i in LIMIT_IDS else x for i, x in zip(ids, positions)]
        if on_clamp is not None:
            on_clamp(clamps)
        write(ids, out)

    raw.sync_write_goal_position = limited
    return raw


def restore_motion_profiles(wire):
    """RAM registers reset on power cycles; restore after the slow Wizard check."""
    wire.sync_write_profile_velocity(IDS, [0]*14+[10])
    wire.sync_write_profile_acceleration(IDS, [0]*15)
    if list(wire.sync_read_profile_velocity(IDS)) != [0]*14+[10] or list(wire.sync_read_profile_acceleration(IDS)) != [0]*15:
        raise Stop('Motion-profile register readback failed')


def verify_and_prepare(raw, c):
    """Called torque-off. EEPROM jaw setup is separate, explicit commissioning."""
    wire = raw._controller
    raw.sync_write_torque_enable(IDS, [False] * 15)
    if any(wire.sync_read_torque_enable(IDS)):
        raise Stop('Torque-off readback failed')
    if list(wire.sync_read_model_number(IDS)) != [1200] * 15:
        raise Stop('Require 15 XL330-M288-T devices with unique IDs 1..15')
    expected_modes = [3] * 14 + [5]
    if list(wire.sync_read_operating_mode(IDS)) != expected_modes:
        raise Stop('Body IDs1..14 require mode3; jaw ID15 requires configured mode5')
    if wire.read_current_limit(15) != c['jaw']['current_limit_ma']:
        raise Stop('Jaw Current Limit readback differs from calibration')
    if any(int(x) & 0x35 != 0x35 for x in wire.sync_read_shutdown(IDS)):
        raise Stop('Voltage, overheating, overload and electrical-shock shutdown protections must remain enabled')
    if list(wire.sync_read_min_voltage_limit(IDS)) != [37]*15 or list(wire.sync_read_max_voltage_limit(IDS)) != [60]*15:
        raise Stop('Servo voltage-limit readback differs from3.7–6.0V configuration')
    if any(int(x) & 1 for x in wire.sync_read_startup_configuration(IDS)) or any(wire.sync_read_drive_mode(IDS)):
        raise Stop('Require Drive Mode0: normal direction, velocity-based profile, automatic torque-on disabled')
    if any(wire.sync_read_hardware_error_status(IDS)):
        raise Stop('Servo hardware error is active; correct it before another session')
    restore_motion_profiles(wire)
    # Clear any old watchdog error only while torque-off; then arm 200ms device watchdog.
    wire.sync_write_bus_watchdog(IDS, [0] * 15)
    wire.sync_write_bus_watchdog(IDS, [10] * 15)
    if list(wire.sync_read_bus_watchdog(IDS)) != [10] * 15:
        raise Stop('200ms bus-watchdog register readback failed')
    wire.sync_write_goal_current([15], [c['jaw']['goal_current_ma']])
    if wire.read_goal_current(15) != c['jaw']['goal_current_ma']:
        raise Stop('Jaw Goal Current readback failed')
    raw.sync_write_kp(ORDER_IDS, [BODY_KP] * 14 + [100])


class Session:
    def __init__(self, raw, calibration, *, clock=time.monotonic, supported=False, max_seconds=120):
        self.raw = extend_jaw(raw)
        self.c = validate_calibration(calibration)
        self.jaw_zero = jaw_limits.JawZero.from_calibration(self.c)
        self.jaw_measured_rad = None
        self.head_measured_rad = None
        self.limit_clamps = []
        install_goal_limits(self.raw, self.jaw_zero, lambda: self.jaw_measured_rad, self.note_clamps,
                            lambda: self.head_measured_rad)
        apply_mount(self.c['imu_mount'])
        self.clock, self.supported = clock, supported
        self.started = self.last_packet = self.last_tick = clock()
        self.max_seconds = max_seconds
        self.last_seq = -1
        self.observer = Observer(raw)
        self.policy = Phase1Walk(controller=raw,latency=self.c.get("latency"))  # Real model load before any torque enable.
        self.reason = None
        self.armed = False
        self.mode = 'off'
        self.target = None
        self.queue = []
        self.segment = None
        self.velocity = dict(vx=0., vy=0., vtheta=0.)
        self.velocity_until = 0.
        self.gait_ready_at = math.inf
        self.stationary_since = self.started
        self.current_poll = -math.inf
        self.current_a = None
        self.voltage_v = None
        self.last_off_error = None
        self.events = []
        self.off('startup torque reset', latch=False)

    def note_clamps(self, clamps):
        if clamps != self.limit_clamps:
            event = {'time': self.clock(), 'event': 'goal_limits', 'clamped': list(clamps)}
            if 'jaw_closed_zone' in clamps:
                # The head pose leaves less than the usable jaw opening before CAD contact: the jaw is held closed.
                event['head_measured_rad'] = dict(self.head_measured_rad or {})
            self.events.append(event)
        self.limit_clamps = list(clamps)

    def off(self, reason, latch=True):
        if latch:
            self.reason = self.reason or reason
        self.armed = False
        self.mode = 'stopped' if latch else 'off'
        self.queue.clear()
        self.segment = None
        try:
            self.raw.sync_write_torque_enable(IDS, [False] * 15)
            self.last_off_error = None
        except Exception as e:
            self.last_off_error = repr(e)
        self.events.append({'time': self.clock(), 'event': 'torque_off_requested', 'reason': reason,
                            'bus_error': self.last_off_error})

    def fail(self, reason):
        self.off(str(reason))
        raise Stop(str(reason))

    def check(self):
        now = self.clock()
        if self.reason:
            raise Stop(self.reason)
        if self.last_off_error:
            self.fail('Torque-off request failed: ' + self.last_off_error)
        if now - self.started > self.max_seconds:
            self.fail('Session time limit')
        if now - self.last_packet > .6:
            self.fail('Mac input stream absent for 600ms')
        if now - self.last_tick > .1:
            self.fail('Control loop missed its 100ms deadline')
        status = self.raw.get_imu_status()
        if (status.get('bus'), status.get('addr')) != (self.c['imu_mount']['i2c_bus'], self.c['imu_mount']['i2c_address']):
            self.fail('IMU bus/address differs from the measured torso calibration')
        age = float(status['age_s'])
        if status.get('valid') is not True or not math.isfinite(age) or not 0 <= age <= .1:
            self.fail('IMU invalid or older than 100ms host receipt')
        q = finite(self.raw.read_quat(0.), 4)
        if sum(x*x for x in q) < 1e-12:
            self.fail('Invalid zero quaternion')
        w, x, y, z = imu_quat_to_body(q)
        if 1 - 2*(x*x + y*y) <= math.cos(math.radians(45)):
            self.fail('Body tilt reached 45 degrees')
        if now - self.current_poll >= .1:
            self.current_poll = now
            currents = finite(self.raw.sync_read_present_current(IDS), 15)
            currents = [v - 65.536 if v > 32.767 else v for v in currents]
            volts = [x*.1 for x in finite(self.raw._controller.sync_read_present_input_voltage(IDS), 15)]
            self.current_a, self.voltage_v = currents, volts
            # Measured jaw for the head-pitch interlock (a jaw held open by an object or still closing counts as open)
            # and measured neck/head pose (IDs 12, 11, 13, 14) for the jaw pose cap; model radians, jaw in ID15
            # hardware radians.
            measured = finite(self.raw.sync_read_present_position(LIMIT_READ_IDS), len(LIMIT_READ_IDS))
            self.head_measured_rad = dict(zip(jaw_limits.POSE_JOINTS, measured[:-1]))
            self.jaw_measured_rad = measured[-1]
            if any(v < 4.0 or v > 5.5 for v in volts):
                self.fail('Servo endpoint voltage outside the 4.0..5.5V commissioning envelope')
            if sum(abs(x) for x in currents) > self.c['servo_current_total_limit_a']:
                self.fail('Measured servo current exceeds the commissioned supply/path limit')
            if max(sum(abs(currents[i-1]) for i in group) for group in GROUPS) > 2.25:
                self.fail('Measured fused-group current exceeds2.25A')
            if max(abs(x) for x in currents[:14]) > 1.3 or abs(currents[14]) > self.c['jaw']['current_limit_ma']/1000 + .03:
                self.fail('Individual servo current above the commissioning envelope')
            if any(self.raw._controller.sync_read_hardware_error_status(IDS)):
                self.fail('Servo hardware error')
            if self.armed and list(self.raw._controller.sync_read_bus_watchdog(IDS)) != [10] * 15:
                self.fail('Servo bus watchdog tripped or was altered')
        # Include sensor/serial transaction latency, rather than checking before I/O only.
        if self.clock() - self.last_tick > .1:
            self.fail('Sensor/serial transaction exceeded the 100ms control deadline')

    def packet(self, packet):
        if not isinstance(packet, dict) or set(packet) != {'seq', 'action'}:
            self.fail('Malformed command packet')
        seq, action = packet['seq'], packet['action']
        if type(seq) is not int or seq <= self.last_seq or action not in ACTIONS:
            self.fail('Stale, duplicate or unknown command')
        self.last_packet, self.last_seq = self.clock(), seq
        if action == 'heartbeat':
            return
        if action == 'stop':
            self.fail('Operator stop')
        self.check()
        if action == 'arm':
            if self.armed:
                return
            verify_and_prepare(self.raw, self.c)
            # Commissioning register transactions happened torque-off; start the periodic
            # deadline now and recheck current/IMU/voltage before enabling.
            self.last_tick = self.clock()
            self.current_poll = -math.inf
            self.check()
            angles = finite(self.raw.sync_read_present_position(ORDER_IDS), 15)
            self.target = dict(zip(NAMES, angles))
            self.validate_target(self.target)
            # Preload the present position, avoiding a retained-goal snap on enable.
            self.raw.sync_write_goal_position(ORDER_IDS, angles)
            self.raw.sync_write_torque_enable(IDS, [True] * 15)
            if not all(self.raw._controller.sync_read_torque_enable(IDS)):
                self.fail('Torque-enable readback failed')
            self.armed = True
            self.mode = 'hold'
            return
        if not self.armed:
            self.fail('Arm with robot supported before requesting movement')
        if action in ('walk', 'forward', 'backward', 'left', 'right', 'halt'):
            if action in ('backward','left','right') and not self.c.get('physical_directional_gait_passed',False):
                self.fail('Backward/turning commands need separate physical directional-gait commissioning')
            if not self.c['physical_supported_walk_passed']:
                # Supported first walking test may precede the freestanding test.
                if not self.supported or not self.c['physical_supported_gait_ready']:
                    self.fail('Complete supported gait commissioning before walk commands')
            if self.queue or self.segment:
                self.fail('Finish pickup and return ready before walking')
            if self.mode != 'walk':
                self.mode = 'walk'
                self.policy.state = MoveState.STARTING
                self.policy._startup_start_s = None
                self.policy._last_action = [0.] * 14
                # Match the rehearsal startup:1.5s posture ramp then2s zero-command policy settling.
                self.gait_ready_at = self.clock() + 3.5
            self.velocity = dict(vx=0., vy=0., vtheta=0.)
            if action == 'forward': self.velocity['vx'] = .30
            if action == 'backward': self.velocity['vx'] = -.05
            if action == 'left': self.velocity['vtheta'] = .20
            if action == 'right': self.velocity['vtheta'] = -.20
            self.velocity_until = self.clock() + .25
            if action not in ('halt', 'walk'): self.stationary_since = self.clock()
            return
        if self.mode == 'walk' and (any(self.velocity.values()) or self.clock() - self.stationary_since < 1.):
            self.fail('Halt walking and remain stationary for at least one second before pickup')
        if not self.supported and not self.c['physical_supported_pickup_passed']:
            self.fail('Run supported pickup before freestanding pickup commissioning')
        self.mode = 'hold'
        self.velocity = dict(vx=0., vy=0., vtheta=0.)
        if action == 'pickup':
            self.queue = [('ready', 2., 'open'), ('lower', 2., 'open'),
                          ('lower', 1., 'closed'), ('carry', 2., 'closed')]
        elif action == 'release':
            self.queue = [('carry', 1., 'open'), ('ready', 2., 'open')]
        elif action in ('ready', 'lower', 'lift'):
            self.queue = [(('carry' if action == 'lift' else action), 2., None)]
        elif action in ('open', 'close'):
            self.queue = [(None, 1., 'open' if action == 'open' else 'closed')]
        self.segment = None

    def validate_target(self, target):
        if set(target) != set(NAMES):
            raise Stop('Require exactly 15 targets including jaw')
        finite(target.values(), 15)
        for name in BODY:
            lo, hi = self.c['joint_limits_rad'][name]
            if not lo <= target[name] <= hi:
                raise Stop('Target exceeds calibrated joint limits: ' + name)
        a, b = sorted([self.c['jaw']['open_rad'], self.c['jaw']['closed_rad']])
        if not a - .035 <= target['jaw'] <= b + .035:
            raise Stop('Jaw target exceeds calibrated open/closed limits')

    def tick(self):
        try:
            self.check()
            now = self.clock()
            if self.armed:
                if self.mode == 'walk':
                    if now > self.velocity_until:
                        self.velocity = dict(vx=0., vy=0., vtheta=0.)
                    state = self.observer.read_state(.02)
                    applied_velocity = self.velocity.copy() if now >= self.gait_ready_at else dict(vx=0.,vy=0.,vtheta=0.)
                    obs = Observation(state, UserInput(velocity=applied_velocity))
                    command = MotorCommand()
                    if self.policy.state == MoveState.STARTING:
                        self.policy.on_start(obs, command)
                    else:
                        self.policy.step(obs, command)
                    self.target = dict(command.target_angles, jaw=self.c['jaw']['open_rad'])
                else:
                    if self.segment is None and self.queue:
                        name, duration, jaw = self.queue.pop(0)
                        dest = self.target.copy() if name is None else self.c['poses'][name].copy()
                        dest['jaw'] = self.target['jaw'] if jaw is None else self.c['jaw'][jaw + '_rad']
                        # Limit commanded speed by lengthening this calibrated segment.
                        duration = max(duration, max(abs(dest[n]-self.target[n])/.25 for n in NAMES)*1.5)
                        self.segment = (now, duration, self.target.copy(), dest)
                    if self.segment:
                        start, duration, initial, dest = self.segment
                        t = min(1., (now-start)/duration)
                        t = t*t*(3-2*t)
                        self.target = {n: initial[n] + t*(dest[n]-initial[n]) for n in NAMES}
                        if now-start >= duration:
                            self.segment = None
                self.validate_target(self.target)
                # This is the only target writer and only owner of the serial controller.
                self.raw.sync_write_goal_position(ORDER_IDS, [self.target[n] for n in NAMES])
            tick_period=now-self.last_tick
            self.last_tick = now
            return {'tick_period_s':tick_period,'tick_work_s':self.clock()-now,'mode': self.mode, 'armed': self.armed, 'pending_segments': len(self.queue),
                    'gait_ready_in_s':max(0.,self.gait_ready_at-now) if self.mode=='walk' else None,'prediction_status':self.policy.prediction_status,'segment_active': self.segment is not None, 'current_a': self.current_a,
                    'voltage_v': self.voltage_v, 'limit_clamps': self.limit_clamps, 'stop_reason': self.reason}
        except Exception as e:
            self.off(str(e))
            raise
