"""Mac mini snapshot only: point asbuilt.config.json's mass_manifest (an absolute MacBook path in the repository) at the
same file inside this snapshot, so harnesses that load the default asbuilt manifest run without bvh_hook's path fix.
Never run on the MacBook checkout (it refuses when the path already exists).

  python3 snapshot_paths.py
"""
import json
import os
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[5]
cfg = ROOT / "microduck-sim/hardware-design-20260912/whole-robot-20260912/dynamics/asbuilt-20261015/asbuilt.config.json"
c = json.loads(cfg.read_text())
old = c["mass_manifest"]
if os.path.exists(old):
    raise SystemExit(f"{old} exists here; nothing to do (this is not the Mac mini snapshot)")
new = str(ROOT / old.split("/code/robotics/", 1)[1])
assert os.path.exists(new), new
c["mass_manifest"] = new
cfg.write_text(json.dumps(c, indent=1))
print(f"mass_manifest: {old} -> {new}")
