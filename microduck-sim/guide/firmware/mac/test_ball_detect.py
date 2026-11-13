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

    return bd.BallDetect((0, 0, 0), (1, 1, 1), 60, now=lambda: clock["t"], learned=learned, colour=colour), clock, calls


def test_the_robots_own_foot_is_never_returned():
    foot = dict(cx=100.0, cy=300.0, bbox=(60, 280, 80, 40))
    d, clock, calls = make({"foot": foot}, {})
    for i in range(30):
        clock["t"] = i * 0.1
        assert d("foot") is None
    assert 2 <= calls["learned"] <= 4   # about one learned pass a second, not one per frame


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
    assert d("foot") is None   # inside the learned detector's rate limit: not confirmed, so not returned
    clock["t"] = 1.2
    assert d("foot") is None and calls["learned"] == 2
