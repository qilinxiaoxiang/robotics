"""Build the access_check self-test: a 60 x 60 x 3 plate with a 30 mm wall; one screw 2 mm from the wall (blocked
for a straight 3 mm shaft past the wall's overhang), one 3.5 mm from the wall face (awkward), one in the open (OK)."""
import json, sys
from pathlib import Path
import trimesh
out = Path(sys.argv[1])
plate = trimesh.creation.box(extents=(60, 60, 3)); plate.apply_translation((0, 0, -1.5))
wall = trimesh.creation.box(extents=(4, 60, 30)); wall.apply_translation((22, 0, 15))
lip = trimesh.creation.box(extents=(10, 60, 3)); lip.apply_translation((17, 0, 25.5))      # overhang 20 mm above the plate
plate.export(out / "plate.stl"); wall.export(out / "wall.stl"); lip.export(out / "lip.stl")
base = dict(spec="M3 x 6 button", head_d=5.7, head_h=1.65, length=6, through_mm=0, drive="hex", table_z=-3.0)
screws = [dict(id="open", step="s1", seat=[-15, 0, 0], axis=[0, 0, -1], present=["plate", "wall", "lip"], **base),
          dict(id="3.5 mm from the wall face", step="s1", seat=[16.5, 15, 0], axis=[0, 0, -1], present=["plate", "wall"], **base),
          dict(id="under the lip", step="s1", seat=[15, -15, 0], axis=[0, 0, -1], present=["plate", "wall", "lip"], **base)]
(out / "selftest.screws.json").write_text(json.dumps(dict(mesh_dir=".", meshes={k: f"{k}.stl" for k in ("plate", "wall", "lip")},
                                                          screws=screws, expect={"open": "OK", "3.5 mm from the wall face": "awkward",
                                                                                 "under the lip": "blocked"}), indent=1))
