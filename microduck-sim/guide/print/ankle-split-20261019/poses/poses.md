# Split-ankle print poses (2026-10-19)

One print pose per part for the six split-ankle parts of `build-pack-20260913/redesign-20260913/ankle-redesign-20261007/`
(left and right base, cheek, sleeve). The machine-readable result is `poses.json` in this directory: for every key the
chosen `sourceToPrint` 4x4 on the LOCAL STL frame (`ankle-redesign-20261007/STL/*-local.stl`, sha256 recorded), bed contact,
height, support on each machine, the functional faces and whether each is clean, the horizontal-hole handling, and every run file.
Nothing outside this directory was changed; no plate was released.

## Result in one paragraph

All six parts keep the 10/07 candidate poses (the 10/07 package was never printed; its README says so). Base: local +X down for the left, -X down for the right, the big gusset end face on
the bed, with the pipeline's R1 brim. Cheek: local +Z down, the two tab tops on the bed and the capture lip facing up, with the
R1 brim and support under the body. Sleeve: axial, no support, no brim. In every chosen pose every bearing, sliding and register
face rests on 0 mm2 of support and has 0 mm of support inside it on both machines. The support that remains sits on cosmetic
faces (base: one wing inner wall and part of the foot block; cheek: the exterior top). Two things are not settled by this study:
the Bambu brim review fails for the bases (brim in a real notch of the gusset end face), and the horizontal small holes have
not been drilled or test-screwed on a V1.22-profile print.

## Method

- **Screen.** `orientation_check.py` over the six parts (`manifest-screen.json`, identity sourceToPrint from the PRINT-STL files)
  plus the named local +-X/+-Y/+-Z poses in `extra-poses.json` (the 10/07 candidate poses and the print-review alternatives).
  Output `screen.json`, log `logs/screen.log`, resource report `logs/screen-resource.json`.
- **Functional-face rule.** `scripts/faces.py` selects face sets on the local-frame mesh and marks them MUST (slide, bear or
  register: must print without support under them) or REPORT (cosmetic, support allowed). Base MUST: motor mating face, four
  output screw seats, slot walls, post register faces, the two d1.6 pilots. Cheek MUST: d15 bearing pocket wall, inside
  capture lip, tongue sides and tips, tab register faces, the two d2.3 clearance bores. Sleeve MUST: bore, outer face, end faces.
- **Native slicing.** The top poses per part (`slice-plan.json`, 11 rows) were prepared and sliced on both machines with the
  V1.22 profiles through `release_pipeline_v2.py` (`prepare` then `slice`), every job under the bounded runner
  (`run_bounded_cad.py --max-mib 3000 --seconds 600`, lock wait 60 s, retried while the parent's print gate held the lock).
  Each slice was read back with the orientation study's `slice_readback.py` and checked face by face with
  `scripts/face_support.py`: a face rests on support when its centre lies within 1.0 mm in XY and 0 to 0.6 mm above a support
  toolpath midpoint; support inside a cavity is support toolpath length mapped back into the local cavity volume. The driver is
  `scripts/slice_poses.py`, log `logs/slice-plan.log` (exit 0). `logs/orca-cli-thumbnail-00000.log` is the slicer's own
  thumbnail-renderer complaint (no OpenGL in the CLI), harmless.
- **Decision.** `decisions.json` holds the written reasons; `scripts/build_poses.py` assembles `poses.json` from it and the run
  files and fails if a MUST face that is not clean has no written explanation. The chosen matrices were re-applied to the local
  STLs: min z = 0.000, heights 36.50 / 8.70 / 2.80 mm, determinant +1.

## Left base: local +X down (10/07 candidate pose)

- **Pose.** The big gusset end face on the bed: 81.1 mm2 contact, tip angle 2.8 deg, 36.5 mm tall, footprint 43 x 25.5 mm.
  `sourceToPrint` rows: (0 0 1 14.377), (0 1 0 3.55), (-1 0 0 21.837).
- **Why.** The only pose family where the motor mating face (399 mm2), the four output seats, the slot walls, the post
  register faces and the pilots all stand vertical or face up. All five MUST sets: 0 mm2 resting on support, 0 mm of support
  inside the pilots, the slot channels and the output holes, on both machines.
- **Support figures.** Bambu 28.8 min, 7.53 g, support 0.76 g / 6909 mm. Elegoo 25.8 min, 7.78 g, support 1.30 g / 12252 mm.
- **Faces still on support.** The inner wall of the lower wing (44.6 / 39.5 mm2; the cheek nests against it with zero nominal
  clearance, scrape the scar flat before the first fit). The underside of the lower slip-fit block (8.2 / 26.6 mm2; the V1.22
  foot socket slides over it with 0.2 mm clearance, file if it binds). The original gusset hole (Orca puts 22 mm of support in
  its counterbore; no function). The open fork between the wings holds the support towers (1408 / 993 mm), clear it fully.
- **Brim.** R1 default kept: outer_only 4 mm, gap 0.1 mm. Elegoo review passes (199 mm2). Bambu review fails: 13.3 mm2 of
  brim lies inside the part's convex outline because Bambu's brim loops into the real 12 x 1.1 mm recess on the inner side of
  the gusset end face (the community-66 notch next to the gusset hole); Orca's does not because its support feet stand there.
  That strip is bonded on three sides, cut it out with a blade.
- **Horizontal holes.** The two d1.6 TAP pilots and the original output screw holes (d4.4 counterbores) are horizontal in
  this pose. They print, but small horizontal FDM holes come out 0.2-0.4 mm under size (ceiling sag); no print exists, so the
  real diameter is unmeasured. Preferred fix without drilling: a teardrop (pointed-top) profile on these holes in
  `generate_candidate.py`, or a modelled oversize after one measured print. Drilling is the last resort only if a printed
  pilot refuses the TAP screw. A pose with these holes vertical (local Y down) has 1.5 / 5.4 mm2 of contact, not printable.
- **Rejected.** Local -X down (mirror, small wing end on the bed): functional faces equally clean, less support (5145 / 9718 mm)
  but more foot block on support (22.7 / 53.3 mm2) and the same Bambu notch (15.3 mm2); the pose with less foot block on support wins (no print exists on either side).
  Local -Z tilted onto the foot facets (screen favourite, 316 mm2 contact, no brim): the output seats face down 2.9 mm above
  the bed and rest on support on Elegoo (35.5 mm2), the foot shoulder is fully on support, Bambu fills the slot channels
  (7.2 mm) and the pilots (3.3 mm) with support.

## Right base: local -X down (10/07 candidate pose)

- **Pose.** Mirror of the left base: 81.1 mm2, tip 2.8 deg, 36.5 mm tall. `sourceToPrint` rows: (0 0 -1 -14.377),
  (0 1 0 3.55), (1 0 0 21.837).
- **Support figures.** Bambu 28.7 min, 7.55 g, support 0.77 g / 7150 mm. Elegoo 25.3 min, 7.73 g, support 1.24 g / 11797 mm.
  MUST faces all clean on both machines.
- **Faces still on support.** Lower wing inner wall (44.6 / 37.3 mm2, same scrape), foot block underside (8.2 / 37.0 mm2),
  gusset hole (Orca 21 mm inside), fork opening (932 / 1026 mm).
- **Brim and holes.** Same as the left base: R1 brim kept, Elegoo review passes, Bambu fails on the same 13.3 mm2 notch;
  pilots and output holes horizontal, teardrop or measured oversize first, drilling last resort.
- **Rejected.** Local +X down (mirror): clean but more foot block on support, same Bambu notch (15.3 mm2); the 7.6 mm2 "near"
  count on the motor face is side proximity only.

## Left cheek: local +Z down (10/07 candidate pose)

- **Pose.** The two 7 x 4 mm tab tops on the bed (57.6 mm2, two islands), capture lip facing up at print z 5.6 mm, 8.7 mm tall,
  footprint 30 x 25.5 mm, tip angle -44.3 deg (not self-standing). `sourceToPrint` rows: (1 0 0 0), (0 -1 0 -3.55), (0 0 -1 7.1).
- **Why.** The bearing pocket wall stands vertical with 0 mm of support inside the pocket, the lip is a clean top surface, the
  tongues print as upright ribs (49-54 mm of toolpath, the 0.4 mm rib is printed), the tab register faces are vertical walls,
  the d2.3 clearance bores are bridged with 0 mm inside. All six MUST sets clean on both machines. The body floats 4.1 mm
  above the bed on support and the exterior top takes the scars instead of the lip.
- **Support figures.** Bambu 16.4 min, 2.54 g, support 0.81 g / 7743 mm. Elegoo 10.2 min, 2.44 g, support 0.93 g / 9089 mm.
- **Faces still on support.** Exterior top planes and sloped ring top (279.6 / 272.5 mm2, cosmetic outside of the ankle). The
  d14 window above the lip (Orca 54 mm of support inside; nothing slides there, pick it out). The two open post pockets
  beside the tabs hold the body support (145 / 398 mm); the register faces beside them are vertical and clean; clear before
  fitting.
- **Brim.** R1 default kept: outer_only 4 mm, gap 0.1 mm; brim review passes on both machines (129 / 122 mm2, reach 4.02 mm).
  The brim and the support under the body hold the two tab pads; the no print of this design exists yet, so this is untested.
- **Horizontal holes.** The two d2.3 clearance holes (local Y, 4.5 mm long) are horizontal and bridged. A clearance hole only
  has to pass the M2 shank: a teardrop profile or 0.2 mm modelled oversize in `generate_candidate.py` removes any binding;
  drilling is the last resort.
- **Rejected.** Local -Z down (lip down, 59 mm2 strip on the bed): less support (2510 / 1384 mm) but the capture lip faces down
  at print z 3.1 and rests on support on Bambu (22.6 mm2, 966 mm of support inside the pocket) or is an unsupported 0.5 mm
  overhang on Elegoo; the 193 mm2 inner face 0.3 mm above the bed prints as overhang wall plus 289 mm of bridge; tab
  undersides (54 mm2) on support; brim review fails on both machines (67.9 mm2 inside the outline). Side poses (+-X, +-Y) were
  dropped at the screen: 21.8 mm2 on one pad or no stable rest, and a horizontal pocket ceiling.

## Right cheek: local +Z down (10/07 candidate pose)

- **Pose.** Mirror of the left cheek, same matrix rows (1 0 0 0), (0 -1 0 -3.55), (0 0 -1 7.1); 57.6 mm2, 8.7 mm tall.
- **Support figures.** Bambu 16.4 min, 2.55 g, support 0.81 g / 7723 mm. Elegoo 10.2 min, 2.46 g, support 0.94 g / 9049 mm.
  All six MUST sets clean on both machines.
- **Faces still on support.** Exterior top (261.6 / 270.9 mm2), lip window (Orca 47 mm inside), post pockets (146 / 455 mm).
- **Brim and holes.** R1 brim kept, review passes (134 / 122 mm2); clearance bores horizontal and bridged, teardrop or
  0.2 mm oversize first, drilling last resort.
- **Rejected.** Local -Z down: lip on support on Bambu (22.4 mm2, 1052 mm inside the pocket), brim review fails on both
  machines (67.9 mm2 inside the outline, Bambu reach 4.67 mm against the planned 4.1).

## Left and right sleeve: axial (10/07 candidate pose)

- **Pose.** Local -Z down; the mesh is exactly z-symmetric and the two files are identical (same sha256), so +Z down and the
  right sleeve are the same print. 66.8 mm2 annular contact, 2.8 mm tall, 14.6 mm round, tip 79 deg.
  `sourceToPrint` rows: (1 0 0 0), (0 1 0 0), (0 0 1 1.4).
- **Support figures.** Bambu 10.2 min, 0.60 g, 0 support. Elegoo 2.9 min, 0.39 g, 0 support. No brim (R1: tip 79 deg).
- **Faces.** Bore and outer face are vertical walls, the end faces are the first and the top layer; the bore is vertical, no
  drill pass. Fit check only: the bore has 0.4 mm nominal diametral clearance on the lower-link d10 boss (DESIGN-NOTES);
  a 10.4 mm reamer is the fallback, not a pose change.

## Open items for the release

- **Bambu brim review on the bases.** `brim_review()` fails both bases on the Bambu (13.3 mm2 of brim inside the convex
  outline, the gusset end-face notch). The parts need the brim (2.8 deg tip, 36.5 mm on a 2.3 mm strip). Options: accept
  the failed check with a written reason for these two objects, or print the bases on the Elegoo only (passes).
- **Base stability.** Tall and narrow; keep the brim, print the two bases on one plate so each layer is short.
- **Wing inner wall scar against a zero-clearance nest.** A 0.1 mm side clearance in `generate_candidate.py` would remove
  the scrape step; that is a geometry change and was not made.
- **Horizontal small holes.** Shawn rejects drilling. The base pilots and output holes and the cheek clearance bores are
  horizontal in every printable pose; the no-drill route is a teardrop (pointed-top) profile or a measured oversize in
  `generate_candidate.py` (geometry change, not made here). No print of this design exists, so the diameters are unmeasured.
- **Cheek pose deviates from R1.** Not self-standing (tip -44.3 deg), body on support. Accepted because every bearing,
  sliding and register face is clean and the alternative puts the lip on support.
- **Tongue rib.** 0.4 mm wide, one extrusion; both slicers print it (49-54 mm per cheek). Check it is present before fitting.

## Runs and files

- Screen: `screen.json`, `logs/screen.log`, `logs/screen-resource.json`; inputs `manifest-screen.json`, `extra-poses.json`,
  `local-to-printstl.json` (built by `scripts/make_screen_inputs.py`).
- Slices: `slices/<key>/<slug>/` with `manifest.json`, `pose.json`, `prepare.log`, `prepare-resource.json`,
  `run/preparation.json`, `run/native/<Color>_<Machine>/sliced.3mf` and `result.json`, `slice-<Machine>.log`,
  `slice-<Machine>-resource.json`, `readback-<Machine>.json` and `.log`, `faces-<Machine>.json` and `.log`;
  driver log `logs/slice-plan.log`.
- Renders: `renders/*-local.png` (local-frame views with the hole axes), `renders/left_base-x-pos-down-Bambu.png` and
  `renders/left_base-x-pos-down-firstlayer-zoom.png` (first layers and brim), `renders/holes-local.json`.
- Scripts: `scripts/make_screen_inputs.py`, `scripts/faces.py`, `scripts/slice_poses.py`, `scripts/face_support.py`,
  `scripts/plot_layers.py`, `scripts/brim_where.py`, `scripts/render_local.py`, `scripts/build_poses.py`.
