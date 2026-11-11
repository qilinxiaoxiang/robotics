"""Scan real MicroDuck brain logs for bend -> stand hand-backs (2026-11-11, report only).

For every switch from a bend mode (groundpick / seepick / pick) back to stand, print the trunk tilt from gravity
during the 3 s after the switch and whether the log shows a fall (tilt over 60 deg).
Usage: python3 robot_handback_scan.py LOG.jsonl [...]
"""
import json
import math
import sys

BEND = ("groundpick", "seepick", "pick", "bow")


def tilt(r):
    g = r.get("gb")
    if not g:
        return None
    n = math.sqrt(sum(x * x for x in g)) or 1.0
    return math.degrees(math.acos(max(-1.0, min(1.0, -g[2] / n))))


def scan(path):
    rows = []
    with open(path) as f:
        for line in f:
            if not line.startswith("{"):
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if "t" in r and "mode" in r:
                rows.append(r)
    out = []
    for i in range(1, len(rows)):
        a, b = str(rows[i - 1]["mode"]), str(rows[i]["mode"])
        if any(k in a for k in BEND) and not any(k in b for k in BEND):
            t0 = rows[i]["t"]
            win = [tilt(r) for r in rows[i:] if r["t"] - t0 < 3.0]
            win = [x for x in win if x is not None]
            pre = [tilt(r) for r in rows[max(0, i - 200):i] if t0 - r["t"] < 4.0]
            pre = [x for x in pre if x is not None]
            out.append(dict(file=path.split("/")[-1], t=round(t0, 2), from_mode=a, to_mode=b,
                            bend_tilt_max=round(max(pre), 1) if pre else None,
                            after_tilt_max=round(max(win), 1) if win else None,
                            after_tilt_end=round(win[-1], 1) if win else None,
                            fell=bool(win and max(win) > 60)))
    return out


if __name__ == "__main__":
    res = []
    for p in sys.argv[1:]:
        res += scan(p)
    for r in res:
        print(json.dumps(r))
    print(json.dumps(dict(handbacks=len(res), falls=sum(r["fell"] for r in res))))
