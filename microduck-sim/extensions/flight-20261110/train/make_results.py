"""Collect the final comparison into train/out/results.json from the eval files (no number is typed by hand).

  python3 train/make_results.py --chosen fq1_1500 --baseline baseline0 [--also fw1_1250 fq2_1000 ...]
Per case: falls / episodes, fall times, median upright speed, leg force p99 (median over upright episodes), share of
steps at >= 95 % of the 0.538 N m clamp (max over upright episodes), max tilt; and the with-pack fall total with the
walk cases below 0.03 m/s (the choice rule) listed. Refuses an eval marked incomplete.
"""
import argparse
import json
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
CASES = ["nominal_stand", "nominal_walk", "nominal_turnL", "nominal_turnR", "mass+10_stand", "mass+10_walk",
         "comx+10_stand", "comx+10_walk", "comx-10_stand", "comx-10_walk", "nominal_stand_shove05",
         "nominal_walk_shove05", "nominal_stand_landing", "nominal_walk_landing",
         "nopack_stand", "nopack_walk", "nopack_turnL", "nopack_turnR"]
MOVING = ("walk",)


def policy_block(prefix):
    out, pack_falls, slow = {}, 0, []
    for c in CASES:
        f = TRAIN / "eval" / f"{prefix}_{c}.json"
        s = json.loads(f.read_text())["summary"]
        if s.get("incomplete") or s["episodes"] < s.get("episodes_planned", 20):
            raise SystemExit(f"{f.name}: incomplete ({s['episodes']} episodes)")
        out[c] = dict(falls=s["falls"], episodes=s["episodes"], fall_times=s["fall_times"],
                      speed_median_upright=s["speed_median_upright"],
                      leg_force_p99_nm=s.get("leg_force_p99_nm_upright_median"),
                      sat_frac_max=s.get("leg_force_sat_frac_upright_max"), max_tilt=s["max_tilt"], file=f"eval/{f.name}")
        if not c.startswith("nopack"):
            pack_falls += s["falls"]
            if "walk" in c and (s["speed_median_upright"] is None or s["speed_median_upright"] < 0.03):
                slow.append(c)
    return dict(cases=out, pack_falls_total=pack_falls, pack_cases=14, walk_cases_below_0_03=slow)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chosen", required=True)
    ap.add_argument("--baseline", default="baseline0")
    ap.add_argument("--also", nargs="*", default=[])
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    res = dict(probe="brain_sim_check.py --model asbuilt --volt 7.6 --drop 0.036, policy from the first tick (--stand-s 0), "
                     "20 episodes x 20 s per case; walk vx 0.25 from 2 s for 15 s; turns vtheta +-0.3; shove 0.5 N s at 8 s; "
                     "landing = released 2-3 cm up with +-5 deg tilt",
               limit_nm=0.538, chosen=a.chosen, note=a.note,
               policies={p: policy_block(p) for p in [a.chosen, a.baseline] + a.also})
    out = TRAIN / "out" / "results.json"
    out.write_text(json.dumps(res, indent=1))
    for p, b in res["policies"].items():
        print(p, "pack falls", b["pack_falls_total"], "of", 14 * 20, "slow walk cases", b["walk_cases_below_0_03"])
    print("wrote", out)


if __name__ == "__main__":
    main()
