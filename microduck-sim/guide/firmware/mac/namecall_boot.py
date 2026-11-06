#!/usr/bin/env python3
"""Run name listening from boot, without starting the brain or enabling torque.

Audio-only while the brain is absent/busy; guarded head responses only at rest or
fully seated. Mode changes stop the complete child process group before a new
capture process starts. Only a bounded tail of the brain log is read.
"""
import glob
import json
import os
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.expanduser("~/duck-logs")
ARGS = ["--name", "mochi", "--spotter", "oww", "--no-person", "--life-max-gb", "1"]
POLL_S = 2.0
FRESH_S = 1.5
RETRY_S = 5.0
QUICK_EXIT_S = 30.0
BACKOFF_S = 60.0
# Entering head mode restarts the listener (a 2-3 s deaf gap). The brain's readiness flickers while Shawn drives it
# (zero-command stops between walks, short mode changes): 2026-11-06 15:49-16:04 the listener restarted 22 times in
# 15 min, 8 runs lasting 2 s. So head mode starts only after readiness has held this long; leaving it stays immediate.
HEAD_HOLD_S = 10.0


def record(**kw):
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "namecall_boot.jsonl"), "a") as f:
        f.write(json.dumps(dict(ts=round(time.time(), 2), **kw)) + "\n")


def brain_ready(now=None, logs=None):
    """Fresh zero-speed walk or completed seat permits guarded head responses."""
    now = time.time() if now is None else now
    paths = glob.glob(os.path.join(logs or LOGS, "duck_wired_log_*.jsonl"))
    if not paths:
        return False
    try:
        path = max(paths, key=os.path.getmtime)
        if not 0 <= now - os.path.getmtime(path) <= FRESH_S:
            return False
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 8192))
            lines = f.read().splitlines()
        row = json.loads(lines[-1])
        if not 0 <= now - float(row.get("t", 0)) <= FRESH_S:
            return False
        cmd = row.get("cmd") or {}
        return (row.get("mode") == "sit" and row.get("sit_phase") == "seated") or (
            row.get("mode") == "walk" and not any(cmd.get(k) for k in ("vx", "vy", "vtheta")))
    except (OSError, ValueError, IndexError, TypeError, AttributeError):
        return False


def selfcheck_running():
    # Read process command lines, not a whole robot log. Selfcheck owns audio.
    p = subprocess.run(["pgrep", "-f", "[d]uck_selfcheck.py"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return p.returncode == 0


def desired_mode(ready, selfcheck):
    return None if selfcheck else "head" if ready else "audio-only"


def command(mode):
    return [sys.executable, os.path.join(HERE, "namecall.py"), *ARGS,
            *(["--audio-only"] if mode == "audio-only" else [])]


def stop_child(proc, killpg=os.killpg):
    """Reap the child and its audio helpers even if the leader already exited."""
    if proc is None:
        return
    try:
        killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        pass
    # A reaped parent does not establish that every audio helper has exited.
    try:
        killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


class Supervisor:
    def __init__(self, popen=subprocess.Popen, stop=stop_child, log=record):
        self.popen, self.stop, self.log = popen, stop, log
        self.child = None
        self.mode = None
        self.started = 0.0
        self.retry_at = 0.0
        self.failed = 0
        self.head_since = None

    def effective(self, mode, now):
        """Hold off entering head mode until it has been wanted for HEAD_HOLD_S; a running head child stays."""
        if mode != "head":
            self.head_since = None
            return mode
        if self.head_since is None:
            self.head_since = now
        if self.child is not None and self.mode == "head":
            return "head"
        return "head" if now - self.head_since >= HEAD_HOLD_S else "audio-only"

    def tick(self, mode, now):
        mode = self.effective(mode, now)
        if self.child is not None and (self.mode != mode or self.child.poll() is not None):
            rc = self.child.poll()
            changed = self.mode != mode
            ran = now - self.started
            self.stop(self.child)
            self.log(event="exit", mode=self.mode, rc=rc, ran_s=round(ran, 1),
                     reason="mode-change" if changed else "child-exit")
            self.child = None
            self.failed = 0 if changed or ran >= QUICK_EXIT_S else self.failed + 1
            self.retry_at = now if changed else now + (BACKOFF_S if self.failed >= 3 else RETRY_S)
        if self.child is None and mode is not None and now >= self.retry_at:
            self.child = self.popen(command(mode), cwd=HERE, start_new_session=True)
            self.mode, self.started = mode, now
            self.log(event="start", mode=mode, pid=self.child.pid)

    def close(self):
        if self.child is not None:
            self.stop(self.child)
            self.log(event="stop", mode=self.mode)
            self.child = None


def main():
    stopping = False

    def request_stop(_signum, _frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    os.makedirs(LOGS, exist_ok=True)
    supervisor = Supervisor()
    try:
        while not stopping:
            supervisor.tick(desired_mode(brain_ready(), selfcheck_running()), time.monotonic())
            time.sleep(POLL_S)
    finally:
        supervisor.close()


if __name__ == "__main__":
    main()
