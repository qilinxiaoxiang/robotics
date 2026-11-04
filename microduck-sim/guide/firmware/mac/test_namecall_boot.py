import json
import os
import signal
import subprocess
import time

import namecall_boot as nb


def write(tmp_path, **row):
    p = tmp_path / "duck_wired_log_a.jsonl"
    row.setdefault("t", time.time())
    p.write_text("x" * 20000 + "\n" + json.dumps(row) + "\n")
    return str(tmp_path)


def test_ready_only_at_rest_on_a_fresh_log(tmp_path):
    logs = write(tmp_path, mode="walk", cmd=dict(vx=0.0, vy=0.0, vtheta=0.0))
    assert nb.brain_ready(logs=logs)
    assert not nb.brain_ready(now=time.time() + 5, logs=logs)
    for mode in ("monitor", "stand", "stop"):
        assert not nb.brain_ready(logs=write(tmp_path, mode=mode, cmd={}))
    assert not nb.brain_ready(logs=write(tmp_path, mode="walk", cmd=dict(vx=0.2)))
    assert not nb.brain_ready(logs=write(tmp_path, mode="walk", cmd=dict(vtheta=-0.1)))
    assert nb.brain_ready(logs=write(tmp_path, mode="sit", sit_phase="seated"))
    for phase in ("sitting", "rising", None):
        assert not nb.brain_ready(logs=write(tmp_path, mode="sit", sit_phase=phase))


def test_no_old_or_broken_brain_log_is_not_ready(tmp_path):
    assert not nb.brain_ready(logs=str(tmp_path))
    assert not nb.brain_ready(logs=write(tmp_path, mode="walk", t=time.time() - 10))
    p = tmp_path / "duck_wired_log_a.jsonl"
    for content in ("", "broken\n", "{}\n", "[]\n", "null\n"):
        p.write_text(content)
        assert not nb.brain_ready(logs=str(tmp_path))


class Child:
    def __init__(self, pid):
        self.pid = pid
        self.rc = None

    def poll(self):
        return self.rc


def harness():
    events, children = [], []

    def start(args, **kw):
        assert kw["start_new_session"] is True
        child = Child(100 + len(children))
        children.append(child)
        events.append(("start", child.pid, "--audio-only" in args))
        return child

    def stop(child):
        events.append(("stop", child.pid))
        child.rc = -15

    return nb.Supervisor(start, stop, lambda **kw: None), events, children


def test_boot_audio_to_head_and_back_stops_old_capture_first():
    s, events, children = harness()
    s.tick(nb.desired_mode(False, False), 0)
    assert events == [("start", 100, True)]
    s.tick("audio-only", 1)
    assert len(children) == 1
    s.tick(nb.desired_mode(True, False), 2)
    assert events[-2:] == [("stop", 100), ("start", 101, False)]
    s.tick(nb.desired_mode(False, False), 4)
    assert events[-2:] == [("stop", 101), ("start", 102, True)]
    s.close()
    assert events[-1] == ("stop", 102)
    assert s.child is None


def test_selfcheck_owns_audio_until_it_finishes():
    s, events, children = harness()
    s.tick(nb.desired_mode(False, True), 0)
    assert events == []
    s.tick(nb.desired_mode(False, False), 2)
    s.tick(nb.desired_mode(True, True), 4)
    assert events[-1] == ("stop", 100)
    assert s.child is None
    s.tick(nb.desired_mode(True, False), 6)
    assert events[-1] == ("start", 101, False)


def test_crashed_child_cleanup_and_bounded_restart_backoff():
    s, events, children = harness()
    s.tick("audio-only", 0)
    for failed_at, restart_at in ((1, 6), (7, 12), (13, 73)):
        children[-1].rc = 1
        s.tick("audio-only", failed_at)
        assert s.child is None
        assert events[-1][0] == "stop"
        s.tick("audio-only", restart_at - 0.1)
        assert s.child is None
        s.tick("audio-only", restart_at)
        assert s.child is not None


def test_group_cleanup_even_when_parent_exited():
    class Proc:
        pid = 123

        def wait(self, timeout=None):
            return 0

    signals = []
    nb.stop_child(Proc(), lambda pid, sig: signals.append((pid, sig)))
    assert signals == [(123, signal.SIGTERM), (123, signal.SIGKILL)]


def test_group_cleanup_escalates_if_process_does_not_exit():
    class Proc:
        pid = 456

        def wait(self, timeout=None):
            if timeout is not None:
                raise subprocess.TimeoutExpired("namecall", timeout)
            return -9

    signals = []
    nb.stop_child(Proc(), lambda pid, sig: signals.append((pid, sig)))
    assert signals[-1] == (456, signal.SIGKILL)
