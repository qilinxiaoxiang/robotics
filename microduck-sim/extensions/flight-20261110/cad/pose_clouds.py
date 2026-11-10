"""Cache the moving-part point clouds of sweep_check.py's pose sets once, so a CAD edit is checked in seconds.

Imports ../sweep_check.py (which builds the pose sets: stand, random legs/head at 50 % and 100 % of joint range, the
pickup head-scan poses, head yaw alone, the 1046 logged real bend rows) and stores, per set, the union of all poses'
points snapped to a 0.5 mm grid (stand-keyframe world frame, mm). The minimum gap from a fixed solid to a set equals the
minimum over this union, so check_parts.py needs no pose loop. Forward kinematics only, no simulation.
Run on the Mac mini (zsh cad/mini_sync.sh run '$PY cad/pose_clouds.py'), about 40 s.
"""
import sys
from pathlib import Path
import numpy as np

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H.parent))
sys.argv = [sys.argv[0], "600"]
import sweep_check as S  # noqa: E402  (builds S.sets)

out = {}
for name, P in S.sets.items():
    allp = np.vstack(P)
    q = np.unique(np.round(allp / 0.5).astype(np.int32), axis=0)
    out[name] = (q * 0.5).astype(np.float32)
    print(f"{name:66s} poses {len(P):5d}  points {len(allp):9d} -> {len(q):7d}")
(H / "build").mkdir(exist_ok=True)
np.savez_compressed(H / "build" / "pose_clouds.npz", names=np.array(list(out)), **{f"s{i}": v for i, v in enumerate(out.values())})
print("wrote", H / "build" / "pose_clouds.npz")
