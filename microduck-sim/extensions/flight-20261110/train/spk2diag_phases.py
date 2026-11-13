"""Where runtime-sim pickups fail (pk_* eval files): per file, how many episodes reached the ball (first beak contact),
pinched it, held it at handback and at the end, and fell; with the means at the close step (pad height, tilt, lip
minimum, beak-on-floor force) and how far the ball was pushed between first contact and the close window (world mm).
python3 train/spk2diag_phases.py eval/pk_a.json ..."""
import json
import statistics as st
import sys
from pathlib import Path


def m(v):
    v = [x for x in v if x is not None]
    return round(st.mean(v), 4) if v else None


for f in sys.argv[1:]:
    d = json.loads(Path(f).read_text())
    eps = d["episodes"]
    sp = [e["probe"]["seepick"] for e in eps]
    ev = [s["events"] for s in sp]
    fell = [e["fell_at"] is not None for e in eps]
    contact = [x.get("first_contact") is not None for x in ev]
    pinched = [x.get("first_pinched_t") is not None for x in ev]
    hb = [bool((s.get("at_handback") or {}).get("held")) for s in sp]
    he = [bool((s.get("at_end") or {}).get("held")) for s in sp]
    which = {}
    for x in ev:
        w = (x.get("first_contact") or {}).get("which")
        which[w] = which.get(w, 0) + 1
    ca = [x.get("close_at") or {} for x in ev]
    push = [((x.get("close_window") or {}).get("world_mm") or {}).get("norm") for x in ev]
    fall_t = [round(e["fell_at"] - s["switched_at"], 2) for e, s in zip(eps, sp) if e["fell_at"] is not None]
    # an episode fails at its first missing stage
    stage = {"no contact": 0, "contact, no pinch": 0, "pinch, lost by handback": 0, "held at handback, lost by end": 0,
             "held at end": 0}
    for c, p, h, e in zip(contact, pinched, hb, he):
        k = ("no contact" if not c else "contact, no pinch" if not p else "pinch, lost by handback" if not h
             else "held at handback, lost by end" if not e else "held at end")
        stage[k] += 1
    print(f"{Path(f).stem}: n {len(eps)} | {stage} | falls {sum(fell)} at {sorted(fall_t)} s from switch "
          f"({dict((k, sum(1 for e in eps if e['fell_at'] is not None and e['fall_dir'] == k)) for k in set(e['fall_dir'] for e in eps if e['fell_at'] is not None))}) | "
          f"first contact by {which} | at close: pad z {m([c.get('pad_z_m') for c in ca])} tilt {m([c.get('tilt') for c in ca])} "
          f"obj-pad {[m([(c.get('object_rel_pad_xy') or [None, None])[i] for c in ca]) for i in (0, 1)]} | "
          f"lip min {m([x.get('lip_min_m') for x in ev])} beak floor force max {m([x.get('beak_floor_force_max_n') for x in ev])} N "
          f"| ball pushed contact->close {m(push)} mm")
