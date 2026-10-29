"""The runner's connection to the duck's brain (walk_wired.py on the A7Z, or walk_brain.py against a simulated duck).

Three things cross this link:
- the control file (walk_brain.py / walk_wired.py `--cmd`, /tmp/duck_cmd.json on the A7Z): written whole and atomically
  (temporary file, then rename), the way walk_wired.py and the app's duck-command.py write it;
- the brain's tick log (JSONL, one row per 20 ms tick) and its stdout, tailed from where the runner joined;
- the control file's current content, so a command the runner did not write (the app, the brain's own stops) is seen.

`LocalLink` does all of it on this machine (the dry run, the simulated duck). `RemoteLink` does it on the A7Z through
one SSH session running `a7z_agent.py` (passed as base64 like the app's duck-command.py; nothing is installed there).

`Readback` turns rows and stdout lines into mind events: `fell`, `guard_trip`, `refused`, `seated`, `standing`, plus
`handback` (the brain rewrote the file to the zero-command walk by itself) and informational `brain_mode`.
"""
from __future__ import annotations

import base64
import json
import math
import os
import re
import subprocess
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WALK_ZERO = {"mode": "walk", "vx": 0.0, "vy": 0.0, "vtheta": 0.0}
SIT = {"mode": "sit"}
IDLE_BY_POSTURE = {"standing": WALK_ZERO, "sitting": SIT}
# walk_brain.py FALL_PREDICT_Z: body gravity z past this (upright is -1) is a fall; the Brain freezes its goals there.
FALL_Z = -0.5
FALL_HOLD_S = 0.3      # the gravity must sit past FALL_Z this long (one bad IMU frame is not a fall)
UPRIGHT_Z = -0.85      # within about 32 deg of upright
UPRIGHT_HOLD_S = 2.0   # after a fall: upright this long again counts as standing
REFUSED = re.compile(r"^(.*?)\s+refused: (.*)$")
STOP = re.compile(r"^STOP -> (.*?): (.*)$")
MODE = re.compile(r"^mode -> (\w+)")
WAITS = re.compile(r"^mode (\w+) waits for a fresh")


def atomic_write(path: str | Path, cmd: dict, suffix=".runner.tmp"):
    """One JSON object, replaced atomically, like walk_wired.write_cmd and duck-command.py write."""
    path = str(path)
    tmp = path + suffix
    with open(tmp, "w") as f:
        json.dump(cmd, f)
    os.replace(tmp, path)


def same_cmd(a, b) -> bool:
    """Two control-file values that mean the same command (dict equality: 0 == 0.0, key order free, nested heads)."""
    return a == b


def is_idle(cmd) -> bool:
    """A zero-command walk (any head pose, with or without for_s) or a plain sit: the states the runner leaves the brain in
    and the states in which it may take over again."""
    if not isinstance(cmd, dict):
        return False
    if cmd.get("mode") == "sit":
        return set(cmd) <= {"mode", "head"}
    if cmd.get("mode") != "walk":
        return False
    return all(abs(float(cmd.get(k, 0) or 0)) < 1e-9 for k in ("vx", "vy", "vtheta")) and \
        set(cmd) <= {"mode", "vx", "vy", "vtheta", "head", "for_s"}


def tilt_deg(gb) -> float | None:
    try:
        return math.degrees(math.acos(max(-1.0, min(1.0, -float(gb[2])))))
    except (TypeError, IndexError, ValueError):
        return None


class Tail:
    """New complete lines of a file since the last call; tolerates the file appearing late or being replaced."""

    def __init__(self, path, from_start=False):
        self.path = str(path) if path else None
        self.pos = None
        self.from_start = from_start
        self.ino = None
        self.buf = ""

    def lines(self) -> list[str]:
        if not self.path:
            return []
        try:
            st = os.stat(self.path)
        except OSError:
            return []
        if self.ino != st.st_ino:  # first sight: join at the end (or the start); a replaced file: read it from its start
            first = self.ino is None
            self.ino, self.buf = st.st_ino, ""
            self.pos = st.st_size if first and not self.from_start else 0
        if st.st_size < self.pos:  # truncated
            self.pos = 0
        if st.st_size == self.pos:
            return []
        with open(self.path, "r", errors="replace") as f:
            f.seek(self.pos)
            chunk = f.read()
            self.pos = f.tell()
        text = self.buf + chunk
        parts = text.split("\n")
        self.buf = parts.pop()  # a partial last line waits for the rest
        return [p for p in parts if p.strip()]


class LocalLink:
    """Control file, tick log and stdout on this machine."""

    def __init__(self, cmd_path, log_path=None, out_path=None, from_start=False):
        self.cmd_path = str(cmd_path)
        self.log_path, self.out_path = (str(log_path) if log_path else None), (str(out_path) if out_path else None)
        self.rows_tail, self.lines_tail = Tail(log_path, from_start), Tail(out_path, from_start)
        self.writes = 0

    def write(self, cmd: dict):
        atomic_write(self.cmd_path, cmd)
        self.writes += 1

    def read(self):
        try:
            with open(self.cmd_path) as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def new_rows(self) -> list[dict]:
        out = []
        for ln in self.rows_tail.lines():
            try:
                out.append(json.loads(ln))
            except ValueError:
                continue
        return out

    def new_lines(self) -> list[str]:
        return self.lines_tail.lines()

    def extra(self) -> list[dict]:
        """Sensor records that only the remote agent produces (sound levels, camera frames): none here."""
        return []

    def close(self):
        pass


class RemoteLink:
    """The same three streams on the A7Z over one SSH session running a7z_agent.py.

    The agent writes the control file atomically on request, reports its content whenever it changes, tails the newest
    ~/duck-logs/duck_wired_log_*.jsonl (rows thinned to about 10 Hz, heavy keys dropped) and duck_wired_*.out, and with
    `mic` also streams sound levels, with `cam_hz` JPEG frames of the head camera while its daemon already runs.
    """

    def __init__(self, host="a7z", cmd_path=None, mic=None, cam_hz=0.0, python=None, timeout_s=20.0):
        src = (HERE / "a7z_agent.py").read_text()
        opts = {"cmd": cmd_path, "mic": mic, "cam_hz": cam_hz}
        code = f"import base64,sys; sys.argv=['a7z_agent', {json.dumps(json.dumps(opts))}]; " \
               f"exec(base64.b64decode('{base64.b64encode(src.encode()).decode()}'))"
        py = python or "P=$HOME/.venvs/duck-policy/bin/python; [ -x \"$P\" ] || P=python3; exec \"$P\""
        self.proc = subprocess.Popen(["ssh", "-o", "BatchMode=yes", "-o", "ServerAliveInterval=5", host,
                                      f"{py} -c {json.dumps(code)}"],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                     bufsize=1)
        self.lock = threading.Lock()
        self.rows, self.lines, self.extras, self.acks = [], [], [], {}
        self.current, self.ready, self.error, self.n = None, None, None, 0
        self.writes = 0
        threading.Thread(target=self._pump, daemon=True).start()
        threading.Thread(target=self._stderr, daemon=True).start()
        t0 = time.monotonic()
        while self.ready is None and time.monotonic() - t0 < timeout_s and self.proc.poll() is None:
            time.sleep(0.05)
        if not self.ready:
            raise RuntimeError(f"a7z agent on {host} did not answer: {self.error or 'no ready line'}")
        self.cmd_path = self.ready.get("path")

    def _stderr(self):
        for ln in self.proc.stderr:
            self.error = ln.strip()[:300]

    def _pump(self):
        for ln in self.proc.stdout:
            try:
                msg = json.loads(ln)
            except ValueError:
                continue
            with self.lock:
                k = msg.get("kind")
                if k == "ready":
                    self.ready = msg
                    self.current = msg.get("current")
                elif k == "row":
                    self.rows.append(msg["row"])
                elif k == "line":
                    self.lines.append(msg["text"])
                elif k == "cmd":
                    self.current = msg.get("cmd")
                elif k == "ack":
                    self.acks[msg.get("n")] = msg
                else:
                    self.extras.append(msg)

    def write(self, cmd: dict, timeout_s=5.0):
        self.n += 1
        n = self.n
        self.proc.stdin.write(json.dumps({"n": n, "op": "write", "cmd": cmd}) + "\n")
        self.proc.stdin.flush()
        t0 = time.monotonic()
        while time.monotonic() - t0 < timeout_s:
            with self.lock:
                ack = self.acks.pop(n, None)
                if ack is not None:
                    if not ack.get("ok"):
                        raise RuntimeError(f"a7z agent could not write the control file: {ack.get('error')}")
                    self.current = cmd
                    self.writes += 1
                    return
            time.sleep(0.01)
        raise RuntimeError("a7z agent did not acknowledge the write")

    def read(self):
        with self.lock:
            return self.current

    def new_rows(self):
        with self.lock:
            out, self.rows = self.rows, []
        return out

    def new_lines(self):
        with self.lock:
            out, self.lines = self.lines, []
        return out

    def extra(self):
        with self.lock:
            out, self.extras = self.extras, []
        return out

    def close(self):
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=3)
        except Exception:
            self.proc.kill()


class Readback:
    """Brain log rows and stdout lines -> mind events. Keeps the brain's mode, gravity and posture as last seen."""

    def __init__(self):
        self.mode = None
        self.gb = None
        self.row_t = None
        self.posture = None          # "standing" | "sitting" | "fallen" | None (not seen yet)
        self.fallen_since = None
        self.upright_since = None
        self.seated_reported = False
        self.stall_reported = False
        self.sit_phase = None
        self.hw_fault = False
        self.imu_lost = False
        self.rows_seen = 0
        self.max_tilt_deg = 0.0
        self.last_stop = None        # (wall time, what, why)
        self.touch = None            # newest pad counts [L1, R1, L2, R2, M] or None
        self.touch_age = None
        self.gyro = None
        self.cmd_in_force = None     # the brain's view of the control file (row "cmd"), when logged
        self.mode_changed_t = None   # row time of the last mode change (posture transients are not bumps)

    def upright(self) -> bool:
        return self.gb is not None and float(self.gb[2]) < UPRIGHT_Z

    def feed(self, rows: list[dict], lines: list[str], now: float) -> list[dict]:
        events = []
        for ln in lines:
            events += self._line(ln, now)
        for row in rows:
            events += self._row(row, now)
        return events

    def _line(self, ln: str, now: float) -> list[dict]:
        s = ln.strip()
        m = STOP.match(s)
        if m:
            what, why = m.group(1), m.group(2)
            self.last_stop = (now, what, why)
            if what == "zero command":
                return [{"kind": "handback", "why": why}]
            return [{"kind": "guard_trip", "why": why, "brain_wrote": what}]
        m = REFUSED.match(s)
        if m:
            return [{"kind": "refused", "what": m.group(1), "why": m.group(2)}]
        if s.startswith("sit: STALLED"):
            return [{"kind": "refused", "what": "sit", "why": "stalled: the legs did not follow the sitstand policy"}]
        if s.startswith("HARDWARE ERROR"):
            self.hw_fault = True
            return [{"kind": "guard_trip", "why": s[:200]}]
        if s.startswith("hardware errors cleared"):
            self.hw_fault = False
            return [{"kind": "brain_cleared", "what": "hardware error"}]
        if s.startswith("IMU LOST"):
            self.imu_lost = True
            return [{"kind": "guard_trip", "why": s[:200]}]
        if s.startswith("IMU back"):
            self.imu_lost = False
            return [{"kind": "brain_cleared", "what": "IMU"}]
        if s.startswith("BATTERY STOP"):
            return [{"kind": "guard_trip", "why": s[:200]}]
        if s.startswith("BATTERY LOW"):
            return [{"kind": "battery_low", "why": s[:200]}]
        m = MODE.match(s)
        if m:
            return [{"kind": "brain_mode", "mode": m.group(1)}]
        m = WAITS.match(s)
        if m:
            return [{"kind": "brain_waits", "mode": m.group(1)}]
        if s.startswith("getup:"):
            return [{"kind": "getup", "why": s[7:200]}]
        return []

    def _row(self, row: dict, now: float) -> list[dict]:
        events = []
        self.rows_seen += 1
        t = float(row.get("t", now))
        mode, gb = row.get("mode"), row.get("gb")
        prev_mode = self.mode
        self.row_t, self.mode = t, mode or self.mode
        if self.mode != prev_mode:
            self.mode_changed_t = t
        if "touch" in row:
            self.touch, self.touch_age = row.get("touch"), row.get("touch_age")
        if row.get("gyro_body") is not None:
            self.gyro = row["gyro_body"]
        if row.get("cmd") is not None:
            self.cmd_in_force = row["cmd"]
        if gb is not None and len(gb) == 3 and all(v is not None for v in gb):
            self.gb = gb
            tilt = tilt_deg(gb)
            if tilt is not None:
                self.max_tilt_deg = max(self.max_tilt_deg, tilt)
            z = float(gb[2])
            if z > FALL_Z:
                self.upright_since = None
                if self.fallen_since is None:
                    self.fallen_since = t
                elif t - self.fallen_since >= FALL_HOLD_S and self.posture != "fallen":
                    self.posture = "fallen"
                    events.append({"kind": "fell", "gb": gb, "tilt_deg": round(tilt or 0.0, 1)})
            else:
                self.fallen_since = None
                if z < UPRIGHT_Z:
                    if self.upright_since is None:
                        self.upright_since = t
                    elif self.posture == "fallen" and t - self.upright_since >= UPRIGHT_HOLD_S:
                        self.posture = "standing"
                        events.append({"kind": "standing", "after": "fall"})
                else:
                    self.upright_since = None
        # sit mode: the sitstand policy's phase and the stall check (walk_brain.py Brain.tick)
        phase = row.get("sit_phase")
        if mode == "sit":
            if phase != self.sit_phase:
                self.sit_phase = phase
                if phase in ("prep", "down"):
                    self.seated_reported = self.stall_reported = False
            stalled = row.get("sit_stalled")
            if phase == "seated" and stalled is False and not self.seated_reported:
                self.seated_reported = True
                self.posture = "sitting"
                events.append({"kind": "seated"})
            elif phase == "seated" and stalled is True and not self.stall_reported:
                self.stall_reported = True
        elif prev_mode == "sit" and mode in ("walk", "stand") and self.posture != "fallen":
            self.sit_phase = None
            if self.posture == "sitting":
                self.posture = "standing"
                events.append({"kind": "standing", "after": "sit"})
        if mode in ("walk", "stand") and self.posture is None and self.upright():
            self.posture = "standing"
        return events
