"""Which difference between the training env and the runtime simulation makes a universal3-trained policy fall?

  python3 train/ts_sep.py <models dir under train/ckpt> <load: none|nobatt|load100|...> <tag>[=<probe flags>] ...
  python3 train/ts_sep.py tsc_750 none base nodrop="--drop 0" volt82="--volt 8.2"

Each tag is one runtime-simulation walk case (flight_eval.py on the Mac mini: 20 s, vx 0.25 from 2 s for 15 s, seeds
0..19, --volt 7.6 --drop 0.036) with the tag's probe flags appended last (they win), so one difference at a time is
switched toward the training env. Result files eval/sep_<dir>_<load>_<tag>.json; printed per tag: falls of 20, fall
times, median upright speed, leg torque p99. Existing result files are reused. A tag without flags uses the built-in
table below.
"""
import json
import subprocess
import sys
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
TABLE = {
    "base": "",
    "nodrop": "--drop 0",                                  # no dropped servo reads (the Brain then never skips a tick)
    "volt82": "--volt 8.2",                                # top of the training supply range (6.5 to 8.2 V)
    "volt10": "--volt 10",                                 # torque clamp well above anything trained
    "adelay0": "--action-delay 0",
    "sdelay0": "--sensor-delay 0",
    "nodelay": "--action-delay 0 --sensor-delay 0",
    "ramp15": "--walk-ramp 1.5",
    "fric09": "--bam-friction-scale 0.9",
    "fric11": "--bam-friction-scale 1.1",
    "elliptic": "--cone elliptic",
    "vx020": "--vx 0.20",
    "vx015": "--vx 0.15",
    "comp": "--compensation",                              # the Brain extrapolates stale readings (walk_wired --compensation)
    "v19": "--model v19 --historical-model ts_sep_study",  # the earlier mass model
    "mu08": "--floor-mu 0.8", "mu12": "--floor-mu 1.2", "kp250": "--kp-rl 250", "kp160": "--kp-rl 160",
    "benign":"--drop 0 --action-delay 0 --sensor-delay 0 --volt 8.2",
}
# tags that switch a constant of the runtime Brain (walk_brain) instead of a probe flag: FLIGHT_BRAIN_SET / joint range
ENV = {
    "nohead": "FLIGHT_BRAIN_SET='{\"HEADING_KP\": 0, \"HEADING_KI\": 0}' ",      # heading hold off: turn command stays 0
    "turn1": "FLIGHT_BRAIN_SET='{\"TURN_MAX\": 1.0}' ",                           # heading hold within the trained +-1.0
    "nocurlim": "FLIGHT_CFG_SET='{\"current_limit\": 100}' ",   # servo current limit off: torque bounded by the supply only
    "curlim175": "FLIGHT_CFG_SET='{\"current_limit\": 1.75}' ",  # the training env's limit (bam XL330 default, 0.64 N m)
    "curlim20":"FLIGHT_CFG_SET='{\"current_limit\": 2.0}' ",
    "curlim25": "FLIGHT_CFG_SET='{\"current_limit\": 2.5}' ",
    "widerange":"SPK3DIAG_JOINT_RANGE='" + json.dumps({f"{s}_{j}": [-3.0, 3.0] for s in ("left", "right") for j in
                                                         ("hip_yaw", "hip_roll", "hip_pitch", "knee", "ankle")}) + "' ",
}
TABLE.update({k: "" for k in ENV})

models, load = sys.argv[1:3]
tags = []
for t in sys.argv[3:]:
    name, _, flags = t.partition("=")
    tags.append((name, flags if "=" in t else TABLE[name]))
stand = "" if load == "none" else "--stand-s 0"            # as accept_universal.py runs its pack cases
mini = str(TRAIN / "mini.sh")
todo = [(n, f) for n, f in tags if not (TRAIN / f"eval/sep_{models}_{load}_{n}.json").exists()]
if todo:
    subprocess.run(["zsh", mini, "push"], check=True, capture_output=True)
    for i in range(0, len(todo), 6):
        cmd = "; ".join(
            f"{ENV.get(n, '')}$PY train/flight_eval.py --models train/ckpt/{models} --manifest train/manifests/flightpack-{load}.json "
            f"--case walk --episodes 20 --workers 8 --extra='{(stand + ' ' + f).strip()}' "
            f"--out train/eval/sep_{models}_{load}_{n}.json > /dev/null 2>&1; echo done {n}" for n, f in todo[i:i + 6])
        r = subprocess.run(["zsh", mini, "run", cmd], capture_output=True, text=True)
        print(r.stdout.replace("busy\n", "").strip()[-200:].replace("\n", " "), r.stderr.strip()[-200:], flush=True)
        subprocess.run(["zsh", mini, "pull"], check=True, capture_output=True)
for n, f in tags:
    p = TRAIN / f"eval/sep_{models}_{load}_{n}.json"
    if not p.exists():
        print(f"{models} {load} {n}: missing")
        continue
    j = json.loads(p.read_text())
    s, eps = j["summary"], j["episodes"]
    p99 = [e["leg_force_p99_nm"] for e in eps if e.get("leg_force_p99_nm") is not None]
    print(f"{models} {load} {n:9s} [{f}]: falls {s['falls']}/20, times {[round(x, 1) for x in s['fall_times']][:8]}, "
          f"speed {s['speed_median_upright']}, leg p99 {round(sorted(p99)[len(p99) // 2], 3) if p99 else None}", flush=True)
