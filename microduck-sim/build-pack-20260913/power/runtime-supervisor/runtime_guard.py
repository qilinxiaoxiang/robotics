# SPDX-License-Identifier: MIT
"""Supervised bench-run guard. No device opens here; wraps the actual controller.

Torque-off is a bus REQUEST, not proven power disconnection. No voltage/cell
sensor or independent watchdog is invented. Current samples are slow software
screening, not a mode-3 current clamp. All exceptions latch until a new process.
"""
import math
import time

IDS = tuple(range(1, 16))
GROUPS = ((1, 2), (3, 4), (5, 10), (6, 7), (8, 9), (11, 12), (13, 14), (15,))

class SafetyStop(Exception):
    pass

class GuardController:
    def __init__(self, raw, imu_to_body, *, clock=time.monotonic,
                 max_session_s=120.0, imu_max_host_age_s=.100,
                 current_interval_s=.100, current_hold_s=.200):
        self.raw = raw
        self.imu_to_body = imu_to_body
        self.clock = clock
        self.started = clock()
        self.max_session_s = max_session_s
        self.imu_max_host_age_s = imu_max_host_age_s
        self.current_interval_s = current_interval_s
        self.current_hold_s = current_hold_s
        self.latched_reason = None
        self.torque_off_request_count = 0
        self.last_torque_off_error = None
        self.last_current_poll = -math.inf
        self.overcurrent_since = None
        self.last_current_a = None
        self.current_poll_duration_s = None
        # Reset residual torque before model loading/ramping; ID15 is included.
        self._disable()

    def __getattr__(self, name):
        return getattr(self.raw, name)

    def _disable(self):
        self.torque_off_request_count += 1
        try:
            self.raw.sync_write_torque_enable(list(IDS), [False] * len(IDS))
            self.last_torque_off_error = None
        except Exception as exc:
            self.last_torque_off_error = repr(exc)

    def stop(self, reason):
        self.latched_reason = self.latched_reason or str(reason)
        self._disable()

    def _trip(self, reason):
        self.stop(reason)
        detail = '; torque-off bus request failed: ' + self.last_torque_off_error if self.last_torque_off_error else ''
        raise SafetyStop(self.latched_reason + detail + '; operator must support robot and switch EN off')

    def _check_imu(self):
        try:
            status = self.raw.get_imu_status()
            age = float(status['age_s'])
            if status.get('valid') is not True or not math.isfinite(age) or not 0 <= age <= self.imu_max_host_age_s:
                self._trip('IMU invalid/stale host-receipt data')
            q = tuple(float(x) for x in self.raw.read_quat(0.0))
            if len(q) != 4 or not all(math.isfinite(x) for x in q) or sum(x*x for x in q) < 1e-12:
                self._trip('IMU quaternion invalid')
            w, x, y, z = self.imu_to_body(q)
            # Body up dot world up; 60 degrees matches old walk's -0.5 gravity threshold.
            body_up_cos = 1 - 2 * (x*x + y*y)
            if not math.isfinite(body_up_cos) or body_up_cos <= .5:
                self._trip('body tilt at least 60 degrees')
        except SafetyStop:
            raise
        except Exception as exc:
            self._trip('IMU read/transform failure: ' + repr(exc))

    def _check_current(self, now):
        if now - self.last_current_poll < self.current_interval_s:
            return
        self.last_current_poll = now
        try:
            # Actual community method returns A, including ID15 without joint-angle mapping.
            start = self.clock()
            values = [float(x) for x in self.raw.sync_read_present_current(list(IDS))]
            self.current_poll_duration_s = self.clock() - start
            if len(values) != 15 or not all(math.isfinite(x) and -32.768 <= x <= 65.535 for x in values):
                self._trip('15 complete finite current readings required')
            # Rust/SDK variants can expose unsigned 16-bit current before scaling to A.
            values = [x - 65.536 if x > 32.767 else x for x in values]
            self.last_current_a = dict(zip(IDS, values))
            currents = [abs(x) for x in values]
            group_peak = max(sum(currents[i-1] for i in group) for group in GROUPS)
            # Conservative supervised-run envelope derived from 7.5A battery,
            # 6.6V input, eta_servo=.80 and logic=2.5A at eta_logic=.85.
            excessive = sum(currents) > 5.0 or group_peak > 2.25 or max(currents) > 1.3
            if excessive:
                if self.overcurrent_since is None:
                    self.overcurrent_since = now
                elif now - self.overcurrent_since >= self.current_hold_s:
                    self._trip('sustained measured servo-side current above bench envelope')
            else:
                self.overcurrent_since = None
        except SafetyStop:
            raise
        except Exception as exc:
            self._trip('current-read failure: ' + repr(exc))

    def check(self):
        if self.latched_reason:
            raise SafetyStop(self.latched_reason + '; re-enable is latched off')
        if self.last_torque_off_error:
            self._trip('initial torque-off request could not be sent')
        now = self.clock()
        if now - self.started >= self.max_session_s:
            self._trip('supervised session time limit reached; not a battery-voltage measurement')
        self._check_imu()
        self._check_current(now)
        # Current read adds bus latency: recheck host freshness after that transaction.
        self._check_imu()

    def sync_write_torque_enable(self, ids, values):
        if any(values):
            self.check()
        return self.raw.sync_write_torque_enable(ids, values)

    def sync_read_present_position(self, ids):
        # Called even when WalkMove returns no target after a fall.
        self.check()
        return self.raw.sync_read_present_position(ids)

    def sync_write_goal_position(self, ids, positions):
        self.check()
        return self.raw.sync_write_goal_position(ids, positions)

    def shutdown(self):
        # Torque request precedes potentially failing input/IMU cleanup.
        self.stop('controller shutdown')
        return self.raw.shutdown()
