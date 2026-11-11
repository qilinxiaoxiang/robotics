"""Collect every finished run into sim/out/results.json: flight rows (sim/out/cut, sim/out/ground), the held-pose probe
(sim/out/hold) and the walking probe (sim/out/walkprobe, brain_sim_check output). Run from the flight-20261110 folder."""
import glob
import json
from pathlib import Path

OUT = Path("sim/out")


def flight(pattern):
    rows = []
    for f in sorted(glob.glob(str(OUT / pattern))):
        r = json.load(open(f)); r["file"] = f; rows.append(r)
    return rows


def walk():
    rows = []
    for f in sorted(glob.glob(str(OUT / "walkprobe/*_ss*.txt"))):
        t = open(f).read(); i = t.rfind('{"model"')
        if i < 0:
            rows.append(dict(file=f, error=t[-300:])); continue
        r = json.loads(t[i:].strip().splitlines()[0])
        name = Path(f).stem
        variant, ss, cmd = name.rsplit("_", 2)
        rows.append(dict(file=f, variant=variant, stand_s=float(ss[2:]), command=cmd, fell_at=r["fell_at"], fall_dir=r["fall_dir"],
                         max_tilt=r["max_tilt"], first_policy_tick_s=r["first_policy_tick_s"], dist_x=r["dist_x"],
                         yaw_walk_deg=r["yaw_walk_deg"]))
    return rows


def hold():
    rows = []
    for f in sorted(glob.glob(str(OUT / "hold/*_h*_a*.json"))):
        r = json.load(open(f))
        rows.append(dict(file=f, case=Path(f).stem, fell_at=r["fell_at"], support_end=r["support_end"]))
    return rows


def summary(path):
    p = OUT / path
    return json.load(open(p)) if p.exists() else None


w = walk()
res = dict(
    batch_ground=summary("batch/summary.json"),          # take-off from the ground, every perturbation
    batch_air=summary("batch_air/summary.json"),         # start hovering 0.3 m up, every perturbation
    ground_options=summary("walk/summary.json"),         # zero-training ground options (walk_batch.py)
    part_c=summary("partc/summary.json"),                # thrust-assisted walking (partc.py)
    authority=summary("authority.json"),
    # full sequence with the leg policy (README "Full sequence"): full_success = airborne part ok, disarmed, then still
    # standing (no tilt over 45 deg, feet on the wanted surface, nothing else on it, tilt under 25 deg) 5 s after the disarm
    full_sequence=dict(handover=summary("fullseq_handover/summary.json"),
                       handover_heldpose=summary("fullseq_handover_heldpose/summary.json"),
                       handover_monitor=summary("fullseq_handover_monitor/summary.json"),
                       policy_through_flight=summary("fullseq_policy/summary.json"),
                       diag_fan_cut_at_land_detect=summary("fullseq_diag_fancut/summary.json"),
                       held_mode_reproduces=summary("heldcheck/heldcheck.json")),
    landing_settle=flight("landing/*.json"),
    crouch_hold_probe=flight("crouch/*.json"),
    mass=json.load(open(OUT / "mass_report.json")),
    flight=flight("cut/*.json"),
    ground_transition_probe=flight("ground/*.json"),
    held_pose_probe=hold(),
    walking_probe=w,
    walking_summary={v: dict(runs=sum(1 for r in w if r.get("variant") == v),
                             falls=sum(1 for r in w if r.get("variant") == v and r.get("fell_at") is not None))
                     for v in sorted({r.get("variant") for r in w if r.get("variant")})},
)
json.dump(res, open(OUT / "results.json", "w"), indent=1)
print(json.dumps(res["walking_summary"]))
print("flight", sum(r["success"] for r in res["flight"]), "/", len(res["flight"]),
      "ground", sum(r["success"] for r in res["ground_transition_probe"]), "/", len(res["ground_transition_probe"]),
      "held poses standing", sum(r["fell_at"] is None for r in res["held_pose_probe"]), "/", len(res["held_pose_probe"]))
