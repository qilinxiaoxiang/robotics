import json

import pytest

from pet.learn import events as E
from pet.learn import instruct as I
from pet.learn import match as M
from pet.learn import reflect as R
from pet.learn import retrieve
from pet.learn import rw
from pet.learn import state as S
from pet.learn.llm import Usage


@pytest.fixture(autouse=True)
def tmp_state(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "STATE_DIR", tmp_path / "state")
    return tmp_path


def rule(**kw):
    r = {"id": "r1", "kind": "pavlovian", "trigger": "sound:keys", "outcome_or_effect": "owner:left",
         "weight": 0.3, "text": "keys then owner leaves", "evidence": {"confirm": 0, "omit": 0},
         "window_s": 120.0, "context": None}
    r.update(kw)
    return S.validate_rule(r)


# ---------------------------------------------------------------- Rescorla-Wagner

def test_rw_confirm_and_omit_formula():
    assert rw.rw_update(0.3, 0.2, True) == pytest.approx(0.3 + 0.2 * (1 - 0.3))
    assert rw.rw_update(0.3, 0.2, False) == pytest.approx(0.3 - 0.2 * 0.3)


def test_rw_converges_to_reinforcement_rate():
    v = 0.3
    for i in range(2000):
        v = rw.rw_update(v, 0.05, i % 5 != 0)  # 80 % confirmations
    assert v == pytest.approx(0.8, abs=0.05)


def test_rw_few_exposures_cross_075():
    r = rule()
    for _ in range(3):
        rw.confirm(r)
    assert r["weight"] > 0.75 and r["evidence"] == {"confirm": 3, "omit": 0}


def test_decay_unused_and_forgetting():
    a, b, c = rule(id="a", weight=0.5), rule(id="b", weight=0.5), rule(id="c", weight=0.051)
    inst = rule(id="d", weight=0.02, kind="operant", source="instruct")
    kept = rw.decay_unused([a, b, c, inst], used_ids={"a"})
    assert a["weight"] == 0.5
    assert b["weight"] < 0.5
    assert "c" not in {r["id"] for r in kept}           # fell under the forget line
    assert "d" in {r["id"] for r in kept} and inst["weight"] == 0.02  # owner's words stay


# ---------------------------------------------------------------- matcher windows

def ev(t, typ, **args):
    return E.Event(t, typ, args)


def test_matcher_confirm_inside_window_and_omit_outside():
    r = rule(window_s=60.0)
    m = M.run_day([r], [ev(0, "sound:keys"), ev(50, "owner:left"), ev(1000, "sound:keys"), ev(1070, "owner:left")])
    assert [x["result"] for x in m.log] == ["confirm", "omit"]
    assert r["evidence"] == {"confirm": 1, "omit": 1}


def test_matcher_omission_at_end_of_day():
    r = rule()
    m = M.run_day([r], [ev(100, "sound:keys")])
    assert [x["result"] for x in m.log] == ["omit"]


def test_matcher_second_trigger_inside_window_is_same_trial():
    r = rule(window_s=60.0)
    m = M.run_day([r], [ev(0, "sound:keys"), ev(10, "sound:keys"), ev(30, "owner:left")])
    assert [x["result"] for x in m.log] == ["confirm"]


def test_matcher_context_owner_home_skips_and_voids():
    r = rule(id="b", kind="operant", trigger="self:entered(bedroom)", outcome_or_effect="owner:said_no",
             window_s=10.0, context="owner_home")
    evs = [ev(0, "owner:left"), ev(5, "self:entered", room="bedroom"),          # away: no trial
           ev(100, "owner:returned"), ev(200, "self:entered", room="bedroom"),
           ev(204, "owner:said_no", text="No!"),                                 # confirm
           ev(300, "self:entered", room="bedroom"), ev(303, "owner:left")]       # voided
    m = M.run_day([r], evs)
    assert [x["result"] for x in m.log] == ["confirm", "void"]
    assert r["evidence"] == {"confirm": 1, "omit": 0}


def test_matcher_room_argument_must_match():
    r = rule(kind="operant", trigger="self:entered(bedroom)", outcome_or_effect="owner:said_no", window_s=10.0)
    m = M.run_day([r], [ev(0, "self:entered", room="kitchen"), ev(3, "owner:said_no", text="no")])
    assert m.log == []


def test_fuzzy_plain_sentence_counts_as_no():
    r = rule(kind="operant", trigger="self:entered(bedroom)", outcome_or_effect="owner:said_no", window_s=10.0)
    m = M.run_day([r], [ev(0, "self:entered", room="bedroom"), ev(4, "owner:said", text="不行，出去。")])
    assert [x["result"] for x in m.log] == ["confirm"]
    r2 = rule(id="r2", kind="operant", trigger="self:entered(bedroom)", outcome_or_effect="owner:said_no", window_s=10.0)
    m2 = M.run_day([r2], [ev(0, "self:entered", room="bedroom"), ev(4, "owner:said", text="I'm making coffee.")])
    assert [x["result"] for x in m2.log] == ["omit"]


def test_fuzzy_uses_model_answer_when_available(monkeypatch):
    calls = []

    def fake(system, user, schema, **kw):
        calls.append(json.loads(user))
        return {"instance": True, "confidence": 0.9, "reason": "telling the pet to leave"}, Usage("m", "mock", "fuzzy")

    monkeypatch.setattr(M, "call_json", fake)
    j = M.FuzzyJudge(use_model=True)
    r = rule(outcome_or_effect="owner:said_no")
    assert j(r, "Scram, little one") is True      # keywords alone would say no
    assert j(r, "Scram, little one") is True and len(calls) == 1  # cached


# ---------------------------------------------------------------- schema round-trip

def test_state_round_trip():
    S.save_rules([rule()])
    assert S.load_rules() == [rule()]
    plan = {"date": "2026-11-03", "intentions": [{"when": "08:30", "condition": "owner home", "goal": "sit by the door", "priority": 0.6}]}
    S.save_plan(plan)
    assert S.load_plan() == plan
    S.append_diary([{"t": "2026-11-02T08:55", "text": "The door closed.", "tags": ["owner"]}])
    assert S.load_diary()[0]["text"] == "The door closed."
    p = S.load_personality()
    S.save_personality(p)
    assert S.load_personality() == p
    card = S.load_body_card()
    sk = {"name": "greet_at_door", "steps": [{"primitive": "go_to", "params": {"place": "door"}},
                                             {"primitive": "vocalise", "params": {"kind": "happy_trill"}}],
          "guards": ["stop if picked up"], "source": "test"}
    S.save_skills([sk])
    assert S.load_skills() == [sk]
    E.write_log(S.STATE_DIR / "e.jsonl", [ev(1.5, "owner:said", text="hi")])
    assert E.read_log(S.STATE_DIR / "e.jsonl")[0].args == {"text": "hi"}


def test_state_rejects_bad_values():
    with pytest.raises(ValueError):
        rule(weight=1.5)
    with pytest.raises(ValueError):
        rule(kind="reflex")
    with pytest.raises(ValueError):
        S.validate_skill({"name": "x", "steps": [{"primitive": "fly", "params": {}}]}, S.load_body_card())
    with pytest.raises(ValueError):
        S.validate_skill({"name": "x", "steps": [{"primitive": "walk", "params": {"vx": 2.0}}]}, S.load_body_card())
    with pytest.raises(ValueError):
        E.validate(ev(0, "owner:said"))  # needs text


def test_personality_nudges_are_bounded():
    p = S.load_personality()
    new, applied = S.apply_nudges(p, [{"group": "drive_rates", "name": "social", "delta": 0.5},
                                      {"group": "secret", "name": "x", "delta": 0.1}])
    assert new["drive_rates"]["social"] == pytest.approx(p["drive_rates"]["social"] * 1.1)
    assert len(applied) == 1


# ---------------------------------------------------------------- reflection

GOOD = {
    "rules": [{"kind": "pavlovian", "trigger": "sound:keys", "outcome_or_effect": "owner:left", "window_s": 120,
               "context": "none", "text": "When the keys jingle, my human leaves soon.", "support": "2/2"},
              {"kind": "pavlovian", "trigger": "sound:spaceship", "outcome_or_effect": "owner:left", "window_s": 10,
               "context": "none", "text": "x", "support": "x"}],
    "diary": [{"time": "08:55", "text": "The keys jingled and the door closed. I waited by it.", "tags": ["owner"]},
              {"time": "23:10", "text": "My owner should go to bed earlier.", "tags": []},
              {"time": "9am", "text": "bad time", "tags": []}],
    "personality_nudges": [{"group": "drive_rates", "name": "social", "delta": 0.05, "reason": "alone all day"},
                           {"group": "drive_rates", "name": "social", "delta": 0.5, "reason": "too big"}],
    "plan": [{"when": "18:00", "condition": "owner away", "goal": "wait near the door", "priority": 0.7}],
    "skills": [{"name": "door_greeting", "steps": [{"primitive": "go_to", "params_json": "{\"place\": \"door\"}"},
                                                   {"primitive": "wiggle", "params_json": "{}"}],
                "guards": ["abort if a stranger is seen"]},
               {"name": "fly_away", "steps": [{"primitive": "fly", "params_json": "{}"}], "guards": []}],
}


def test_validate_reflection_keeps_good_drops_bad():
    clean, problems = R.validate_reflection(GOOD, "2026-11-02", S.load_body_card())
    assert [r["trigger"] for r in clean["rules"]] == ["sound:keys"]
    assert clean["rules"][0]["context"] is None
    assert [d["t"] for d in clean["diary"]] == ["2026-11-02T08:55"]     # judging line and bad time dropped
    assert any("evaluating the owner" in p for p in problems)
    assert len(clean["personality_nudges"]) == 1
    assert clean["plan"]["date"] == "2026-11-03"
    assert [s["name"] for s in clean["skills"]] == ["door_greeting"]
    assert clean["skills"][0]["steps"][0]["params"] == {"place": "door"}


def test_nightly_with_mocked_model_writes_state_and_logs_cost(tmp_state):
    seen = {}

    def fake(system, user, schema, **kw):
        seen["system"], seen["user"] = system, json.loads(user)
        return GOOD, Usage("claude-opus-5-5", "mock", "nightly_reflection", 5000, 3000, cost_usd=0.08)

    res = R.nightly(E.synth_day(1), "2026-11-02", call=fake, log_dir=tmp_state / "out")
    assert "never judges" in seen["system"]
    assert seen["user"]["day"]["timeline"]
    rules = S.load_rules()
    assert len(rules) == 1 and rules[0]["weight"] == S.INITIAL_WEIGHT and rules[0]["source"] == "model:claude-opus-5-5"
    assert S.load_plan()["intentions"][0]["goal"] == "wait near the door"
    assert len(S.load_diary()) == 1 and S.load_skills()[0]["name"] == "door_greeting"
    assert res["comparison"]["both"] == [["sound:keys", "owner:left"]]
    logged = json.loads((tmp_state / "out" / "reflections.jsonl").read_text().splitlines()[0])
    assert logged["usage"]["cost_usd"] == 0.08


def test_existing_rule_keeps_weight_when_reproposed():
    S.save_rules([rule(weight=0.9, id="old")])
    rules, added = R.merge_rules(S.load_rules(), [{"kind": "pavlovian", "trigger": "sound:keys",
                                                   "outcome_or_effect": "owner:left", "window_s": 60,
                                                   "context": None, "text": "t"}], "2026-11-03", "x")
    assert added == [] and rules[0]["weight"] == 0.9


def test_fallback_finds_planted_regularities():
    found = {(r["trigger"], r["outcome_or_effect"]) for r in R.fallback_rules(E.synth_day(1, seed=0))}
    assert ("sound:keys", "owner:left") in found
    assert ("self:entered(bedroom)", "owner:said_no") in found
    assert ("sound:tv", "sound:doorbell") in found


def test_nightly_without_model_falls_back(monkeypatch):
    from pet.learn import llm

    def unavailable(*a, **k):
        raise llm.LLMUnavailable("none")

    res = R.nightly(E.synth_day(1), "2026-11-02", call=unavailable)
    assert res["source"] == "fallback" and S.load_rules()


# ---------------------------------------------------------------- instruct

def fake_answer(ans):
    def f(system, user, schema, **kw):
        return ans, Usage("claude-haiku-5-5", "mock", "instruct")
    return f


def test_instruct_parses_rule_and_saves():
    ans = {"is_instruction": True, "reason": "", "trigger": "self:entered(bedroom)", "outcome_or_effect": "owner:said_no",
           "direction": "less", "window_s": 10, "context": "owner_home", "text": "I should stay out of the bedroom."}
    r, why = I.instruct("别进卧室", call=fake_answer(ans), date="2026-11-02", save=True)
    assert why == "ok" and r["kind"] == "operant" and r["weight"] == I.INSTRUCT_WEIGHT and r["source"] == "instruct"
    assert r["context"] == "owner_home" and S.load_rules()[0]["said"] == "别进卧室"


def test_instruct_rejects_chatter_and_unknown_events():
    no = {"is_instruction": False, "reason": "a remark about the weather", "trigger": "", "outcome_or_effect": "",
          "direction": "none", "window_s": 0, "context": "none", "text": ""}
    assert I.instruct("Nice weather today", call=fake_answer(no))[0] is None
    bad = dict(no, is_instruction=True, trigger="self:flew", outcome_or_effect="owner:said_no")
    r, why = I.instruct("Don't fly", call=fake_answer(bad))
    assert r is None and "vocabulary" in why


# ---------------------------------------------------------------- retrieval

def test_retrieve_hash_fallback_ranks_overlap():
    entries = [{"t": "2026-11-02T08:55", "text": "keys jingled then the door closed"},
               {"t": "2026-11-02T12:00", "text": "a nap in the sun by the window"}]
    hits = retrieve.retrieve("the keys jingled", k=1, entries=entries, force_hash=True)
    assert hits[0]["text"].startswith("keys")
