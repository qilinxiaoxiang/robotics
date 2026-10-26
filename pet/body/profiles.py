"""Known bodies: how a bus scan is recognised, joint names per servo id, joint ranges, which joints the body can
lose and still move. Ranges and limits are read at inspection time from the files that own them, never copied here:

- MicroDuck: joint ranges = walk_brain.JOINT_RANGE (the policy goal clamp, CURRENT-STATE fact policy_goal_guards),
  jaw opening cap = guide/firmware/pi/jaw_limits.json, rail voltage = microduck-sim/CURRENT-STATE.json servo_rail_v.
- OMX-F arm: limits = omx-local/CURRENT-STATE.json (shoulder_min_deg, wrist_pitch_max_deg, wrist_roll_max_deg),
  joint names = omx-local/grasp_step.py NAMES.

An unknown bus gets joint_<id> names and the servo's own EEPROM position limits.
"""
import ast
import json
import math
import os

from . import dxl_models

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DUCK = os.path.join(REPO, "microduck-sim")
DUCK_STATE = os.path.join(DUCK, "CURRENT-STATE.json")
WALK_BRAIN = os.path.join(DUCK, "guide", "firmware", "mac", "walk_brain.py")
JAW_LIMITS = os.path.join(DUCK, "guide", "firmware", "pi", "jaw_limits.json")
OMX = os.path.join(REPO, "omx-local")
OMX_STATE = os.path.join(OMX, "CURRENT-STATE.json")
OMX_NAMES_SRC = os.path.join(OMX, "grasp_step.py")

# servo id -> joint name, as guide/firmware/pi/scan_bus.py ROLES and walk_brain.NAMES (ids 1-14), 15 = jaw
DUCK_IDS = {1: "right_ankle", 2: "right_knee", 3: "right_hip_pitch", 4: "right_hip_roll", 5: "right_hip_yaw",
            6: "left_ankle", 7: "left_knee", 8: "left_hip_pitch", 9: "left_hip_roll", 10: "left_hip_yaw",
            11: "head_pitch", 12: "neck_pitch", 13: "head_yaw", 14: "head_roll", 15: "jaw"}
DUCK_LEGS = [n for i, n in DUCK_IDS.items() if i <= 10]
DUCK_HEAD = ["neck_pitch", "head_pitch", "head_yaw", "head_roll"]


def state_facts(path):
    with open(path) as f:
        return json.load(f)["facts"]


def _literal_assign(path, name):
    """Value of a module-level `NAME = <literal>` in a source file, without importing it."""
    tree = ast.parse(open(path).read(), path)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(f"{name} not found in {path}")


def duck_ranges():
    rng = {k: [float(a), float(b)] for k, (a, b) in _literal_assign(WALK_BRAIN, "JOINT_RANGE").items()}
    jaw = json.load(open(JAW_LIMITS))
    rng["jaw"] = [0.0, round(math.radians(jaw["jaw_max_open_deg"]), 4)]  # opening from the calibrated closed jaw
    return rng


def omx_names():
    return list(_literal_assign(OMX_NAMES_SRC, "NAMES"))


def omx_ranges():
    f = state_facts(OMX_STATE)
    full = [-math.pi, math.pi]
    rng = {n: list(full) for n in omx_names()}
    rng["shoulder"][0] = round(math.radians(f["shoulder_min_deg"]["value"]["calibrated"]), 4)
    rng["wrist_pitch"][1] = round(math.radians(f["wrist_pitch_max_deg"]["value"]["calibrated"]), 4)
    roll = math.radians(f["wrist_roll_max_deg"]["value"])
    rng["wrist_roll"] = [round(-roll, 4), round(roll, 4)]
    return rng


PROFILES = {
    "microduck": dict(
        ids=DUCK_IDS, models={i: 1200 for i in DUCK_IDS},
        ranges=duck_ranges, range_source="walk_brain.JOINT_RANGE (policy goal clamp) and pi/jaw_limits.json jaw_max_open_deg",
        state=DUCK_STATE, critical=DUCK_LEGS, fixed_location=None,
        # joints whose loss the walking primitives may survive; the failure study decides (failure_study/results.json)
        tolerable=DUCK_HEAD + ["jaw"],
    ),
    "omx_arm": dict(
        ids=None, models={11: 1060, 12: 1060, 13: 1060, 14: 1200, 15: 1200, 16: 1200},
        ranges=omx_ranges, range_source="omx-local/CURRENT-STATE.json shoulder_min_deg, wrist_pitch_max_deg, wrist_roll_max_deg; "
                                       "other joints one full turn (EEPROM limits are not in the recorded scan)",
        state=OMX_STATE, critical=[], fixed_location=None, tolerable=[],
    ),
}
ALIASES = {"duck": "microduck", "arm": "omx_arm", "omx": "omx_arm"}


def joint_names(profile_name):
    p = PROFILES[profile_name]
    if p["ids"] is not None:
        return dict(p["ids"])
    return {11 + k: n for k, n in enumerate(omx_names())}


def identify(scan):
    """Profile name whose id set and model numbers match the scan exactly, else None (unknown body).
    Missing servos do not change the identity when at least 2/3 of the profile answers with the right models:
    a duck with a dead neck servo is still the duck."""
    found = {m["id"]: m["model"] for m in scan["motors"]}
    best = None
    for name, p in PROFILES.items():
        want = p["models"]
        if any(i not in want or want[i] != mdl for i, mdl in found.items()):
            continue
        share = len(found) / len(want)
        if share >= 2 / 3 and (best is None or share > best[1]):
            best = (name, share)
    return best[0] if best else None


def resolve(name):
    return ALIASES.get(name, name)


def unknown_range(motor):
    """EEPROM limits when the scan read them (mode 3 position control), else one full turn."""
    lo, hi = motor.get("min_position_limit"), motor.get("max_position_limit")
    if lo is None or hi is None or hi <= lo:
        return [-math.pi, math.pi]
    return [round(dxl_models.tick_to_rad(lo), 4), round(dxl_models.tick_to_rad(hi), 4)]
