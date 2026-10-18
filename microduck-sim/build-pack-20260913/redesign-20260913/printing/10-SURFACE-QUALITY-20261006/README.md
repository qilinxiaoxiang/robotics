# MicroDuck replacement print files — surface quality, 2026-10-06

Optional replacements for the already printed robot. This pack retains all 89 print-stock instances and the existing Elegoo/Bambu variants. Use a replacement only for a part that needs it; sound completed parts do not need another print. Original source meshes and previous jobs remain in their original folders. Problems advanced: P5 / P6.

## Saved left-ankle-only option for a later trial

No printing is requested now. [The orange left-ankle-only editable project](QUICK-TEST/MicroDuck_Elegoo_Left-Ankle-66_SURFACE_editable.3mf) and [the native Elegoo print file](QUICK-TEST/MicroDuck_Elegoo_Left-Ankle-66_SURFACE.gcode) are saved for a future replacement trial. They are for **Elegoo Centauri Carbon, 0.4 mm nozzle, Textured PEI plate, ordinary orange PLA** using the retained MicroDuck PLA profile. Native estimate: **36 min 41 sec**. This is community-66, the part in the rough-surface photo. The four output screw-head seats face upward; the supported face in the photo is no longer the downward printing face.

When a future trial is requested, inspect the four seats, bore edges and sliding-ring fit after removing accessible support before committing to a full plate. The digital files have not established physical adhesion, surface finish, support-removal ease or assembly fit. This workflow has not sent a print job. The file is machine-specific; do not run this Elegoo G-code on a Bambu printer.

## What changed

- Eight instances have a new rigid print orientation: left ankle community-66; thighs community-72/74; hip brackets community-14/60; yaw-to-roll links community-36/38; head yaw-to-roll community-70. The opposite ankle community-64 already exposes its functional surfaces upward and retains its pose.
- For plates with demonstrated supported-surface risk, support top interface uses three layers with 0.15 mm spacing; top gap remains 0.2 mm; bridges run at 30 mm/s and the interface at 40 mm/s. Native paths, rather than these settings alone, are checked.
- Bambu yellow also disables the two options that suppressed support under small overhangs and body interfaces. Actual support under its two head-cover closing seats is now measured; their previously unexplained downward samples are resolved without changing the model.
- Complete model/support/brim footprints are repacked and centered. Conservative native extrusion separation is at least 4 mm, including every layer and generated support; model rectangles alone are not used.
- Bambu native coordinates compensate a configured nozzle offset of (0, 2) mm. Current projects center the actual material footprint; the nozzle offset itself is retained. Explicit per-plate Cool Plate metadata preserves the intended build plate when the project is opened.
- All source mesh geometry, screw holes, mating dimensions, part quantities and accepted color groups are retained. This is a print-preparation repair, with no material cut from the models and no screw-length redesign.

## Primary replacement jobs

These six jobs cover all 89 print-stock instances. Choose the matching machine and group; do not print both old and new versions. Elegoo files are plain `.gcode`; Bambu files stay intact as `.gcode.3mf`.

- **Elegoo · old-orange-plate1 · 10 parts · orange PLA** — [MicroDuck_Elegoo_old-orange-plate1_SURFACE.gcode](READY-TO-PRINT/MicroDuck_Elegoo_old-orange-plate1_SURFACE.gcode). Estimate: 7h 22m 41s. Nozzle: 0.4 mm. Plate: Textured PEI Plate.
- **Elegoo · old-black-plate5 · 18 parts · black PLA** — [MicroDuck_Elegoo_old-black-plate5_SURFACE.gcode](READY-TO-PRINT/MicroDuck_Elegoo_old-black-plate5_SURFACE.gcode). Estimate: 51m 18s. Nozzle: 0.4 mm. Plate: Textured PEI Plate.
- **Elegoo · orange · 4 parts · orange PLA** — [MicroDuck_Elegoo_orange_SURFACE.gcode](READY-TO-PRINT/MicroDuck_Elegoo_orange_SURFACE.gcode). Estimate: 1h 38m 42s. Nozzle: 0.4 mm. Plate: Textured PEI Plate.
- **Elegoo · black · 50 parts · black PLA** — [MicroDuck_Elegoo_black_SURFACE.gcode](READY-TO-PRINT/MicroDuck_Elegoo_black_SURFACE.gcode). Estimate: 4h 53m 31s. Nozzle: 0.4 mm. Plate: Textured PEI Plate.
- **Bambu · yellow · 4 parts · yellow PLA** — [MicroDuck_Bambu_yellow_SURFACE.gcode.3mf](READY-TO-PRINT/MicroDuck_Bambu_yellow_SURFACE.gcode.3mf). Estimate: 4h 22m 29s. Nozzle: 0.4 mm. Plate: Cool Plate.
- **Bambu · WHITE · 3 parts · white PLA** — [MicroDuck_Bambu_WHITE_SURFACE.gcode.3mf](READY-TO-PRINT/MicroDuck_Bambu_WHITE_SURFACE.gcode.3mf). Estimate: 55m 20s. Nozzle: 0.4 mm. Plate: Cool Plate.

Preview swatches do not select physical filament. Load and purge the stated ordinary PLA color on the external spool, or map the AMS slot actually containing that color and compatible PLA. The physical AMS slot configuration is not recorded here.

## Editable projects and alternate machine exports

All ten retained machine variants are listed below. An alternate machine export is an option for the same parts, not an additional quantity to print.

- **Elegoo · old-orange-plate1 · 10 parts** — [editable project](projects/Elegoo/old-orange-plate1/MicroDuck_Elegoo_old-orange-plate1_SURFACE_editable.3mf); [native print file](native/Elegoo/old-orange-plate1/MicroDuck_Elegoo_old-orange-plate1_SURFACE.gcode). 7h 22m 41s. Color: orange. Plate: Textured PEI Plate.
- **Elegoo · old-black-plate5 · 18 parts** — [editable project](projects/Elegoo/old-black-plate5/MicroDuck_Elegoo_old-black-plate5_SURFACE_editable.3mf); [native print file](native/Elegoo/old-black-plate5/MicroDuck_Elegoo_old-black-plate5_SURFACE.gcode). 51m 18s. Color: black. Plate: Textured PEI Plate.
- **Elegoo · orange · 4 parts** — [editable project](projects/Elegoo/orange/MicroDuck_Elegoo_orange_SURFACE_editable.3mf); [native print file](native/Elegoo/orange/MicroDuck_Elegoo_orange_SURFACE.gcode). 1h 38m 42s. Color: orange. Plate: Textured PEI Plate.
- **Elegoo · yellow · 4 parts** — [editable project](projects/Elegoo/yellow/MicroDuck_Elegoo_yellow_SURFACE_editable.3mf); [native print file](native/Elegoo/yellow/MicroDuck_Elegoo_yellow_SURFACE.gcode). 4h 21m 9s. Color: yellow. Plate: Textured PEI Plate.
- **Elegoo · WHITE · 3 parts** — [editable project](projects/Elegoo/WHITE/MicroDuck_Elegoo_WHITE_SURFACE_editable.3mf); [native print file](native/Elegoo/WHITE/MicroDuck_Elegoo_WHITE_SURFACE.gcode). 58m 0s. Color: white. Plate: Textured PEI Plate.
- **Elegoo · black · 50 parts** — [editable project](projects/Elegoo/black/MicroDuck_Elegoo_black_SURFACE_editable.3mf); [native print file](native/Elegoo/black/MicroDuck_Elegoo_black_SURFACE.gcode). 4h 53m 31s. Color: black. Plate: Textured PEI Plate.
- **Bambu · old-orange-plate1 · 10 parts** — [editable project](projects/Bambu/old-orange-plate1/MicroDuck_Bambu_old-orange-plate1_SURFACE_editable.3mf); [native print file](native/Bambu/old-orange-plate1/MicroDuck_Bambu_old-orange-plate1_SURFACE.gcode.3mf). 6h 20m 41s. Color: orange. Plate: Cool Plate.
- **Bambu · old-black-plate5 · 18 parts** — [editable project](projects/Bambu/old-black-plate5/MicroDuck_Bambu_old-black-plate5_SURFACE_editable.3mf); [native print file](native/Bambu/old-black-plate5/MicroDuck_Bambu_old-black-plate5_SURFACE.gcode.3mf). 47m 23s. Color: black. Plate: Cool Plate.
- **Bambu · yellow · 4 parts** — [editable project](projects/Bambu/yellow/MicroDuck_Bambu_yellow_SURFACE_editable.3mf); [native print file](native/Bambu/yellow/MicroDuck_Bambu_yellow_SURFACE.gcode.3mf). 4h 22m 29s. Color: yellow. Plate: Cool Plate.
- **Bambu · WHITE · 3 parts** — [editable project](projects/Bambu/WHITE/MicroDuck_Bambu_WHITE_SURFACE_editable.3mf); [native print file](native/Bambu/WHITE/MicroDuck_Bambu_WHITE_SURFACE.gcode.3mf). 55m 20s. Color: white. Plate: Cool Plate.

## Evidence and scope

[Geometry and source readback](geometry/final-geometry-verification.json), [native paths, first layers, spacing and thumbnails](native-verification.json), [functional bore/surface readback](geometry/native-functional-verification.json), and [handoff hashes](handoff-index.json) bind the actual final files. The old ankle remains a negative regression: broad first-layer contact alone does not accept its downward supported screw seats. The side-print alternative is retained as an experiment, not selected, because it creates a worse horizontal large-bore ceiling.

Orca 2.4.2 CLI export crashed when the material-ID vector was empty. The same failing input now exports successfully with the exact matching filament profile loaded explicitly. [Crash diagnosis and original-entry repair](diagnostics/repaired-cli/repair-acceptance.json) and the bounded helper retain that failure and acceptance. A normal path-conflict rejection is handled by repacking generated support footprints; collision checks remain enabled. Elegoo final exports include genuine native GUI thumbnails. Bambu exports must contain genuine embedded native render images; manually inserted images do not qualify.

This pack accepts digital print-file preparation. A successful sample print can change the orientation/support decision if a seat is damaged, support cannot be removed, a bore is obstructed or a sliding fit binds. Physical commissioning and the robot visual-pickup goal remain separate and unverified.

[Required printing workflow](../WORKFLOW.md) · [Previous 09 pack](../09-REPRINT-READY-20260930/README.md) · [Interactive left-leg assembly guide](../../leg-guide-20261006/LEFT-LEG.html)
