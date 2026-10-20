"""Aside (outside the kp-400 brief): same open-loop stand at stand KP 800 and 1600 (walk_wired --kp-stand), start a,
head 0/+20/-20 g and a 0.1 m/s backward push, 60 s. Writes results/kp_aside.jsonl. Sim only."""
import json, os, sys, multiprocessing as mp
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import search as SR  # re-execs under the sim venv

def jobs():
    J = []
    for name, dl in (("NEUTRAL", {}), ("knee_back_0.045", SR.back(0, 0, 0.045))):
        for kp in (800, 1600):
            for lbl, kw in (("head+0", {}), ("head+20", dict(head_g=20)), ("head-20", dict(head_g=-20)), ("push back", dict(push=(20, -0.1)))):
                J.append((f"{name} kp{kp} a {lbl}", dl, dict(T=60, kp=kp, **kw)))
    for kp in (800, 1600):  # NEUTRAL only: the remaining perturbations and the real forward start
        for lbl, kw in (("a 120 s", dict(T=120)), ("a f0.4", dict(friction=0.4)), ("a 6.6V", dict(volt=6.6)),
                        ("a head+20 f0.4 push fwd", dict(head_g=20, friction=0.4, push=(20, 0.1))),
                        ("b head+0", dict(start_b=True)), ("b head+20", dict(start_b=True, head_g=20))):
            J.append((f"NEUTRAL kp{kp} {lbl}", {}, dict(dict(T=60, kp=kp), **kw)))
    return J

if __name__ == "__main__":
    with mp.get_context("spawn").Pool(6) as pool, open(os.path.join(HERE, "results", "kp_aside.jsonl"), "w") as f:
        for r in pool.imap(SR.job, jobs()):
            f.write(json.dumps(r) + "\n")
            print(r["label"], "fell", r["fell_at"], "max_after5", r["max_tilt_after_5s"], "end_pitch", r["end_pitch"], flush=True)
