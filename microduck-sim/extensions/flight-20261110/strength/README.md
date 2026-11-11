# Flight pack: printed-part strength check

Geometry: commit `1b392541` (clamp change included). STL sha256 prefixes: wing_plate `2a7f344b193bcdc8`, tray_L `2a82c784b5075e2d`, nacelle_inner_L `08368bcc55d6f487`, nacelle_outer_L `bd100e020e35f6ff`, fc_bracket `66cc6d929c3091eb`. All numbers are in `results.json`.

## Conclusion

At SF 2, three things fail in PLA as built: the wing-plate root, the nacelle clamp blocks and two screw joints. A topple onto a nacelle breaks the root by 5 to 10 times, and no section change fixes that.

- **Wing-plate root (|y| 21 to 31, where the arm leaves the centre plate): fails, even in normal use.**
  - Peak thrust, 980 g × 1.5 per fan with the feet on the ground: SF 1.1.
  - 15.6 g landing: SF 0.55.
  - Lifting the duck by one nacelle: SF 0.69.
  - 10 g fore-aft: SF 0.33 to 0.45.
  - 10 g sideways: SF 0.51.
  - Fix: root-fix geometry plus PA-CF printed at 100 % infill clears the vertical cases (SF 2.2 to 2.9). The fore-aft 10 g case also needs a 3 mm carbon rod bonded in the free slot behind the band (SF 2.2 to 2.7). Mass about +15 g in total.
- **Nacelle clamp: fails at assembly.**
  - Each M2 screw sits 9.3 mm outboard of the 3.4 mm collar wall, so tightening bends the wall where the screw block ends.
  - Snug (167 N): 76 MPa, SF 0.42. Even at the 120 N strip load: SF 0.59.
  - Fix: thicken the collar wall to 7.0 mm at each block end (the middle web too), tapering back over 10 mm. SF 2.0 at snug. Mass +3 g per nacelle.
- **Tray flange screws: fail** at 15.6 g, 99 N pull-out, SF 1.2.
  - Fix: raise both flanges to z 50 and move both screws to z 45. SF 3.4. Mass +2.2 g per tray.
- **Nacelle lug screws: open.** Handling gives SF 1.29 and the landing SF 1.24 against the low pull-out estimate. They pass (2.6 to 2.8) if the real pull-out is near the high estimate. The pull-out test below decides.
- **Clamp screw head bearing: marginal.** SF 1.62 at snug, 1.04 at strip.
  - Fix: an M2 washer with OD 5 and a 5.4 mm head seat. SF about 4.
- **Topple (the duck falls onto a nacelle end): every load path fails.**
  - Wing root: SF 0.07 to 0.14.
  - Lug screws: SF 0.14 to 0.43.
  - Pack posts: SF 0.39.
  - Nacelle beam: SF 0.43.
  - The root reaches its allowable with about 16 N at the nacelle tip. The sim strike is 131 N.
  - Material and section changes do not fix this. It has to be prevented: in the sim, keeping the fans at 40 to 50 % after touchdown keeps the duck up. Otherwise, treat a fall as a reprint of the wing plate.
- **Nacelle inner half under handling: marginal.**
  - Hand calculation: SF ≥ 2.6 in every case outside the topple.
  - FEA, handling case: 13 to 14 MPa (solid) at the lug root and at x −36, about 18 MPa printed, so SF about 1.8. This comes from shear lag, at 2 to 3.6 × the hand value.
  - Fix, not computed: a 3 mm fillet where the lug meets the rear collar.
- **Pass:**
  - Tray deck: SF ≥ 2.4.
  - Ear pockets under thrust and motor torque: SF > 70.
  - Fan retention by clamp friction on landing: SF 2.4 with 10 % of the preload left.
  - Post screws outside the topple: SF ≥ 2.0.
  - Post-hole tear-out: SF ≥ 6.7.
- **Rerun needed if** the wing plate, nacelle halves or trays change: run everything below. The clamp geometry is already the current one, and nothing needs rerunning for it.

## Materials (design allowables = TDS strength × about 0.8, in the part's print orientation)

- **PLA:** 32 MPa in the layer plane, 17.5 MPa across layers. HDT 57 to 60 C. The allowable falls to about half at 55 C, so keep PLA away from the ESCs. Sources: Bambu PLA Basic TDS, Polymaker PolyLite PLA TDS.
- **PETG:** 38 / 19.5 MPa. HDT 69 C. Source: Bambu PETG Basic TDS.
- **PLA-CF:** 22.6 / 6.3 MPa. Weaker than PLA across layers, so do not use it. Sources: Bambu PLA-CF and Polymaker PLA-CF TDS.
- **PA-CF:** 65 / 32 MPa, dry. HDT 194 to 215 C. Needs a hardened nozzle (the X1C and H2S have one) and dried filament. Sources: Bambu PAHT-CF TDS, Polymaker PolyMide PA6-CF TDS (dry and at 70 % RH).
- **Print orientations:**
  - Wing plate: front face down, layers at x = const. The root bending stress σyy lies in the layer plane, so re-orienting cannot help.
  - Nacelles: upright, layers at z = const. The hoop stress lies in the layer plane.
  - Tray: flat.
- **Printed section:** 4 walls (1.77 mm), 30 % gyroid (taken as 0.15 E) and skins, from the slice gcode headers. In the root band the printed stress is 1.3 to 1.6 × the solid-section stress.
- **M2 thread-forming screw in a 2.15 mm horizontal pilot:** no published pull-out value exists, so 120 N (low) and 260 N (high) are used, with low as the design value. Snug preload is 167 N (0.1 N·m, K = 0.3).

## Load cases

- **Thrust:** 980 g seller thrust × 1.5 per fan, along each canted axis, feet on the ground.
- **Landing:** 15.6 g upward trunk acceleration from a 0.3 m throttle cut at 2.44 m/s. Source: `sim/out/cut/cut03.json`, reproduced by `sim_contact_probe.py`.
  - The sim records `qacc`, which excludes gravity, so the side masses carry 16.6 g downward.
  - At that instant the feet carry 304 N and the nacelles nothing.
- **10 g fore-aft and 10 g sideways:** inertia of the side assemblies only. Per side: fans 160 g, nacelle 47 g, tray 15 g, battery 151 g, straps 19 g.
- **Handling:** 2 kg lifted by one front collar, × 1.5.
- **Topple:** after landing, cut03 and the nominal hover landing both fall onto a nacelle end. The 10 ms mean nacelle contact force is 131 N, under soft MuJoCo contact (20 ms), so a hard floor gives more.
  - Crash cases reach 275 to 615 N. They are not design cases.
- **Clamp preload:** snug, and up to the strip load.
- **Motor torque:** 82 N·mm × 1.5.
- **Vibration:** not modelled (see limits).

## Method and hand-vs-FEA check

- **Hand calculations** (`hand_calcs.py`):
  - Sections cut from the built meshes and weighted for the printed structure, with unsymmetric bending and open-section torsion.
  - Bolt groups as a rigid plate on compression-only contact with tension-only screws.
  - Clamp wall as an eccentric strip.
- **FEA** (`fea_run.py`, scikit-fem):
  - Linear hex voxels at 0.6 mm, solved with pyamg CG on the Mac mini, solid isotropic.
  - Its section stress is multiplied by the hand printed/solid ratio before the verdict.
  - Moment equilibrium at the cuts matches the applied loads within about 4 %.
  - Corner peaks (99 to 1219 MPa) sit on stair-stepped re-entrant edges. They mark where a crack starts and are not used as nominal values. The two weak corners: the band's lower front lip meets the column lip at y 28.5, z 9; and, in the clamp, the block ends.
- **Disagreements over 30 %:**
  - **Wing root, vertical cases:** FEA is 2.3 to 2.7 × hand at y 21 to 29. The fans sit ahead of the root, so every vertical load also twists the root. The posts stop the open section from warping, so the twist shows up as normal stress (restrained warping). The hand model treats it as free shear only: torsion shear SF 0.9 at landing. The FEA value governs.
  - **Wing root, fore-aft and lateral:** 1.3 to 1.6 × hand at y 21 and 31, and 2.1 × at y 29 beside the corner. Cause: shear lag and the corner.
  - **Nacelle inner half near the lug:** 1.8 to 3.6 × hand, from shear lag. The section is short and thin-walled, so the beam model spreads the stress too evenly. The FEA value governs, and it puts handling at SF about 1.8.
  - **Nacelle under the topple:** within 30 %.
  - **Clamp:** hand 76 MPa nominal, FEA 157 to 217 MPa at the block-end corner. Same place and same sign.

## Fixes, sized

The required order was: section, then orientation, then carbon, then material. All numbers are in `results.json → fixes`, `clamp`.

- **Root, as a package:**
  1. Raise the band to z 42.5 in the slot between the backpack (x −50.5) and the saddle zone (x −46.5), and fill the band/column corner (`fea_setup.py ROOT_FIX`, +1.0 cm³, about 1.3 g). Alone this gives a moderate gain:
     - Landing at y 25: SF 0.85 → 1.64.
     - Handling at y 25: SF 1.07 → 2.09.
     - Fore-aft: SF 0.45 → 0.47.
  2. Print the wing plate in PA-CF at 100 % infill: 54 g PLA-equivalent volume, about 52 g PA-CF, +13 g.
  3. Bond a 3 mm carbon rod in the slot (`cad/checks/variant_root_rod.json`). It cuts the fore-aft root stress to 0.43 to 0.55 of today. Its retention needs epoxy, or a reprinted backpack front plate with a lip.
  - Package result: fore-aft 10 g SF 2.3 to 2.7; vertical cases SF 2.2 to 2.9 without the rod.
  - Sideways 10 g stays at SF 1.8 at y 29 (1.9 at y 21). The rod is not credited there: its effect on a sideways load was not modelled.
  - Without PA-CF, the best PLA or PETG option reaches SF 1.1 to 1.3. Thicker sections in x are blocked by the backpack and the saddle.
- **Clamp:** a 7.0 mm wall at the block ends gives SF 2.0 at snug and 2.8 at 120 N. The wall face stays 4.0 mm from the screw axis, which keeps the driver corridor. Holding the fan on landing needs only about 13 N per screw, so most of the preload is excess.
- **Tray:** with the flanges raised to z 50, the screws at z 45 pull against a 23 mm lever instead of 9 mm. The web face reaches z 59 at y 40 to 66, and the battery starts at x −36, behind the flange.
- **Lug:** a fourth screw in a second column barely helps (SF 1.29 → 1.46). The joint's verdict comes from the pull-out test.

## What the calculation cannot show

- Layer-adhesion scatter between printers and spools. Allowables are TDS values for dry filament.
- Brittle impact behaviour of PLA: strain-rate effects and notch sensitivity at the stair-stepped corners.
- Vibration fatigue from four EDFs, and creep of preload in PLA. Friction retention is checked with 10 % of the preload left.
- Heat from the ESCs on the FC bracket and nearby PLA.
- The real topple force on a hard floor.
- The M2 pull-out capacity in these pilots. This is the largest gap: it sets the tray, lug and post verdicts and the clamp preload ceiling.

**Cheap test that closes the largest gap:** print a 20 × 20 × 12 mm PLA block with the same 2.15 mm horizontal teardrop pilot and slicer settings. Drive an M2 × 10 thread-former to 4.8 mm bite. Hang weights from the screw head until it pulls out. Above about 195 N the lug and tray joints pass as built; below 120 N they need the tray fix and inserts.

## Reproduce

- **Hand calculations**, a few seconds: `/tmp/microduck-cad-venv/bin/python strength/hand_calcs.py` writes `out/hand_calcs.json`.
- **FEA inputs:** `/tmp/microduck-cad-venv/bin/python strength/fea_setup.py` writes `out/fea_inputs.json` and the STL copies.
- **FEA on the Mac mini:**
  1. Rsync `strength/` to `~/code/flight-strength-mirror/strength/`.
  2. Run `.venv/bin/python strength/fea_run.py <wing|wing_fix|nacelle_inner|nacelle_outer_preload> --h 0.6`. About 1 to 2 minutes per model.
  3. Rsync `out/fea_*.json` and the PNG files back.
- **Merge and fixes:** `/tmp/microduck-cad-venv/bin/python strength/build_results.py` writes `results.json`.
- **Sim contact forces:** `strength/sim_contact_probe.py <case>` in the flight-sim mirror (`sim/mini.sh`).
- **Stress plots:** local only, because the repository does not track images. All are in `out/`. The four most useful:
  - `out/fea_wing_fore_aft_10g.png`
  - `out/fea_wing_vertical_impact_15.6g.png`
  - `out/fea_wing_topple_strike_front_end.png`
  - `out/fea_nacelle_outer_preload_preload_snug.png`
