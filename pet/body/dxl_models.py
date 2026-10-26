"""Dynamixel X-series facts the inspector needs: model numbers, stall torque, control-table addresses.

Stall torques and addresses are from the ROBOTIS e-manual pages (read 2026-10-26):
https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/, .../xl330-m077/, .../xl430-w250/, .../xm430-w350/, .../xm430-w210/.
Model numbers 1200/1190/1060 match the read-only OMX scan (omx-local/evidence/hardware-check.json) and
omx-local/current_state_probe.py; 1020/1030 are the e-manual XM430 values.
"""
import math

TICKS = 4096  # one turn in position mode
CENTER = 2048

# model number -> name, published (volts, stall N m) points, what register 126 holds and its unit
MODELS = {
    1200: dict(name="XL330-M288", stall=[(3.7, 0.42), (5.0, 0.52), (6.0, 0.60)], present_126="current", unit_126=1.0),
    1190: dict(name="XL330-M077", stall=[(5.0, 0.228)], present_126="current", unit_126=1.0),
    1060: dict(name="XL430-W250", stall=[(9.0, 1.0), (11.1, 1.4), (12.0, 1.5)], present_126="load", unit_126=0.1),
    1020: dict(name="XM430-W350", stall=[(11.1, 3.8), (12.0, 4.1), (14.8, 4.8)], present_126="current", unit_126=2.69),
    1030: dict(name="XM430-W210", stall=[(12.0, 3.0)], present_126="current", unit_126=2.69),
}

# control-table addresses shared by these models (X series, protocol 2.0): (address, bytes)
REG = dict(model=(0, 2), operating_mode=(11, 1), homing_offset=(20, 4), temperature_limit=(31, 1), max_voltage=(32, 2),
           min_voltage=(34, 2), pwm_limit=(36, 2), max_position_limit=(48, 4), min_position_limit=(52, 4),
           torque_enable=(64, 1), hardware_error=(70, 1), position_p_gain=(84, 2), goal_position=(116, 4),
           present_126=(126, 2), present_position=(132, 4), present_input_voltage=(144, 2), present_temperature=(146, 1))

# register 70 bits (e-manual "Hardware Error Status")
HW_ERROR_BITS = {0: "input_voltage", 2: "overheating", 3: "motor_encoder", 4: "electrical_shock", 5: "overload"}


def model_name(number):
    return MODELS[number]["name"] if number in MODELS else f"unknown-{number}"


def stall_torque(number, volts=None):
    """Stall torque (N m) at `volts`, linear between the published points and clamped to their range (no
    extrapolation past the highest published voltage). None for an unknown model."""
    m = MODELS.get(number)
    if m is None:
        return None
    pts = m["stall"]
    if volts is None:  # the recommended point: the middle published one where there are three
        return pts[len(pts) // 2][1]
    if len(pts) == 1:
        return pts[0][1]
    if volts <= pts[0][0]:
        return pts[0][1]
    if volts >= pts[-1][0]:
        return pts[-1][1]
    for (v0, t0), (v1, t1) in zip(pts, pts[1:]):
        if v0 <= volts <= v1:
            return round(t0 + (t1 - t0) * (volts - v0) / (v1 - v0), 3)
    return None


def above_published(number, volts):
    m = MODELS.get(number)
    return m is not None and volts is not None and volts > m["stall"][-1][0]


def tick_to_rad(tick):
    """Position tick to rad about the servo centre (2048 = 0)."""
    return (tick - CENTER) * 2 * math.pi / TICKS


def hw_error_names(byte):
    return [name for bit, name in HW_ERROR_BITS.items() if byte >> bit & 1]
