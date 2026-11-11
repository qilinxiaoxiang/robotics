"""Visual parts of the flight pack for the with-pack mass manifests: drawn only (no mass, no contact).

Every with-pack manifest (sim/out/manifest_pack_*.json, and copies made from them) carries a "visual_parts" list next to
its mass "parts". The loader (evaluate_delay.load -> microduck_rl/cmu/model/visual.py::apply_manifest_visuals) adds one
mesh geom per item to its body: contype 0, conaffinity 0, group 2, density 0, mass 0, so the compiled physics is the
same as without them. The duck's own look still comes only from cmu/model/visual (fitted.json -> make_visual).

Meshes are read by path at load time, so a CAD rebuild is picked up without regenerating anything:
  printed parts  the release manifest cad/slices/release-FlightPack-D1/manifest-FlightPack-D1.json (path and colour per
                 part; the paths point at cad/build/<part>-world.stl)
  bought parts   the CAD dummies cad/build/dummy_*-world.stl (fans, batteries, FC/ESC stack, MTF-01, capacitor)
All world STLs are in the guide frame (mm, x forward, y left, z up) = the trunk_base frame, so scale 0.001, no offset.

  python3 sim/pack_visual.py --manifest <in.json> --out <out.json>    add visual_parts to a copy of a manifest
"""
import argparse
import json
import os
from pathlib import Path

H = Path(__file__).resolve().parent
FL = H.parent
RELEASE = FL / "cad/slices/release-FlightPack-D1/manifest-FlightPack-D1.json"
BUILD = FL / "cad/build"
# colours of the CMU visual palette (microduck_rl/cmu/model/visual/visual.json) for the filament colours of the release
FILAMENT = {"Orange": [0.95, 0.45, 0.06, 1], "Black": [0.11, 0.11, 0.12, 1]}
# bought parts (appearance approximations: fan housings anodised grey, battery shrink dark blue-grey, boards dark)
BOUGHT = [("dummy_fan_front_L", [0.62, 0.63, 0.66, 1]), ("dummy_fan_front_R", [0.62, 0.63, 0.66, 1]),
          ("dummy_fan_rear_L", [0.62, 0.63, 0.66, 1]), ("dummy_fan_rear_R", [0.62, 0.63, 0.66, 1]),
          ("dummy_battery_L", [0.18, 0.22, 0.32, 1]), ("dummy_battery_R", [0.18, 0.22, 0.32, 1]),
          ("dummy_fc_esc_stack", [0.15, 0.3, 0.62, 1]), ("dummy_mtf01", [0.15, 0.4, 0.28, 1]),
          ("dummy_esc_capacitor", [0.2, 0.2, 0.22, 1])]


SIMROOT = FL.parents[1]   # microduck-sim: mesh paths are stored relative to it, and the loader finds that root by walking
                          # up from the manifest, so a copy of the manifest anywhere in the tree still finds the meshes


def visual_parts(rel_to=SIMROOT):
    """visual_parts with mesh paths relative to microduck-sim (the loader resolves them from the manifest upwards)."""
    out = []
    for p in json.loads(RELEASE.read_text())["parts"]:
        f = Path(p["path"])
        if not f.is_absolute():
            f = RELEASE.parent / f
        f = BUILD / f.name if not f.exists() else f   # the release lists absolute paths of this checkout
        out.append(dict(id=p["key"], body="trunk_base", file=os.path.relpath(f, rel_to), scale=0.001,
                        rgba=FILAMENT[p["color"]], source=f"{RELEASE.name} part {p['key']} ({p['color']})"))
    for stem, rgba in BOUGHT:
        f = BUILD / f"{stem}-world.stl"
        if f.exists():
            out.append(dict(id=stem, body="trunk_base", file=os.path.relpath(f, rel_to), scale=0.001, rgba=rgba,
                            source=f"cad/build/{f.name} (CAD dummy of a bought part; colour approximate)"))
    return out


def with_visuals(manifest):
    """Path of the visual copy of a sim/out manifest (sim/out/visual/<name>): same mass parts plus visual_parts. Written
    when missing or older than its source (atomic rename, safe under parallel batch runs). The sim/out manifests
    themselves stay without visual_parts: their copies are read by loaders whose mirrors may not hold cad/build."""
    src = Path(manifest)
    if not any(p.get("group") == "pack" for p in json.loads(src.read_text())["parts"]):
        return src     # no pack in this manifest (e.g. manifest_pack_none): nothing to draw
    dst = src.parent / "visual" / src.name
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        man = json.loads(src.read_text())
        man["visual_parts"] = visual_parts()
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(f".{dst.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(man))
        os.replace(tmp, dst)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    man = json.loads(Path(a.manifest).read_text())
    out = Path(a.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    man["visual_parts"] = visual_parts()
    out.write_text(json.dumps(man))
    print(out, len(man["visual_parts"]), "visual parts")


if __name__ == "__main__":
    main()
