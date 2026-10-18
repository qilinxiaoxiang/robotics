# Curved head restoration — P5 / P6

The current review candidate is `curved-cap-final-candidate-world.stl`. All exported meshes use **world millimetres** and must be placed with an identity transform. `viewer-fragment.json` is the integration interface; only `integrationReady: true` permits using its files. `curved-head-review.json` is the current source-bound receipt. Intermediate spatial or mount reports are not final acceptance.

The shell starts from the actual community `top_head_shell.stl`, transformed using the robot kinematic source. It is not reconstructed from a bounding box. Local edits are the two USB receiving/service openings, the bottom mating-seam relief, and inward mounting bosses. The original curved roof is preserved; no squared enclosure or enlarged outer envelope is added. The exact source, additions and removals remain separate files.

The populated Zero W receiving space includes components, the soldered 40-pin header, mating housing and solder tails. These overlapping buffers describe **one board assembly**, and are unioned in `zero-w-populated-receiving-union-world.stl`. They are not a claim that the borrowed board or plug dimensions have been measured. Pi 3 Model B V1.2 at the old Zero pose fails; this directory does not claim a Pi 3 head fit. Pi 3 remains the bench option.

## Assembly constraints retained by executable checks

1. With the cap detached, load the four M2 nuts through the side windows. Rear nuts enter from positive local X.
2. Seat and fasten OpenRB before audio. Four M2 × 6 machine screws replace the old square-shell M2 × 18 stack. Tightening after the speaker is present is an explicit failing regression.
3. Fasten the prewired amplifier, then install the speaker rear keeper, speaker and lower cradle. Four M2.5 × 8 tapping screws provide the defined audio retention. These dimensions specify candidate hardware; they do not assert inventory or authorize procurement.
4. The populated rigid cap descends 40 mm along world −Z. The scan includes all retained source parts, neck interfaces, camera retention and the populated Zero receiving space.
5. For the three shell screws, hold the jaw and lower pad 30° open and install the upper pad afterwards. Closed-jaw tool blockage remains an explicit negative control.
6. Plug USB-C into OpenRB after closing the cap. The independent `../usb-access/usb-report.json` checks this axial local insertion. It does not validate the complete external cable.

The driver requirement is a 3 mm diameter, 45 mm long clear shaft; this is a modeled access requirement, not a claim that a particular tool is owned. STL precision simplification is bounded at 0.00003 mm per repair pass; the exported STL is reloaded and required to be watertight and a single connected body before path checks.

## Reproduction

Run these with `/tmp/microduck-cad-venv/bin/python`, from this directory:

```sh
python board_envelopes.py
python amp_model.py
python build_curved_layout.py
python build_mounts_and_paths.py
python build_audio_mounts.py
python finalize_cap.py
python verify_mount_access.py
python check_cap_fasteners.py
python deliver_review.py
```

The first two commands regenerate source-based receiving models; the next commands build the candidate. Camera-retainer and USB-access inputs must exist and remain unchanged during verification. `deliver_review.py` rejects changes to meshes used by the final path receipt. The independent parent integration check must also pass before publishing the review.

The amplifier uses the official Adafruit 3006 STEP and Eagle footprint plus an explicitly unmeasured terminal-block receiving allowance. The speaker uses the SameSky CMS-30204-18SP manufacturer's dimensioned capsule/frame/magnet geometry and dimensional tolerance. Primary source URLs and downloaded-source hashes are in `amp-model-evidence.json`, `board-envelope-review.json`, and `sources/`; supplier dimensions do not establish physical fit of the received parts.

## Remaining acceptance

This is a rigid mechanical review candidate. Full camera ribbon routing and its closure movement belong to `../camera-retainer/cabling/`. Complete SC0727 + 4472 USB cable routing/strain relief, actual connector and borrowed-board measurements, print fit, tapping torque, boss strength, acoustic performance and live electrical commissioning remain separate gates. A digital rigid-path pass does not close these items or the robot's visual-pickup objective.
