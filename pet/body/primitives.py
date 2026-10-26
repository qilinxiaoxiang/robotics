"""Primitive discovery: which entries of the known policy and skill library this actuator and sensor set supports.

Each rule names the joints and sensor kinds it needs. A rule whose needs are all present and ok enters the card. A
needed joint that is failed (ok false) drops the rule, unless the rule lists the joint in `survives` and the sim
failure study (failure_study/results.json) marks the joint `still_walks` both frozen and weak (at most 1 fall in 10
and at least half the healthy distance);
then the rule stays with a precondition saying so. Preconditions hold only what the mind can check or act on; where a
primitive comes from and which safety limit its executor keeps (`source`) goes to the card's notes. Bounds marked
"rules-table" are design defaults no robot run has confirmed.
"""
import json
import os

from .profiles import DUCK_HEAD, DUCK_LEGS

HERE = os.path.dirname(os.path.abspath(__file__))
STUDY = os.path.join(HERE, "failure_study", "results.json")

WALK_SRC = "walk61.onnx at KP_RL 200, 4 s walks at 0.25 m/s (microduck-sim/CURRENT-STATE.json walking_policy)"

RULES = [
    # MicroDuck: Pollen policies on the 14 policy joints (walk_brain.py), jaw via jaw_ctl.py
    dict(name="walk", body="microduck", joints=DUCK_LEGS + DUCK_HEAD, sensors=["imu"], survives=DUCK_HEAD,
         params={"vx": [0.0, 0.25], "vtheta": [-0.3, 0.3], "seconds": [1, 4]},
         preconditions=["standing"], source=WALK_SRC + "; vtheta 0 and +-0.3 rad/s are the robot-tested turns",
         duration_s_max=4, tags=["locomotion", "explore"], effects={"posture": "standing"}),
    dict(name="stand", body="microduck", joints=DUCK_LEGS + DUCK_HEAD, sensors=["imu"], survives=DUCK_HEAD,
         params={"seconds": [1, 60]}, preconditions=["standing"], source="stand61.onnx at zero command (walk mode, vx 0)",
         duration_s_max=60, tags=["rest"], effects={"posture": "standing"}),
    dict(name="sit", body="microduck", joints=DUCK_LEGS + DUCK_HEAD, sensors=["imu"], survives=[],
         params={"seconds": [2, 30]},
         preconditions=["standing"], source="sit mode; policy goals clamped to the trained ranges (CURRENT-STATE policy_goal_guards)",
         duration_s_max=30, tags=["rest"], effects={"posture": "sitting"}),
    dict(name="groundpick", body="microduck", joints=DUCK_LEGS + DUCK_HEAD, sensors=["imu"], survives=[],
         params={"phase": [0.0, 1.0], "seconds": [2, 10]},
         preconditions=["standing", "the beak stays closed while bowing"],
         source="Pollen groundpick61; a beak-open bend is not trained (D-027)",
         duration_s_max=10, tags=["explore", "play"], effects={"posture": "standing"}),
    dict(name="getup", body="microduck", joints=DUCK_LEGS + DUCK_HEAD, sensors=["imu"], survives=[],
         params={}, preconditions=["lying"],
         source="walk_brain recover mode (DUCK_GETUP=recover); sim only, never run on the robot (CURRENT-STATE getup)",
         duration_s_max=8, duration_s_typical=4, tags=["rest"], effects={"posture": "standing"}),
    dict(name="wait", body="microduck", joints=DUCK_LEGS + DUCK_HEAD, sensors=["imu"], survives=DUCK_HEAD,
         params={"seconds": [1, 60]}, preconditions=["standing"], source="stand61 at zero command",
         duration_s_max=60, tags=["rest"], effects={"posture": "standing"}),
    dict(name="stop", body="microduck", joints=DUCK_LEGS + DUCK_HEAD, sensors=["imu"], survives=DUCK_HEAD,
         params={}, preconditions=[], source="zero velocity command; walk61 brings its stride to rest",
         duration_s_max=2, duration_s_typical=1, tags=["rest"], effects={"posture": "standing"}),
    dict(name="look_around", body="microduck", joints=["head_yaw"], sensors=[], survives=[],
         params={"seconds": [2, 8]}, preconditions=[], source="head yaw sweep within its trained range; rules-table bounds",
         duration_s_max=8, tags=["explore", "orient"]),
    dict(name="turn_head", body="microduck", joints=["head_yaw", "head_pitch"], sensors=[], survives=[],
         params={"yaw": "range:head_yaw", "pitch": "range:head_pitch", "seconds": [0.5, 5]},
         preconditions=[], source="joint ranges; while walking only head pitch is robot-tested (2026-10-24)",
         duration_s_max=5, tags=["orient", "social"]),
    dict(name="nod", body="microduck", joints=["head_pitch"], sensors=[], survives=[],
         params={"times": [1, 3]}, preconditions=[], source="rules-table bounds", duration_s_max=4, duration_s_typical=2,
         tags=["social", "express"]),
    dict(name="shake_head", body="microduck", joints=["head_yaw"], sensors=[], survives=[],
         params={"times": [1, 3]}, preconditions=[], source="rules-table bounds", duration_s_max=4, duration_s_typical=2,
         tags=["social", "express"]),
    dict(name="beak", body="microduck", joints=["jaw"], sensors=[], survives=[],
         params={"open": "range:jaw", "seconds": [0.3, 5]},
         preconditions=[], source="jaw limits in software (pi/jaw_limits.py): head pitch <= 65 deg while open",
         duration_s_max=5, tags=["express", "play"]),
    # OMX-F arm (fixed base, wrist camera); grasping through vs_grasp.py, which refuses on a stale CURRENT-STATE
    dict(name="turn_camera", body="omx_arm", joints=["base", "shoulder", "elbow", "wrist_pitch"], sensors=["camera"], survives=[],
         params={"yaw": "range:base", "pitch": [-0.6, 0.6], "seconds": [0.5, 4]},
         preconditions=[], source="shoulder kept above its CURRENT-STATE minimum (camera cable); rules-table pitch bounds",
         duration_s_max=4, tags=["orient", "social"]),
    dict(name="wave", body="omx_arm", joints=["shoulder", "elbow", "wrist_pitch"], sensors=[], survives=[],
         params={"times": [1, 3]},
         preconditions=[], source="from the low-load pose (XL430 shoulder overload, omx-local CURRENT-STATE camera_cable_and_stops); "
                                  "load guard load_guard_pct",
         duration_s_max=6, duration_s_typical=3, tags=["social", "express"]),
    dict(name="point", body="omx_arm", joints=["base", "shoulder", "elbow"], sensors=[], survives=[],
         params={"yaw": "range:base", "pitch": [-0.6, 0.6], "seconds": [0.5, 4]},
         preconditions=[], source="rules-table pitch bounds; no long hold of an extended forearm (XL430 overload)",
         duration_s_max=4, tags=["social", "express"]),
    dict(name="nod", body="omx_arm", joints=["wrist_pitch"], sensors=[], survives=[],
         params={"times": [1, 3]}, preconditions=[], source="rules-table bounds", duration_s_max=4, duration_s_typical=2,
         tags=["social", "express"]),
    dict(name="look_around", body="omx_arm", joints=["base", "shoulder", "elbow", "wrist_pitch"], sensors=["camera"],
         survives=[], params={"seconds": [2, 8]},
         preconditions=[], source="base sweep only; oblique survey views swing the camera cable across the lens (CURRENT-STATE)",
         duration_s_max=8, tags=["explore", "orient"]),
    dict(name="rest_pose", body="omx_arm", joints=["shoulder", "elbow", "wrist_pitch"], sensors=[], survives=[],
         params={"seconds": [1, 600]}, preconditions=[], source="the low-load pose (XL430 shoulder overload when extended)",
         duration_s_max=600, tags=["rest"]),
    dict(name="wait", body="omx_arm", joints=[], sensors=[], survives=[], params={"seconds": [1, 60]},
         preconditions=[], duration_s_max=60, tags=["rest"]),
    dict(name="stop", body="omx_arm", joints=[], sensors=[], survives=[], params={}, preconditions=[], source="hold the present pose",
         duration_s_max=1, duration_s_typical=1, tags=["rest"]),
    dict(name="grasp", body="omx_arm", joints=["base", "shoulder", "elbow", "wrist_pitch", "wrist_roll", "gripper"],
         sensors=["camera"], survives=[],
         params={"seconds": [5, 60]},
         preconditions=["object visible on the table"],
         source="vs_grasp.py (refuses unless the omx-local CURRENT-STATE check passes); gripper mode 5 at gripper_grip currents",
         duration_s_max=60, tags=["play", "explore"]),
]


def study_tolerance(path=STUDY):
    """{joint: True/False} survivable with the existing walking policy, from the failure study; {} without it."""
    if not os.path.exists(path):
        return {}
    res = json.load(open(path))
    out = {}
    for joint, modes in res.get("per_joint", {}).items():
        out[joint] = all(modes.get(m, {}).get("still_walks", False) for m in ("frozen", "weak"))
    return out


def _params(rule, ranges):
    out = {}
    for k, v in rule["params"].items():
        out[k] = list(ranges[v.split(":", 1)[1]]) if isinstance(v, str) else list(v)
    return out


def discover(body, actuators, sensors, tolerance=None):
    """(primitives, notes) for a body. `actuators`: card actuator dicts, `sensors`: card sensor dicts."""
    tolerance = study_tolerance() if tolerance is None else tolerance
    by_name = {a["name"]: a for a in actuators}
    ranges = {a["name"]: a["range_rad"] for a in actuators}
    kinds = {s["kind"] for s in sensors}
    prims, notes = [], []
    rules = [r for r in RULES if r["body"] == body]
    if not rules:
        for a in actuators:
            if a["ok"]:
                prims.append(dict(name=f"move_{a['name']}", params={"target": list(a["range_rad"]), "seconds": [0.5, 3]},
                                  preconditions=["unknown body: joint-level primitive only"], duration_s_max=3,
                                  tags=["explore"]))
        notes.append(f"unknown body: {len(prims)} joint-level primitives, no policy library entries")
        return prims, notes
    for r in rules:
        missing = [j for j in r["joints"] if j not in by_name]
        lacking = [k for k in r["sensors"] if k not in kinds]
        if missing or lacking:
            notes.append(f"{r['name']}: not available, missing " + ", ".join(missing + [f"sensor {k}" for k in lacking]))
            continue
        failed = [j for j in r["joints"] if not by_name[j]["ok"]]
        fatal = [j for j in failed if j not in r["survives"] or not tolerance.get(j, False)]
        if fatal:
            why = ", ".join(f"{j}{'' if j in r['survives'] else ' (needed)'}" +
                            ("" if j not in r["survives"] else " (failure study: not survivable or not run)") for j in fatal)
            notes.append(f"{r['name']}: dropped, failed joint {why}")
            continue
        p = dict(name=r["name"], params=_params(r, ranges), preconditions=list(r["preconditions"]),
                 duration_s_max=r["duration_s_max"], tags=list(r["tags"]))
        for k in ("duration_s_typical", "effects"):
            if k in r:
                p[k] = r[k]
        if r.get("source"):
            notes.append(f"{r['name']}: {r['source']}")
        for j in failed:
            p["preconditions"].append(f"{j} failed; the sim failure study shows {r['name']} survives it frozen and weak")
            notes.append(f"{r['name']}: kept with {j} failed (failure_study/results.json)")
        prims.append(p)
    return prims, notes
