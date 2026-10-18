"""Run one of the V1.8 pack checks (../rear-pack/check_fit.py, check_assembly.py, check_print.py, pack_sweep2.py) on the V1.9 STLs.
The V1.8 scripts read the pack from pack_lib.OUT and write their JSON there; this sets OUT to this folder first, so the V1.8 folder
is never touched. Usage: run_v18_check.py <script name> [script args ...]
"""
import sys, runpy
from pathlib import Path
HERE = Path(__file__).resolve().parent
V18 = HERE.parent / 'rear-pack'
sys.path.insert(0, str(V18))
import pack_lib as P  # noqa: E402

P.OUT = HERE
script = V18 / sys.argv[1]
sys.argv = [str(script)] + sys.argv[2:]
runpy.run_path(str(script), run_name='__main__')
