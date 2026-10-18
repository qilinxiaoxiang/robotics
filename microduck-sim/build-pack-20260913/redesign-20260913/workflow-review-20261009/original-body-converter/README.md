# Original body and converter restoration

Current user direction, 2026-10-09: reject the central battery and increased hip spacing, retain the original body/leg arrangement, and use the former battery location for the existing DFR1202 converter. This supersedes the archived C layout. Problem P0/P5/P6; no printing or deployment performed here.

## Fusion reference

`fusion-import-manifest.json` contains 161 named mesh parts, each with color, source file/hash, a millimeter translation and expected final world bounds. It reuses the archived C STL files without modifying them. Apply **each `importTranslationMm` exactly once**: 20 left-side parts move -11 mm along Y and 20 right-side parts move +11 mm; other parts stay fixed. Fusion's internal centimeter coordinate system requires dividing these millimeter translations by 10 after a millimeter import.

Final hip yaw spacing is 35 mm and hip pitch spacing is 85 mm. Internal leg geometry is unchanged. The final current head meshes are retained. There is no bank, C bridge, lowered8 skeleton or new battery tray. The eleven-fuse carrier and its four dedicated nuts are excluded explicitly. Current power distribution is reviewed separately; removing these display parts is not a replacement electrical protection specification.

`expectedFinalBoundsMm` is the per-part readback target. The source point clouds and prior STL export readback are in `../central-cad/`; this package does not convert their meshes into invented native solids.

## Existing converter installation

DFR1202 is retained at world center `[-35.5, 0, -14]` mm. Its XYZ receiving size is `8 × 26 × 30` mm, with bounds `[-39.5,-13,-29]` to `[-31.5,13,1]`. [DFRobot's official product page](https://www.dfrobot.com/product-2907.html), checked 2026-10-09, specifies module size 30 × 26 × 8 mm. The mesh is this published installation envelope, **not native component, solder-pad or connector CAD**.

The existing black open insert is reused. It gives 0.3 mm nominal side/rear clearance, 0.6 mm at the lower support and 2 mm to the front frame. Use the already modeled insulating edge liner and removable ties at the two existing band stations. Do not cover components, exposed pads or the rear thermal face. No new mounting screw or new printed component is proposed.

Wire and insulate the converter on the bench while the insert is loose; then insert the prewired group and retain it through the existing band passages. The exact solder fillets, attached wires and their exit geometry are not represented by the module box. Do not infer a seated USB/JST socket from its center. Practical prewiring avoids claiming solder-tool access through an already closed torso. The module's rear thermal pad and actual operating heat remain commissioning checks, not reasons to change this mechanical baseline arbitrarily.

## Provenance: original versus prior changes

The community source-12 power support is `hardware-design-20260912/whole-robot-20260912/assembly/compact-battery/original-power-support-body.stl`, reconstructed from the pinned source 3MF and recorded registration. It occupies X -31..-14, Y ±27.249, Z -44.068..39.422 mm; volume 10487.5 mm³.

The retained `power_support` is the **previously designed integrated replacement**, not an upstream original. Its existing generator added battery stops/tie passages, a lower former-regulator deck and an inner former-regulator pocket while preserving the motor interfaces. It occupies X -59.1..10.25, Y ±27.249, Z -57.5..39.422 mm; volume 18822.1 mm³. The existing `regulator_insert` is also a prior assistant-designed part. This restoration preserves those already modeled/printed parts rather than starting another mount redesign. Its older empty auxiliary features are not being relabeled as currently populated hardware.

The converter and insert also have zero intersection with the original community support in the provenance comparison. That observation does **not** replace the currently retained integrated support or establish identical retention without its added stops and belt openings.

## Bounded verification

`converter-local-fit.json` records all 320 expected static comparisons for converter and insert against the restored 161-part scene. All are clear, using exact valid solid intersections for overlapping bounds and explicit separated-AABB proofs elsewhere. Converter-to-insert minimum gap is 0.299999 mm; converter-to-support is 5.247685 mm.

Two existing assembly motions were rechecked against their immediate mating parts, each at 57 positions with 0.5 mm spacing: board from +Z28 into the loose insert, and the combined insert/board from -X28 into the support. Both have zero rigid intersection. These samples do not include the attached leads and do not certify a continuous full-robot motion domain.

The previous September mechanical report is linked as historical evidence: 250 trajectory frames, 31500 pair checks, no then-recorded collision. It is not rebranded as a new all-joint test of the current head. Current local verification used 134 MiB and 1.42 seconds; no broad robot collision search was run.
