"""namecall.py off the robot: head path (take -> walk_brain head command), control-file writer, brain gate, lock probe,
and the whole sound-to-command chain on a synthetic 4-channel scene.

  pet/.venv/bin/python -m pytest microduck-sim/guide/firmware/mac/test_namecall_chain.py -q
"""
import fcntl
import json
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import namecall as nc  # noqa: E402
from pet.express.duck import HEAD_JOINTS, HEAD_RANGE, ema  # noqa: E402

FS, B = nc.FS, nc.BLOCK


def args(**kw):
    base = dict(threshold_db=12.0, rise_db=6.0, refractory=2.5, floor_tau=3.0, swap_ears=False, no_head=False, seed=3,
                smooth=False, idle=False, no_sound=True, bank_dir="/tmp/namecall_test_bank", sounds=None, mute=True,
                cmd="/tmp/namecall_test_cmd.json", dry=False, no_gate=True, brain_logs="/nonexistent/*.jsonl", pitch=0.2,
                once=0, default_head_file=None)
    base.update(kw)
    return type("A", (), base)()


# --- head path

def test_take_runs_under_head_range_and_lands_near_the_caller():
    hp = nc.HeadPath(seed=1, default=dict(nc.DEFAULT_HEAD))
    perf = hp.start(0.0, 0.8, 0.2)
    assert perf.take in ("quick_snap", "curious_turn", "double_take", "groggy", "glance")
    rows, events = [], []
    t = 0.0
    while True:
        head, ev, active = hp.tick(t)
        events += ev
        if head is None:
            break
        rows.append([head[j] - nc.DEFAULT_HEAD[j] for j in HEAD_JOINTS])
        t += 0.02
        if not active:
            break
    r = np.array(rows)
    assert len(r) > 50 and (np.abs(r) <= np.asarray(HEAD_RANGE) + 1e-9).all()      # trained head command range
    c = ema(r)                                                                     # what walk_brain's EMA produces
    k = int(round((perf.arrival or 1.0) / 0.02))
    assert abs(c[min(k + 10, len(c) - 1), 2] - 0.8) < 0.25 or np.abs(c[:, 2] - 0.8).min() < 0.15   # yaw reached the caller
    assert abs(c[-1, 2]) < 0.3 and (r[-1] == 0).all()        # content_idle drifted home and the last command is the default
    calls = [e for e in events if e.get("kind") == "call"]
    if calls:
        assert all(0.7 < e["pitch"] < 1.4 for e in calls)
        assert calls[0]["t_abs"] >= (perf.arrival or 0) * 0.5


def test_calls_from_behind_turn_as_far_as_the_cap():
    hp = nc.HeadPath(seed=2, default=dict(nc.DEFAULT_HEAD))
    hp.start(0.0, math.radians(150), 0.2)
    assert hp.last["behind"] and abs(hp.last["yaw"] - nc.YAW_CAP) < 1e-9
    hp2 = nc.HeadPath(seed=2, default=dict(nc.DEFAULT_HEAD))
    hp2.start(0.0, math.radians(-150), 0.2)
    assert abs(hp2.last["yaw"] + nc.YAW_CAP) < 1e-9


def test_no_repeat_take_and_smooth_mode_never_exceeds_the_take():
    hp = nc.HeadPath(seed=5, default=dict(nc.DEFAULT_HEAD), preinverse=False)
    takes = []
    t = 0.0
    for i in range(6):
        perf = hp.start(t, 0.7 * (1 if i % 2 == 0 else -1), 0.2)
        takes.append(perf.take)
        t_end = hp.active_until
        peak = 0.0
        while t < t_end:
            head, _, _ = hp.tick(t)
            if head is not None:
                peak = max(peak, abs(head["head_yaw"]))
            t += 0.02
        assert peak <= 1.4 + 1e-6
        t += 1.0
    assert all(a != b for a, b in zip(takes, takes[1:]))


def test_want_head_is_absolute_model_rad():
    hp = nc.HeadPath(seed=1, default={"neck_pitch": 0.349, "head_pitch": 0.349, "head_yaw": 0.0, "head_roll": 0.0})
    hp.start(0.0, 0.5, 0.2)
    head, _, _ = hp.tick(1.0)
    assert set(head) == set(HEAD_JOINTS)
    assert abs(head["head_pitch"] - 0.349) < 1.2 and abs(head["head_yaw"]) < 1.41


# --- control file

def test_writer_writes_zero_walk_and_yields_to_other_writers(tmp_path):
    p = str(tmp_path / "cmd.json")
    w = nc.CmdWriter(p)
    assert w.write({"head_yaw": 0.3})
    cmd = json.load(open(p))
    assert cmd["mode"] == "walk" and cmd["vx"] == 0 and cmd["vy"] == 0 and cmd["vtheta"] == 0
    assert cmd["head"] == {"head_yaw": 0.3}
    assert w.write({"head_yaw": 0.4})                       # its own last command: fine
    json.dump({"mode": "walk", "vx": 0.25, "vy": 0, "vtheta": 0}, open(p, "w"))
    assert not w.write({"head_yaw": 0.5})                   # someone started a walk: yield
    assert json.load(open(p))["vx"] == 0.25
    json.dump({"mode": "walk", "vx": 0, "vy": 0, "vtheta": 0, "quack": 3}, open(p, "w"))
    assert not w.write({"head_yaw": 0.5})                   # a quack from the app: not ours to overwrite
    json.dump({"mode": "walk", "vx": 0, "vy": 0, "vtheta": 0}, open(p, "w"))
    assert w.write({"head_yaw": 0.5})                       # a plain zero walk: claimable
    json.dump({"mode": "off"}, open(p, "w"))
    assert not w.write(None)


# --- brain gate

def brain_log(path, mode, cmd, age=0.0):
    row = dict(t=time.time() - age, mode=mode, cmd=cmd, torque=True, q=[0] * 14)
    with open(path, "a") as f:
        f.write(json.dumps(row) + "\n")


def test_gate_accepts_walk_zero_and_stand_only(tmp_path):
    log = str(tmp_path / "duck_wired_log_x.jsonl")
    g = nc.BrainGate(str(tmp_path / "duck_wired_log_*.jsonl"), str(tmp_path / "cmd.json"))
    assert not g.state()["ok"] and "no brain tick log" in g.state()["why"]
    brain_log(log, "monitor", {"mode": "monitor"})
    assert not g.state()["ok"] and "monitor" in g.state()["why"]
    brain_log(log, "walk", {"mode": "walk", "vx": 0.25, "vy": 0, "vtheta": 0})
    assert not g.state()["ok"] and "walking" in g.state()["why"]
    brain_log(log, "walk", {"mode": "walk", "vx": 0, "vy": 0, "vtheta": 0})
    assert g.state()["ok"] and g.state()["mode"] == "walk"
    brain_log(log, "stand", {"mode": "stand"})
    assert g.state()["ok"] and g.state()["mode"] == "stand"
    brain_log(log, "sit", {"mode": "sit"})
    assert not g.state()["ok"]
    brain_log(log, "walk", {"mode": "walk", "vx": 0, "vy": 0, "vtheta": 0}, age=3.0)
    assert not g.state()["ok"] and "stale" in g.state()["why"]
    # a torn last line is skipped, the previous complete one counts
    brain_log(log, "walk", {"mode": "walk", "vx": 0, "vy": 0, "vtheta": 0})
    with open(log, "a") as f:
        f.write('{"t": 1, "mode": "wal')
    assert g.state()["ok"]


def test_gate_follows_the_newest_log(tmp_path):
    a, b = str(tmp_path / "duck_wired_log_a.jsonl"), str(tmp_path / "duck_wired_log_b.jsonl")
    brain_log(a, "walk", {"mode": "walk", "vx": 0, "vy": 0, "vtheta": 0})
    g = nc.BrainGate(str(tmp_path / "duck_wired_log_*.jsonl"))
    assert g.state()["ok"]
    time.sleep(0.02)
    brain_log(b, "monitor", {"mode": "monitor"})
    os.utime(b, None)
    assert not g.state()["ok"] and g.state()["log"] == b


def test_lock_probe_sees_a_holder_and_never_keeps_the_lock(tmp_path):
    p = str(tmp_path / "duck-hw.lock")
    assert nc.lock_free(p)
    assert nc.lock_free(p)                      # the probe released it
    f = open(p, "a")
    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    assert not nc.lock_free(p)                  # a brain holds it
    fcntl.flock(f, fcntl.LOCK_UN)
    assert nc.lock_free(p)


# --- the chain on a synthetic scene

def scene(calls, dur, seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * FS)
    sig = nc.synth_call(seed=seed)
    rms = float(np.sqrt(np.mean(sig ** 2)))
    x = rng.standard_normal((n, 4)).astype(np.float32) * rms * 10 ** (-20 / 20)
    x[:, 3] = 0
    for t, az in calls:
        y, _ = nc.render_scene(sig, math.radians(az), pre_s=0.0, post_s=0.0, snr_db=200, seed=seed)
        i = int(t * FS)
        x[i:i + len(y)] += y[: n - i]
    return x


def blocks(x):
    for i in range(0, len(x) - B + 1, B):
        yield i / FS, x[i:i + B]


def test_chain_sound_to_commands(tmp_path):
    cmd = str(tmp_path / "cmd.json")
    a = args(cmd=cmd, log=None)
    log = nc.Log(str(tmp_path / "nc.jsonl"), echo=False)
    n = nc.NameCall(a, log, now=lambda: 0.0)
    n.head.default = dict(nc.DEFAULT_HEAD)
    rows = []
    dets = n.run_blocks(blocks(scene([(1.5, 60), (6.0, -45)], 10.0)), head_rows=rows)
    assert [round(d["t"], 1) for d in dets] == [1.5, 6.0]
    assert abs(dets[0]["az_deg"] - 60) < 4 and abs(dets[1]["az_deg"] + 45) < 4
    assert dets[0]["decided_t"] - dets[0]["t"] < 0.1           # direction known within 100 ms of the onset
    assert dets[0]["take"] != dets[1]["take"]
    assert all(abs(h["head_yaw"]) <= 1.4 + 1e-6 for _, h, _ in rows)
    first = [(t, h) for t, h, _ in rows if 1.5 <= t < 6.0]
    assert first and max(h["head_yaw"] for _, h in first) > 0.5          # turned left toward +60
    second = [(t, h) for t, h, _ in rows if t >= 6.0]
    assert second and min(h["head_yaw"] for _, h in second) < -0.4         # then right toward -45
    assert json.load(open(cmd))["mode"] == "walk"
    kinds = [json.loads(l)["kind"] for l in open(str(tmp_path / "nc.jsonl"))]
    assert kinds.count("call") == 2
    assert n.writer.writes > 100


def test_chain_no_head_mode_writes_nothing(tmp_path):
    cmd = str(tmp_path / "cmd.json")
    n = nc.NameCall(args(cmd=cmd, no_head=True), nc.Log(None, echo=False), now=lambda: 0.0)
    dets = n.run_blocks(blocks(scene([(1.0, -90)], 4.0)))
    assert len(dets) == 1 and abs(dets[0]["az_deg"] + 90) < 4
    assert not os.path.exists(cmd)


def test_wav_replay_through_main(tmp_path):
    import wave
    x = scene([(1.0, 30)], 3.0)
    p = str(tmp_path / "scene.wav")
    with wave.open(p, "w") as w:
        w.setnchannels(4), w.setsampwidth(4), w.setframerate(FS)
        w.writeframes((np.clip(x, -1, 1) * (2 ** 23 - 1)).astype("<i4").__lshift__(8).astype("<i4").tobytes())
    log = str(tmp_path / "log.jsonl")
    assert nc.main(["--wav", p, "--no-head", "--log", log, "--quiet"]) == 0
    rows = [json.loads(l) for l in open(log)]
    calls = [r for r in rows if r["kind"] == "call"]
    assert len(calls) == 1 and abs(calls[0]["az_deg"] - 30) < 4
