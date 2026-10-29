"""The voice layer's inbox in the runner: owner tasks pre-empt, run once and report back; rules reach rules.json and the
matcher; praise reaches the drives. Fixtures under fixtures/voice/ are real pet/voice output: the Chinese fetch task
(pet/voice/out/e2e-zh01-robot-wav), the bedroom rule (pet/voice/out/e2e-typed-rule) and 停下 / 过来 / 坐下 / 好鸭子，真乖
typed through `pet.voice.voice --say` on 2026-10-29."""
import json
import shutil
from pathlib import Path

from pet.mind.brain_link import WALK_ZERO
from pet.mind.inbox import VoiceInbox, translate_task
from pet.mind.state import EXAMPLES

from .test_runner import Rig, answer

FIX = Path(__file__).parent / "fixtures" / "voice"
SAID = [json.loads(ln) for ln in (FIX / "owner_said.jsonl").read_text().splitlines() if ln.strip()]


def said(text):
    return next(d for d in SAID if d["text"] == text)


class VoiceRig(Rig):
    def __init__(self, tmp_path, answers, **kw):
        state = tmp_path / "state"
        shutil.copytree(EXAMPLES, state)
        self.state, self.inbox = state, tmp_path / "inbox"
        (self.inbox / "tasks").mkdir(parents=True)
        (self.inbox / "rules").mkdir()
        super().__init__(tmp_path, answers, state_dir=state, inbox=self.inbox, **kw)

    def say(self, text, task=None, rule=None):
        """What pet/voice does: the file first (renamed into place), then the sentence line."""
        if task:
            shutil.copy(FIX / "tasks" / task, self.inbox / "tasks" / task)
        if rule:
            shutil.copy(FIX / "rules" / rule, self.inbox / "rules" / rule)
        with (self.inbox / "owner_said.jsonl").open("a") as f:
            f.write(json.dumps(said(text), ensure_ascii=False) + "\n")

    def owner(self, kind="owner_task"):
        return [e for e in self.r.events if e["kind"] == kind]


LONG_WAIT = answer(("wait", {"seconds": 10}), text="just waiting")


def test_fetch_task_preempts_runs_once_and_reports(tmp_path):
    rig = VoiceRig(tmp_path, [LONG_WAIT] * 6).started()
    rig.advance(2.0)
    assert rig.r.mind.current["intention_text"] == "just waiting"
    rig.say("把橙色方块雕来。", task="fetch_zh.json")
    rig.advance(1.0)
    assert (rig.inbox / "tasks" / "fetch_zh.json.done").exists() and not (rig.inbox / "tasks" / "fetch_zh.json").exists()
    text = rig.text()
    assert "STOP 'just waiting'" in text and "INTENT [owner]" in text
    assert "groundpick -> bow" in text  # the voice layer's card name for the runner's bow
    assert rig.owner()[0]["outcome"] == "started"
    rig.advance(25.0)
    done = rig.owner()[-1]
    assert done["outcome"] == "done" and done["steps_done"] == done["steps"] == 5
    assert {"mode": "groundpick", "phase": 0.4} in rig.cmds() and {"mode": "groundpick", "phase": 0.9} in rig.cmds()
    assert any("did what the owner asked" in txt for _, txt in rig.r.world.recent_events)  # the mind sees it
    types = [e.type for e in rig.r.learn_events]
    assert "owner:said" in types and any(e.type == "self:did" and e.args["primitive"] == "bow"
                                         for e in rig.r.learn_events)
    rig.advance(5.0)
    assert sum(1 for h in rig.r.mind.history if h["source"] == "owner") == 1  # never twice


def test_bedroom_rule_reaches_rules_json_the_prompt_and_the_matcher(tmp_path):
    rig = VoiceRig(tmp_path, [LONG_WAIT] * 4).started()
    rig.say("Stop going in the bedroom", rule="bedroom.json")
    rig.advance(1.0)
    assert (rig.inbox / "rules" / "bedroom.json.done").exists()
    rules = json.loads((rig.state / "rules.json").read_text())
    mine = [r for r in rules if r["trigger"] == "self:entered(bedroom)" and r["outcome_or_effect"] == "owner:said_no"]
    assert len(mine) == 1 and mine[0]["id"] == "i20261029_deda17" and mine[0]["source"] == "instruct"
    assert any("I will not go into the bedroom" in t for t in rig.r.shared.rules_text())
    assert "i20261029_deda17" in rig.r.matcher.by_id
    rig.r.learn("self:entered", room="bedroom")
    rig.r.learn("owner:said_no", text="no!")
    assert rig.r.matcher.log[-1]["rule"] == "i20261029_deda17" and rig.r.matcher.log[-1]["result"] == "confirm"
    shutil.copy(FIX / "rules" / "bedroom.json", rig.inbox / "rules" / "again.json")  # same trigger and outcome
    rig.advance(1.0)
    rules = json.loads((rig.state / "rules.json").read_text())
    assert sum(1 for r in rules if r["trigger"] == "self:entered(bedroom)") == 1


def test_praise_is_felt_and_replans(tmp_path):
    rig = VoiceRig(tmp_path, [LONG_WAIT] * 6).started()
    rig.advance(1.0)
    before = rig.r.mind.drives.valence
    rig.say("好鸭子，真乖")
    rig.advance(1.0)
    assert rig.r.mind.drives.valence >= min(1.0, before + 0.3)
    assert 'the owner said "好鸭子，真乖" (praise)' in rig.text()
    types = [e.type for e in rig.r.learn_events]
    i = types.index("owner:said")
    assert types[i + 1] == "owner:praised" and rig.r.learn_events[i + 1].args["text"] == "好鸭子，真乖"
    assert not rig.owner()  # ignore: no task


def test_stop_come_sit_trio(tmp_path):
    rig = VoiceRig(tmp_path, [LONG_WAIT] * 10).started()
    rig.advance(2.0)
    rig.say("过来", task="come_zh.json")
    rig.advance(1.0)
    assert any(c.get("mode") == "walk" and c.get("vx") == 0.2 for c in rig.cmds()) is False  # turn_head first
    rig.advance(2.0)
    assert any(c.get("mode") == "walk" and c.get("vx") == 0.2 and c.get("for_s") for c in rig.cmds())
    rig.say("停下", task="stop_zh.json")
    rig.advance(1.0)
    outcomes = [e["outcome"] for e in rig.owner() if e["outcome"] != "started"]
    assert outcomes[0] == "replaced by a newer request"
    assert rig.cmds()[-1] == WALK_ZERO  # stop: the zero-command walk at once
    rig.advance(2.0)
    rig.say("坐下", task="sit_zh.json")
    rig.advance(6.0)
    assert {"mode": "sit"} in rig.cmds() and rig.r.world.posture == "sitting"
    assert "sit: parameter seconds not taken" in rig.text()
    assert "abort condition 'not standing' left out" in rig.text()
    assert [e["outcome"] for e in rig.owner() if e["outcome"] != "started"] == [
        "replaced by a newer request", "done", "done"]
    rig.say("过来", task="come_zh.json")  # sitting: stand first, then come
    rig.advance(1.0)
    assert "stand first (the body was sitting)" in rig.text()


def test_task_while_stopped_is_dropped_not_kept(tmp_path):
    rig = VoiceRig(tmp_path, [LONG_WAIT] * 4).started()
    rig.fake.fall()
    rig.advance(1.0)
    assert rig.r.state == "stopped"
    rig.say("过来", task="come_zh.json")
    rig.advance(1.0)
    assert (rig.inbox / "tasks" / "come_zh.json.done").exists()
    assert rig.owner()[-1]["outcome"].startswith("dropped: the runner is stopped")


def test_old_sentences_are_history(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "owner_said.jsonl").write_text(json.dumps(said("好鸭子，真乖"), ensure_ascii=False) + "\n")
    vi = VoiceInbox(inbox)
    assert vi.new_said() == []
    with (inbox / "owner_said.jsonl").open("a") as f:
        f.write(json.dumps(said("停下"), ensure_ascii=False) + "\n" + '{"partial": ')
    assert [d["text"] for d in vi.new_said()] == ["停下"]  # the half-written line waits


def test_translate_keeps_only_what_the_card_takes(tmp_path):
    from pet.mind.body import BodyCard
    from pet.mind.runner import allowed_names, filtered_card
    from pet.mind.state import load_body_card
    head_only = BodyCard(filtered_card(load_body_card("duck"), allowed_names("head")))
    obj, notes = translate_task(json.loads((FIX / "tasks" / "fetch_zh.json").read_text()), head_only)
    assert [s["primitive"] for s in obj["steps"]] == ["look_around", "turn_head"]
    assert any("walk left out" in n for n in notes) and any("groundpick left out" in n for n in notes)
