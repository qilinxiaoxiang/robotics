"""pet/mind tests. No test calls a model: the LLM path uses ScriptedBackend."""
import json
import random

import pytest

from pet.mind.backends import BackendError, CallLog, ScriptedBackend, parse_json_answer
from pet.mind.body import BodyCard, check_condition
from pet.mind.drives import Drives
from pet.mind.executors import duck_commands
from pet.mind.metrics import rigidity
from pet.mind.mind import Mind
from pet.mind.state import EXAMPLES, SharedState, load_body_card
from pet.mind.validator import usable_skills, validate
from pet.mind.world import World

T0 = 8 * 3600


@pytest.fixture
def duck():
    return BodyCard(load_body_card("duck"))


@pytest.fixture
def arm():
    return BodyCard(load_body_card("arm"))


def facts(**kw):
    base = {"posture": "standing", "owner_visible": True, "owner_home": True, "stranger_present": False,
            "touched": False, "battery": 0.9, "hour": 8.0, "tired": 0.1, "bored": 0.2, "miss_owner": 0.1,
            "curious": 0.2}
    return {**base, **kw}


def answer(*steps, duration=10, abort_if=()):
    return json.dumps({"intention_text": "test", "steps": [{"primitive": p, "params": prm} for p, prm in steps],
                       "duration_s": duration, "abort_if": list(abort_if), "mood_note": "ok"})


def make_mind(body, answers=None, state_dir=EXAMPLES, seed=0):
    rng = random.Random(seed)
    w = World(body, rng, T0)
    w.owner_room = w.pet_room
    w._was_visible = w.owner_visible
    backend = ScriptedBackend(answers) if answers is not None else None
    return Mind(body, SharedState(state_dir), w, backend=backend, rng=rng, call_log=CallLog()), w


# ---------- drives ----------

def test_drives_rise_when_alone_and_fall_with_owner():
    d = Drives()
    for _ in range(1800):
        d.update(1, set(), owner_visible=False, owner_home=False, hour=13)
    assert d.v["miss_owner"] > 0.5 and d.v["bored"] > 0.9
    lonely_valence = d.valence
    for _ in range(300):
        d.update(1, {"social"}, owner_visible=True, owner_home=True, hour=13)
    assert d.v["miss_owner"] < 0.1 and d.v["bored"] < 0.5 and d.valence > lonely_valence


def test_drives_tired_and_battery():
    d = Drives({"drive_rates": {"tired_active": 0.002}})
    for _ in range(600):
        d.update(1, {"locomotion"}, owner_visible=True, owner_home=True, hour=10)
    walked = d.v["tired"]
    assert walked > 0.9 and d.battery_level < 1.0
    for _ in range(300):
        d.update(1, {"rest"}, owner_visible=True, owner_home=True, hour=10)
    assert d.v["tired"] < walked
    d.battery_level = 0.1
    d.update(1, set(), owner_visible=True, owner_home=True, hour=10)
    assert d.v["battery"] > 0.7


def test_sleep_barely_drains_the_battery():
    d = Drives()
    for _ in range(5 * 60):
        d.update(60, {"sleep"}, owner_visible=False, owner_home=False, hour=11)
    assert d.battery_level > 0.75 and d.v["battery"] == 0


def test_events_move_mood():
    d = Drives()
    v0, a0 = d.valence, d.arousal
    d.apply_event({"kind": "touch"})
    assert d.valence > v0
    d.apply_event({"kind": "face", "who": "stranger"})
    assert d.arousal > a0 and d.v["curious"] > 0.4
    d.v["miss_owner"] = 0
    d.apply_event({"kind": "expect", "outcome": "owner_leaves", "weight": 0.8})
    assert d.v["miss_owner"] == pytest.approx(0.24)


# ---------- condition grammar ----------

def test_condition_grammar():
    f = facts(posture="sitting", standing=False, sitting=True)
    assert check_condition("sitting", f) is True
    assert check_condition("not standing", f) is True
    assert check_condition("battery > 0.5", f) is True
    assert check_condition("battery < 0.5", f) is False
    assert check_condition("the floor is dry", f) is None


# ---------- validator ----------

def test_validator_accepts_and_fills_defaults(duck):
    obj = json.loads(answer(("walk", {"vx": 0.2, "seconds": 4}), ("turn_head", {"yaw": 0.5})))
    intent, errs, _ = validate(obj, duck, {}, facts())
    assert not errs
    assert intent["steps"][0]["params"] == {"vx": 0.2, "vtheta": 0.0, "seconds": 4}
    assert intent["steps"][1]["params"]["pitch"] == 0.0


def test_validator_rejects_unknown_primitive(duck):
    _, errs, _ = validate(json.loads(answer(("fly", {}))), duck, {}, facts())
    assert errs and "unknown primitive 'fly'" in errs[0]


def test_validator_rejects_raw_joint_command(duck):
    raw = {"steps": [{"primitive": "set_joint", "params": {"head_yaw": 2.0}}]}
    assert validate(raw, duck, {}, facts())[0] is None
    sneaky = {"steps": [{"primitive": "turn_head", "params": {"yaw": 0.1}, "joints": {"left_knee": 1.5}}]}
    intent, errs, _ = validate(sneaky, duck, {}, facts())
    assert intent is None and "unexpected keys" in errs[0]
    extra_param = {"steps": [{"primitive": "turn_head", "params": {"yaw": 0.1, "left_knee": 1.5}}]}
    assert validate(extra_param, duck, {}, facts())[0] is None


def test_validator_rejects_out_of_range_param(duck):
    _, errs, _ = validate(json.loads(answer(("walk", {"vx": 0.6, "seconds": 3}))), duck, {}, facts())
    assert errs and "outside [0.0, 0.25]" in errs[0]


def test_validator_rejects_missing_precondition(duck):
    _, errs, _ = validate(json.loads(answer(("walk", {"vx": 0.1, "seconds": 3}))), duck, {}, facts(posture="sitting"))
    assert errs and "precondition of walk 'standing'" in errs[0]
    # standing up first makes the same walk valid: posture is tracked through the steps
    ok, errs, _ = validate(json.loads(answer(("stand", {}), ("walk", {"vx": 0.1, "seconds": 3}))), duck, {},
                           facts(posture="sitting"))
    assert ok and not errs
    _, errs, _ = validate(json.loads(answer(("walk", {"vx": 0.1, "seconds": 3}))), duck, {}, facts(battery=0.05))
    assert errs and "battery > 0.1" in errs[0]


def test_posture_noop_is_dropped(duck):
    ok, errs, _ = validate(json.loads(answer(("sit", {}), ("rest", {"seconds": 10}))), duck, {}, facts(posture="sitting"))
    assert not errs and [s["primitive"] for s in ok["steps"]] == ["rest"]
    _, errs, _ = validate(json.loads(answer(("sit", {}))), duck, {}, facts(posture="sitting"))
    assert "already has" in errs[0]


def test_resting_while_lying_is_not_a_noop(arm):
    ok, errs, _ = validate(json.loads(answer(("rest_pose", {"seconds": 10}))), arm, {}, facts(posture="lying"))
    assert not errs and ok["steps"][0]["primitive"] == "rest_pose"


def test_validator_limits_steps_and_duration(duck):
    _, errs, _ = validate(json.loads(answer(*[("nod", {"times": 1})] * 7)), duck, {}, facts())
    assert "at most 6" in errs[0]
    _, errs, _ = validate(json.loads(answer(("rest", {"seconds": 30}), ("nod", {"times": 1}))), duck, {},
                          facts(posture="sitting"))
    assert errs and "steps take 32.0s > max 30.0s" in errs[-1]
    _, errs, _ = validate(json.loads(answer(("wait", {"seconds": 5}), duration=90)), duck, {}, facts())
    assert "duration_s 90 > max" in errs[0]


def test_arm_cannot_walk(arm):
    _, errs, _ = validate(json.loads(answer(("walk", {"vx": 0.1}))), arm, {}, facts())
    assert errs and "unknown primitive 'walk'" in errs[0]


def test_skills_validated_per_body(duck, arm):
    skills = SharedState(EXAMPLES).skills
    assert set(usable_skills(skills, duck)) == {"greet_owner", "door_check"}
    assert set(usable_skills(skills, arm)) == {"greet_owner_wave"}
    ds = usable_skills(skills, duck)
    intent, errs, _ = validate({"steps": [{"primitive": "greet_owner"}]}, duck, ds, facts())
    assert [s["primitive"] for s in intent["steps"]] == ["turn_head", "nod"]
    _, errs, _ = validate({"steps": [{"primitive": "greet_owner"}]}, duck, ds, facts(owner_visible=False))
    assert "guard 'owner_visible'" in errs[0]


# ---------- intention layer: retry and fallback ----------

def test_bad_answer_is_reasked_once_with_the_error(duck):
    good = answer(("nod", {"times": 2}))
    m, w = make_mind(duck, [answer(("fly", {})), good])
    m.tick()
    assert m.current["source"] == "llm" and m.current["steps"][0]["primitive"] == "nod"
    retry_prompt = m.backend.prompts[1][1]
    assert "previous answer was rejected" in retry_prompt and "unknown primitive 'fly'" in retry_prompt
    assert [c["ok"] for c in m.call_log.calls] == [False, True]


def test_two_bad_answers_fall_back(duck):
    m, w = make_mind(duck, ["not json at all", answer(("walk", {"vx": 9}))])
    m.tick()
    assert m.current["source"] == "fallback"
    assert all(s["primitive"] in duck.primitives for s in m.current["steps"])


def test_offline_backend_falls_back_and_waits_before_retrying(duck):
    m, w = make_mind(duck, [BackendError("connection refused")])
    m.tick()
    assert m.current["source"] == "fallback" and len(m.call_log.calls) == 1
    for _ in range(60):
        m.tick()
    assert len(m.call_log.calls) == 1  # no new call inside the offline window
    assert all(h["source"] == "fallback" for h in m.history)


def test_fallback_only_mind_runs_a_day_segment(arm):
    m, w = make_mind(arm, None)
    for _ in range(600):
        m.tick()
    assert len(m.history) >= 20
    assert all(set(h["signature"]) <= set(arm.primitives) for h in m.history)
    assert rigidity(m.history)["distinct_action_sequences"] > 5


# ---------- interrupts ----------

def test_minor_interrupt_reflex_then_resume(duck):
    m, w = make_mind(duck, [answer(("look_around", {"seconds": 6}), ("nod", {"times": 2}))])
    m.tick()
    assert m.current["intention_text"] == "test"
    for _ in range(3):
        m.tick()
    m.perceive([{"kind": "sound", "label": "footsteps", "direction": -0.8}])
    assert m.current is None and m.paused is not None
    assert m.reflex[0]["primitive"] == "turn_head" and m.reflex[0]["params"]["yaw"] == -0.8
    for _ in range(3):
        m.tick()
    assert m.reflex == [] and m.current is not None and m.current["intention_text"] == "test"
    assert any("resumes 'test' at step 1" in line for line in m.lines)
    assert len(m.call_log.calls) == 1  # resuming needs no model call


def test_salient_interrupt_reaches_next_round(duck):
    answers = [answer(("look_around", {"seconds": 8})), answer(("approach_owner", {"seconds": 5}))]
    m, w = make_mind(duck, answers)
    m.tick()
    m.perceive(w.apply({"kind": "sound", "label": "keys_jingle", "direction": 1.2}))
    assert m.reflex[0]["params"]["yaw"] == 1.2
    for _ in range(4):
        m.tick()
    assert len(m.call_log.calls) == 2
    second = m.backend.prompts[1][1]
    assert "heard keys_jingle from the left" in second
    assert "expect: owner_leaves (w=0.80)" in second
    assert "Interrupted: 'test' at step 1/1" in second
    assert m.current["steps"][0]["primitive"] == "approach_owner"


def test_body_without_mic_ignores_sounds(arm):
    m, w = make_mind(arm, None)
    assert w.apply({"kind": "sound", "label": "doorbell", "direction": 1.0}) == []
    w.stranger_room = w.pet_room
    assert {"kind": "face", "who": "stranger"} in w.visibility_changes()


def test_stranger_reflex_stops_then_orients(arm):
    m, w = make_mind(arm, None)
    m.tick()
    m.perceive([{"kind": "face", "who": "stranger"}])
    assert [s["primitive"] for s in m.reflex] == ["stop", "turn_camera"]


def test_abort_if_fires_on_change_only(duck):
    m, w = make_mind(duck, [answer(("look_around", {"seconds": 8}), abort_if=["not owner_visible"])])
    m.tick()
    m.tick()
    w.owner_room = "kitchen" if w.pet_room != "kitchen" else "hallway"
    m.tick()
    assert any("aborts 'test': not owner_visible" in line for line in m.lines)


# ---------- prompt and misc ----------

def test_prompt_contains_the_contract_pieces(duck):
    m, w = make_mind(duck, [answer(("nod", {"times": 1}))])
    m.tick()
    system, user = m.backend.prompts[0]
    assert "walk(vx 0..0.25, vtheta -0.3..0.3, seconds 1..10)" in system and "greet_owner" in system
    for piece in ("Drives 0-1:", "Mood:", "Today's plan:", "What you have learned:", "Personality:", "Memories:"):
        assert piece in user


def test_missing_state_files_mean_defaults(duck, tmp_path):
    m, w = make_mind(duck, None, state_dir=tmp_path)
    for _ in range(30):
        m.tick()
    assert m.history and m.skills == {} and m.shared.rules == []


def test_parse_json_answer_handles_fences():
    assert parse_json_answer('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json_answer('Sure: {"a": {"b": 2}} done') == {"a": {"b": 2}}
    with pytest.raises(ValueError):
        parse_json_answer("no json")


def test_duck_command_mapping_has_no_joint_values(duck):
    obj = json.loads(answer(("walk", {"vx": 0.2, "vtheta": 0.1, "seconds": 3}), ("turn_head", {"yaw": 0.4}),
                            ("bow", {})))
    intent, _, _ = validate(obj, duck, {}, facts())
    cmds = [c for s in intent["steps"] for _, c in duck_commands(s)]
    assert cmds[0] == {"mode": "walk", "vx": 0.2, "vy": 0.0, "vtheta": 0.1}
    assert cmds[2]["head"] == {"head_yaw": 0.4, "head_pitch": 0.0}
    assert {"mode": "groundpick", "phase": 0.4} in cmds
    for p in duck.primitives:
        step = {"primitive": p, "params": {k: lo for k, (lo, hi) in duck.primitives[p]["params"].items()},
                "seconds": 2}
        for _, c in duck_commands(step):
            assert c["mode"] in ("walk", "sit", "groundpick")
            assert set(c) <= {"mode", "vx", "vy", "vtheta", "head", "phase"}


def test_rigidity_counts_repeats():
    h = [{"signature": ["nod"], "steps": ["nod(times=1)"], "text": "a", "source": "llm"}] * 3 + \
        [{"signature": ["wave"], "steps": ["wave(times=1)"], "text": "b", "source": "llm"}]
    r = rigidity(h)
    assert r["distinct_action_sequences"] == 2 and r["longest_identical_run"] == 3 and r["repeat_of_previous"] == 2


# ---------- backends without network ----------

def test_ollama_unreachable_falls_back(duck):
    from pet.mind.backends import OllamaBackend
    m, w = make_mind(duck, None)
    m.backend = OllamaBackend(url="http://127.0.0.1:9", timeout_s=2)
    m.tick()
    assert m.current["source"] == "fallback" and m.call_log.calls[0]["ok"] is False


def test_anthropic_backend_with_fake_client(duck):
    from types import SimpleNamespace as NS

    from pet.mind.backends import AnthropicBackend
    sent = {}

    def create(**kw):
        sent.update(kw)
        return NS(stop_reason="end_turn", content=[NS(type="text", text=answer(("nod", {"times": 2})))],
                  usage=NS(input_tokens=1500, output_tokens=120, cache_read_input_tokens=0,
                           cache_creation_input_tokens=0))

    be = AnthropicBackend.__new__(AnthropicBackend)
    be.client = NS(messages=NS(create=create))
    be.model, be.max_tokens, be.effort = "claude-haiku-5-5", 1024, "low"
    m, w = make_mind(duck, None)
    m.backend = be
    m.tick()
    assert m.current["source"] == "llm" and sent["model"] == "claude-haiku-5-5"
    assert sent["output_config"] == {"effort": "low"}
    assert m.call_log.calls[0]["api_cost_usd"] == pytest.approx(1500 * 0.1e-6 + 120 * 0.5e-6)


def test_stop_with_a_posture_effect_is_kept(duck):
    card = load_body_card("duck")
    for p in card["primitives"]:
        if p["name"] == "stop":
            p["effects"] = {"posture": "standing"}
    body = BodyCard(card)
    ok, errs, _ = validate({"steps": [{"primitive": "stop"}]}, body, {}, facts())
    assert not errs and ok["steps"][0]["primitive"] == "stop"


def test_nothing_valid_means_hold_without_crashing():
    card = {"name": "stuck", "sensors": [], "actuators": [],
            "primitives": [{"name": "dance", "params": {}, "preconditions": ["lying"], "duration_s_max": 3}]}
    m, w = make_mind(BodyCard(card), None)
    for _ in range(20):
        m.tick()
    assert m.current is None and any("holding without a command" in line for line in m.lines)
