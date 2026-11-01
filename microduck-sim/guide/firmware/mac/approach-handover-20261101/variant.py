"""approach_sim.py with the hand-over constants of approach.py overridden (sim only; approach.py is not changed).
  VARIANT_STOP_R, VARIANT_DONE_BEARING_DEG, VARIANT_DONE_R_MAX (environment) -> apc.STOP_R, DONE_BEARING, DONE_R[1]
  ~/.venvs/microduck-dyn/bin/python variant.py --obj 0.6 0 --obj-height 0.012 --out x.json"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.argv[0] = os.path.join(os.path.dirname(HERE), "approach_sim.py")
import approach as apc  # noqa: E402
if os.environ.get("VARIANT_STOP_R"):
    apc.STOP_R = float(os.environ["VARIANT_STOP_R"])
if os.environ.get("VARIANT_DONE_BEARING_DEG"):
    apc.DONE_BEARING = math.radians(float(os.environ["VARIANT_DONE_BEARING_DEG"]))
if os.environ.get("VARIANT_DONE_R_MAX"):
    apc.DONE_R = (apc.DONE_R[0], float(os.environ["VARIANT_DONE_R_MAX"]))
import approach_sim  # noqa: E402
print(f"variant STOP_R {apc.STOP_R} DONE_BEARING {math.degrees(apc.DONE_BEARING):.0f} DONE_R {apc.DONE_R}", flush=True)
approach_sim.main()
