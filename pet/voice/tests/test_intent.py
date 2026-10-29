"""intent.py with a scripted backend: validation through pet/mind's validator and pet/learn's rule parser, re-asks,
reactions, and the shape of the 20-sentence test set. No model calls."""
import json

import pytest

from pet.mind.backends import ScriptedBackend
from pet.mind.state import EXAMPLES
from pet.voice import intent


def make(answers):
    be = ScriptedBackend([json.dumps(a) if isinstance(a, dict) else a for a in answers])
    return intent.Interpreter("live", EXAMPLES, backend=be), be


def test_task_is_validated_and_filled():
    it, be = make([{"kind": "task", "reaction": "none", "intention_text": "I go and pick it up",
                    "steps": [{"primitive": "look_around", "params": {"seconds": 3}},
                              {"primitive": "walk", "params": {"vx": 0.2}},
                              {"primitive": "groundpick", "params": {"phase": 1.0}}],
                    "abort_if": ["not standing"], "say_back": None}])
    r = it.interpret("把橙色方块叼来", "zh")
    assert r["kind"] == "task" and r["rule"] is None and r["attempts"] == 1
    steps = r["task"]["steps"]
    assert [s["primitive"] for s in steps] == ["look_around", "walk", "groundpick"]
    assert steps[1]["params"] == {"vx": 0.2, "vtheta": 0.0, "seconds": 1.0}      # missing params: closest to 0
    assert r["task"]["say_back"] is None and r["task"]["abort_if"] == ["not standing"]
    assert "look_around" in be.prompts[0][0] and "self:entered(room)" in be.prompts[0][0]


def test_out_of_range_param_is_reasked_once():
    it, be = make([{"kind": "task", "reaction": "none", "intention_text": "run", "steps": [{"primitive": "walk", "params": {"vx": 2.0}}]},
                   {"kind": "task", "reaction": "none", "intention_text": "walk", "steps": [{"primitive": "walk", "params": {"vx": 0.25}}]}])
    r = it.interpret("Come here.")
    assert r["kind"] == "task" and r["attempts"] == 2
    assert "outside [0.0, 0.25]" in r["errors"][0]
    assert "rejected" in be.prompts[1][1]


def test_twice_rejected_is_ignore_with_reason():
    bad = {"kind": "task", "reaction": "none", "intention_text": "x", "steps": [{"primitive": "fly", "params": {}}]}
    it, _ = make([bad, bad])
    r = it.interpret("Fly to the kitchen.")
    assert r["kind"] == "ignore" and r["task"] is None and len(r["errors"]) == 2
    assert "twice" in r["reason"]


def test_no_raw_joint_command_can_pass():
    it, _ = make([{"kind": "task", "reaction": "none", "intention_text": "x",
                   "steps": [{"primitive": "walk", "params": {"vx": 0.1}, "joint": {"id": 5, "pos": 2048}}]},
                  {"kind": "ignore", "reaction": "none", "reason": "gave up"}])
    r = it.interpret("whatever")
    assert r["kind"] == "ignore" and "unexpected keys" in r["errors"][0]


def test_rule_goes_through_learn_parser():
    it, _ = make([{"kind": "rule", "reaction": "said_no", "trigger": "self:entered(bedroom)", "outcome_or_effect": "owner:said_no",
                   "direction": "less", "window_s": 10, "context": "owner_home", "text": "I stay out of the bedroom."}])
    r = it.interpret("Stop going in the bedroom.", "en", date="2026-10-29")
    assert r["kind"] == "rule" and r["task"] is None and r["reaction"] == "said_no"
    ru = r["rule"]
    assert ru["kind"] == "operant" and ru["trigger"] == "self:entered(bedroom)" and ru["weight"] == 0.6
    assert ru["source"] == "instruct" and ru["said"] == "Stop going in the bedroom." and ru["created"] == "2026-10-29"


def test_rule_outside_vocabulary_is_reasked():
    it, _ = make([{"kind": "rule", "reaction": "none", "trigger": "self:smelled(cheese)", "outcome_or_effect": "owner:said_no",
                   "direction": "less", "window_s": 10, "context": "owner_home", "text": "x"},
                  {"kind": "ignore", "reaction": "none", "reason": "cannot express it"}])
    r = it.interpret("Don't sniff the cheese.")
    assert r["kind"] == "ignore" and "outside the event vocabulary" in r["errors"][0]


def test_praise_is_ignore_with_reaction():
    it, _ = make([{"kind": "ignore", "reaction": "praised", "reason": "praise alone"}])
    r = it.interpret("好鸭子")
    assert r["kind"] == "ignore" and r["reaction"] == "praised" and r["reason"] == "praise alone"


def test_unparseable_answer_is_ignore():
    it, _ = make(["I would rather not say."])
    r = it.interpret("Sit.")
    assert r["kind"] == "ignore" and r["errors"] and "nothing done" in r["reason"]


def test_posture_fact_is_used():
    it, _ = make([{"kind": "task", "reaction": "none", "intention_text": "walk", "steps": [{"primitive": "walk", "params": {}}]},
                  {"kind": "task", "reaction": "none", "intention_text": "walk", "steps": [{"primitive": "walk", "params": {}}]}])
    r = it.interpret("Come here.", facts={"posture": "sitting"})
    assert r["kind"] == "ignore" and "precondition of walk" in r["errors"][0]


def test_eval_set_shape():
    s = intent.EVAL_SENTENCES
    assert len(s) == 20
    zh = [x for x in s if any("一" <= c <= "鿿" for c in x[0])]
    assert len(zh) >= 9 and len(s) - len(zh) >= 9          # both languages, near half each
    assert {k for _, k, _ in s} == {"task", "rule", "ignore"}
    assert sum(1 for _, k, r in s if r == "praised") == 2
    assert all(k in intent.KINDS for _, k, _ in s)


def test_system_prompt_lists_every_live_primitive():
    it, _ = make([])
    for name in it.body.primitives:
        assert f"- {name}(" in it.system
    assert "never speaks" in it.system
