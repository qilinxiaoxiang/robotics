# Fastener audit (V1.6 guide)

This folder produces `guide/content/fasteners.json`: one record for every screw in the torso, power, IMU, neck, head, camera, electronics and head-closure steps. Each record holds the spec, the parts it passes through and threads into, the head seat point, the insertion axis and the measured engagement. The file also lists holes without screws, joints held without screws, and problems with proposed fixes. Nothing here edits steps.py, the viewer, routes.json, a print release or any STL.

## Result (2026-10-09)

- **Screws:** 76 records.
  - By step: torso-fasten 6, board 2, imu-holder 2, imu-cover 4, neck-lower-fasten 10, neck-pitch 4, neck-roll 4, neck-yaw-case 4, neck-upper-join 8, shells 10, jaw 4, head-bottom 4, camera 3, speaker 2, amp 2, pi 4, close 3.
  - By spec: M2×6 38, M2×10 14, M2×8 6, M2.5×8 7, M2.5×6 4, M2×4 3, M2×7 2, M2.6×6 2. All are self-tapping (TAP); none use nuts or washers.
- **Ray-cast hits:** 76/76 hit a hole on the full-resolution V1.6 meshes. 76/76 also hit on the meshes the viewer draws (guide-data.json sha256 e6ebf4d9…).
  - An earlier guide build (sha abb07f0b…) cut motors to 9000 faces. It missed 29 records, because the horn holes and case bores were destroyed.
- **Verified:** 75 records pass every check. S05-case-075 fails because the right shell is modelled 0.45-0.5 mm outboard, which puts its clearance hole 0.5 mm off the ID5 bore.
- **Agreement with the guide:** 54 of the 76 records match the guide's current prepare lists. The other 22 are in seven steps:
  - jaw, head-bottom and close list no screws.
  - camera gives no size.
  - speaker and amp say M2×6 where M2.5×8 is needed.
  - pi says M2.5×8 where M2×6 is needed.

  `stepReconciliation` in fasteners.json gives the per-step comparison.
- **Unassigned holes:** 44 screw-sized holes have no screw. 39 are explained as not needing one. 5 are unexplained: two in the face panel, one small hole in the jaw support, and a shell-to-shell pair at x −38, z 35. The 48 Pi header through-holes are excluded.
- **Unfastened joints:** 18 are listed with their retention and measured free travel. Four have no stated retention and can move:
  - the DFR1202 insert
  - both lip pads
  - the speaker inside its cage

## Method

1. **`extract_meshes.py`** caches two mesh sets as npz in the scratch directory.
   - The full set holds the full-build-data-current.json parts with undecimated motors. It adds the V1.6 head cap, OpenRB tray and OpenRB board from `guide/print/world`. It also adds the V1.6 jaw support, registered to the robot frame with a mean error of 0.0008 mm.
   - The guide set holds the meshes decoded from guide-data.json.
   - `evidence/mesh-manifest.json` records the sha256 of every source.
2. **`hole_inventory.py`** finds round holes of 1.0-3.8 mm in 26 changed or adjacent parts.
   - It slices each part every 0.4 mm along x, y, z and the camera and Pi axes.
   - A void face in the section counts as a hole when its circularity is at least 0.7.
3. **`screw_defs.py`** gives the nominal centres and axes from three sources:
   - the V1.4 verified records, where the parts are unchanged
   - the earlier head records (jaw horn, support frame, closure), re-measured
   - V1.6 geometry: tray.py rear holes, cap posts, rails and the camera clamp report
4. **`probe.py`** casts rays parallel to each screw axis: one on the axis and 8 at each of 25 radii from 0.5 to 3.5 mm.
   - Solid intervals come from depth-counting face-normal entries and exits (`geom.py`). This tolerates the touching sub-solids in the ROBOTIS motor meshes.
   - It measures:
     - the head seat on a declared part
     - the stack, with the hole diameter of each part
     - the thread engagement at r = 0.45 d, less 0.3 mm for the tip
     - the first solid past the tip
     - intrusions into undeclared parts
     - head clash
     - straight-driver room for a Ø3 mm shaft, counting only the parts present at that step (taken from the current steps.py)
   - A record "hits" when every declared part around the axis has a void on the axis over at least 90 % of its span.
5. **Joint checks.**
   - `freeplay.py` measures each unscrewed part's free travel in ±x, ±y and ±z before it meets any other part.
   - `capture.py` is an earlier contact-count version of the same check, kept for reference.
   - `jaw_access.py` rotates the jaw about the ID15 axis to find when the front closure screws become reachable. The corridor is clear from 30°, and the jaw meets the lower shell at about 40°.
6. **`build_fasteners.py`** composes fasteners.json from `evidence/`.

All geometry ran through `head-redesign-20261008/run_bounded_cad.py` (via `run_bounded.sh`), one job at a time, under a 1536 MiB limit. The run reports in `evidence/run-*.json` record a peak of 507 MiB or less for the final runs.

To reproduce, run the scripts in the order above with `/tmp/microduck-cad-venv/bin/python`. Set `FA_MESHES` to the folder that `extract_meshes.py --out` wrote.

## Conventions and assumptions

- **`center`:** the head seat point, meaning the underside of the head, measured on the full meshes.
- **`axis`:** the unit direction of travel. It equals −`world_axis` in the older records.
- **Head size (assumption):** 4.0 × 1.5 mm for M2 and M2.5, and 4.5 × 1.8 mm for M2.6. No drawing of the purchased screws is on file.
- **Probe resolution:** hole diameters are given as ranges, such as 1.6-1.7 mm. A diameter can be 0.1-0.2 mm larger than the lower value.
- **Inference:** statements marked "inference" in fasteners.json are not measured.

## Manufacturer sources

- **ROBOTIS X330 drawing (28 May 2020)**
  - Contents:
    - horn holes "4-Ø1.6 HOLE DP3.0 (Max.), P.C.D Ø12, Using M2 Tapping Screw"
    - case holes Ø1.6, with a Ø2 collar 3.5 mm deep at one end (Detail A) and 4.5 mm deep at the other (Detail B)
  - Local copy: `build-pack-20260913/redesign-20260913/fastener-audit/sources/X330_dimension.pdf`.
  - URL: https://www.besttechnology.co.jp/modules/knowledge/gate.php/X330_dimension.pdf?way=attach&_noumb&refer=Dynamixel%20XL330-M077&openfile=X330_dimension.pdf
  - ROBOTIS's own case fastening uses M2×8 TAP: https://robotis.us/products/fpx330-s101-set
- **ROBOTIS OpenRB-150 drawing (23 Aug 2022)**
  - Contents: "4-Ø2.5 HOLE THRU", "4-Ø4.5 INSULATED", hole pattern 61.5 × 20.5, board 66 × 25 × 1.6.
  - Local copy: `guide/data/sources/openrb-drawing.png`.
  - Page: https://emanual.robotis.com/docs/en/parts/controller/openrb-150/
- **Raspberry Pi Zero W mechanical drawing**
  - Contents: board 65 × 30, holes 58 × 23 apart and 3.5 mm from the edges, "all holes M2.5".
  - URL: https://datasheets.raspberrypi.com/rpizero/raspberry-pi-zero-w-mechanical-drawing.pdf (checked 2026-10-09).
- **DFRobot DFR1202**
  - Contents: "Dimensions: 30 x 26 x 8mm". The product page text gives no mounting-hole data.
  - URL: https://www.dfrobot.com/product-2907.html (checked 2026-10-09).
  - The guide holds the module with two ties, so no screw is involved.
- **Camera Module 3 Wide**
  - Contents: the board is clamped by the three-screw retainer, and its holes are not used.
  - Local source: `head-redesign-20261008/camera-ribbon-repair/positive-x225/camera-three-screw-clamp-report.json`.
  - Drawing: https://datasheets.raspberrypi.com/camera/camera-module-3-wide-mechanical-drawing.pdf
- **MAX98357A amplifier board:** no drawing on file. Its hole size (2.4-2.5 mm as modelled) is unverified.

## Files

- **Scripts:** `extract_meshes.py`, `geom.py`, `hole_inventory.py`, `screw_defs.py`, `probe.py`, `freeplay.py`, `capture.py`, `jaw_access.py`, `build_fasteners.py`, `run_bounded.sh`.
- **Evidence:** `evidence/probe-full.json`, `evidence/probe-guide.json`, `evidence/inventory.json`, `evidence/freeplay.json`, `evidence/freeplay-spk.json`, `evidence/capture.json`, `evidence/jaw-access.json`, `evidence/mesh-manifest.json` and `evidence/run-*.json`.
