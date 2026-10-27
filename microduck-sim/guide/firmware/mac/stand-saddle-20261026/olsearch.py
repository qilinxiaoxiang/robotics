"""Open-loop stand with the A7Z on the roof saddle (2026-10-26). Robot: entering the open-loop stand (NEUTRAL, KP 400)
from stand61 leaned back to 10 deg in 2 s while the neck went from stand61's -0.03 to NEUTRAL's +0.35 (neck back).
Each case starts from stand61's measured pose (stand61_real_1026.json, mean of 96 telemetry rows, Mac mini bridge
history), ramps 2 s to the candidate as walk_brain does, holds T s on the cmu plugged manifest (microduck_rl
1f2ab62c, saddle D-022) with the whole-robot COM moved dx mm (comsim pair). Sim only.

  ~/.venvs/microduck-dyn/bin/python olsearch.py <stage> [--workers N]   -> results/<stage>.jsonl
"""
import argparse, json, multiprocessing as mp, os, sys

SIM_PYTHON = os.path.expanduser("~/.venvs/microduck-dyn/bin/python")
if os.path.realpath(sys.prefix) != os.path.realpath(os.path.dirname(os.path.dirname(SIM_PYTHON))):
    os.execv(SIM_PYTHON, [SIM_PYTHON, os.path.abspath(__file__)] + sys.argv[1:])
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "stand-gap-20261021"))
RES = os.path.join(HERE, "results")
MANIFEST = os.path.join(HERE, "..", "..", "..", "..", "microduck_rl", "cmu", "model", "manifests", "plugged.json")
S61 = json.load(open(os.path.join(HERE, "stand61_real_1026.json")))
HEAD = ("neck_pitch", "head_pitch", "head_yaw", "head_roll")


def candidates():
    import comsim
    N = comsim.S.NEUTRAL
    return {
        "A_neutral": dict(N),
        "B_neck61": dict(N, neck_pitch=S61["neck_pitch"]),
        "C_head61": dict(N, **{k: S61[k] for k in ("neck_pitch", "head_pitch")}),
        "D_stand61": dict(S61),
    }


def job(spec):
    import comsim
    comsim.S.MANIFEST = os.path.abspath(MANIFEST)
    label, pose, dx, kw = spec
    r = comsim.run(pose, dx, start=dict(S61), **kw)
    tr = r.pop("trace") or []
    r.update(label=label, dx_mm=dx, pose=pose, pitch_trace=[(round(t, 2), round(p, 2)) for t, _, p, _ in tr[::10]])
    r.pop("start", None)
    return r


def specs(stage):
    if stage == "base":
        return [(k, p, dx, dict(T=60)) for k, p in candidates().items() for dx in (0.0, -1.0, -2.0)]
    if stage == "neck":   # neck forward only, legs and head at NEUTRAL, over the calibrated COM range
        import comsim
        N = comsim.S.NEUTRAL
        return [(f"neck{n:+.2f}", dict(N, neck_pitch=n), dx, dict(T=60))
                for n in (0.35, 0.25, 0.15, 0.05) for dx in (-1.0, -2.0, -3.0, -4.0)]
    if stage == "robust":  # the neck values around the hold band, wider COM range, pushes and a slippery floor at -3 mm
        import comsim
        N = comsim.S.NEUTRAL
        out = []
        for n in (0.20, 0.25, 0.30):
            p = dict(N, neck_pitch=n)
            out += [(f"neck{n:+.2f}", p, dx, dict(T=60)) for dx in (0.0, -1.0, -2.0, -3.0, -4.0, -5.0)]
            out += [(f"neck{n:+.2f} push{dv:+.1f}", p, -3.0, dict(T=40, push=(20.0, dv))) for dv in (0.1, -0.1)]
            out.append((f"neck{n:+.2f} mu0.4", p, -3.0, dict(T=60, friction=0.4)))
        return out
    if stage == "mid":     # neck 0.225, between the 0.20 and 0.25 bands, finer COM steps
        import comsim
        p = dict(comsim.S.NEUTRAL, neck_pitch=0.225)
        out = [("neck+0.225", p, dx, dict(T=60)) for dx in (-0.5, -1.0, -1.5, -2.0, -3.0, -4.0, -4.5, -5.0, -5.5)]
        out += [(f"neck+0.225 push{dv:+.1f}", p, dx, dict(T=40, push=(20.0, dv))) for dv in (0.1, -0.1) for dx in (-3.0, -4.5)]
        out.append(("neck+0.225 mu0.4", p, -3.0, dict(T=60, friction=0.4)))
        return out
    if stage == "v135":    # the manifest with the V1.35 saddle, 6530B and camera lead: recalibrate NEUTRAL's fall, recheck neck 0.25
        import comsim
        N = comsim.S.NEUTRAL
        out = [("A_neutral", dict(N), dx, dict(T=60)) for dx in (0.0, -1.0, -1.5, -2.0, -2.5, -3.0)]
        out += [("neck+0.25", dict(N, neck_pitch=0.25), dx, dict(T=60)) for dx in (0.0, -1.0, -2.0, -3.0, -4.0, -5.0)]
        return out
    if stage == "v135b":   # finer: the calibrated band -2..-2.5 mm sits on neck 0.25's toe-rest/flat edge; 0.275 and 0.30 beside it
        import comsim
        N = comsim.S.NEUTRAL
        out = [("A_neutral", dict(N), dx, dict(T=60)) for dx in (-1.25, -1.75, -2.25)]
        out += [(f"neck{n:+.3f}", dict(N, neck_pitch=n), dx, dict(T=60)) for n in (0.25, 0.275, 0.30)
                for dx in (-1.5, -2.0, -2.25, -2.5, -2.75, -3.0, -3.5)]
        return out
    if stage == "v135push":  # neck 0.25 at the recalibrated COM: both 0.1 m/s pushes and friction 0.4
        import comsim
        p = dict(comsim.S.NEUTRAL, neck_pitch=0.25)
        out = [(f"neck+0.25 push{dv:+.1f}", p, dx, dict(T=40, push=(20.0, dv))) for dv in (0.1, -0.1) for dx in (-2.25, -2.5)]
        out += [("neck+0.25 mu0.4", p, dx, dict(T=40, friction=0.4)) for dx in (-2.25, -2.5)]
        return out
    if stage == "takeover":  # walk mode at zero command (stand61) takes over after 8 s of open-loop stand, 12 s of walk mode
        import comsim
        N = comsim.S.NEUTRAL
        return [(k, p, dx, dict(T=20, walk_at=8.0, walk_s=12.0)) for k, p in
                (("A_neutral", dict(N)), ("neck+0.25", dict(N, neck_pitch=0.25))) for dx in (-1.0, -3.0, -4.0)]
    raise SystemExit(f"unknown stage {stage}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    os.makedirs(RES, exist_ok=True)
    out = os.path.join(RES, a.stage + ".jsonl")
    with mp.get_context("spawn").Pool(a.workers) as pool, open(out, "w") as f:
        for r in pool.imap_unordered(job, specs(a.stage)):
            f.write(json.dumps(r) + "\n"); f.flush()
            print(r["label"], r["dx_mm"], "fell", r.get("fell_at"), "end", r.get("end_pitch"), "max5", r.get("max_tilt_after_5s"), flush=True)
