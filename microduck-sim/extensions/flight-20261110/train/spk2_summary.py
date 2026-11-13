"""Summarise the spk2 pre-launch checks (spk2_prelaunch.sh) into out/spk2_prelaunch_summary.json and print them.

cliff: seepick61 in the training env (1.47 A, 7.2-8.2 V) at whole-pack scale s, 256 episodes: held at the episode end
       (grasp_state held in the last step, the measure the curriculum counts), success (held >= 0.4 s), falls, and the
       held rate relative to s = 0 (what the curriculum's FRAC is compared with).
fall-early audit, per s: full-episode returns (the 4 s window is the training episode; a fallen env earns nothing after
       the fall):
         fall at 0.7 s   seepick61's mean return accumulated by 0.7 s (the policy that falls right after the bow starts)
         stand still     the fq2 stander, episodes that did not fall, to the end
         held pick       seepick61's successful episodes at that s when there are at least 5, else the carried
                         seepick61's (the pack weight taken by an upward force: what a pick that copes earns)
       verdict: falling early beats standing still when fall_at_0.7 > stand_still.
  python3 train/spk2_summary.py [TAG]     (TAG = the audit file suffix, e.g. _fp2 for the after-fix audit)
"""
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "out"
SCALES = ("0.00", "0.02", "0.05", "0.10", "0.15", "0.20", "0.50", "1.00")


def _returns(c):
    """episode_return and return_at_s from the per-env lists (a single run's file has only those; the merge in
    seeing_pack_check.py computes the same), plus the mean return of the episodes that fell"""
    if "per_env" not in c:   # a merged file: the fallen mean from the totals
        e, n = c["episode_return"], c["envs"]
        nf = n - e["n_not_fallen"]
        e["fallen"] = round((e["all"] * n - (e["not_fallen"] or 0) * e["n_not_fallen"]) / nf, 4) if nf else None
        return c
    pe, n = c["per_env"], len(c["per_env"]["ret"])
    mean = lambda idx: round(sum(pe["ret"][i] for i in idx) / len(idx), 4) if idx else None  # noqa: E731
    alive = [i for i in range(n) if not pe["fell"][i]]
    c.setdefault("episode_return", dict(all=mean(range(n)), success=mean([i for i in range(n) if pe["success"][i]]),
                                        not_fallen=mean(alive), n_not_fallen=len(alive)))
    c["episode_return"]["fallen"] = mean([i for i in range(n) if pe["fell"][i]])
    if "ret_t" in pe:
        c.setdefault("return_at_s", {t: round(sum(v) / n, 4) for t, v in pe["ret_t"].items()})
    return c


def load(p):
    return {k: _returns(v) for k, v in json.loads(p.read_text())["cases"].items()} if p.exists() else {}


def main():
    tag = sys.argv[1] if len(sys.argv) > 1 else ""
    res = dict(cliff={}, audit={})
    base = None
    for s in SCALES:
        c = load(OUT / f"spk_cliff_none_s{s}.json").get("seepick")
        if not c:
            continue
        r = dict(envs=c["envs"], held_end=c["held_end"], success=c["success"], falls=c["falls"],
                 held_rate=round(c["held_end"] / c["envs"], 4), fall_time_s=c.get("fall_time_s"),
                 payload_kg=c["payload_kg"], leg_pitch_p99_Nm=c["leg_pitch_p99_Nm_max_of_parts"],
                 at_clamp=c["leg_pitch_at_clamp_frac_env_weighted"],
                 return_at_s=c.get("return_at_s"), episode_return=c.get("episode_return"))
        if s == "0.00":
            base = r["held_rate"]
        r["held_vs_s0"] = round(r["held_rate"] / base, 3) if base else None
        res["cliff"][s] = r
    for s in SCALES:
        a = load(OUT / f"spk_fea{tag}_none_s{s}.json")
        # an audit file with its own seepick61 run (the Modal route, and every after-fix audit) is used on its own
        # draws; otherwise the cliff file's
        cl = a.get("seepick") or load(OUT / f"spk_cliff_none_s{s}.json").get("seepick")
        if not a or not cl:
            continue
        fq2, car = a.get("fq2"), a.get("carried")
        own = cl["episode_return"]["success"] if cl["success"] >= 5 else None
        held = own if own is not None else (car or {}).get("episode_return", {}).get("success")
        fall07 = cl.get("return_at_s", {}).get("0.7")
        stand = fq2["episode_return"]["not_fallen"] if fq2 else None
        r = dict(fall_at_0p7=fall07, stand_still=stand, stand_still_n=fq2["episode_return"]["n_not_fallen"] if fq2 else None,
                 stand_all=fq2["episode_return"]["all"] if fq2 else None, held_pick=held,
                 held_pick_from="seepick61 successes" if own is not None else "carried seepick61 successes",
                 start_policy_return=cl["episode_return"]["all"], start_policy_falls=cl["falls"], envs=cl["envs"])
        r["falling_beats_standing"] = (fall07 is not None and stand is not None and fall07 > stand)
        res["audit"][s] = r
    (OUT / f"spk2_prelaunch_summary{tag}.json").write_text(json.dumps(res, indent=1) + "\n")
    # control (Modal, seed 1, 256 episodes each): pinned no-pack load (spk1's path) against s = 0 (spk2's path)
    for k in ("none", "s0.00"):
        ctl = load(OUT / f"spk_ctl_none_{k}.json").get("seepick")
        if ctl:
            res.setdefault("control", {})[k] = dict(envs=ctl["envs"], held_end=ctl["held_end"], success=ctl["success"],
                                                    falls=ctl["falls"])
            print(f"control {k}: held {ctl['held_end']}/{ctl['envs']}, success {ctl['success']}, falls {ctl['falls']}")
    (OUT / f"spk2_prelaunch_summary{tag}.json").write_text(json.dumps(res, indent=1) + "\n")
    for s, r in res["cliff"].items():
        print(f"cliff s={s} ({r['payload_kg']} kg): held {r['held_end']}/{r['envs']} = {r['held_rate']} "
              f"(x{r['held_vs_s0']} of s=0), success {r['success']}, falls {r['falls']}, fall t {r['fall_time_s']}, "
              f"p99 {r['leg_pitch_p99_Nm']}")
    for s, r in res["audit"].items():
        print(f"audit s={s}: fall@0.7 {r['fall_at_0p7']} | stand still {r['stand_still']} (n {r['stand_still_n']}, "
              f"all {r['stand_all']}) | held pick {r['held_pick']} ({r['held_pick_from']}) | start policy "
              f"{r['start_policy_return']} | falling beats standing: {r['falling_beats_standing']}")


if __name__ == "__main__":
    main()
