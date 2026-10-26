"""Rebuild the dry-run fixtures from recorded robot data (run from the repository root):

  python3 -m pet.body.fixtures.make_fixtures

- duck_bus_scan.json: servo ids that answered, bus voltage and hardware-error state from a recorded walk_wired tick log
  (microduck-sim/guide/firmware/mac/robot-runs-20261023-a7z), jaw ID15 from that run's stdout. Model numbers are not
  logged: 1200 (XL330-M288-T, the servo order in microduck-sim/PROJECT-CONTEXT.json servo_order). EEPROM position
  limits were never dumped (regdump.py reads no limits), so they are null.
- duck_babble_recorded.json: real windows from every recorded tick log (stand mode, or walk mode standing at zero
  command) in which exactly one joint moved (> 0.05 rad within 0.5 s) while every other joint stayed within 0.02 rad,
  and that joint's goal moved by at least half as much: the brain commanded it. A move nobody commanded (a hand on the
  robot: 57 such windows in the logs up to 2026-10-23) is never picked. Per joint the window with the largest commanded
  move; the goal change is the commanded amplitude. Walk-mode windows carry the standing policy's own balancing in the
  IMU trace. Only neck_pitch, head_pitch, head_yaw and left_hip_roll have such windows. No camera was logged.
- omx_bus_scan.json: the follower arm of omx-local/evidence/hardware-check.json (read-only scan 2026-10-05).
- duck_health_replay.jsonl: tick-log rows around the recorded hardware fault (left_ankle, run 1019c) and around
  a stretch of unanswered reads, trimmed to the fields health.py reads.
"""
import glob
import gzip
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
MAC = os.path.join(REPO, "microduck-sim", "guide", "firmware", "mac")
NAMES = ["right_ankle", "right_knee", "right_hip_pitch", "right_hip_roll", "right_hip_yaw", "left_ankle", "left_knee",
         "left_hip_pitch", "left_hip_roll", "left_hip_yaw", "head_pitch", "neck_pitch", "head_yaw", "head_roll"]
SCAN_RUN = "robot-runs-20261023-a7z/duck_wired_log_app1023-225437.jsonl.gz"
SCAN_OUT = "robot-runs-20261023-a7z/duck_wired_app1023-225437.out"


def rows(path):
    with gzip.open(path, "rt") as f:
        for line in f:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def rel(p):
    return os.path.relpath(p, REPO)


def duck_scan():
    path = os.path.join(MAC, SCAN_RUN)
    row = next(r for r in rows(path) if r.get("q") and not r.get("missing") and r.get("servo_v"))
    jaw = [ln.strip() for ln in open(os.path.join(MAC, SCAN_OUT)) if ln.startswith("jaw ID15")]
    motors = [dict(id=i, model=1200, hardware_error=1 if NAMES[i - 1] in row.get("hw_faults", []) else 0,
                   min_position_limit=None, max_position_limit=None) for i in range(1, 15)]
    motors.append(dict(id=15, model=1200, hardware_error=0, min_position_limit=None, max_position_limit=None))
    return dict(body_hint="microduck", port="/dev/ttyAS2", baud=500000, voltage_v=row["servo_v"][1], motors=motors,
                provenance=dict(
                    answered=f"{rel(path)} first row with all 14 policy servos read (t {row['t']}); servo_v {row['servo_v']}",
                    jaw=f"{rel(os.path.join(MAC, SCAN_OUT))}: {jaw[0] if jaw else 'no jaw line'}",
                    model="not logged; 1200 = XL330-M288-T per microduck-sim/PROJECT-CONTEXT.json servo_order",
                    limits="EEPROM position limits never dumped: null"))


TICK_RAD = 2 * 3.141592653589793 / 4096


def duck_windows(win=25, move=0.05, still=0.02):
    best = {}
    for path in sorted(glob.glob(os.path.join(MAC, "robot-runs-*", "**", "duck_wired_log*.jsonl.gz"), recursive=True)):
        rr, goal = [], {}
        for r in rows(path):  # a row's goal_tick lists only the servos written that tick: carry the others forward
            goal.update(r.get("goal_tick") or {})
            r["goal_full"] = dict(goal)
            if r.get("q") and not r.get("missing") and r.get("imu_valid", True) and r.get("torque") and r.get("gb") \
                    and r.get("gyro_body") and all(str(k) in goal for k in range(1, 15)) and r.get("mode") in ("stand", "walk"):
                rr.append(r)
        for i in range(0, len(rr) - win, 5):
            seg = rr[i:i + win]
            if seg[0]["mode"] != seg[-1]["mode"] or seg[-1]["t"] - seg[0]["t"] > win * 0.03:
                continue
            dq = [max(abs(r["q"][j] - seg[0]["q"][j]) for r in seg) for j in range(14)]
            moved = [j for j in range(14) if dq[j] > move]
            if len(moved) != 1 or any(dq[j] >= still for j in range(14) if j != moved[0]):
                continue
            j = moved[0]
            dg = [max(abs(r["goal_full"][str(k + 1)] - seg[0]["goal_full"][str(k + 1)]) for r in seg) * TICK_RAD
                  for k in range(14)]
            if seg[0]["mode"] == "walk" and any(abs(seg[0].get("cmd", {}).get(v, 0) or 0) > 1e-6 for v in ("vx", "vy", "vtheta")):
                continue  # walking: every joint is the policy's
            if dg[j] < 0.5 * dq[j]:
                continue  # not commanded: something pushed the joint
            if dg[j] > best.get(NAMES[j], (0,))[0]:
                best[NAMES[j]] = (dg[j], path, seg)
    out = []
    for name, (cmd, path, seg) in sorted(best.items()):
        j = NAMES.index(name)
        t0 = seg[0]["t"]
        out.append(dict(joint=name, commanded_rad=round(cmd, 4), babble=False, t=[round(r["t"] - t0, 3) for r in seg],
                        q=[r["q"][j] for r in seg], gb=[r["gb"] for r in seg], gyro=[r["gyro_body"] for r in seg],
                        img_change=None, mode=seg[0]["mode"],
                        source=f"{rel(path)} t {t0:.2f} ({seg[0]['mode']} mode, recorded)"))
    return out


def omx_scan():
    path = os.path.join(REPO, "omx-local", "evidence", "hardware-check.json")
    d = json.load(open(path))
    arm = next(a for a in d["arms"] if a["role"] == "follower")
    motors = [dict(id=m["id"], model=m["model"], hardware_error=m["hardware_error"], voltage_v=m["voltage"] / 10,
                   operating_mode=m["operating_mode"], min_position_limit=None, max_position_limit=None)
              for m in arm["motors"]]
    return dict(body_hint="omx_arm", port=arm["port"], baud=1000000, voltage_v=None, motors=motors,
                provenance=dict(scan=f"{rel(path)} follower, read-only scan {d['timestamp']}",
                                limits="the scan read no EEPROM position limits: null"))


def health_replay():
    out = []
    fault = os.path.join(MAC, "robot-runs-20261019-a7z", "duck_wired_log_1019c.jsonl.gz")
    rr = list(rows(fault))
    k = next(i for i, r in enumerate(rr) if r.get("hw_faults"))
    seg = rr[max(0, k - 50):k + 25]
    path2 = os.path.join(MAC, "robot-runs-20261023-a7z", "duck_wired_log_app1023-225437.jsonl.gz")
    rr2 = list(rows(path2))
    m = next((i for i, r in enumerate(rr2) if i > 50 and r.get("missing") and r.get("torque")), None)
    if m is None:  # no unanswered stretch with torque on: take the first unanswered rows of the run
        m = next(i for i, r in enumerate(rr2) if r.get("missing"))
    seg2 = rr2[max(0, m - 10):m + 20]
    for src, seg_ in ((fault, seg), (path2, seg2)):
        for r in seg_:
            out.append(dict(t=r["t"], mode=r.get("mode"), missing=r.get("missing", []), hw_faults=r.get("hw_faults", []),
                            cur_ma=r.get("cur_ma"), source=rel(src)))
    return out


def main():
    json.dump(duck_scan(), open(os.path.join(HERE, "duck_bus_scan.json"), "w"), indent=1)
    w = duck_windows()
    json.dump(dict(note="real single-joint windows from walk_wired tick logs; see make_fixtures.py", traces=w),
              open(os.path.join(HERE, "duck_babble_recorded.json"), "w"))
    json.dump(omx_scan(), open(os.path.join(HERE, "omx_bus_scan.json"), "w"), indent=1)
    with open(os.path.join(HERE, "duck_health_replay.jsonl"), "w") as f:
        for r in health_replay():
            f.write(json.dumps(r) + "\n")
    print(f"{len(w)} recorded babbling windows: " + ", ".join(t["joint"] for t in w))


if __name__ == "__main__":
    main()
