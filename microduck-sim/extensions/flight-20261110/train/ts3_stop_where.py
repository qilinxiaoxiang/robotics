"""Round 3 check: what runs when a pack-walk gate episode stops walking (17.0 s), and how a policy falls there.

  $PY train/ts3_stop_where.py <dir under ckpt> <seed> [<seed> ...]      (Mac mini only: zsh train/mini.sh run '...')

One gate pack_walk episode per seed (manifest nominal, --stand-s 0, tick log on). Prints, per second from 15 s on:
the brain mode, the policy slot, the position gain, the commanded vx seen by the policy, action jumps (steps over
0.5 rad), the largest action step and the trunk tilt; then the fall time. The names come from the tick rows' own
keys, no joint index is used.
"""
import json
import os
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import flight_eval as fe  # noqa: E402


def main():
    # kp=<walk gain> adds --kp-rl; count=<n> runs seeds 0..n-1 and prints only the fall times (no per-second lines)
    opts = dict(x.split("=") for x in sys.argv[2:] if "=" in x)
    d, seeds = sys.argv[1], [int(s) for s in sys.argv[2:] if "=" not in s]
    kp = ["--kp-rl", opts["kp"]] if "kp" in opts else []
    if "count" in opts:
        falls = []
        for seed in range(int(opts["count"])):
            r = fe.episode((str(HERE / "ckpt" / d), str(HERE / "manifests/flightpack-nominal.json"), "walk", seed, 0.0,
                            8.0, False, ["--stand-s", "0"] + kp))
            falls.append(r["fell_at"])
        ft = sorted(f for f in falls if f is not None)
        print(f"{d} pack walk, walk gain {opts.get('kp', 'default 200')}: {len(ft)} falls of {len(falls)}; "
              f"{sum(1 for f in ft if f >= 17.0)} after the stop at 17.0 s; times {ft}", flush=True)
        return
    for seed in seeds:
        log = f"/tmp/ts3_stop_{d}_{seed}.jsonl"
        r = fe.episode((str(HERE / "ckpt" / d), str(HERE / "manifests/flightpack-nominal.json"), "walk", seed, 0.0, 8.0,
                        False, ["--stand-s", "0", "--tick-log", log, "--tick-diag"] + kp))
        rows = [json.loads(x) for x in open(log)]
        os.remove(log)
        print(f"{d} seed {seed}: fell at {r['fell_at']}; row keys {sorted(rows[-1].keys())}", flush=True)
        prev = None
        per = {}
        for x in rows:
            s = int(x["t"])
            p = per.setdefault(s, dict(mode=Counter(), policy=Counter(), kp=Counter(), jumps=0, max_step=0.0, tilt=0.0,
                                       acts=0))
            p["mode"][str(x.get("mode"))] += 1
            p["policy"][str(x.get("policy"))] += 1
            p["kp"][str(x.get("kp"))] += 1
            dg = x.get("diag") or {}
            for k in ("tilt_deg", "tilt"):
                if k in dg:
                    p["tilt"] = max(p["tilt"], abs(float(dg[k])))
            a = x.get("action")
            if a is not None:
                p["acts"] += 1
                if prev is not None:
                    st = max(abs(u - v) for u, v in zip(a, prev))
                    p["max_step"] = max(p["max_step"], st)
                    p["jumps"] += st > 0.5
                prev = a
            else:
                prev = None
        for s in sorted(per):
            if s >= 15:
                p = per[s]
                print(f"  {s:2d} s: mode {dict(p['mode'])} policy {dict(p['policy'])} kp {dict(p['kp'])} policy ticks "
                      f"{p['acts']} jumps {p['jumps']} max step {p['max_step']:.2f} tilt {p['tilt']:.1f}", flush=True)


if __name__ == "__main__":
    main()
