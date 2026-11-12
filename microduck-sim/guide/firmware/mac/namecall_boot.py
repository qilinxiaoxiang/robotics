#!/usr/bin/env python3
"""Run name listening from boot, without starting the brain or enabling torque.

One namecall.py --follow-brain process listens for the whole boot: it answers with the
head only while the brain rests (zero-command walk or fully seated) and with a quack
otherwise. The child is restarted only when it exits (bounded backoff) and stopped while
duck_selfcheck.py owns the sound card; a stop takes the whole child process group.
"""
import json
import os
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.expanduser("~/duck-logs")
# The life log is the only record of a missed call (its index keeps the spotter score every 0.1 s). At 1 GB it filled
# on 2026-11-11 23:54 and stopped, so the 11-12 00:26 calls left no audio; life_log.py still stops at 2 GB disk free.
ARGS = ["--name", "mochi", "--spotter", "oww", "--no-person", "--life-max-gb", "4"]
POLL_S = 2.0
RETRY_S = 5.0
QUICK_EXIT_S = 30.0
BACKOFF_S = 60.0


def record(**kw):
    os.makedirs(LOGS, exist_ok=True)
    with open(os.path.join(LOGS, "namecall_boot.jsonl"), "a") as f:
        f.write(json.dumps(dict(ts=round(time.time(), 2), **kw)) + "\n")


def selfcheck_running():
    # Read process command lines, not a whole robot log. Selfcheck owns audio.
    p = subprocess.run(["pgrep", "-f", "[d]uck_selfcheck.py"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return p.returncode == 0


def desired_mode(selfcheck):
    # One listener for the whole boot: namecall.py --follow-brain switches the head on and off itself as the brain
    # rests or moves. 2026-11-12 00:26-00:34 the old head/audio-only split restarted the listener at every app drive
    # or stand change, 28 times in 8 minutes, and the duck missed most of Shawn's calls while it reloaded.
    return None if selfcheck else "listen"


def command(mode):
    return [sys.executable, os.path.join(HERE, "namecall.py"), *ARGS, "--follow-brain"]


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

    def tick(self, mode, now):
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
            supervisor.tick(desired_mode(selfcheck_running()), time.monotonic())
            time.sleep(POLL_S)
    finally:
        supervisor.close()


if __name__ == "__main__":
    main()
