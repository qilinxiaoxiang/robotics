"""Run a sim harness with the open-loop stand's neck_pitch set to V instead of pi/stand_pose.py's (D-030: 0.25 since
2026-10-26, NEUTRAL 0.35 before), to bisect a stand-phase result against the D-030 change. Files stay unchanged.

  ~/.venvs/microduck-dyn/bin/python stand_neck_run.py 0.35 ../brain_sim_check.py --model asbuilt --com-x 5 ...
"""
import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "pi"))
import stand_pose  # noqa: E402

stand_pose.STAND_POSE["neck_pitch"] = float(sys.argv[1])
script = os.path.abspath(sys.argv[2])
sys.argv = [script] + sys.argv[3:]
sys.path[0] = os.path.dirname(script)
runpy.run_path(script, run_name="__main__")
