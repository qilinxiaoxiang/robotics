"""t2pick's box feed and walk_brain's picture slots on a fake camera and brain.

    python3 -m pytest -q test_t2pick.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import t2pick  # noqa: E402
import walk_brain  # noqa: E402


def det(x, y, w=20, h=20):
    return {"bbox": (x, y, w, h)}


def feed_of(seq):
    it = iter(seq)
    return t2pick.PixFeed(lambda f: next(it))


def test_blank_frame_keeps_the_box_and_its_capture_time():
    feed = feed_of([det(100, 100), None])
    assert feed.update(None, 10.0) == {"u": 110.0, "v": 110.0, "w": 20.0, "t": 10.0, "seen": True}
    assert feed.update(None, 10.1) == {"u": 110.0, "v": 110.0, "w": 20.0, "t": 10.0, "seen": False}


def test_far_blob_is_rejected_as_another_object():
    feed = feed_of([det(100, 100), det(500, 300)])
    feed.update(None, 10.0)
    obj = feed.update(None, 10.1)
    assert obj["u"] == 110.0 and obj["t"] == 10.0 and obj["seen"] is False and feed.rejected == 1


def test_slots_match_training_normalisation_and_aging():
    assert walk_brain.is_pix_object({"u": 1, "v": 2, "w": 3, "t": 4, "seen": True})
    assert not walk_brain.is_pix_object({"x": 0.1, "y": 0.0, "size": 0.01, "t": 4})
    obj = {"u": 480.0, "v": 90.0, "w": 64.0, "t": 10.0, "seen": False}
    out = walk_brain.seepickpix_body(np.zeros(6, dtype=np.float32), obj, True, 10.5)
    assert np.allclose(out, [0.5, -0.5, 0.1, 0.5, 1.0, 0.0])


class Clock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s


class Cam:
    def __init__(self, clock):
        self.clock = clock

    def latest(self):
        return None, self.clock.t, int(self.clock.t * 10)


class Tail:
    def __init__(self, clock, modes):
        self.clock, self.modes = clock, modes

    def latest(self):
        for until, mode in self.modes:
            if self.clock.t < until:
                return {"mode": mode, "sp_phase": self.clock.t / 4.0 if mode == "seepick" else None}
        return {"mode": self.modes[-1][1]}


def run(modes, timeout=6.0, current=None, keep=lambda: True):
    clock, sent = Clock(), []
    feed = t2pick.PixFeed(lambda f: det(300, 170))
    feed.update(None, -0.1)
    current = current or (lambda: sent[-1])
    rows, why = t2pick.run_pick(feed, Cam(clock), Tail(clock, modes), sent.append, current, keep, now=clock.now,
                                sleep=clock.sleep, timeout=timeout)
    return rows, why, sent, clock


def test_feeds_until_the_hand_back_and_never_writes_another_mode():
    rows, why, sent, _ = run([(0.1, "walk"), (4.0, "seepick"), (99.0, "walk")])
    assert why == "brain left seepick for walk"
    assert all(c["mode"] == "seepick" for c in sent)
    assert len(sent) > 20 and rows


def test_stops_writing_when_the_brain_refused_the_switch():
    rows, why, sent, _ = run([(99.0, "walk")], timeout=1.0)
    assert "never entered" in why
    assert len(sent) == 1


def test_no_rewrite_around_the_hand_back():
    times = []
    clock_box = {}

    class Rec(list):
        def append(self, c):
            times.append(clock_box["c"].t)

    clock = Clock()
    clock_box["c"] = clock
    feed = t2pick.PixFeed(lambda f: det(300, 170))
    feed.update(None, -0.1)
    t2pick.run_pick(feed, Cam(clock), Tail(clock, [(0.1, "walk"), (4.0, "seepick"), (99.0, "walk")]), Rec().append,
                    lambda: {"mode": "seepick"}, lambda: True, now=clock.now, sleep=clock.sleep, timeout=6.0)
    assert max(times) <= 0.85 * 4.0 + 0.11


def test_a_command_from_the_brain_is_never_overwritten():
    rows, why, sent, _ = run([(99.0, "seepick")], current=lambda: {"mode": "monitor"})
    assert "stopped writing" in why and len(sent) == 1


def test_a_stop_on_the_page_ends_the_feed():
    calls = []

    def keep():
        calls.append(1)
        return len(calls) < 50
    rows, why, sent, _ = run([(99.0, "seepick")], keep=keep)
    assert "took over" in why


def test_lease_refuses_a_live_holder_and_takes_an_idle_one(tmp_path):
    t = [100.0]
    cmd = str(tmp_path / "c.json")
    (tmp_path / "c.json.driver").write_text('{"id": "page", "name": "遥控页", "last": 95.0}')
    lease = t2pick.Lease(cmd, clock=lambda: t[0])
    assert lease.take() == "遥控页"
    t[0] = 116.0
    assert lease.take() is None and lease.keep()
    (tmp_path / "c.json.driver").write_text('{"id": "page", "name": "遥控页", "last": 116.0}')
    assert not lease.keep()
