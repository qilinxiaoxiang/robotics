# MicroDuck ankle assembly redesign — 7 October 2026

Problems P5/P6: the original closed fork obstructs a straight lower-link approach, and its nominal Ø9.65 mm sleeve bore interferes with the roughly Ø10 mm link post. This package develops a local mechanical replacement for review. It does not replace the accepted source files or certify a printed robot.

## Design choice

A larger sleeve bore alone would remove the inner interference but leave the closed-fork access problem. Thinning the fork so it can be forced apart would depend on unmeasured printed-part strain and fatigue. The selected candidate opens the passive side during assembly, then retains that side with two existing M2×8 TAP screws per ankle.

The retained outer side material forms two guide pillars. The removable side slides along open-ended guides; two black M2×8 TAP screws enter from above and retain it. Their modeled engagement is 3.5 mm, with 0.5 mm reserve before the blind end.

The candidate keeps the motor-output and foot interfaces, the original lower-leg link, the motor and the foot. It replaces the orange ankle with an orange base and detachable side, plus a revised black sleeve. The sleeve is a plain floating bushing; both its inner and outer faces can slide. Its axial retaining faces must not be clamped by the new side screws.

## Status and files

The editable generator, candidate STEP/STL geometry, preview manifest, independent geometry checks and print-facing review belong in this directory. `ANKLE-REDESIGN.html` is the self-contained 3D review; the existing localhost guide links to it. `preview-data.json` identifies exact candidate geometry and the actual modeled assembly sequence.

The independent `verify_redesign.py` evaluates the original failure, candidate identities, interfaces, fasteners, assembly poses and joint-motion evidence. `verify_redesign_delivery.py` binds the final files, actual browser controls and baseline design regression. Their reports distinguish source-model results from physical tests.

## Physical decision still to make

A larger sleeve bore improves insertion but adds radial play. The sleeve itself is a small, inexpensive fit sample: check it on the existing link post and inside the new side before committing to an assembled prototype. A nominal CAD clearance is not a measured printing tolerance. The final print review records the candidate's actual clearance and functional-face orientation.

This is a dimensioned prototype package. Layer bonding, screw retention, loaded side stiffness, wear and fit need printed-part evidence. No sliced printer job is included and no print has been started. Preserve the original parts until the replacement is physically accepted.

## How to inspect the prototype

Open `ANKLE-REDESIGN.html` in a modern Chrome browser. It embeds its 3D meshes and runs without an internet connection. Begin with **Identify replacement parts**, then select **New assembly**. Use the slider or **Play** to follow the modeled approach. Click a part name and **Inspect selected alone** to enlarge the washer or sleeve; **Reset view** restores the assembly context. Left and right are separate actual models.

The six files in `PRINT-STL/` are orientation candidates, not a print-ready order: base and removable side in orange, sleeve in black. The base lies on its side so the motor contact face and screw seats stand vertically; the sleeve axis is vertical. The removable side has **no accepted print orientation yet**. Its supplied +Z-down trial keeps the retaining lip upward but leaves a large face above support. A side-down alternative puts the bearing-pocket ceiling over support instead. See the measured alternatives in `print-review.md`; native slicing and a finish/fit sample are still needed before adopting a print orientation. `STL/*-world.stl` serves the assembly viewer and should not be mistaken for print placement. The metal screw-envelope files are visualization aids and must never be printed as hardware.

`CAD/` contains STEP exports. Base and side are mesh-derived faceted solids; the generator retains the original triangle-defined interfaces. The editable Python generators expect this project's source geometry and CAD environment. They are development sources, not a standalone installer. The STEP/STL geometry and embedded HTML can be inspected independently of those scripts.
