# MicroDuck assembly delivery

Start with [index.html](index.html), the generated assembly manual. Editable sources are [ASSEMBLY.md](ASSEMBLY.md), [PRINT-LIST.md](PRINT-LIST.md), [FIRST-ARTICLE.md](FIRST-ARTICLE.md) and [purchasing-impact.md](purchasing-impact.md). All current material is in English. **15 total actuators, including one jaw actuator.**

The directory contains the real-geometry figures, 89-instance print inventory and both Bambu projects. Procurement and electrical sources remain canonical in the sibling directories. Five reader pages are generated locally; no account, API key or service is required by the artifact itself.

## Current manufacturing files

- [Complete 89-instance queue](printing-full/MicroDuck-complete-89-instances-X1C-CoolPlate.3mf): 64 retained source instances, eleven current parts and fourteen explicit idler/cap stock additions.
- [Eleven current parts](printing/MicroDuck-current-11-parts-X1C-CoolPlate.3mf): changed and added mounts only.
- [Print list](PRINT-LIST.md): current slicer predictions, part orientation/support guidance and fasteners.
- `print-manifest.json`: source ID, quantity basis, path, dimensions and SHA-256 per instance.

Both projects use X1 Carbon, 0.4 mm nozzle, PLA, Cool Plate, 0.2 mm layers, four walls, 30% gyroid and tree supports. A different machine or plate requires a fresh correct profile and slice.

## Geometry and verification

The current mounts provide the narrow two-tier eleven-fuse carrier, alarm carrier, ENA-switch saddle and five tie paths. The relieved head cap and replacement motor support close the modeled mouth interference: the new integral sliding seat is coaxial with both jaw ends and the motor output.

- `source-verification.json`: eight frozen source hashes.
- `community-print-inventory.json`, `source-surface-comparison.json`, `source-surface-refinement.json`: actual 3MF extraction and surface comparisons. The jaw and pads match within approximately 0.002 mm; community ankles and sliding rings differ from the official model.
- `service-mounts/verification.json`: 250 recorded poses and 408250 candidate pairs clear for the added service components. This is sampled rigid geometry, not continuous flexible-harness validation.
- `head-din7985-check.json`, `usb-bare-plug-check.json`, `pi-mount-check.json`: head fasteners, bare USB envelopes and Pi mounting.
- `mouth-support/design.json`, `mouth-support/static-check.json`: one connected replacement mesh and no added-material overlap against 41 head objects.
- `mouth-motion-coaxial-conditional.json`: 61 clear jaw poses, 0–30 degrees at 0.5-degree intervals. No physical print or actuated fifteenth XML joint is implied.
- `mouth-motion-conditional.json` and `mouth-motion-trimmed-conditional.json`: retained historical failures before the support replacement. They are not current pass reports.
- `printing*/slice-verification.json`: actual slicer results and input hashes.
- `delivery-verification.json`: generated-page links, absence of tables, current STL hashes, embedded profiles and digital checks.
- `review-visual.txt`, `review-electrical.txt`: historical scoped reviews; current English-figure review is recorded separately.
- `release-hashes.json`: current deliverable hashes.

## Rebuilding

Frozen sources are under `../../hardware-design-20260912/whole-robot-20260912`; community 3MF and official XML paths are resolved by the scripts. The CAD runtime is `/tmp/microduck-cad-venv/bin/python`; pinned library versions are in `requirements-cad.txt`. Slicing uses `/Applications/BambuStudio.app/Contents/MacOS/BambuStudio` 2.7.1.62. No secret configuration is required.

After geometry edits, run the corresponding builder and checker. The jaw support uses `build_mouth_support.py`, `check_mouth_support_static.py` and `check_mouth_coaxial.py`; service mounts use `build_service_mounts.py` and `check_service_mounts.py`. Then run `slice_current_parts.py` followed by `slice_full_print_queue.py`, regenerate print lists and CAD figures, run `build_reader.py`, then `verify_delivery.py`. `export_print_preview.py` regenerates slicer plate images with absolute paths. No browser preview is required by this rebuild pipeline.

First-article fit, exact original case-hole lengths and installed counts, cable motion, received-part measurements, actual mass and powered acceptance remain explicit in the manual and first-article sheet. Digital success is not physical acceptance.
