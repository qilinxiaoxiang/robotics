"""Seeing-pick gap study (2026-10-29): the ball numbers Shawn asked for, from results/<stage>.jsonl.

Per stage (ball rows only unless --all): train-measure / held at hand-back / held 3 s after; when and with which half the
beak first touched the ball; how far the ball travelled between first touch and pinch; its travel over the trained close
window (phase 0.34 -> 0.40) and whether it was pinched at 0.40; how often --sp-close-on-contact fired. The contact fields
exist only in rows written after the 2026-10-29 harness change (ball_baseline and later stages).

  python3 levers.py                      # ball rows of every stage that has them
  python3 levers.py --all                # every shape
  python3 levers.py --stages lip_mu110 lip_mu050 lip_mu035 ball_baseline
"""
import argparse
import json
import os
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
SUCCESS_TICKS = 20


def med(xs, nd=1):
    xs = [x for x in xs if x is not None]
    return None if not xs else (round(st.median(xs), nd), round(min(xs), nd), round(max(xs), nd))


def stage_numbers(rows):
    ok = [r for r in rows if r.get("error") is None and "result" in r]
    sp = [r["result"]["seepick"] for r in ok]
    ev = [s["events"] for s in sp]
    out = dict(runs=len(rows), errors=len(rows) - len(ok),
               train=sum(e.get("held_ticks", 0) >= SUCCESS_TICKS for e in ev),
               hand_back=sum(bool(s["at_handback"] and s["at_handback"]["held"]) for s in sp),
               end=sum(bool(s.get("at_end") and s["at_end"]["held"]) for s in sp),
               pinched_ever=sum(e["first_pinched_t"] is not None for e in ev),
               fell=sum(r["result"].get("fell_at") is not None for r in ok))
    fc = [e.get("first_contact") for e in ev]
    if any(fc):
        have = [x for x in fc if x]
        out["first_contact"] = dict(
            runs_with_contact=len(have),
            phase_median_min_max=med([x["phase"] for x in have], 3),
            before_close_start=sum(x["phase"] is not None and x["phase"] < 0.34 for x in have),
            which={w: sum(x["which"] == w for x in have) for w in ("jaw", "upper", "both")},
            jaw_opening_deg_median_min_max=med([x["jaw_measured_deg"] for x in have]))
        push = [e.get("push_contact_to_pinch_mm") for e in ev if e.get("push_contact_to_pinch_mm")]
        out["touch_to_pinch"] = dict(runs=len(push), s_median_min_max=med([p["s"] for p in push], 2))
        cw = [e.get("close_window") for e in ev if e.get("close_window")]
        out["close_window_034_to_040"] = dict(runs=len(cw), pinched_at_040=sum(c["pinched"] for c in cw))
        for frame in ("world", "rel_pad", "foot"):  # rows written after the world/rel_pad fields were added
            k = frame + "_mm"
            if any(k in p for p in push):
                out["touch_to_pinch"][frame] = dict(
                    x_mm_median_min_max=med([p[k]["x"] for p in push if k in p]),
                    y_mm_median_min_max=med([p[k]["y"] for p in push if k in p]),
                    travel_mm_median_min_max=med([p[k]["norm"] for p in push if k in p]))
            if any(k in c for c in cw):
                out["close_window_034_to_040"][frame] = dict(
                    x_mm_median_min_max=med([c[k]["x"] for c in cw if k in c]),
                    y_mm_median_min_max=med([c[k]["y"] for c in cw if k in c]),
                    travel_mm_median_min_max=med([c[k]["norm"] for c in cw if k in c]),
                    over_10mm=sum(c[k]["norm"] > 10 for c in cw if k in c))
        cc = [e.get("contact_close") for e in ev if e.get("contact_close")]
        out["close_on_contact_fired"] = dict(runs=len(cc), advance_s_median_min_max=med([c["advance_s"] for c in cc], 2))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="every shape, not only the ball")
    ap.add_argument("--stages", nargs="*", default=None)
    a = ap.parse_args()
    res = os.path.join(HERE, "results")
    stages = a.stages or sorted(f[:-6] for f in os.listdir(res) if f.endswith(".jsonl") and f != "train_eval.jsonl")
    out = {}
    for stg in stages:
        rows = [json.loads(x) for x in open(os.path.join(res, f"{stg}.jsonl"))]
        if not a.all:
            rows = [r for r in rows if r.get("shape") == "ball"]
        if rows:
            out[stg] = stage_numbers(rows)
    print(json.dumps(out, indent=1))
    json.dump(out, open(os.path.join(res, "levers_all.json" if a.all else "levers_ball.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
