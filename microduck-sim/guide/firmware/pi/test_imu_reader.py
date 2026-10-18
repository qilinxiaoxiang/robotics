"""Unit tests for microduck_rt/imu_reader.py and the age field of pi_imu_uart.py. No hardware: SHTP payloads are
built by hand from the SH-2 Reference Manual (CEVA 1000-3625 v1.9):
  6.5.1  Common Fields: byte 2 status, bits 7:2 = 6 MSBs of the report delay; byte 3 = 8 LSBs; units 100 us.
  6.5.13 Gyroscope Calibrated (0x02): 10 bytes, X Y Z int16, Q9.
  6.5.19 Game Rotation Vector (0x08): 12 bytes, i j k real int16, Q14.
  7.2.1  Base Timestamp Reference (0xFB): int32 base delta, signed, 100 us ticks, "delta of 10" => timestamps
         relative to HINT - 1 ms.
  7.2.2  Timestamp Rebase (0xFA): int32 signed, added to the base; worked example HINT 5.0 s, base 4.0 s,
         rebase 1.5 s, report delay 1.0 s => sample at 3.5 s.
  5.2 / 6.5.44  Gyro-Integrated Rotation Vector (0x2A): set-feature with ID 0x2A on the control channel, data on
         the separate "gyroRV" SHTP channel (sh2.c: CHAN_SENSORHUB_INPUT_GIRV = 5); input report is 14 bytes,
         "*DOES NOT* contain a report ID field" (so no sequence/status/delay either, no 0xFB base timestamp):
         i j k real int16 Q14, then angular velocity x y z int16 Q10 rad/s (Figure 119).

Run from this folder:  python3 -m pytest test_imu_reader.py
"""
import os
import struct
import sys
import time
import types
from unittest import mock

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "microduck_rt"))

try:
    import serial  # noqa: F401
except ImportError:
    _serial = types.ModuleType("serial")
    _serial.Serial = None
    sys.modules["serial"] = _serial

import imu_reader  # noqa: E402
import pi_imu_uart  # noqa: E402
from imu_reader import (  # noqa: E402
    CHAN_CONTROL,
    CHAN_GYRO_RV,
    CHAN_REPORTS,
    GYRO_RV_REPORT_LEN,
    REPORT_ACCEL,
    REPORT_BASE_TIMESTAMP,
    REPORT_GAME_RV,
    REPORT_GYRO,
    REPORT_GYRO_INTEGRATED_RV,
    REPORT_RV,
    REPORT_TIMESTAMP_REBASE,
    IMUSnapshot,
    ThreadedIMUReader,
    _parse_gyro_rv,
    _parse_reports,
)

TICK = 100e-6


def base_record(delta_ticks):
    return bytes([REPORT_BASE_TIMESTAMP]) + struct.pack("<i", delta_ticks)


def rebase_record(delta_ticks):
    return bytes([REPORT_TIMESTAMP_REBASE]) + struct.pack("<i", delta_ticks)


def sensor_report(report_id, delay_ticks, fields, seq=0, accuracy=3):
    """Common 4-byte header (6.5.1) followed by int16 LE fields."""
    assert 0 <= delay_ticks <= 0x3FFF
    status = (accuracy & 0x03) | (((delay_ticks >> 8) & 0x3F) << 2)
    header = bytes([report_id, seq & 0xFF, status, delay_ticks & 0xFF])
    return header + struct.pack("<%dh" % len(fields), *fields)


# Q14 quaternion (i, j, k, real) and Q9 gyro / Q8 accel raw values chosen so the scaled floats are exact.
GRV_RAW = (4096, -8192, 2048, 12288)  # i=0.25 j=-0.5 k=0.125 real=0.75
GRV_WXYZ = (0.75, 0.25, -0.5, 0.125)
GYRO_RAW = (512, -256, 64)  # 1.0, -0.5, 0.125 rad/s
GYRO_SI = (1.0, -0.5, 0.125)
ACC_RAW = (0, -128, 2509)  # 0, -0.5, 9.80078125 m/s2
ACC_SI = (0.0, -0.5, 9.80078125)


def test_base_delta_plus_report_delay():
    # Base 20 ticks before HINT; GRV sampled 5 ticks after the base, gyro 12 ticks after it.
    payload = (base_record(20)
               + sensor_report(REPORT_GAME_RV, 5, GRV_RAW)
               + sensor_report(REPORT_GYRO, 12, GYRO_RAW))
    got = _parse_reports(payload)
    assert got["quat"] == GRV_WXYZ
    assert got["gyro"] == GYRO_SI
    assert got["quat_delay_s"] == pytest.approx((20 - 5) * TICK)  # 1.5 ms old at data-ready
    assert got["gyro_delay_s"] == pytest.approx((20 - 12) * TICK)  # 0.8 ms old


def test_delay_msbs_live_in_status_bits_7_2():
    # 300 ticks = 0x12C: status byte = accuracy 3 | (1 << 2) = 0x07, delay LSB = 0x2C.
    rpt = sensor_report(REPORT_GAME_RV, 300, GRV_RAW)
    assert rpt[2] == 0x07 and rpt[3] == 0x2C
    got = _parse_reports(base_record(400) + rpt)
    assert got["quat_delay_s"] == pytest.approx((400 - 300) * TICK)  # 10 ms
    # Accuracy bits do not leak into the delay.
    rpt0 = sensor_report(REPORT_GAME_RV, 300, GRV_RAW, accuracy=0)
    assert _parse_reports(base_record(400) + rpt0)["quat_delay_s"] == pytest.approx(100 * TICK)


def test_spec_example_base_delta_10_is_1ms_before_hint():
    # 7.2.1: "delta of 10 ... relative to t - 1 ms"; a report with delay 0 is therefore 1 ms old at HINT.
    got = _parse_reports(base_record(10) + sensor_report(REPORT_GAME_RV, 0, GRV_RAW))
    assert got["quat_delay_s"] == pytest.approx(1e-3)


def test_sign_sample_before_interrupt_is_positive_delay():
    # Sample 50 ticks before HINT: offset relative to HINT is -5 ms, so the delay (age) is +5 ms.
    got = _parse_reports(base_record(50) + sensor_report(REPORT_GYRO, 0, GYRO_RAW))
    assert got["gyro_delay_s"] > 0
    assert -got["gyro_delay_s"] == pytest.approx(-50 * TICK)
    # Report delay beyond the base (sample later than the base) brings it closer to HINT.
    got = _parse_reports(base_record(50) + sensor_report(REPORT_GYRO, 30, GYRO_RAW))
    assert got["gyro_delay_s"] == pytest.approx(20 * TICK)


def test_without_base_record_uses_report_delay_only():
    # No 0xFB: base = HINT (as CEVA sh2.c, referenceDelta starts at 0), so only the report's own delay counts.
    got = _parse_reports(sensor_report(REPORT_GAME_RV, 3, GRV_RAW) + sensor_report(REPORT_GYRO, 0, GYRO_RAW))
    assert got["quat"] == GRV_WXYZ
    assert got["quat_delay_s"] == pytest.approx(-3 * TICK)
    assert got["gyro_delay_s"] == 0.0


def test_timestamp_rebase_spec_example():
    # 7.2.2: HINT 5.0 s, base delta 4.0 s, rebase 1.5 s, report delay 1.0 s => sample at 3.5 s, 1.5 s old.
    payload = (base_record(40000) + rebase_record(15000)
               + sensor_report(REPORT_GYRO, 10000, GYRO_RAW))
    got = _parse_reports(payload)
    assert got["gyro_delay_s"] == pytest.approx(1.5)


def test_base_delta_overflow_marker_ignored():
    got = _parse_reports(base_record(0x7FFFFFFF) + sensor_report(REPORT_GAME_RV, 7, GRV_RAW))
    assert got["quat_delay_s"] == pytest.approx(-7 * TICK)


def test_existing_value_parsing_unchanged():
    payload = (base_record(0)
               + sensor_report(REPORT_GAME_RV, 0, GRV_RAW)
               + sensor_report(REPORT_GYRO, 0, GYRO_RAW)
               + sensor_report(REPORT_ACCEL, 0, ACC_RAW))
    got = _parse_reports(payload)
    assert got["quat"] == GRV_WXYZ  # (w, x, y, z) from the wire order (i, j, k, real)
    assert got["gyro"] == GYRO_SI
    assert got["acc"] == ACC_SI
    assert got["quat_delay_s"] == got["gyro_delay_s"] == got["acc_delay_s"] == 0.0
    # Rotation Vector (0x05) is 14 bytes: the gyro after it still parses.
    rv = sensor_report(REPORT_RV, 0, GRV_RAW + (100,))
    assert len(rv) == 14
    got = _parse_reports(rv + sensor_report(REPORT_GYRO, 0, GYRO_RAW))
    assert got["quat"] == GRV_WXYZ and got["gyro"] == GYRO_SI
    # Unknown bytes are skipped one at a time, as before.
    assert _parse_reports(b"\x00\x00" + sensor_report(REPORT_GYRO, 0, GYRO_RAW))["gyro"] == GYRO_SI
    assert _parse_reports(b"") == {}


def test_snapshot_default_sensor_delay_keeps_old_constructor_calls_working():
    snap = IMUSnapshot(1.0, (1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), True, 0)
    assert snap.sensor_delay_s == 0.0


class FakeBNO:
    def __init__(self, packets):
        self.packets = list(packets)

    def read_packet(self):
        return self.packets.pop(0) if self.packets else None

    def close(self):
        pass


def _reader_with(packets):
    with mock.patch.object(imu_reader, "_find_bno08x", return_value=(1, 0x4A)), \
            mock.patch.object(imu_reader, "_BNO08x", lambda bus, addr: FakeBNO(packets)):
        return ThreadedIMUReader(i2c_bus=1, frequency_hz=100.0)


def test_threaded_reader_snapshot_and_status_delay():
    # Three packets: GRV+gyro (quat delay wins), gyro only (gyro delay), GRV with a different delay.
    pk1 = base_record(30) + sensor_report(REPORT_GAME_RV, 10, GRV_RAW) + sensor_report(REPORT_GYRO, 0, GYRO_RAW)
    pk2 = base_record(60) + sensor_report(REPORT_GYRO, 0, GYRO_RAW)
    pk3 = base_record(40) + sensor_report(REPORT_GAME_RV, 0, GRV_RAW)
    reader = _reader_with([(imu_reader.CHAN_REPORTS, pk1), (imu_reader.CHAN_REPORTS, pk2),
                           (imu_reader.CHAN_REPORTS, pk3)])
    t0 = time.perf_counter()
    reader._thread.start()  # skip _configure (hardware reset + sleeps); the loop itself is under test
    try:
        deadline = time.time() + 2.0
        while time.time() < deadline and len(reader._delay_hist) < 3:
            time.sleep(0.005)
        snap = reader.get_latest()
        status = reader.get_status()
    finally:
        reader.stop()
    assert snap.valid
    assert snap.quat == pytest.approx(imu_reader._normalize_quat(GRV_WXYZ))
    assert snap.gyro == GYRO_SI
    assert t0 <= snap.timestamp_s <= time.perf_counter()  # host read time, unchanged meaning
    assert snap.sensor_delay_s == pytest.approx(40 * TICK)
    delays = [(30 - 10) * TICK, 60 * TICK, 40 * TICK]
    assert status["sensor_delay_s"] == pytest.approx(40 * TICK)
    assert status["sensor_delay_mean_s"] == pytest.approx(sum(delays) / 3)
    assert status["sensor_delay_max_s"] == pytest.approx(60 * TICK)


def test_status_delay_window_is_one_second():
    reader = _reader_with([])
    now = time.perf_counter()
    with reader._lock:
        reader._delay_hist.extend([(now - 1.5, 0.050), (now - 0.5, 0.002), (now - 0.1, 0.004)])
    status = reader.get_status()
    assert status["sensor_delay_mean_s"] == pytest.approx(0.003)
    assert status["sensor_delay_max_s"] == pytest.approx(0.004)
    reader.stop()


def test_frame_age_adds_sensor_delay_unless_raw():
    snap = IMUSnapshot(100.0, (1.0, 0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), True, 0,
                       sensor_delay_s=0.0035)
    assert pi_imu_uart.frame_age_s(snap, 100.002) == pytest.approx(0.0055)
    assert pi_imu_uart.frame_age_s(snap, 100.002, raw_age=True) == pytest.approx(0.002)
    # Same wire format as before.
    payload = struct.pack(pi_imu_uart.PAYLOAD_FMT, 1, *snap.quat, *snap.gyro, *snap.acc,
                          pi_imu_uart.frame_age_s(snap, 100.002), 1)
    assert len(payload) == 49
    assert struct.unpack(pi_imu_uart.PAYLOAD_FMT, payload)[11] == pytest.approx(0.0055)


# --- Gyro-Integrated Rotation Vector (0x2A) on the gyroRV channel, SH-2 6.5.44 -------------------------------------

# Q10 angular velocity raw values chosen so the scaled floats are exact: 1024 -> 1.0 rad/s, -512 -> -0.5, 128 -> 0.125.
GIRV_ANGVEL_RAW = (1024, -512, 128)
GIRV_ANGVEL_SI = (1.0, -0.5, 0.125)


def gyro_rv_report(quat_ijkr=GRV_RAW, angvel=GIRV_ANGVEL_RAW):
    """Figure 119: i j k real (Q14) then angular velocity x y z (Q10), int16 LE, no header of any kind."""
    rpt = struct.pack("<7h", *quat_ijkr, *angvel)
    assert len(rpt) == GYRO_RV_REPORT_LEN == 14
    return rpt


def test_gyro_rv_packet_parses_quaternion_and_angular_velocity():
    got = _parse_gyro_rv(gyro_rv_report())
    assert got["quat"] == GRV_WXYZ  # (w, x, y, z) from wire order (i, j, k, real), same as 0x08
    assert got["gyro"] == GIRV_ANGVEL_SI  # Q10, not the Q9 of report 0x02
    # No delay field in this report: the age is unknown and reported as 0.
    assert got["quat_delay_s"] == 0.0 and got["gyro_delay_s"] == 0.0
    # Q point check against 0x02: the same raw int16 means half the rate in 0x2A.
    same_raw = _parse_reports(sensor_report(REPORT_GYRO, 0, (1024, 0, 0)))["gyro"][0]
    assert same_raw == 2.0 and got["gyro"][0] == 1.0


def test_gyro_rv_packet_has_no_report_id_and_is_not_a_normal_channel_report():
    rpt = gyro_rv_report()
    assert rpt[0] != REPORT_GYRO_INTEGRATED_RV  # byte 0 is the quaternion i LSB, not an ID
    # Fed to the normal-channel parser it must not be mistaken for a 0x08/0x02 report: nothing decodes.
    assert "quat" not in _parse_reports(rpt) and "gyro" not in _parse_reports(rpt)


def test_gyro_rv_newest_report_wins_and_partial_tail_ignored():
    older = gyro_rv_report(quat_ijkr=(0, 0, 0, 16384), angvel=(0, 0, 0))  # identity, still
    newer = gyro_rv_report()
    got = _parse_gyro_rv(older + newer + b"\x01\x02\x03")  # sh2.c walks 14-byte steps; a short tail is garbage
    assert got["quat"] == GRV_WXYZ and got["gyro"] == GIRV_ANGVEL_SI
    assert _parse_gyro_rv(b"") == {}
    assert _parse_gyro_rv(b"\x00" * 13) == {}


class FakeBNOConfigurable(FakeBNO):
    """FakeBNO that also records the control-channel traffic of _configure()."""

    def __init__(self, packets):
        super().__init__(packets)
        self.sent = []  # (channel, payload bytes)

    def send(self, channel, data):
        self.sent.append((channel, bytes(data)))

    def enable_feature(self, report_id, interval_us):
        imu_reader._BNO08x.enable_feature(self, report_id, interval_us)

    def enabled_ids(self):
        # Set Feature Command 0xFD on the control channel: byte 1 = feature report ID (SH-2 6.5.4, Figure 78).
        return [p[1] for ch, p in self.sent if ch == CHAN_CONTROL and p[0] == imu_reader.SET_FEATURE]


def _configurable_reader(rv_report=None):
    kwargs = {} if rv_report is None else {"rv_report": rv_report}
    with mock.patch.object(imu_reader, "_find_bno08x", return_value=(1, 0x4A)), \
            mock.patch.object(imu_reader, "_BNO08x", lambda bus, addr: FakeBNOConfigurable([])):
        return ThreadedIMUReader(i2c_bus=1, frequency_hz=100.0, **kwargs)


def test_game_mode_is_default_and_enables_the_same_three_reports_as_before():
    reader = _configurable_reader()
    assert reader.rv_report == "game"
    assert reader.get_status()["rv_report"] == "game"
    with mock.patch.object(imu_reader.time, "sleep"):
        reader._configure()
    assert reader._imu.enabled_ids() == [REPORT_GAME_RV, REPORT_GYRO, REPORT_ACCEL]
    interval = struct.unpack_from("<I", reader._imu.sent[-1][1], 5)[0]
    assert interval == 10_000  # 100 Hz in microseconds
    reader.stop()


def test_gyro_integrated_mode_enables_0x2a_and_accel_only():
    reader = _configurable_reader("gyro_integrated")
    assert reader.get_status()["rv_report"] == "gyro_integrated"
    with mock.patch.object(imu_reader.time, "sleep"):
        reader._configure()
    # 6.5.44.1: controlled with ID 0x2A on the control channel; gyro comes inside that report, so no 0x02.
    assert reader._imu.enabled_ids() == [REPORT_GYRO_INTEGRATED_RV, REPORT_ACCEL]
    assert REPORT_GYRO not in reader._imu.enabled_ids()
    reader.stop()


def test_unknown_rv_report_rejected():
    with pytest.raises(ValueError):
        _configurable_reader("arvr")


def test_threaded_reader_gyro_integrated_mode_fills_snapshot_from_channel_5():
    acc_pk = base_record(30) + sensor_report(REPORT_ACCEL, 0, ACC_RAW)
    girv_old = gyro_rv_report(quat_ijkr=(0, 0, 0, 16384), angvel=(0, 0, 0))
    girv_new = gyro_rv_report()
    packets = [(CHAN_REPORTS, acc_pk), (CHAN_GYRO_RV, girv_old), (CHAN_GYRO_RV, girv_new)]
    with mock.patch.object(imu_reader, "_find_bno08x", return_value=(1, 0x4A)), \
            mock.patch.object(imu_reader, "_BNO08x", lambda bus, addr: FakeBNO(packets)):
        reader = ThreadedIMUReader(i2c_bus=1, frequency_hz=100.0, rv_report="gyro_integrated")
    reader._thread.start()  # skip _configure; the loop and channel routing are under test
    try:
        deadline = time.time() + 2.0
        while time.time() < deadline and len(reader._delay_hist) < 3:
            time.sleep(0.005)
        snap = reader.get_latest()
        status = reader.get_status()
    finally:
        reader.stop()
    assert snap.valid
    assert snap.quat == pytest.approx(imu_reader._normalize_quat(GRV_WXYZ))
    assert snap.gyro == GIRV_ANGVEL_SI  # from the 0x2A angular velocity, rad/s
    assert snap.acc == ACC_SI  # accel still arrives on the normal channel
    assert snap.sensor_delay_s == 0.0  # 0x2A carries no timestamp
    assert status["rv_report"] == "gyro_integrated"
    # Three snapshots were recorded; an accel-only packet records 0 (quat/gyro delay only, unchanged behaviour)
    # and the 0x2A packets have no delay field, so the window holds only zeros.
    assert len(reader._delay_hist) == 3 and status["sensor_delay_max_s"] == 0.0


def test_game_mode_loop_unchanged_by_channel_routing():
    # Same packets as test_threaded_reader_snapshot_and_status_delay plus a control-channel packet that must be
    # ignored (no snapshot, no delay record).
    pk1 = base_record(30) + sensor_report(REPORT_GAME_RV, 10, GRV_RAW) + sensor_report(REPORT_GYRO, 0, GYRO_RAW)
    reader = _reader_with([(CHAN_CONTROL, b"\xfc\x08" + b"\x00" * 15), (CHAN_REPORTS, pk1)])
    reader._thread.start()
    try:
        deadline = time.time() + 2.0
        while time.time() < deadline and len(reader._delay_hist) < 1:
            time.sleep(0.005)
        time.sleep(0.03)
        snap = reader.get_latest()
    finally:
        reader.stop()
    assert len(reader._delay_hist) == 1
    assert snap.quat == pytest.approx(imu_reader._normalize_quat(GRV_WXYZ)) and snap.gyro == GYRO_SI
    assert snap.sensor_delay_s == pytest.approx(20 * TICK)


class SteadyThenSilentBNO(FakeBNO):
    """Returns one GIRV packet per read for `steady_s`, then nothing (the BNO reset case)."""

    def __init__(self, steady_s):
        super().__init__([])
        self.t_end = time.perf_counter() + steady_s

    def read_packet(self):
        if time.perf_counter() < self.t_end:
            return (CHAN_GYRO_RV, gyro_rv_report())
        return None


def test_stale_detection_in_gyro_integrated_mode():
    # While 0x2A packets flow (and 0x02 is off), both last_q and last_g refresh: no false "stale" for > 0.5 s.
    # Once they stop, the 0.5 s watchdog marks the snapshot invalid and calls _configure() again.
    with mock.patch.object(imu_reader, "_find_bno08x", return_value=(1, 0x4A)), \
            mock.patch.object(imu_reader, "_BNO08x", lambda bus, addr: SteadyThenSilentBNO(0.7)):
        reader = ThreadedIMUReader(i2c_bus=1, frequency_hz=100.0, rv_report="gyro_integrated")
    reconfigs = []
    reader._configure = lambda: reconfigs.append(time.perf_counter())
    reader._thread.start()
    try:
        time.sleep(0.6)
        assert reader.get_latest().valid and not reconfigs  # streaming: never declared stale
        deadline = time.time() + 2.0
        while time.time() < deadline and not reconfigs:
            time.sleep(0.01)
        snap = reader.get_latest()
    finally:
        reader.stop()
    assert reconfigs, "stale watchdog did not re-enable the reports"
    assert not snap.valid
    assert snap.gyro == GIRV_ANGVEL_SI  # last good values kept, flagged invalid


def test_cli_rv_report_flag_defaults_to_game():
    ap = pi_imu_uart.build_parser()
    assert ap.parse_args([]).rv_report == "game"
    assert ap.parse_args(["--rv-report", "gyro_integrated"]).rv_report == "gyro_integrated"
    with pytest.raises(SystemExit):
        ap.parse_args(["--rv-report", "arvr"])


def test_raw_gyro_report_parses_counts_and_rides_in_acc_slot():
    import struct
    from imu_reader import REPORT_RAW_GYRO, _parse_reports
    rep = bytes([REPORT_RAW_GYRO, 1, 0, 0]) + struct.pack("<hhhhI", -120, 45, 7, 2300, 123456)
    got = _parse_reports(rep)
    assert got["raw_gyro"] == (-120.0, 45.0, 7.0)
    assert "gyro" not in got and "acc" not in got
