"""Summarise the spk3 pre-launch checks (microduck_rl-grasp/cmu/grasp/spk3_check_modal.py, files in out/spk3/) into
out/spk3/spk3_prelaunch_summary.json and print them.

jaw     training-env jaw angle (deg, mean over 256 envs, s = 0, ball) at close phases 0.36-0.45 against the runtime sim's
        20.2 / 17.4 / 11.1 / 3.5 deg at 0.36 / 0.38 / 0.40 / 0.42 (spk2 diagnosis, runtime traces)
floor   no-pack (s = 0) held-at-end rate in the training placement (window 0.04, kicks, distractors), with exploration
        noise (the curriculum's in-run measure) and deterministic: seepick61 (sp-b-1027 model_2500.pt) and spk2's
        model_best, fast (spk2) jaw and matched (spk3) jaw
start   spk2 model_best under the matched jaw, check placement (window 0.03), deterministic, at s = 0 / 0.10 / 0.25 /
        0.50 / 1.00
audit   per s: return of falling at 0.7 s, of the fq2 stander standing still, of a held pick (spk2_summary.py's rule)
  python3 train/spk3_summary.py
"""
import json
from pathlib import Path

import spk2_summary as S2

OUT = Path(__file__).resolve().parent / "out" / "spk3"
RUNTIME_DEG = {"0.36": 20.2, "0.38": 17.4, "0.40": 11.1, "0.42": 3.5}
PH = ("0.36", "0.38", "0.40", "0.42", "0.45")


def load(name):
    p = OUT / f"{name}.json"
    return {k: S2._returns(v) for k, v in json.loads(p.read_text())["cases"].items()} if p.exists() else {}


def main():
    res = dict(jaw={}, floor={}, start={}, audit={})
    for p in sorted(OUT.glob("jaw_*.json")):
        d = json.loads(p.read_text())
        res["jaw"][p.stem] = dict(deg={ph: round(d[f"jaw_deg_at_{ph}"]["mean"], 2) for ph in PH},
                                  sd={ph: round(d[f"jaw_deg_at_{ph}"]["sd"], 2) for ph in PH},
                                  minus_runtime={ph: round(d[f"jaw_deg_at_{ph}"]["mean"] - v, 2)
                                                 for ph, v in RUNTIME_DEG.items()},
                                  lip_mm={ph: round(d[f"lip_m_at_{ph}"]["mean"] * 1000, 1) for ph in PH},
                                  held_end=d["held_at_end"], success=d["success"], falls=d["falls"], envs=d["envs"],
                                  jaw=dict(matched=d["jaw_matched"], kp=d["jaw_kp"], effort=d["jaw_effort"],
                                           damping=d["jaw_damping"]))
    for pol in ("s61", "best"):
        for jaw in ("fast", "matched"):
            for mode in ("noise", "det"):
                c = load(f"floor_{pol}_{jaw}_{mode}").get("seepick")
                if c:
                    res["floor"][f"{pol}_{jaw}_{mode}"] = dict(held_rate=round(c["held_end"] / c["envs"], 4),
                                                               held_end=c["held_end"], success=c["success"],
                                                               falls=c["falls"], envs=c["envs"])
    for s in ("0.00", "0.10", "0.25", "0.50", "1.00"):
        a = load(f"spk_fea_spk3_none_s{s}")
        cl, fq2, car = a.get("seepick"), a.get("fq2"), a.get("carried")
        if not cl:
            continue
        res["start"][s] = dict(held_end=cl["held_end"], held_rate=round(cl["held_end"] / cl["envs"], 4),
                               success=cl["success"], falls=cl["falls"], envs=cl["envs"])
        own = cl["episode_return"]["success"] if cl["success"] >= 5 else None
        held = own if own is not None else (car or {}).get("episode_return", {}).get("success")
        fall07 = cl.get("return_at_s", {}).get("0.7")
        stand = fq2["episode_return"]["not_fallen"] if fq2 else None
        res["audit"][s] = dict(fall_at_0p7=fall07, stand_still=stand,
                               stand_still_n=fq2["episode_return"]["n_not_fallen"] if fq2 else None,
                               held_pick=held, held_pick_from="start policy successes" if own is not None
                               else "carried start policy successes",
                               start_policy_return=cl["episode_return"]["all"],
                               falling_beats_standing=fall07 is not None and stand is not None and fall07 > stand,
                               held_beats_standing=held is not None and stand is not None and held > stand)
    (OUT / "spk3_prelaunch_summary.json").write_text(json.dumps(res, indent=1) + "\n")
    for k, r in res["jaw"].items():
        print(f"jaw {k}: deg {r['deg']} minus runtime {r['minus_runtime']} lip mm {r['lip_mm']} held "
              f"{r['held_end']}/{r['envs']} falls {r['falls']}")
    for k, r in res["floor"].items():
        print(f"floor {k}: held {r['held_end']}/{r['envs']} = {r['held_rate']}, success {r['success']}, falls {r['falls']}")
    for s, r in res["start"].items():
        print(f"start s={s}: held {r['held_end']}/{r['envs']} = {r['held_rate']}, success {r['success']}, falls {r['falls']}")
    for s, r in res["audit"].items():
        print(f"audit s={s}: fall@0.7 {r['fall_at_0p7']} | stand still {r['stand_still']} (n {r['stand_still_n']}) | "
              f"held pick {r['held_pick']} ({r['held_pick_from']}) | start {r['start_policy_return']} | falling beats "
              f"standing {r['falling_beats_standing']} | held beats standing {r['held_beats_standing']}")


if __name__ == "__main__":
    main()
