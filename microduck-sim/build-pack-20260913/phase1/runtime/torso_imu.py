# SPDX-License-Identifier: GPL-3.0-or-later
"""Frozen BNO085 transport/parser with separate quaternion/gyro freshness.

The upstream reader refreshed its timestamp on any report, allowing a stream of
accelerometer reports to conceal an old quaternion. Here the timestamp is the
oldest required quaternion/gyro receipt. It is still not a sensor-sampling time.
"""
import time
import imu_reader as upstream


class TorsoIMUReader(upstream.ThreadedIMUReader):
    def _run_loop(self):
        values = {'quat': (1., 0., 0., 0.), 'gyro': (0., 0., 0.), 'acc': (0., 0., 0.)}
        arrived = {'quat': None, 'gyro': None}
        while not self._stop_event.is_set():
            try:
                packet = self._imu.read_packet()
                now = time.perf_counter()
                if packet is None or packet[0] not in (upstream.CHAN_REPORTS, 4):
                    time.sleep(.001)
                    continue
                got = upstream._parse_reports(packet[1])
                for name in values:
                    if name in got:
                        values[name] = got[name]
                        if name in arrived:
                            arrived[name] = now
                valid = all(t is not None for t in arrived.values())
                timestamp = min(arrived.values()) if valid else now
                with self._lock:
                    self._snapshot = upstream.IMUSnapshot(timestamp_s=timestamp, **values,
                        valid=valid, error_count=self._error_count)
            except Exception:
                self._error_count += 1
                # Preserve the last timestamp; a broken bus must become stale.
                time.sleep(.02)


def install_reader():
    import robot_controller
    robot_controller.ThreadedIMUReader = TorsoIMUReader
