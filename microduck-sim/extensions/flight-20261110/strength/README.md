# Flight pack: printed-part strength check

Geometry: commit `6fa0d176`. The wing root band is solid to x −53.5, out to |y| 32.1, with the corner filled. The wing centre is 6.9 mm thick. The post screws are M2 × 12 with a 3.1 mm bite, and the backpack sits 3.4 mm further back. The Orange plate prints at 100 % infill. The inner tray flange rises to z 50 with a third screw at (46, 45). The clamp collar wall is 7.4 mm at the block ends, with M2 washers, and the lug has a 3 mm fillet. STL sha256 prefixes: wing_plate `18a9cdd3d1a161fb`, tray_L `0898024d71a26756`, nacelle_inner_L `c9e9875c704a041c`, nacelle_outer_L `7b646b6cd392b989`. All numbers are in `results.json`: `summary_by_case`, then the rows. Earlier rounds are under `history`.

## Conclusion

The wing root is three times stronger than before, but it still misses SF 2 in plain PLA in the landing, fore-aft and sideways cases. Within the space that exists, no depth or fillet reaches SF 2. The smallest step that does is printing the wing plate in PA-CF. The topple still breaks the plate.

**Wing plate, FEA von Mises on the cut** (the FEA decides). Each line gives the first-check SF, then the SF now, then where the worst section is:
- Peak thrust × 1.5: 1.1 → 3.1, at the arm root, y 40.
- 15.6 g landing: 0.55 → 1.37, at the band top edge, y 21. The arm root at y 40 gives 1.40.
- Lift by one nacelle: 0.69 → 1.84 at y 40; the root at y 21 gives 1.95.
- 10 g fore-aft: 0.33 to 0.45 → 1.28, where the deep part ends at y 33. The band at y 21 gives 1.37.
- 10 g sideways: 0.51 → 1.51, at y 33.
- Topple, 131 N on a nacelle end: 0.07 to 0.14 → 0.26. Still a reprint.

**What still fails at SF 2, and the smallest fix:**
- **Wing plate in PLA** (landing 1.37, fore-aft 1.28, sideways 1.51, handling 1.84).
  - Carrying the 8.5 mm depth out to the gusset above and below the cross harness (variant `wing_deep_transition`, +0.6 cm³) lifts y 33 to 40. Even so, fore-aft drops to 1.20 at y 29 and the landing stays at 1.36 at y 21.
  - The y 21 band is boxed in: the backpack front is at x −53.9, the backpack top plugs need 2 mm at |y| ≤ 21 below z 43, the shell lip is below.
  - One line: no PLA geometry in this space reaches SF 2. The wing plate in PA-CF at 100 % infill (65 MPa) reaches 2.6 fore-aft, 2.8 landing and 3.0 sideways. PETG (38 MPa) gives 1.5, which is not enough.
- **Post screws, 10 g fore-aft: SF 1.31** (was 2.0 with a 4.5 mm bite). Sideways 1.93, landing 2.21.
  - The 3.1 mm bite carries 65 % of the 4.8 mm thread.
  - A full 4.8 mm bite would give 2.0. That needs a 13.7 mm screw: M2 × 14 bottoms in the 4.8 mm pilot, and M2 × 12 is what is stocked.
  - If the pull-out test below gives the high estimate (260 N), the post screws pass at 2.8.
- **Tray screws, landing: SF 1.96** (was 1.21). The third screw takes 61 N. It misses 2.0 only because the tray at 100 % infill now weighs 21.7 g instead of 14.5 g. The flange layer interfaces pass at 2.3 or more.
- **Lug screws: SF 1.24 landing, 1.29 handling.** Unchanged and still open. The pull-out test decides.
- **Clamp under snug preload: improved, still marginal in FEA.**
  - Hand: SF 2.2 at snug (was 0.42), 1.4 at the 260 N high pull-out.
  - FEA: the corner peak fell from 217 to 77 MPa. A band of 30 to 45 MPa now sits on the bore face where the thick wall tapers back to 3.4 mm, about SF 0.7 to 1.1 at snug. The bending moved off the block end to the end of the taper.
  - The fan needs only about 13 N per screw on landing. A quarter of hand-snug torque (about 0.025 N·m) keeps the clamp at SF 2 or more with 3 × margin on retention. Alternatively, run the 7.4 mm wall over 20 mm of arc before it tapers. Neither is computed in FEA.
- **Nacelle inner half, handling:** FEA 12.9 MPa solid at the lug end of the beam (x −36), about 17 MPa printed, so SF about 1.9. The 3 mm fillet barely changed the lug root (24.1 → 22.7 MPa corner peak). Marginal, as before.
- **Topple:** every load path is below SF 0.5 (wing 0.26, post screws 0.27, lug screws 0.14 to 0.43, nacelle beam 0.46). This is still prevented in flight control (fans at 40 to 50 % after touchdown) or accepted as a wing-plate reprint.

**Pass:** tray deck SF ≥ 3.1, tray flange layers ≥ 2.3, post-hole tear-out ≥ 10, washer seat 4.0 at snug, ear pockets and motor torque > 70, fan friction retention 2.5 with 10 % of the preload left.

## Materials (design allowables = TDS strength × about 0.8, in the part's print orientation)

- **PLA:** 32 MPa in the layer plane, 17.5 MPa across layers. HDT 57 to 60 C. The allowable falls to about half at 55 C, so keep PLA away from the ESCs. Sources: Bambu PLA Basic TDS, Polymaker PolyLite PLA TDS.
- **PETG:** 38 / 19.5 MPa. HDT 69 C. Source: Bambu PETG Basic TDS.
- **PLA-CF:** 22.6 / 6.3 MPa. Weaker than PLA across layers, so do not use it.
- **PA-CF:** 65 / 32 MPa, dry. HDT 194 to 215 C. Needs a hardened nozzle (the X1C and H2S have one) and dried filament. Sources: Bambu PAHT-CF TDS, Polymaker PolyMide PA6-CF TDS.
- **Print orientations:**
  - Wing plate: front face down, layers at x = const. The root stresses σyy and τ lie in the layer plane.
  - Nacelles: upright, layers at z = const.
  - Tray: flat.
- **Printed section:**
  - The Orange plate (wing plate, trays, FC bracket) is at 100 % infill (`cad/make_slice_manifest.py`), so it is solid. The plate has not been resliced yet.
  - The Black nacelles keep 4 walls (1.77 mm) and 30 % gyroid, taken as 0.15 E.
- **M2 thread-forming screw in a horizontal pilot:** no published pull-out value. 120 N (low) and 260 N (high) for a 4.8 mm bite, scaled by bite length; low is the design value. Snug preload is 167 N (0.1 N·m, K = 0.3).

## Load cases

- **Thrust:** 980 g seller thrust × 1.5 per fan, along each canted axis, feet on the ground.
- **Landing:** 15.6 g upward trunk acceleration from a 0.3 m throttle cut (`sim/out/cut/cut03.json`, `sim_contact_probe.py`). The sim's `qacc` excludes gravity, so the side masses carry 16.6 g down.
- **10 g fore-aft and sideways:** inertia of the side assemblies only.
- **Handling:** 2 kg lifted by one front collar, × 1.5.
- **Topple:** the 10 ms mean nacelle contact force of 131 N, under soft MuJoCo contact, so a hard floor gives more.
- **Clamp preload:** snug, and up to 260 N per screw.
- **Masses:** from `mass_budget.json`, v7 case. Per side: ARESWEI fans 2 × 77 g at their own centre 45 mm down each axis, nacelle 53.8 g, tray 21.7 g (solid), battery 151 g, straps and leads 19 g. Pack 967.2 g at (−18.0, −4.6, 34.2) in the guide frame.

## Method and hand-vs-FEA check

- **Hand calculations** (`hand_calcs.py`):
  - Sections cut from the built meshes, unsymmetric bending.
  - Saint-Venant torsion from the Prandtl stress function solved on the section raster. It matches Roark for an 8.5 × 19 rectangle: J within 0.1 %, τ within 3 %. This replaces the earlier per-row Σ t³/3. At y 35 to 60 (web plus flanges) the old method overstated J several times and under-reported the arm torsion; at the root band it was close.
  - Bolt groups as a rigid plate on compression-only contact. Clamp wall as an eccentric strip.
- **FEA** (`fea_run.py`): linear hex voxels at 0.6 mm, about 940 k DOF, pyamg CG on the Mac mini, solid isotropic.
  - Each y cut reports σyy, the shear on the cut and von Mises of the element-mean stress, away from supports and load patches.
  - The torque about each root cut matches the hand value within 1 %. Arm cuts (y 45, 60) differ where a load patch straddles the cut.
- **Hand vs FEA at the root:**
  - Normal stress, vertical cases: FEA is 2.9 to 3.2 × hand at y 21 to 29, because the posts restrain warping. Compare 2.3 to 2.7 × for the open band.
  - Shear: FEA is 0.6 to 0.7 × hand, because the hand Prandtl peak sits on raster re-entrant corners.
  - Combined, vertical cases: FEA von Mises is 0.8 to 1.0 × the hand upper bound.
  - Combined, fore-aft and sideways: FEA is 1.7 to 3.0 × hand, from shear lag at the band step and the deep-part edge.
  - Either way the FEA governs.
- **Arm, y 35 to 60:** the hand free-warping torsion of the open web gives SF 0.6 to 1.0 in the landing case. The FEA gives 0.15 to 0.4 × that, because the gussets and the tray and lug patches restrain the web. The FEA value is used.
- **Corner peaks** (not nominal values): 43 MPa in the landing case at (−53.1, 22.5, 27.9), where the raised band starts at y 23. Clamp: 77 MPa at the top edge where the thick wall ends.

## What the calculation cannot show

- Layer-adhesion scatter between printers and spools. Allowables are TDS values for dry filament.
- Brittle impact behaviour of PLA and notch sensitivity at the band step at y 23 and the deep-part edge at y 32.
- Vibration fatigue, and creep of clamp preload in PLA.
- ESC heat on the FC bracket.
- The real topple force on a hard floor.
- The M2 pull-out capacity, which still sets the post, tray and lug verdicts.

**Cheap test that closes the largest gap:** print a 20 × 20 × 12 mm block on the Orange plate settings (100 % infill) with the 2.15 mm horizontal teardrop pilot. Drive an M2 × 10 to 4.8 mm bite and hang weights from the head until it pulls out; repeat at 3.1 mm bite for the post screws. Above about 125 N at 4.8 mm, the tray screws pass. Above about 195 N at 4.8 mm, the lug screws pass. Above about 120 N at 3.1 mm, the post screws pass.

## Reproduce

- **Hand calculations**, about a second: `/tmp/microduck-cad-venv/bin/python strength/hand_calcs.py`.
- **FEA inputs:** `/tmp/microduck-cad-venv/bin/python strength/fea_setup.py`. The sizing variants are in `VARIANTS`.
- **FEA on the Mac mini:**
  1. Rsync `strength/` to `~/code/flight-strength-mirror/strength/`.
  2. Run `.venv/bin/python strength/fea_run.py <wing|nacelle_inner|nacelle_outer_preload|wing_deep_transition> --h 0.6`. About 3 to 4 minutes for the wing (7 cases), less for the others.
  3. Rsync `out/fea_*.json` and the PNG files back.
- **Merge:** `/tmp/microduck-cad-venv/bin/python strength/build_results.py` writes `results.json`. It moves the previous round under `history` once.
- **Plots:** local only. `out/fea_wing_vertical_impact_15.6g.png`, `out/fea_wing_fore_aft_10g.png`, `out/fea_nacelle_outer_preload_preload_snug.png`.

## History

- **First check, geometry `1b392541`:** wing centre 3.5 mm, band 5.1 mm open section, 30 % infill.
  - Root SF 1.1 / 0.55 / 0.69 / 0.33 to 0.45 / 0.51 (thrust, landing, handling, fore-aft, sideways).
  - Clamp 0.42 at snug, tray screws 1.21, post screws 2.0 fore-aft with a 4.5 mm bite.
  - Fixes proposed then: the clamp end wall, the tray third screw, the washer and the lug fillet are now built. The root package (corner fill and solid section) was built as the 8.5 mm solid band, after `SPAR-OPTION.md` showed that the twist lever is physical.
  - Full file: `git show 2458251d:microduck-sim/extensions/flight-20261110/strength/results.json`. A compact copy is in `results.json → history`.
