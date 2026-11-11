"""Write the full evaluation suite spec for one models dir (the brief's list), policy from the first tick (--stand-s 0).

  python3 train/make_suite.py <prefix> <models dir relative to train/> [--episodes 20] -> train/specs/suite_<prefix>.json
Cases: nominal stand/walk/turnL/turnR; mass +10 % and COM x +-10 mm (stand, walk); 0.5 N s shove at 8 s (stand, walk);
landing hand-over (stand, walk); no pack (stand, walk, turnL, turnR). Then: modal run train/flight_eval_modal.py --spec ...
"""
import argparse
import json
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
S0 = ["--stand-s", "0"]  # the runtime's open-loop stand mode alone falls at 0.54 s with the pack (eval/olstand_pack.json)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prefix")
    ap.add_argument("models")
    ap.add_argument("--episodes", type=int, default=20)
    a = ap.parse_args()
    ev = []

    def add(name, manifest, case, **kw):
        ev.append(dict(name=f"{a.prefix}_{name}", models=a.models, manifest=f"manifests/flightpack-{manifest}.json", case=case,
                       episodes=a.episodes, extra=S0, **kw))
    for c in ("stand", "walk", "turnL", "turnR"):
        add(f"nominal_{c}", "nominal", c)
    for m in ("mass+10", "comx+10", "comx-10"):
        for c in ("stand", "walk"):
            add(f"{m}_{c}", m, c)
    for c in ("stand", "walk"):
        add(f"nominal_{c}_shove05", "nominal", c, shove_ns=0.5, shove_at=8.0)
        add(f"nominal_{c}_landing", "nominal", c, landing=True)
    for c in ("stand", "walk", "turnL", "turnR"):
        add(f"nopack_{c}", "none", c)
    out = TRAIN / "specs" / f"suite_{a.prefix}.json"
    out.write_text(json.dumps(dict(evals=ev), indent=1))
    print(out, len(ev), "evals")


if __name__ == "__main__":
    main()
