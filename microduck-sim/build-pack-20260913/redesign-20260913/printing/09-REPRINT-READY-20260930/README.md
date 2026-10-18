# Optional MicroDuck reprint files

**For new optional replacements, use [the 2026-10-06 surface-quality pack](../10-SURFACE-QUALITY-20261006/README.md).** This09 pack is retained as history; its original files remain unchanged.

The user confirmed on 2026-10-01 that all parts, including orange, have been printed. This folder is a reference and prepares replacements if an already printed part needs reprinting; it does not instruct you to print all89 parts again. Keep sound completed parts. Choose one version of a logical group, never both its primary file and another printer version.

The six logical groups contain10 +18 +4 +4 +3 +50 =89 original print instances, including existing spare parts. Original STLs, earlier projects and printer exports are preserved. [Original STL instance folders](../01-STL/) retain original coordinates; use the editable3MF projects below to preserve the verified print orientation.

## Primary printer files

These six files are assembled into READY-TO-PRINT from the matching native exports. Use the final reprint-verification.json result before treating the folder as digitally accepted. A passing result covers files and geometry, not actual adhesion or completed assembly.

- **old-orange-plate1 — 10 parts, Elegoo**: [printer file](READY-TO-PRINT/MicroDuck_Elegoo_Orange-10-Original-Plate1.gcode); [editable project](Elegoo/old-orange-plate1/MicroDuck_Elegoo_old-orange-plate1_REPRINT_editable.3mf).
- **old-black-plate5 — 18 parts, Elegoo**: [printer file](READY-TO-PRINT/MicroDuck_Elegoo_Black-18-Original-Plate5.gcode); [editable project](Elegoo/old-black-plate5/MicroDuck_Elegoo_old-black-plate5_REPRINT_editable.3mf).
- **orange — 4 parts, Elegoo**: [printer file](READY-TO-PRINT/MicroDuck_Elegoo_Orange-4.gcode); [editable project](Elegoo/orange/MicroDuck_Elegoo_orange_REPRINT_editable.3mf).
- **black — 50 parts, Elegoo**: [printer file](READY-TO-PRINT/MicroDuck_Elegoo_Black-50.gcode); [editable project](Elegoo/black/MicroDuck_Elegoo_black_REPRINT_editable.3mf).
- **yellow — 4 parts, Bambu**: [printer file](READY-TO-PRINT/MicroDuck_Bambu_Yellow-4.gcode.3mf); [editable project](Bambu/yellow/MicroDuck_Bambu_yellow_REPRINT_editable.3mf).
- **WHITE — 3 parts, Bambu**: [printer file](READY-TO-PRINT/MicroDuck_Bambu_White-3.gcode.3mf); [editable project](Bambu/WHITE/MicroDuck_Bambu_WHITE_REPRINT_editable.3mf).

## All ten printer versions

Use the version matching the actual machine. Bambu files remain intact.gcode.3mf packages; Elegoo uses plain.gcode. These alternatives contain the same group of parts and must not be added to the primary queue as extra parts.

- Elegoo / old-orange-plate1 (10 parts): [native file](Elegoo/old-orange-plate1/MicroDuck_Elegoo_old-orange-plate1_REPRINT.gcode); [editable3MF](Elegoo/old-orange-plate1/MicroDuck_Elegoo_old-orange-plate1_REPRINT_editable.3mf).
- Elegoo / old-black-plate5 (18 parts): [native file](Elegoo/old-black-plate5/MicroDuck_Elegoo_old-black-plate5_REPRINT.gcode); [editable3MF](Elegoo/old-black-plate5/MicroDuck_Elegoo_old-black-plate5_REPRINT_editable.3mf).
- Elegoo / orange (4 parts): [native file](Elegoo/orange/MicroDuck_Elegoo_orange_REPRINT.gcode); [editable3MF](Elegoo/orange/MicroDuck_Elegoo_orange_REPRINT_editable.3mf).
- Elegoo / yellow (4 parts): [native file](Elegoo/yellow/MicroDuck_Elegoo_yellow_REPRINT.gcode); [editable3MF](Elegoo/yellow/MicroDuck_Elegoo_yellow_REPRINT_editable.3mf).
- Elegoo / WHITE (3 parts): [native file](Elegoo/WHITE/MicroDuck_Elegoo_WHITE_REPRINT.gcode); [editable3MF](Elegoo/WHITE/MicroDuck_Elegoo_WHITE_REPRINT_editable.3mf).
- Elegoo / black (50 parts): [native file](Elegoo/black/MicroDuck_Elegoo_black_REPRINT.gcode); [editable3MF](Elegoo/black/MicroDuck_Elegoo_black_REPRINT_editable.3mf).
- Bambu / old-orange-plate1 (10 parts): [native file](Bambu/old-orange-plate1/MicroDuck_Bambu_old-orange-plate1_REPRINT.gcode.3mf); [editable3MF](Bambu/old-orange-plate1/MicroDuck_Bambu_old-orange-plate1_REPRINT_editable.3mf).
- Bambu / old-black-plate5 (18 parts): [native file](Bambu/old-black-plate5/MicroDuck_Bambu_old-black-plate5_REPRINT.gcode.3mf); [editable3MF](Bambu/old-black-plate5/MicroDuck_Bambu_old-black-plate5_REPRINT_editable.3mf).
- Bambu / yellow (4 parts): [native file](Bambu/yellow/MicroDuck_Bambu_yellow_REPRINT.gcode.3mf); [editable3MF](Bambu/yellow/MicroDuck_Bambu_yellow_REPRINT_editable.3mf).
- Bambu / WHITE (3 parts): [native file](Bambu/WHITE/MicroDuck_Bambu_WHITE_REPRINT.gcode.3mf); [editable3MF](Bambu/WHITE/MicroDuck_Bambu_WHITE_REPRINT_editable.3mf).

## Machine and material

Elegoo versions use **Centauri Carbon,0.4mm nozzle, Textured PEI Plate, MicroDuck Generic PLA**. Bambu versions use **X1 Carbon,0.4mm nozzle, Cool Plate, Bambu PLA Basic**. Printing settings are carried in the sliced file. Confirm those settings match the actual nozzle, build plate and loaded ordinary PLA; another printer, plate or material requires its matching project and a new slice.

Load the physical spool matching the group's color: orange, black, yellow or white. A preview color does not choose the real spool or an AMS slot. If using AMS, map to the correct compatible PLA slot at the machine. Use the printer-specific file, check its thumbnail and watch the first layer adhere before leaving it unattended under club rules.

## What changed

Community-64 and66 on old orange plate1 were laid flat by rigid rotations of6.472° and7.124°. The earlier community-8 correction is retained on the orange four-part plate. Every other instance was checked and kept in its existing bottom orientation; documented black-group rotations are only about the vertical axis for packing. No blanket0.75mm cut was applied, and no mesh material was removed.

Layouts use regenerated native model/support/brim paths for spacing and centering checks. The50-part black plate remains a tight single-plate job: the latest CLI reslice had4.617mm minimum separation and6.286mm minimum bed-edge margin. Final GUI-export measurements in reprint-verification.json govern acceptance. This is a verified feasible arrangement, not a claim of globally optimal packing or large margins on every plate.

[Preparation workflow](../WORKFLOW.md) · [Geometry audit](geometry-review.md) · [Final native verification](reprint-verification.json) · [Exact copy index](handoff-index.json)
