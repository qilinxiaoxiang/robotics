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


def test_response_looks_up_to_a_standing_face():
    """The default gaze pitch sends head_pitch to its look-up cap (negative = up on this robot, approach.py;
    face-view-20261029: -0.75 absolute puts a standing face in frame from 1-2 m). The first robot name-call of
    2026-10-30 pitched the head DOWN (card signs inverted)."""
    for seed in range(4):
        hp = nc.HeadPath(seed=seed, default=dict(nc.DEFAULT_HEAD))
        perf = hp.start(0.0, 0.5)
        rows, t = [], 0.0
        while True:
            head, ev, active = hp.tick(t)
            if head is None:
                break
            rows.append([head[j] - nc.DEFAULT_HEAD[j] for j in HEAD_JOINTS])
            t += 0.02
            if not active:
                break
        c = ema(np.array(rows))
        k = int(round((perf.arrival or 1.0) / 0.02))
        at_arrival = c[min(k + 10, len(c) - 1)]
        assert at_arrival[1] < -0.7, (perf.take, at_arrival)       # head_pitch well up (cap -1.10)
        assert (c[:, 1] > 0.1).sum() == 0, perf.take                 # never a look DOWN on the way
        assert at_arrival[0] >= -0.05, (perf.take, at_arrival)      # the neck does not drop the head


def test_playback_keepalive_starts_before_capture_and_stops():
    import subprocess as sp
    started = []

    class Fake:
        def __init__(self, cmd, **kw):
            started.append(cmd)
            self.killed = False
            self.returncode = None
            self.stderr = sp.PIPE

        def poll(self):
            return 0 if self.killed else None

        def kill(self):
            self.killed = True
            self.returncode = -9

        def wait(self, timeout=None):
            return self.returncode

    ka = nc.PlaybackKeepAlive(popen=Fake).start(settle_s=0.0)
    assert ka.alive and started == [list(nc.KEEPALIVE_CMD)]
    assert started[0][0] == "aplay" and "/dev/zero" in started[0] and "-D" not in started[0]   # the ALSA default (dmix + softvol)
    ka.stop()
    assert not ka.alive

    def failing(cmd, **kw):
        raise FileNotFoundError("aplay")

    kb = nc.PlaybackKeepAlive(popen=failing).start(settle_s=0.0)
    assert not kb.alive and "aplay" in kb.err     # the program goes on without it


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

def scene(calls, dur, seed=0, el=35.0):
    """White noise at 20 dB SNR with calls from the given azimuths, the caller standing (elevation el, the call
    localiser's default prior)."""
    rng = np.random.default_rng(seed)
    n = int(dur * FS)
    sig = nc.synth_call(seed=seed)
    rms = float(np.sqrt(np.mean(sig ** 2)))
    x = rng.standard_normal((n, 4)).astype(np.float32) * rms * 10 ** (-20 / 20)
    x[:, 3] = 0
    for t, az in calls:
        y, _ = nc.render_scene(sig, math.radians(az), pre_s=0.0, post_s=0.0, snr_db=200, seed=seed, el_rad=math.radians(el))
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
    # the scene renders bearings in the resting head frame, so the second call waits until the attention phase
    # (ATTEND_S after the first) has let the head drift home; a call during the hold is heard in the turned frame
    dets = n.run_blocks(blocks(scene([(1.5, 60), (15.5, -45)], 19.0)), head_rows=rows)
    assert [round(d["t"], 1) for d in dets] == [1.5, 15.5]
    assert abs(dets[0]["az_deg"] - 60) < 4 and abs(dets[1]["az_deg"] + 45) < 4
    assert dets[0]["decided_t"] - dets[0]["t"] < nc.CALL_WINDOW_S + 0.1    # the call localiser hears the whole call first
    assert dets[0]["el_deg"] == 35.0 and dets[0]["bins"] > 50
    assert dets[0]["take"] != dets[1]["take"]
    assert all(abs(h["head_yaw"]) <= 1.4 + 1e-6 for _, h, _ in rows)
    first = [(t, h) for t, h, _ in rows if 1.5 <= t < 15.5]
    assert first and max(h["head_yaw"] for _, h in first) > 0.5          # turned left toward +60
    held = [h["head_yaw"] for t, h, _ in rows if 5.0 <= t < 11.0]
    assert held and min(held) > 0.7                                         # and stayed there through the attention
    second = [(t, h) for t, h, _ in rows if t >= 15.5]
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


def test_short_localiser_and_energy_detector_decide_at_the_onset(tmp_path):
    """--localiser short --detector energy: the 64 ms GCC at the onset (the sim evidence of NAMECALL.md 1-5)."""
    cmd = str(tmp_path / "cmd.json")
    n = nc.NameCall(args(cmd=cmd, no_head=True, localiser="short", detector="energy"), nc.Log(None, echo=False), now=lambda: 0.0)
    assert isinstance(n.loc, nc.Localiser) and isinstance(n.det, nc.OnsetDetector)
    dets = n.run_blocks(blocks(scene([(1.0, 40)], 4.0, el=0.0)))
    assert len(dets) == 1 and abs(dets[0]["az_deg"] - 40) < 4
    assert dets[0]["decided_t"] - dets[0]["t"] < 0.1


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


def test_turn_plan_only_for_callers_beyond_the_head():
    assert nc.NameCall.plan_turn(0.2) is None                         # the head shows it
    p = nc.NameCall.plan_turn(2.09)                                   # 120 deg behind-left (robot 2026-10-30)
    assert p["sign"] == 1.0 and 9.5 < p["dur_s"] < 11.5
    assert nc.NameCall.plan_turn(-3.0)["sign"] == -1.0 and nc.NameCall.plan_turn(-3.0)["dur_s"] <= nc.TURN_S[1]
    assert nc.NameCall.plan_turn(0.4)["dur_s"] == nc.TURN_S[0]


def test_every_response_quacks_and_a_caller_behind_gets_a_body_turn(tmp_path):
    """The take library drops the call on habituated or glancing takes (vocal_events); namecall adds its own, and a
    caller heard behind gets the front-half search first (no camera here, so it is spent after FACE_WAIT_S), then the
    body turns toward the back on that side, the head tracking the caller in the turning frame (Shawn 2026-10-30:
    turn head and body together, not head, centre, then body)."""
    cmd = str(tmp_path / "cmd.json")
    a = args(cmd=cmd, no_sound=False, mute=True, seed=5, pitch=nc.LOOK_PITCH)
    a.no_turn = False
    n = nc.NameCall(a, nc.Log(None, echo=False))
    quacks, turns, writes = [], [], []
    n.log.write = lambda kind, **rec: (quacks.append(rec) if kind == "quack" else turns.append(dict(rec, kind=kind)) if kind in ("turn", "turn_done") else None)
    real_write = n.writer.write
    def spy(head=None, vtheta=0.0, for_s=None):
        writes.append((vtheta, None if head is None else head["head_yaw"], None if head is None else head["head_pitch"]))
        return real_write(head, vtheta, for_s)
    n.writer.write = spy
    t = 0.0
    for i in range(12):   # twelve calls from behind-left, 30 s apart (take, 10.5 s turn, 10 s attention, ease home)
        det = dict(t=t, az_rad=2.09, az_deg=120.0, bins=100, e_db=-30.0, floor_db=-48.0, margin=0.5)
        writes.clear()
        n.respond(det, t)
        t_end = t + 30.0
        while t < t_end:
            n.motion_tick(t)
            t += 0.02
        turning = [w for w in writes if w[0]]
        assert turning and all(w[0] == 0.3 for w in turning)                       # body turns left at vtheta 0.3
        yaws = [w[1] for w in turning]
        assert yaws[0] > 1.0 and yaws[-1] < 0.5 and all(b <= a_ + 1e-9 for a_, b in zip(yaws, yaws[1:]))   # head unwinds
        assert all(w[2] < -0.3 for w in turning)                                    # looking up throughout
        k = max(i for i, w in enumerate(writes) if w[0])
        held = writes[k + 1:k + 1 + 450]                                            # the next 9 s: attention
        assert held and all(w[0] == 0 for w in held)
        assert all(abs(w[1] - yaws[-1]) < 0.25 and w[2] < -0.3 for w in held)     # gaze stays on the caller, up
        assert writes[-1][0] == 0 and abs(writes[-1][1]) < 1e-6                     # 30 s on: at rest, head home
    assert len(quacks) == 12, len(quacks)                                            # one quack per call, never dropped
    assert sum(1 for r in turns if r["kind"] == "turn") == 12 and sum(1 for r in turns if r["kind"] == "turn_done") == 12
    last = json.load(open(cmd))
    assert nc.zero_walk(last) and "for_s" not in last
    a2 = args(cmd=cmd, seed=5)
    a2.no_turn = True
    n2 = nc.NameCall(a2, nc.Log(None, echo=False))
    n2.respond(dict(t=0.0, az_rad=0.5, az_deg=29.0, bins=100, e_db=-30.0, floor_db=-48.0), 0.0)
    assert n2.turn is None


def test_a_name_without_a_bearing_quacks_and_keeps_the_head_where_it_looks(tmp_path):
    """No bearing (the localiser found no voice bins): one quack, no take, no turn; during attention it extends the
    attention instead of moving the head."""
    a = args(cmd=str(tmp_path / "c.json"), no_sound=False, mute=True, seed=5)
    a.no_turn = False
    n = nc.NameCall(a, nc.Log(None, echo=False))
    r = n.respond(dict(t=0.0, az_rad=None, az_deg=None, no_direction=True), 0.0)
    assert not n.head.busy and n.turn is None and n.attend_until is None
    assert len(n.quack_due) == 1 and r["quack_own_at"] == 0.3
    n.respond(dict(t=1.0, az_rad=0.4, az_deg=23.0, bins=100, e_db=-30.0, floor_db=-48.0, margin=0.5), 1.0)
    t = 1.0
    while n.head.busy:
        n.motion_tick(t)
        t += 0.02
    until, yaw = n.attend_until, n.head.last["yaw"]
    n.respond(dict(t=t, az_rad=None, az_deg=None, no_direction=True), t + 2.0)
    assert n.attend_until > until and not n.head.busy and n.head.last["yaw"] == yaw


def test_quack_skipped_only_when_the_caller_really_repeats(tmp_path):
    """Novelty x0.75 per call, 40 s recovery: calls 30 s apart are always answered; eight calls 2 s apart lose
    the quack from about the fifth on (Shawn 2026-10-30: skip only when he has repeated it over and over)."""
    def run(gap_s, n_calls, seed=7):
        a = args(cmd=str(tmp_path / "c.json"), no_sound=False, mute=True, seed=seed)
        a.no_turn = True
        n = nc.NameCall(a, nc.Log(None, echo=False))
        quacks = []
        n.log.write = lambda kind, **rec: quacks.append(rec) if kind == "quack" else None
        t, recs = 0.0, []
        for i in range(n_calls):
            recs.append(n.respond(dict(t=t, az_rad=0.4, az_deg=23.0, bins=100, e_db=-30.0, floor_db=-48.0), t))
            t_end = t + gap_s
            while t < t_end:
                n.motion_tick(t)
                t += 0.02
        return quacks, recs
    q, r = run(30.0, 8)
    assert len(q) == 8, [x["params"]["novelty"] for x in r]
    q, r = run(2.0, 8)
    skipped = [x for x in r if "quack_skipped" in x]
    assert 4 <= len(q) < 8 and skipped and all(x["quack_skipped"]["novelty"] < nc.QUACK_NOVELTY_MIN for x in skipped)


# --- attention: hold, face lock, scan, gyro turn, margin gate (2026-10-30 home test)

class FakeFinder:
    """facefind.FaceFinder double: a face fixed in the world at (yaw, pitch up) from t_face on, reported as the offset
    from the current gaze the camera would see (4 Hz frames); None = no face ever."""

    def __init__(self, gaze, world=None, t_face=0.0):
        self.gaze, self.world, self.t_face = gaze, world, t_face
        self.rate_hz, self.det_size = 4.0, 640

    def latest(self, now=None, stale_s=1.0):
        t_frame = math.floor(now / 0.25) * 0.25
        if self.world is None or t_frame < self.t_face:
            return None
        gy, gp = self.gaze(now)
        return dict(t=t_frame, yaw_err=gy - self.world[0], pitch_err=self.world[1] - gp, size=0.1, score=0.9)

    def stats(self):
        return dict(frames=0)


def attention_run(tmp_path, az=0.6, finder=None, until=16.0, seed=3, **kw):
    a = args(cmd=str(tmp_path / "c.json"), seed=seed, pitch=nc.LOOK_PITCH, **kw)
    a.no_turn = True
    n = nc.NameCall(a, nc.Log(None, echo=False))
    if finder is not None:
        n.finder = finder(n.head.gaze) if callable(finder) else finder
    recs, writes, clock = [], [], [0.0]
    n.log.write = lambda kind, **rec: recs.append((kind, rec))
    real = n.writer.write
    def spy(head=None, vtheta=0.0, for_s=None):
        writes.append((clock[0], None if head is None else head["head_yaw"], None if head is None else head["head_pitch"]))
        return real(head, vtheta, for_s)
    n.writer.write = spy
    n.respond(dict(t=0.0, az_rad=az, az_deg=round(math.degrees(az)), bins=100, e_db=-30.0, floor_db=-48.0, margin=0.5), 0.0)
    t = 0.0
    while t < until:
        clock[0] = t
        n.motion_tick(t)
        t += 0.02
    return n, recs, writes


def test_attention_holds_the_gaze_on_the_caller_then_drifts_home(tmp_path):
    """After the take the head stays on the caller, looking up, for ATTEND_S (Shawn 2026-10-30: look at me and wait,
    do not turn back and stand), then drifts home; with no camera nothing scans."""
    n, recs, writes = attention_run(tmp_path)
    at = lambda s: next(w for w in writes if abs(w[0] - s) < 0.011)
    for s in (4.0, 6.0, 9.5):
        w = at(s)
        assert abs(w[1] - 0.6) < 0.15 and w[2] < -0.5, (s, w)            # on the caller (yaw 0.6), camera up
    assert n.attend_until is None and [k for k, _ in recs if k == "attend_done"] == ["attend_done"]
    assert not [k for k, _ in recs if k == "scan"]
    assert abs(writes[-1][1]) < 1e-6 and abs(writes[-1][2] - n.head.default["head_pitch"]) < 1e-6   # home at 16 s


def test_a_face_in_view_is_centred_and_followed(tmp_path, monkeypatch):
    """A face 0.2 rad left of the heard bearing and lower than the look-up pitch: the gaze converges on it within a
    couple of seconds (FACE_GAIN per 4 Hz frame), the sighting is logged once and extends the attention."""
    monkeypatch.setattr(nc, "EYE_CONTACT_S", (30.0, 30.0))   # tracking quality, not the contact length
    n, recs, writes = attention_run(tmp_path, finder=lambda gaze: FakeFinder(gaze, world=(0.8, 0.5), t_face=2.5), until=9.0)
    yaw, pitch = n.head.gaze(9.0)
    assert abs(yaw - 0.8) < 0.05 and abs(pitch - 0.5) < 0.05, (yaw, pitch)
    faces = [r for k, r in recs if k == "face"]
    assert len(faces) == 1 and faces[0]["yaw_err_deg"] < -5 and faces[0]["pitch_err_deg"] < -20
    assert n.attend_until is not None and n.attend_until <= 2.5 + 2.0 + 30.0                     # contact capped from the lock
    assert not [k for k, _ in recs if k == "scan"]


def test_eye_contact_ends_while_the_face_is_still_in_view(tmp_path):
    """A face that stays in view gets EYE_CONTACT_S of eye contact per call, then the head drifts home (Shawn
    2026-10-30: it kept staring at him; a pet looks for 5-10 s, then looks away). A new call looks again."""
    n, recs, writes = attention_run(tmp_path, finder=lambda gaze: FakeFinder(gaze, world=(0.8, 0.5), t_face=1.0), until=30.0)
    lock = next(r for k, r in recs if k == "face")
    done = [k for k, _ in recs if k == "attend_done"]
    assert done == ["attend_done"] and n.attend_until is None
    home = next(w[0] for w in writes if w[0] > 2.0 and abs(w[1]) < 1e-6)
    assert nc.EYE_CONTACT_S[0] <= home - 1.0 <= nc.EYE_CONTACT_S[1] + 3.0, home        # drifted home after the contact
    assert abs(writes[-1][1]) < 1e-6                                                       # still home at 30 s, face in view
    n.respond(dict(t=30.0, az_rad=0.6, az_deg=34, bins=100, e_db=-30.0, floor_db=-48.0, margin=0.5), 30.0)
    assert n.contact_until is None


def test_no_face_in_view_sweeps_once_around_the_bearing(tmp_path):
    """With a camera but no face the head waits FACE_WAIT_S, sweeps SCAN_OFFSETS around the heard bearing at the pitch
    cap (within YAW_CAP), returns to the bearing and waits; the detector is deafened only as each step starts."""
    n, recs, writes = attention_run(tmp_path, finder=lambda gaze: FakeFinder(gaze, world=None), until=16.0)
    scans = [r for k, r in recs if k == "scan"]
    assert len(scans) == 1 and abs(scans[0]["around_deg"] - math.degrees(0.6)) < 10 and scans[0]["steps"] == len(nc.SCAN_OFFSETS)
    yaws = [w[1] for w in writes if 3.5 < w[0] < 9.5]
    assert max(yaws) > 1.1 and min(yaws) < -0.4                              # swept both ways
    assert all(w[2] < -0.5 for w in writes if 3.5 < w[0] < 9.5)               # pitch stays at the cap
    assert abs(writes[-1][1]) < 1e-6                                          # 16 s: attention over, home


def test_body_turn_stops_on_the_gyro_not_the_clock(tmp_path):
    """The brain's tick log says how far the body really turned: at 0.4 rad/s (the home floor) a caller at 120 deg is
    within TURN_KEEP after 4.5 s, not the 10.5 s the planning rate would wait (2026-10-30: a timed turn went 273 deg)."""
    cmd, log_path = str(tmp_path / "c.json"), str(tmp_path / "brain.jsonl")
    a = args(cmd=cmd, seed=5, pitch=nc.LOOK_PITCH)
    a.no_turn = False
    n = nc.NameCall(a, nc.Log(None, echo=False))
    n.gyro = nc.GyroTurn(log_path)
    recs = []
    n.log.write = lambda kind, **rec: recs.append((kind, rec))
    f = open(log_path, "a")
    def row(t, gz):
        f.write(json.dumps(dict(t=t, mode="walk", gyro_body=[0.0, 0.0, gz], cmd=nc.WALK_ZERO)) + "\n")
        f.flush()
    row(0.0, 0.0)
    n.respond(dict(t=0.0, az_rad=2.09, az_deg=120.0, bins=100, e_db=-30.0, floor_db=-48.0, margin=0.5), 0.0)
    t = 0.0
    while t < 20.0:
        cur = nc.read_cmd_file(cmd) or {}
        row(t, 0.4 if cur.get("vtheta") else 0.0)       # the body turns left at 0.4 rad/s while the command says so
        n.motion_tick(t)
        t += 0.02
    turn = next(r for k, r in recs if k == "turn")
    done = next(r for k, r in recs if k == "turn_done")
    assert turn["dur_s"] > 10 and done["by"] == "gyro" and 4.0 < done["s"] < 5.5, (turn, done)
    assert abs(done["turned_deg"] - math.degrees(2.09 - nc.TURN_KEEP)) < 6
    assert n.attend_until is not None or any(k == "attend_done" for k, _ in recs)   # attention followed the turn


def test_no_body_turn_at_the_take_front_first(tmp_path):
    """Front first (Shawn 2026-10-30 17:30; replaces the margin gate): a call heard at -103 deg aims the head at the
    front-half mirror on the right (-77 deg), never turns the body at the take, and plans a back turn to the right
    for later whatever the margin says; the margin and the behind flag are only logged."""
    a = args(cmd=str(tmp_path / "c.json"), seed=5, pitch=nc.LOOK_PITCH)
    a.no_turn = False
    n = nc.NameCall(a, nc.Log(None, echo=False))
    for margin in (0.01, 0.6):
        r = n.respond(dict(t=0.0, az_rad=-1.8, az_deg=-103.0, bins=100, e_db=-30.0, floor_db=-48.0, margin=margin), 0.0)
        assert n.turn is None and "turn_skipped" not in r and r["margin"] == margin and r["behind_heard"]
        assert r["side"] == -1 and abs(r["az_front_rad"] + (math.pi - 1.8)) < 1e-3
        assert abs(r["target_yaw"] + min(nc.YAW_CAP, math.pi - 1.8)) < 1e-3         # front half, capped at YAW_CAP
        assert n.back_turn["sign"] == -1.0 and abs(n.back_turn["az_rad"] + 1.8) < 1e-3


def test_a_back_turn_that_finds_nobody_turns_on_until_the_camera_sees_someone(tmp_path):
    """2026-10-30 21:03:09: every side cue read right, Shawn stood on the left; the duck turned right, scanned, found
    nobody and gave up. With a camera the back turn's failed search is followed by one more turn the same way (the
    time cap), and any turn stops as soon as a face or a person comes into view; without a camera nothing changes
    (test_every_response_quacks_... keeps its one turn per call)."""
    a = args(cmd=str(tmp_path / "c.json"), seed=5, pitch=nc.LOOK_PITCH)
    a.no_turn = False
    n = nc.NameCall(a, nc.Log(None, echo=False))
    n.finder = FakeFinder(n.head.gaze, world=(0.0, 0.5), t_face=34.0)     # nobody in view until 34 s
    recs = []
    n.log.write = lambda kind, **rec: recs.append((kind, dict(rec)))
    n.respond(dict(t=0.0, az_rad=-0.57, az_deg=-32.6, bins=100, e_db=-30.0, floor_db=-48.0, margin=0.05), 0.0)
    t = 0.0
    while t < 60.0:
        n.motion_tick(t)
        t += 0.02
    turns = [r for k, r in recs if k == "turn"]
    dones = [r for k, r in recs if k == "turn_done"]
    assert len(turns) == 2 and len(dones) == 2, (turns, dones)
    assert turns[0]["vtheta"] == -0.3 and turns[1]["vtheta"] == -0.3            # the same way round, never back
    assert abs(turns[1]["az_deg"] + 180.0) < 0.1 and dones[1]["more"] and not dones[0]["more"]
    assert dones[0]["by"] == "time" and dones[1]["by"] == "seen" and dones[1]["s"] < turns[1]["dur_s"] - 1.0
    assert [k for k, _ in recs if k == "face"]                                   # and the face is then tracked
    # the same call with the face in view from the start: no body turn at all
    n2 = nc.NameCall(a, nc.Log(None, echo=False))
    n2.finder = FakeFinder(n2.head.gaze, world=(-0.5, 0.5), t_face=0.0)
    recs2 = []
    n2.log.write = lambda kind, **rec: recs2.append(kind)
    n2.respond(dict(t=0.0, az_rad=-0.57, az_deg=-32.6, bins=100, e_db=-30.0, floor_db=-48.0, margin=0.05), 0.0)
    t = 0.0
    while t < 30.0:
        n2.motion_tick(t)
        t += 0.02
    assert "turn" not in recs2 and "face" in recs2


def test_the_name_is_the_default_trigger_on_the_robot():
    assert nc.parse_args([]).name == "mochi"
    assert nc.parse_args(["--any-voice"]).name is None
    assert nc.parse_args(["--wav", "x.wav"]).name is None                   # replays and the replay tool stay any-voice
    assert nc.parse_args(["--wav", "x.wav", "--name", "mochi"]).name == "mochi"


def test_life_log_stop_does_not_crash_namecall(tmp_path):
    """2026-10-30 18:35: the life log stopped on a nearly full card and its on_stop note crashed namecall
    (Log.write got 'why' twice); the stop must only log a warning."""
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "namecall.py")).read()
    line = [l for l in src.splitlines() if "life log stopped" in l][0]
    assert "**st)" not in line
    log = nc.Log(None, echo=False)
    st = dict(why="disk nearly full", used_mb=1.0, free_gb=1.7)
    log.write("warn", why=f"life log stopped: {st['why']}", **{k: v for k, v in st.items() if k != "why"})


class LaggedWorld:
    """A face fixed in the world, seen through the real delays of the 2026-10-30 18:53 live test: the head reaches the
    commanded gaze HEAD_LAG_S later, a frame is captured every FRAME_S and its result arrives DET_S after capture,
    offset measured from where the head really was at capture. Also stands in for HeadHistory (at(t): the real gaze)."""
    HEAD_LAG_S, FRAME_S, DET_S = 0.25, 0.22, 0.45

    def __init__(self, gaze, world):
        self.gaze, self.world = gaze, world
        self.hist = []                   # (t, commanded yaw, pitch)
        self.rate_hz, self.det_size = 4.0, 640

    def record(self, now):
        self.hist.append((now,) + tuple(self.gaze(now)))

    def at(self, t):
        t -= self.HEAD_LAG_S
        past = [h for h in self.hist if h[0] <= t]
        return (past[-1][1], past[-1][2]) if past else (self.hist[0][1], self.hist[0][2]) if self.hist else None

    def latest(self, now=None, stale_s=1.0):
        t_frame = math.floor((now - self.DET_S) / self.FRAME_S) * self.FRAME_S
        real = self.at(t_frame) if t_frame > 0 else None
        if real is None:
            return None
        return dict(t=t_frame, yaw_err=real[0] - self.world[0], pitch_err=self.world[1] - real[1], size=0.1, score=0.9)

    def update(self):
        pass

    def stats(self):
        return dict(frames=0)


def test_face_tracking_does_not_swing_with_the_real_delays(tmp_path, monkeypatch):
    """2026-10-30 18:53: the head swung +-0.35 rad with a 2.2 s period for 40 s around Shawn's face (offset added to
    the commanded gaze, behind about 0.5 s of delay). With the gaze measured at the frame's capture time it settles
    on the face and stays there."""
    monkeypatch.setattr(nc, "EYE_CONTACT_S", (30.0, 30.0))   # tracking quality, not the contact length
    a = args(cmd=str(tmp_path / "c.json"), seed=3, pitch=nc.LOOK_PITCH)
    a.no_turn = True
    n = nc.NameCall(a, nc.Log(None, echo=False))
    w = LaggedWorld(n.head.gaze, world=(0.2, 0.9))
    n.finder, n.head_hist = w, w
    n.log.write = lambda kind, **rec: None
    n.respond(dict(t=0.0, az_rad=0.6, az_deg=34, bins=100, e_db=-30.0, floor_db=-48.0, margin=0.5), 0.0)
    t, yaws = 0.0, []
    while t < 14.0:
        w.record(t)
        n.motion_tick(t)
        if t > 9.0:
            yaws.append(w.at(t)[0])
        t += 0.02
    yaws = np.array(yaws)
    assert abs(yaws.mean() - 0.2) < 0.04 and yaws.max() - yaws.min() < 0.06, (yaws.mean(), yaws.min(), yaws.max())


def test_the_first_look_goes_to_the_heard_side_by_the_learned_bearing(tmp_path):
    """2026-10-30 19:48, 15 camera-confirmed calls: the heard side was right every time, the heard magnitude never
    (readings of 100-176 deg from callers 13-51 deg in front). With bearing_prior.json the take aims side * look_deg
    and the raw bearing stays in the record; without the file the folded bearing is used as before."""
    prior = tmp_path / "bearing_prior.json"
    prior.write_text(json.dumps(dict(look_deg=35.0, n=15, side_correct=15)))
    for az, want in ((2.4, 0.611), (-0.5, -0.611), (1.0, 0.611)):
        a = args(cmd=str(tmp_path / "c.json"), seed=3, pitch=nc.LOOK_PITCH, bearing_prior=str(prior))
        a.no_turn = True
        n = nc.NameCall(a, nc.Log(None, echo=False))
        rec = n.respond(dict(t=0.0, az_rad=az, az_deg=round(math.degrees(az)), bins=100, e_db=-30.0, floor_db=-48.0, margin=0.5), 0.0)
        assert abs(rec["target_yaw"] - want) < 0.02 and abs(rec["az_look_deg"] - math.degrees(want)) < 0.1, (az, rec["target_yaw"])
        assert abs(rec["az_rest_rad"] - az) < 1e-6                       # the heard bearing is kept for fit_bearing.py
    a = args(cmd=str(tmp_path / "c.json"), seed=3, pitch=nc.LOOK_PITCH)
    a.no_turn = True
    rec = nc.NameCall(a, nc.Log(None, echo=False)).respond(dict(t=0.0, az_rad=1.0, az_deg=57, bins=100, e_db=-30.0, floor_db=-48.0, margin=0.5), 0.0)
    assert "az_look_deg" not in rec and abs(rec["target_yaw"] - 1.0) < 0.05
