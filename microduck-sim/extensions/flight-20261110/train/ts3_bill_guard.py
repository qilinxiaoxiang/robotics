"""Round 3: hard stop on the Modal bill (2026-11-19 20:50: 18.45 USD of credit left, real charges are not approved).

  python3 train/detach.py train/logs/ts3_bill_guard.out python3 train/ts3_bill_guard.py <hours>

Every 2 minutes reads `modal billing summary`. Line: metered this month at or under 51.00 USD. At STOP_USD (50.00) it
stops every live Modal app of this work (names starting with microduck-flight: the training arms and the gate
batches), ends this work's local watchers that submit Modal jobs (ts3m_watch.py, ts3_after_teach.sh,
ts3_after_kaggle.sh, ts3s_watch.py) and writes STOPPED. A bill that cannot be read three times in a row is
reported in the heartbeat (nothing is stopped on an unread bill).

Heartbeat: train/logs/ts3_bill_heartbeat.txt, a line every 10 minutes with the metered cost, last line DONE or STOPPED.
"""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

T = Path(__file__).resolve().parent
MODAL = "/Users/xiangzheng/code/robotics/omx-local/.venv/bin/modal"
HB = T / "logs/ts3_bill_heartbeat.txt"
LINE_USD, STOP_USD = 51.00, 50.00
WATCHERS = ("ts3m_watch.py", "ts3_after_teach.sh", "ts3_after_kaggle.sh", "ts3s_watch.py")


def hb(msg):
    with open(HB, "a") as f:
        f.write(time.strftime("%Y-%m-%dT%H:%M:%S ") + msg + "\n")


def metered():
    try:
        out = subprocess.run([MODAL, "billing", "summary"], capture_output=True, text=True, timeout=120).stdout
        return float(re.search(r"Metered Cost:\s+([0-9.]+)", out).group(1))
    except Exception:  # noqa: BLE001
        return None


def stop_all():
    out = subprocess.run([MODAL, "app", "list", "--json"], capture_output=True, text=True, timeout=120).stdout
    for a in json.loads(out or "[]"):
        name, state = str(a.get("description", "")), str(a.get("state", ""))
        if name.startswith("microduck-flight") and "stopped" not in state:
            r = subprocess.run([MODAL, "app", "stop", a["app_id"]], capture_output=True, text=True, timeout=120)
            hb(f"stopped app {a['app_id']} {name} (exit {r.returncode})")
    for w in WATCHERS:
        r = subprocess.run(["pkill", "-f", w], capture_output=True, text=True)
        hb(f"watcher {w}: pkill exit {r.returncode}")


def main():
    t_end = time.time() + float(sys.argv[1]) * 3600
    hb(f"bill guard START, line {LINE_USD}, stop at {STOP_USD}")
    n, unread = 0, 0
    while time.time() < t_end:
        m = metered()
        unread = unread + 1 if m is None else 0
        if unread == 3:
            hb("Modal bill unread three times in a row")
        if m is not None and m >= STOP_USD:
            hb(f"metered {m} >= {STOP_USD}: stopping every Modal app and watcher of this work")
            stop_all()
            hb("STOPPED")
            return
        if n % 5 == 0:
            hb(f"metered {m}")
        n += 1
        time.sleep(120)
    hb("DONE")


if __name__ == "__main__":
    main()
