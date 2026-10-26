"""Write the three example cards with a `channels` block: copies of pet/state/examples/duck.json and omx_arm.json
(owned by pet/body; read here, never edited) plus a hypothetical vacuum robot, the third body.

  python3 -m pet.express.cards.make_cards
"""
import copy
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
EXAMPLES = os.path.join(HERE, "..", "..", "state", "examples")

# walk_brain.py HEAD_RANGE (neck_pitch, head_pitch, head_yaw, head_roll): the head-command range stand61/walk61 were
# trained on, as deltas from the policy default pose. tests/test_channels.py checks these against walk_brain.py.
DUCK_HEAD_RANGE = {"neck_pitch": 1.10, "head_pitch": 1.10, "head_yaw": 1.40, "head_roll": 0.31}

DUCK_CHANNELS = {
    "space": "delta",
    "space_note": "head outputs are walk_brain head-command deltas from the policy default pose (HEAD_JOINTS order "
                  "neck_pitch, head_pitch, head_yaw, head_roll); the stand/walk policy tracks them",
    "orient_threshold": 1.2,
    "head_lead_s": 0.22,
    "motion_lag_s": 0.14,
    "motion_lag_note": "head_yaw joint 0.12-0.16 s behind the head command under stand61 (as-built sim, "
                       "pet/express/out/duck_tilt.json track_lag_s); calls are delayed by it to land with the head",
    "ATTEND": {"map": [
        {"axis": "yaw", "to": "head_yaw", "gain": 1.0},
        {"axis": "pitch", "to": "head_pitch", "gain": 0.75},
        {"axis": "pitch", "to": "neck_pitch", "gain": -0.25},
    ], "note": "sim signs (as-built MuJoCo head camera): head_yaw + turns left, head_pitch + looks up, neck_pitch + "
               "lowers the head"},
    "ORIENT": {"map": [
        {"axis": "yaw", "to": "head_yaw", "gain": -1.0},
        {"axis": "yaw", "to": "body_heading", "gain": 1.0},
    ], "note": "the head counter-rotates while the body turns; body_heading is a heading goal for walk_brain's "
               "heading controller (walk61, robot-tested turns +-0.3 rad/s); not exercised under the stand policy"},
    "POSTURE": {"map": [
        {"axis": "height", "to": "neck_pitch", "gain": -0.22},
        {"axis": "height", "to": "head_pitch", "gain": -0.18},
    ], "note": "alert = neck back and head up, gaze kept near level; slumped = neck forward"},
    "GESTURE": {"map": [
        {"axis": "tilt", "to": "head_roll", "gain": 1.0},
        {"axis": "bob", "to": "head_pitch", "gain": -1.0},
    ]},
    "VOCALISE": {"render": "call", "device": "speaker",
                 "note": "duck_sound.Voice recordings, resampled for pitch and stretched for length (pet/express/voice.py)"},
    "outputs": {
        "neck_pitch": {"limit": [-0.45, 0.45], "max_rate": 4.0,
                       "note": "inside HEAD_RANGE 1.10; neck moves tilt the trunk (pet/state/examples/duck.json body schema 15 deg/rad)"},
        "head_pitch": {"limit": [-0.6, 0.6], "max_rate": 6.0},
        "head_yaw": {"limit": [-DUCK_HEAD_RANGE["head_yaw"], DUCK_HEAD_RANGE["head_yaw"]], "max_rate": 7.0},
        "head_roll": {"limit": [-DUCK_HEAD_RANGE["head_roll"], DUCK_HEAD_RANGE["head_roll"]], "max_rate": 4.0},
        "body_heading": {"limit": [-math.pi, math.pi], "max_rate": 0.3},
    },
}

ARM_CHANNELS = {
    "space": "delta",
    "space_note": "deltas from the LOOK pose (omx-local servo_grasp.LOOK_POSE); the executor adds them and keeps its "
                  "own load guard and cable stops (omx-local/CURRENT-STATE.json)",
    "orient_threshold": 0.0,
    "head_lead_s": 0.25,
    "motion_lag_s": 0.0,
    "motion_lag_note": "not measured on the arm (no robot run); the executor's own lag adds to the call timing",
    "ATTEND": {"map": [
        {"axis": "yaw", "to": "base", "gain": 0.35},
        {"axis": "pitch", "to": "wrist_pitch", "gain": 1.0},
    ], "note": "no neck: a fast 35 % glance on the base, the rest comes with ORIENT; wrist camera pitch is the gaze "
               "pitch (sign not verified on the arm)"},
    "ORIENT": {"map": [{"axis": "yaw", "to": "base", "gain": 0.65}]},
    "POSTURE": {"map": [{"axis": "height", "to": "shoulder", "gain": -0.12}],
                "note": "small shoulder lift only: an extended forearm held for minutes trips the shoulder XL430 "
                        "(omx-local/CURRENT-STATE.json camera_cable_and_stops)"},
    "GESTURE": {"map": [
        {"axis": "tilt", "to": "wrist_roll", "gain": 1.2},
        {"axis": "bob", "to": "wrist_pitch", "gain": -0.8},
    ]},
    "VOCALISE": {"render": "clack", "to": "gripper", "amplitude": 0.35, "ms": 110, "clacks": 1,
                 "note": "no speaker: a quick gripper close-open per call, a second clack for a high (happy) call"},
    "outputs": {
        "base": {"limit": [-1.4, 1.4], "max_rate": 2.5},
        "shoulder": {"limit": [-0.12, 0.12], "max_rate": 1.0},
        "wrist_pitch": {"limit": [-0.45, 0.0], "max_rate": 3.0,
                        "note": "LOOK wrist pitch 105.0 deg is 1.35 deg under the cap (CURRENT-STATE wrist_pitch_max_deg): "
                                "moves only away from the stop"},
        "wrist_roll": {"limit": [-0.5, 0.5], "max_rate": 3.0, "note": "camera cable: +-90 deg cap, this is +-29"},
        "gripper": {"limit": [-0.1, 0.5], "max_rate": 8.0},
    },
}

VACUUM_CARD = {
    "name": "vacuum_bot",
    "hypothetical": True,
    "sensors": [{"kind": "range", "id": "bumper_ir", "notes": "front bumper and cliff IR"},
                {"kind": "mic", "id": "mic", "notes": "assumed, to hear its name"}],
    "actuators": [
        {"id": 1, "name": "heading", "model": "differential drive heading loop", "torque_nm": 0.0,
         "range_rad": [-math.pi, math.pi], "ok": True},
        {"id": 2, "name": "drive", "model": "differential drive speed loop, m/s", "torque_nm": 0.0,
         "range_rad": [-0.3, 0.3], "ok": True},
    ],
    "devices": [{"name": "beeper", "kind": "buzzer"}, {"name": "ring_led", "kind": "light", "notes": "brightness 0-1"}],
    "primitives": [
        {"name": "turn_to", "params": {"yaw": [-math.pi, math.pi]}, "preconditions": [], "duration_s_max": 4,
         "tags": ["orient", "social"]},
        {"name": "drive", "params": {"vx": [-0.3, 0.3], "seconds": [1, 10]}, "preconditions": [],
         "duration_s_max": 10, "tags": ["locomotion"]},
        {"name": "beep", "params": {"hz": [400, 4000]}, "preconditions": [], "duration_s_max": 1,
         "tags": ["express"]},
    ],
    "notes": ["no such robot in hand: a third body that proves the channel abstraction (register section 12, "
              "'a vacuum robot's head is its heading')"],
    "channels": {
        "space": "delta",
        "space_note": "heading delta from the heading at the call; drive is a speed in m/s",
        "orient_threshold": 0.0,
        "head_lead_s": 0.2,
        "ATTEND": {"map": [{"axis": "yaw", "to": "heading", "gain": 0.35}],
                   "note": "gaze = heading; no pitch (ATTEND.pitch absent)"},
        "ORIENT": {"map": [{"axis": "yaw", "to": "heading", "gain": 0.65}]},
        "POSTURE": {"map": [{"axis": "height", "to": "drive", "gain": 0.12}],
                    "note": "the anticipation dip becomes a short back-up, alertness a forward creep"},
        "GESTURE": {"map": [
            {"axis": "tilt", "to": "heading", "gain": 0.5},
            {"axis": "bob", "to": "drive", "gain": 0.6},
        ], "note": "tilt = a small heading wiggle, bob = a forward-back jiggle"},
        "VOCALISE": {"render": "beep", "device": "beeper", "base_hz": 1400, "ms": 120, "light": "ring_led"},
        "outputs": {
            "heading": {"limit": [-math.pi, math.pi], "max_rate": 3.0},
            "drive": {"limit": [-0.15, 0.15], "max_rate": 1.5},
            "ring_led": {"limit": [0.0, 1.0]},
        },
    },
}


def with_channels(src, channels, devices=()):
    card = copy.deepcopy(json.load(open(os.path.join(EXAMPLES, src))))
    if devices:
        card["devices"] = list(devices)
    card["channels"] = channels
    card.setdefault("notes", []).append(f"channels block added by pet/express/cards/make_cards.py to a copy of "
                                        f"pet/state/examples/{src}")
    return card


def build():
    return {
        "duck.json": with_channels("duck.json", DUCK_CHANNELS, [
            {"name": "speaker", "kind": "speaker", "notes": "head speaker, ALSA default, -3 dB softvol ceiling"},
            {"name": "body_heading", "kind": "heading_goal", "notes": "walk_brain heading controller goal"}]),
        "omx_arm.json": with_channels("omx_arm.json", ARM_CHANNELS),
        "vacuum.json": VACUUM_CARD,
    }


def main():
    for name, card in build().items():
        with open(os.path.join(HERE, name), "w") as f:
            json.dump(card, f, indent=1)
            f.write("\n")
        print("wrote", os.path.join(HERE, name))


if __name__ == "__main__":
    main()
