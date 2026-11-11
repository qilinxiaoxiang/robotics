"""Write the payload probe manifests for the universal stand/walk plan (UNIVERSAL-PLAN.md) from the latest sim snapshot.

  python3 train/make_payload_manifests.py   -> train/manifests/flightpack-load*.json + manifests/payload_loads.json

Source: sim/out/manifest_pack_nominal.json and manifest_pack_none.json (sim/ is read-only; this only reads it).
The pack = parts in nominal and not in none (all on trunk_base). Loads written:
  load000   no pack (the none manifest)
  load025 / load050 / load075   every pack part's mass and inertia x 0.25 / 0.50 / 0.75 at its own position
  nobatt    the pack with battery-L and battery-R removed (charging state, FP-R4)
  load100   the full pack (latest snapshot)
Each manifest keeps the none parts unchanged, so only the back load differs between them.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIM = HERE.parent / "sim" / "out"
OUT = HERE / "manifests"
BATT = {"battery-L", "battery-R"}


def main():
    nom = json.loads((SIM / "manifest_pack_nominal.json").read_text())
    none = json.loads((SIM / "manifest_pack_none.json").read_text())
    base_ids = {p["id"] for p in none["parts"]}
    pack = [p for p in nom["parts"] if p["id"] not in base_ids]
    assert all(p["body"] == "trunk_base" for p in pack)
    base = [p for p in nom["parts"] if p["id"] in base_ids]

    def scaled(parts, s):
        out = []
        for p in parts:
            q = dict(p)
            q["mass_kg"] = p["mass_kg"] * s
            if "inertia_about_com_kg_m2" in p:  # box parts (dimensions_m) get mass-proportional inertia in the worker
                q["inertia_about_com_kg_m2"] = [[v * s for v in row] for row in p["inertia_about_com_kg_m2"]]
            out.append(q)
        return out

    loads = {"load000": base,
             "load025": base + scaled(pack, 0.25), "load050": base + scaled(pack, 0.50),
             "load075": base + scaled(pack, 0.75),
             "nobatt": base + [p for p in pack if p["id"] not in BATT],
             "load100": base + pack}
    summary = {}
    for name, parts in loads.items():
        d = {k: v for k, v in nom.items() if k != "parts"}
        d["parts"] = parts
        d["payload_note"] = f"{name}: written by train/make_payload_manifests.py from sim/out manifest_pack_nominal/none"
        (OUT / f"flightpack-{name}.json").write_text(json.dumps(d, indent=1))
        m = sum(p["mass_kg"] for p in parts)
        pay = m - sum(p["mass_kg"] for p in base)
        com = [sum(p["mass_kg"] * p["position_m"][i] for p in parts if p["body"] == "trunk_base") /
               sum(p["mass_kg"] for p in parts if p["body"] == "trunk_base") for i in range(3)]
        summary[name] = dict(parts=len(parts), manifest_kg=round(m, 4), payload_kg=round(pay, 4),
                             trunk_parts_com_mm=[round(c * 1000, 1) for c in com])
        print(name, summary[name])
    (OUT / "payload_loads.json").write_text(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
