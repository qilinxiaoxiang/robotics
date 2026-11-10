"""Inline three.js and duck_poses.json into design-template.html -> flying-duck-design.html (self-contained)."""
from pathlib import Path
H = Path(__file__).resolve().parent
three = (H.parents[1] / "microduck-simulator/app/node_modules/three/build/three.module.min.js").read_text()
assert "</script" not in three.lower()
out = H.joinpath("design-template.html").read_text().replace("__MESH__", H.joinpath("duck_poses.json").read_text()).replace("__THREE__", three)
H.joinpath("flying-duck-design.html").write_text(out); print(len(out))
