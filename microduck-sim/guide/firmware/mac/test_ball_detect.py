"""ball_detect: a colour candidate is acted on only once the learned detector has confirmed it; then it is tracked."""
import ball_detect as bd


def make(colour_hits, learned_hits):
    clock = {"t": 0.0}
    calls = {"learned": 0}

    def colour(frame, lo, hi, min_area, accept=None):
        return colour_hits.get(frame)

    def learned(frame, accept=None):
        calls["learned"] += 1
        return learned_hits.get(frame)

    return bd.BallDetect((0, 0, 0), (1, 1, 1), 60, now=lambda: clock["t"], learned=learned, colour=colour,
                         threaded=False), clock, calls


def test_the_robots_own_foot_is_never_returned():
    foot = dict(cx=100.0, cy=300.0, bbox=(60, 280, 80, 40))
    d, clock, calls = make({"foot": foot}, {})
    for i in range(30):
        clock["t"] = i * 0.1
        assert d("foot") is None
    assert d.pending and d.stats["rejected"] == 30   # the candidate stays unconfirmed however often it is ruled on


def test_a_confirmed_ball_is_tracked_at_camera_rate():
    ball = dict(cx=300.0, cy=100.0, bbox=(290, 90, 20, 20))
    d, clock, calls = make({"a": ball, "b": dict(ball, cx=330.0)}, {"a": dict(ball, score=0.8)})
    assert d("a") is not None and calls["learned"] == 1
    for i in range(1, 20):
        clock["t"] = i * 0.1
        assert d("b")["cx"] == 330.0
    assert calls["learned"] == 1


def test_a_far_ball_the_colour_filter_misses_is_found():
    d, clock, calls = make({}, {"far": dict(cx=500.0, cy=30.0, bbox=(494, 24, 13, 14), score=0.7)})
    assert d("far")["bbox"] == (494, 24, 13, 14)


def test_a_colour_box_far_from_the_track_needs_a_new_confirmation():
    ball = dict(cx=300.0, cy=100.0, bbox=(290, 90, 20, 20))
    foot = dict(cx=100.0, cy=300.0, bbox=(60, 280, 80, 40))
    d, clock, calls = make({"a": ball, "foot": foot}, {"a": ball})
    assert d("a") is not None
    clock["t"] = 0.1
    assert d("foot") is None and calls["learned"] == 2   # far from the track: ruled on again, and rejected


def test_the_caller_is_never_held_up_by_a_learned_pass():
    """Robot 2026-11-12 (seepick_1112m): the pass ran inside the 50 Hz loop, a turn's walk command ran out during
    every pass and the ball seen in a scan was never faced."""
    import time
    ball = dict(cx=300.0, cy=100.0, bbox=(290, 90, 20, 20))

    def slow(frame, accept=None):
        time.sleep(0.3)
        return dict(ball, score=0.8) if frame == "ball" else None

    d = bd.BallDetect((0, 0, 0), (1, 1, 1), 60, learned=slow, colour=lambda f, lo, hi, a, accept=None: None)
    t0, got, worst = time.time(), None, 0.0
    while got is None and time.time() - t0 < 3.0:
        t = time.time()
        got = d("ball", ctx="state of that frame")
        worst = max(worst, time.time() - t)
        time.sleep(0.02)
    assert worst < 0.05
    assert got is not None and got["ctx"] == "state of that frame" and got["bbox"] == ball["bbox"]


def test_a_background_box_is_not_handed_to_a_moving_robot_but_confirms_the_colour_box():
    import time
    ball = dict(cx=300.0, cy=100.0, bbox=(290, 90, 20, 20))
    d = bd.BallDetect((0, 0, 0), (1, 1, 1), 60, learned=lambda f, accept=None: dict(ball, score=0.8),
                      colour=lambda f, lo, hi, a, accept=None: ball if f == "seen" else None)
    assert d("far", late_ok=False) is None
    time.sleep(0.2)
    assert d("far", late_ok=False) is None        # the pass has finished: its box is old, the robot is moving
    assert d("seen", late_ok=False)["cx"] == 300.0   # the colour box next to it is from this frame: tracked at once
