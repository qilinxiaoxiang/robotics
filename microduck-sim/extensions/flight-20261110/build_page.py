"""Inline three.js and the duck mesh into template.html -> flying-duck-3d.html (self-contained)."""
from pathlib import Path
H = Path(__file__).resolve().parent
three = (H.parents[1] / "microduck-simulator/app/node_modules/three/build/three.module.min.js").read_text()
assert "</script" not in three.lower()
out = H.joinpath("template.html").read_text().replace("__MESH__", H.joinpath("duck_mesh.json").read_text()).replace("__THREE__", three)
H.joinpath("flying-duck-3d.html").write_text(out); print(len(out))
