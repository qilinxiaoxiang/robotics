#!/usr/bin/env python3
"""Walk ledger: every walk the brain logs, measured the same way, so changes show up across days.

The brain (walk_wired.py) already writes one row per 50 Hz tick to ~/duck-logs/duck_wired_log_<suffix>.jsonl on the
A7Z: present ticks, the goal ticks last written, currents, IMU gravity and gyro, the command. This tool turns those
rows into one ledger record per walk and a report:

  walk_ledger.py sync [--note TEXT]      pull new/grown logs from the A7Z (nice + idle IO), analyse, write the report
  walk_ledger.py analyze LOG... [--note TEXT]   analyse local logs (.jsonl or .jsonl.gz) into the ledger
  walk_ledger.py report [--last N]       rewrite and print the report from the ledger

Raw logs stay outside git in ~/duck-walks/raw (they reach hundreds of MB). The ledger and report are in git:
microduck-sim/walk-ledger/ledger.jsonl and REPORT.md. Logs are never parsed on the A7Z (2 GB RAM; 2026-10-30 a log
parse there stalled the brain and the duck fell): rsync only copies bytes.

Per walk (contiguous ticks in walk mode with a non-zero velocity command, plus the 2 s after it):
  - heading: yaw rate from gyro along gravity, integrated; drift = measured minus commanded turn, deg/s
  - tilt: roll/pitch from body gravity, mean and max; fell = tilt > 30 deg or the brain left walk mode
  - per joint: error = present - goal in model radians. The goal is shifted by the lag that minimises the error
    (the servos follow about 4 ticks late), then bias (mean), rms (spread), lag (ms) and amplitude ratio
    (present swing / goal swing) are kept; bias is also split by the joint's own leg in stance vs swing
    (stance = that leg's ankle+knee+hip-pitch current > 1.5 x the other leg's).
The report compares left with right per joint and the newest walks with the earlier ones (same --note groups
conditions, for example "usb lead left" before the lead is replaced). It flags; it changes nothing on the robot.
"""
import argparse
import glob
import gzip
import json
import math
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "pi"))
sys.path.insert(0, os.path.join(HERE, "..", "pi", "microduck_rt"))
from joint_signs import MOTOR_OFFSET, MOTOR_SIGN  # noqa: E402
from constants import MOTOR_TO_ID  # noqa: E402

IDS = list(range(1, 15))
ID_TO_NAME = {v: k for k, v in MOTOR_TO_ID.items()}
NAMES = [ID_TO_NAME[i] for i in IDS]          # pos_tick / cur_ma index order (ID 1..14)
TICK = 2 * math.pi / 4096
LEG_JOINTS = ("hip_yaw", "hip_roll", "hip_pitch", "knee", "ankle")
LOAD_JOINTS = ("ankle", "knee", "hip_pitch")
MAX_LAG = 10
POST_S = 2.0
MERGE_GAP_S = 0.5
FALL_TILT_DEG = 30.0

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))       # microduck-sim
LEDGER_DIR = os.path.join(ROOT, "walk-ledger")
LEDGER = os.path.join(LEDGER_DIR, "ledger.jsonl")
REPORT = os.path.join(LEDGER_DIR, "REPORT.md")
RUNS = os.path.join(LEDGER_DIR, "runs.jsonl")
STILL = os.path.join(LEDGER_DIR, "still.jsonl")
RAW = os.path.expanduser("~/duck-walks/raw")


def to_model(name, tick):
    return ((tick - 2048) * TICK - MOTOR_OFFSET[name]) * MOTOR_SIGN[name]


def open_log(path):
    return gzip.open(path, "rt") if path.endswith(".gz") else open(path, errors="replace")


def walk_rows(path):
    """Rows needed for walks: walk-mode rows plus the rows right after (stop/fall). Others are skipped unparsed."""
    with open_log(path) as f:
        for line in f:
            if '"mode": "walk"' in line or '"mode": "stand"' in line or '"mode": "stop"' in line \
                    or '"mode": "monitor"' in line:
                try:
                    yield json.loads(line)
                except ValueError:
                    continue


def moving(r):
    c = r.get("cmd") or {}
    return r.get("mode") == "walk" and any(abs(c.get(k) or 0) > 1e-6 for k in ("vx", "vy", "vtheta"))


def segments(rows):
    """[(walk_rows, post_rows)] with walk_rows the commanded-motion ticks (zero gaps < MERGE_GAP_S merged)."""
    out, cur, post, last_move = [], None, [], None
    for r in rows:
        t = r.get("t")
        if t is None:
            continue
        if moving(r):
            if cur is not None and post and t - last_move > MERGE_GAP_S:
                out.append((cur, post)); cur, post = None, []
            if cur is None:
                cur, post = [], []
            cur.extend(post); post = []
            cur.append(r); last_move = t
        elif cur is not None:
            if t - last_move <= POST_S:
                post.append(r)
            else:
                out.append((cur, post)); cur, post = None, []
    if cur is not None:
        out.append((cur, post))
    return out


def yaw_rate(r):
    g, gb = r.get("gyro_body"), r.get("gb")
    if not g or not gb:
        return None
    n = math.sqrt(sum(x * x for x in gb)) or 1.0
    return -sum(a * b for a, b in zip(g, gb)) / n


def tilt_deg(r):
    gb = r.get("gb")
    if not gb or not r.get("imu_valid", True):
        return None
    n = math.sqrt(sum(x * x for x in gb)) or 1.0
    return math.degrees(math.acos(max(-1.0, min(1.0, -gb[2] / n))))


def stance_side(r):
    cu = r.get("cur_ma")
    if not cu:
        return None
    s = {side: sum(abs(cu[NAMES.index(f"{side}_{j}")] or 0) for j in LOAD_JOINTS) for side in ("left", "right")}
    if s["left"] > 1.5 * s["right"]:
        return "left"
    if s["right"] > 1.5 * s["left"]:
        return "right"
    return None


def joint_series(rows, name):
    k = NAMES.index(name)
    pos, goal = [], []
    for r in rows:
        p, g = r.get("pos_tick"), r.get("goal_tick") or {}
        gv = g.get(str(IDS[k])) if isinstance(g, dict) else None
        pv = p[k] if p and k < len(p) else None
        pos.append(None if pv is None else to_model(name, pv))
        goal.append(None if gv is None else to_model(name, gv))
    return pos, goal


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def std(xs):
    xs = [x for x in xs if x is not None]
    if len(xs) < 2:
        return None
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def track(pos, goal, sides, side):
    """Lag-aligned tracking of one joint: error = pos[i] - goal[i - lag]."""
    best = None
    for lag in range(MAX_LAG + 1):
        e = [p - goal[i - lag] for i, p in enumerate(pos)
             if i >= lag and p is not None and goal[i - lag] is not None]
        if len(e) < 10:
            continue
        m = sum(e) / len(e)
        rms = math.sqrt(sum((x - m) ** 2 for x in e) / len(e))
        if best is None or rms < best[1]:
            best = (lag, rms, m)
    if best is None:
        return None
    lag, rms, bias = best
    err = [(p - goal[i - lag]) if i >= lag and p is not None and goal[i - lag] is not None else None
           for i, p in enumerate(pos)]
    sp, sg = std(pos), std(goal)
    return dict(lag_ticks=lag, bias=round(bias, 4), rms=round(rms, 4),
                amp=round(sp / sg, 3) if sp and sg and sg > 1e-4 else None,
                bias_stance=_r(mean([e for e, s in zip(err, sides) if s == side])),
                bias_swing=_r(mean([e for e, s in zip(err, sides) if s is not None and s != side])),
                goal_swing=round(sg, 4) if sg else None)


def _r(x, n=4):
    return None if x is None else round(x, n)


def analyse_segment(walk, post, source, log_end=False):
    t0, t1 = walk[0]["t"], walk[-1]["t"]
    dts = [b["t"] - a["t"] for a, b in zip(walk, walk[1:])]
    dt = sorted(dts)[len(dts) // 2] if dts else 0.02
    yaw = 0.0
    cmd_yaw = 0.0
    dist = 0.0
    for a, b in zip(walk, walk[1:]):
        d = b["t"] - a["t"]
        if d > 0.1:
            continue
        w = yaw_rate(a)
        if w is not None:
            yaw += w * d
        c = a.get("cmd") or {}
        cmd_yaw += (c.get("vtheta") or 0) * d
        dist += math.hypot(c.get("vx") or 0, c.get("vy") or 0) * d
    dur = max(t1 - t0, 1e-3)
    tilts = [x for x in (tilt_deg(r) for r in walk + post) if x is not None]
    left_walk = next((r.get("mode") for r in post if r.get("mode") != "walk"), None)
    if left_walk is None and log_end:
        left_walk = "log-end"  # the log stopped inside the walk or right after it (power pulled, brain killed)
    fell = (max(tilts) if tilts else 0) > FALL_TILT_DEG or left_walk in ("stand", "stop", "log-end")
    cmds = [r.get("cmd") or {} for r in walk]
    sides = [stance_side(r) for r in walk]
    joints = {}
    for name in NAMES:
        if not any(name.endswith(j) for j in LEG_JOINTS):
            continue
        pos, goal = joint_series(walk, name)
        side = "left" if name.startswith("left") else "right"
        joints[name] = track(pos, goal, sides, side)
    loops = [r.get("loop_ms") for r in walk if r.get("loop_ms") is not None]
    return dict(
        source=source, t_start=round(t0, 2), when=time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(t0)),
        dur_s=round(dur, 2), ticks=len(walk), hz=round(1 / dt, 1) if dt else None,
        loop_ms_p90=_r(sorted(loops)[int(0.9 * (len(loops) - 1))] if loops else None, 1),
        cmd_vx=_r(mean([c.get("vx") for c in cmds]), 3), cmd_vtheta=_r(mean([c.get("vtheta") for c in cmds]), 3),
        cmd_dist_m=round(dist, 2),
        yaw_deg=round(math.degrees(yaw), 1), cmd_yaw_deg=round(math.degrees(cmd_yaw), 1),
        drift_deg_s=round(math.degrees(yaw - cmd_yaw) / dur, 2),
        tilt_mean=_r(mean(tilts), 2), tilt_max=_r(max(tilts) if tilts else None, 1),
        fell=bool(fell), ended_in=left_walk or "walk",
        stance_share={s: round(sides.count(s) / len(sides), 2) for s in ("left", "right")},
        servo_v_min=_r(min([r["servo_v"][1] for r in walk if r.get("servo_v") and r["servo_v"][1]] or [None],
                           key=lambda v: v if v is not None else 99), 2),
        policy_models=walk[0].get("models"),
        joints=joints)


def still_record(path, source):
    """Standing still under the policy (walk mode, zero command): left share of the load-bearing leg current and
    the median roll (+ = leaning left, body y points left). A one-sided weight shows up here without any stepping."""
    L = R = 0.0
    rolls = []
    for r in walk_rows(path):
        if r.get("mode") != "walk" or moving(r) or not r.get("cur_ma") or r.get("policy") not in ("stand", "walk"):
            continue
        cu = r["cur_ma"]
        L += sum(abs(cu[NAMES.index("left_" + j)] or 0) for j in LOAD_JOINTS)
        R += sum(abs(cu[NAMES.index("right_" + j)] or 0) for j in LOAD_JOINTS)
        gb = r.get("gb")
        if gb and r.get("imu_valid", True):
            rolls.append(math.degrees(math.atan2(gb[1], -gb[2])))
    if len(rolls) < 100 or L + R <= 0:
        return None
    rolls.sort()
    return dict(source=source, kind="still", ticks=len(rolls), left_share=round(L / (L + R), 3),
                roll_median_deg=round(rolls[len(rolls) // 2], 2))


def load_jsonl(path):
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in open(path) if l.strip()]


def write_jsonl(path, rows):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def analyse_logs(paths, note):
    os.makedirs(LEDGER_DIR, exist_ok=True)
    ledger = load_jsonl(LEDGER)
    done = 0
    for p in paths:
        src = os.path.basename(p).replace(".gz", "")
        old = {r["t_start"]: r for r in ledger if r["source"] == src}
        ledger = [r for r in ledger if r["source"] != src]
        segs = [(w, post) for w, post in segments(walk_rows(p)) if len(w) >= 10]  # under 0.2 s: no step
        for k, (w, post) in enumerate(segs):
            last_t = (post or w)[-1]["t"]
            rec = analyse_segment(w, post, src, log_end=k == len(segs) - 1 and last_t - w[-1]["t"] < POST_S - 0.1)
            prev = old.get(rec["t_start"])
            rec["note"] = prev.get("note") if prev and prev.get("note") else note
            ledger.append(rec)
        done += len(segs)
        print(f"{src}: {len(segs)} walks")
        st = still_record(p, src)
        stills = [r for r in load_jsonl(STILL) if r["source"] != src]
        if st:
            prev = next((r for r in load_jsonl(STILL) if r["source"] == src), None)
            st["note"] = prev.get("note") if prev and prev.get("note") else note
            stills.append(st)
        write_jsonl(STILL, sorted(stills, key=lambda r: r["source"]))
    ledger.sort(key=lambda r: r["t_start"])
    write_jsonl(LEDGER, ledger)
    return done


def sync(host, note):
    """Copy new or grown brain logs (rsync appends; the A7Z side runs at nice 19, idle IO), then analyse them."""
    os.makedirs(RAW, exist_ok=True)
    before = {p: os.path.getsize(p) for p in glob.glob(os.path.join(RAW, "duck_wired_log_*.jsonl"))}
    t0 = time.time()
    cmd = ["rsync", "-a", "--append-verify", "-z", "--timeout=30",
           "--rsync-path=nice -n 19 ionice -c3 rsync",
           f"{host}:duck-logs/duck_wired_log_*.jsonl", RAW + "/"]
    rc = subprocess.run(cmd).returncode
    after = {p: os.path.getsize(p) for p in glob.glob(os.path.join(RAW, "duck_wired_log_*.jsonl"))}
    changed = sorted(p for p, s in after.items() if before.get(p) != s)
    n = analyse_logs(changed, note) if changed else 0
    rec = dict(ts=round(time.time(), 1), when=time.strftime("%Y-%m-%d %H:%M:%S"), host=host, rsync_rc=rc,
               logs_changed=len(changed), walks=n, secs=round(time.time() - t0, 1), note=note)
    with open(RUNS, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"sync: rsync exit {rc}, {len(changed)} logs changed, {n} walks analysed")
    return rc


def pair_stats(recs, joint):
    out = {}
    for side in ("left", "right"):
        js = [r["joints"].get(f"{side}_{joint}") for r in recs]
        js = [j for j in js if j]
        out[side] = dict(n=len(js), bias=_r(mean([j["bias"] for j in js])),
                         stance=_r(mean([j["bias_stance"] for j in js])),
                         rms=_r(mean([j["rms"] for j in js])),
                         lag_ms=_r(mean([j["lag_ticks"] * 20 for j in js]), 0),
                         amp=_r(mean([j["amp"] for j in js]), 2))
    return out


def deg(x):
    return "-" if x is None else f"{math.degrees(x):+.1f}"


def report(last):
    ledger = load_jsonl(LEDGER)
    lines = ["# Walk ledger report", "",
             f"Generated {time.strftime('%Y-%m-%d %H:%M')} from `walk-ledger/ledger.jsonl` ({len(ledger)} walks). "
             "Angles in degrees, model frame; error = present - goal after the lag shift. Built by "
             "`guide/firmware/mac/walk_ledger.py`.", ""]
    if not ledger:
        lines.append("No walks yet.")
    else:
        recent = ledger[-last:]
        earlier = ledger[:-last]
        lines += ["## Newest walks", ""]
        for r in reversed(recent[-12:]):
            lines.append(f"- {r['when']} ({r['source']}{', ' + r['note'] if r.get('note') else ''}): "
                         f"{r['dur_s']} s, vx {r['cmd_vx']} vth {r['cmd_vtheta']}, drift {r['drift_deg_s']:+} deg/s, "
                         f"tilt mean {r['tilt_mean']} max {r['tilt_max']}, {r['hz']} Hz, "
                         f"stance L/R {r['stance_share']['left']}/{r['stance_share']['right']}"
                         f"{', FELL (' + r['ended_in'] + ')' if r['fell'] else ''}")
        lines += ["", f"## Left against right, newest {len(recent)} walks", ""]
        flags = []
        for j in LEG_JOINTS:
            s = pair_stats(recent, j)
            L, R = s["left"], s["right"]
            lines.append(f"- {j}: bias L {deg(L['bias'])} R {deg(R['bias'])}; in own stance L {deg(L['stance'])} "
                         f"R {deg(R['stance'])}; rms L {deg(L['rms'])} R {deg(R['rms'])}; lag L {L['lag_ms']} "
                         f"R {R['lag_ms']} ms; amplitude L {L['amp']} R {R['amp']}")
            if L["stance"] is not None and R["stance"] is not None and \
                    abs(abs(L["stance"]) - abs(R["stance"])) > math.radians(3):
                worse = "left" if abs(L["stance"]) > abs(R["stance"]) else "right"
                flags.append(f"{worse} {j} sags more under its own stance ({deg(L['stance'])} vs {deg(R['stance'])})")
            if L["amp"] and R["amp"] and abs(L["amp"] - R["amp"]) > 0.15:
                flags.append(f"{j} amplitude differs L {L['amp']} R {R['amp']}")
            if L["lag_ms"] is not None and R["lag_ms"] is not None and abs(L["lag_ms"] - R["lag_ms"]) >= 40:
                flags.append(f"{j} lag differs L {L['lag_ms']} R {R['lag_ms']} ms")
        drifts = [r["drift_deg_s"] for r in recent if r["dur_s"] >= 1.5]
        if len(drifts) >= 3 and (all(d > 1 for d in drifts) or all(d < -1 for d in drifts)):
            flags.append(f"heading drifts the same way on every walk ({mean(drifts):+.1f} deg/s, "
                         f"{'left' if mean(drifts) > 0 else 'right'})")
        sl = mean([r["stance_share"]["left"] for r in recent])
        sr = mean([r["stance_share"]["right"] for r in recent])
        if sl is not None and sr is not None and abs(sl - sr) > 0.1:
            flags.append(f"stance time uneven: left {sl:.2f}, right {sr:.2f} of ticks")
        slow = [r for r in recent if r["hz"] and r["hz"] < 45]
        if slow:
            flags.append(f"control loop under 45 Hz on {len(slow)} walks (lowest {min(r['hz'] for r in slow)} Hz; "
                         "the 50 Hz policy diverged at 36 Hz on 10/23): check CPU clock and temperature")
        falls = sum(r["fell"] for r in recent)
        lines += ["", "## Flags (what to look at; nothing here is applied to the robot)", ""]
        lines += [f"- {f}" for f in flags] or ["- none"]
        lines.append(f"- falls: {falls} of {len(recent)} newest walks")
        if earlier:
            lines += ["", f"## Newest {len(recent)} against the {len(earlier)} before", ""]
            for j in LEG_JOINTS:
                a, b = pair_stats(earlier, j), pair_stats(recent, j)
                lines.append(f"- {j} stance bias: L {deg(a['left']['stance'])} -> {deg(b['left']['stance'])}, "
                             f"R {deg(a['right']['stance'])} -> {deg(b['right']['stance'])}")
            lines.append(f"- drift: {mean([r['drift_deg_s'] for r in earlier]) or 0:+.1f} -> "
                         f"{mean([r['drift_deg_s'] for r in recent]) or 0:+.1f} deg/s; falls "
                         f"{sum(r['fell'] for r in earlier)}/{len(earlier)} -> {falls}/{len(recent)}")
        stills = load_jsonl(STILL)
        notes = sorted({r.get("note") for r in ledger + stills if r.get("note")})
        if len(notes) > 1:
            lines += ["", "## By condition (--note)", ""]
            for nt in notes:
                ss = [r for r in stills if r.get("note") == nt]
                if ss:
                    lines.append(f"- {nt}, standing still: left leg share {mean([r['left_share'] for r in ss]):.2f}, "
                                 f"roll {mean([r['roll_median_deg'] for r in ss]):+.1f} deg (+ = leaning left), "
                                 f"{len(ss)} logs")
            for nt in notes:
                rs = [r for r in ledger if r.get("note") == nt]
                if not rs:
                    continue
                lines.append(f"- {nt}: {len(rs)} walks, drift {mean([r['drift_deg_s'] for r in rs]):+.1f} deg/s, "
                             f"falls {sum(r['fell'] for r in rs)}, knee stance L "
                             f"{deg(pair_stats(rs, 'knee')['left']['stance'])} R "
                             f"{deg(pair_stats(rs, 'knee')['right']['stance'])}")
    os.makedirs(LEDGER_DIR, exist_ok=True)
    open(REPORT, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync"); s.add_argument("--host", default=os.environ.get("A7Z_HOST", "a7z"))
    s.add_argument("--note", default=None); s.add_argument("--last", type=int, default=10)
    a = sub.add_parser("analyze"); a.add_argument("logs", nargs="+"); a.add_argument("--note", default=None)
    a.add_argument("--last", type=int, default=10)
    r = sub.add_parser("report"); r.add_argument("--last", type=int, default=10)
    args = ap.parse_args()
    rc = 0
    if args.cmd == "sync":
        rc = sync(args.host, args.note)
    elif args.cmd == "analyze":
        analyse_logs(args.logs, args.note)
    report(args.last)
    sys.exit(1 if rc else 0)


if __name__ == "__main__":
    main()
