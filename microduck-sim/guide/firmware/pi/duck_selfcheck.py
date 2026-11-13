"""MicroDuck A7Z boot self-check: IMU, touch board, camera, servos, speaker and the three microphones.

Runs once per boot from duck-selfcheck.service (/home/radxa/rt/microduck-sim/guide/firmware/pi/duck_selfcheck.py, as
radxa) and again on request from the phone app. Writes /home/radxa/duck-logs/selfcheck/latest.json and appends the same
record to history.jsonl; the app's a7z bridge reads latest.json. Exit code 0 when no item failed.

Items (ok true = green, false = red, null = skipped or not fitted, each with an English detail line for the app):
  imu      BNO085 at 0x4A on i2c-7 (CURRENT-STATE a7z_imu_bus): accelerometer magnitude 8.0-11.6 m/s2 within 4 s
  touch    XIAO at 0x2A on the TWI0 bus (a7z_touch_bus): 24-byte block, five counts below 4194303, sequence advancing
  camera   U20CAM on USB and a7z_cam.py publishing frames to /dev/shm/a7z_cam.bgr (frame index advancing, not black)
  servos   IDs 1-15 answer a ping on /dev/ttyAS2 at 500 kbaud (servo_bus_hosts); reports the lowest input voltage
  audio    a 0.5 s 1.5-3 kHz sweep from the speaker (MAX98357A, DOUT0) while I2S0 records 4 channels
           (a7z_audio_capture): speaker ok when any microphone hears the sweep 15 dB over its own floor; each
           microphone ok when it hears it; the back microphone (ch2) reads all zero when it is not fitted (null)
The IMU and servo checks hold the robot I/O lock (/tmp/duck-hw.lock, shared with walk_wired.py and duck_sense.py).
duck_sense.py, the phone app's standby reader, quits within 0.5 s when it sees this script running, so the check waits up
to 4 s for the lock; a brain (walk_wired.py) keeps it and both checks are skipped and named. The touch board is read even
while the app's touch thread has the bus open: each 24-byte read is one kernel I2C transaction. A sound stream another
process holds skips the audio check. Pings and reads change no servo register, so torque and goals stay as they are.
The sweep plays at -10.5 dBFS straight to the sndi2s0 hardware device in S32_LE: below the -3 dB softvol ceiling (D-012), and in the
capture's own sample format, since a 16-bit stream reconfigures the shared I2S0 and shifts the capture samples.

  python3 duck_selfcheck.py [--out DIR] [--skip imu,touch,camera,servos,audio]
"""
import argparse, fcntl, glob, json, os, struct, subprocess, sys, time, wave

OUT = "/home/radxa/duck-logs/selfcheck"
HW_LOCK = "/tmp/duck-hw.lock"
CARD = "sndi2s0"   # the I2S0 card's number changes between boots (HDMI is sometimes card 0): always by name
SHM = "/dev/shm/a7z_cam.bgr"
SERVO_PORT, SERVO_BAUD = "/dev/ttyAS2", 500_000
MIC_NAMES = ["Ear A (L/R to GND, channel 0)", "Ear B (L/R to VDD, channel 1)", "Back of head (pin 10, channel 2)"]


def holders(dev):
    """Names of other processes that have dev open."""
    me, names = os.getpid(), set()
    real = os.path.realpath(dev)
    for fd in glob.glob("/proc/[0-9]*/fd/*"):
        try:
            pid = int(fd.split("/")[2])
            if pid != me and os.path.realpath(fd) == real:
                with open(f"/proc/{pid}/cmdline", "rb") as f:
                    cmd = f.read().split(b"\0")
                names.add(next((os.path.basename(a.decode()) for a in cmd[1:] if a.endswith(b".py")),
                               os.path.basename(cmd[0].decode())))
        except (OSError, ValueError, IndexError):
            pass
    return sorted(names)


def take_hw_lock(wait_s=4.0):
    """The robot I/O lock, or None and the holders' names after wait_s."""
    f = open(HW_LOCK, "a")
    end = time.time() + wait_s
    while True:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return f, None
        except BlockingIOError:
            if time.time() > end:
                f.close()
                return None, holders(HW_LOCK) or ["another program"]
            time.sleep(0.2)


def check_imu():
    if not os.path.exists("/dev/i2c-7"):
        return {"ok": False, "detail": "No i2c-7 (TWI7 overlay not loaded)"}
    try:
        from adafruit_bno08x import BNO_REPORT_ACCELEROMETER
        from adafruit_bno08x.i2c import BNO08X_I2C
        from adafruit_extended_bus import ExtendedI2C
        bno = BNO08X_I2C(ExtendedI2C(7), address=0x4A)
        bno.enable_feature(BNO_REPORT_ACCELEROMETER)
        end, g = time.time() + 4.0, None
        while time.time() < end:
            ax, ay, az = bno.acceleration
            g = (ax * ax + ay * ay + az * az) ** 0.5
            if g > 1.0:
                break
            time.sleep(0.05)
    except Exception as e:  # the library raises plain RuntimeError/OSError subclasses
        return {"ok": False, "detail": imu_diagnosis() or f"Cannot read the IMU: {type(e).__name__} {e}"[:160]}
    if g is None or not 8.0 <= g <= 11.6:
        return {"ok": False, "detail": f"IMU answers, but gravity reads wrong: {g if g is None else round(g, 2)} m/s²"}
    return {"ok": True, "detail": f"Gravity {g:.2f} m/s²"}


def imu_diagnosis():
    """Tell a missing IMU from a stuck one with a plain 4-byte read (no zero-length write, which wedges TWI7)."""
    try:
        fd = os.open("/dev/i2c-7", os.O_RDWR)
        try:
            fcntl.ioctl(fd, 0x0703, 0x4A)
            head = os.read(fd, 4)
        finally:
            os.close(fd)
    except OSError:
        return "IMU does not answer (no reply at 0x4A): check pins 1, 3, 5, 9 and the IMU plug"
    if head == b"\0\0\0\0":
        return "IMU answers its address but sends no data (stuck): unplug the A7Z power for 5 s, then plug it back in (a reboot does not power-cycle the IMU)"
    return None


def touch_bus():
    for n in sorted(glob.glob("/sys/bus/i2c/devices/i2c-*")):
        if os.path.realpath(n + "/of_node").endswith("twi@2510000"):
            return "/dev/" + os.path.basename(n)
    return None


def touch_decode(raw):
    """The block from 24 read bytes, as duck-telemetry.py decodes it: the XIAO sometimes sends a filler byte first
    (then the block's last byte, the always-zero top byte of M, is lost); the wrong alignment puts every count above
    0x3FFFFF, so the right one is the one whose five counts all fit. None when neither does."""
    for block in (raw, raw[1:] + b"\0"):
        b = struct.unpack("<6I", block)
        if max(b[1:]) <= 0x3FFFFF:
            return b
    return None


def check_touch():
    dev = touch_bus()
    if dev is None:
        return {"ok": False, "detail": "No TWI0 bus (touch board overlay not loaded)"}
    blocks = []
    try:
        fd = os.open(dev, os.O_RDWR)
        try:
            fcntl.ioctl(fd, 0x0703, 0x2A)  # I2C_SLAVE
            for _ in range(2):
                blocks.append(touch_decode(os.read(fd, 24)))
                time.sleep(0.15)
        finally:
            os.close(fd)
    except OSError as e:
        return {"ok": False, "detail": f"Touch board (0x2A) does not answer: {e.strerror}"}
    if None in blocks:
        return {"ok": False, "detail": "Touch board answers, but the data does not decode (all readings out of range)"}
    counts = blocks[-1][1:]
    bad = [p for p, c in zip(["L1", "R1", "L2", "R2", "M"], counts) if c == 0 or c >= 4194303]
    if blocks[0][0] == blocks[1][0]:
        return {"ok": False, "detail": "Touch board answers, but the counter does not advance (scan stuck)"}
    if bad:
        return {"ok": False, "detail": f"Bad pad readings: {', '.join(bad)} (touching metal or a broken wire)"}
    return {"ok": True, "detail": "Five pads " + " ".join(str(c) for c in counts)}


def check_camera():
    usb = subprocess.run(["lsusb"], capture_output=True, text=True).stdout
    if "U20CAM" not in usb:
        return {"ok": False, "detail": "No camera on USB (U20CAM not connected or bad cable)"}

    def frame():
        try:
            with open(SHM, "rb") as f:
                data = f.read()
        except FileNotFoundError:
            return None
        return (struct.unpack_from("<Q", data)[0], data[16:]) if len(data) > 16 else None

    first = frame()
    if first is None:
        return {"ok": None, "detail": "Camera is on USB; the camera program is off (the app's switch is off), so no picture was taken"}
    time.sleep(1.5)
    last = frame()
    if last is None or last[0] == first[0]:
        return {"ok": False, "detail": "Camera program is running, but no new frame in 1.5 s"}
    mean = sum(last[1][::997]) / len(last[1][::997])
    if mean < 4:
        return {"ok": False, "detail": f"Frames are updating, but all black with only noise (mean brightness {mean:.0f}): lens facing down or covered"}
    return {"ok": True, "detail": f"Frames are updating, mean brightness {mean:.0f}"}


def check_servos():
    try:
        from dynamixel_sdk import COMM_SUCCESS, PacketHandler, PortHandler
    except ImportError:
        return {"ok": False, "detail": "dynamixel_sdk is missing"}
    port, packet = PortHandler(SERVO_PORT), PacketHandler(2.0)
    if not port.openPort() or not port.setBaudRate(SERVO_BAUD):
        return {"ok": False, "detail": f"Cannot open {SERVO_PORT}"}
    missing, volts = [], []
    try:
        for sid in range(1, 16):
            for _ in range(3):
                _, res, _ = packet.ping(port, sid)
                if res == COMM_SUCCESS:
                    v, res, _ = packet.read2ByteTxRx(port, sid, 144)  # present input voltage, 0.1 V
                    if res == COMM_SUCCESS:
                        volts.append(v / 10)
                    break
            else:
                missing.append(sid)
    finally:
        port.closePort()
    if len(missing) == 15:
        return {"ok": False, "detail": "None of the 15 servos answer (is servo power on? is the OpenRB connected?)"}
    if missing:
        return {"ok": False, "detail": f"Servos not answering: {', '.join(map(str, missing))}"}
    return {"ok": True, "detail": f"All 15 answer, {min(volts):.1f}-{max(volts):.1f} V" if volts else "All 15 answer"}


def sweep_wav(path, sr=48000):
    import numpy as np
    t = np.arange(int(0.5 * sr)) / sr
    y = (0.3 * np.sin(2 * np.pi * (1500 * t + 1500 * t * t)) * np.hanning(len(t)) * 2147483647).astype("<i4")
    pad = int(0.3 * sr)
    s = np.zeros((2 * pad + len(y), 2), "<i4")
    s[pad:pad + len(y), :] = y[:, None]
    with wave.open(path, "wb") as w:
        w.setnchannels(2), w.setsampwidth(4), w.setframerate(sr), w.writeframes(s.tobytes())


def check_audio():
    import numpy as np
    card = os.path.basename(os.path.realpath(f"/proc/asound/{CARD}"))   # e.g. card1
    if not card.startswith("card"):
        return {"ok": False, "detail": f"No {CARD} sound card (I2S0 overlay not loaded)"}, []
    pcm = glob.glob(f"/dev/snd/pcmC{card[4:]}D0*")
    held = sorted({n for p in pcm for n in holders(p)})
    if held:
        return {"ok": None, "detail": f"Skipped: the sound card is in use by {', '.join(held)}"}, []
    sweep, rec = "/tmp/duck_selfcheck_sweep.wav", "/tmp/duck_selfcheck_rec.wav"
    sweep_wav(sweep)
    r = subprocess.Popen(["arecord", "-q", "-D", f"hw:CARD={CARD},DEV=0", "-c", "4", "-r", "48000", "-f", "S32_LE", "-d", "3", rec],
                         stderr=subprocess.PIPE)
    time.sleep(0.8)
    p = subprocess.run(["aplay", "-q", "-D", f"hw:CARD={CARD},DEV=0", sweep], capture_output=True, text=True)
    err = r.communicate(timeout=10)[1].decode().strip()
    if r.returncode or p.returncode:
        return {"ok": False, "detail": f"Recording or playback failed: {(err or p.stderr).strip()[:120]}"}, []
    with wave.open(rec) as w:
        x = (np.frombuffer(w.readframes(w.getnframes()), "<i4").reshape(-1, 4) >> 8).astype(float)
    sr, blk = 48000, 2400
    f = np.fft.rfftfreq(blk, 1 / sr)
    band = (f > 1400) & (f < 3200)
    mics = []
    for ch in range(3):
        v = x[:, ch]
        if not v.any():
            mics.append({"ok": None if ch == 2 else False,
                         "detail": "All zeros: not fitted (optional)" if ch == 2 else "All zeros: no data on this channel (SD wire broken or unplugged)"})
            continue
        e = np.array([(np.abs(np.fft.rfft(v[i:i + blk] * np.hanning(blk)))[band] ** 2).sum()
                      for i in range(0, len(v) - blk, blk)])
        db = 10 * np.log10(np.maximum(e, 1))
        floor = np.median(np.r_[db[2:14], db[-12:]])  # before the sweep starts (1.1 s) and after it ends (1.6 s)
        heard = db[20:34].max() - floor               # blocks covering 1.0-1.7 s
        mics.append({"ok": bool(heard >= 15), "detail": f"Heard the beep {heard:.0f} dB above the noise floor" if heard >= 15 else
                     f"Did not hear the beep (only {heard:.0f} dB above the floor)"})
    any_heard = any(m["ok"] for m in mics)
    live = [m for m in mics if m["ok"] is not None]
    speaker = ({"ok": True, "detail": "A microphone heard the beep it played"} if any_heard else
               {"ok": None if not live else False,
                "detail": "No working microphone, so the speaker cannot be tested" if not live else "Played the beep; none of the three microphones heard it (amp or speaker silent)"})
    return speaker, mics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--skip", default="")
    args = ap.parse_args()
    skip = set(filter(None, args.skip.split(",")))
    items = []

    def add(key, label, fn):
        if key in skip:
            items.append({"id": key, "label": label, "ok": None, "detail": "Not tested this time"})
            return
        t0 = time.time()
        try:
            res = fn()
        except Exception as e:
            res = {"ok": False, "detail": f"Self-check program error: {type(e).__name__} {e}"[:160]}
        items.append({"id": key, "label": label, **res, "s": round(time.time() - t0, 1)})

    lock, held_by = take_hw_lock() if {"imu", "servos"} - skip else (None, None)
    for key, label, fn in [("imu", "IMU", check_imu), ("touch", "Touch board", check_touch),
                           ("camera", "Camera", check_camera), ("servos", "Servos", check_servos)]:
        if key in ("imu", "servos") and key not in skip and lock is None:
            items.append({"id": key, "label": label, "ok": None,
                          "detail": f"Skipped: the brain is using the servo bus and IMU ({', '.join(held_by)})"})
            continue
        add(key, label, fn)
    if lock is not None:
        lock.close()
    if "audio" in skip:
        items += [{"id": k, "label": l, "ok": None, "detail": "Not tested this time"}
                  for k, l in [("speaker", "Amp and speaker")] + [(f"mic{i}", n) for i, n in enumerate(MIC_NAMES)]]
    else:
        try:
            speaker, mics = check_audio()
        except Exception as e:
            speaker, mics = {"ok": False, "detail": f"Self-check program error: {type(e).__name__} {e}"[:160]}, []
        items.append({"id": "speaker", "label": "Amp and speaker", **speaker})
        items += [{"id": f"mic{i}", "label": n, **m} for i, (n, m) in enumerate(zip(MIC_NAMES, mics))]
    with open("/proc/uptime") as f:
        uptime = float(f.read().split()[0])
    with open("/proc/sys/kernel/random/boot_id") as f:
        boot_id = f.read().strip()
    rec = {"t": time.time(), "uptime_s": round(uptime), "boot_id": boot_id, "trigger": os.environ.get("DUCK_SELFCHECK_TRIGGER", "manual"),
           "failed": sum(i["ok"] is False for i in items), "items": items}
    os.makedirs(args.out, exist_ok=True)
    tmp = os.path.join(args.out, "latest.json.tmp")
    with open(tmp, "w") as f:
        json.dump(rec, f, ensure_ascii=False)
    os.replace(tmp, os.path.join(args.out, "latest.json"))
    with open(os.path.join(args.out, "history.jsonl"), "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(json.dumps(rec, ensure_ascii=False, indent=1))
    return 1 if rec["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
