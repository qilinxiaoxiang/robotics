"""Round 3 gap study: which runtime-simulation condition makes s2r6_4 chatter and fall at standstill (robot,
2026-11-19: 172 action jumps per 10 s, fall at 4.4 s) while the deployed walk61 still stands and walks.

  python3 train/ts3_gap_sweep.py spec <set> [<model dir under ckpt or walk61> ...]  -> train/eval/spec_gap_<set>.json
  modal run train/flight_eval_modal.py --spec train/eval/spec_gap_<set>.json
  python3 train/ts3_gap_sweep.py table <set> [<model> ...]                         -> train/out/chatter/gap_<set>.json

Cells per condition and model: stand (no pack, zero command 20 s, SEEDS seeds) and, for sets marked walk, walk
(vx 0.25 for 15 s). Per cell: falls, fall times, action jumps over 0.5 rad per 10 s (the episode's count over its
upright time). Conditions are probe flags (brain_sim_check.py) and flight_eval switches; each names its source.
"""
import json
import sys
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
WALK61 = "../../../microduck_rl/cmu/whole/runtime-overlay/models"
import os
SEEDS = int(os.environ.get("GAP_SEEDS", 3))
SLOW = {"FLIGHT_SLOW_LOOP_MS": "3.2"}  # 43 Hz, the robot's loop rate in the failed run (184 policy ticks in 4.42 s)
# name: (probe flags, env). Sources: delays and IMU rate as sim_suite.py's stress cases; friction scale from the
# jitter sim-ID (2026-10-17, BAM friction x1.5); joint and foot play from the play studies (2026-10-21, 2026-11-12);
# kp from the servo deadband study (2026-10-15/16); supply from CURRENT-STATE.json servo_rail_v (7.2 to 8.2 V).
SETS = {
    "a": {
        "base": ([], {}),
        "sdelay2": (["--sensor-delay", "2"], {}),
        "adelay2": (["--action-delay", "2"], {}),
        "delay22": (["--sensor-delay", "2", "--action-delay", "2"], {}),
        "sdelay3": (["--sensor-delay", "3"], {}),
        "slow43": ([], SLOW),
        "slow43_sdelay2": (["--sensor-delay", "2"], SLOW),
        "slow43_delay22": (["--sensor-delay", "2", "--action-delay", "2"], SLOW),
        "fric1.5": (["--bam-friction-scale", "1.5"], {}),
        "fric0.5": (["--bam-friction-scale", "0.5"], {}),
        "fric0.2": (["--bam-friction-scale", "0.2"], {}),
        "play1": (["--joint-play", "1"], {}),
        "play2": (["--joint-play", "2"], {}),
        "play4": (["--joint-play", "4"], {}),
        "footplay2": (["--foot-play", "2"], {}),
        "kp300": (["--kp-rl", "300"], {}),
        "kp400": (["--kp-rl", "400"], {}),
        "volt8.2": (["--volt", "8.2"], {}),
        "imu35_drop8": (["--drop", "0.08", "--imu-hz", "35"], {}),
        "mu0.5": (["--floor-mu", "0.5"], {}),
        "sole_soft": (["--sole-solref", "0.05", "1"], {}),
        "sole_softer": (["--sole-solref", "0.1", "0.5"], {}),
        "play2_slow43": (["--joint-play", "2"], SLOW),
        "play2_delay22": (["--joint-play", "2", "--sensor-delay", "2", "--action-delay", "2"], {}),
        "fric0.5_slow43_sdelay2": (["--bam-friction-scale", "0.5", "--sensor-delay", "2"], SLOW),
    },
    # set b: the gain hit of set a (kp400) and the observation-side switches of the jitter study (its matched
    # condition 2026-10-30: gyro noise 0.25 x rms leg joint speed + BAM friction x1.4), with walking cells
    "b": {
        "base": ([], {}),
        "kp250": (["--kp-rl", "250"], {}),
        "kp350": (["--kp-rl", "350"], {}),
        "kp400": (["--kp-rl", "400"], {}),
        "gndq0.15": ([], {"FLIGHT_GYRO_NOISE_DQ": "0.15"}),
        "gndq0.25": ([], {"FLIGHT_GYRO_NOISE_DQ": "0.25"}),
        "gndq0.4": ([], {"FLIGHT_GYRO_NOISE_DQ": "0.4"}),
        "gndq0.25_fric1.4": (["--bam-friction-scale", "1.4"], {"FLIGHT_GYRO_NOISE_DQ": "0.25"}),
        "gndq0.25_fric1.25": (["--bam-friction-scale", "1.25"], {"FLIGHT_GYRO_NOISE_DQ": "0.25"}),
        "gn0.2": ([], {"FLIGHT_GYRO_NOISE": "0.2"}),
        "gn0.5": ([], {"FLIGHT_GYRO_NOISE": "0.5"}),
        "obsdel1": ([], {"FLIGHT_OBS_DELAY": "1"}),
        "kp300_gndq0.25": (["--kp-rl", "300"], {"FLIGHT_GYRO_NOISE_DQ": "0.25"}),
    },
    # set c: combinations of the two hits of set b (loop gain and motion-driven gyro vibration)
    "c": {
        "kp350_gndq0.15": (["--kp-rl", "350"], {"FLIGHT_GYRO_NOISE_DQ": "0.15"}),
        "kp350_gndq0.25": (["--kp-rl", "350"], {"FLIGHT_GYRO_NOISE_DQ": "0.25"}),
        "kp400_gndq0.15": (["--kp-rl", "400"], {"FLIGHT_GYRO_NOISE_DQ": "0.15"}),
        "kp400_gndq0.25": (["--kp-rl", "400"], {"FLIGHT_GYRO_NOISE_DQ": "0.25"}),
        "gndq0.6": ([], {"FLIGHT_GYRO_NOISE_DQ": "0.6"}),
        "kp450": (["--kp-rl", "450"], {}),
        "kp500": (["--kp-rl", "500"], {}),
    },
    # set d: the single-switch match (loop gain) on 10 seeds
    "d": {
        "kp400": (["--kp-rl", "400"], {}),
        "kp425": (["--kp-rl", "425"], {}),
    },
}
WALK_SETS = {"b", "c", "d"}


def mdir(m):
    return WALK61 if m == "walk61" else f"ckpt/{m}"


def cells(sset):
    return ["stand"] + (["walk"] if sset in WALK_SETS else [])


def name(sset, cond, m, cell):
    return f"gap_{sset}_{cond}_{m}_{cell}".replace("+", "p")


if __name__ == "__main__":
    mode, sset = sys.argv[1], sys.argv[2]
    models = sys.argv[3:] or ["s2r6_4", "walk61"]
    conds = SETS[sset]
    if mode == "spec":
        evals = [dict(name=name(sset, c, m, cell), models=mdir(m), manifest="manifests/flightpack-none.json", case=cell,
                      episodes=SEEDS, extra=flags, env=env)
                 for c, (flags, env) in conds.items() for m in models for cell in cells(sset)
                 if not (TRAIN / f"eval/{name(sset, c, m, cell)}.json").exists()]
        out = TRAIN / f"eval/spec_gap_{sset}.json"
        out.write_text(json.dumps(dict(evals=evals), indent=1))
        print(f"{out}: {len(evals)} evals, {sum(e['episodes'] for e in evals)} episodes")
    else:
        rows = {}
        for c, (flags, env) in conds.items():
            rows[c] = dict(flags=flags, env=env)
            for m in models:
                for cell in cells(sset):
                    p = TRAIN / f"eval/{name(sset, c, m, cell)}.json"
                    if not p.exists():
                        continue
                    eps = json.loads(p.read_text())["episodes"]
                    up = [(e["fell_at"] if e["fell_at"] is not None else 20.0) for e in eps]
                    rows[c][f"{m}_{cell}"] = dict(
                        episodes=len(eps), falls=sum(e["fell_at"] is not None for e in eps),
                        fall_times=[e["fell_at"] for e in eps if e["fell_at"] is not None],
                        action_jumps=[e["action_jumps"] for e in eps],
                        jumps_per_10s=[round(e["action_jumps"] / max(u, 0.5) * 10, 1) for e, u in zip(eps, up)],
                        max_tilt=[e["max_tilt"] for e in eps])
            print(c, " | ".join(f"{k}: falls {v['falls']}/{v['episodes']} at {v['fall_times']} jumps/10s {v['jumps_per_10s']}"
                                for k, v in rows[c].items() if isinstance(v, dict) and "falls" in v))
        (TRAIN / "out/chatter").mkdir(parents=True, exist_ok=True)
        (TRAIN / f"out/chatter/gap_{sset}.json").write_text(json.dumps(rows, indent=1))
