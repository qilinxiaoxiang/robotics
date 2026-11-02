#!/usr/bin/env python3
"""Keeps namecall.py running on the A7Z (duck-namecall.service): it starts it once the brain stands in walk mode at zero
velocity, and again after it exits (the brain left walk mode, a guard trip, a stop). Waiting costs a few file reads: the
models load only when namecall.py can really run. Every start and exit goes to ~/duck-logs/namecall_boot.jsonl."""
import glob
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.expanduser("~/duck-logs")
ARGS = ["--name", "mochi", "--spotter", "oww", "--no-person", "--life-max-gb", "1"]
POLL_S = 2.0
FRESH_S = 1.5
RETRY_S = 5.0      # after namecall.py exits
QUICK_EXIT_S = 30.0  # an exit this soon counts as a failed start
BACKOFF_S = 60.0   # after three failed starts in a row


def record(**kw):
    with open(os.path.join(LOGS, "namecall_boot.jsonl"), "a") as f:
        f.write(json.dumps(dict(ts=round(time.time(), 2), **kw)) + "\n")


def brain_ready(now=None, logs=None):
    """The newest brain log's last line, read from its tail only: fresh, walk mode, zero velocity."""
    now = time.time() if now is None else now
    paths = glob.glob(os.path.join(logs or LOGS, "duck_wired_log_*.jsonl"))
    if not paths:
        return False
    path = max(paths, key=os.path.getmtime)
    if now - os.path.getmtime(path) > FRESH_S:
        return False
    with open(path, "rb") as f:
        f.seek(0, os.SEEK_END)
        f.seek(max(0, f.tell() - 8192))
        lines = f.read().splitlines()
    try:
        row = json.loads(lines[-1])
    except (ValueError, IndexError):
        return False
    cmd = row.get("cmd") or {}
    return row.get("mode") == "walk" and not any(cmd.get(k) for k in ("vx", "vy", "vtheta"))


def main():
    failed = 0
    while True:
        if not brain_ready():
            time.sleep(POLL_S)
            continue
        t0 = time.time()
        record(event="start")
        rc = subprocess.run([sys.executable, os.path.join(HERE, "namecall.py"), *ARGS], cwd=HERE).returncode
        ran = time.time() - t0
        record(event="exit", rc=rc, ran_s=round(ran, 1))
        failed = failed + 1 if ran < QUICK_EXIT_S else 0
        time.sleep(BACKOFF_S if failed >= 3 else RETRY_S)


if __name__ == "__main__":
    main()
