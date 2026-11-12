"""Write the slice manifest of the flight pack, geometry as hashed in the release STATUS.json (Shawn 2026-11-10 asked for slice files; the fans are
not in hand, so the nacelle bore follows the listing drawing and is confirmed on arrival; the release waits for the print gate). Two plates: Orange (wing plate, two battery trays, FC
bracket) and Black (the four nacelle clamp halves; they do not fit beside the wing on one bed). Sources are cad/build/*-world.stl
in the print poses of build_pack.POSES; profiles and the 89-record baseline stock come from guide/print/release-V1.41
(the X1C profile on the Textured PEI Plate, 55 C).
    /tmp/microduck-cad-venv/bin/python cad/make_slice_manifest.py       (after build_pack.py; writes slices/<REL>/manifest-<VER>.json)
"""
import hashlib
import json
from pathlib import Path
import numpy as np
import trimesh

import cadlib
from build_pack import POSES, COLOUR

H = Path(__file__).resolve().parent
SIM = H.parents[2]
VER = "FlightPack-D1"
REL = H / "slices" / f"release-{VER}"
BASE = SIM / "guide/print/release-V1.41/manifest-V1.41.json"
GAP = 6.0          # mm between parts on the plate
# Black: Bambu Studio found "gcode path conflicts" between the nacelle halves at 6 mm (2026-11-10, thick-collar geometry)
GAP_BY = {"Black": 14.0}
BED = 256.0


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p): return {"path": str(Path(p).resolve()), "sha256": sha(p)}


def pose(key):
    T = np.eye(4); T[:3, :3] = cadlib.rot_matrix(POSES[key])
    m = trimesh.load(H / "build" / f"{key}-world.stl", force="mesh"); m.apply_transform(T)
    m.apply_translation([0, 0, -m.bounds[0, 2]])
    bottom = float(m.area_faces[np.max(np.abs(m.triangles[:, :, 2]), axis=1) <= .01].sum())
    return T, m, bottom


WHY = {
    "wing_plate": "front face (x -45) down: the arm webs, flanges and gussets stand up; the post holes print vertical",
    "tray_L": "deck underside down", "tray_R": "deck underside down",
    "fc_bracket": "plate front face (x -64) down; the M3 standoff bosses stand up",
}
for k in ("nacelle_inner_L", "nacelle_outer_L", "nacelle_inner_R", "nacelle_outer_R"):
    WHY[k] = "upright, the lowest collar rim (bed plane z 32.36) down; the clamp bore prints vertical (locating fit)"

# Rows of each plate, in print x order per row (fits a 220 mm usable square with GAP).
LAYOUT = {"Orange": [["wing_plate", "fc_bracket"], ["tray_L", "tray_R"]],
          "Black": [["nacelle_inner_L"], ["nacelle_outer_L"], ["nacelle_inner_R"], ["nacelle_outer_R"]]}


def main():
    m = json.loads(BASE.read_text())
    build = json.loads((H / "build/build.json").read_text())
    reason = ("Flying MicroDuck four-EDF jetpack (Shawn 2026-11-10: '感觉还是4个电机好一点', '64太大太重了 就按50来做', '共用螺丝'). "
              f"Geometry: world STL sha256[:12] in STATUS.json (wing_plate {json.loads((REL / 'STATUS.json').read_text())['geometry']['wing_plate']}); the fans are not in hand, so the nacelle bore and stops follow the ARESWEI listing drawing "
              "and are confirmed on arrival. New part: ")
    rows, placed = [], {}
    for key in POSES:
        T, mesh, bottom = pose(key)
        placed[key] = mesh
        rows.append(dict(key=key, color=COLOUR[key], quantity=1, decision="addition", replacesStockIds=[],
                         path=str((H / "build" / f"{key}-world.stl").resolve()), sha256=sha(H / "build" / f"{key}-world.stl"),
                         sourceFrame="guide frame (mm, x forward, y left, z up)", sourceToPrint=T.round(12).tolist(),
                         flatContact={"minimumAreaMm2": int(0.9 * bottom), "reason": "90 % of the measured contact in this pose."},
                         poseOrigin=f"{WHY[key]}; {bottom:.1f} mm2 bed contact, {mesh.extents[2]:.1f} mm tall",
                         changeReason=reason + key.replace("_", " ") + f" ({build[key]['volume_cm3']} cm3).",
                         incrementalEvidence=ref(H / "build/build.json"),
                         evidenceAlso=[ref(H / "build_pack.py"), ref(H / "flight_params.py"), ref(H / "DESIGN-CONTRACT.json"),
                                       ref(H / "features.json"), ref(H / "FITS.json"), ref(H / "checks/check_parts.json")],
                         supportBlockers=[], thinWallAllowances=[]))
    placements = {}
    for colour, plate in LAYOUT.items():
        GAP = GAP_BY.get(colour, 6.0)
        sizes = [[placed[k].extents[:2] for k in r] for r in plate]
        widths = [sum(s[0] for s in r) + GAP * (len(r) - 1) for r in sizes]
        heights = [max(s[1] for s in r) for r in sizes]
        total_h = sum(heights) + GAP * (len(plate) - 1)
        assert max(widths) <= 220 and total_h <= 220, (colour, widths, total_h)
        y, pl = BED / 2 - total_h / 2, []
        for r, w, h in zip(plate, widths, heights):
            x = BED / 2 - w / 2
            for k in r:
                lo, ext = placed[k].bounds[0], placed[k].extents
                pl.append(dict(key=k, copy=1, translation=[round(x - float(lo[0]), 4), round(y + (h - ext[1]) / 2 - float(lo[1]), 4), 0.0]))
                x += ext[0] + GAP
            y += h + GAP
        placements[colour] = pl
    # the wing plate prints at 100 % infill (strength/SPAR-OPTION.md: the 8.5 mm solid root band is sized as solid PLA).
    # The pipeline has plate-wide process overrides only (objectSettings take brim keys), so the whole Orange plate
    # (wing plate, trays, FC bracket) gets it; the mass budget already counts printed parts as solid.
    # Bambu Studio refuses gyroid at 100 % ("gyroid doesn't work at 100% density", 2026-11-10): zig-zag lines, as both slicers take
    # layer_height 0.2 on every plate: the stock Black profile is 0.1 mm (made for the duck's cosmetic shells), which put the
    # functional nacelle plate at 8h36m on the H2S (2026-11-12, Shawn: "怎么要8个小时"); the fit numbers in
    # cad-practice/PRINT-FIT.md are measured at 0.2 mm layers.
    solid = {"sparse_infill_density": "100%", "sparse_infill_pattern": "zig-zag", "layer_height": "0.2"}
    # Black (nacelle halves): 6 walls (about 2.7 mm a side, every screw hole gets its own 6 loops) + 40 % gyroid, 2026-11-12
    # (Shawn: "如果不需要实心就简化一下 搞快点"). The nacelle gates are bending (lift by one nacelle, thrust): the stress sits in
    # the outer fibres the walls now fill; the solid-isotropic FEA (SF about 2.0 at x -36/-25) overstates the core's share.
    shell = {"sparse_infill_density": "40%", "sparse_infill_pattern": "gyroid", "wall_loops": "6", "layer_height": "0.2"}
    over = {f"Orange_{m}": dict(solid) for m in ("Bambu", "Elegoo")}
    over.update({f"Black_{m}": dict(shell) for m in ("Bambu", "Elegoo")})
    m.update(version=VER, parts=rows, placements=placements,
             processOverrides=over,
             processOverrideReason="Orange at 100 % sparse infill (zig-zag): the wing plate's solid root band (strength "
                                   "check, plain PLA, lift SF 1.67 already under 2). Black (nacelle halves) at 6 walls and "
                                   "40 % gyroid since 2026-11-12: the 100 % plate took 8h36m at the stock Black 0.1 mm layers "
                                   "and 4h42m at 0.2 mm; the nacelle loads are bending, carried by the walls. Both plates "
                                   "0.2 mm layers (PRINT-FIT.md basis). Plate-wide because the pipeline sets no per-object "
                                   "infill.",
             retiredParts=[],
             prototypeScope=f"{VER}: flight pack, Orange plate (wing plate, battery trays L/R, FC bracket) and Black plate "
                            "(nacelle inner/outer halves L/R). Print gate: see STATUS.json (chapter-12 bp-hatch exception "
                            "A-GATE-BPHATCH, Shawn 2026-11-11 '记为例外放行').",
             knownFitBoundary=("Fans not in hand: ARESWEI HDS001 duct OD 50.6 (clamp closes on 49.1..52.5 with 1 mm foam "
                               "tape), lip OD 58.4, ears from the listing drawing (+-1.5 mm). Battery 74 x 33 x 31 from the listing (+4 mm length slack). FC/ESC 30.5 mm pattern and "
                               "MTF-01 holes from the listings, not measured. M3 standoffs are not in stock."))
    for k in ("deferred", "supersedes"):
        m.pop(k, None)
    m["deliveryContract"] = dict(m["deliveryContract"], colors=list(LAYOUT), filesPerColor=2, fileCount=2 * len(LAYOUT),
                                 baseline="printed releases through V1.41 (no stock part replaced)",
                                 # gate state as scripts/gate_status.py recorded it (A-GATE-BPHATCH exception included)
                                 status=json.loads((REL / "STATUS.json").read_text()).get("status", "PREPARED_GATE_PENDING")
                                 if (REL / "STATUS.json").exists() else "PREPARED_GATE_PENDING",
                                 supersedes=[])
    REL.mkdir(parents=True, exist_ok=True)
    (REL / f"manifest-{VER}.json").write_text(json.dumps(m, indent=1, ensure_ascii=False))
    print(json.dumps({c: [(p["key"], p["translation"][:2]) for p in v] for c, v in placements.items()}))


if __name__ == "__main__":
    main()
