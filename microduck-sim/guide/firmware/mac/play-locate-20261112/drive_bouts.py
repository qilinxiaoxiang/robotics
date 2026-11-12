#!/usr/bin/env python3
"""Short test walks on the robot, driven from the Mac through the same command writer the app uses
(microduck-simulator/desktop/duck-command.py over one ssh session to the A7Z; it holds the driver lease, so the app
and this script never interleave commands). Only robot-tested commands: forward vx 0.25, turns vtheta +-0.3, and
zero-velocity walk (closed-loop stand) between bouts. A held walk is repeated every 0.3 s with for_s 0.6, as the app
does, so if this script dies the duck stops walking within 0.6 s.

  python3 drive_bouts.py --status           # who drives, the command in force, the brain's notes; writes nothing
  python3 drive_bouts.py --program std      # claim the lease (only if nobody drives), run the program, stand
  python3 drive_bouts.py --program std --log-mark   # same

Ctrl-C at any time: a marked stop (zero walk, "stop": true) is sent, the duck stands.
Every command sent is logged with its time to ~/duck-walks/drive-<time>.jsonl.
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time

WRITER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "microduck-simulator",
                      "desktop", "duck-command.py")
CLIENT = {"id": "claude-gap-study", "name": "Claude gap study"}
STAND = {"mode": "walk", "vx": 0, "vy": 0, "vtheta": 0}
# (label, command or None for stand, seconds)
PROGRAMS = {
    "std": [("stand", None, 4), ("fwd", dict(vx=0.25), 4), ("stand", None, 4), ("left", dict(vtheta=0.3), 3),
            ("stand", None, 4), ("right", dict(vtheta=-0.3), 3), ("stand", None, 4), ("fwd", dict(vx=0.25), 4),
            ("stand", None, 5)],
    "fwd": [("stand", None, 4), ("fwd", dict(vx=0.25), 4), ("stand", None, 5)],
    "stand": [("stand", None, 10)],
}


class Writer:
    def __init__(self):
        code = base64.b64encode(open(os.path.abspath(WRITER), "rb").read()).decode()
        self.p = subprocess.Popen(
            ["ssh", "-o", "ConnectTimeout=8", "a7z",
             f"exec python3 -u -c 'import sys,base64;exec(base64.b64decode(sys.argv[1]))' {code}"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self.n = 0
        self.ready = json.loads(self.p.stdout.readline())

    def req(self, **kw):
        self.n += 1
        kw["n"] = self.n
        self.p.stdin.write(json.dumps(kw) + "\n")
        self.p.stdin.flush()
        return json.loads(self.p.stdout.readline())

    def close(self):
        try:
            self.req(op="release", id=CLIENT["id"])
        finally:
            self.p.stdin.close()
            self.p.wait(timeout=10)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--program", choices=sorted(PROGRAMS))
    a = ap.parse_args()
    w = Writer()
    r = w.req(op="read")
    print(json.dumps(dict(current=r.get("current"), driver=r.get("driver"), supply=r.get("supply"),
                          notes=r.get("notes")), ensure_ascii=False))
    if a.status or not a.program:
        w.close()
        return
    cur = r.get("current") or {}
    if cur.get("mode") not in ("walk", "stand"):
        w.close()
        sys.exit(f"brain is in mode {cur.get('mode')!r}, not standing: switch to stand/walk in the app first")
    if cur.get("head"):  # keep the head where the app left it
        STAND["head"] = cur["head"]
    c = w.req(op="claim", client=CLIENT)
    if not c.get("ok"):
        w.close()
        sys.exit(f"lease busy: {c}")
    log = open(os.path.expanduser(time.strftime("~/duck-walks/drive-%Y%m%d-%H%M%S.jsonl")), "w")

    def send(cmd, label):
        ans = w.req(op="set", cmd=cmd, client=CLIENT)
        log.write(json.dumps(dict(t=time.time(), label=label, cmd=cmd, ok=ans.get("ok"))) + "\n")
        if not ans.get("ok"):
            raise RuntimeError(f"refused: {ans}")

    try:
        for label, extra, secs in PROGRAMS[a.program]:
            print(f"{time.strftime('%H:%M:%S')} {label} {secs}s", flush=True)
            end = time.time() + secs
            if extra is None:
                send(dict(STAND), label)
                time.sleep(secs)
                continue
            while time.time() < end:
                send(dict(STAND, **extra, for_s=0.6), label)
                time.sleep(0.3)
    except KeyboardInterrupt:
        print("interrupted", flush=True)
    finally:
        try:
            send(dict(STAND, stop=True), "stop")
        except Exception as e:  # noqa: BLE001
            print("stop failed:", e, flush=True)
        r = w.req(op="read")
        print("after:", json.dumps(dict(current=r.get("current"), notes=r.get("notes")), ensure_ascii=False))
        log.close()
        w.close()


if __name__ == "__main__":
    main()
