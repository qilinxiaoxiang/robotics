"""Slicer grams and times of the FlightPack-D1 plates into slices/grams.json: per part, the H2S plate total split by CAD volume
(supports included, so a part's share is slightly high), plus each machine's plate time and grams.
    /tmp/microduck-cad-venv/bin/python cad/collect_grams.py       (run by slices/release-FlightPack-D1/scripts/run_fp.sh)
"""
import json
import re
from pathlib import Path

H = Path(__file__).resolve().parent
REL = H / "slices" / "release-FlightPack-D1"


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
            rv = json.loads((REL / "review" / f"{colour}_{'Bambu' if m == 'X1C' else 'Elegoo'}-review.json").read_text())
            p[m]["grams"] = rv["final"]["filamentGrams"]
        keys = [k for k, v in build.items() if isinstance(v, dict) and v.get("colour") == colour]
        tot = sum(vol[k] for k in keys)
        for k in keys:
            parts[k] = round(h2s["filamentGrams"] * vol[k] / tot, 1)
        plates[colour] = p
    geo = json.loads((REL / "STATUS.json").read_text())["geometry"]
    out = dict(source=f"slices of release-FlightPack-D1, geometry: world STL sha256[:12] in its STATUS.json (wing_plate {geo['wing_plate']}); parts split from the H2S plate grams by CAD volume (Generic PLA @BBL H2S, 0.20 mm Standard, release profile; Orange at 100 % infill)",
               plates=plates, parts=parts)
    (H / "slices" / "grams.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
