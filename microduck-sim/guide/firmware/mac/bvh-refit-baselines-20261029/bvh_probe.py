"""Which bodies' collision bounding boxes the refit changes, per mass model the baselines use (seconds, no stepping).

  nice -n 19 ~/.venvs/microduck-dyn/bin/python bvh_probe.py > results/probe.json
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MAC = os.path.dirname(HERE)
WHOLE = os.path.join(MAC, "..", "..", "..", "hardware-design-20260912", "whole-robot-20260912")
for p in (os.path.join(WHOLE, "delay-repair-20260912"), os.path.join(WHOLE, "dynamics", "realgap-20261014"), MAC, HERE):
    sys.path.insert(0, p)
import bvh_hook  # noqa: E402

bvh_hook.install()
import evaluate_delay as ev  # noqa: E402
from static_gap import cfg  # noqa: E402

SIM = os.path.normpath(os.path.join(MAC, "..", "..", ".."))
MODELS = {
    "asbuilt (sim_suite, approach, pickup_sim)": {},
    "saddle (get-up, namecall, joint-failure study)": {"mass_manifest": os.path.join(SIM, "guide/print/a7z-saddle/balance/manifest-saddle.json")},
    "plugged (teleop batch: sit, kick, groundpick)": {"mass_manifest": os.path.join(SIM, "microduck_rl/cmu/model/manifests/plugged.json")},
    "plugged, com-x -2.25 (seeing pick, stand-saddle)": {
        "mass_manifest": os.path.join(SIM, "microduck_rl/cmu/model/manifests/plugged.json"),
        "mass_parts": [dict(body="trunk_base", mass_kg=-0.05, position_m=[0, 0, 0.0]),
                       dict(body="trunk_base", mass_kg=0.05, position_m=[-2.25 / 1000 * 0.76 / 0.05, 0, 0.0])]},
}
out = {}
for label, extra in MODELS.items():
    c0 = cfg(0.09, model="asbuilt", kp=200, voltage=7.0)
    c0.update(extra)
    m = ev.load(c0)[0]
    acc = bvh_hook._RUNS[-1]
    geoms = {}
    for b in acc.changed:
        bid = m.body(b).id
        geoms[b] = [m.geom(g).name or f"geom{g}" for g in range(m.ngeom)
                    if m.geom_bodyid[g] == bid and (m.geom_contype[g] or m.geom_conaffinity[g])]
    out[label] = dict(changed=acc.changed, colliding_geoms=geoms,
                      unchanged_colliding_bodies=sorted(m.body(b).name for b in acc.geoms if m.body(b).name not in acc.changed))
print(json.dumps(out, indent=1))
