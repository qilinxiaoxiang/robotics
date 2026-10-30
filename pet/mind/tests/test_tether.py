"""Tether (charging cable) tests: odometry, the write guard, the turn-stall stop and the cable reflex, on FakeBrain."""
import json
import math

import pytest

from pet.mind.brain_link import WALK_ZERO
from pet.mind.tether import SPIN_MAX_DEG, Tether
from pet.mind.tests.test_runner import T0, Rig, answer


def quat(yaw):
    return [math.cos(yaw / 2), 0.0, 0.0, math.sin(yaw / 2)]


def rows(t0, seconds, yaw=0.0, vx=0.0, vtheta=0.0, dt=0.1):
    pol = "walk" if vx or vtheta else "stand"
    return [{"t": t0 + i * dt, "mode": "walk", "policy": pol, "quat": quat(yaw),
             "cmd": {"mode": "walk", "vx": vx, "vy": 0.0, "vtheta": vtheta}} for i in range(int(seconds / dt) + 1)]


def test_odometry_walks_at_the_measured_ground_speed():
    t = Tether(0.8)
    t.feed_rows(rows(T0, 4.0, vx=0.25))
    assert t.dist == pytest.approx(0.6, abs=0.02) and t.x > 0.55 and abs(t.y) < 1e-6
    t.feed_rows(rows(T0 + 4.1, 1.0, yaw=math.pi))   # turned round, standing: no travel
    assert t.dist == pytest.approx(0.6, abs=0.02) and abs(t.yaw_deg) == pytest.approx(180, abs=0.5)
    assert abs(t.bearing_to_start_deg()) < 1


def test_guard_refuses_walks_past_the_limit_but_not_back():
    t = Tether(0.8)
    t.feed_rows(rows(T0, 3.3, vx=0.25))             # about 0.5 m out, facing away
    ok, why = t.allow({"mode": "walk", "vx": 0.25, "vtheta": 0.0, "for_s": 4.0})
    assert not ok and "cable" in why and "room for 0.17 m" in why
    assert t.allow({"mode": "walk", "vx": 0.25, "vtheta": 0.0, "for_s": 1.5})[0]   # a short step still fits
    t.feed_rows(rows(T0 + 3.4, 0.5, yaw=math.pi))
    assert t.allow({"mode": "walk", "vx": 0.25, "vtheta": 0.0, "for_s": 4.0})[0]   # toward the start
    assert t.allow({"mode": "walk", "vx": 0.0, "vy": 0.0, "vtheta": 0.0})[0]


def test_guard_refuses_winding_the_cable_and_picks_the_unwinding_way():
    t = Tether(0.8)
    t.feed_rows(rows(T0, 0.2))
    t.feed_rows(rows(T0 + 0.3, 0.2, yaw=math.radians(170)))
    ok, why = t.allow({"mode": "walk", "vx": 0.0, "vtheta": 0.3, "for_s": 4.0})
    assert not ok and "wind" in why and abs(170 + 4 * 17) > SPIN_MAX_DEG
    assert t.allow({"mode": "walk", "vx": 0.0, "vtheta": -0.3, "for_s": 10.0})[0]
    t.x, t.y = -0.5, -0.2                          # start ahead-right of a duck facing 170 deg
    turn = t.turn_toward_start()
    assert abs(t.yaw_deg + turn) <= SPIN_MAX_DEG


class FakeVision:
    def __init__(self, cable):
        self.cable, self.calls = cable, 0

    def describe(self, jpeg, where, prompt):
        self.calls += 1
        return json.dumps({"cable_visible": True, "cable": self.cable, "pile_visible": False, "pile_xy": None,
                           "scene": "floor"}), {}


class TetherRig(Rig):
    def advance(self, seconds, dt=0.1):
        for _ in range(int(round(seconds / dt))):
            self.r.newest_frame = (self.clock.t, b"jpg", self.clock.t + dt)   # the camera keeps sending frames
            if self.r.scene is not None:
                self.r.scene.feed_frame(*self.r.newest_frame)
            super().advance(dt, dt)


def test_turn_into_a_wall_is_stopped_and_told_to_the_mind(tmp_path):
    rig = TetherRig(tmp_path, [answer(("walk", {"vx": 0.0, "vtheta": 0.3, "seconds": 8}))],
                    tether=Tether(0.8)).started()
    rig.fake.turn_blocked = True
    rig.advance(6.0)
    assert any(e["what"] == "turn_blocked" for e in rig.r.cable_log)
    assert "my turn to the left got stuck" in rig.text()
    assert rig.cmds()[-1] == WALK_ZERO and rig.r.state == "running"
    assert any("got stuck" in txt for _, txt in rig.r.world.recent_events)


def test_look_back_finds_a_taut_cable_and_walks_back(tmp_path):
    walk = answer(("walk", {"vx": 0.25, "vtheta": 0.0, "seconds": 4}))
    vision = FakeVision("pulled taut behind the robot")
    rig = TetherRig(tmp_path, [walk] * 6, tether=Tether(0.8), vision=vision).started()
    rig.advance(4.0)                                  # 0.39 m out: the reflex takes over and turns round
    assert rig.r.cable is not None and rig.r.cable["look"]
    rig.advance(40.0)
    t = rig.r.tether
    ev = [e["what"] for e in rig.r.cable_log]
    assert ev[:2] == ["start", "look"] and "end" in ev and vision.calls == 1
    assert t.cable == "taut" and t.limit_m < 0.8      # the taut look set the real limit
    assert t.max_dist_m < 0.8 - 0.15 + 0.05           # never past the limit
    assert t.dist < t.max_dist_m                      # it walked back
    assert any("looked back at my cable" in txt for _, txt in rig.r.world.recent_events)
    assert "Your situation:" in rig.r.mind.calls_text() if hasattr(rig.r.mind, "calls_text") else True


def test_without_vision_the_limit_still_holds(tmp_path):
    walk = answer(("walk", {"vx": 0.25, "vtheta": 0.0, "seconds": 4}))
    rig = TetherRig(tmp_path, [walk] * 8, tether=Tether(0.8)).started()
    rig.advance(60.0)
    t = rig.r.tether
    assert t.max_dist_m <= 0.8 - 0.15 + 0.03
    assert any(e["what"] in ("refused", "start") for e in rig.r.cable_log)
    assert rig.r.counters["falls"] == 0


def test_the_prompt_carries_the_cable_situation(tmp_path):
    rig = TetherRig(tmp_path, [answer(("wait", {"seconds": 3}))], tether=Tether(0.8)).started()
    ctx = rig.r.mind.context({})
    assert "charging cable" in ctx["situation"] and "from where your cable starts" in ctx["situation"]


class SceneVision:
    """Answers the scene prompt: a person only when the head looks left; a doorway when it looks right."""

    def __init__(self):
        self.calls = []

    def describe(self, jpeg, where, prompt):
        self.calls.append(where)
        if "to its left" in where:
            ans = {"person": True, "person_x": 0.2, "things": [{"name": "desk", "x": 0.5}], "blocked": False,
                   "summary": "a person on a chair at a desk"}
        elif "to its right" in where:
            ans = {"person": False, "person_x": None, "things": [{"name": "doorway", "x": 0.5}], "blocked": False,
                   "summary": "an open doorway"}
        else:
            ans = {"person": False, "person_x": None, "things": [], "blocked": False, "summary": "bare floor"}
        return json.dumps(ans), {}


def test_sees_the_owner_remembers_the_direction_and_turns_to_walk_there(tmp_path):
    from pet.mind.glance import bearing_in_frame
    vision = SceneVision()
    rig = TetherRig(tmp_path, [answer(("approach_owner", {"seconds": 3}))], tether=Tether(3.0), vision=vision,
                    see=True).started()
    for _ in range(200):                                # the startup look finds the person on the left
        rig.advance(0.1)
        if rig.r.scene.person is not None:
            break
    owner_world = 1.2 * 57.2958 + bearing_in_frame(0.2)  # head yaw + where the person sits in the picture
    assert rig.r.scene.person[0] == pytest.approx(owner_world, abs=3)
    ctx = rig.r.mind.context({})
    assert "my owner (a person) 9" in ctx["situation"] and "deg to your left, seen" in ctx["situation"]
    assert rig.r.world.owner_visible
    for _ in range(300):                                # the model's approach_owner: turn on the spot, then walk
        rig.advance(0.1)
        if rig.r.turn_then and rig.r.turn_then["phase"] == "walk":
            break
    assert rig.r.tether.yaw_deg == pytest.approx(rig.r.scene.person[0], abs=10)
    assert "my owner (a person) ahead" in rig.r.mind.context({})["situation"]
    rig.advance(3.5)
    walks = [c for c in rig.cmds() if c.get("vx")]
    assert walks and walks[0]["vx"] == 0.25 and walks[0]["vtheta"] == 0.0
    assert rig.r.tether.walked_m > 0.3
    assert "toward where the owner was seen" in rig.text()
