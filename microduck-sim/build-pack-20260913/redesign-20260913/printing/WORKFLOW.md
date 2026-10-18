# Default printing workflow

Required for every new or revised MicroDuck plate. Applies to Bambu and Elegoo exports. The current hardware workflow routes here. Keep the accepted color plan and known printer context. This is an agent preparation checklist; it does not claim that Orca automatically performs every check.

## Prepare each part

1. Identify the exact printer, nozzle, build plate and material profile. Use the editable3MF when available so that intended orientations, supports and object settings are retained. STL alone does not preserve these settings.
2. Inspect the intended contact face of **every part** in its transformed print orientation. For a designed planar bottom, use Lay on Face (按面放平) and land it on the bed. Drop to Bed only lands the lowest point; it does not remove tilt. Compare the face normal and height spread when visual inspection is ambiguous.
3. Slice and inspect the actual first layer, separating model bottom/walls from supports, brim and intended holes. Confirm the expected broad contact is present, and investigate unexplained islands or missing bottom fill. A nonzero contact area or the presence of support alone is insufficient acceptance. There is no universal minimum area for all geometries.
4. Inspect functional surfaces throughout the entire slice: screw-head seats, mating faces, sliding-ring lips, bores and connector/service openings. Identify which are bed-facing or support-facing; broad first-layer contact cannot accept a rough supported screw seat. Prefer a rigid orientation that makes the functional face upward without creating a worse horizontal bore. Check actual model/support bead envelopes (including line width and layer height), bridge spans and support access. A configured support gap or a support-presence flag alone is insufficient. Leave physical finish, support removal and assembly fit explicitly unverified until a printed sample is inspected.
5. Fix the demonstrated cause: rigid orientation first for a tilted flat face; repair malformed source geometry where necessary; use suitable orientation/support for curved surfaces. Do not automatically cut0.75mm. Before any material removal, check remaining wall thickness, overall dimensions, screw seats, holes and mating surfaces; reslice and verify affected features.

## Arrange the whole job

6. Pack parts compactly in rows or another suitable cluster. Center the **complete regenerated model/support/brim extrusion footprint** on both X and Y, maximizing the smallest bed-edge clearance rather than centering a long row that still approaches the edges. Respect printer exclusion zones and retain adequate separation; current by-layer MicroDuck jobs target at least4mm between conservative extrusion footprints. Sequential printing needs its own printhead-clearance check.
7. Regenerate supports after rotation or placement changes. Measure actual sliced footprint, edge margins and inter-object separation again; model bounding boxes alone are insufficient. Preserve geometry, quantities, color assignments and machine/material settings unless the requested change specifically requires altering them.

## Export and hand off

8. Export using the matching native slicer. Elegoo Centauri Carbon uses plain.gcode; these Bambu jobs use intact.gcode.3mf. Verify the real embedded printer thumbnail, not merely the application preview. For the current Orca2.4.2 workflow, use native GUI export because prior CLI exports omitted the thumbnail. Decode the final image and check it is nonblank and matches the job.
9. Preserve previous machine variants and original STLs. Label one current replacement job clearly; do not tell the user to print both old and new versions. Give the exact file link, printer/nozzle/material, estimated time, and physical spool or AMS-slot mapping. A preview color does not select the physical filament.
10. Record digital evidence for each part: orientation decision, first-layer result, unchanged or deliberately revised geometry, native slice, final footprint and embedded thumbnail. Apply an independent scope/evidence review for multi-step changes. Never start a printer without the user's instruction. Observe actual first-layer adhesion at the machine; a correct preview does not prove real adhesion or final assembly fit.

## Native export guard (Orca 2.4.2)

Verified 2026-10-06 against the original failing entrypoint. Orca CLI export dereferences the first `filament_ids` entry without an empty-vector guard; some imported 3MFs contain singular `filament_id` but no populated plural vector. Do not repeat a crashed invocation. Load the exact matching existing filament profile with `--load-filaments`, require a nonempty material ID before launch, and compare printer/nozzle/plate/material values against the source. Run with ordinary collision checks enabled. Require exit zero, a valid archive with actual G-code, and no new crash report. Exit 155 is a toolpath-conflict rejection, not this crash; investigate the named pair in the native logfile and repack complete support/model envelopes. Never use `--no-check` to accept it. The current bounded helper and failure/repair evidence live in [the surface-quality pack](10-SURFACE-QUALITY-20261006/).

In Bambu Studio 02.08.02.61, the original native CLI export includes real rendered plate/top/pick PNGs; it can satisfy Bambu handoff when the actual images, geometry, machine settings, toolpaths and hashes are verified. Do not describe CLI evidence as a successful GUI export. Explicit per-plate `bed_type=Cool Plate` metadata preserves the intended plate when the GUI has a different global default. Native Bambu commanded XY subtracts the configured extruder offset; add it back when auditing physical material footprints and geometry.

Native UI navigation must assert the actual Open/Save dialog before sending Go To Folder keys. In Bambu Studio, Command+Shift+G on the main window opens **Send print job**. If the save panel is not observable, do not send that shortcut to the main window. Use the observed File → Export action, and inspect the returned dialog. A printing-preparation task does not authorize sending a job.

CLI acceptance remains separate from GUI thumbnail export for Orca. Obtain real thumbnails through the matching native GUI, then audit the final exported bytes again. Preserve the unmodified failing input and crash evidence for regression checks.

Official source: [OrcaSlicer 2.4.2 CLI](https://github.com/OrcaSlicer/OrcaSlicer/blob/v2.4.2/src/OrcaSlicer.cpp), checked 2026-10-06.

## Accepted example: orange four-part plate

Verified2026-09-30: community-8 required a1.997° rigid rotation; native first-layer model footprint149.02→1383.34mm². Community-10,60,18 were inspected and retained. No material was cut; all mesh geometry and dimensions were preserved. Full footprint minimum bed margin63.47mm, inter-object gap4.43mm. [Current file and evidence](08-ORANGE-BOTTOM-AUDIT-20260930/README.md).

Official tool references: [Orca Lay on Face shortcut](https://github.com/OrcaSlicer/OrcaSlicer/wiki/keyboard_shortcuts), [Prusa Place on Face](https://help.prusa3d.com/article/place-on-face-tool_1781), and [deliberate below-bed trimming](https://help.prusa3d.com/article/move-rotate-scale-tools_1914). Sources checked2026-09-30.
