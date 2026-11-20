"""Seated-pose clearance of the battery V2 backpack envelope.

Runs brain_sim_check.main() (the real Brain sit, current as-built model) with mujoco.mj_step wrapped so every
50th step is sampled. For each sample: the new and today's backpack boxes (trunk frame, mm, from concept.json)
are placed with trunk_base's pose and their lowest corner height above the floor (z = 0) is recorded, plus the
lowest robot mesh vertex outside the feet. Prints standing and seated numbers as JSON on stderr-free stdout tail.
"""
import json, os, sys, itertools
import numpy as np
import mujoco

MAC = os.path.expanduser("~/code/robotics/microduck-sim/guide/firmware/mac")
CONCEPT = os.path.expanduser("~/code/robotics/microduck-sim/guide/print/battery-v2-concept-20261119/concept.json")
sys.path.insert(0, MAC)
os.chdir(MAC)
outl = json.load(open(CONCEPT))["outline"]
BOXES = {"new_lower": outl["lower_tier"], "today_lower": outl["today_lower_tier"], "upper": outl["upper_tier"],
         "contacts": [[-77.0, -10.0, -55.0], [-75.0, 10.0, -49.0]]}
samples = []
_step = mujoco.mj_step
n = [0]


def corners(b):
    lo, hi = np.array(b[0]), np.array(b[1])
    return np.array([[(lo, hi)[i][0], (lo, hi)[j][1], (lo, hi)[k][2]] for i, j, k in itertools.product((0, 1), repeat=3)])


def step(m, d, *a):
    _step(m, d, *a)
    n[0] += 1
    if n[0] % 50:
        return
    t = m.body("trunk_base").id
    R, p = d.xmat[t].reshape(3, 3), d.xpos[t]
    row = {"t": round(float(d.time), 2)}
    for k, b in BOXES.items():
        W = corners(b) / 1000.0 @ R.T + p
        row[k] = round(float(W[:, 2].min() * 1000), 1)
    gb = R.T @ np.array([0, 0, -1.0])
    row["pitch_deg"] = round(float(np.degrees(np.arctan2(gb[0], -gb[2]))), 1)
    row["trunk_z"] = round(float(p[2] * 1000), 1)
    samples.append(row)


sys.argv = ["brain_sim_check.py", "--model", "asbuilt", "--manifest", "current", "--stand-s", "1", "--walk-at", "3",
            "--walk-s", "0.5", "--vx", "0", "--sit-at", "4", "--after-walk", "14"]
mujoco.mj_step = step
import io, contextlib, atexit, runpy  # noqa: E402
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    try:
        runpy.run_path(os.path.join(MAC, "brain_sim_check.py"), run_name="__main__")
    except SystemExit as e:
        sys.stderr.write(f"SystemExit {e.code}\n")
res = buf.getvalue().strip().splitlines()
summary = json.loads(res[-1]) if res else {}
stand = [s for s in samples if 2.0 <= s["t"] <= 3.0]
seated = [s for s in samples if s["t"] >= samples[-1]["t"] - 2.0]
low = {k: min(s[k] for s in samples if s["t"] >= 4.0) for k in BOXES}
print(json.dumps({"stand": stand[-1] if stand else None, "seated": seated[-1] if seated else None,
                  "min_after_sit_cmd": low, "fell": summary.get("fell"), "sit": summary.get("sit"),
                  "t_end": samples[-1]["t"]}, default=str))
