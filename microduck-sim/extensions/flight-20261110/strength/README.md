# Flight pack: printed-part strength check

Geometry: commit `821288b7` plus the M3 lug screws of 2026-11-11 (wing plate with the arm root wedge, the R 2.5 slot fillet and 3.5 mm lug clearance holes; nacelle inner halves with 3.1 mm M3 lug pilots; STL prefixes in `cad/slices/release-FlightPack-D1/STATUS.json`). The wing, nacelle inner and hand calculations were rerun on it; the clamp and FC bracket numbers below are from `480610d1` (their parts did not change). Before that, commit `480610d1` (cable-gate round E). It adds a camera-cable notch at the left arm's inner upper corner (x −51..−44.9, y 37.8..43, z 47..54) and makes the battery lead windows 11 × 18 in both arms. The two inner ribs per side are now rear-open slots over z 22..34. The centre flat window is raised from 4.9 to 7.0, the FC bracket window is 11 × 17.5, and the old fan window is filled. The nacelle clamp screws are M2 × 12 with shallower counterbores. Both print plates are now at 100 % infill (Orange since 6fa0d176, Black since 4fed9fa5). STL sha256 prefixes: wing_plate `541b5c193bfb6200`, tray_L `9cffe3d30bf8900a`, nacelle_inner_L `34dcd547be3383aa`, nacelle_outer_L `76dcde97dd4a0ea8`, fc_bracket `d5edc0088c51581f`. All numbers are in `results.json`: `gates`, `summary_by_case`, then the rows. Earlier rounds are under `history`.

## Gates

Shawn's decision (2026-11-10) is PLA, with crash cases excluded from the design gates ("不用考虑极端情况"). The gates are therefore peak thrust × 1.5, lift by either nacelle and clamp preload at assembly, with target SF 2. The left and right arms are no longer mirror images, so each side is checked on its own.

## Conclusion

Thrust passes on both sides. Lift by one nacelle is now **SF 1.67 on the left and 1.70 on the right** (it was 1.84). Two small CAD additions bring it to 1.79 / 1.73. What remains under 2 is the root band top edge at |y| 20.7. That edge was already there, and the earlier 1.84 came from a cut that missed it. No local fix for it fits in the available space. The clamp passes nominally, but its corner peaks sit near SF 1. Half of snug torque fixes that.

**Wing plate, FEA von Mises on the cut (the FEA decides):**
- **Peak thrust × 1.5 (gate):** left SF 2.9 at the arm root y 40 (11.0 MPa), right 3.0 at y −40. The roots are at 3.16 to 3.27. Pass; it was 3.07.
- **Lift by the left nacelle (gate):** SF 1.67 at y 40 (19.1 MPa at (−45.9, 39.9, 17.7)). This is where the arm underside steps up from the column bottom at z 9 to the web bottom at z 18. The rear-open slots and the cable notch took section out of this spot. The root edge at y 20.7 gives 18.2 MPa (SF 1.76), and the slot top corner at y 38.5 gives 17.6 MPa.
- **Lift by the right nacelle (gate):** SF 1.70 at y −20.7 (18.8 MPa, on the band top edge at x −50.1, z 27.9). The arm root at y −40 gives 18.2 MPa (SF 1.76).

**Smallest local fix, both checked in FEA (`VARIANTS` in `fea_setup.py`):**
1. **Wedge under each arm web** (variant `wing_arm_root_wedge`). The wedge spans x −50.2..−45. It fills the step from the column bottom up to the web: at |y| 37.9 it runs z 9..18.1, and at |y| 43.9..46 it runs z 15.75..18.1, a linear ramp between. It goes on both arms, adds 0.28 cm³ in total, and stays below the web, away from the camera notch (z 47..54) and the lead windows. Left y 40 drops from 19.1 to 13.5 MPa.
2. **R 2.5 fillet at the top front corner of each rear-open gusset slot** (variant `wing_wedge_slot_corner`). The corner is at x −52, z 34, in both arms. Left y 38.5 drops from 17.5 to 15.3 MPa. The XT60 passes through this slot, so the CAD agent must rerun the cable and lead check after adding it.
- **With both fixes:** lift left SF 1.79 (y 20.7, 17.9 MPa), lift right 1.73 (y −20.7, 18.5 MPa; y −33 at 18.1). Thrust is unchanged at 3.2 or better.
- **What still caps lift at about 1.75:** the raised band starts at |y| 23, so the edge at |y| 20.7 carries the bending. The space below it is held clear for the backpack top plugs, so it cannot be filled. Reaching 2 there needs a different material: in PETG the same stress gives about 2.1, and in PA-CF about 3.6.

**Lug screws are M3 × 12 since 2026-11-11** (Shawn: "改成 M3"; three per side, 6.8 mm bite in a 3.1 mm teardrop pilot through the 8.2 mm lug, 3.5 mm clearance in the web). On the low pull-out estimate, lift by one nacelle is **SF 2.64** (92.9 N on the top screw against 245 N; it was 1.29 with M2 × 10) and peak thrust is **SF 5.74** (42.7 N; it was 2.81). Thread bearing: lift 6.7, thrust 12.9. With M3 × 10 (4.8 mm bite, the length RoboClub's list names) the same model gives lift 1.86 and thrust 4.05. The nacelle inner half FEA with the larger pilots is unchanged (lift: 13.8 MPa at x −36, 16.0 at x −25, lug root corner 22.7). The pull-out test below still decides the absolute value.

**Clamp under snug preload (gate):**
- **Hand:** wall bending SF 2.2, washer seat 4.0.
- **FEA:** the corner peak fell to 60.5 MPa at the block top corner (53.7, 119.2, 64.3). It was 77 MPa on 6fa0d176 and 217 in the first check. The collar's largest principal stress is 30.4 MPa on the middle web (−6.9, 119.8, 60.7) and 26.7 MPa at the rear collar. Most of the bore face sits at 10 to 20 MPa.
- **Verdict:** nominal SF is about 1.6 to 3, and about 1.05 at the local peaks.
- **Fix, an assembly instruction rather than geometry:** tighten to half of snug, about 0.05 N·m. The peaks then fall to about 15 MPa, SF about 2.1. Preload stays at about 83 N per screw against the 13 N the fan needs. At 260 N per screw the peak is 94 MPa, so do not overtighten.

**FC bracket:** FEA SF over 100 in every case, and its plate screws over 50. The 11 × 17.5 window has no strength effect.

**Nacelle inner half, lift (now solid):** 13.8 MPa at x −36 and 16.0 MPa at x −25, so SF about 2.0 to 2.3. The lug root corner peak is 22.7 MPa.

**Crash cases, information only:**
- **Landing 15.6 g:** wing root SF 1.13 to 1.17 at y ±20.7; post screws 2.13, tray screws 1.95, lug screws 2.37 (M3 × 12; 1.16 with M2 × 10).
- **10 g fore-aft:** wing root 1.12 to 1.18; post screws 1.27.
- **10 g sideways:** wing root 1.5 to 1.62; post screws 1.87.
- **Topple, 131 N on a nacelle end:** wing 0.26, post screws 0.27, lug screws 0.29 to 0.88 (M3 × 12). A topple breaks the plate.

## Materials (design allowables = TDS strength × about 0.8, in the part's print orientation)

- **PLA:** 32 MPa in the layer plane, 17.5 MPa across layers. HDT 57 to 60 C. The allowable falls to about half at 55 C, so keep PLA away from the ESCs. Sources: Bambu PLA Basic TDS, Polymaker PolyLite PLA TDS.
- **PETG:** 38 / 19.5 MPa. HDT 69 C. Source: Bambu PETG Basic TDS.
- **PLA-CF:** 22.6 / 6.3 MPa. It is weaker than PLA across layers; do not use it.
- **PA-CF:** 65 / 32 MPa, dry. HDT 194 to 215 C. Needs a hardened nozzle (the X1C and H2S have one) and dried filament. Sources: Bambu PAHT-CF TDS, Polymaker PolyMide PA6-CF TDS.
- **Print orientations:**
  - Wing plate: front face down, layers at x = const. The root stresses σyy and τ lie in the layer plane.
  - Nacelles: upright, layers at z = const.
  - Tray: flat.
- **Printed section:** the Orange plate (wing plate, trays, FC bracket) prints at 100 % infill and is taken as solid. The Black plate (nacelle halves) prints at 6 walls (about 2.7 mm a side) and 40 % gyroid since 2026-11-12 (`cad/make_slice_manifest.py`). The governing nacelle sections at x −36 and x −25 (94 and 122 mm²) have no point deeper than 2.7 mm from the surface, so they print solid and the solid-section FEA holds there; sparse core appears only in the thick screw blocks and ear-pocket regions, which carry low stress.
- **M2 thread-forming screw in a horizontal pilot:** no published pull-out value. The check uses 120 N (low) and 260 N (high) for a 4.8 mm bite, scaled by bite length; the low value is the design value. Snug preload is 167 N (0.1 N·m, K = 0.3).
- **M3 in a horizontal pilot (nacelle lug):** also no published value. Both ends of the M2 range are scaled by the threaded cylinder area, pilot diameter × bite (`common.pullout`): 3.1 / 2.15 × 6.8 / 4.8 = 2.04, so 245 N low and 531 N high for M3 × 12. The high end is thread shear on that cylinder, so it scales this way directly; the low end is a shell pull-out per mm whose perimeter grows with the diameter, which is an assumption.

## Load cases

- **Thrust (gate):** 980 g seller thrust × 1.5 per fan, along each canted axis, feet on the ground.
- **Lift by one nacelle (gate):** 2 kg lifted by one front collar, × 1.5. It is computed for the left and the right nacelle separately.
- **Clamp preload (gate):** snug, and up to 260 N per screw.
- **Landing (information):** 15.6 g upward trunk acceleration from a 0.3 m throttle cut (`sim/out/cut/cut03.json`, `sim_contact_probe.py`). The sim's `qacc` excludes gravity, so the side masses carry 16.6 g down.
- **10 g fore-aft and sideways (information):** inertia of the side assemblies only.
- **Topple (information):** the 10 ms mean nacelle contact force of 131 N under soft MuJoCo contact; a hard floor gives more.
- **FC bracket:** stack 30 g and flow sensor 4.5 g from `mass_budget.json`, under the same accelerations.
- **Masses:** from `mass_budget.json`, v7 case. Per side: ARESWEI fans 2 × 77 g at their own centre 45 mm down each axis, nacelle 53.8 g, tray 21.7 g, battery 151 g, straps and leads 19 g. Pack 967.2 g at (−18.0, −4.6, 34.2) in the guide frame.

## Method and hand-vs-FEA check

- **Hand calculations** (`hand_calcs.py`):
  - Sections are cut from the built meshes at ±y, with unsymmetric bending.
  - Saint-Venant torsion comes from the Prandtl stress function solved on the section raster. It matches Roark for an 8.5 × 19 rectangle: J within 0.1 %, τ within 3 %.
  - Bolt groups are a rigid plate on compression-only contact. The clamp wall is an eccentric strip. The FC bracket bolt group sits on the plate face at x −64.
  - The hand values on the right arm (y −35 and beyond) come out several times lower than on the left. The mirroring of the arm loads is not trusted there, and the FEA, which models both sides directly, is used.
- **FEA** (`fea_run.py`): linear hex voxels at 0.6 mm, about 940 k DOF, pyamg CG on the Mac mini, solid isotropic.
  - Each cut reports σnn, the shear on the cut and von Mises of the element-mean stress, away from supports and load patches.
  - Voxel layers sit at ±(0.3 + 0.6k) mm. A cut asked for at y 21 therefore landed at 21.3 on one side and 20.7 on the other. Cuts at 20.7 and 21.3 are now requested on both sides. The band edge at 20.7 is the higher of the two, and earlier rounds sampled only 21.3 on the left.
- **Hand vs FEA at the root (vertical cases):** FEA von Mises is 0.8 to 1.0 × the hand upper bound. FEA normal stress is about 3 × hand, because the posts restrain warping. FEA shear is 0.6 to 0.7 × hand, because the hand Prandtl peak sits on raster corners. Either way the FEA governs.
- **Corner peaks** (mesh-dependent, they mark crack start points, not nominal stress): clamp 60.5 MPa at the block top corner.

## What the calculation cannot show

- Layer-adhesion scatter between printers and spools. The allowables are TDS values for dry filament.
- Notch sensitivity of PLA at the band edge at |y| 20.7, the slot corners and the cable notch.
- Vibration fatigue, and creep of the clamp preload in PLA.
- ESC heat on the FC bracket.
- The real pull-out capacity of the M3 lug screws and the M2 tray, post and bracket screws in printed pilots.

**Cheap test that closes the largest gap:** print a 20 × 20 × 12 mm block on the plate settings (100 % infill) with the 3.1 mm horizontal teardrop pilot. Drive an M3 × 12 to a 6.8 mm bite and hang weights from the head until it pulls out. If it holds about 186 N, the lug screws keep SF 2 when lifted by one nacelle.

## Reproduce

- **Hand calculations,** about a second: `/tmp/microduck-cad-venv/bin/python strength/hand_calcs.py`.
- **FEA inputs:** `/tmp/microduck-cad-venv/bin/python strength/fea_setup.py`. The sizing variants are in `VARIANTS`.
- **FEA on the Mac mini:**
  1. Rsync `strength/` to `~/code/flight-strength-mirror/strength/`.
  2. Run `.venv/bin/python strength/fea_run.py <wing|nacelle_inner|nacelle_outer_preload|fc_bracket|wing_arm_root_wedge|wing_wedge_slot_corner> --h 0.6`. The wing takes about 4 minutes for 8 cases; the others are shorter.
  3. Rsync `out/fea_*.json` and the PNG files back.
- **Merge:** `/tmp/microduck-cad-venv/bin/python strength/build_results.py` writes `results.json`. It moves the previous round under `history` once.

## History

- **First check, geometry `1b392541`:** wing centre 3.5 mm, band 5.1 mm open section, 30 % infill.
  - Root SF 1.1 / 0.55 / 0.69 / 0.33 to 0.45 / 0.51 (thrust, landing, lift, fore-aft, sideways).
  - Clamp 0.42 at snug, tray screws 1.21.
  - The fixes proposed then (clamp end wall, tray third screw, washer, lug fillet, solid root band) were all built.
  - Full file: `git show 2458251d:microduck-sim/extensions/flight-20261110/strength/results.json`.
- **Rerun, geometry `6fa0d176`:** 8.5 mm solid root band, M2 × 12 posts, tray third screw.
  - Thrust 3.1, landing 1.37, lift 1.84 (left only; that cut missed the y 20.7 edge), fore-aft 1.28, sideways 1.51.
  - Clamp FEA corner peak 77 MPa.
  - The PLA-vs-PA-CF discussion closed with Shawn's PLA decision.
  - Full file: `git show f9a4dc2e:microduck-sim/extensions/flight-20261110/strength/results.json`.
- **Spar option and thrust-centre studies:** `SPAR-OPTION.md`, summarised in `results.json → history`.
