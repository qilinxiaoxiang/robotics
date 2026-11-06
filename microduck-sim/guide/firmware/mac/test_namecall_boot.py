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


SYSTEMD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pi", "systemd")


def unit_ordering(texts):
    """name -> set of units it starts after, with systemd's implicit target edges.

    A target adds After= on every unit it Wants unless that unit already orders itself after the target
    (systemd unit_add_default_target_dependency); that implicit edge is how a boot cycle can appear.
    """
    after, wanted_by = {}, {}
    for name, text in texts.items():
        keys = {}
        for line in text.splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                keys.setdefault(k.strip(), []).extend(v.split())
        after[name] = set(keys.get("After", []))
        wanted_by[name] = set(keys.get("WantedBy", []))
    for name in texts:
        for target in wanted_by[name]:
            if target not in after[name]:
                after.setdefault(target, set()).add(name)
    return after


def boot_cycle(after):
    """First ordering cycle found, as a list of units, or None."""
    state = {}

    def visit(u, path):
        state[u] = 1
        for v in after.get(u, ()):
            if state.get(v) == 1:
                return path + [u, v]
            if v not in state:
                found = visit(v, path + [u])
                if found:
                    return found
        state[u] = 2
        return None

    for u in list(after):
        if u not in state:
            found = visit(u, [])
            if found:
                return found
    return None


def systemd_units():
    return {n: open(os.path.join(SYSTEMD, n)).read() for n in os.listdir(SYSTEMD) if n.endswith(".service")}


def test_boot_units_have_no_ordering_cycle():
    assert boot_cycle(unit_ordering(systemd_units())) is None


def test_the_1104_namecall_unit_is_caught():
    # The 2026-11-04 unit: systemd dropped duck-namecall at boot ("Job duck-namecall.service/start deleted to
    # break ordering cycle starting with multi-user.target/start", reproduced in a VM 2026-11-06).
    units = systemd_units()
    units["duck-namecall.service"] = ("[Unit]\nAfter=duck-camera.service duck-selfcheck.service sound.target\n"
                                      "[Install]\nWantedBy=multi-user.target\n")
    assert "duck-namecall.service" in boot_cycle(unit_ordering(units))
