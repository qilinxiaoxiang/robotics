"""Score the bend acceptance (BEND-PLAN.md section 6) for a models dir from the two probes accept_bend.sh writes.

  python3 train/score_bend.py <models dir> [--ref bend_gp61ref]
Inputs: eval/st_<R>_gp_<load>.json (runtime sim, style_eval stand case with the PICKUP command; falls over the whole
episode, which runs 3 s past the hand-back, and per-joint torque p99) and eval/bendaccept_<R>_<env load>.json (training
env: mouth tip height and trunk pitch over the hold, leg pose at the lowest mouth sample, hand-back, p99).
Lines per load (full pack, batteries out, no pack):
  falls: at least 18 of 20 without a fall, rise and hand-back included (runtime probe)
  mouth: every episode that reached the hold has its median mouth tip height within 3 cm of the floor (training env)
  trunk pitch: every such episode has its median trunk pitch in 25-45 deg (training env)
  hip pitch, knee, ankle torque p99 at most 0.50 N m each (runtime probe; the training-env value is shown too)
Writes out/accept_bend_<R>.json.
"""
import argparse
import json
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
LOADS = (("full", "load100", "full"), ("batteries out", "nobatt", "nobatt"), ("no pack", "load000", "none"))


def read(p):
    p = TRAIN / p
    return json.loads(p.read_text()) if p.exists() else None


def joint_max(jp, key):
    v = [x for k, x in (jp or {}).items() if key in k]
    return max(v) if v else None


def lines_for(R):
    out = []

    def line(name, ok, detail):
        out.append(dict(line=name, result="MISSING" if ok is None else ("PASS" if ok else "FAIL"), detail=detail))
    for label, rt_load, env_load in LOADS:
        rt = read(f"eval/st_{R}_gp_{rt_load}.json")
        ev = read(f"eval/bendaccept_{R}_{env_load}.json")
        rs = rt["summary"] if rt else None
        es = ev["summary"] if ev else None
        if rs:
            nf = rs["episodes"] - rs["falls"]
            line(f"{label}: at least 18 of 20 without a fall incl. rise and hand-back (runtime)", nf >= 18,
                 f"{nf} of {rs['episodes']} without a fall, fall times {rs.get('fall_times', [])[:8]}")
        else:
            line(f"{label}: at least 18 of 20 without a fall incl. rise and hand-back (runtime)", None, "no runtime result")
        if es:
            held = [e for e in ev["episodes"] if e.get("mouth_median_m") is not None]
            nm = sum(e["mouth_median_m"] <= 0.03 for e in held)
            npi = sum(25 <= e["pitch_median_deg"] <= 45 for e in held)
            line(f"{label}: mouth within 3 cm of the floor at the hold (training env)", bool(held) and nm == len(held),
                 f"{nm} of {len(held)} held episodes, median {es['mouth_median_m']} m, max {es['mouth_max_m']} m; "
                 f"env falls {es['falls']} of {es['envs']}, handed back {sum(e['handed_back'] for e in ev['episodes'])}")
            line(f"{label}: trunk pitch 25-45 deg at the hold (training env)", bool(held) and npi == len(held),
                 f"{npi} of {len(held)} held episodes, median {es['pitch_median_deg']} deg")
        else:
            for n in ("mouth within 3 cm of the floor at the hold", "trunk pitch 25-45 deg at the hold"):
                line(f"{label}: {n} (training env)", None, "no training-env result")
        for j, key in (("hip pitch", "hip_pitch"), ("knee", "knee"), ("ankle", "ankle")):
            v = joint_max(rs.get("joint_p99_nm") if rs else None, key)
            ve = joint_max({k: x["p99"] for k, x in ev["per_actuator"].items()} if ev else None, key)
            extra = f"; knee angle at the lowest mouth, median |q| {es.get('knee_abs_at_low_median')} rad" \
                if key == "knee" and es else ""
            line(f"{label}: {j} torque p99 at most 0.50 N m (runtime)", None if v is None else v <= 0.50,
                 f"runtime {v}, training env {ve}{extra}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("models")
    ap.add_argument("--ref", default="bend_gp61ref")
    a = ap.parse_args()
    lines = lines_for(a.models)
    ref = {ln["line"]: ln for ln in lines_for(a.ref)}
    for ln in lines:
        r = ref.get(ln["line"])
        ln["ref"] = f"{r['result']} {r['detail']}" if r else None
    verdict = "PASS" if all(ln["result"] == "PASS" for ln in lines) else "FAIL"
    (TRAIN / f"out/accept_bend_{a.models}.json").write_text(
        json.dumps(dict(models=a.models, ref=a.ref, verdict=verdict, lines=lines), indent=1))
    for ln in lines:
        print(f"{ln['result']:7s} {ln['line']}: {ln['detail']}  || {a.ref}: {ln['ref']}")
    print(f"verdict {verdict}")


if __name__ == "__main__":
    main()
