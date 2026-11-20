"""Slice manifest of the battery backpack V2 rev M (frame and cap, one Orange plate), from the build in ../../../build.
Profiles and the baseline stock come from guide/print/release-V1.41 (Orange incremental, X1C on the Textured PEI Plate);
poses are build_v2.POSES (the sourceToPrint recorded in build/build.json). Pattern: extensions/flight-20261110/cad/
make_slice_manifest.py. Not a print-gate release: the guide (chapter 12) is not rebuilt for this design yet.

    ~/.venvs/microduck-cad/bin/python scripts/make_slice_manifest.py      (writes ../manifest-BatteryV2-M1.json)
"""
import hashlib, json
from pathlib import Path
import numpy as np, trimesh

REL = Path(__file__).resolve().parents[1]
CAD = REL.parents[1]                      # battery-v2-cad-20261120
SIM = CAD.parents[2]
VER = "BatteryV2-M1"
BASE = SIM / "guide/print/release-V1.41/manifest-V1.41.json"
GAP, BED = 8.0, 256.0
WHY = {"battery_v2_frame": "front face (x -45) on the bed: the open back faces up, so the box has no ceiling; the fixing "
                           "holes print vertical",
       "battery_v2_cap": "back face (x -75.55) on the bed, ribs up; the screw holes and the switch cutout print vertical"}


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p): return {"path": str(Path(p).resolve()), "sha256": sha(p)}


def main():
    m = json.loads(BASE.read_text())
    build = json.loads((CAD / "build/build.json").read_text())
    rows, placed = [], {}
    for key in ("battery_v2_frame", "battery_v2_cap"):
        info = build["parts"][key]; T = np.array(info["source_to_print"])
        w = CAD / "build" / f"{key}-world.stl"
        mesh = trimesh.load(w, force="mesh"); mesh.apply_transform(T); mesh.apply_translation([0, 0, -mesh.bounds[0, 2]])
        bottom = float(mesh.area_faces[np.max(np.abs(mesh.triangles[:, :, 2]), axis=1) <= .01].sum())
        placed[key] = mesh
        rows.append(dict(key=key, color="Orange", quantity=1, decision="addition", replacesStockIds=[],
                         path=str(w.resolve()), sha256=sha(w), sourceFrame="robot frame (mm, x forward, y left, z up)",
                         sourceToPrint=T.round(12).tolist(),
                         flatContact={"minimumAreaMm2": int(0.9 * bottom), "reason": "90 % of the measured contact in this pose."},
                         poseOrigin=f"{WHY[key]}; {bottom:.1f} mm2 bed contact, {mesh.extents[2]:.1f} mm tall",
                         poseCheck={"bedContactMm2": round(bottom, 2), "printSizeMm": [round(float(v), 1) for v in mesh.extents],
                                    "printStl": ref(CAD / "build" / f"{key}-print.stl")},
                         changeReason=("Battery backpack V2 rev M (Shawn 2026-11-20 '最小改造', '重做背包'): upright 74 x 34 x 20 pack, "
                                       "lower tier to z -46 so the robot still sits, today's Swann 39 switch in the cap, balance-plug notch. New part: "
                                       f"{key.replace('_', ' ')} ({info['volume_cm3']} cm3)."),
                         supersedes="battery_backpack_frame of V1.40 and battery_backpack_cap/battery_hatch of V1.41 (when built)",
                         incrementalEvidence=ref(CAD / "build/build.json"),
                         evidenceAlso=[ref(CAD / "build_v2.py"), ref(CAD / "DESIGN-CONTRACT.json"), ref(CAD / "features.json"),
                                       ref(CAD / "FITS.json"), ref(CAD / "checks/checks.json")],
                         supportBlockers=[], thinWallAllowances=[]))
    keys = list(placed)
    widths = [placed[k].extents[0] for k in keys]
    total_w = sum(widths) + GAP * (len(keys) - 1); assert total_w <= 220, total_w
    x, pl = BED / 2 - total_w / 2, []
    for k in keys:
        lo, ext = placed[k].bounds[0], placed[k].extents
        pl.append(dict(key=k, copy=1, translation=[round(x - float(lo[0]), 4), round(BED / 2 - ext[1] / 2 - float(lo[1]), 4), 0.0]))
        x += ext[0] + GAP
    m.update(version=VER, parts=rows, placements={"Orange": pl}, processOverrides={},
             processOverrideReason="none: the release profiles as in V1.41 (Orange, 0.2 mm layers)", retiredParts=[],
             prototypeScope=f"{VER}: battery backpack V2 rev M frame and cap on one Orange plate. Gated: the assembly "
                            "guide chapter 12 is rebuilt from this geometry and the print gate runs on it (CAD checks: battery-v2-cad-20261120/checks).",
             knownFitBoundary=("Bought part at its published size: pack 74 x 34 x 20 envelope (B08LZ8L4YD listing); moved in: "
                               "Swann 39 switch (DESIGN-D010 cutout 27.5 x 12.3, 3 mm panel), DFR1202."))
    for k in ("deferred", "supersedes"):
        m.pop(k, None)
    m["deliveryContract"] = dict(m["deliveryContract"], colors=["Orange"], filesPerColor=2, fileCount=2,
                                 baseline="printed releases through V1.41", supersedes=[], status="INCREMENTAL_REPRINT")
    (REL / f"manifest-{VER}.json").write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(json.dumps({k: p["translation"][:2] for k, p in zip(keys, pl)}))


if __name__ == "__main__":
    main()
