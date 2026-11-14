"""One line per training-env probe (train/out/spk3diag/*.json from spk2diag_probe.py): success / falls of envs, fall
direction counts, median fall time, and the policy goals outside walk_brain.JOINT_RANGE on the hip rolls and ankles.
  python3 train/spk3diag_train_table.py train/out/spk3diag/spk3_*.json
"""
import json
import sys

for f in sys.argv[1:]:
    d = json.load(open(f))
    if "success" not in d:
        continue
    ex = d.get("goal_exceed_steps") or {}
    ft = d.get("fall_t") or {}
    print(f"{d['label']:<24} success {d['success']:>3}/{d['envs']} falls {d['falls']:>3} "
          f"dir {d.get('fall_dir')} fall_t {ft.get('mean') if ft else None} "
          f"exceed hip_roll L/R {ex.get('left_hip_roll', 0)}/{ex.get('right_hip_roll', 0)} "
          f"ankle L/R {ex.get('left_ankle', 0)}/{ex.get('right_ankle', 0)}")
