"""Find walk-policy segments at a forward command in brain logs and print per-segment tilt and action statistics,
so a T1 robot walk can be compared with walk61 walks on the same robot.

    python3 compare_walks.py LOG [LOG...]
    python3 compare_walks.py --extract walk61_see_walks.jsonl WINDOW.part ...   # keep only the walk rows

A segment is consecutive rows in walk mode with a commanded vx above 0.05 lasting at least 1.5 s. Tilt is the angle
between body gravity and straight down; a jump is a tick-to-tick change of any action above 0.5 rad.
"""
import json
import math
import sys


def tilt(gb):
    g = math.sqrt(sum(x * x for x in gb)) or 1.0
    return math.degrees(math.acos(max(-1.0, min(1.0, -gb[2] / g))))


def segments(path):
    seg = []
    for line in open(path):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        cmd = r.get("cmd") or {}
        vx = float(cmd.get("vx") or 0)
        walking = r.get("mode") == "walk" and vx > 0.05 and r.get("gb")
        if walking:
            seg.append(r)
        elif seg:
            yield seg
            seg = []
    if seg:
        yield seg


def stats(seg, name):
    t0 = seg[0]["t"]
    dur = seg[-1]["t"] - t0
    if dur < 1.5:
        return None
    walk_rows = [r for r in seg if r.get("policy") == "walk" and r.get("action")]
    tilts = [tilt(r["gb"]) for r in seg]
    acts = [max(abs(a) for a in r["action"]) for r in walk_rows]
    jumps, prev = [], None
    for r in walk_rows:
        if prev is not None:
            jumps.append(max(abs(x - y) for x, y in zip(r["action"], prev)))
        prev = r["action"]
    first3 = [tilt(r["gb"]) for r in seg if r["t"] - t0 < 3.0]
    miss = sum(1 for r in seg if r.get("missing")) / len(seg)
    vx = (seg[len(seg) // 2].get("cmd") or {}).get("vx")
    srt = sorted(acts) or [0]
    return dict(log=name, start=round(t0, 1), dur=round(dur, 1), vx=vx, tilt_max=round(max(tilts), 1),
                tilt_max_first3=round(max(first3), 1), tilt_mean=round(sum(tilts) / len(tilts), 1),
                act_p95=round(srt[int(0.95 * (len(srt) - 1))], 2), act_max=round(max(srt), 2),
                jumps_over_0p5=sum(1 for j in jumps if j > 0.5), jump_rate_per_s=round(sum(1 for j in jumps if j > 0.5) / dur, 2),
                miss_frac=round(miss, 3), fell=max(tilts) > 45)


def main():
    # --extract OUT: also write the rows of every reported segment to OUT (keeps a large log's walks small)
    args = sys.argv[1:]
    out = None
    if args[:1] == ["--extract"]:
        out, args = open(args[1], "w"), args[2:]
    for p in args:
        name = p.rsplit("/", 1)[-1]
        for seg in segments(p):
            s = stats(seg, name)
            if s:
                print(json.dumps(s))
                if out:
                    out.writelines(json.dumps(r) + "\n" for r in seg)


if __name__ == "__main__":
    main()
