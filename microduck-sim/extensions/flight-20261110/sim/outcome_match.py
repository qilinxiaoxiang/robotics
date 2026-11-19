"""Compare two flight.py outcome rows field by field: exit 0 when equal, 3 when any field differs.

  $PY sim/outcome_match.py recorded.json new.json
Used by render_full_videos_hd.sh: a presentation render is only kept when its run is the recorded run.
"""
import json
import sys
from pathlib import Path


def flat(x, pre=""):
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            out.update(flat(v, f"{pre}{k}."))
        return out
    return {pre[:-1]: x}


a, b = (flat(json.loads(Path(p).read_text())) for p in sys.argv[1:3])
diff = [(k, a.get(k, "<missing>"), b.get(k, "<missing>")) for k in sorted(set(a) | set(b)) if a.get(k, "<missing>") != b.get(k, "<missing>")]
for k, va, vb in diff:
    print(f"DIFF {k}: recorded {va!r} new {vb!r}")
print(f"OUTCOME_MATCH {sys.argv[2]} fields={len(a)} differing={len(diff)}")
sys.exit(3 if diff else 0)
