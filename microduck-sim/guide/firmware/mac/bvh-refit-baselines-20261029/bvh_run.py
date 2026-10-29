"""Run a sim harness as __main__ with bvh_hook installed (BVH_REFIT=0|1, BVH_OUT=<contacts.jsonl>).

  BVH_REFIT=1 BVH_OUT=/tmp/c.jsonl ~/.venvs/microduck-dyn/bin/python bvh_run.py ../brain_sim_check.py --walk-s 10 ...
"""
import os
import runpy
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bvh_hook  # noqa: E402

bvh_hook.install()
script = os.path.abspath(sys.argv[1])
sys.argv = [script] + sys.argv[2:]
sys.path[0] = os.path.dirname(script)
runpy.run_path(script, run_name="__main__")
