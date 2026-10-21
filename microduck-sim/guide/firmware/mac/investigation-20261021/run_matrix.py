import subprocess, sys, os, json
HERE = os.path.dirname(os.path.abspath(__file__))
M = "/Users/xiangzheng/code/robotics/microduck-sim/microduck_rl/cmu/model/manifests/plugged.json"
PY = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
COMMON = ["--model", "asbuilt", "--manifest", M, "--volt", "7.0", "--drop", "0.04", "--walk-s", "0", "--walk-at", "4", "--sit-at", "9.0"]
runs = []
for tag, S, R in (("A", "1.6", "0.5"), ("B", "0.5", "0.15"), ("C", "0.5", "0")):
    for seed in (0, 1, 2):
        runs.append((f"{tag}_s{seed}", S, R, ["--quack-at", "5.0", "15.0", "--seed", str(seed)]))
# extras: look-up style as a step (seed 0); two quacks 0.7 s apart on stand61 and seated with the short profile (seed 0)
runs.append(("C_lookup_s0", "0.5", "0", ["--quack-at", "5.0", "15.0", "--quack-roll", "0.10", "--quack-yaw", "0", "--quack-pitch", "-0.30", "--seed", "0"]))
runs.append(("B_rapid_s0", "0.5", "0.15", ["--quack-at", "5.0", "5.7", "15.0", "15.7", "--seed", "0"]))
sel = sys.argv[1:]
for name, S, R, extra in runs:
    if sel and name not in sel:
        continue
    cmd = ["timeout", "600", PY, os.path.join(HERE, "quack_sim.py"), "--profile-s", S, "--ramp-s", R, "--out", os.path.join(HERE, "runs", name + ".json")] + COMMON + extra
    p = subprocess.run(cmd, capture_output=True, text=True)
    last = [l for l in p.stdout.splitlines() if l.strip()]
    print(f"== {name} S={S} ramp={R} rc={p.returncode}")
    if p.returncode != 0:
        print(p.stderr[-800:])
    elif last:
        o = json.loads(last[-1])
        for qt, r in o["per_quack"].items():
            if r is None:
                print(f"   quack@{qt}: no data"); continue
            js = ", ".join(f"{n}: peak {j['peak']:+.3f} ({j['peak_frac']:.0%}) t90 {j['t90_of_peak']} s t_half {j['t_half_command']} s back {j['back_within_0p03_after_end_s']} s" for n, j in r["joints"].items())
            print(f"   quack@{qt} {r['mode']}: ran={r['ran']} tilt base {r['base_tilt']} peak {r['peak_tilt']} rise {r['tilt_rise']} swing {r['tilt_swing']} | {js}")
        print(f"   fell_at={o['fell_at']}")
