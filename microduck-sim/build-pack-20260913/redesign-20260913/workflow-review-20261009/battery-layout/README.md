# Central PB1033MI layout — stage A review

These are envelope concepts, not printable parts or assembly acceptance. The existing V1.4 files are unchanged. The blue battery is the published 80.9 × 65.9 × 26 mm box. Grey objects are existing leg bounding envelopes, translated as complete assemblies. Red objects are the existing central chassis/power geometry that still occupies the proposed battery space.

The current hip yaw axes are 35 mm apart; hip pitch axes are 85 mm apart. The narrowest conservative gap between the two yaw-link bounding envelopes is 12.002 mm. The torso's outside width is not its available cavity width.

- A, wide face across the hips: total widening 62 mm, 31 mm per leg. Battery depth/width/height is 26 / 65.9 / 80.9 mm. This is a large stance change and is not preferred.
- B, thin edge across the hips, upright: total widening 22 mm, 11 mm per leg. Depth/width/height is 65.9 / 26 / 80.9 mm. New yaw/pitch spacing is 57 / 107 mm. It uses less front-to-back length, but the upper cable end competes with the central neck region and the lower port needs unobstructed access.
- C, thin edge across the hips, long axis front-to-back: the same 22 mm total widening, depth/width/height 80.9 / 26 / 65.9 mm. It is 15 mm lower than B. Its two end faces can remain broadly open at the front and rear. This is the preferred next **review** candidate, not an approved placement.

The width calculation includes 1 mm battery clearance, a provisional 2 mm channel wall and 1 mm nominal wall-to-moving-part space on each side, then rounds total widening upward. These wall dimensions are design allowances, not a strength result. The dashed 25 mm service space at each port end is a declared trial allowance, not a measured Xiaomi cable/plug dimension. B and C battery bodies fit the lateral screen; neither has a fully free central cavity today.

A new torso base/bridge (community 34, Black), revised central power support (Black), revised left/right torso-shell interfaces (community 8/10, Orange), and relocated converter insert (Black) need investigation. Neck-axis locations must remain unchanged when widening the lower torso. The old eleven-fuse carrier appears only as existing occupancy; the user-requested electrical architecture review will decide whether it remains. Do not silently remove necessary electrical protection or assume that old architecture is already approved.

Preserve each assembled leg's internal geometry. Translate the yaw motor and its whole associated hip/leg subtree together, with matching base mount and bearing features. Moving only a lower leg would break the original alignment. Any adopted widening also changes joint origins, mass distribution and stance; it requires model and walking-policy revalidation.

Files:

- `central-battery-layouts.svg` and `.png`: visually inspected English front/side comparison.
- `central-battery-A-concept.step`, `-B-`, `-C-`: valid named BREP envelope boxes and yaw-axis cylinders. Each file contains 24 valid read-back shapes. They are deliberately marked as bounding context, not detailed original component solids.
- `layout-report.json`: dimensions, proposed placements, affected parts, explicit old-occupancy warnings and source hashes.
- `step-export-receipt.json`: STEP hashes and read-back checks.

No full-robot collision search, insertion-path validation, load/thermal/power test or new print geometry was performed. The first CadQuery exporter exceeded the 512 MiB guard and was stopped; its failure is retained in `step-resource.json`. The OCP-only exporter completed within the same 512 MiB limit; see `step-ocp-resource.json`.
