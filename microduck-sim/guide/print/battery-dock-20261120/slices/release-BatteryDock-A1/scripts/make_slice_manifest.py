"""Slice manifest of the battery backpack rev B charging dock base (BatteryDock-A1: one part, one Orange plate), from the
build in ../../../build. Profiles and the baseline stock come from guide/print/release-V1.41 (Orange incremental, X1C on the
Textured PEI Plate); the pose is build_dock's print pose (base plate on the bed, the sourceToPrint recorded in
build/build.json). Copied from battery-v2-cad-20261120/slices/release-BatteryV2-B1/scripts/make_slice_manifest.py. Not a
print-gate release: the assembly guide chapter 12 is being rebuilt in parallel.

    ~/.venvs/microduck-cad/bin/python scripts/make_slice_manifest.py      (writes ../manifest-BatteryDock-A1.json)
"""
import hashlib, json
from pathlib import Path
import numpy as np, trimesh

REL = Path(__file__).resolve().parents[1]
CAD = REL.parents[1]                      # battery-dock-20261120
SIM = CAD.parents[2]
VER = "BatteryDock-A1"
BASE = SIM / "guide/print/release-V1.41/manifest-V1.41.json"
BED = 256.0
KEY = "dock_base"
WHY = "base plate on the bed, tower open top up: the grooves, slots and jack hole need no support; the jack hole prints as a teardrop"


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p): return {"path": str(Path(p).resolve()), "sha256": sha(p)}


def main():
    m = json.loads(BASE.read_text())
    build = json.loads((CAD / "build/build.json").read_text())
    assert not build["fails"], build["fails"]
    T = np.array(build["source_to_print"])
    w = CAD / "build" / f"{KEY}-world.stl"
    mesh = trimesh.load(w, force="mesh"); mesh.apply_transform(T); mesh.apply_translation([0, 0, -mesh.bounds[0, 2]])
    bottom = float(mesh.area_faces[np.max(np.abs(mesh.triangles[:, :, 2]), axis=1) <= .01].sum())
    row = dict(key=KEY, color="Orange", quantity=1, decision="addition", replacesStockIds=[],
               path=str(w.resolve()), sha256=sha(w), sourceFrame="robot seated frame (mm, x forward, y left, z above the floor)",
               sourceToPrint=T.round(12).tolist(),
               flatContact={"minimumAreaMm2": int(0.9 * bottom), "reason": "90 % of the measured contact in this pose."},
               poseOrigin=f"{WHY}; {bottom:.1f} mm2 bed contact, {mesh.extents[2]:.1f} mm tall",
               poseCheck={"bedContactMm2": round(bottom, 2), "printSizeMm": [round(float(v), 1) for v in mesh.extents],
                          "printStl": ref(CAD / "build" / f"{KEY}-print.stl")},
               changeReason=("Battery backpack rev B dock charging (Keystone 5209 leaves under the robot's Keystone 615 pads, "
                             f"Same Sky PJ-005A jack): new part dock_base ({build['volume_cm3']} cm3)."),
               supersedes="nothing (new part)",
               incrementalEvidence=ref(CAD / "build/build.json"),
               evidenceAlso=[ref(CAD / "build_dock.py"), ref(CAD / "features.json"), ref(CAD / "FITS.json")],
               supportBlockers=[], thinWallAllowances=[])
    lo, ext = mesh.bounds[0], mesh.extents
    pl = [dict(key=KEY, copy=1, translation=[round(BED / 2 - ext[0] / 2 - float(lo[0]), 4), round(BED / 2 - ext[1] / 2 - float(lo[1]), 4), 0.0])]
    m.update(version=VER, parts=[row], placements={"Orange": pl}, processOverrides={},
             processOverrideReason="none: the release profiles as in V1.41 (Orange, 0.2 mm layers)", retiredParts=[],
             prototypeScope=f"{VER}: battery backpack rev B charging dock base on one Orange plate. Not gated: the assembly "
                            "guide chapter 12 is rebuilt separately (CAD checks: battery-dock-20261120/build/build.json).",
             knownFitBoundary=("Bought parts at published sizes: Keystone 5209 (M65p15) in a 0.40 x 10.50 press groove, Same Sky "
                               "PJ-005A (rev 1.09) in an 8.44 teardrop hole."))
    for k in ("deferred", "supersedes"):
        m.pop(k, None)
    m["deliveryContract"] = dict(m["deliveryContract"], colors=["Orange"], filesPerColor=2, fileCount=2,
                                 baseline="printed releases through V1.41", supersedes=[], status="INCREMENTAL_REPRINT")
    (REL / f"manifest-{VER}.json").write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(json.dumps(pl[0]["translation"][:2]))


if __name__ == "__main__":
    main()
