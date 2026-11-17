"""Walk, stop, turn by IMU heading, stop: record walk-mode zero-command stances for the left-lean fault (FAULTS T11).

Drives the A7Z brain through desktop/duck-command.py (the driver lease, atomic command writes) and follows its tick
log with tail -F over a second ssh. Steps are given as arguments, run in order:

  walk:S        vx 0.25 for S seconds (robot-tested speed)
  turn:DEG      in place at vtheta 0.5 rad/s (robot-tested) until the IMU heading has changed by DEG (sign = direction,
                + is to the robot's left), 12 s at most
  hold:S:NAME   zero-velocity walk (closed-loop stand) for S seconds; the last 6 s of rows go to OUT/NAME.jsonl

Stops with a marked stop and ends if the trunk tilts past 30 deg. Leaves the robot in walk mode at zero command (agent
scripts never send stand to a robot on the policy, FAULTS fall-on-switch mitigation).

  python3 lean_walk_turn.py --log ~/duck-logs/duck_wired_log_SUFFIX.jsonl --out DIR walk:2 hold:10:a turn:180 hold:10:b
"""
import argparse
import base64
import json
import math
import os
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
sys.path.insert(0, MAC)
from walk_brain import IMU_MOUNT_QUAT, MOUNT_FIX, qmul  # noqa: E402

DUCK_COMMAND = os.path.join(MAC, "..", "..", "..", "microduck-simulator", "desktop", "duck-command.py")
CLIENT = {"id": "claude-lean-test", "name": "Claude lean test"}

ap = argparse.ArgumentParser()
ap.add_argument("--log", required=True, help="tick log path on the A7Z")
ap.add_argument("--out", required=True)
ap.add_argument("steps", nargs="+")
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)

code = base64.b64encode(open(DUCK_COMMAND, "rb").read()).decode()
cmd_proc = subprocess.Popen(["ssh", "a7z", f"echo {code} | base64 -d > /tmp/duck_command_lean.py && "
                             "python3 /tmp/duck_command_lean.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            text=True, bufsize=1)
print("command channel:", cmd_proc.stdout.readline().strip(), flush=True)  # duck-command.py's ready line
log_proc = subprocess.Popen(["ssh", "a7z", f"tail -n 0 -F {a.log}"], stdout=subprocess.PIPE, text=True, bufsize=1)

state = {"row": None, "rows": []}
lock = threading.Lock()


def follow():
    for line in log_proc.stdout:
        try:
            r = json.loads(line)
        except ValueError:
            continue
        with lock:
            state["row"] = r
            state["rows"].append(line)
            if len(state["rows"]) > 2000:
                del state["rows"][:1000]


threading.Thread(target=follow, daemon=True).start()
n = [0]


def send(op, **kw):
    n[0] += 1
    req = dict(n=n[0], op=op, client=CLIENT, **kw)
    cmd_proc.stdin.write(json.dumps(req) + "\n")
    cmd_proc.stdin.flush()
    ans = json.loads(cmd_proc.stdout.readline())
    if ans.get("busy") or ans.get("error"):
        print("command refused:", ans, flush=True)
    return ans


def walk(vx=0.0, vtheta=0.0, stop=False):
    c = {"mode": "walk", "vx": vx, "vy": 0, "vtheta": vtheta, "for_s": 0.6}
    if stop:
        c["stop"] = True
    return send("set", cmd=c)


def heading(r):
    q = qmul(qmul(r["quat"], MOUNT_FIX), IMU_MOUNT_QUAT)
    w, x, y, z = q
    fx, fy = 1 - 2 * (y * y + z * z), 2 * (x * y + w * z)  # body x axis in the world frame
    return math.degrees(math.atan2(fy, fx))


def tilt(r):
    g = r.get("gb") or [0, 0, -1]
    return math.degrees(math.acos(max(-1.0, min(1.0, -g[2] / (math.sqrt(sum(v * v for v in g)) or 1)))))


def current():
    with lock:
        return state["row"]


def guarded_sleep(s):
    t_end = time.time() + s
    while time.time() < t_end:
        r = current()
        if r and tilt(r) > 30:
            walk(stop=True)
            sys.exit(f"tilt {tilt(r):.0f} deg: stopped")
        time.sleep(0.05)


send("take")
t0 = time.time()
while current() is None and time.time() - t0 < 10:
    time.sleep(0.1)
if current() is None:
    sys.exit("no tick rows from the brain log")

for step in a.steps:
    kind, *args = step.split(":")
    if kind == "walk":
        t_end = time.time() + float(args[0])
        while time.time() < t_end:
            walk(vx=0.25)
            guarded_sleep(0.3)
        walk()
        print(f"walked {args[0]} s", flush=True)
    elif kind == "turn":
        want = float(args[0])
        h0 = heading(current())
        turned, prev, t_end = 0.0, h0, time.time() + 12
        while abs(turned) < abs(want) - 5 and time.time() < t_end:
            walk(vtheta=math.copysign(0.5, want))
            guarded_sleep(0.3)
            h = heading(current())
            turned += (h - prev + 180) % 360 - 180
            prev = h
        walk()
        guarded_sleep(1.5)
        h = heading(current())
        turned += (h - prev + 180) % 360 - 180
        print(f"turned {turned:+.0f} deg (asked {want:+.0f})", flush=True)
    elif kind == "hold":
        s, name = float(args[0]), args[1]
        t_end = time.time() + s
        while time.time() < t_end:
            walk()
            guarded_sleep(0.3)
        with lock:
            rows = list(state["rows"])
        t_last = json.loads(rows[-1])["t"]
        keep = [l for l in rows if json.loads(l)["t"] >= t_last - 6]
        open(os.path.join(a.out, name + ".jsonl"), "w").writelines(keep)
        print(f"held {s} s, {len(keep)} rows -> {name}.jsonl", flush=True)
    else:
        sys.exit(f"unknown step {step}")

walk()
cmd_proc.stdin.close()
log_proc.terminate()
