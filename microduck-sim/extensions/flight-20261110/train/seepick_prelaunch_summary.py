"""Summarise the seeing-pick pack pre-launch checks (seepick_prelaunch.sh) into out/spk_prelaunch_summary.json and print it.

start: seepick61 in the fine-tune's env per base model and load, beside the runtime-sim pickup numbers (FP-R7 status,
train/eval/pk_*.json). audit: reward per second of the degenerate policies at each load, against seepick61 as is and
against seepick61 with the pack weight carried by an upward force (what a policy that copes with the pack could earn).
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
# runtime-sim pickup test, 20 seeds per case, held at the hand-back (REQUIREMENTS.json FP-R7 status, 2026-11-12)
RUNTIME = {"none": "ball 11/20 held, box 14/20, 0 falls (original stander); ball 15/20, box 16/20, 1 fall (fq2)",
           "nobatt": "0/20 held, 20/20 falls, ball and box", "full": "0/20 held, 20/20 falls, ball and box"}
KEYS = ("envs", "success", "held_end", "falls", "tilt_over_55", "reward_per_s", "fail_reward_per_s")


def case(path, name):
    c = json.loads(path.read_text())["cases"][name]
    r = {k: c.get(k) for k in KEYS}
    r["success_reward_per_s"] = c.get("success_reward_per_s", c.get("succ_reward_per_s"))
    r["fall_time_median_s"] = (c.get("fall_time_s") or {}).get("median")
    r["leg_pitch_p99_Nm"] = c.get("leg_pitch_p99_Nm_max_of_parts")
    return r


def main():
    s = {"start": {}, "audit": {}}
    for base in ("none", "plugged"):
        for load in ("none", "nobatt", "full"):
            p = OUT / f"spk_start_{base}_{load}.json"
            if p.exists():
                s["start"][f"{base}/{load}"] = dict(case(p, "seepick"), runtime_sim=RUNTIME[load])
    for load in ("none", "nobatt", "full"):
        row = {"seepick61": s["start"].get(f"none/{load}")}
        for c in ("stand61", "fq2", "blind", "carried"):
            p = OUT / f"spk_audit_{c}_none_{load}.json"
            if p.exists():
                row[c] = case(p, c)
        s["audit"][load] = row
    (OUT / "spk_prelaunch_summary.json").write_text(json.dumps(s, indent=1))
    for k, v in s["start"].items():
        print(f"start {k:15s} success {v['success']}/{v['envs']} held_end {v['held_end']} falls {v['falls']} "
              f"reward/s {v['reward_per_s']}  | runtime sim: {v['runtime_sim']}")
    for load, row in s["audit"].items():
        print(f"audit {load:7s} " + "  ".join(f"{c} {r['reward_per_s']}/s ({r['success']} ok, {r['falls']} falls of {r['envs']})"
                                              for c, r in row.items() if r))


if __name__ == "__main__":
    main()
