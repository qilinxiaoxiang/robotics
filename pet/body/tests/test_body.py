"""Body layer tests: card schema, babbling inference on recorded traces, primitive discovery, health transitions.

  ~/.venvs/microduck-dyn/bin/python -m pytest pet/body/tests -q        (from the repository root)
"""
import copy
import json
import os

import pytest

from pet.body import babble, card, dxl_models, health, inspect as body_inspect, primitives, profiles

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(os.path.dirname(HERE), "fixtures")
EXAMPLES = os.path.join(card.STATE_DIR, "examples")


def dry_card(tmp_path, body):
    out = tmp_path / f"{body}.json"
    body_inspect.main(["--dry-run", "--body", body, "--out", str(out)])
    return json.load(open(out))


# --- card schema -------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("body", ["duck", "arm"])
def test_dry_run_cards_validate(tmp_path, body):
    c = dry_card(tmp_path, body)
    assert card.validate(c) == []


@pytest.mark.parametrize("name", ["duck.json", "omx_arm.json"])
def test_checked_in_examples_validate(name):
    assert card.validate(json.load(open(os.path.join(EXAMPLES, name)))) == []


def test_validate_catches_bad_cards(tmp_path):
    good = dry_card(tmp_path, "duck")
    for mutate, expect in [
        (lambda c: c["sensors"].append({"kind": "lidar", "id": "x", "notes": ""}), "sensors"),
        (lambda c: c["actuators"][0].update(range_rad=[1.0, -1.0]), "range_rad"),
        (lambda c: c["actuators"][1].update(id=c["actuators"][0]["id"]), "repeated"),
        (lambda c: c["actuators"][0].update(ok="yes"), "ok"),
        (lambda c: c["primitives"][0]["params"].update(vx=[0.0]), "params"),
        (lambda c: c["primitives"][0].update(duration_s_max=0), "duration_s_max"),
        (lambda c: c.pop("notes"), "notes"),
    ]:
        c = copy.deepcopy(good)
        mutate(c)
        errs = card.validate(c)
        assert errs and any(expect in e for e in errs), (expect, errs)
    with pytest.raises(ValueError):
        bad = copy.deepcopy(good)
        bad["actuators"][0]["ok"] = None
        card.write(bad, str(tmp_path / "bad.json"))
    assert not (tmp_path / "bad.json").exists()


def test_stall_torque_table():
    assert dxl_models.stall_torque(1200, 5.0) == 0.52
    assert dxl_models.stall_torque(1200, 5.5) == pytest.approx(0.56)
    assert dxl_models.stall_torque(1200, 7.2) == 0.60  # clamped at the highest published point, not extrapolated
    assert dxl_models.above_published(1200, 7.2)
    assert dxl_models.stall_torque(1060, 11.6) == pytest.approx(1.4 + 0.1 * 0.5 / 0.9, abs=1e-3)
    assert dxl_models.stall_torque(9999, 5.0) is None
    assert dxl_models.hw_error_names(0x24) == ["overheating", "overload"]


# --- body recognition --------------------------------------------------------------------------------------------

def test_identify_bodies():
    duck = json.load(open(os.path.join(FIX, "duck_bus_scan.json")))
    arm = json.load(open(os.path.join(FIX, "omx_bus_scan.json")))
    assert profiles.identify(duck) == "microduck"
    assert profiles.identify(arm) == "omx_arm"
    dead_neck = dict(duck, motors=[m for m in duck["motors"] if m["id"] != 12])
    assert profiles.identify(dead_neck) == "microduck"
    stranger = dict(motors=[dict(id=1, model=1020), dict(id=2, model=1020)])
    assert profiles.identify(stranger) is None


def test_ranges_come_from_their_owners():
    r = profiles.duck_ranges()
    assert r["neck_pitch"] == [-1.5708, 1.0472]  # walk_brain.JOINT_RANGE, CURRENT-STATE policy_goal_guards
    assert r["jaw"][1] == pytest.approx(0.4363, abs=1e-4)  # jaw_limits.json 25 deg
    a = profiles.omx_ranges()
    facts = profiles.state_facts(profiles.OMX_STATE)
    assert a["shoulder"][0] == pytest.approx(facts["shoulder_min_deg"]["value"]["calibrated"] * 3.14159265 / 180, abs=1e-3)


# --- babbling inference ------------------------------------------------------------------------------------------

def recorded():
    return {t["joint"]: t for t in json.load(open(os.path.join(FIX, "duck_babble_recorded.json")))["traces"]}


def test_recorded_neck_tilts_body_head_pitch_does_not():
    tr = recorded()
    neck = babble.analyse(tr["neck_pitch"])
    assert "tilts the body" in neck["effects"] and neck["tilt_deg"] >= babble.TILT_DEG
    head = babble.analyse(tr["head_pitch"])
    assert head["effects"] == ["does nothing visible"]


def test_policy_window_never_judged_unresponsive():
    hip = babble.analyse(recorded()["left_hip_roll"])  # policy asked 0.24 rad, the loaded joint moved 0.07
    assert hip["responds"] is None and "did not move" not in hip["effects"]


def synth(joint, q_amp, tilt_axis=None, cmd=0.04, img=None):
    import math
    n = 50
    q = [q_amp * math.sin(math.pi * k / (n - 1)) for k in range(n)]
    gb = []
    for k in range(n):
        a = math.radians(5.0) * q[k] / max(q_amp, 1e-9) if tilt_axis else 0.0
        gb.append([math.sin(a), 0.0, -math.cos(a)])
    return dict(joint=joint, commanded_rad=cmd, babble=True, t=[k * 0.02 for k in range(n)], q=q, gb=gb,
                gyro=[[0, 0, 0]] * n, img_change=img)


def test_babble_classification_on_synthetic_traces():
    assert babble.analyse(synth("j", 0.04, tilt_axis="x"))["effects"] == ["tilts the body"]
    assert babble.analyse(synth("j", 0.04, img=[0.0, 0.3]))["effects"] == ["moves the camera"]
    assert babble.analyse(synth("j", 0.04))["effects"] == ["does nothing visible"]
    stuck = babble.analyse(synth("j", 0.005))
    assert stuck["responds"] is False and stuck["effects"] == ["did not move"]


def test_unresponsive_joint_marked_failed_on_the_card():
    scan = json.load(open(os.path.join(FIX, "duck_bus_scan.json")))
    eff = [babble.analyse(synth("left_knee", 0.002))]
    acts, notes = body_inspect.actuators_from_scan("microduck", scan, eff, 7.0)
    knee = next(a for a in acts if a["name"] == "left_knee")
    assert knee["ok"] is False and any("left_knee" in n and "babbling" in n for n in notes)


# --- primitive discovery -----------------------------------------------------------------------------------------

def duck_parts():
    scan = json.load(open(os.path.join(FIX, "duck_bus_scan.json")))
    acts, _ = body_inspect.actuators_from_scan("microduck", scan, [], 7.0)
    from pet.body import devices
    sensors, _ = devices.from_state("microduck")
    return acts, sensors


def names(prims):
    return [p["name"] for p in prims]


def test_duck_primitives():
    acts, sensors = duck_parts()
    prims, _ = primitives.discover("microduck", acts, sensors, tolerance={})
    assert names(prims) == ["walk", "stand", "sit", "groundpick", "getup", "wait", "stop", "look_around", "turn_head", "nod",
                            "shake_head", "beak"]
    walk = prims[0]
    assert walk["params"]["vx"] == [0.0, 0.25] and walk["duration_s_max"] == 4
    assert next(p for p in prims if p["name"] == "turn_head")["params"]["yaw"] == [-2.9671, 2.9671]


def test_duck_leg_failure_drops_locomotion_keeps_head():
    acts, sensors = duck_parts()
    next(a for a in acts if a["name"] == "left_hip_roll")["ok"] = False
    prims, notes = primitives.discover("microduck", acts, sensors, tolerance={"left_hip_roll": True})
    assert names(prims) == ["look_around", "turn_head", "nod", "shake_head", "beak"]
    assert any(n.startswith("walk: dropped") for n in notes)


def test_duck_head_failure_follows_the_failure_study():
    acts, sensors = duck_parts()
    next(a for a in acts if a["name"] == "head_roll")["ok"] = False
    kept, _ = primitives.discover("microduck", acts, sensors, tolerance={"head_roll": True})
    walk = next(p for p in kept if p["name"] == "walk")
    assert any("head_roll failed" in c for c in walk["preconditions"])
    assert "sit" not in names(kept)  # sit and groundpick bend the head down: not covered by the walking study
    dropped, _ = primitives.discover("microduck", acts, sensors, tolerance={"head_roll": False})
    assert "walk" not in names(dropped) and "turn_head" in names(dropped)


def test_study_tolerance_reads_still_walks(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"per_joint": {"head_yaw": {"frozen": {"still_walks": True}, "weak": {"still_walks": True}},
                                           "neck_pitch": {"frozen": {"still_walks": True}, "weak": {"still_walks": False}}}}))
    assert primitives.study_tolerance(str(p)) == {"head_yaw": True, "neck_pitch": False}
    assert primitives.study_tolerance(str(tmp_path / "none.json")) == {}


def test_arm_primitives(tmp_path):
    c = dry_card(tmp_path, "arm")
    assert names(c["primitives"]) == ["turn_camera", "wave", "point", "nod", "look_around", "rest_pose", "wait", "stop", "grasp"]
    assert "walk" not in names(c["primitives"])
    no_cam, _ = primitives.discover("omx_arm", c["actuators"], [], tolerance={})
    assert names(no_cam) == ["wave", "point", "nod", "rest_pose", "wait", "stop"]
    shoulder = next(a for a in c["actuators"] if a["name"] == "shoulder")
    volts = next(m["voltage_v"] for m in json.load(open(os.path.join(FIX, "omx_bus_scan.json")))["motors"] if m["id"] == 12)
    assert shoulder["model"] == "XL430-W250"
    assert shoulder["torque_nm"] == pytest.approx(1.4 + 0.1 * (volts - 11.1) / 0.9, abs=1e-3)  # e-manual 11.1 / 12.0 V points


def test_mind_example_skills_validate_on_these_cards():
    """The greeting skills in pet/state/examples/skills.json (written by pet/mind) name primitives and params these
    cards offer; the mind hides a skill whose steps do not validate. door_check needs `wander`, a navigation behaviour
    no body has yet, so it stays hidden on both."""
    path = os.path.join(EXAMPLES, "skills.json")
    if not os.path.exists(path):
        pytest.skip("pet/mind's example skills.json is not present")
    skills = {s["name"]: s for s in json.load(open(path))}

    def fits(skill, card_name):
        prims = {p["name"]: p for p in json.load(open(os.path.join(EXAMPLES, card_name)))["primitives"]}
        return all(s["primitive"] in prims and set(s.get("params", {})) <= set(prims[s["primitive"]]["params"])
                   for s in skill["steps"])
    assert fits(skills["greet_owner"], "duck.json")
    assert fits(skills["greet_owner_wave"], "omx_arm.json")


def test_unknown_body_gets_joint_level_primitives():
    scan = dict(motors=[dict(id=1, model=1020, min_position_limit=1024, max_position_limit=3072),
                        dict(id=2, model=1020)])
    acts, _ = body_inspect.actuators_from_scan(None, scan)
    assert acts[0]["range_rad"] == [-1.5708, 1.5708] and acts[1]["range_rad"][1] == pytest.approx(3.1416, abs=1e-4)
    prims, notes = primitives.discover("unknown", acts, [])
    assert names(prims) == ["move_joint_1", "move_joint_2"] and "unknown body" in notes[0]


# --- health ------------------------------------------------------------------------------------------------------

def fresh(tmp_path):
    c = dry_card(tmp_path, "duck")
    return c, health.Health(c, miss_limit=3, recover_after=3, card_path=str(tmp_path / "card.json"),
                            events_path=str(tmp_path / "events.jsonl"), tolerance={n: True for n in profiles.DUCK_HEAD})


def all_ok(c, **override):
    p = {a["id"]: dict(replied=True, hw_error=0) for a in c["actuators"]}
    for i, r in override.items():
        p[int(i[1:])] = r
    return p


def test_health_single_miss_is_not_a_fault(tmp_path):
    c, h = fresh(tmp_path)
    h.update(all_ok(c, i12=dict(replied=False, hw_error=0)))
    h.update(all_ok(c))
    h.update(all_ok(c, i12=dict(replied=False, hw_error=0)))
    assert all(a["ok"] for a in c["actuators"]) and h.events == []


def test_health_no_reply_fault_and_recovery(tmp_path):
    c, h = fresh(tmp_path)
    for _ in range(3):
        h.update(all_ok(c, i2=dict(replied=False, hw_error=0)))  # right knee silent
    knee = h.by_id[2]
    assert knee["ok"] is False
    ev = h.events[-1]
    assert ev["kind"] == "body_fault" and ev["actuator"] == "right_knee" and "walk" in ev["lost"]
    saved = json.load(open(tmp_path / "card.json"))
    assert card.validate(saved) == [] and "walk" not in names(saved["primitives"])
    for _ in range(3):
        h.update(all_ok(c))
    assert knee["ok"] is True and h.events[-1]["kind"] == "body_recovered" and "walk" in h.events[-1]["gained"]
    lines = open(tmp_path / "events.jsonl").read().splitlines()
    assert [json.loads(x)["kind"] for x in lines] == ["body_fault", "body_recovered"]


def test_health_hardware_error_latches(tmp_path):
    c, h = fresh(tmp_path)
    h.update(all_ok(c, i12=dict(replied=True, hw_error=0x20)))  # neck overload
    assert h.by_id[12]["ok"] is False and "overload" in h.events[-1]["reason"]
    assert "walk" in names(c["primitives"])  # head joint, tolerance given: walking stays
    h.update(all_ok(c, i12=dict(replied=False, hw_error=0)))
    h.update(all_ok(c, i12=dict(replied=True, hw_error=0x20)))
    assert h.by_id[12]["ok"] is False and len(h.events) == 1
    for _ in range(3):
        h.update(all_ok(c))
    assert h.by_id[12]["ok"] is True


def test_health_replays_the_recorded_left_ankle_fault(tmp_path):
    c, h = fresh(tmp_path)
    h.miss_limit = h.recover_after = 25
    path = os.path.join(FIX, "duck_health_replay.jsonl")
    ids = {a["name"]: a["id"] for a in c["actuators"]}
    for t, poll in health.log_polls(path, ids):
        h.update(poll, t)
    faults = [e for e in h.events if e["kind"] == "body_fault"]
    assert [e["actuator"] for e in faults] == ["left_ankle"]  # the transient ID13 miss in the same log is ignored
    assert faults[0]["t"].startswith("2026-10-19") and "walk" in faults[0]["lost"]


def test_health_cli_replay(tmp_path):
    c = dry_card(tmp_path, "duck")
    src = tmp_path / "start.json"
    card.write(c, str(src))
    health.main(["--log", os.path.join(FIX, "duck_health_replay.jsonl"), "--card", str(src), "--out", str(tmp_path / "o.json"),
                 "--events", str(tmp_path / "e.jsonl")])
    kinds = [json.loads(x)["kind"] for x in open(tmp_path / "e.jsonl")]
    assert kinds[0] == "body_fault"


# --- sim babbling (needs ~/.venvs/microduck-dyn) -----------------------------------------------------------------

def test_sim_babbling_card(tmp_path):
    pytest.importorskip("mujoco")
    pytest.importorskip("bam")
    out = tmp_path / "sim.json"
    body_inspect.main(["--sim", "--out", str(out), "--traces-out", str(tmp_path / "tr.json")])
    c = json.load(open(out))
    assert card.validate(c) == []
    eff = {e["joint"]: e for e in json.load(open(tmp_path / "tr.json"))["effects"]}
    assert len(eff) == 14
    assert "moves the camera" in eff["head_pitch"]["effects"] and "tilts the body" not in eff["head_pitch"]["effects"]
    assert "tilts the body" in eff["left_hip_pitch"]["effects"]
    assert all(e["responds"] for e in eff.values())
