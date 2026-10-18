# Native USB passage revision

`FusionBodyUsbNotch.py` runs in Autodesk Fusion and already calls `run(None)` at the end. Execute it once without appending another call. It creates its own named document on first execution; subsequent executions resume that exact open document and preserve completed cuts/rails using the receipt. It never modifies the original assembly or released print files. Only a successful final receipt establishes completed native exports.

The cut extends the existing body opening to X−30.77 with two rear R2 corners, reaches forward to X−19.8, spans Y±7, and cuts Z37–44. This removes the approximately 0.89–1.02mm original roof strip between the former proposed hole and the existing opening. The two original shell meshes already contain source-ID8/10 world registration; the script records their original matrices but does not apply them a second time.

Each half may receive a rear and side rail of 2 mm width and 2.5 mm depth, without bridging the two shells. Source-facet projection places the rail top at least 0.57 mm inside the upper exterior roof. The native script separately requires an actual volume connection to its shell and zero interference with all imported manufacturer board bodies and the full 22 + 5 mm C-plug reference. Rejected rails are removed, with the reason recorded; no front bridge is restored.

The nearest nominal existing screw shaft is 12.600 mm from the notch bounding box. That is clearance evidence, not load-path, fatigue, printing or physical-strength acceptance. Board mounting, DFR relocation, the rest of the wiring and all-joint motion remain separate work.

Outputs after native execution:

- `shell_left-usb-u-notch.step` and `.f3d`
- `shell_right-usb-u-notch.step` and `.f3d`
- `body-usb-u-notch-with-board-references.f3d`
- `fusion-passage-receipt.json`, including original/cut/final volumes, rail decisions, old plug collision and final plug clearance, precise shell bounds contained within the original source bounds (material removal may reduce extrema), and exported-file hashes

Only the new cut and rail operations are native editable features. The inherited shell geometry is a faceted BRep converted from the exact source mesh, not recovered smooth analytical CAD or original feature history. The USB-C 7 mm receiving thickness and 1.2 mm mouth-to-mould gap remain explicit assumptions; the socket mouth centre itself is registered from the manufacturer source geometry.

The initial geometry succeeded for the left half, but an overly strict bounds equality and then an incorrect archive-export object type interrupted handoff. Both failed receipts and script versions are retained. The current script compares `preciseBoundingBox` with source STL vertices and passes a Component to the installed Fusion archive API; it resumes existing features rather than recreating them.

## Completed native result

The resumed Fusion execution now records `LOCAL_NATIVE_NOTCH_AND_PLUG_CHECK_PASSED`. Both halves are solid and remain within their original source bounds. The left cut removes 169.99385 mm³ and adds 70.98460 mm³ of internal rails; the right removes 112.76829 mm³ and adds 67.07357 mm³. Both halves have zero intersection with the seated USB-C mould and strain reference bodies. All four independent rails were retained after native attachment and reference-body checks.

The five STEP/F3D exports listed above were read back and matched their receipt hashes; `native-artifact-readback.json` binds this check to the final receipt, script and specification. These files are the completed local CAD revision, not a complete robot or printing release.
