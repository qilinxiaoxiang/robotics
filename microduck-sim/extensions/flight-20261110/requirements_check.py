"""Flight-pack requirement coverage check: every requirement Shawn stated must be tied to gate cells and training
conditions that exist in the code, or carry a written reason why it needs none.

  python3 requirements_check.py            # prints one line per requirement, exit 1 if any is uncovered
  python3 requirements_check.py --launch   # same; for launchers: a nonzero exit blocks a training launch

Why it exists (2026-11-20): the round 3 gates (train/ts3_gates.py) were written from the training env's own load
list (no pack, nominal pack), not from what the robot does. The pack is a jet pack: thrust takes the load on the legs
from pack plus body down to zero inside one run. Neither training nor the gates held any thrust for nine days of runs,
and Shawn found it, not a check.

Each requirement in REQUIREMENTS.json carries a "coverage" object:
  gate_cells       names that must appear as quoted strings in train/ts3_gates.py
  train_terms      strings that must appear in the training env sources (TRAIN_SOURCES below)
  not_applicable   a reason of at least 20 characters when the requirement needs neither (hardware, UI, another policy)
A requirement with no coverage object, an empty one, or a listed name that the code does not contain is UNCOVERED.
The check proves that the named cell or term exists in the code. It cannot prove that the cell tests the requirement
well; that is for whoever writes the coverage entry and for review.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATES = HERE / "train" / "ts3_gates.py"
TRAIN_SOURCES = [HERE.parent.parent / "microduck_rl" / "cmu" / "finetune" / "flight" / n
                 for n in ("flight_worker.py", "payload.py", "distill_worker.py", "teacher.py")]


def main():
    reqs = json.loads((HERE / "REQUIREMENTS.json").read_text())["requirements"]
    gates = GATES.read_text()
    train = "\n".join(p.read_text() for p in TRAIN_SOURCES if p.exists())
    bad = 0
    for r in reqs:
        cov = r.get("coverage") or {}
        na = (cov.get("not_applicable") or "").strip()
        cells, terms = cov.get("gate_cells") or [], cov.get("train_terms") or []
        problems = []
        if na:
            if len(na) < 20:
                problems.append("not_applicable reason too short")
        else:
            if not cells:
                problems.append("no gate cell named")
            if not terms:
                problems.append("no training condition named")
            problems += [f"gate cell {c!r} not in ts3_gates.py" for c in cells if f'"{c}"' not in gates]
            problems += [f"training term {t!r} not in the env sources" for t in terms if t not in train]
        state = "UNCOVERED" if problems else ("n/a" if na else "covered")
        bad += bool(problems)
        print(f"{state:9s} {r['id']}: {r['meaning'][:90]}")
        for p in problems:
            print(f"          - {p}")
    print(f"requirements_check: {len(reqs) - bad} of {len(reqs)} tied to code, {bad} UNCOVERED")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
