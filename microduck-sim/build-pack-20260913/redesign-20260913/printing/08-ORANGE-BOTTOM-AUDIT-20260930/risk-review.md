# Independent orange bottom-cut risk review

Reviewed 2026-09-30 for P5/P6. Read the current PROJECT-CONTEXT first. This is an evaluation only: no STL, project or G-code was changed.

## Decision

**Do not apply a blanket 0.75 mm bottom cut to any of these four parts.** None is demonstrated to need this dimension-changing operation. The observations below establish real material and feature changes; the main audit separately checks flat contact facets and native first-layer paths. Actual plate cleanliness, calibration, adhesion and the printed first layer remain physical observations. This review does not claim that an arbitrary uneven STL can never benefit from a deliberate cut.

- **community-8, left shell: no cut.** Source object 8 (`7.obj`) closely matches the assembled left shell (95th-percentile vertex residual 0.00231 mm). It participates in motor12 horn attachments and a hip-yaw case mount in the verified fastener map. The current print bottom is at Z=0. A 0.75 mm slice removes **481.244 mm³, 4.225%** of the model. Bottom-facing shell walls sampled by vertical rays are approximately2.2 mm; remaining first-wall thickness at affected sampled positions drops to **1.449625 mm**. This is thinning the shell, not merely removing a numerically tiny protrusion. Correct its diagnosed orientation error by rigid rotation; do not remove shell material.

- **community-10, right shell: no cut.** Source object10 (`8.obj`) matches the right shell to0.00256 mm at the95th percentile. It also carries motor12 horn and hip-yaw case interfaces. Its current broad bottom face has only a0.038° tilt. The opposite shell (community-8) has the significant1.997° tilt; see orientation-review.md for the later measured diagnosis. A blanket cut removes **1133.758 mm³, 10.108%**. Sampled remaining first-wall thickness reaches **1.450368 mm**. Its angled bottom must be assessed with the intended support and actual first-layer paths; a larger flat contact patch alone does not justify removing this much functional wall material.

- **community-60, hip bracket: no cut.** Source object60 (`b.obj`) is the repeated hip-bracket geometry also represented by source14; reference match residual0.00289 mm. The print height is34.5 mm. Cutting0.75 mm removes **125.891 mm³, 2.782%** and truncates the original low edges. A cross-section at the proposed cut passes through a circular recess approximately **4.84 mm across**, so the operation changes material surrounding a designed pocket. Twelve grid-sampled low material spans would disappear entirely; these are local edge/taper spans, not evidence that twelve whole features disappear. Remaining thicker sampled spans do not prove that removing the edge is harmless. Preserve the existing bracket and its checked mating geometry.

- **community-18, thin four-hole plate: no cut.** Source `e.obj` is a20×11×2 mm plate with four approximately2.3 mm through-hole contours. Cutting0.75 mm reduces its thickness to **1.25 mm**, removing **149.958 mm³, 37.500%**. The screw-bearing thickness therefore changes by0.75 mm. The historical inventory labels its nearest reference mesh `neck`, but that registration has a poor6.85 mm95th-percentile residual; that label is not adequate evidence for an exact installed connection. Its directly measured dimensions and hole pattern alone decisively rule out treating0.75 mm as harmless cleanup.

## Native evidence and limits

The current editable07-COMPACT3MF was read directly, recursively applying each component transform and build-item transform before measurement. All four model bounds have minimumZ=0. Removed volumes were calculated in memory by clipping each original triangle against Z=0.75 and integrating its oriented surface contribution; the new horizontal cut-face contribution vanishes when the divergence-field datum is Z=0.75. No replacement mesh was generated or saved.

Independent wall sampling used45×45 vertical rays through the original oriented STL footprint and sorted surface intersections. These STL vertical extents match the current project; horizontal placement/rotation does not change vertical thickness. Reported minimum wall values are sampled measurements, not certified global minima or strength tests. The circular pocket/through-hole sizes are measured bounds of the actual section contours. This review does not assert that the proposed cut directly intersects every functional hole center; it demonstrates measurable changes to walls, local pocket material and the thin plate stack.

A suitable future rule is to **check transformed bottom contact and native first-layer support before printing**, not to automatically remove0.75 mm from every STL. If a particular first layer proves problematic, change only that identified part after checking its dimensional and mating consequences, then reslice and reverify. The user reports fragmented contact in the slicer. The later orientation review identifies and corrects community-8; a physical adhesion failure has not been reported for these four files.

## Source hashes

- `/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/PRINTING/04-FOUR-COLOR-20260929/07-COMPACT-CENTER-20260929/Elegoo/orange/MicroDuck_Elegoo_orange_COMPACT_editable.3mf`: `1d392d18f6175ead4c6b650932bd42902f4f3ce200c3f3c7a6f37fb2e9536901`
- `/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/assembly/community-print-inventory.json`: `66aa8d07afb2a89201487af4f6a6b20bdeb3dc24c51ebef2e0d5d048b02625d5`
- `/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/fastener-audit/joint-fasteners.json`: `3b0151f171350305be0702da1a0f916f8fcd40cbb0a441bc5a95629bf487c5db`
- `/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/assembly/print-parts/community-8.stl`: `c8f0753778630d8e6a0ff56daea9c00a37f7426ba743eba3493c054aa7750f02`
- `/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/assembly/print-parts/community-10.stl`: `18e766ee969fab35151581c6c3b92d83854779139a92591e6fba945ad732012c`
- `/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/assembly/print-parts/community-60.stl`: `8a37a457e689e79dac79e113ff883821d197540b953068b92cd24cb8785c943a`
- `/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/assembly/print-parts/community-18.stl`: `0e5738da8d515a1b964482c7bd7643c3244dbd3a77936ceefafae20a0f7fc6f4`
