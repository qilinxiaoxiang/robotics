# Orange plate: corrected bottom orientation

**Printing complete:** the user confirmed all parts, including orange, printed on 2026-10-01. Retain this job as a reference or optional replacement.

Use **MicroDuck_Elegoo_orange_FLAT.gcode** for the four orange parts on **Elegoo Centauri Carbon, 0.4 mm nozzle, ordinary PLA**. The native Orca estimate is **1 h 40 min 14 s**. This file includes a verified 144×144 PNG thumbnail. Copy the plain .gcode to the printer's USB drive; select the orange PLA physically loaded in the machine. The editable .3mf is for File > Open Project in OrcaSlicer; it must be sliced again if changing printer or process. Existing Bambu and previous Elegoo files are preserved. Use this replacement orange job once, not both old and new orange jobs.

## Diagnosis and correction

The left shell, community-8, had a broad almost-planar underside tilted1.997°. Its vertices spanned0.876 mm vertically, although deviation from its own plane was only0.0034 mm. The prepared orientation therefore sliced just an edge of that face in the first layer. A rigid rotation now lays the intended bottom flat. No vertices, triangles, holes, wall thickness or part dimensions were altered; no material was cut off.

The native first-layer model extrusion footprint increased from149.02 to1383.34 mm², with1123.84 mm² of bottom-surface toolpaths instead of none. See first-layer-before-after.png: orange is model extrusion; gray is support. These are calculated bead footprints from the actual native G-code, not physical adhesion measurements.

The right shell, community-10, is already nearly horizontal (0.038°); its native first layer has a broad bottom and was retained. The hip bracket, community-60, and thin four-hole plate, community-18, already have horizontal bottom faces. Holes, chamfers and small disconnected section slivers do not necessarily indicate a broken bottom. All four exact source meshes remain unchanged.

The regenerated support/model footprint remains centered: minimum bed-edge clearance63.47 mm, minimum conservative inter-object extrusion separation4.43 mm. No printing was started.

## Practical workflow

1. For a designed planar underside, select **Lay on Face (F)** in OrcaSlicer and choose the intended broad bottom. Merely dropping the lowest point onto the bed does not remove a tilt. [Orca shortcuts](https://github.com/OrcaSlicer/OrcaSlicer/wiki/keyboard_shortcuts) and [Prusa Place on Face](https://help.prusa3d.com/article/place-on-face-tool_1781) document this standard tool.
2. Slice and inspect layer1 with the legend separating model bottom surfaces from support. A perspective view of the unsliced mesh is insufficient. If holes are designed into the part, they should remain open.
3. For genuinely curved bottoms, choose an appropriate orientation and support; for malformed mesh geometry, repair the source. A deliberate bottom cut is useful only after checking dimension and mating effects. [Prusa documents lowering below the bed](https://help.prusa3d.com/article/move-rotate-scale-tools_1914) as a way to flatten an uneven bottom.0.75 mm is not a universal allowance: it would reduce our2 mm plate to1.25 mm and thin the shell walls substantially.
4. If the preview is correct but the real extrusion fails to adhere, investigate the physical first layer: clean plate, bed leveling, nozzle height, temperature and speed. Those cannot explain an already-fragmented software preview.

Verified2026-09-30 for P5/P6. The digital issue is corrected; actual adhesion and assembly remain observations during printing/building. Evidence: final-verification.json, orientation-review.md and risk-review.md.
