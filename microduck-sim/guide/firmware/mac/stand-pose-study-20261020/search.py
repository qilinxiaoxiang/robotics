"""Stages of the open-loop stand study; each writes results/<stage>.jsonl (one row per sim case). Sim only.

  ~/.venvs/microduck-dyn/bin/python search.py <stage> [--workers 5]

Stages:
  repro     current STAND (NEUTRAL_POSE) from (a) NEUTRAL feet flat and (b) the real 1018d 7-deg start, nominal and
            +-20 g head, 60 s; plus (b0) the 1018d start held without a ramp.
  single    one backward joint group at a time (ankle, hip, knee: 0.01..0.08 rad), starts a/b, head 0 and +20 g, 60 s
  combo     ankle x hip x knee grid (0, 0.02, 0.04, 0.06), starts a/b, head +20 g, 60 s
  robust    shortlisted poses (ROBUST below) over the perturbation set, 60 s
  pollen    policy mean stances (real 1019f coordinator mean, symmetrised, stand61-only symmetrised; sim stand61 mean)
            at KP 400 and 200, starts a/b, head 0/+20
  takeover  walk mode (stand61, zero command) taking over from each shortlisted pose after 5 s, 10 s of walk
  lift      stand61 with the trunk held in the air (feet free) for 5 s
Every job is a 60 s or shorter simulated run of about 6-10 s wall time.
"""
import argparse
import itertools
import json
import multiprocessing as mp
import os
import sys

SIM_PYTHON = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
if os.path.realpath(sys.prefix) != os.path.realpath(os.path.dirname(os.path.dirname(SIM_PYTHON))):
    os.execv(SIM_PYTHON, [SIM_PYTHON, os.path.abspath(__file__)] + sys.argv[1:])
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
RES = os.path.join(HERE, "results")
REAL = json.load(open(os.path.join(HERE, "real_poses.json")))
START_B = REAL["start_7deg"]["q"]

# coordinator's mean of walk-mode upright ticks in 1019f (stand61 + walk61 at zero command, 6506 ticks)
COORD_MEAN = {"right_ankle": 0.0273, "right_knee": 0.0079, "right_hip_pitch": -0.0740, "right_hip_roll": 0.0104,
              "right_hip_yaw": 0.0515, "left_ankle": 0.0081, "left_knee": 0.0158, "left_hip_pitch": 0.0002,
              "left_hip_roll": -0.0075, "left_hip_yaw": 0.0112, "head_pitch": 0.0522, "neck_pitch": -0.1467,
              "head_yaw": -0.0038, "head_roll": -0.0042}


def symmetrise(delta):
    out = dict(delta)
    for n in delta:
        if n.startswith("right_"):
            j = n[6:]
            avg = (delta["right_" + j] - delta["left_" + j]) / 2
            out["right_" + j], out["left_" + j] = round(avg, 4), round(-avg, 4)
    return out


def job(spec):
    import stand_sim as S
    label, delta, kw = spec
    kw = dict(kw)
    if kw.pop("start_b", False):
        kw["start"] = START_B
    if kw.get("start") == "target":
        kw["start"] = S.pose_from(delta)
    r = S.run_case(S.pose_from(delta), **kw)
    r["trace"] = [x for x in r["trace"] if abs(x[0] - round(x[0])) < 1e-6 and int(round(x[0])) % 5 == 0] if r.get("trace") else []
    r.update(label=label, delta=delta)
    if isinstance(r.get("start"), dict):
        r.pop("start")
    return r


def back(a=0.0, h=0.0, k=0.0):
    import stand_sim as S
    return S.back_delta(a, h, k)


def stage_jobs(stage):
    J = []
    if stage == "repro":
        for hg in (0, 20, -20):
            J.append((f"NEUTRAL a head{hg:+d}", {}, dict(T=60, head_g=hg)))
            J.append((f"NEUTRAL b head{hg:+d}", {}, dict(T=60, head_g=hg, start_b=True)))
        J.append(("b0: 1018d start held (no ramp)", {k: START_B[k] - v for k, v in __import__("stand_sim").NEUTRAL.items()},
                  dict(T=10, start_b=True)))
    elif stage == "single":
        for grp in ("ankle", "hip", "knee"):
            for i in range(1, 9):
                amt = i / 100
                dl = back(**{grp[0]: amt})
                for hg in (0, 20):
                    for sb in (False, True):
                        J.append((f"{grp}_back {amt:.2f} {'b' if sb else 'a'} head{hg:+d}", dl, dict(T=60, head_g=hg, start_b=sb)))
    elif stage == "combo":
        # start a only: from start b every pose falls during the 2 s entry ramp (single stage); see stage ramp
        vals = (0.0, 0.02, 0.04, 0.06)
        for a, h, k in itertools.product(vals, vals, vals):
            if (a > 0) + (h > 0) + (k > 0) < 2:
                continue  # singles are in the single stage
            dl = back(a, h, k)
            for hg in (0, 10, 20):
                J.append((f"a{a:.2f} h{h:.2f} k{k:.2f} a head{hg:+d}", dl, dict(T=60, head_g=hg)))
        for k in (0.035, 0.045, 0.055):  # finer knee singles around the best single
            for hg in (0, 10, 20):
                J.append((f"a0.00 h0.00 k{k:.3f} a head{hg:+d}", back(0, 0, k), dict(T=60, head_g=hg)))
    elif stage == "ramp":
        # start b (real 1018d forward start) with shorter entry ramps, for NEUTRAL and the shortlist
        for name, dl in dict(NEUTRAL={}, **ROBUST).items():
            for rs in (2.0, 1.0, 0.5, 0.3, 0.1):
                for hg in (0, 10, 20):
                    J.append((f"{name} b ramp{rs} head{hg:+d}", dl, dict(T=60, head_g=hg, start_b=True, ramp_s=rs)))
    elif stage == "robust":
        # start a only (start b is the ramp stage); a head+10 case sits between the falls seen on the robot
        for name, dl in dict(ROBUST, NEUTRAL={}).items():
            for sb in (False,):
                s = "b" if sb else "a"
                cases = [("nominal", {}), ("nominal 120 s", dict(T=120)), ("head+10", dict(head_g=10)), ("f0.4", dict(friction=0.4)), ("f0.6", dict(friction=0.6)),
                         ("f1.0", dict(friction=1.0)), ("head+20", dict(head_g=20)), ("head-20", dict(head_g=-20)),
                         ("lid", dict(lid=True)), ("6.6V", dict(volt=6.6)), ("7.32V", dict(volt=7.32)),
                         ("push fwd 0.1 m/s", dict(push=(20, 0.1))), ("push back 0.1 m/s", dict(push=(20, -0.1))),
                         ("head+20 f0.4 push fwd", dict(head_g=20, friction=0.4, push=(20, 0.1))),
                         ("seed1", dict(seed=1))]
                for cname, kw in cases:
                    J.append((f"{name} {s} {cname}", dl, dict(dict(T=60, start_b=sb), **kw)))
    elif stage == "pollen":
        sim_mean = json.load(open(os.path.join(RES, "sim_stand61_mean.json")))["delta_from_neutral"] \
            if os.path.exists(os.path.join(RES, "sim_stand61_mean.json")) else None
        cands = {"coord_raw": COORD_MEAN, "coord_sym": symmetrise(COORD_MEAN),
                 "stand61only_sym": REAL["stand61_mean_1019f"]["symmetrised_delta"]}
        if sim_mean:
            cands["sim_stand61_mean"] = sim_mean
        for name, dl in cands.items():
            for kp in (400, 200):
                for hg in (0, 20):
                    for sb in (False, True):
                        J.append((f"{name} kp{kp} {'b' if sb else 'a'} head{hg:+d}", dl, dict(T=60, kp=kp, head_g=hg, start_b=sb)))
    elif stage == "takeover":
        for name, dl in dict(ROBUST, NEUTRAL={}).items():
            for hg in (0, 20):
                J.append((f"{name} walk-takeover head{hg:+d}", dl, dict(T=16, walk_at=5.0, walk_s=11.0, head_g=hg)))
    elif stage == "lift":
        for hp in (0.0, 10.0, -10.0):
            for hg in (0,):
                J.append((f"stand61 lifted 8 cm pitch{hp:+.0f}", {}, dict(T=10, walk_at=1.0, walk_s=9.0,
                                                                          lift=(4.0, 0.08, hp, 5.0))))
        J.append(("stand61 on ground (reference, same window)", {}, dict(T=10, walk_at=1.0, walk_s=9.0, lift=(4.0, 0.0, 0.0, 5.0))))
    return J


ROBUST = {}
if os.path.exists(os.path.join(HERE, "shortlist.json")):
    ROBUST = json.load(open(os.path.join(HERE, "shortlist.json")))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage")
    ap.add_argument("--workers", type=int, default=5)
    a = ap.parse_args()
    os.makedirs(RES, exist_ok=True)
    J = stage_jobs(a.stage)
    print(f"{a.stage}: {len(J)} jobs", flush=True)
    out = os.path.join(RES, a.stage + ".jsonl")
    with mp.get_context("spawn").Pool(a.workers) as pool, open(out, "w") as f:
        for r in pool.imap(job, J):
            f.write(json.dumps(r) + "\n")
            f.flush()
            print(r["label"], "fell", r["fell_at"], "max_after5", r["max_tilt_after_5s"], "end", r["end_tilt"], flush=True)


if __name__ == "__main__":
    main()
