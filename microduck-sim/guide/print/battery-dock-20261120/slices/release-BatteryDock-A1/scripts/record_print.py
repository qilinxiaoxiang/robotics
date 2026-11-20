"""Write the BatteryDock-A1 print times and filament masses (X1C, Elegoo Centauri Carbon, H2S) into ../../build/build.json
under 'print', from the delivered slices: run/delivery-index.json (X1C and Elegoo files and times), review/Orange_*-review.json
(grams read back from the gcode) and run-h2s/Orange/result.json (H2S). Read-only on the release.

    ~/.venvs/microduck-cad/bin/python scripts/record_print.py
"""
import json
from pathlib import Path

REL = Path(__file__).resolve().parents[1]
BUILD = REL.parents[1] / "build/build.json"


def main():
    idx = json.loads((REL / "run/delivery-index.json").read_text())
    rows = {}
    for f in idx["files"]:
        m = "Bambu" if "Bambu" in f["machine"] else "Elegoo"
        rev = json.loads((REL / f"review/Orange_{m}-review.json").read_text())
        key = "X1C" if m == "Bambu" else "Elegoo Centauri Carbon"
        rows[key] = dict(machine=f["machine"], plate=f["plate"], time=f["estimatedTime"], seconds=f["estimatedSeconds"],
                         filament_g=rev["final"]["filamentGrams"], support_extrusion_mm=rev["supportExtrusionTotalMm"],
                         file=f["path"], sha256=f["sha256"])
    h = json.loads((REL / "run-h2s/Orange/result.json").read_text())
    rows["H2S"] = dict(machine=h["machine"], plate=h["bed"], time=h["estimatedTime"], filament_g=h["filamentGrams"],
                       file=h["delivered"]["path"], sha256=h["delivered"]["sha256"])
    b = json.loads(BUILD.read_text())
    b["print"] = dict(release="BatteryDock-A1", color="Orange", material="PLA", status=idx["status"],
                      delivery_folder=str((REL / "run/delivery-folder").resolve()), printers=rows)
    BUILD.write_text(json.dumps(b, indent=1, ensure_ascii=False))
    print(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
