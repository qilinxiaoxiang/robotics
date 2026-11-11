"""Build a bridge job: folder.py prelude + a job template, with '@@KEY@@' literals replaced
by Python repr() of the value, so names with spaces or quotes are safe.

Usage: python3 job.py TEMPLATE.py OUT.py KEY=VALUE ...
PROJECT and PATH come from FUSION_PROJECT and FUSION_PATH unless given.
"""
import os
import sys
from pathlib import Path

here = Path(__file__).parent
tpl, out, *kvs = sys.argv[1:]
vals = {"PROJECT": os.environ.get("FUSION_PROJECT"), "PATH": os.environ.get("FUSION_PATH"), "CREATE": "no"}
vals.update(kv.split("=", 1) for kv in kvs)
missing = [k for k, v in vals.items() if v is None]
if missing:
    sys.exit(f"job.py: set {missing} (FUSION_PROJECT / FUSION_PATH or KEY=VALUE)")
code = (here / "folder.py").read_text() + "\n" + Path(tpl).read_text()
for k, v in vals.items():
    code = code.replace(f"'@@{k}@@'", repr(v))
left = [w for w in code.split("'") if w.startswith("@@") and w.endswith("@@")]
if left:
    sys.exit(f"job.py: unfilled placeholders {sorted(set(left))}")
Path(out).write_text(code)
