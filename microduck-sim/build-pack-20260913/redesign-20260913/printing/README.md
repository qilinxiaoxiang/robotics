# MicroDuck printing files

**Printing complete (user-confirmed 2026-10-01):** all parts, including orange, have been printed. Files are retained for reference and optional replacement printing only. The [corrected orange plate](08-ORANGE-BOTTOM-AUDIT-20260930/README.md) preserves the four-part orientation correction. Do not print duplicate old/new jobs. Physical fit, assembly and commissioning are separate checks.

**Current optional reprints (2026-10-06):** [The surface-quality replacement pack](10-SURFACE-QUALITY-20261006/README.md) audits all89 instances and repairs eight print orientations plus support, packing and portable plate settings. Start with the single left-ankle file only when a replacement print is needed. [The earlier09 pack](09-REPRINT-READY-20260930/README.md) remains as history; do not print both versions.

**Required preparation:** follow [the default printing workflow](WORKFLOW.md) for every new or revised plate.

Use this folder to find the models, editable projects and printer-ready exports. Original files remain in their existing folders unchanged.

- `01-STL/plate-01` through `plate-06`: all 89 STL instance copies, grouped by the current project’s plate assignments. Repeated parts have separate numbered files. These are byte-identical source STLs; their source coordinates and orientation are unchanged. Plate placement and instance transforms belong to the 3MF project, so importing these STL folders alone does not reproduce the arranged plates.
- `02-PROJECTS/Bambu`: the current editable six-plate Bambu 3MF project.
- `02-PROJECTS/Elegoo`: the Centauri Carbon project and sliced project. Open the matching printer project when changing settings or exporting again. `MicroDuck-Elegoo-GUI-all-plates.gcode.3mf` is the native GUI export archive containing all six print files, not an editable model project.
- `03-PRINT/Bambu`: six original native `.gcode.3mf` exports. Copy these intact to the printer’s SD card; do not unzip or rename their extension. They use the existing X1 Carbon / 0.4 mm / Cool Plate / Bambu PLA Basic profile.
- `03-PRINT/Elegoo`: native `.gcode` exports for the Centauri Carbon. All six native exports contain decoded, nonblank 144 × 144 PNG thumbnails. Plate 5 remains byte-identical to the verified manual Desktop export. This confirms export completeness and embedded thumbnails; it does not claim a physical printer test.

The workflow is **STL model → 3MF project with arrangement and printer/material settings → sliced printer file**. Bambu uses the native `.gcode.3mf` package here; Elegoo uses `.gcode`. Printer files are specific to their printer, nozzle, plate and filament profile.

Changing between ordinary PLA colors does not by itself require a new model or plate arrangement. Confirm the filament uses the same compatible PLA profile; silk, filled, foaming or other special PLA can require different settings. Changing material, such as PLA to PETG, requires the matching material profile and a new slice. Printing multiple colors in one object requires an appropriate multicolor workflow and hardware; merely choosing another single-color spool does not create a multicolor print.

Plate instance counts: 1: 10, 2: 7, 3: 13, 4: 13, 5: 18, 6: 28. Total: 89. `copy-manifest.json` maps every copied file to its original path and SHA-256 hash, including each STL’s project object ID and manifest index. The print stock includes spare parts; 89 is not the installed-part count.

## Color and export notes

There is no mandatory part color in the current build. The user reports printing plate 5 in black; black ordinary PLA is suitable. Slicer color swatches describe previews; actual color comes from the physical spool. With the standard external spool, unload/load the desired compatible PLA and purge the previous color before starting. With a multi-spool accessory, select/map the slot holding the desired compatible material. Club accessory configuration is unverified. Optional CANVAS support: https://www.elegoo.com/products/canvas-for-centauri-carbon (checked 2026-09-29).

The earlier “not recognized” report meant no thumbnail was visible, not firmware rejection. Raw Orca 2.4.2 CLI slices omitted thumbnail data. These final files come from native GUI export and contain actual thumbnails; plate 5 exactly matches the user's manual export. Future CLI runs create intermediate slices only. Native GUI export followed by the organized verifier is required before replacing final printer files.
