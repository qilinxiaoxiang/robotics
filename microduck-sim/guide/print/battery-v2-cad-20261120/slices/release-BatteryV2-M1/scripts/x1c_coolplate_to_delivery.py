"""Put the Cool Plate X1C file in the Downloads delivery in place of the Textured PEI one (Shawn 2026-11-12: the club X1C
he prints on has a Cool Plate; FlightPack-D1 precedent: ~/Downloads/zhengxia_MicroDuck_FlightPack-D1/X1C-CoolPlate/).
Run after make_delivery_folder.py <release> has written ~/Downloads/zhengxia_MicroDuck_<version>/. Copies every file of
<release>/delivery-x1c-cool/ byte-checked into X1C-CoolPlate/ and removes the X1C/ Textured PEI folder.

    ~/.venvs/microduck-cad/bin/python scripts/x1c_coolplate_to_delivery.py <release-dir>
"""
import hashlib, shutil, sys
from pathlib import Path

REL = Path(sys.argv[1]).resolve(); VER = REL.name.split("-", 1)[1]
OUT = Path.home() / "Downloads" / f"zhengxia_MicroDuck_{VER}"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert OUT.is_dir(), OUT
src = sorted((REL / "delivery-x1c-cool").glob("*"))
assert any(p.name.endswith(".gcode.3mf") for p in src), "no Cool Plate X1C file"
dst = OUT / "X1C-CoolPlate"; dst.mkdir(exist_ok=True)
for p in src:
    shutil.copy2(p, dst / p.name); assert sha(p) == sha(dst / p.name), p
if (OUT / "X1C").is_dir(): shutil.rmtree(OUT / "X1C")
for p in sorted(OUT.rglob("*")):
    if p.is_file(): print(p.relative_to(OUT), p.stat().st_size)
