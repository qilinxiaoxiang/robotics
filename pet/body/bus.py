"""Live Dynamixel bus access through dynamixel-sdk (protocol 2.0): scan for the inspector, poll for the health check.
Nothing here writes to a servo except `babble_move`, which the inspector calls only with --babble --i-am-watching."""
from . import dxl_models
from .dxl_models import REG


def _open(port, baud):
    from dynamixel_sdk import PacketHandler, PortHandler
    ph, pk = PortHandler(port), PacketHandler(2.0)
    if not ph.openPort() or not ph.setBaudRate(baud):
        raise OSError(f"cannot open {port} at {baud}")
    return ph, pk


def _read(pk, ph, dxl_id, reg):
    from dynamixel_sdk import COMM_SUCCESS
    addr, size = REG[reg]
    fn = {1: pk.read1ByteTxRx, 2: pk.read2ByteTxRx, 4: pk.read4ByteTxRx}[size]
    val, res, err = fn(ph, dxl_id, addr)
    if res != COMM_SUCCESS:
        return None
    if size == 4 and val >= 2 ** 31:
        val -= 2 ** 32
    return val


def scan(port, baud, ids=None):
    """Broadcast ping (or ping `ids`), then read each answering servo's identity, limits and state. Read-only."""
    from dynamixel_sdk import COMM_SUCCESS
    ph, pk = _open(port, baud)
    try:
        if ids is None:
            found, res = pk.broadcastPing(ph)
            found = {i: v[0] for i, v in found.items()} if res == COMM_SUCCESS else {}
        else:
            found = {}
            for i in ids:
                model, res, _ = pk.ping(ph, i)
                if res == COMM_SUCCESS:
                    found[i] = model
        motors = []
        for i, model in sorted(found.items()):
            m = dict(id=i, model=model)
            for reg in ("operating_mode", "hardware_error", "min_position_limit", "max_position_limit", "present_input_voltage",
                        "present_temperature", "present_position"):
                m[reg] = _read(pk, ph, i, reg)
            m["voltage_v"] = None if m["present_input_voltage"] is None else m["present_input_voltage"] / 10
            motors.append(m)
        volts = [m["voltage_v"] for m in motors if m["voltage_v"]]
        return dict(port=port, baud=baud, voltage_v=max(volts) if volts else None, motors=motors)
    finally:
        ph.closePort()


class BusPoller:
    """One health poll per call: for each id, did it answer, its hardware-error byte, its present load or current."""

    def __init__(self, port, baud, models):
        self.ph, self.pk = _open(port, baud)
        self.models = models  # id -> model number

    def poll(self):
        out = {}
        for i, model in self.models.items():
            err = _read(self.pk, self.ph, i, "hardware_error")
            raw = _read(self.pk, self.ph, i, "present_126") if err is not None else None
            if raw is not None and raw >= 2 ** 15:
                raw -= 2 ** 16
            spec = dxl_models.MODELS.get(model, {})
            out[i] = dict(replied=err is not None, hw_error=err or 0,
                          present=None if raw is None else raw * spec.get("unit_126", 1.0), present_kind=spec.get("present_126"))
        return out

    def close(self):
        self.ph.closePort()


def babble_joint(port, baud, dxl_id, amps, kp, sample, settle_s=0.5, abort_tilt_deg=6.0, grow_tilt_deg=3.0):
    """Move one servo +A, -A and home at P gain `kp`, A growing through `amps` while the trunk tilt stays under
    `grow_tilt_deg`; abort to home past `abort_tilt_deg`. `sample()` returns (gravity_body, gyro, image_change or None).
    The servo's own P gain and goal are restored. Torque must already be on (the robot standing in stand mode)."""
    import math
    import time
    ph, pk = _open(port, baud)
    addr_goal = REG["goal_position"][0]
    addr_p = REG["position_p_gain"][0]
    home = _read(pk, ph, dxl_id, "present_position")
    p0 = _read(pk, ph, dxl_id, "position_p_gain")
    if home is None or p0 is None:
        ph.closePort()
        raise OSError(f"ID {dxl_id} did not answer")
    try:
        pk.write2ByteTxRx(ph, dxl_id, addr_p, kp)
        kept = None
        for amp in amps:
            tr = dict(commanded_rad=amp, babble=True, t=[], q=[], gb=[], gyro=[], img_change=[])
            g0, aborted, t0 = None, False, time.monotonic()
            for frac in (1.0, -1.0, 0.0):
                pk.write4ByteTxRx(ph, dxl_id, addr_goal, int(round(home + frac * amp * dxl_models.TICKS / (2 * math.pi))) & 0xFFFFFFFF)
                end = time.monotonic() + settle_s
                while time.monotonic() < end:
                    g, w, img = sample()
                    pos = _read(pk, ph, dxl_id, "present_position")
                    g0 = g0 or g
                    tr["t"].append(round(time.monotonic() - t0, 3))
                    tr["q"].append(dxl_models.tick_to_rad(pos if pos is not None else home))
                    tr["gb"].append(list(g))
                    tr["gyro"].append(list(w))
                    tr["img_change"].append(img)
                    dot = sum(a * b for a, b in zip(g, g0))
                    if math.degrees(math.acos(max(-1.0, min(1.0, dot)))) > abort_tilt_deg:
                        aborted = True
                        break
                if aborted:
                    pk.write4ByteTxRx(ph, dxl_id, addr_goal, home & 0xFFFFFFFF)
                    time.sleep(settle_s)
                    tr["aborted"] = True
                    break
            if any(v is None for v in tr["img_change"]):
                tr["img_change"] = None
            if kept is None or not aborted:
                kept = tr
            tilt = max(math.degrees(math.acos(max(-1.0, min(1.0, sum(a * b for a, b in zip(g, tr["gb"][0])))))) for g in tr["gb"])
            if aborted or tilt >= grow_tilt_deg:
                break
        return kept
    finally:  # back to the servo's own goal and gain whatever happened
        pk.write4ByteTxRx(ph, dxl_id, addr_goal, home & 0xFFFFFFFF)
        pk.write2ByteTxRx(ph, dxl_id, addr_p, p0)
        ph.closePort()
