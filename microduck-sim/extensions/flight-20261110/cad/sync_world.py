"""Copy the eight printed flight parts from cad/build/*-world.stl to guide/print/world/*.stl, the git-ignored mirrors the
MicroDuck guide (build_flight_guide.main_fragment) and the print gate read; main_fragment asserts they match by sha256.
    /tmp/microduck-cad-venv/bin/python cad/sync_world.py       (after build_pack.py, before the guide build)
"""
import hashlib
import shutil
from pathlib import Path

H = Path(__file__).resolve().parent
WORLD = H.parents[2] / "guide" / "print" / "world"
PARTS = ["wing_plate", "tray_L", "tray_R", "nacelle_inner_L", "nacelle_outer_L", "nacelle_inner_R", "nacelle_outer_R", "fc_bracket"]

for k in PARTS:
    src, dst = H / "build" / f"{k}-world.stl", WORLD / f"{k}.stl"
    shutil.copyfile(src, dst)
    assert hashlib.sha256(src.read_bytes()).digest() == hashlib.sha256(dst.read_bytes()).digest()
    print(k, "->", dst)
