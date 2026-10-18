# White and yellow — Bambu print files

Current queue update 2026-09-29: print white and yellow on Bambu; orange and black retain their existing Elegoo jobs. Original plate 1 orange and plate 5 black remain unchanged. Do not also print the equivalent Elegoo white/yellow jobs or old plates 2/3/4/6.

Copy these complete files from `SD-CARD` to the Bambu microSD card. Keep the `.gcode.3mf` extension; do not unzip or rename them.

- `MicroDuck_Bambu_WHITE.gcode.3mf`: white face panel and upper/lower mouth contact pads, 3 parts, 55 min 26 s.
- `MicroDuck_Bambu_yellow.gcode.3mf`: yellow fixed upper-beak/lower-head shell, moving jaw and both foot pads, 4 parts, 3 h 58 min 53 s.

These are native Bambu Studio exports with actual 512 × 512 plate thumbnails and smaller thumbnails. Slicing settings are baked in: Bambu Lab X1 Carbon, 0.4 mm nozzle, Cool Plate, Bambu PLA Basic profile, 0.20 mm layers, 4 walls, 30% infill and tree supports. The machine and physical build plate must match. A different Bambu model, nozzle, plate type or incompatible filament requires changing the editable project and reslicing.

Choose the file on the printer. If using AMS, map its single filament to the slot physically holding white or yellow compatible PLA; the file's filament 1 is not a command to always use physical AMS slot 1. With an external spool, use the matching loaded spool. The physical filament determines color. The files do not contain multi-color switches. No print has been started remotely.

To inspect or adjust before printing, use Bambu Studio File > Open Project and select the corresponding `WHITE/MicroDuck_Bambu_WHITE_editable.3mf` or `yellow/MicroDuck_Bambu_yellow_editable.3mf`. The `.gcode.3mf` files are sliced print packages, not editable model projects. WHITE was also successfully opened in the Bambu Studio native GUI.

The accepted compact geometry and orientations are preserved. Each entire plate was shifted +25 mm in Y to avoid Bambu's different lower-left excluded area; relative placement is unchanged. Final native-toolpath verification includes support, brim, extrusion width, arc error, bed boundary and exclusion. `spacing-verification.json` contains measured clearance and archive/Gcode hashes. `bambu-colors-verification.json` checks the exact 7 instances, native profiles, real thumbnails, Gcode MD5, identical SD copies and preservation of existing Elegoo/Bambu files. Verification is digital, not a physical print result.
