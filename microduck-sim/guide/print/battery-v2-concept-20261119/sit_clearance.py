"""Seated-pose clearance of the battery V2 backpack envelopes.

Runs brain_sim_check.main() (the real Brain sit, current as-built model) with mujoco.mj_step wrapped so every
50th step is sampled. For each sample: every box (trunk frame, mm) is placed with trunk_base's pose and its lowest
corner height above the floor (z = 0) is recorded. Boxes come from concept.json: the chosen lower tier, today's lower
tier and front plate, the upper tier, the contact pads and every explored layout (opt_<letter>_<i>).
Prints standing and seated numbers as JSON and writes them to sit_clearance.json next to this file.

    Mac mini: ~/.venvs/microduck-dyn/bin/python sit_clearance.py      (about a minute)
"""
import json, os, sys, itertools
import numpy as np
import mujoco

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.abspath(os.path.join(HERE, "../../firmware/mac"))
CONCEPT = os.path.join(HERE, "concept.json")
sys.path.insert(0, MAC)
os.chdir(MAC)
cj = json.load(open(CONCEPT))
outl = cj["outline"]
BOXES = {"new_lower": outl["lower_tier"], "today_lower": outl["today_lower_tier"],
         "today_front_plate": outl["today_front_plate"], "upper": outl["upper_tier"],
         "contact_pads": cj["contacts"]["pad_box"]}
for k, o in cj.get("options", {}).items():
    for i, b in enumerate(o["boxes"]):
        BOXES[f"opt_{k}_{i}"] = b
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
import io, contextlib, runpy  # noqa: E402
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
out = {"stand": stand[-1] if stand else None, "seated": seated[-1] if seated else None,
       "min_after_sit_cmd": low, "fell": summary.get("fell"), "sit": summary.get("sit"),
       "t_end": samples[-1]["t"], "boxes": BOXES,
       "model": "brain_sim_check --model asbuilt --manifest current (battery-20261104), real Brain sit"}
json.dump(out, open(os.path.join(HERE, "sit_clearance.json"), "w"), indent=1, default=str)
print(json.dumps({k: out[k] for k in ("stand", "seated", "min_after_sit_cmd", "fell", "sit", "t_end")}, default=str))
