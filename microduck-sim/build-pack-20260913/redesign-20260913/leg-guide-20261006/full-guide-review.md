# Independent full-guide source review

The final frozen exporter v4 source and bundled HTML review passes. Browser interaction acceptance is separate and remains owned by the main branch.

- Actual source bindings match the current files, including the accepted left-leg data and original community 3MF.
- The 103 displayed meshes and 154 individual screws are introduced exactly once across 76 operations. The 56 installed prints use distinct stock instances; the remaining 33 complete the original 89-instance inventory.
- Fifty-one new community/current source meshes match their source geometry with unchanged triangle counts and bidirectional vertex error below 0.00002 mm. All accepted left mesh payloads remain exact.
- All 15 motor reference poses match the independent FK lookup from the original per-hole schedule. Maximum measured world-vertex error is 0.00000761 mm.
- Thirty-four electronic screws use the source head points and the opposite of the source insertion axis as their outward guide axis.
- Eight washers and 17 nuts match the specified stack positions. Camera head points already include their washers: camera `washer_mm=0` is intentional. Adding another 0.5 mm to those heads would move them incorrectly.
- Motor groups, 15 DATA links and 12 used Pi physical pins match the current wiring contract. Speaker outputs remain floating; the 100 kΩ GAIN-to-VIN connection retains 3 dB gain.
- The final actual HTML decompresses to the exact current v4 assembly payload, embeds the exact current wiring JSON and contains the current viewer source.

The earlier electronics-selector description and stale left-source hash have been corrected. Generic approach animations visibly state that they are illustrative. The viewer keeps a physical fitting checkpoint where the complete rigid insertion path is not established; partial ankle demonstrations do not prove later lower-link closure.

The screw-head primitives are generic display shapes. Their nominal diameter is 1.7 times the thread diameter and height is 1 mm; they are not the supplier head dimensions. The sourced washers, nuts and source meshes receive the geometric checks above. No screw-head fit, collision-free insertion path, actual printed fit, motor calibration, power commissioning or camera-guided pickup is certified by this review.

Evidence: [full-guide-review.json](/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/leg-guide-20261006/full-guide-review.json) and runnable [verify_full_guide.py](/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/leg-guide-20261006/verify_full_guide.py). This reviewer performed no GUI, printer, motor, purchasing or power action. The frozen exporter v4 data SHA is fa087e05d48e6c5cce5f13fd62573a319eb4c8cf74c263268990954c7e6d9f60. The final regenerated bundle now matches this frozen data; the review JSON binds its exact guide and source hashes.
