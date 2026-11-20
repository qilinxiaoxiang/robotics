"""Round 3: rescore every already-scored teacher save from its existing gate episodes (no new episodes), after a
line was added to ts3_gates.py. Run with the gates' python:
  /Users/xiangzheng/.venvs/microduck-walk/bin/python train/ts3_rescore.py
Rewrites out/gates/gates_<dir>.json and logs/gates_<dir>_score.log; prints the passing saves and the speed-line fails.
"""
import contextlib
import io
import re
from pathlib import Path

import ts3_gates as g

T = Path(__file__).resolve().parent
dirs = sorted(p.stem[len("gates_"):] for p in (T / "out/gates").glob("gates_*.json") if re.match(r"gates_[tm]3[a-z]_\d+$", p.stem))
ok, slow = [], []
for d in dirs:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        good = g.score(d, teacher=True)
    (T / f"logs/gates_{d}_score.log").write_text(buf.getvalue())
    if good:
        ok.append(d)
    slow += [x[:110] for x in buf.getvalue().splitlines() if x.startswith("FAIL") and "walking speed" in x]
print(f"rescored {len(dirs)} saves; passing: {ok or 'none'}; walking-speed FAIL lines: {len(slow)}")
for x in slow:
    print("  " + x)
print("walk61 reference speeds:", {c: g.read("walk61", c)["speed_mean"] for c in ("none_walk", "none_g400_walk")})
