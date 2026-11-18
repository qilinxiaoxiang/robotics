"""Round 2: write a flight_eval_modal.py spec for the selection of student checkpoints on Modal CPU containers.

  python3 train/ts2_modal_spec.py <tag> <ckpt dir> [<ckpt dir> ...]   ->  train/eval/spec_<tag>.json
  modal run train/flight_eval_modal.py --spec train/eval/spec_<tag>.json
  python3 train/ts2_modal_spec.py --table <ckpt dir> [...]            ->  one line per dir from the result files

Cells per directory (same flags as ts2_pick.py and ts2_bcheck.py on the Mac mini, seeds 0 to 19):
  five selection cases   none | nobatt | full | comx | shove            -> eval/pk_<dir>_<case>.json
  drops off              comx, shove with --drop 0                       -> eval/bc_<dir>_<case>_nodrop.json
Existing result files are skipped, so Mac mini results and Modal results share one set of names. Parity check
2026-11-18 (s2c_132, Modal against the Mac mini): base COM x 11 against 12 of 20, shove 6 against 5, drops off 0 / 0 on
both; borderline episodes differ by about one in twenty between the two hosts.
Acceptance for a student: 0 falls wanted in all seven cells; the two delay switches are not required because teacher
A-999 itself falls 20/20 with one tick of delay removed.
"""
import json
import sys
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
SEL = [("none", "none", 0.0, []), ("nobatt", "nobatt", 0.0, ["--stand-s", "0"]), ("full", "load100", 0.0, ["--stand-s", "0"]),
       ("comx", "comx+10", 0.0, ["--stand-s", "0"]), ("shove", "nominal", 0.5, ["--stand-s", "0"])]
ND = [c for c in SEL if c[0] in ("comx", "shove")]


def cells(d):
    for name, man, sh, extra in SEL:
        yield f"pk_{d}_{name}", man, sh, extra
    for name, man, sh, extra in ND:
        yield f"bc_{d}_{name}_nodrop", man, sh, extra + ["--drop", "0"]


def falls(name):
    p = TRAIN / f"eval/{name}.json"
    if not p.exists():
        return None
    s = json.loads(p.read_text())["summary"]
    return None if s.get("incomplete") else s["falls"]


if sys.argv[1] == "--table":
    rows = []
    for d in sys.argv[2:]:
        f = [falls(n) for n, *_ in cells(d)]
        tot = sum(x for x in f if x is not None)
        rows.append((tot if None not in f else 999, d, f))
        print(f"{d:10s} sel {f[:5]} = {sum(x or 0 for x in f[:5]) if None not in f[:5] else 'missing'}; drops off {f[5:]}; "
              f"all seven {tot if None not in f else 'missing'}")
    rows.sort()
    print("best:", [(d, t) for t, d, _ in rows[:4]])
else:
    tag, dirs = sys.argv[1], sys.argv[2:]
    evals = []
    for d in dirs:
        assert (TRAIN / f"ckpt/{d}/walk61.onnx").exists(), f"ckpt/{d}/walk61.onnx missing"
        for name, man, sh, extra in cells(d):
            if falls(name) is None:
                evals.append(dict(name=name, models=f"ckpt/{d}", manifest=f"manifests/flightpack-{man}.json", case="walk",
                                  episodes=20, shove_ns=sh, shove_at=8.0, extra=extra))
    out = TRAIN / f"eval/spec_{tag}.json"
    out.write_text(json.dumps(dict(evals=evals), indent=1))
    n = len(evals) * 20
    print(f"{out}: {len(evals)} evals, {n} episodes, about {n / 60 * (0.0473 + 0.008):.2f} USD at one core-minute each")
