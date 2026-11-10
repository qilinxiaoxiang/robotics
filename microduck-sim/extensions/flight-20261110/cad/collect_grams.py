"""Slicer grams and times of the draft plates into slices/grams.json: per part, the H2S plate total split by CAD volume
(supports included, so a part's share is slightly high), plus each machine's plate time and grams.
    /tmp/microduck-cad-venv/bin/python cad/collect_grams.py       (after run_slices.sh)
"""
import json
import re
from pathlib import Path

H = Path(__file__).resolve().parent
REL = H / "slices" / "release-FlightPack-D1-DRAFT"


def main():
    build = json.loads((H / "build/build.json").read_text())
    vol = {k: v["volume_cm3"] for k, v in build.items() if isinstance(v, dict) and "colour" in v}
    plates, parts = {}, {}
    for colour in ("Orange", "Black"):
        h2s = json.loads((REL / "run-h2s" / colour / "result.json").read_text())
        p = dict(H2S=dict(time=h2s["estimatedTime"], grams=h2s["filamentGrams"]))
        for g in (REL / "run/delivery").glob(f"*_{colour}_*"):
            m = "X1C" if "X1C" in g.name else "Elegoo-CC"
            p[m] = dict(time=re.search(r"_(\d+h\d+m)\.", g.name).group(1), file=g.name)
            if g.suffix == ".gcode":
                t = g.read_text(errors="ignore")
                p[m]["grams"] = float(re.search(r"total filament used \[g\] = ([\d.]+)", t).group(1))
        keys = [k for k, v in build.items() if isinstance(v, dict) and v.get("colour") == colour]
        tot = sum(vol[k] for k in keys)
        for k in keys:
            parts[k] = round(h2s["filamentGrams"] * vol[k] / tot, 1)
        plates[colour] = p
    out = dict(source="H2S slices of release-FlightPack-D1-DRAFT (Generic PLA @BBL H2S, 0.20 mm Standard, release profile)",
               plates=plates, parts=parts)
    (H / "slices" / "grams.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
