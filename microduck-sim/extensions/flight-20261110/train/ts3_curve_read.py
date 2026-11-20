"""Read a Kaggle teacher training log and print window means of the terms that
could explain why gate results swing from save to save.

usage: ts3_curve_read.py <train log> [window] [first] [last]
Prints one line per window (mean over the window) and, for the same terms,
the iteration-to-iteration standard deviation inside the window.
"""
import json
import re
import statistics as st
import sys

KEYS = [
    ("Mean value loss", "vloss"),
    ("Mean surrogate loss", "surr"),
    ("Mean entropy loss", "entropy"),
    ("Mean anchor loss", "anchor"),
    ("Mean reward", "reward"),
    ("Mean episode length", "eplen"),
    ("Mean action std", "std"),
    ("Episode_Reward/action_rate_l2", "arate"),
    ("Episode_Reward/action_acc_l2", "aacc"),
    ("Episode_Metrics/mean_action_acc", "acc_metric"),
    ("Episode_Reward/track_linear_velocity", "track"),
    ("Episode_Reward/progress_along_cmd", "progress"),
    ("Episode_Reward/air_time", "air"),
    ("Episode_Reward/torque_margin", "torque"),
    ("Episode_Termination/fell_over", "fell"),
    ("Metrics/twist/error_vel_xy", "err_xy"),
    ("Metrics/air_time_mean", "air_s"),
]


def parse(path):
    rows, cur, it = {}, None, None
    head = re.compile(r"Learning iteration (\d+)/")
    anc = re.compile(r"\[anchor\] it (\d+) leg distance to walk61 on no-pack rows ([0-9.]+)")
    for line in open(path, errors="replace"):
        m = head.search(line)
        if m:
            it = int(m.group(1))
            cur = rows.setdefault(it, {})
            continue
        m = anc.search(line)
        if m:
            rows.setdefault(int(m.group(1)), {})["anchor_dist"] = float(m.group(2))
            continue
        if cur is None or ":" not in line:
            continue
        name, _, val = line.rpartition(":")
        name = name.strip()
        for key, short in KEYS:
            if name == key and short not in cur:
                try:
                    cur[short] = float(val)
                except ValueError:
                    pass
    return rows


def main():
    path = sys.argv[1]
    win = int(sys.argv[2]) if len(sys.argv) > 2 else 125
    first = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    last = int(sys.argv[4]) if len(sys.argv) > 4 else 10 ** 9
    rows = parse(path)
    its = sorted(i for i in rows if first <= i <= last)
    shorts = [s for _, s in KEYS] + ["anchor_dist"]
    out = []
    for lo in range(first, (its[-1] if its else 0) + 1, win):
        sel = [rows[i] for i in its if lo <= i < lo + win]
        if not sel:
            continue
        rec = {"from": lo, "to": lo + win - 1, "n": len(sel)}
        for s in shorts:
            vals = [r[s] for r in sel if s in r]
            if vals:
                rec[s] = round(st.mean(vals), 4)
                if len(vals) > 2:
                    rec[s + "_sd"] = round(st.pstdev(vals), 4)
        out.append(rec)
        print(json.dumps(rec))
    return out


if __name__ == "__main__":
    main()
