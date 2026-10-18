# MicroDuck V1.12 print release plan

Status: plan written 2026-10-14; the release ran the same evening under the decisions below (`manifest-V1.12.json`, `run/`). The per-object brim landed in `release_pipeline_v2.py`.

Problem IDs: P5, P6 (as in V1.9 and V1.11).

**Decisions after this plan (Shawn, 2026-10-14). They override sections A2, B2, B3 and B4 where those differ.**

- **White plate only.** The release is one White plate: `shell_left_v20`, `shell_right_v20`, `thigh_left` (community-74), `thigh_right` (community-72) and the head cap. Each replaces its orange print, which becomes a spare on the retired-parts sheet.
- **Yellow plate deferred.** `head_bottom_v20` and `jaw_frame_v20` are not in V1.12. Print them when the head is next opened.
- **Cap stays V1.9 and M2.6.** The cap on the White plate is the V1.9 cap (`ext-v19/head_cap_v19-world.stl`, sha256 `da655c65…`) printed white, manifest key `head_cap_v19_white`. Its closing pilots stay for the three ROBOTIS M2.6 × 6 (K-head_close-01..03). The lower head shell and jaw support stay M2.6 this run, so an M2 cap would mix two sizes in the head, and the OMX kit M2.6 screws are on hand. `head_cap_v20` (the M2 × 8 re-cut) is deferred with the Yellow parts.
- **Rear pack.** The V1.9 rear pack is on the robot, so the V2.0 shells screw into its shoulder bars.
- **Support.** The club X1C has an AMS but no support material. Single-material support stays, with the C4 interface settings and support ironing on the cap; light sanding of the crown is accepted.

**Summary.**

- **One new White plate.** It holds the two V2.0 side shells, the two stock thighs and the V2.0 head cap, about 85 g. This is colour scheme C, and it also carries the shell and cap changes that were designed but never printed.
- **Optional Yellow plate.** It holds the V2.0 lower head shell and the V2.0 jaw frame, about 65 g. These are the last unprinted V2.0 changes, and fitting them means taking the head apart.
- **Orange V1.11 box.** The released Orange V1.11 box (frame and cap) is the only part that can be printed today, and it stays its own job.
- **Head cap.** The rough area is the outer crown, the visible top of the head. Keep the dome-down pose. Carry the Orange support-interface settings onto the White plate, add support ironing on the cap, and prefer the X1C.

---

## A. Parts designed but not yet printed

Sources read: `PROJECT-CONTEXT.json` (`current_build` sections, including `printing_status`, `current_incremental_print_release`, `design_gate`, `v2_0_source`, `audio`, `servo_rail_7v_20261014` and `optional_ankle_prototype`), `release-V1.6-final` through `release-V1.11` (rows.json `decision`/`supersedes`, manifests), `world/v18-sources.json`, `v20-source/`, `shells-v19-source/`, `ext-v19/`, `candidates/` and `colour-study-20261014/`, plus the 10-SURFACE-QUALITY pack.

### How the robot is built today (2026-10-14)

- **V1.8 base.** The V1.8 set is printed and mostly assembled. `printing_status.user_statement_en`: "White and Yellow V1.8 are printed, Orange and Black V1.8 are printed too, and the robot is roughly assembled."
- **V1.9 Orange plate.** It is printed, but its small parts are not installed. The 2026-10-14 as-built facts: no microphone, no amplifier installed, and the V1.9 clips and speaker retainer are printed but not fitted. The speaker will be held by a foam-tape loop (`audio.speaker_mount`: "Two strips of 1 mm foam double-sided tape … butted into one closed loop"). That record also says "No CAD rerun", so the retainer needs no reprint.
- **Which rear pack is fitted: the records disagree.**
  - `release-V1.11/manifest-V1.11.json` prototypeScope says "the printed V1.8 pack stays as built".
  - `colour_as_built.json` lists `rear_pack` V1.8 as `"installed": true`.
  - `design_gate.physicalAcceptance` `v19_printed_and_fitted` reads `"accepted": false`.
  - `v20-source/README.md` says "The robot keeps … the V1.9 rear pack until then".
  - **This matters for the shells (section B2).** Shawn can settle it by looking at the pack: the V1.9 pack has the BNO085 rib on its front plate and two shoulder bars behind it.
- **V1.11 box.** It is released and about to print (`current_incremental_print_release.status`: "RELEASED").

### A1. Ready to print now

These parts are released and have a gate receipt, or their geometry is unchanged from the printed parts that the gate already audits.

1. **`rear_frame` + `rear_lid` (V1.11, layout F), Orange.**
   - **Files:** `guide/print/back-plate/layout-F/rear_frame-world.stl` and `rear_lid-world.stl`.
   - **What it is:** the rear converter box for the 6.8 V servo rail and the 5 V Pi lead (D-007). It "replace[s] the printed V1.8 rear_pack_cover (its four M2 x 6 are reused)" (`current_incremental_print_release.baseline`).
   - **Gate:** "Print gate guide-20261014 (gate-receipt.json 2026-10-14 17:30, guide-data aaf3d6ba)".
   - **Print time:** "1h48m" Elegoo and "1h49m" Bambu (`release-V1.11/run/delivery-index.json`). Filament: about 28 g (memory `microduck-build-state`, V1.11 release note).
   - **Action:** print the released zip as it is. Scheme C keeps every part except the shells, thighs and cap, so this stays Orange.
   - **Open item:** "The cap tongue connection still needs Shawn's confirmation (AGENTS.md connection-method rule)".
2. **`thigh_left` (community-74) and `thigh_right` (community-72), stock geometry, recoloured White.** They are listed in full under B1. No design change is pending on them. Only the colour changes, so they need a White-plate slice and a pose check, and no new gate work.

The V1.9 retainer and clips are printed and unchanged, so they are not on this list.

### A2. Designed, but gate and release work comes first

All five parts below are `v20-source` "Source only; not released, not printed. Print pose, slicing, guide rebuild and the print gate run at the V2.0 release." (`current_build.v2_0_source.status`). The README repeats it: "No print pose, slicing or print gate has run on these parts." So none of them has a gate receipt.

1. **`shell_left_v20` and `shell_right_v20`, White in V1.12.**
   - **Files:** `guide/print/v20-source/shell_left_v20-world.stl` (sha256 `4e55338e…`, 11640.74 mm³) and `shell_right_v20-world.stl` (sha256 `a718e927…`, 11407.13 mm³).
   - **What changed and why** (`v20-source/README.md`):
     - Screw to the pack. "One M2 x 6 per shell, straight down through the shell roof … into the V1.9 pack shoulder bar at x -21.5, y +-20". Shawn asked for this on 2026-10-13 because the rear cross screw "has to be driven 27 mm down a hand-drilled tunnel".
     - Filled tunnels. "Cross tunnels filled flush".
     - Seven horn-screw counterbores. "S12-horn-026..032 become M2 x 4", carried over from `shells-v19-source`.
   - **Replaces:** the stock orange shells community-8 and community-10 from the 10/1 batch.
   - **Grams:** about 14.8 g and 14.4 g. These are estimated from the stock grams (14.51 g and 14.20 g, `object_grams.json`, `MicroDuck_Elegoo_orange_FLAT.gcode`) scaled by the volume ratio (11640.74 / 11389.37 and 11407.13 / 11216.91 mm³ against the printed shells, `v20-source.json` inputs).
   - **Dependency:** the screw bites only into the V1.9 pack's shoulder bar. The V1.9 manifest says the bars are new in V1.9: "two 3 mm shoulder bars behind the plate seat the printed V1.8 side shells".
2. **`head_cap_v20`, White in V1.12.**
   - **File:** `guide/print/v20-source/head_cap_v20-world.stl` (sha256 `b187fc96…`, 35352.80 mm³).
   - **What changed:** the three cap closure pilots K-head_close-01..03 are re-cut at Ø1.6 for M2 × 8. Shawn's reason, 2026-10-13: "M2.5 is hard to find … Shawn prefers M2 so the whole robot uses one screw size". Everything else is the V1.9 cap: speaker collar, amplifier posts and Pi rails ("builds the two head parts from … the V1.9 `head_cap`").
   - **Fits the current lower shell:** "the lower-shell tabs keep their 2.65 to 2.85 mm through holes, which clear M2 by 0.65 mm or more". So the White cap works with the printed V1.8 yellow lower shell.
   - **Replaces:** the orange V1.9 cap (`head_cap_v19`, installed).
   - **Grams:** about 46.0 g, from the V1.9 cap's 45.96 g (`object_grams.json`) and a +0.14 % volume change.
3. **`jaw_frame_v20`, Yellow (optional plate).**
   - **File:** `guide/print/v20-source/jaw_frame_v20-world.stl` (sha256 `b046fbd1…`, 27985.43 mm³).
   - **What changed:** "Jaw pivot hole filled … nothing in the build uses it. Shawn asked for it to be removed."
   - **Replaces:** the V1.8 yellow jaw frame (22.94 g, `object_grams.json`, V1.8 Yellow gcode).
   - **Cost:** cosmetic only, and the head has to come apart to fit it.
4. **`head_bottom_v20`, Yellow (optional plate).**
   - **File:** `guide/print/v20-source/head_bottom_v20-world.stl` (sha256 `3b0425a5…`).
   - **What changed:** the four jaw-support pilots H-jaw_support-01..04 are re-cut for M2.
   - **Replaces:** the V1.8 yellow lower head shell (41.93 g).
   - **The README's own judgement:** "These two parts are a full head reprint … this change only makes sense once the head is reprinted for some other reason or when you want a single screw size." Shawn has said he wants a single screw size (memory `microduck-screw-stock`: "M2 everywhere is best").
5. **Jaw pose-cap rule for items 3 and 4.** AGENTS.md says the jaw study "is rerun only when jaw, neck or head geometry changes, never for clips, wires or screws". The v20 README says the jaw fill is flush and "the boss outline, its tip face … and the sliding-ring seat are all unchanged". The head pilot fill "lies inside each part's old outline". The outer geometry does not change, so this plan does not schedule a jaw rerun. If that reading is wrong, only Shawn can widen the scope.

**What A2 needs before slicing:** the guide integration listed in `v20-source/README.md` under "Guide integration handoff". That is the `fasteners.json` rows (remove `X-shell_cross-01`, add the two pack screws, horn screws to M2 × 4, K-head_close to M2 × 8, plus H-jaw_support if the Yellow plate goes ahead), the `steps.py` `shells` / `close` / `prints` edits, a guide rebuild and the print gate (`content/interference-audit/run_gate.py`).

### A3. Not worth printing

- **`shells-v19-source`: superseded.** Its README says "Source only. These shells are not in the V1.9 print set". Its bored tunnel is replaced by the V2.0 tunnel fill, and its counterbores are carried in V2.0.
- **V1.10 `rear_frame` and `rear_lid`: void.** "superseded by V1.11 (layout F); do not print or fit the V1.10 frame or lid" (`current_incremental_print_release.previous`).
- **V1.7 head cap and OpenRB tray: never printed and superseded.** "V1.7. Its head cap and OpenRB tray are superseded by the printed V1.8 head cap and rear pack" (`printing_status.never_printed`).
- **`candidates/head-cap-pi-shift`, `head-cap-idc-seat` and `head-cap-v18-with-audio-posts`: earlier cap candidates.** `world/v18-sources.json` _doc says "The V1.7 cap … remains under print/candidates/head-cap-pi-shift/". The V1.9 and V2.0 caps carry the adopted Pi rails and audio posts.
- **`candidates/back-box-20261014`: superseded.** These were box concepts before layout F, which is released in V1.11.
- **`ext-v19/resistor_envelope_v19-world.stl`: an envelope, not a part.** The ext-v19 README calls it "envelope only, not printed", and the resistor was dropped on 2026-10-14 (`audio.gain_decision_20261014`).
- **Ø1.6 pilot in the pack shoulder bar: not worth a pack reprint.** The README says only "If the pack is ever reprinted, model the Ø1.6 × 5 mm pilot". The V1.9 pack is already printed, and the guide drills that pilot through the shell hole.
- **Optional ankle prototype (2026-10-07): deferred by the user.** `assembly_user_evidence.ankle_and_foot` says "defer their redesign and preserve the assembled legs". `optional_ankle_prototype.status` is "digital_prototype_physical_fit_and_strength_pending".
- **10-SURFACE-QUALITY replacement jobs: optional.** These are surface-repair reprints, and the pack says "Use a replacement only for a part that needs it". No part is requested, but its thigh pose is relevant to B1.
- **V1.9 speaker retainer and four clips: already printed, not yet fitted.** No geometry change has happened since, so fit the printed parts.

---

## B. The White plate

### B1. Which STL each printed part came from

- **Side shells: stock community meshes, 10/1 batch.**
  - Left is `community-8.stl` and right is `community-10.stl`.
  - Sources: `build-pack-20260913/assembly/print-parts/community-8.stl` and `community-10.stl`. The 10/1 copies are `printing/01-STL/plate-02/03_community-8.stl` and `04_community-10.stl` (`printing/copy-manifest.json`, `"plate": 2`).
  - They were printed orange: `colour_as_built.json` says "groups.orange placements include \"community-8.stl\"", with grams from `08-ORANGE-BOTTOM-AUDIT-20260930/MicroDuck_Elegoo_orange_FLAT.gcode`.
- **Thighs: stock, 10/1 batch.**
  - Left is `community-74.stl` and right is `community-72.stl`, from the same `assembly/print-parts/` folder. The 10/1 copies are `01-STL/plate-01/04_community-74.stl` and `03_community-72.stl` (`copy-manifest.json`, `"plate": 1`).
  - They were printed in `03-PRINT/Elegoo/MicroDuck_Elegoo_plate_1.gcode` at 4.97 g each (`object_grams.json`).
- **Head cap: V1.9.**
  - File: `guide/print/ext-v19/head_cap_v19-world.stl`, sha256 `da655c65…` (`release-V1.9/manifest-V1.9.json` and `world/v18-sources.json` `head_cap.stl`).
  - It replaced the V1.8 cap, which had the same top-down pose.
- **The community source colours these white.** In `printing/color-analysis-20260929/original-current-colors.json`, community-8, -10, -72 and -74 are in `source_color_group` "白色的外壳" (white outer shell), `#FAFAFA`. So scheme C brings back the community design's white shell parts.

### B2. Which version to print

- **Head cap: print `head_cap_v20`.** Its only change from the V1.9 cap is the three Ø1.6 M2 pilots, and the white cap is a new print anyway. The colour study says the same: "Once V2.0 is released, those three parts are reprinted anyway."
  - Fasteners: K-head_close-01..03 become M2 × 8, which is in stock (memory `microduck-screw-stock`: "M2 × 4, 6, 8, 10").
- **Shells: print `shell_left_v20` and `shell_right_v20`, fitted together with the V1.9 rear pack.**
  - Stock-geometry white shells would keep the cross tunnel that Shawn rejected ("too hard to drive"). They would also be reprinted again at V2.0.
  - On the V1.8 pack, the V2.0 roof hole has no bar under it and would be an open hole with no purpose. That breaks the "MicroDuck no dead features" rule (every boss and hole needs a purpose).
  - **If the V1.8 pack is still fitted and Shawn does not want to swap packs now,** print the stock shells (`community-8.stl`, `community-10.stl`) in White instead and leave V2.0 for later. That costs one more white shell print later.
- **Thighs: stock geometry, the only option.** Replacing them means taking both legs apart. Each thigh holds the hip-pitch and knee servos ("two motor seats", colour-study README). After rebuilding, read the joint zeros with `guide/firmware/mac/pose_snapshot.py` before standing the robot.
- **Thigh pose: check two candidates.**
  - **10/1 pose.** Flat, 28.0 mm tall, first-layer section 1497 mm² (`10-SURFACE-QUALITY-20261006/geometry/nominations.json` baseline).
  - **10-SURFACE side pose.** It was chosen so the servo screw seats are clear of support: `"support_exposed_functional_count": 0`, first-layer section 465.5 mm² (`geometry/prepared-geometry-verification.json`).
  - Run `orientation-study/orientation_check.py` on the V1.12 manifest and choose by R1 and R2 of `PRINT-ORIENTATION-PRACTICE.md`. The 10/1 pose is the regression floor.

### B3. Plate contents (White, one plate, Bambu X1C and Elegoo CC files)

- **`shell_left_v20`:** about 14.8 g. Pose comes from the release orientation check.
- **`shell_right_v20`:** about 14.4 g.
- **`thigh_left` (community-74):** 4.97 g.
- **`thigh_right` (community-72):** 4.97 g.
- **`head_cap_v20`:** about 46.0 g. Use the V1.9 pose (`manifest-V1.9.json` `head_cap_v19.sourceToPrint`), the V1.8 Bambu support blocker for E-pi-04 (`release-V1.8/blockers/pi-positive-y-upper-hole-support-blocker-v18-world.stl`), and a 4 mm outer brim on this object only.
- **Total: about 85 g.** The colour study gives 84.61 g for the same five parts with stock and V1.9 grams (`reprint_cost.json` option C, `"whiteGrams": 84.61`).
- **Estimated time: about 4 h to 4.5 h.** This is an estimate. No manifest gives per-object times. It adds up as follows:
  - Cap alone: 135.1 min (Bambu) and 148.1 min (Elegoo) for the slightly smaller V1.6 cap in the same pose (`orientation-study/results.json`, head_cap nativeSlices).
  - Shells: about 80 % of the 1 h 40 m `MicroDuck_Elegoo_orange_FLAT.gcode` ("estimated printing time (normal mode) = 1h 40m 14s"; the shells are 28.7 g of that job's 35.83 g).
  - Thighs: about 10 g, a small share of the 6 h 31 m plate-1 job.
  - The release slice gives the real figure.

**White profile warning.** The White donor profiles have weaker support interfaces than the Orange profile that printed the V1.9 cap:

- White (`12-REPAIR-V1-20261008/dual-printer/White_Elegoo_editable.3mf`): `support_interface_top_layers = 2`, `support_interface_spacing = 0.5`, `support_interface_speed = 80`, `bridge_speed = 50`, `support_style = tree_hybrid`.
- The Bambu White profile (`delivery-V1.3-Incremental/White/White_V1.3_editable.3mf`) also has 2 layers and 0.5 spacing.
- The V1.9 Orange files have 3 layers, 0.15 spacing, 40 mm/s and 30 mm/s (section C2).
- If the plate is sliced with the White defaults, the white crown would come out rougher than the orange one. The fix is in C4.

### B4. Optional Yellow plate (the remaining V2.0 changes)

- **Contents:** `head_bottom_v20` and `jaw_frame_v20`.
- **Reference figures:** the V1.8 Yellow plate held exactly these two parts: 65.0 g in the header, "zhengxia_V1.8_Yellow_Elegoo-Centauri-Carbon_2h56m.gcode" (`object_grams.json`). Use 65 g and 2 h 56 m as the reference.
- **Assembly cost:** a full head teardown (jaw servo, jaw support and lower shell), plus the M2 head-screw guide changes.
- **Include it if** Shawn wants the single screw size now. Otherwise it waits for the next time the head is opened.

### B5. Release steps (after the brim change lands)

1. Confirm which rear pack is on the robot (A, "Which rear pack is fitted").
2. Integrate the V2.0 guide handoff (A2) and rebuild the guide.
3. Write `manifest-V1.12.json` with White rows (and Yellow rows if chosen). Set `decision: replacement`, and set `supersedes` to the orange shells, the orange thighs, the orange V1.9 cap (and the V1.8 jaw frame and lower shell if Yellow).
4. Set the White `processOverrides` and the per-object brim (C4). Run `orientation_check.py`.
5. Run the release pipeline, review and the print gate (`run_gate.py`, four scripts) as AGENTS.md requires. Then package `zhengxia_MicroDuck_V1.12_<N>-files.zip` with a parts sheet and a retired-parts sheet. The retired parts are the orange shells, thighs and V1.9 cap, which become spares.

---

## C. Why the top of the cap prints rough, and what to do at print time

### C1. Which surface Shawn sanded

Shawn sanded the **outer dome**, the visible top of the head. The inside of the cap does not touch support.

**The pose.** The cap prints top-down, with the crown on the bed.

- `manifest-V1.9.json` `head_cap_v19.poseOrigin`: "V1.8 cap pose (roof on the bed) … 104.39 mm2 contact, tip angle 7.7 deg so the Orange 4 mm outer brim override stays".
- `orientation-check.json` gives `bedFacingSourceDir [-0.0765, 0.0215, 0.9968]`: robot +z, the top of the head, faces the bed.

**Why the crown needs support.**

- Only a narrow flat strip along the top centre lies on the bed (104.4 mm² true contact, 463.8 mm² first-layer section).
- Beside that strip the crown curves up at only 10 to 20 degrees from the bed. That is far below the 30 degree support threshold (`support_threshold_angle = 30` in both files). So the slicer supports the outer crown from the bed, and those faces print on support interface.

**Why there is a brim.** The brim is a separate issue. The cap stands 47 mm tall on that strip, with its centre of mass 15.9 mm up and a tip margin of 2.14 mm. That gives a 7.7 degree tip angle, under the 10 degree brim line of R1. The brim keeps the cap from tipping and does not cause the rough surface.

**The 2026-10-09 study recorded the same cost.** `orientation-study/results.json` head_cap verdict: "its cost is cosmetic: 3743 mm2 of the outer dome near the bed rests on support interface".

**Measured from the delivered V1.9 files (run-r2, 2026-10-14).**

- **Method:** every `Support interface` toolpath inside the cap footprint was taken from the G-code. For each 0.5 mm cell, a ray was cast up from the topmost interface point to the cap mesh in the 3MF (object 3, placed at 150, 104.2). Each hit was then classified as either "support stands on the bed, under the outer skin" or "support stands on the cap, inside".
  - This is a lower bound, because tree tips leave gaps in the cells.
  - The scripts are `cap_support.py` and `world_map.py` in this session's scratchpad (temporary; recreate them for the V1.12 check).
- **Bambu** (`zhengxia_V1.9_Orange_Bambu-X1C_3h38m.gcode.3mf`): 1033 mm² of outer skin on interface, between 0.36 and 3.8 mm print height. Median surface tilt is 10.5 degrees from the bed. Inside the cap, 0 mm² of interface.
- **Elegoo** (`zhengxia_V1.9_Orange_Elegoo-Centauri-Carbon_3h55m.gcode`): 2566 mm² of outer skin on interface, between 0.53 and 7.83 mm print height. Median tilt is 20.4 degrees. Inside the cap, 2.8 mm².
- **Where it is on the robot.** In the robot frame (cap z 111.1 to 157.45), the supported area is the crown from robot z 141.5 to 157.2. It runs from the front edge above the face (x 91.8) back to x -17.5, as two bands either side of the flat top strip (|y| up to 30).
  - The strip itself (about x 20 to 70, |y| under 10) shows no support, because it prints as the first layers.
  - Elegoo puts support over more than twice the area that Bambu does. Elegoo also prints the strip on Textured PEI, so the strip carries the plate texture as well.
- **Layer steps.** On a 10 to 20 degree slope, 0.2 mm layers also leave steps 0.55 to 1.1 mm wide (0.2 / tan of the angle). Every pose shows these on a shallow dome. On a top surface they are clean steps; on a supported face they combine with the interface scars.

### C2. Support settings in the V1.9 files

Both files use the same values, from `Metadata/project_settings.config` (Bambu) and the G-code footer (Elegoo):

- `support_type = tree(auto)` and `support_style = default`
- `support_top_z_distance = 0.2` and `support_bottom_z_distance = 0.2`
- `support_interface_top_layers = 3`, `support_interface_spacing = 0.15` and `support_interface_pattern = auto`
- `support_interface_speed = 40`, `bridge_speed = 30` and `support_object_xy_distance = 0.35`
- `support_threshold_angle = 30`, `tree_support_branch_diameter = 2` and `tree_support_branch_angle = 45`
- Support ironing off (`enable_support_ironing = 0` Bambu, `support_ironing = 0` Elegoo)
- `brim_type = outer_only`, `brim_width = 4` and `brim_object_gap = 0.1`
- Ironing off (`ironing_type = no ironing`)

So the usual tuning (a 0.2 mm z gap, 3 interface layers and slow interface and bridges) is already in these files. It came from the 10-SURFACE pack: "support top interface uses three layers with 0.15 mm spacing; top gap remains 0.2 mm; bridges run at 30 mm/s and the interface at 40 mm/s". The rough crown is what these settings produce with same-material support.

### C3. Print-time options and their trade-offs

1. **Flip the cap dome-up (rim down).**
   - **Gains:** the crown becomes a top surface, so it is smooth apart from the layer steps. The cap stands on its rim: 189.8 mm² contact and a 57.7 degree tip angle in the V1.9 screen (`orientation-check.json`, "stable p=0.28", bedFacing robot -z). No brim is needed (R1).
   - **Costs:** every post and pilot moves onto support. The V1.9 screen shows 62 hole ends and 13 boss faces facing down, with a support proxy of 192215 mm³ against 8792 mm³ top-down. The V1.6 native slices measured "2869 mm support under them", 156.9 mm of support inside hole cores (Bambu), and +79 min / +15.2 g on Bambu (214.1 against 135.1 min). Elegoo was 258.6 against 148.1 min.
   - **Removal risk:** support removal inside the cap is where the V1.8 Pi post broke (memory `microduck-build-state`: "The broken Pi post came from V1.8 Orange support removal").
   - **Verdict:** rejected under R2 again, as in the study ("Rim-down … puts every post on support").
2. **Tune the interface further (same material, same pose).**
   - The 0.2 mm gap and 3 layers are already set.
   - **Support ironing is still off.** Orca's wiki says it "uses a small flow to print over the top support interface again at the same height to make it smoother", and "the top support interface … [is] also printed solid". A smoother interface top gives a smoother face to print on. That last step is an inference; the wiki does not state it.
   - A smaller top z distance (0.15 or 0.1 mm) gives a smoother face but fuses the support on. Bambu's support page says the top Z gap trades easy removal against surface quality (`PRINT-ORIENTATION-PRACTICE.md` R2 source note). Rejected: hard removal on a visible face.
   - The interface pattern stays on `auto`. No evidence favours another pattern for this dome.
3. **Tree (slim or hybrid) against normal support.**
   - The supported crown sits 0.4 to 7.8 mm above the bed, so the trees are almost all interface. Branch style changes little at this height.
   - Normal (snug) support would cover the band evenly, but it adds base material under the whole band.
   - Neither has been sliced for this part, so this stays a candidate with no evidence behind it.
4. **Split or reorient.**
   - Every other screened pose fails R1 (tip margin at or below zero for all flat facets in `orientation-check.json`) or stands 116 mm tall ("stable p=0.07").
   - Splitting the dome adds a seam on the visible crown and needs glue or extra screws.
   - Rejected.
5. **Second material for the interface (X1C with an AMS only).** An interface in a material that does not bond to PLA gives a clean crown that peels off. Orca's support-filament page says it prints the interface on a "solid, well matched surface". Which interface material to use has not been checked against a source. This option depends on the club X1C having an AMS and that spool loaded, which no record shows. Shawn loads one spool per plate (memory `print-delivery-format`).

### C4. Recommendation

**Keep the dome-down pose and make four changes:**

1. **Carry the V1.9 Orange interface settings onto the White plate** through `processOverrides`: `support_interface_top_layers = 3`, `support_interface_spacing = 0.15`, `support_interface_speed = 40`, `bridge_speed = 30`. Without this, the White defaults (2 layers, 0.5 spacing) make the crown worse.
2. **Turn on support ironing:** `enable_support_ironing = 1` on Bambu, `support_ironing = 1` on Elegoo, with flow left at the 10 % default.
3. **Brim on the cap only:** set it per object, `brim_type = outer_only`, `brim_width = 4`, `brim_object_gap = 0.1`, and `no_brim` on the shells and thighs (PRINT-LESSONS.md fix 1).
4. **Prefer the X1C file for this plate.** On Bambu, about 1033 mm² of crown sits on interface against 2566 mm² on Elegoo, and the Cool Plate leaves the bed strip smooth instead of textured.

Even with these changes, expect a matte band that needs light cleanup. A crown that comes off the printer smooth needs either option 1, which breaks the posts rule, or option 5, which needs an AMS.

**What the next slice must show** (readback before the White files are handed over):

- **First layer:** cap true contact about 104 mm² on the crown strip (`flatContact.minimumAreaMm2` 93). Brim only around the cap, comparable to V1.9 ("head_cap_v19: 449 against 451 mm2"). Zero brim around the shells and thighs.
- **Support settings readback** in both files: `support_interface_top_layers = 3`, `support_interface_spacing = 0.15`, `support_top_z_distance = 0.2`, and support ironing on. The ironing pass must appear over the support interface under the crown band.
- **Crown map:** rerun the C1 interface-to-mesh mapping on the V1.12 G-code. The supported outer skin should cover the same region as V1.9 (robot z 141.5 to 157.2, two bands either side of the strip), with no gaps where interface was before. Interface on the inside of the cap should be at most the V1.9 value (0 mm² Bambu, 2.8 mm² Elegoo).
- **Posts and pilots:** `orientation-study/scripts/seat_support.py` shows 0 mm of support under down-facing hole ends and boss faces, and 0 mm inside hole cores. This matches the V1.6 "current" slice ("supportUnderDownHoleEndsMm": 0.0) and the E-pi-04 blocker still applied on Bambu.
- **Physical check:** after the first White cap is printed, Shawn compares the crown band with the sanded orange cap. If it still needs filing, the next step is option 5 on the X1C.
