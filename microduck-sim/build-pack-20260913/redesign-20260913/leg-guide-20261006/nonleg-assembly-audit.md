# Non-leg assembly access review

Checked 2026-10-08. Problems P5 and P6. The acceptance question is whether a builder can reach each fastener and connector in the stated order, without passing real solids through each other. A final CAD pose and a complete screw inventory do not answer that question.

## Reproduced access failures and sequence repairs

- The right torso shell obstructs the ID12 rear-center driver only 3.4 mm beyond its screw head. Keep both torso shells off until the neck cases and rear centers are complete; then fit the shells from their respective open sides. The torso's six base/support screws and two shell screws now occur at different stages.
- ID11 obstructs all four head-yaw output screw paths 6.29 mm beyond their heads. Fasten ID13 to the detached pitch bracket before joining that bracket to ID11.
- ID13 obstructs all four head-roll output screw paths 4.5 mm beyond their heads. Complete the roll motor/fork on the bench before inserting ID13. The fork itself still obstructs a long straight driver at 24.5 mm. A specified right-angle working envelope fits: Ø3 mm bit from 2–18 mm ahead of the screw head, Ø6 mm transverse handle centered 17 mm ahead, exiting sideways. Actual tool availability, tip shape and grip remain unverified; the guide exposes this requirement before the operation.
- The installed jaw support and jaw motor obstruct two Pi screwdriver corridors, starting 27.21 and 16.71 mm from their respective heads. Mount and connect the Pi on the detached face panel before fitting that panel into the head.
- The seated lower head/motors obstruct access beneath OpenRB. The cap is a real detached bench assembly during controller, audio and camera mounting. This is reflected in both the instructions and visible part set.
- The closed jaw and both lip pads obstruct the two front cap-closure screws. The revised head sequence installs the moving jaw and lower pad while their entry remains open, then holds that assembly at +30° about the jaw axis during cap fastening. The fixed upper pad stays off until all three cap screws are complete. The tool verifier applies that exact rotation to the actual jaw/pad solids and retains the closed-jaw obstruction as a negative regression.

`verify_nonleg_access.py` independently imports the actual mesh payloads into Manifold and checks each non-leg fastener's working tool envelope. It includes all previously introduced physical parts except explicitly declared detached bench stations; it does not infer the physical obstacle set from the viewer's smaller visual context. The original trapped-tool cases are replayed as negative regression checks. A passing result does not validate a real screwdriver or compensate for a failed part fit.

## Insertion repairs

`nonleg-subassembly-paths.py` records 121 samples at 0.5 mm spacing for each of six investigated source-based bench motions. These bounded component tests support the repair; the integrated motion verifier checks the final guide sequence:

1. Place the near head-roll ring into the empty fork from −X before fitting the roll motor.
2. Bring the roll motor from −X through the already seated rings.
3. Fit ID15 into its detached support from +Y.
4. Place the amplifier from +Z onto its detached carrier.
5. Place the speaker from +Z onto that carrier.
6. Bring the complete carrier/amplifier/speaker group from −Z into the detached cap.

All six have zero measured material overlap along the sampled paths. Independent source geometry hashes and transforms are retained in `nonleg-subassembly-paths.json`. These are finite samples rather than continuous proofs.

## Head-shell fit remains conditional

The source lower shell has genuine final interference with both motors and both roll rings: approximately 15.91 mm³ at ID14, 15.96 mm³ at ID15, and 5.893 mm³ at each ring. Its support also has a 0.107 mm³ nominal intersection. These are retained as explicit fit evidence; the animation must not silently certify that source pose.

`head-shell-fit-check.py` derives every physical part introduced before the shell operation, including the already fitted jaw and lower pad. A −60 mm starting offset collides with both torso shells. The revised preview starts at −40 mm and stops at −20.225281 mm, before the assembled jaw blocks the shell near −19.725220 mm. All 81 displayed-path samples have zero material intersection; the smallest modeled endpoint gap is approximately 0.466 mm. The complete closing maneuver remains unresolved, and all nominal source seat conflicts remain recorded. Do not use the support screws to pull a resistant shell into place.

## Cabling gates

The sequence now connects the IMU before fitting its cover; loads and labels fuse leads before fixing the carrier; connects Pi GPIO and camera ribbon on the detached face; populates audio before its carrier enters the cap; and passes the free camera connector through the opening before latching it. The final disconnected inspection precedes closure, and the later hand-operated joint sweep checks the real service loops.

These are access/order repairs. Existing schematic wire curves are not measured flexible-cable trajectories or proof that a real connector body passes a particular aperture. Actual connector openings, exact borrowed board, wire bend radii, slack and moving-joint clearance require physical readback. No hardware was powered or moved by these checks.

## Recompute

Run with the project's CAD Python environment:

```sh
python verify_nonleg_access.py
python nonleg-subassembly-paths.py
python head-shell-fit-check.py
```

Rerun `verify_nonleg_access.py` after rebuilding the guide data, because its output binds the complete data hash. The other two reports bind each participating mesh payload and transform. Root integration separately checks the displayed operation paths and live browser page.
