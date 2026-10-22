"""Read one walk_wired JSONL log and report how the robot veers while walking forward, and how symmetric it stands.

  python3 veer_check.py LOG.jsonl [--last N]   (on the A7Z the logs are in ~/duck-logs; plain python3, no extra packages)
  --last N reports only the newest N forward bursts (stance split over those bursts only).

Forward bursts are walk-mode ticks with cmd vx > 0. Yaw is the gyro projected on gravity (body up = -gb), so it is the
turn about the vertical whatever the IMU mount, + = counter-clockwise seen from above = left. The stance leg is the
one whose ankle + knee + hip pitch draw over 1.5x the other leg's current. Hip yaw error is present minus goal on the
stance leg (+ = the joint sits further + than commanded). Stand rows: torque on, mode stand, last two thirds.
Also reads brain_sim_check.py --tick-log files (no cmd there: walk61 ticks count as the forward burst).

Acceptance used on 2026-10-22: |yaw rate| < 5 deg/s averaged over three 2 s bursts at vx 0.25 (2026-10-21: +23 to +42).
"""
import json
import math
import sys

TICK_DEG = 360 / 4096
R_LEG, L_LEG = (0, 1, 2), (5, 6, 7)  # pos/cur index = ID - 1: ankle, knee, hip pitch
R_HIP_YAW, L_HIP_YAW = 4, 9
NAMES = ("R_ankle", "R_knee", "R_hip_pitch", "R_hip_roll", "R_hip_yaw",  # q is in servo ID order, ID1 first
         "L_ankle", "L_knee", "L_hip_pitch", "L_hip_roll", "L_hip_yaw")


def yaw_rate(r):
    g, gb = r.get("gyro_body"), r.get("gb")
    if not g or not gb:
        return None
    n = math.sqrt(sum(x * x for x in gb)) or 1.0
    return -sum(a * b for a, b in zip(g, gb)) / n


def bursts(rows):
    out, cur = [], None
    for r in rows:
        cmd = r.get("cmd")  # brain_sim_check --tick-log rows carry no cmd: there walk61 ticks are the forward burst
        fw = r.get("mode", "").startswith("walk") and (cmd.get("vx", 0) > 0 if cmd else r.get("policy") == "walk")
        if fw:
            cur = cur if cur is not None else []
            cur.append(r)
        elif cur:
            out.append(cur)
            cur = None
    if cur:
        out.append(cur)
    return [b for b in out if len(b) >= 10]


def burst_report(b):
    yaw = t = 0.0
    for a, c in zip(b, b[1:]):
        dt, w = c["t"] - a["t"], yaw_rate(a)
        if w is not None and dt < 0.1:
            yaw, t = yaw + w * dt, t + dt
    return t, math.degrees(yaw)


def stance_report(rows):
    groups = {"R": [], "L": [], "both": []}
    for r in rows:
        c, w = r.get("cur_ma"), yaw_rate(r)
        if not c or w is None or not r.get("goal_tick") or not r.get("pos_tick"):
            continue
        rs, ls = sum(abs(c[i]) for i in R_LEG), sum(abs(c[i]) for i in L_LEG)
        side = "R" if rs > 1.5 * ls else "L" if ls > 1.5 * rs else "both"
        groups[side].append(r)
    for side, g in groups.items():
        if not g:
            continue
        w = sum(math.degrees(yaw_rate(r)) for r in g) / len(g)
        line = f"  {side:4s} stance: {len(g):4d} ticks, yaw rate {w:+6.1f} deg/s"
        if side != "both":
            i = R_HIP_YAW if side == "R" else L_HIP_YAW
            e = [(r["pos_tick"][i] - r["goal_tick"][str(i + 1)]) * TICK_DEG for r in g]
            line += f", stance hip yaw error {sum(e) / len(e):+5.1f} deg (|err| {sum(map(abs, e)) / len(e):.1f})"
        print(line)


def stand_report(rows):
    st = [r for r in rows if r.get("mode") == "stand" and r.get("torque", True) and r.get("gb") and r.get("q")]
    st = st[len(st) // 3:]
    if len(st) < 20:
        print("stand: fewer than 20 torque-on stand ticks")
        return
    n = len(st)
    gb = [sum(r["gb"][i] for r in st) / n for i in range(3)]
    roll = math.degrees(math.atan2(gb[1], -gb[2]))
    pitch = math.degrees(math.atan2(gb[0], -gb[2]))
    print(f"stand: {n} ticks, trunk roll {roll:+.2f} deg, pitch {pitch:+.2f} deg (gb {[round(x, 3) for x in gb]})")
    q = [math.degrees(sum(r["q"][i] for r in st) / n) for i in range(10)]
    print("  joints deg: " + ", ".join(f"{k} {v:+.1f}" for k, v in zip(NAMES, q)))
    if st[0].get("cur_ma"):
        c = [sum(abs(r["cur_ma"][i]) for r in st) / n for i in range(10)]
        print("  |current| mA by ID1-10: " + " ".join(f"{x:.0f}" for x in c))


def main():
    rows = [json.loads(line) for line in open(sys.argv[1]) if line.strip()]
    stand_report(rows)
    bs = bursts(rows)
    if "--last" in sys.argv:
        bs = bs[-int(sys.argv[sys.argv.index("--last") + 1]):]
    print(f"forward bursts: {len(bs)}")
    for b in bs:
        t, yaw = burst_report(b)
        c = b[0].get("cmd") or {}
        print(f"  vx {c.get('vx', '?')} vtheta {c.get('vtheta', 0)}: {t:4.1f} s, "
              f"yaw {yaw:+5.0f} deg ({yaw / t if t else 0:+5.1f} deg/s)")
    if bs:
        stance_report([r for b in bs for r in b])


if __name__ == "__main__":
    main()
