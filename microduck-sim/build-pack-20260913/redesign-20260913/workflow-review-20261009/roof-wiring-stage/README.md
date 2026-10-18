# Restored crown and wiring trial

This stage answers the user's request to close an unnecessary crown opening and put cables into the CAD assembly. It advances P0/P5/P6. It is an intermediate review with retained routing failures, not a full assembly or print release.

The crown is repaired by reconstructing the original curved material. Its internal mounts and rear USB service aperture are preserved. The added patch clears the current 160 other component references at the closed pose. The adopted CAD configuration connects the Mac directly to OpenRB at the rear; Pi USB remains empty, and Pi sensor/audio connections remain. The old combined Pi runtime has not been migrated. See `CONNECTION-DECISION.md`.

Open `fusion/MicroDuck-roof-and-wiring-stage.f3d` in Fusion. Named components separate the body references, head wires, and motor harness. `fusion/fusion-receipt.json` records source-bound placement and reopening. `fusion/model-inputs/` freezes the exact wires used in that export; later worker changes cannot silently alter a saved review. Imported mesh bodies remain mesh references, not recovered original parametric solids.

Review the head closed, then with the cap hidden, then the full harness. Failed motor routes are red. `motor-wires/stage-summary.json` lists the exact obstacles. Four of fifteen motor routes clear the checked neutral pose: 11→12,12→5,3→2,7→8. Eleven retain interference. The two knee bridges and neck-to-leg route were corrected without changing shells or reducing wire diameter. A static empty intersection is not motion, spare-length or insertion acceptance.

`head-wires/` contains the camera ribbon, speaker, USB, I2S, paired power/return and IMU lines with endpoint provenance. The Pi pins and OpenRB sockets are registered. Proposed board-envelope terminations are labelled and must not be used as authoritative assembly pinout instructions.

Next work is local, in this order:

1. Repair remaining head motor/speaker/cap conflicts and head signal-to-ribbon conflicts, preserving the original head exterior.
2. Correct power/IMU routes around existing structures and register remaining board pads; complete the revised power-injection and current contract.
3. Repair the remaining leg and hip paths. Keep the demonstrated cable-before-cover insertion order and model actual spare cable length.
4. Check reachable joint motion, retention, closure and installation. Keep negative traces and bind new checks to changed source hashes.
5. Only after the relevant stage passes, produce incremental print files and rebuild the accepted assembly instructions.

`design-verifier.log` is the existing design baseline verifier run for this handoff. Its successful exit does not certify this new harness or close physical commissioning. Native and route-specific receipts own this stage's actual evidence.

The live review is served by the existing Mac mini `DESIGN-REVIEW.html`. F3D/STL/print outputs remain local. The previously released print archive is unchanged.

AI assistance was used to draft.
