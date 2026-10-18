# Native underside-path diagnostics and isolated ankle experiment

Problem P5/P6; prepared 2026-10-06. Files here are experimental or diagnostic. They do not establish physical finish, usable printed holes, support removal, or acceptance of a complete print job.

## Sources and candidate reasoning

The official [OrcaSlicer support documentation](https://github.com/OrcaSlicer/OrcaSlicer/wiki/support_settings_advanced), checked 2026-10-06, defines the support/object Z gap and explains that additional top interface layers improve support but add printing time and make removal harder. Zero interface spacing creates a solid interface. Top interface spacing is separate from bottom interface spacing. Independent support layers permit custom support gap heights. [Official bridge controls](https://github.com/OrcaSlicer/OrcaSlicer/wiki/quality_settings_bridging) distinguish printed bridges from ordinary skin.

The bounded engineering candidate retains ordinary PLA, printer/nozzle/plate, accepted mesh bytes, accepted orientation, 0.2 mm layers, 0.2 mm support top gap and existing support XY separation. Only top-interface spacing 0.5→0.15 mm, top layers 2→3, external bridge speed 50→30 mm/s and internal bridge speed 150%→100% are proposed. These exact values are an experimental selection; official documentation does not promise that they produce usable surface quality on these parts. No zero-gap same-PLA interface or geometry cut is proposed. A separate gap0.16 project is retained as an unused experimental variant; it is not the current selection.

## Evidence

`baseline89-path-index.json` covers the six current primary groups and all 89 instances. `baseline89-surface-triage.json` identifies 24 instances with external bridge paths, 56 with overhang-wall paths, and 39 with support interfaces. These are risk categories, not 24/56/39 proven failed parts. Color and source geometry remain unchanged.

`audit_surface_paths.py` reads actual native G-code, resolves Bambu object labels against its editable project, respects relative/absolute extrusion, samples arcs, and groups extrusion by object, feature and actual Z. For MODEL Bottom surface, Bridge, Internal Bridge and Overhang wall it computes path length/speed and projected proximity to support-interface beads at model Z minus extrusion height minus configured gap. It records nearest matching interface Z rather than inferring support from the first layer. Sampling interval is 0.25 mm; a 0.15 mm proximity allowance accounts for sample discretization. These estimates are diagnostic, not exact surface area or structural strength.

Intentional hole/void bridges may have no support. No blanket 100%-coverage rule is applied. Exact mesh regions for holes, screw-head seats and motor mating planes must distinguish intentional bridges, exterior surface gaps and trapped-support/removal risk. Do not pass a whole job from nonzero first-layer contact or this script alone. Native GUI export, thumbnails, adhesion-footprint checks and region/mesh validation remain part of final acceptance.

`prepare_ankle_candidates.py` produces isolated ankle66 projects from the accepted 09-reprint orientation; every retained mesh member is byte-identical and there is exactly one printed object. The first baseline and dense CLI calls generated `plate_1.gcode` then exited 139 during export because the necessary explicit filament-profile loading step was absent. Root diagnosed and repaired that failure, verified the original failed input, and authorized subsequent guarded experiments. `guarded_orca_slice.py` now requires exact matching material settings and a nonempty profile ID; it passes `--load-filaments`, verifies successful exit and archive G-code filament IDs, and rejects newly observed crash reports. Both side and opposite-end flip exports passed this guard. The earlier plain G-codes remain labeled experimental. Final accepted printer files still require native GUI thumbnails and full-job acceptance.


## Ankle functional choice

`flip_dense/ankle66-flip_dense.3mf` uses the latest exact opposite-end candidate from `geometry/surface-audit.json`, with the same dense interface/bridge parameters and auto brim. It points all four screw-head seats upward, retains near-vertical screw axes, and removes downward exposure from the sampled sliding-pocket wall and narrow ring shoulder. `side_plusX_dense` points those seats sideways but creates horizontal-hole ceilings; its much lower total bridge length does not establish better critical-feature fit. Keep whole-part appearance and exact functional interfaces distinct.

`audit_ankle_bore_core.py` maps actual sampled native bead centerlines into the exact source frame. It checks a strict0.6mm radial through-bore core from0.25–1.5mm inward from each seat. Flip has no model or support paths in those four cores. This is a finite core-clearance check, not full bore-diameter, layer-envelope, seat-planarity or physical fit acceptance.

`baseline89-authoritative-trace.json` joins all89 original manifest indices and40 geometry families to annotated functional surfaces, support-removal access checks and actual native feature metrics. It spells out traceability, adhesion, critical surfaces, hole bridges, support access and physical acceptance boundaries for the root's final group replacement work.
