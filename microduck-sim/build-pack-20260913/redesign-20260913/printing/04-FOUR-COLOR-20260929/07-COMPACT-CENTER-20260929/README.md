# Compact center layout — 2026-09-29

This version replaces the long rows in the previous centered copies with compact groups. Each part keeps its geometry and print orientation; only its position in the bed plane changes. The layout search prioritizes maximizing the minimum clearance to the four bed edges, with support/brim included and safe gaps retained. It compares bounded candidate layouts, not every possible geometric packing.

Use `READY-TO-PRINT`: orange plain Gcode for Elegoo Centauri Carbon 0.4; yellow and WHITE complete Gcode.3mf packages for Bambu X1 Carbon 0.4. `ALTERNATE-ELEGOO` contains optional yellow/white copies for Elegoo. Do not print both machine variants. Old files remain preserved. Black and white were already printing; no live job was changed, and this revision does not require reprinting white.

The settings and native thumbnails are included. Physical PLA determines color; on Bambu AMS choose the slot with the correct PLA. Match the machine, 0.4 mm nozzle and physical plate to the profile. Bambu retains its Cool Plate profile.

## Center in both axes

Future layouts should form compact clusters or multiple rows, keeping both X and Y away from the edges. Merely centering a long row is insufficient. Count support and brim, preserve machine keepouts, and prioritize the smallest margin to any of the four bed edges. Repack the editable 3MF then reslice, with native thumbnails.

## Why startup lines remain at the edge

The actual Bambu startup Gcode prints a nozzle-load line from X18 toward X240 at Y1 to establish extrusion before the model. It also contains conditional calibration paths controlled by the printer's extrusion-calibration flag. These preparation paths are independent of model placement and intentionally remain in the machine profile. File presence does not show whether calibration was enabled for a specific live print. See `start-lines-evidence.txt` for actual exported commands.

Digital acceptance covers geometry, positions, process settings, regenerated toolpaths, thumbnails and preservation. It does not establish physical print or assembly results. Problem IDs P5/P6.

Native tree supports can regenerate with slightly different outer extents after position changes. Actual final margins, separation and finite before/after improvement determine acceptance; centering is approximate within 2 mm, not a claim of submillimeter symmetry or globally optimal packing. The final alternative Elegoo yellow footprint is about 1.15 mm off the geometric bed center while retaining roughly 4 cm edge clearance.
