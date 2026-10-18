# Four-color remaining print queue

**Latest machine assignment:** white and yellow now have [Bambu SD files](05-BAMBU-WHITE-YELLOW/README.md); orange and black remain on Elegoo. Print each color once; the Elegoo white/yellow copies remain as backups.

Updated 2026-09-29. Keep original plate 1 orange and original plate 5 black. This queue replaces all 61 instances from original plates 2, 3, 4 and 6. Do not print the old four plates in addition to these replacements. All original files and Bambu exports remain unchanged.

## Files to print

Use the four files inside `USB-PRINT` on an Elegoo Centauri Carbon with the existing 0.4 mm nozzle, textured PEI plate and compatible ordinary PLA. Settings are already sliced into the files. They are not Bambu print files.

- `MicroDuck_orange.gcode` — 4 parts: left/right torso covers, matching hip bracket and neck link. 1 h 43 min 29 s.
- `MicroDuck_yellow.gcode` — 4 parts: fixed upper-beak/lower-head shell, moving jaw frame and both foot pads. 4 h 1 min 7 s.
- `MicroDuck_WHITE.gcode` — 3 parts: face panel and upper/lower mouth contact pads. 58 min 7 s.
- `MicroDuck_black.gcode` — 50 structural parts, carriers, idlers and rings, including every part from old plate 6. 4 h 29 min 26 s.

Total native GUI estimate: 11 h 12 min 9 s, excluding the two preserved plates, handling and spool changes. Packing chiefly enables the accepted color separation without adding jobs; it barely changes total print time. Four jobs is the minimum for these four separate colors in this single-filament workflow, not a claim of globally optimal packing or print speed.

If the black Elegoo becomes free after original plate 5, continue with `MicroDuck_black.gcode` using compatible black PLA. If a short job is preferred, load white PLA and use `MicroDuck_WHITE.gcode`. On the orange machine, follow original plate 1 with the orange job. Each new job has one physical spool color; the slicer color swatch does not change loaded filament. Purge the previous color after a spool change.

## Arrangement and evidence

Source mesh bytes, original tilt, component transforms and vertical position are preserved; only horizontal positions changed. The old approximately 24 mm model spacing was a conservative arrangement, not a mandatory clearance for these by-layer prints. New packing uses actual support and brim footprints, not just model bounds. `spacing-verification.json` audits the final GUI G-code with extrusion widths, support/brim paths, build plate boundary and excluded region. `spacing-four-colors.png` shows the audited footprints.

Each color folder includes `MicroDuck-COLOR-editable.3mf`: open this through OrcaSlicer File > Open Project to edit or reslice. `MicroDuck-COLOR-GUI.gcode.3mf` is the native GUI print archive from which the final plain G-code was extracted unchanged. It is not the editable model project. All four final G-codes contain actual nonblank 144 × 144 PNG thumbnails.

`four-color-verification.json` records finite acceptance: exact 61-instance coverage; original files and Bambu preservation; unchanged source geometry and print orientations; native slicing; final support/brim spacing; byte identity to GUI archives; embedded thumbnails. This verifies digital exports, not physical print or assembly results. `color-layout.json` maps each instance back to its original plate, source and object ID. `SUPERSEDED-TRIALS` contains earlier candidates, not current print jobs.

## Source colors and adapted design

The actual community source project groups beak/ankles as yellow, main shells as white, face/contact pads and structures as gray, bearings/idlers as black, and eye rim/foot pads as pale yellow. These labels describe source groups; the saved yellow/pale-yellow color swatches are orange/brown rather than exact yellow. See `../color-analysis-20260929/README.md` for source identity and per-part evidence.

Original current plates 2, 3, 4 and 6 mix source color groups. Plate 2 contains the beak plus torso covers and structure. Plate 4 contains the face panel, both mouth contact pads, leg links and small structure. The eye outer ring is on original plate 5, already chosen black. This adapted scheme keeps original plate 1 orange and plate 5 black, uses a white face to contrast the black eye rim, yellow beak and foot pads, orange remaining torso covers, and black remaining structure. Small caps already on plate 1 remain orange accents.
