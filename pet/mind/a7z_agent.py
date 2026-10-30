"""Runs on the A7Z over one SSH session for pet/mind/runner.py (sent as base64 by brain_link.RemoteLink; nothing is
installed). It never touches the servo bus, the IMU or the camera device: it only reads files the brain and the camera
daemon already write, and writes the brain's control file on request, atomically, like duck-command.py.

stdin, one JSON object per line:   {"n": 1, "op": "write", "cmd": {...}}      write the control file
                                   {"n": 2, "op": "read"}                     answer with its content
stdout, one JSON object per line:  {"kind": "ready", "path": ..., "current": ...}
                                   {"kind": "ack", "n": 1, "ok": true}
                                   {"kind": "cmd", "cmd": {...}}              the control file changed (anyone's write)
                                   {"kind": "row", "row": {...}}              a tick-log row (about 10 Hz, thinned)
                                   {"kind": "line", "text": "..."}            a stdout line of the brain
                                   {"kind": "sound", "t": ..., "db": [...]}   with "mic": RMS level per channel, 10 Hz
                                   {"kind": "frame", "t": ..., "jpeg_b64": ...}  with "cam_hz": the head camera's newest
                                                                              frame while its daemon runs (never started here)
                                   {"kind": "note", "text": "..."}            anything the runner should log

argv[1] is a JSON object: {"cmd": control file path or null, "mic": ALSA device or null, "cam_hz": frames per second}.
"""
import base64
import glob
import json
import os
import re
import select
import struct
import subprocess
import sys
import threading
import time
from array import array

OPTS = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
LOGS = os.path.expanduser("~/duck-logs")
SHM_FRAME = "/dev/shm/a7z_cam.bgr"
FRAME_W, FRAME_H = 640, 360
HEADER = struct.Struct("<Qd")
ROW_KEEP = ("t", "mode", "gb", "gyro_body", "sit_phase", "sit_flag", "sit_stalled", "torque", "fresh", "hw_faults",
            "imu_age", "imu_valid", "touch", "touch_age", "touch_seq", "cmd", "policy", "fall_pred", "getup", "kp",
            "gp_phase", "hold_on", "grip_stop", "battery", "missing",
            "q", "head_cmd", "quat")  # joint angles, head command and IMU attitude: the camera's pose for saved frames
ROW_EVERY = 5  # every 5th 20 ms row (10 Hz), plus every row where the state changed
NEWEST_EVERY_S = 2.0
LOCK = threading.Lock()


def emit(obj):
    with LOCK:
        sys.stdout.write(json.dumps(obj, separators=(",", ":")) + "\n")
        sys.stdout.flush()


def cmd_path():
    if OPTS.get("cmd"):
        return OPTS["cmd"]
    try:
        with open(os.path.expanduser("~/duck-run.sh")) as f:
            m = re.search(r"--cmd\s+(\S+)", f.read())
    except OSError:
        m = None
    return m.group(1) if m else "/tmp/duck_cmd.json"


PATH = cmd_path()


def read_cmd():
    try:
        with open(PATH) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def write_cmd(cmd):
    tmp = PATH + ".runner.tmp"
    with open(tmp, "w") as f:
        json.dump(cmd, f)
    os.replace(tmp, PATH)


def newest(pattern):
    files = glob.glob(os.path.join(LOGS, pattern))
    return max(files, key=os.path.getmtime) if files else None


class Tail:
    def __init__(self):
        self.path, self.pos, self.buf = None, 0, ""

    def follow(self, path):
        if path != self.path:
            self.path, self.pos, self.buf = path, 0, ""
            if path:  # join at the end: the past is not this session's business
                try:
                    self.pos = os.path.getsize(path)
                except OSError:
                    self.pos = 0

    def lines(self):
        if not self.path:
            return []
        try:
            size = os.path.getsize(self.path)
        except OSError:
            return []
        if size < self.pos:
            self.pos = 0
        if size == self.pos:
            return []
        with open(self.path, "r", errors="replace") as f:
            f.seek(self.pos)
            text = self.buf + f.read()
            self.pos = f.tell()
        parts = text.split("\n")
        self.buf = parts.pop()
        return [p for p in parts if p.strip()]


def thin_row(row):
    return {k: row[k] for k in ROW_KEEP if k in row}


def state_key(row):
    return (row.get("mode"), row.get("sit_phase"), row.get("sit_stalled"), row.get("torque"), bool(row.get("hw_faults")),
            row.get("getup"))


def stdin_loop():
    for line in sys.stdin:
        n = None
        try:
            req = json.loads(line)
            n = req.get("n")
            if req.get("op") == "write":
                write_cmd(req["cmd"])
                emit({"kind": "ack", "n": n, "ok": True})
                emit({"kind": "cmd", "cmd": req["cmd"], "by": "runner"})
            elif req.get("op") == "read":
                emit({"kind": "ack", "n": n, "ok": True, "current": read_cmd()})
            else:
                raise ValueError("unknown op %r" % req.get("op"))
        except Exception as e:  # one bad request never ends the session
            emit({"kind": "ack", "n": n, "ok": False, "error": "%s: %s" % (type(e).__name__, e)})
    os._exit(0)  # the runner closed stdin: stop everything


def mic_loop(device):
    """RMS level in dB (full scale) per channel every 100 ms from arecord; silent failure if the device is busy."""
    rate, ch, frames = 48000, 4, 4800
    try:
        p = subprocess.Popen(["arecord", "-q", "-D", device, "-f", "S32_LE", "-r", str(rate), "-c", str(ch), "-t", "raw"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as e:
        emit({"kind": "note", "text": "mic: arecord not available (%s)" % e})
        return
    step = 8  # every 8th sample: 600 per channel per 100 ms is enough for a level
    need = frames * ch * 4
    while True:
        buf = p.stdout.read(need)
        if len(buf) < need:
            err = p.stderr.read().decode(errors="replace").strip()[-200:]
            emit({"kind": "note", "text": "mic: arecord stopped (%s)" % (err or "no data")})
            return
        a = array("i")
        a.frombytes(buf)
        db = []
        for c in range(ch):
            s = a[c::ch * step]
            if not s:
                db.append(None)
                continue
            ms = sum(float(v) * float(v) for v in s) / len(s)
            db.append(round(10 * (0.0 if ms <= 0 else __import__("math").log10(ms / (2.0 ** 31) ** 2)), 1))
        emit({"kind": "sound", "t": time.time(), "db": db})


def cam_loop(hz):
    """The camera daemon's newest frame as JPEG while /dev/shm/a7z_cam.bgr is fresh. The daemon is never started here."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        emit({"kind": "note", "text": "cam: no cv2 in this interpreter, no face frames"})
        return
    last_idx = None
    while True:
        time.sleep(1.0 / max(0.1, hz))
        try:
            if time.time() - os.path.getmtime(SHM_FRAME) > 1.0:
                continue
            with open(SHM_FRAME, "rb") as f:
                data = f.read()
        except OSError:
            continue
        if len(data) < HEADER.size + FRAME_W * FRAME_H * 3:
            continue
        idx, cap_t = HEADER.unpack_from(data)
        if idx == last_idx:
            continue
        last_idx = idx
        img = np.frombuffer(data, dtype=np.uint8, count=FRAME_W * FRAME_H * 3, offset=HEADER.size).reshape(FRAME_H, FRAME_W, 3)
        ok, jpg = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        if ok:
            emit({"kind": "frame", "t": cap_t, "jpeg_b64": base64.b64encode(jpg.tobytes()).decode()})


def main():
    emit({"kind": "ready", "path": PATH, "current": read_cmd(), "host": os.uname().nodename})
    threading.Thread(target=stdin_loop, daemon=True).start()
    if OPTS.get("mic"):
        threading.Thread(target=mic_loop, args=(OPTS["mic"],), daemon=True).start()
    if OPTS.get("cam_hz"):
        threading.Thread(target=cam_loop, args=(float(OPTS["cam_hz"]),), daemon=True).start()
    rows, out = Tail(), Tail()
    last_newest, last_cmd_mt, last_cmd, n_row, last_key = 0.0, None, read_cmd(), 0, None
    while True:
        now = time.time()
        if now - last_newest >= NEWEST_EVERY_S:
            last_newest = now
            log = newest("duck_wired_log_*.jsonl")
            if log != rows.path:
                rows.follow(log)
                out.follow(log.replace("duck_wired_log_", "duck_wired_").replace(".jsonl", ".out") if log else None)
                emit({"kind": "note", "text": "brain log: %s" % (os.path.basename(log) if log else "none yet")})
        try:
            mt = os.path.getmtime(PATH)
        except OSError:
            mt = None
        if mt != last_cmd_mt:
            last_cmd_mt = mt
            cur = read_cmd()
            if cur != last_cmd:
                last_cmd = cur
                emit({"kind": "cmd", "cmd": cur, "by": "file"})
        for ln in out.lines():
            emit({"kind": "line", "text": ln[:400]})
        for ln in rows.lines():
            try:
                row = json.loads(ln)
            except ValueError:
                continue
            n_row += 1
            key = state_key(row)
            gb = row.get("gb")
            bad = gb is not None and gb[2] is not None and gb[2] > -0.5
            if key != last_key or n_row % ROW_EVERY == 0 or bad:
                last_key = key
                emit({"kind": "row", "row": thin_row(row)})
        select.select([], [], [], 0.05)


if __name__ == "__main__":  # also true when exec'd from `python -c` by brain_link.RemoteLink
    main()
