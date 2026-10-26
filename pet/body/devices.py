"""Sensor enumeration: live on the robot's Linux host (V4L2, ALSA, I2C), or from the body's CURRENT-STATE.json for a
dry run. Every function returns (sensors, notes) in body-card form."""
import fcntl
import glob
import os
import re
import subprocess

from .profiles import PROFILES, state_facts

I2C_SLAVE = 0x0703
# address -> (kind, id, what); the duck's IMU and touch board addresses are CURRENT-STATE facts a7z_imu_bus, a7z_touch_bus
I2C_KNOWN = {0x4A: ("imu", "bno085", "BNO085 IMU"), 0x4B: ("imu", "bno085", "BNO085 IMU (alternate address)"),
             0x2A: ("touch", "xiao_touch", "XIAO ESP32-S3 touch pad board"), 0x29: ("range", "vl53", "VL53 time-of-flight")}


def cameras():
    out, seen = [], set()
    for dev in sorted(glob.glob("/sys/class/video4linux/video*")):
        name = open(os.path.join(dev, "name")).read().strip() if os.path.exists(os.path.join(dev, "name")) else "?"
        index = open(os.path.join(dev, "index")).read().strip() if os.path.exists(os.path.join(dev, "index")) else "0"
        if index != "0" or name in seen:  # a UVC camera exposes a metadata node too (index 1)
            continue
        seen.add(name)
        out.append(dict(kind="camera", id=f"/dev/{os.path.basename(dev)}", notes=f"V4L2 '{name}'"))
    return out


def mics():
    try:
        txt = subprocess.run(["arecord", "-l"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [dict(kind="mic", id=f"hw:{c},{d}", notes=f"ALSA capture '{name.strip()}'")
            for c, name, d in re.findall(r"card (\d+): ([^\[]+)\[.*?device (\d+):", txt)]


def i2c_probe(buses=None):
    out = []
    for path in sorted(glob.glob("/dev/i2c-*")):
        bus = int(path.rsplit("-", 1)[1])
        if buses is not None and bus not in buses:
            continue
        for addr, (kind, sid, what) in I2C_KNOWN.items():
            try:
                fd = os.open(path, os.O_RDWR)
            except OSError:
                break
            try:
                fcntl.ioctl(fd, I2C_SLAVE, addr)
                os.read(fd, 1)  # a plain read: ACKed only when a device sits at that address
                out.append(dict(kind=kind, id=f"{sid}@i2c-{bus}:0x{addr:02X}", notes=what))
            except OSError:
                pass
            finally:
                os.close(fd)
    return out


def imu_sample(bus):
    """One quaternion from a BNO085 through the reader guide/firmware/pi/imu_read.py uses; None if unavailable."""
    try:
        from adafruit_bno08x import BNO_REPORT_ROTATION_VECTOR
        from adafruit_bno08x.i2c import BNO08X_I2C
        from adafruit_extended_bus import ExtendedI2C
        bno = BNO08X_I2C(ExtendedI2C(bus), address=0x4A)
        bno.enable_feature(BNO_REPORT_ROTATION_VECTOR)
        return bno.quaternion
    except Exception:
        return None


def live(i2c_buses=None):
    sensors = cameras() + mics() + i2c_probe(i2c_buses)
    notes = []
    for s in sensors:
        if s["kind"] == "imu" and "@i2c-" in s["id"]:
            q = imu_sample(int(s["id"].split("@i2c-")[1].split(":")[0]))
            s["notes"] += "; streams" if q else "; answers, no sample through adafruit_bno08x"
    if not any(s["kind"] == "imu" for s in sensors):
        notes.append("no IMU found on I2C: balance policies cannot run")
    return sensors, notes


def from_state(profile):
    """Sensors of a known body from its CURRENT-STATE.json (dry run and sim)."""
    facts = state_facts(PROFILES[profile]["state"])
    rel = os.path.relpath(PROFILES[profile]["state"], os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    sensors, notes = [], []
    if profile == "microduck":
        sensors.append(dict(kind="imu", id="bno085@i2c-7:0x4A", notes=f"trunk IMU ({rel} a7z_imu_bus)"))
        sensors.append(dict(kind="touch", id="xiao_touch@i2c-0:0x2A", notes=f"five head pads L1 R1 L2 R2 M ({rel} a7z_touch_bus)"))
        parts = facts["parts_a7z_extensions"]["value"]
        cam = parts.get("innomaker_u20cam", {})
        if "fitted" in cam.get("status", ""):
            sensors.append(dict(kind="camera", id="u20cam", notes=f"Innomaker U20CAM-720P on the face, USB to the A7Z ({rel} parts_a7z_extensions)"))
        else:
            notes.append(f"camera not fitted: {cam.get('status', 'no record')}")
        mic = parts.get("inmp441_mics", {})
        if "fitted" in mic.get("status", ""):
            sensors.append(dict(kind="mic", id="inmp441", notes=f"I2S microphones ({rel} parts_a7z_extensions)"))
        else:
            notes.append(f"no microphones on the body yet: INMP441 {mic.get('status', 'no record')} ({rel} parts_a7z_extensions); "
                         "no sound events until they are fitted")
        notes.append("speaker in the head (output only; quack calls through walk_wired.py)")
    elif profile == "omx_arm":
        cam = facts.get("camera_intrinsics")
        if cam:
            v = cam["value"]
            sensors.append(dict(kind="camera", id="wrist_cam", notes=f"wrist camera, fx {v['fx']} fy {v['fy']} ({rel} camera_intrinsics)"))
        notes.append("no IMU, microphone or touch sensor on the arm; servo load is its only sense of contact")
    return sensors, notes
