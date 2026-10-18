# Camera inside the existing central eye

**The eye-camera candidate is spatially feasible against a first-generation Pi Zero outline reference; Pi 3 and complete Zero-board fit are unverified.** The available board is Pi 3 or first-generation Zero, explicitly not Zero 2 W; exact subtype/revision is unknown. The native head has one central eye with a 30 mm outside diameter. The proposed pose retains that eye outline and puts the lens 1.4 mm behind its front rim. The camera tower and tilt cradle are removed from the candidate assembly.

This is a clearance and optical-view candidate, not a finished camera mount. The current face and eye trim require local internal changes; a four-point removable camera retainer and the full ribbon loop remain to be designed and checked.

## Measured package

The lens-front center is `[88.0, -0.0913782, 131.1145973]` mm in the current guide's world frame, looking along +X. The transform from the current rooftop camera is a pure translation of `[29.9349884, -0.0914527, -62.0667179]` mm.

- Camera to the Zero-outline reference slab: **6.920 mm** minimum modeled separation. The four original Pi screw-pilot neighborhoods are untouched.
- Camera to existing cap: **4.730 mm**; to OpenRB: **16.363 mm**.
- New face/trim camera pockets retain **0.300 mm** nominal envelope clearance.
- Both replacement candidates are watertight, single connected bodies. The pocket includes the rear-entry corridor. Any severed obsolete central-post remnants are removed; the outer Pi mounting posts remain connected and untouched.
- Sampled front skin created by the PCB pocket is at least **1.399 mm** thick along X. A thinner **0.298 mm** native lip survives unchanged elsewhere in the sampled area; this geometry check does not establish strength.

The original unmodified face intersects the camera by about 69.0 mm³ at this pose, and its eye trim by 1.89 mm³. Simply moving the camera in the animation would therefore be wrong. The candidate STLs contain actual local boolean relief, while keeping the outer face bounds, eye outline, the Zero-outline slab pose and its pilots.

## View through the eye

The official Wide camera has a 102° horizontal and 67° vertical field of view. A conservative geometric frustum beginning just beyond the lens, including a 6.95 mm square pupil envelope, has zero intersection with the candidate eye, face, cap and retained head components out to 200 mm. No cover glass is introduced. This checks geometric obstruction, not optical distortion or actual image calibration.

At zero tilt, a point at the approximately 109 mm beak height enters the lower image boundary only about 33 mm forward of the lens. The official closest focus is approximately 50 mm. The camera can support approach/alignment, but a target at the final mouth-contact position may be outside the image or focus range. Head pitching and a real near-grasp view test remain part of the visual-pickup design.

## Assembly and remaining mount work

Install the camera and latch its ribbon on the detached face **before mounting the Pi**. The script samples rear camera entry at 0.25 mm spacing against the candidate face and eye trim. The first 12 mm of the ribbon exit is reserved and clear; the full loop and populated board connector are not verified. Pi 3 requires separate geometry and routing; it is not represented here.

The four camera mounting-hole interfaces are exported in `camera-eye-feasibility.json`. They follow the official 21 mm × 12.5 mm pattern with 2.2 mm holes. The candidate does not yet include a retainer. Use those four board holes for a removable retainer, leaving the autofocus body free, and verify screw access, nut retention and cable/latch access before treating it as an assembly-ready replacement. The rooftop M2/M3 hardware cannot be reassigned without that stack check.

## Files and provenance

- `camera-in-eye-world.stl`: camera installation envelope at the proposed pose.
- `face-eye-camera-clearance-world.stl`: source face with local camera/ribbon relief and obsolete central-post remnants removed.
- `eye-trim-camera-clearance-world.stl`: source eye outline with local rear lens-body relief.
- `camera-eye-feasibility.json`: transform, native mesh hashes, collision results, topology, mounting interfaces, optical test and explicit remaining work.
- `camera-eye-wall-samples.json`: directional wall samples, including the unchanged thin native lip.
- `camera-eye-feasibility.py`: reproducible isolated generator/checker. Run with the CAD Python environment.

The source camera is the existing dimension-built installation envelope, not detailed manufacturer CAD. Its dimensions were checked on 2026-10-08 against the [official product page](https://www.raspberrypi.com/products/camera-module-3/), [Wide mechanical drawing](https://datasheets.raspberrypi.com/camera/camera-module-3-wide-mechanical-drawing.pdf), and [official hardware specifications and connector instructions](https://www.raspberrypi.com/documentation/accessories/camera.html#hardware-specification). The product gives approximately 25 × 24 × 12.4 mm; the component envelope models 25 × 23.862 mm PCB dimensions and 12.17 mm overall depth, so the local 0.30 mm relief remains part of the candidate. Actual board, autofocus motion, print fit and final cable routing are not established by these meshes.

Canonical guide and build files are unchanged by this isolated generator. Physical fit and functioning have not been tested.

## Board identity and camera cable — corrected 8 October

The user has a Pi 3 or a first-generation Pi Zero, not a Zero 2 W; exact subtype/revision is unknown. The current model measures 65 × 30 × 1.6 mm and represents only the Zero PCB outline. The 6.92 mm gap and preserved pilot regions apply to that reference slab; populated components, headers and connectors still require verification. No conclusion about retaining a Pi 3 in this position is supported.

The [original Zero official dimensions](https://www.raspberrypi.com/news/raspberry-pi-zero/) are 65 × 30 mm. For comparison, [Pi 3 B+ official drawings](https://datasheets.raspberrypi.com/rpi3/raspberry-pi-3-b-plus-product-brief.pdf) show an 85 × 56 mm board; the [official 3A+ drawing](https://datasheets.raspberrypi.com/rpi3/raspberry-pi-3-a-plus-product-brief.pdf) shows a 65 × 56 mm board. These are different geometries, not interchangeable fit results.

[Official connector documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html) specifies a 22-pin, 0.5 mm camera connector for first-generation Zero with CSI (original Zero rev1.3 or Zero W); earlier original Zero revisions have no CSI connector. Pi 3 A+/B/B+ uses 15-pin, 1 mm CSI. Camera Module 3 has a 15-pin connector, so Zero uses a 15-to-22-pin cable while Pi 3 uses 15-to-15-pin. The exact board and cable route must be established before choosing an assembly layout. No procurement is implied. Sources verified 2026-10-08.
