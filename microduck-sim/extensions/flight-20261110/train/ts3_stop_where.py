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
    if "prewarm" in opts:  # prewarm=<N>: flight_eval FLIGHT_PREWARM
        os.environ["FLIGHT_PREWARM"] = opts["prewarm"]
    if "vth" in opts:  # vth=<rad/s>: a commanded turn while walking (with heading hold off it is the turn command)
        kp = kp + ["--vtheta", opts["vth"]]
    # first=<teacher dir>:<tick>  the teacher drives up to that tick, then the student (which saw every observation)
    # after=<teacher dir>:<tick>  the student drives up to that tick, then the teacher
    for key, var in (("first", "FLIGHT_HANDOVER"), ("after", "FLIGHT_HANDOVER_AFTER")):
        if key in opts:
            td, tk_ = opts[key].split(":")
            os.environ[var] = str(HERE / "ckpt" / td / "walk61.onnx") + ":" + tk_
    if "zero" in opts:  # zero=<tick>: empty the recurrent state once at that control tick (850 = the stop at 17.0 s)
        os.environ["FLIGHT_STATE_ZERO_TICK"] = opts["zero"]
    if "shadow" in opts:
        # shadow=<teacher dir under ckpt>: the privileged teacher's action on every observation the student sees
        # (flight_eval's FLIGHT_DAGGER=0 record: nothing of the teacher is applied). Per second of the episode over
        # all seeds: student-teacher difference, both tick-to-tick steps, the command the policy saw. Columns by the
        # actor layout asserted in ts3_g1_where.check_layout (twist 48:51); the legs/head split by joint name.
        import numpy as np
        os.environ["FLIGHT_DAGGER"] = "0"
        os.environ["FLIGHT_TEACHER"] = str(HERE / "ckpt" / opts["shadow"] / "walk61.onnx")
        per, falls = {}, []
        for seed in range(int(opts.get("count", 10))):
            r = fe.episode((str(HERE / "ckpt" / d), str(HERE / "manifests/flightpack-nominal.json"), "walk", seed, 0.0,
                            8.0, False, ["--stand-s", "0"] + kp))
            falls.append(r["fell_at"])
            dg = r["dagger"]
            obs, lab, stu = (np.asarray(dg[k], np.float32) for k in ("obs", "lab", "stu"))
            tk = np.asarray(dg["tick"]) - int(dg["tick"][0])
            for i in range(1, len(tk)):
                grp = "fell after the stop" if (r["fell_at"] or 0) >= 17.0 else "stood"
                p = per.setdefault((grp, int(tk[i] // 50)), dict(n=0, e2=0.0, sstep=0.0, tstep=0.0, vx=0.0, turn=0.0, big=0))
                e = stu[i] - lab[i]
                p["n"] += 1
                p["e2"] += float((e ** 2).mean())
                p["sstep"] += float(np.abs(stu[i] - stu[i - 1]).max())
                p["tstep"] += float(np.abs(lab[i] - lab[i - 1]).max())
                p["vx"] += float(obs[i, 48])
                p["turn"] += float(abs(obs[i, 50]))
                p["big"] += int(np.abs(e).max() > 0.2)
        wb = sys.modules["walk_brain"]
        print(f"{d} shadowed by {opts['shadow']}, pack walk, walk gain {opts.get('kp', 'default 200')}: falls {falls}", flush=True)
        for grp, s in sorted(per):
            p = per[(grp, s)]
            if s >= int(opts.get("from", 12)) or s < 3:
                print(f"  [{grp}] {s:2d} s: ticks {p['n']} command vx {p['vx'] / p['n']:.3f} |turn| {p['turn'] / p['n']:.3f}  student-teacher "
                      f"mse {p['e2'] / p['n']:.5f} (ticks with a joint over 0.2 rad apart {p['big'] / p['n']:.2f})  step student "
                      f"{p['sstep'] / p['n']:.3f} teacher-on-same-states {p['tstep'] / p['n']:.3f}", flush=True)
        return
    if "count" in opts:
        falls = []
        for seed in range(int(opts["count"])):
            r = fe.episode((str(HERE / "ckpt" / d), str(HERE / "manifests/flightpack-nominal.json"), "walk", seed, 0.0,
                            8.0, False, ["--stand-s", "0"] + kp))
            falls.append(r["fell_at"])
        ft = sorted(f for f in falls if f is not None)
        if "zero" in opts:
            print(f"  state emptied at tick {fe.DIAG['stat'].get('state_zeroed_at_tick')} of the last episode", flush=True)
        print(f"  switches {[f'{k}={opts[k]}' for k in ('first', 'after') if k in opts]}; last episode's counters "
              f"{ {k: v for k, v in fe.DIAG['stat'].items() if 'handover' in k or 'obs_set' in k or 'gain_flag' in k or 'prewarm' in k} }", flush=True)
        print(f"{d} pack walk, walk gain {opts.get('kp', 'default 200')}{', state emptied at tick ' + opts['zero'] if 'zero' in opts else ''}: {len(ft)} falls of {len(falls)}; "
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
            if dg.get("trunk"):
                p.setdefault("xy0", dg["trunk"][:2])
                p["xy1"] = dg["trunk"][:2]
            gb = x.get("gb")
            if gb:  # trunk tilt from the logged body-frame gravity, degrees from upright
                import math
                p["tilt"] = max(p["tilt"], math.degrees(math.acos(max(-1.0, min(1.0, -gb[2] / math.hypot(*gb))))))
                p["pitch"] = p.get("pitch", 0.0) + math.degrees(math.atan2(-gb[0], -gb[2]))
                p["gn"] = p.get("gn", 0) + 1
            p["turn"] = p.get("turn", 0.0) + abs(float(x.get("turn") or 0.0))
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
            if s >= int(opts.get("from", 15)):
                p = per[s]
                n = sum(p["mode"].values())
                dist = ((p["xy1"][0] - p["xy0"][0]) ** 2 + (p["xy1"][1] - p["xy0"][1]) ** 2) ** 0.5 if "xy0" in p else 0.0
                print(f"  {s:2d} s: policy {dict(p['policy'])} kp {dict(p['kp'])} jumps {p['jumps']} max step "
                      f"{p['max_step']:.2f} max tilt {p['tilt']:.1f} deg mean pitch {p.get('pitch', 0.0) / max(p.get('gn', 0), 1):+.1f} "
                      f"deg trunk moved {dist * 100:.1f} cm |turn cmd| {p['turn'] / n:.2f}", flush=True)


if __name__ == "__main__":
    main()
