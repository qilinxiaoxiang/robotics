# Functional-surface geometry audit

Problem P5/P6; verified 2026-10-06. This folder owns geometry evidence only. It does not modify any source STL, current 3MF, printer setting, colour assignment, or print quantity.

Run `audit_surfaces.py` with `/tmp/microduck-current-check-venv/bin/python`. Use `--verify-only` to check the saved source hashes, rigid rotations, volume preservation and 89-instance coverage without regenerating the measurements. A successful exit verifies the audit's integrity; it does **not** accept a new print file or physical fit.

`surface-audit.json` covers the six final primary printer projects: all 89 instances and 40 unique source-geometry families. Exact source hashes deduplicate repeated hardware but each instance retains its current native transform and its own measurements. `native-review-queue.json` contains the subset needing focused native slice review, including actual screw/mating surface samples and up to three candidate rigid rotations. `ankle-early-candidates.json` preserves the specifically requested +X-side-down candidate for each ankle.

## Why the old ankle passes adhesion and fails quality

The current source66 first-layer section is about 335.76 mm². Nevertheless, all 32 sampled points across the four countersunk screw bearing annuli face downward and float above the bed. The actual ring pocket's narrow axial seating shoulder also faces downward. A pass based only on broad first-layer contact would miss both functional interfaces. The regression therefore tests the four real bearing annuli, rather than total normal-down area alone.

Source64 is evaluated independently: its opposite-end-down orientation leaves the four output bearing annuli and the ring pocket's narrow shoulder upward. It is retained unless native/physical evidence establishes another defect. A mirror shape does not imply the same supported functional surface in its actual print orientation.

## Measurement and limits

- The native final 3MF meshes are transformed exactly. Source-to-native vertex alignment is checked within 0.025 mm.
- Joint screw schedules are mapped back into the original source meshes. Eight annular rays per bearing interface capture actual triangles and their surface normals. These are sparse interface samples, not full surface coverage.
- Electronics schedules list board or mounting axes. The matching real assembly STL is rigidly fitted to its print STL; rays on each documented axis find the nearest printed mounting interface. The report distinguishes this from a board screw-head plane.
- Sliding rings and idler/cap bores are sampled at three axial depths and sixteen radial directions. The sign of the hit normal separates cavity walls from external silhouettes. The ankle shoulder is sampled at radii 7.1 and 7.3 mm: its centre is through-open, so smaller radii would miss the real shoulder.
- A surface normal below −cos(45°), above the bed by more than 0.4 mm, is a geometric support-demand proxy. Actual bridge, support interface, floating wall, support exclusion, and clearance require native toolpaths. Total surface area is a comparison metric, never an automatic quality threshold.
- Every geometry family has named screw seats, mating/sliding surfaces, blind pilots, seams or support extraction paths. Unsupported samples and custom open channels remain explicit native/physical checks; missing evidence is never relabelled a clear surface.

## Applying candidate transforms

Each `delta4x4` operates on the old final printer project's world coordinates. Left-multiply that matrix into the object's build transform, then independently repack and recenter the regenerated full model/support/brim footprint. A candidate is landed on the bed and retains volume; it carries no new slice, profile or packing acceptance.

Candidates first prioritise sampled functional surfaces, then global downward area. Smaller bed contact, horizontal holes, supported seats and unsampled features are explicit tradeoffs. Rotating an ankle to its side changes which walls cross layers and makes circular hole ceilings horizontal; compare bridge sag, hole clearance, screw bearing flatness and printed wall strength before accepting it. A denser interface can improve a support-contact surface but cannot by itself prove clearance or remove trapped support.

## Native and physical acceptance

For each nominated part, compare the same functional ROI between the old file and candidate. Check actual model paths, bridge paths and support-interface contact at their real layer heights. Inspect every blind pilot, slot and cavity for an extraction route, including the fuse carrier's lower open-ended channels, motor bays, jaw sliding seat and head posts. Retain good orientations rather than changing all parts to a common pose.

Acceptance of a new file additionally requires its machine/nozzle/plate/material, regenerated first layer, support access, full extrusion footprint spacing/centering, native export and embedded thumbnail. Physical hand assembly checks screw seating, sliding clearance, support remnants and hole roundness. No physical quality acceptance is asserted by this audit.

## Final native checks

`verify_final_geometry.py PACKAGE_MANIFEST --output REPORT.json` verifies exact source mesh bytes, all instance identities, rigid selected rotations plus packing yaw/translation, actual bed contact, machine/material invariants and 89 distinct primary indices. Native print-only `.gcode.3mf` archives legitimately have no editable mesh; their emitted material paths are independently checked.

`run_native_package_checks.py NATIVE_MANIFEST` reads `project` plus `archive`, `gcode` or `native_archive` for each printer/group. It writes per-variant bore/seat reports and `native-functional-verification.json`. Exact source/project/native/checker hashes invalidate cached reports. All ten variants and all 89 distinct primary indices are required. Missing variants remain a separate incomplete-coverage state.

The known-empty core is a finite **source** volume: every source triangle intersecting its axial slab is clipped to both planes, then its projected convex polygon's exact minimum distance to the bore axis is evaluated. The cylinder radius is the minimum source boundary distance over the whole slab minus the documented 0.10 mm radial discretization allowance. This preserves actual tapered/pilot geometry rather than asserting a major screw diameter. Four third-depth source28 probes cross its original blind bottom and are recorded as invalid empty-volume tests; its first two depths remain tested. The final requirements contain 586 valid finite levels across all 89 instances.

Native core tests include actual width and height. Ordinary native beads use the slicer's rounded-stadium section from OrcaSlicer 2.4.2 `Flow::mm3_per_mm`; its conservative 3D bound is an XY disk of radius `(width-height)/2` plus a sphere of radius `height/2`. Bridges and widths smaller than height retain the more conservative box/slab bound. Potential model overlaps additionally use a directly evaluated support-function separating plane, including the finite cylinder's end planes. The numerical intersection tolerance is 0.001 mm. Fitted G2/G3 arc sagitta and measured fit residual are included. The regression rejects deliberately invading beads and correctly maps the Bambu command coordinate frame to deposited material by adding its actual `[0,2]` nozzle offset. A negative conservative bound alone is not proof of physical invasion.

Native `_id_N` identifies the emitted ModelObject's build ordinal; persistent `identify_id` is a different metadata value. Repeated parts bind by exact printed name plus native ordinal, with their own actual transformed ROI. Bambu command coordinates are inverted before every material comparison. Packing translations remain independent of that coordinate correction.

A functional mesh probe can fall between interface stripes. Besides direct bed/interface/prior-model footprints, the check measures the actual model centreline against real anchor footprints. It requires at least 0.10 mm lateral bead overlap. A short unanchored span is accepted only along a real connected same-layer native path with each end reaching at least 0.40 mm continuously supported anchor, a conservative total free-span bound of at most 4 mm, and main-span speed at most 30 mm/s. Sparse-point matching allows the documented 0.025 mm surface discretization plus the native 0.001 mm XY coordinate rounding bound. It does not claim a flat, smooth physical face.

`old-ankle-native-roi-rejection.json` is the direct old-native negative fixture: its four actual output annuli contain real model beads, all 32 samples face downward away from the bed. This selected quality target fails even if supports exist underneath. The same four annuli in the final flipped66 pose face upward. Open source-axis escape routes are only necessary extraction evidence; intact support removal, hole roundness, screw fit and surface finish remain unverified physical work.

The native Bambu 2.8.02.61 profile was independently checked against its [official Flow.cpp](https://raw.githubusercontent.com/bambulab/BambuStudio/v02.08.02.61/src/libslic3r/Flow.cpp): `mm3_per_mm` uses the same rounded-stadium ordinary profile and circular bridge profile. Its [GCode.cpp](https://raw.githubusercontent.com/bambulab/BambuStudio/v02.08.02.61/src/libslic3r/GCode.cpp) emits the actual path width and effective extrusion height. Both primary files are saved here with their version in the filename. These nominal native bead profiles remain digital geometry; actual deposited shape is a later physical measurement.

Bambu yellow provided a genuine process discrimination after the geometry/parser false holds were removed. The two small source2 closure annuli had 15 modeled downward samples without local interface/finite anchor evidence. A controlled same-geometry, same-position native trial changed only `support_remove_small_overhang` and `support_interface_not_for_body` from1 to0. The first annulus gained direct interfaces at8/8 samples; the second gained6/8, with the remaining samples explained by real neighboring native material. The controlled and subsequently recentered native files both passed the four-part ROI and12 valid finite-core checks. `control-yellow-twoflags-comparison.json` preserves this baseline/perturbation evidence. This does not prove physical screw seating or finished surface smoothness.

Final functional binding prefers the formal native `archive` over a separately extracted `gcode` path. A previously audited extracted file can be rebound to its formal container only after proving **all original embedded G-code bytes** identical, with the exact project and checker source hashes unchanged. The per-report container `file_sha256` and original-byte `gcode_sha256` are distinct and both match the final package. Native archive machine/material/semantic geometry are still mandatory in the separate geometry gate. No header stripping or assertion of merely unchanged physics permits reuse.

Final verified package SHA256: `efc34cd1b8a0b19906e198c1c358121a2dfdbc3704e07d95030b2c3e7825b214`. `final-geometry-verification.json` and `native-functional-verification.json` both pass, with ten variants and all89 distinct primary instances. The old ankle's native ROI still fails the four real downward output annuli. Physical fit, support removal and finished surface quality remain unverified.
