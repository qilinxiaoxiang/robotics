"""Regression tests for sch_lint.py against a fixture directory that a project owns.

Usage: python3 tests/run_tests.py FIXTURE_DIR      (or set FUSION_LINT_FIXTURES)

FIXTURE_DIR holds good*.sch (must pass) and mutations/m_<defect>.sch: copies of a good file with
one defect each. Every mutation must fail with the check named for its defect below; a mutation
whose defect is not listed fails the run, so new fixtures need an expectation. Fixtures stay in
the project (coursework may not be published through this repository). The first set is the
18-021 board: ~/Desktop/courses/18-021/.work/final/lint-fixtures (independent review, 2026-11-11).
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from sch_lint import lint

EXPECT = {   # defect -> substring that must appear in a failure (None = must pass)
    "mirrored_instance": None,       # mirrored supply whose pin sits at its origin: still connected
    "atts_block": "rejects these library tags",
    "endpoint_touch": "touch at",
    "t_junction": "ends on the middle of",
    "group_in_plain": "outside schematic-level <groups>",
    "undeclared_groupref": "undeclared groups",
    "layer93_missing": "layer 93",
    "unsmashed_no_attrs": "lacks",
    "pin_miss_0p0004": "not on a wire end",
    "mirror_q5v": "not on a wire end",
    "split_segment": "disjoint pieces",
    "label_off_wire": "from its own wires",
    "label_r180": "rotated",
    "text_on_label": "text collides",
}
arg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FUSION_LINT_FIXTURES")
if not arg:
    sys.exit(__doc__)
d = Path(arg).expanduser()
cases = [(f, None) for f in sorted(d.glob("good*.sch"))]
for f in sorted((d / "mutations").glob("m_*.sch")):
    cases.append((f, EXPECT.get(f.stem[2:], "__unlisted__")))
if not cases:
    sys.exit(f"no fixtures in {d}")
bad = 0
for f, want in cases:
    if want == "__unlisted__":
        ok, fails = False, ["defect not listed in EXPECT"]
    else:
        fails, _ = lint(f)
        ok = (not fails) if want is None else any(want in x for x in fails)
    bad += not ok
    print(("ok  " if ok else "FAIL"), f.relative_to(d), "" if ok else (fails[:3] or "passed but should fail"))
print("PASS" if not bad else f"{bad} failing")
sys.exit(1 if bad else 0)
