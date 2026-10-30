"""Runner tests: sequencing, aborts, readback, ownership of the control file. No model, no sim: a ScriptedBackend
answers, FakeBrain stands in for walk_brain.py, and a hand-driven clock makes every timing exact."""
import json

import pytest

from pet.mind.backends import ScriptedBackend
from pet.mind.body import BodyCard
from pet.mind.brain_link import WALK_ZERO, LocalLink, Readback, is_idle, same_cmd
from pet.mind.perception import FaceAdapter, SoundOnset, TouchDetector
from pet.mind.prompt import system_prompt
from pet.mind.runner import FakeBrain, Runner, allowed_names, filtered_card
from pet.mind.state import EXAMPLES, SharedState, load_body_card

T0 = 1_793_300_000.0  # a fixed wall time (09:33 local on 2026-10-29 in New York is irrelevant to the checks)


class Clock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


def answer(*steps, duration=10, abort_if=(), text="test"):
    return json.dumps({"intention_text": text, "steps": [{"primitive": p, "params": prm} for p, prm in steps],
                       "duration_s": duration, "abort_if": list(abort_if), "mood_note": "ok"})


class Rig:
    def __init__(self, tmp_path, answers, events=None, allow=None, resume_s=30.0, state_dir=EXAMPLES, **runner_kw):
        self.cmd, self.log, self.out = tmp_path / "cmd.json", tmp_path / "log.jsonl", tmp_path / "brain.out"
        self.cmd.write_text('{"mode": "monitor"}')
        self.fake = FakeBrain(self.cmd, self.log, self.out)
        self.clock = Clock(T0)
        body = BodyCard(filtered_card(load_body_card("duck"), allowed_names(allow or "all")))
        backend = ScriptedBackend(answers) if answers is not None else None
        self.r = Runner(body, SharedState(state_dir), backend, LocalLink(self.cmd, self.log, self.out, from_start=True),
                        tmp_path / "out", mode="dry", clock_fn=self.clock, events=events, resume_s=resume_s,
                        **runner_kw)

    def advance(self, seconds, dt=0.1):
        for _ in range(int(round(seconds / dt))):
            self.clock.t += dt
            self.fake.step(self.clock.t)
            if self.r.mind.pending:  # the scripted answer runs in the mind's thread: a loaded host must not make a
                self.r.mind.pending[0].result(timeout=10)  # tick miss it (2026-10-29: one failure at load 90)
            self.r.step(self.clock.t)

    def started(self):
        self.r.begin()
        self.advance(3.0)
        assert self.r.state == "running", self.r.mind.lines
        return self

    def cmds(self):
        return [c["cmd"] for c in self.r.commands]

    def app_writes(self, cmd):
        """The app's write: a value the runner did not produce (duck-command.py style atomic replace)."""
        tmp = self.cmd.with_suffix(".live.tmp")
        tmp.write_text(json.dumps(cmd))
        tmp.replace(self.cmd)

    def text(self):
        return "\n".join(self.r.mind.lines)


# ---------- readback parser ----------

def test_readback_lines():
    rb = Readback()
    ev = rb.feed([], ["STOP -> zero command: ground pick complete, stand61 takes over"], 0.0)
    assert ev == [{"kind": "handback", "why": "ground pick complete, stand61 takes over"}]
    ev = rb.feed([], ["STOP -> stand: tilt 31.2 deg over 30"], 1.0)
    assert ev[0]["kind"] == "guard_trip" and ev[0]["brain_wrote"] == "stand"
    ev = rb.feed([], ["torque refused: battery stop marker present"], 2.0)
    assert ev == [{"kind": "refused", "what": "torque", "why": "battery stop marker present"}]
    ev = rb.feed([], ["kick 'a' refused: not in stand or walk mode"], 2.0)
    assert ev[0]["kind"] == "refused" and ev[0]["what"] == "kick 'a'"
    ev = rb.feed([], ["sit: STALLED, still standing on the sitstand policy: knees +0.02 / -0.03 rad"], 3.0)
    assert ev[0]["kind"] == "refused" and ev[0]["what"] == "sit"
    ev = rb.feed([], ["sit: RISE FAILED, not up 4.0 s after the stand-up command (knees, pitch rate or tilt out of "
                      "range: tilt 31 deg); sitting back down (posture flag 1)."], 3.5)
    assert ev == [{"kind": "refused", "what": "stand", "why": "rise failed: the body sat back down"}]
    ev = rb.feed([], ["HARDWARE ERROR (address 70) on ['left_knee']: the policy holds its last goals"], 4.0)
    assert ev[0]["kind"] == "guard_trip" and rb.hw_fault
    ev = rb.feed([], ["hardware errors cleared"], 5.0)
    assert ev[0]["kind"] == "brain_cleared" and not rb.hw_fault
    ev = rb.feed([], ["IMU LOST: no IMU sample for 0.61 s, the policy holds its last goals; hold the robot."], 6.0)
    assert ev[0]["kind"] == "guard_trip" and rb.imu_lost
    assert rb.feed([], ["IMU back"], 7.0)[0]["kind"] == "brain_cleared" and not rb.imu_lost
    assert rb.feed([], ["mode -> walk"], 8.0) == [{"kind": "brain_mode", "mode": "walk"}]
    assert rb.feed([], ["walk    50.0 Hz read 12.0 ms imu_age   10 ms applied   19 ms | body g [-0.05 +0.01 -1.00]"], 9.0) == []


def test_readback_fall_then_standing():
    rb = Readback()
    rows = [{"t": t / 10, "mode": "walk", "gb": [0.0, 0.0, -0.99]} for t in range(10)]
    assert rb.feed(rows, [], 1.0) == [] and rb.posture == "standing"
    one = [{"t": 1.0, "mode": "walk", "gb": [0.9, 0.0, -0.3]}, {"t": 1.1, "mode": "walk", "gb": [0.0, 0.0, -0.99]}]
    assert rb.feed(one, [], 1.1) == []  # one bad frame is not a fall
    rows = [{"t": 2 + t / 20, "mode": "walk", "gb": [0.9, 0.0, -0.3]} for t in range(10)]
    ev = rb.feed(rows, [], 3.0)
    assert [e["kind"] for e in ev] == ["fell"] and rb.posture == "fallen"
    rows = [{"t": 10 + t / 10, "mode": "walk", "gb": [0.0, 0.0, -0.99]} for t in range(25)]
    ev = rb.feed(rows, [], 13.0)
    assert [e["kind"] for e in ev] == ["standing"] and rb.posture == "standing"


def test_readback_seat_stall_and_stand():
    rb = Readback()
    rb.feed([{"t": 0, "mode": "walk", "gb": [0, 0, -1]}], [], 0)
    rows = [{"t": 1, "mode": "sit", "gb": [0, 0, -1], "sit_phase": "prep"},
            {"t": 2, "mode": "sit", "gb": [0, 0, -1], "sit_phase": "down"},
            {"t": 4, "mode": "sit", "gb": [0, 0, -1], "sit_phase": "seated", "sit_stalled": False},
            {"t": 4.1, "mode": "sit", "gb": [0, 0, -1], "sit_phase": "seated", "sit_stalled": False}]
    assert [e["kind"] for e in rb.feed(rows, [], 4.1)] == ["seated"] and rb.posture == "sitting"
    ev = rb.feed([{"t": 8, "mode": "walk", "gb": [0, 0, -1]}], [], 8)
    assert [e["kind"] for e in ev] == ["standing"] and rb.posture == "standing"
    rows = [{"t": 9, "mode": "sit", "gb": [0, 0, -1], "sit_phase": "prep"},
            {"t": 12, "mode": "sit", "gb": [0, 0, -1], "sit_phase": "seated", "sit_stalled": True}]
    assert rb.feed(rows, [], 12) == [] and rb.posture == "standing"  # a stalled seat is not a seat


def test_idle_detection():
    assert is_idle(WALK_ZERO) and is_idle({"mode": "walk", "vx": 0, "vy": 0, "vtheta": 0, "for_s": 0.6})
    assert is_idle({"mode": "walk", "vx": 0, "vy": 0, "vtheta": 0, "head": {"head_yaw": 0.3}}) and is_idle({"mode": "sit"})
    assert not is_idle({"mode": "walk", "vx": 0.25, "vy": 0, "vtheta": 0}) and not is_idle({"mode": "stand"})
    assert not is_idle({"mode": "walk", "vx": 0, "vy": 0, "vtheta": 0, "quack": 3})
    assert same_cmd({"mode": "walk", "vx": 0, "vy": 0.0, "vtheta": 0}, WALK_ZERO)


# ---------- sequencing ----------

def test_steps_run_in_order_with_their_commands(tmp_path):
    rig = Rig(tmp_path, [answer(("turn_head", {"yaw": 0.5, "pitch": 0.0}), ("nod", {"times": 1}), ("wait", {"seconds": 2}))]).started()
    assert rig.cmds()[0] == WALK_ZERO  # the start command
    rig.advance(7.0)   # the model's answer is picked up at the next poll (0.5 s), then the steps run
    c = rig.cmds()[1:]
    assert c[0]["head"] == {"head_yaw": 0.5, "head_pitch": 0.0} and c[0]["mode"] == "walk"
    assert [x["head"]["head_pitch"] for x in c[1:4]] == [0.3, -0.1, 0]      # nod: down, up, centre
    assert c[4] == WALK_ZERO                                                 # idle after the intention
    times = [x["session_s"] for x in rig.r.commands[1:]]
    assert times[2] - times[1] == pytest.approx(0.4, abs=0.06) and times[1] - times[0] == pytest.approx(1.1, abs=0.06)  # a step starts on the tick after the previous one ended
    assert rig.fake.mode == "walk" and rig.r.state == "running"
    assert "step turn_head(yaw=0.5, pitch=0)" in rig.text()


def test_walk_carries_for_s_and_ends_at_zero(tmp_path):
    rig = Rig(tmp_path, [answer(("walk", {"vx": 0.2, "vtheta": 0.1, "seconds": 3}))]).started()
    rig.advance(1.0)
    walk = rig.cmds()[1]
    assert walk["vx"] == 0.2 and walk["vtheta"] == 0.1 and walk["for_s"] == 4.0
    rig.advance(3.2)
    assert rig.cmds()[2] == WALK_ZERO
    t = [c["session_s"] for c in rig.r.commands]
    assert t[2] - t[1] == pytest.approx(3.0, abs=0.06)
    assert not any("walk for_s" in ln for ln in rig.out.read_text().splitlines())  # the runner stopped it first


def test_sit_rest_stand_follow_the_body(tmp_path):
    rig = Rig(tmp_path, [answer(("sit", {}), ("rest", {"seconds": 5}), ("stand", {}))]).started()
    rig.advance(1.0)
    assert rig.cmds()[1] == {"mode": "sit"}
    rig.advance(4.0)
    assert rig.r.world.posture == "sitting" and "body: seated" in rig.text()
    rig.advance(1.0)
    assert {"mode": "sit", "head": {"head_pitch": -0.3}} in rig.cmds()
    rig.advance(8.0)
    assert rig.cmds()[3] == {"mode": "sit"}  # stand from a seat: re-arm the rise first (sit-rise-20261029)
    assert rig.cmds()[4] == WALK_ZERO  # then the zero-command walk stands it up
    assert "body: standing (after sit)" in rig.text()
    assert [c["why"] for c in rig.r.commands[:3]] == ["start", "sit", "rest"]
    assert all(c["why"] == "stand" for c in rig.r.commands[3:5])


def test_idle_between_intentions_keeps_a_seated_duck_seated(tmp_path):
    rig = Rig(tmp_path, [answer(("sit", {}), ("rest", {"seconds": 5})), answer(("turn_head", {"yaw": 0.3, "pitch": 0}))]).started()
    rig.advance(12.0)
    cmds = rig.cmds()
    assert cmds[-1] == {"mode": "sit"}  # idle for a seated body is the plain sit, not a stand-up
    rig.advance(5.0)
    assert {"mode": "sit", "head": {"head_yaw": 0.3, "head_pitch": 0.0}} in rig.cmds()  # the head moves in sit mode
    assert "body: standing" not in rig.text()


def test_abort_condition_ends_the_intention(tmp_path):
    events = [(0.5, {"kind": "face", "who": "owner"}), (4.0, {"kind": "face_lost", "who": "owner"})]
    rig = Rig(tmp_path, [answer(("wait", {"seconds": 10}), abort_if=["not owner_visible"]),
                         answer(("turn_head", {"yaw": -0.5, "pitch": 0}))], events=events).started()
    rig.advance(1.0)
    assert rig.r.mind.current and rig.r.mind.current["abort_if"] == ["not owner_visible"]
    rig.advance(4.0)
    assert "aborts 'test': not owner_visible" in rig.text()
    rig.advance(2.0)
    assert any(c.get("head") == {"head_yaw": -0.5, "head_pitch": 0.0} for c in rig.cmds())  # the next intention started early


def test_touch_reflex_runs_first_then_replans(tmp_path):
    events = [(2.0, {"kind": "touch", "where": "head"})]
    rig = Rig(tmp_path, [answer(("walk", {"vx": 0.2, "vtheta": 0, "seconds": 8})), answer(("nod", {"times": 2}))],
              events=events).started()
    rig.advance(1.0)
    assert rig.cmds()[-1]["vx"] == 0.2
    rig.advance(1.1)
    assert "reflex: stop() -> nod(times=1)" in rig.text()
    after = rig.cmds()[2:]
    assert after[0] == WALK_ZERO and after[0] is not None  # stop: the walk ended at once, before the nod
    rig.advance(4.0)
    heads = [c["head"]["head_pitch"] for c in rig.cmds() if "head" in c]
    assert heads[:2] == [0.3, -0.1]
    assert any(h["signature"] == ["nod"] for h in rig.r.mind.history)  # the touch made it re-plan


def test_app_write_yields_and_idle_resumes(tmp_path):
    rig = Rig(tmp_path, [answer(("wait", {"seconds": 10})), answer(("nod", {"times": 1}))], resume_s=5.0).started()
    rig.advance(1.0)
    n = len(rig.r.commands)
    rig.app_writes({"mode": "walk", "vx": 0.25, "vy": 0, "vtheta": 0, "for_s": 0.6})
    rig.advance(2.0)
    assert rig.r.state == "yield" and rig.r.mind.current is None and "YIELD" in rig.text()
    rig.advance(3.0)
    assert len(rig.r.commands) == n  # nothing written while someone else drives
    rig.app_writes(dict(WALK_ZERO))
    rig.advance(6.0)
    assert rig.r.state == "running" and "RESUME" in rig.text()
    rig.advance(2.0)
    assert len(rig.r.commands) > n and any("head" in c for c in rig.cmds()[n:])  # the nod ran after the resume


def test_brain_handback_after_bow_is_not_a_yield(tmp_path):
    rig = Rig(tmp_path, [answer(("bow", {}))]).started()
    rig.advance(1.0)
    assert rig.cmds()[1] == {"mode": "groundpick", "phase": 0.4}
    rig.advance(4.0)
    assert {"mode": "groundpick", "phase": 0.9} in rig.cmds()
    assert not any(c.get("mode") == "groundpick" and c.get("phase", 0) >= 1.0 for c in rig.cmds())
    rig.advance(4.0)
    assert "brain wrote the file itself: zero command" in rig.text()
    assert rig.r.state == "running" and rig.r.counters["yield"] == 0 and rig.r.counters["handback"] == 1


def test_fall_stops_the_runner_until_the_brain_is_back(tmp_path):
    rig = Rig(tmp_path, [answer(("wait", {"seconds": 10})), answer(("nod", {"times": 1}))], resume_s=3.0).started()
    rig.advance(1.0)
    rig.fake.fall()
    rig.advance(1.0)
    assert rig.r.state == "stopped" and rig.r.counters["fell"] == 1 and "FELL" in rig.text()
    n = len(rig.r.commands)
    rig.advance(5.0)
    assert len(rig.r.commands) == n
    rig.fake.fallen = False  # a person rights the duck ...
    rig.app_writes(dict(WALK_ZERO))  # ... and the app puts the brain back to the zero-command walk
    rig.advance(6.0)
    assert rig.r.state == "running"


def test_sit_stall_is_a_refusal_and_posture_stays_standing(tmp_path):
    rig = Rig(tmp_path, [answer(("sit", {}), ("rest", {"seconds": 8})), answer(("nod", {"times": 1}))]).started()
    rig.fake.stall = True
    rig.advance(6.0)
    assert rig.r.counters["refused"] == 1 and rig.r.world.posture == "standing"
    assert rig.cmds()[-1] == WALK_ZERO and rig.r.state == "running"
    assert "the brain refused sit" in rig.text()


def test_three_refusals_stop_the_runner(tmp_path):
    rig = Rig(tmp_path, [answer(("wait", {"seconds": 30}))]).started()
    for _ in range(3):
        rig.fake.say("torque refused: battery stop marker present")
        rig.advance(1.0)
    assert rig.r.state == "stopped" and "3 refusals" in rig.r.state_why


def test_guard_trip_line_stops_and_marks_the_brain_write(tmp_path):
    rig = Rig(tmp_path, [answer(("walk", {"vx": 0.2, "vtheta": 0, "seconds": 8}))]).started()
    rig.advance(1.0)
    rig.fake._write({"mode": "stand"}, "tilt 31.0 deg over 30")  # what walk_wired.py does on a trip
    rig.advance(1.0)
    assert rig.r.state == "stopped" and rig.r.counters["guard_trip"] == 1 and rig.r.counters["yield"] == 0


def test_allow_groups_filter_the_card():
    assert allowed_names("head") == {"turn_head", "look_around", "nod", "wait", "stop"}
    card = filtered_card(load_body_card("duck"), allowed_names("head,sit"))
    names = {p["name"] for p in card["primitives"]}
    assert names == {"turn_head", "look_around", "nod", "wait", "stop", "sit", "rest", "stand"}
    assert "walk" not in system_prompt(BodyCard(card), {})
    with pytest.raises(ValueError):
        allowed_names("legs")


def test_offline_fallback_session_runs_without_a_model(tmp_path):
    rig = Rig(tmp_path, None, events=[(5, {"kind": "touch", "where": "head"})]).started()
    rig.advance(60.0)
    s = rig.r.save()
    assert s["intentions"] >= 2 and s["sources"] == {"fallback": s["intentions"]}
    assert s["falls"] == 0 and s["brain_refusals"] == 0 and s["validator_rejections"] == 0
    assert s["commands_written"] >= 3 and (tmp_path / "out" / "commands.jsonl").exists()
    assert all(c["cmd"]["mode"] in ("walk", "sit", "groundpick") for c in rig.r.commands)


# ---------- perception ----------

def test_touch_detector_counts_presses_once():
    td = TouchDetector()
    rest = [24000.0, 24100.0, 23000.0, 23100.0, 25000.0]
    ev = []
    for i in range(20):
        ev += td.feed(rest, i * 0.1)
    assert ev == []
    for i in range(20, 26):
        ev += td.feed([24000.0 + 1500.0, 24100.0, 23000.0, 23100.0, 25000.0], i * 0.1)
    assert ev == [{"kind": "touch", "where": "left", "pads": ["L1"]}]
    for i in range(26, 32):
        ev += td.feed(rest, i * 0.1)
    for i in range(32, 38):
        ev += td.feed([24000.0, 24100.0, 23000.0, 23100.0, 25000.0 + 1500.0], i * 0.1)
    assert len(ev) == 2 and ev[1]["where"] == "head"


def test_sound_onset_and_face_adapter():
    so = SoundOnset()
    ev = []
    for i in range(30):
        ev += so.feed([-50.0, -50.0, -52.0, None], i * 0.1)
    assert ev == []
    ev += so.feed([-30.0, -30.0, -45.0, None], 3.0)
    assert ev and ev[0]["kind"] == "sound" and ev[0]["direction"] == 0.0
    assert so.feed([-30.0, -30.0, -45.0, None], 3.1) == []  # one onset, not one per frame

    seen = {"who": None}
    fa = FaceAdapter(lambda frame: [{"who": seen["who"], "x": 0.5}] if seen["who"] else [])
    seen["who"] = "owner"
    assert fa.feed_frame(None, 0.0) == []
    ev = fa.feed_frame(None, 0.5)
    assert ev == [{"kind": "face", "who": "owner", "direction": -0.6}]
    seen["who"] = None
    assert fa.feed_frame(None, 1.0) == [] and fa.tick(7.0) == [{"kind": "face_lost", "who": "owner"}]


def test_stand_from_a_seat_rearms_with_sit_then_walks():
    from pet.mind.executors import duck_commands
    step = {"primitive": "stand", "params": {}}
    assert duck_commands(step, "standing") == [(0, dict(WALK_ZERO))]
    cmds = duck_commands(step, "sitting")
    assert cmds[0] == (0, {"mode": "sit"}) and cmds[-1][1] == dict(WALK_ZERO) and cmds[-1][0] > 0
    assert all(c.get("mode") != "stand" for _, c in cmds)


def test_frame_recorder_matches_the_nearest_row(tmp_path):
    import base64
    from pet.mind.perception import FrameRecorder
    rec = FrameRecorder(tmp_path / "frames")
    jpg = base64.b64encode(b"\xff\xd8 not really a jpeg").decode()
    rec.feed_rows([{"t": T0, "q": [0.0] * 14, "head_cmd": [0, 0, 0, 0], "quat": [1, 0, 0, 0], "gb": [0, 0, -1],
                    "mode": "walk"}])
    rec.feed_jpeg(jpg, T0 + 0.05)          # waits: no row newer than the frame yet
    assert rec.saved == 0
    rec.feed_rows([{"t": T0 + 0.06, "q": [0.1] * 14, "head_cmd": [0.2, 0, 0, 0], "mode": "walk"}])
    assert rec.saved == 1 and rec.matched == 1
    rec.feed_jpeg(jpg, T0 + 5.0)           # no row near it: saved at close, unmatched
    rec.close()
    lines = [json.loads(x) for x in (tmp_path / "frames" / "frames.jsonl").read_text().splitlines()]
    assert lines[0]["q"] == [0.1] * 14 and lines[0]["head_cmd"] == [0.2, 0, 0, 0] and lines[0]["row_dt"] == 0.01
    assert "q" not in lines[1] and lines[1]["row_dt"] > 4
    assert (tmp_path / "frames" / lines[0]["img"]).read_bytes() == base64.b64decode(jpg)
