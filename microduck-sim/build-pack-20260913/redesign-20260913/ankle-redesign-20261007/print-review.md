# Ankle redesign: print-facing review

Problems P5/P6. All six source solids and six rigid-oriented exports pass geometry/hash readback. **The cheeks have no settled recommended print orientation.** Their exported+Z pose is a trial only. No native sliced plate, printed fit, load rating or commissioning is accepted. No slicer or printer was operated.

## Source identity and orientation

The files in `PRINT-STL/` contain proper rigid rotation/translation only, with bottomZ0 and XY bounding-box centre0. Exact matrices, source/output hashes and float32 triangle identity are in [print-review.json](print-review.json). Local/world files remain assembly/evidence CAD. Orange base/cheek and black sleeve are retained.

- **left_base — geometric starting pose**: local_positive_X_down; flat contact81.14mm², model-only section0.2mm abovebed81.22mm²/1island(s). [left-base-PRINT.stl](/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/ankle-redesign-20261007/PRINT-STL/left-base-PRINT.stl)
- **left_cheek — TRIAL ONLY**: local_positive_Z_down; flat contact57.60mm², model-only section0.2mm abovebed57.60mm²/2island(s). [left-cheek-PRINT.stl](/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/ankle-redesign-20261007/PRINT-STL/left-cheek-PRINT.stl)
- **left_sleeve — geometric starting pose**: local_negative_Z_down; flat contact66.76mm², model-only section0.2mm abovebed82.47mm²/1island(s). [left-sleeve-PRINT.stl](/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/ankle-redesign-20261007/PRINT-STL/left-sleeve-PRINT.stl)
- **right_base — geometric starting pose**: local_negative_X_down; flat contact81.14mm², model-only section0.2mm abovebed81.22mm²/1island(s). [right-base-PRINT.stl](/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/ankle-redesign-20261007/PRINT-STL/right-base-PRINT.stl)
- **right_cheek — TRIAL ONLY**: local_positive_Z_down; flat contact57.60mm², model-only section0.2mm abovebed57.60mm²/2island(s). [right-cheek-PRINT.stl](/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/ankle-redesign-20261007/PRINT-STL/right-cheek-PRINT.stl)
- **right_sleeve — geometric starting pose**: local_negative_Z_down; flat contact66.76mm², model-only section0.2mm abovebed82.47mm²/1island(s). [right-sleeve-PRINT.stl](/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/ankle-redesign-20261007/PRINT-STL/right-sleeve-PRINT.stl)

Those areas are mesh sections, not actual extruded first layers or adhesion evidence. Six cardinal directions were compared on both real side meshes. There is no universal minimum bed-contact area.

## Why these starting poses, and why the cheek remains a trial

The left base+X and right base−X poses land an actual81.14mm² side facet as a single island. The four output seats and399.17mm² inner motor-contact plane become vertical;32 native-schedule output-seat probes per side verify the preserved surfaces. This avoids placing the large motor face above support. It creates horizontal original output/central bores and the newØ1.6mm transverse pilots, which need actual native roof/bridge and clear-bore checks. A vertical face finding is not a native quality result.

A base+Z pose would begin on only49.8mm²/two post pads with the original split face8.7mm above bed. That is not the old broad split-face contact, and is not selected. ±Y directions have tiny or nonplanar first contact; the oppositeX direction lacks the designed planar facet.

Cheek+Z keeps its22.75mm² inside capture lip upward and ring pocket vertical, while both new transverse screw head seats are vertical (16 STL probes per side). But it starts on57.6mm²/two tab pads, with the old main exterior plane4.1mm abovebed and other surfaces above support. Cheek±X has only21.8mm²/one pad and introduces horizontal14/15mm bearing-pocket ceilings. Cheek−Z gives a better contact island but turns the capture lip downward. The lower global overhang area of a side pose cannot accept a rough sliding bore. **No cheek pose is declared a settled print recommendation:** native support/bridge paths and an actual sample must select this tradeoff.

The black sleeve has a broad66.76mm² annular bed face with its bore vertical; the geometric0.2mm section is82.47mm²/one island and no downward45°region lies above0.4mm. This axial starting pose avoids a sideways sliding bore.

- **left bracket envelope, local axes**: source36.50×25.50×39.49mm → candidate36.84×25.50×42.95mm; axis changes+0.34/+0.00/+3.46mm. Coordinate directions are recorded explicitly; this is not a load or gait-clearance rating.
- **right bracket envelope, local axes**: source36.50×25.50×39.49mm → candidate36.84×25.50×42.95mm; axis changes+0.34/+0.00/+3.47mm. Coordinate directions are recorded explicitly; this is not a load or gait-clearance rating.

## Fit, existing hardware and process limits

The actual sleeve is ID10.39987–10.40000mm, OD14.59982–14.60000mm, width2.8mm, with approximately2.10mm radial wall. It is a plain floating bushing: both inner and outer interfaces can slide. Roughly0.2mm radial clearance on each can combine to approximately0.4mm radial play; stiffness, wear and installed fit remain physical questions. Its end chamfer leaves the flat end at radius7.1mm against a lip beginning near radius7mm, only about0.1mm flat radial overlap. The larger middle diameter still gives geometric capture, not a contact-pressure rating.

The final mechanism has transverseY M2×8TAP screws and open tongue/slot guides, **no round pegs**. TongueX width2mm in a2.2mm channel has only0.1mm nominal clearance per side and still needs its own printed fit check. The pilot post has4mm X width around a1.6mm pilot:1.2mm nominal radialX wall, roughly1mm after forming a nominalM2 external thread. That last value is an engineering estimate because real threads are not modeled. The retained4-wall setting cannot establish four complete lines in every thin rail or a verified tightening torque. Use the final mechanical report for actual screw heads, engagement, tip margin and access; ordinary machine screws do not become TAP screws by diameter alone. No missing-stock or purchasing need is inferred.

Keep the known orange/black ordinary PLA context. The earlier0.4mm-nozzle/0.2mm-layer profile with4walls and30%infill is only a source starting point. [Prusa design guidance](https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135) supports choosing layer/face direction deliberately and testing actual fits, with no universal tolerance. [PLA guidance](https://help.prusa3d.com/article/pla_2062) does not certify this joint’s clamp load, fatigue, temperature resistance or wear.

No generic coupon was produced. If a later print trial is requested, the actual small sleeve in its final orientation is the useful local fit sample; test inner and outer fits independently, then the open guide/cap before using screw force to close the assembly. Do not infer guide fit from the sleeve’s larger clearance. Native layer coverage, support extraction, hole/guide bead envelopes, full plate footprint and real thumbnails are still required by [the printing workflow](../printing/WORKFLOW.md). The old photograph’s rough downward screw seats remain a regression; surface quality has not been proven by this new CAD or its animation.
