"""Which observation channel makes stand61 churn its goals on the robot but not in the sim?

Offline, no robot and no sim stepping: rebuild stand61's observation from each logged tick (gyro_body, gb, q, dq, the
previous logged action, zero command, head command) and check the replay matches the logged action. Then smooth one
observation block at a time (centred 5-tick moving average, i.e. its 10-25 Hz content removed) and measure how much of
the action's fast part (action minus its 0.5 s moving average) is left. The block whose smoothing removes most of the
fast action is what drives the churn.

  python3 churn_replay.py ROBOT_OR_SIM_LOG.jsonl[.gz] ...
"""
import gzip, json, sys, os, statistics as st
import numpy as np
FW = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, FW + "/pi/microduck_rt"); sys.path.insert(0, FW + "/pi")
from constants import MOTOR_TO_ID, OBSERVATION_DOF_ORDER as OBS  # noqa: E402
import onnxruntime as ort  # noqa: E402
ID_TO_NAME = {v: k for k, v in MOTOR_TO_ID.items()}
NAMES = [ID_TO_NAME[i] for i in range(1, 15)]
MODELS = os.path.abspath(os.path.join(FW, "..", "..", "hardware-design-20260912", "whole-robot-20260912", "runtime-overlay", "models"))
so = ort.SessionOptions(); so.intra_op_num_threads = 1; so.inter_op_num_threads = 1
sess = ort.InferenceSession(os.path.join(MODELS, "stand61.onnx"), so)
default = dict(zip(OBS, [float(v) for v in sess.get_modelmeta().custom_metadata_map["default_joint_pos"].split(",")]))
LEGS = [k for k, n in enumerate(OBS) if any(s in n for s in ("ankle", "knee", "hip"))]


def segments(path):
    """Contiguous stand61 runs at zero command: lists of logged rows with an action."""
    seg = []
    for line in (gzip.open(path, "rt") if path.endswith(".gz") else open(path)):
        r = json.loads(line)
        if r.get("mode") == "walk" and r.get("policy") is None and seg:
            continue  # a dropped read inside the run
        if r.get("mode") == "walk" and r.get("policy") == "stand" and r.get("action") is not None:
            seg.append(r)
        else:
            if len(seg) > 100:
                yield seg
            seg = []
    if len(seg) > 100:
        yield seg


def blocks(r):
    q = dict(zip(NAMES, r["q"])); dq = dict(zip(NAMES, r["dq"]))
    return {"gyro": np.array(r["gyro_body"], np.float32), "grav": np.array(r["gb"], np.float32),
            "qpos": np.array([q[n] - default[n] for n in OBS], np.float32),
            "qvel": np.array([dq[n] for n in OBS], np.float32),
            "head": np.array(r.get("head_cmd") or [0, 0, 0, 0], np.float32)}


def act(b, last):
    obs = np.concatenate([b["gyro"], b["grav"], b["qpos"], b["qvel"], last, [0, 0, 0], b["head"], np.zeros(6)]).astype(np.float32)
    return sess.run(None, {sess.get_inputs()[0].name: obs[None]})[0][0]


def smooth(x, w):
    k = np.ones(2 * w + 1) / (2 * w + 1)
    return np.stack([np.convolve(np.pad(x[:, j], w, mode="edge"), k, mode="valid") for j in range(x.shape[1])], 1)


def fast(a, w=12):
    return a - smooth(a, w)


def run(seg, smooth_block=None, w=2, feedback=False):
    """Actions for the segment. feedback=False: the previous action is the logged one (one-step replay);
    feedback=True: the replayed action feeds the next step (the policy's own loop closed, sensors still logged)."""
    B = [blocks(r) for r in seg]
    if smooth_block:
        arr = smooth(np.stack([b[smooth_block] for b in B]), w)
        for b, v in zip(B, arr):
            b[smooth_block] = v.astype(np.float32)
    out, last = [], np.array(seg[0]["action"], np.float32)
    for i in range(1, len(seg)):
        prev = last if feedback else np.array(seg[i - 1]["action"], np.float32)
        a = act(B[i], prev)
        out.append(a); last = a
    return np.array(out)


def rms_fast(a):
    return float(np.sqrt(np.mean(fast(a)[:, LEGS] ** 2)))


for path in sys.argv[1:]:
    segs = [s[25:] for s in segments(path)]  # skip the first 0.5 s of each run (the switch into stand61)
    segs = [s for s in segs if len(s) > 100]
    if not segs:
        print(path, "no stand61 run"); continue
    logged = np.concatenate([np.array([r["action"] for r in s[1:]]) for s in segs])
    replay = np.concatenate([run(s) for s in segs])
    print(f"{os.path.basename(path)}: {len(segs)} stand61 runs, {len(logged)} ticks; replay max |err| {np.max(np.abs(replay - logged)):.4f} rad")
    base = rms_fast(logged)
    print(f"   fast leg action, logged: {base * 1000:6.1f} mrad rms")
    B = [blocks(r) for s in segs for r in s]
    for k in ("gyro", "grav", "qpos", "qvel"):
        x = np.stack([b[k] for b in B])
        print(f"   obs {k:5s} fast part rms {np.sqrt(np.mean(fast(x) ** 2)) * 1000:7.1f} m-units", end="")
        a = np.concatenate([run(s, k) for s in segs])
        print(f"   -> smoothing it leaves {rms_fast(a) * 1000:6.1f} mrad ({rms_fast(a) / base:4.0%})")
