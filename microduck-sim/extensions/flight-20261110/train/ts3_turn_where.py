"""Round 3 check (2026-11-20): does the heading hold's turn command saturate in the gate's walk, and for whom?

  $PY train/ts3_turn_where.py <dir under ckpt | walk61> <manifest name> <seeds, e.g. 0,1> [probe flags ...]
  e.g.  $PY train/ts3_turn_where.py s3a_60 nominal 0,1 --stand-s 0 --kp-rl 200          (Mac mini only)

One gate walk episode per seed through flight_eval.episode with the tick log and tick diagnostics on. Per 2 s of the
episode: the mean and the largest turn command the policy was given (the tick row's own "turn" key), the heading
drift in degrees since the walk command began (mean of the two feet's world yaw from the tick diagnostics, unwrapped;
the trunk's own yaw is not in the log, so this is a proxy averaged over the gait), and the trunk's path length. The
heading hold's error is minus that drift (it holds the heading the walk starts with). No joint index is used.
"""
import json
import math
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import flight_eval as fe  # noqa: E402


def main():
    d, man, seeds, extra = sys.argv[1], sys.argv[2], [int(s) for s in sys.argv[3].split(",")], sys.argv[4:]
    mdir = (HERE / "../../../microduck_rl/cmu/whole/runtime-overlay/models").resolve() if d == "walk61" else HERE / "ckpt" / d
    for seed in seeds:
        log = f"/tmp/ts3_turn_{d}_{man}_{seed}.jsonl"
        r = fe.episode((str(mdir), str(HERE / f"manifests/flightpack-{man}.json"), "walk", seed, 0.0, 8.0, False,
                        list(extra) + ["--tick-log", log, "--tick-diag"]))
        rows = [json.loads(x) for x in open(log)]
        os.remove(log)
        yaw, prev, acc = [], None, 0.0
        for x in rows:  # unwrapped mean foot yaw, degrees
            dg = x.get("diag") or {}
            if "left" in dg and "right" in dg:
                y = math.degrees(math.atan2(sum(math.sin(math.radians(dg[s]["yaw"])) for s in ("left", "right")),
                                            sum(math.cos(math.radians(dg[s]["yaw"])) for s in ("left", "right"))))
                if prev is not None:
                    acc += (y - prev + 180.0) % 360.0 - 180.0
                prev = y
            yaw.append(acc)
        t_walk = next((x["t"] for x in rows if abs(float(x.get("turn") or 0.0)) > 0 or x["t"] >= 2.0), 2.0)
        y0 = next(y for x, y in zip(rows, yaw) if x["t"] >= t_walk)
        print(f"{d} {man} {' '.join(extra)} seed {seed}: fell at {r['fell_at']}; speed {r['speed']}", flush=True)
        per = {}
        for x, y in zip(rows, yaw):
            p = per.setdefault(int(x["t"] // 2) * 2, dict(n=0, turn=0.0, mx=0.0, y=0.0, path=0.0, last=None))
            tc = float(x.get("turn") or 0.0)
            p["n"] += 1
            p["turn"] += tc
            p["mx"] = max(p["mx"], abs(tc))
            p["y"] += y - y0
            tr = (x.get("diag") or {}).get("trunk")
            if tr:
                if p["last"] is not None:
                    p["path"] += math.hypot(tr[0] - p["last"][0], tr[1] - p["last"][1])
                p["last"] = tr
        for s in sorted(per):
            p = per[s]
            print(f"  {s:2d}-{s + 2:2d} s: turn command mean {p['turn'] / p['n']:+.2f} largest {p['mx']:.2f} rad/s; heading "
                  f"drift since the walk began {p['y'] / p['n']:+7.1f} deg; trunk path {p['path'] * 100:5.1f} cm", flush=True)


if __name__ == "__main__":
    main()
