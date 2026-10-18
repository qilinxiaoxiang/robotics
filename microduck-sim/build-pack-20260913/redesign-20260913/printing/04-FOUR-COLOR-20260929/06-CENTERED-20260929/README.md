# Centered print files — 2026-09-29

Current queue: orange on Elegoo Centauri Carbon 0.4 mm; yellow and white on Bambu X1 Carbon 0.4 mm. Black and white were already printing when this update was requested. No running job was changed, and white does not need another print merely because a new file exists. Use the centered white file only if another copy is actually needed.

Use the three files in `READY-TO-PRINT`. Elegoo takes the plain `.gcode`; Bambu takes the complete `.gcode.3mf`, without unzipping or renaming. The separate Elegoo yellow/white alternatives are optional machine variants; do not print duplicate parts. Existing black and original orange plate 1 files remain unchanged.

All new projects preserve the part geometry, count, orientation and relative spacing. The entire group is translated in X/Y so the regenerated model, support and brim footprint is centered near (128, 128) mm on the 256 mm bed. Machine purge and calibration paths are controlled by the original machine profile and may still run near a bed edge. The nozzle must remain 0.4 mm and the physical plate and PLA must match the selected profile. Bambu settings retain Cool Plate; a different physical plate requires changing the profile and reslicing.

Print settings are already included: 0.20 mm layers, 4 walls, 30% infill and supports. Physical filament sets the actual color. On Bambu AMS, map the job to the slot containing the requested compatible PLA; the file's filament number is not a physical AMS slot instruction.

## Layout preference

For future prints, center the whole occupied footprint within the usable bed, including support and brim. Avoid placing groups against the bed edge. Preserve safe spacing and printer exclusion zones; rotate or split the layout if it cannot fit with sensible margins. Reposition the editable 3MF and reslice rather than shifting finished Gcode. Always retain slicer-generated thumbnails in final exports.

`centering-verification.json` records actual regenerated print footprints, clearances, identity/settings checks and preservation hashes. The new exports are digital slicing results; they do not establish physical print or assembly success. Problem IDs: P5/P6.
