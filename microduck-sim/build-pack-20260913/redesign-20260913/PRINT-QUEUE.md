# Current 89-instance print queue

2026-09-26: All original six plates have now been sliced with Bambu Studio. The six native SD-card files are in [printing-20260926/SD-CARD](printing-20260926/SD-CARD/); see [printing instructions](printing-20260926/README.md). All 89 instances retain their original placement. The editable source below remains unchanged.

Open `current-print-queue.3mf` in Bambu Studio. It is an editable project containing all 89 embedded model instances arranged on six plates, with no machine G-code inside. The matching exact source list is `print-manifest.json`.

The revision preserves the previous 85 print-stock instances, replaces the old head cap with the new USB-service-window cap, and adds the regulator insert, camera tilt foot, camera cradle and audio carrier. It contains no voltage-alarm carrier. The idler/cap counts remain spare-stock allowances rather than instructions to install every copy.

The embedded recipe is X1 Carbon, 0.4 mm nozzle, Cool Plate, Bambu PLA Basic, 0.2 mm layers, four walls, 30% gyroid infill and automatic tree support. Before using the sliced exports, match the actual RoboClub printer, nozzle, material and bed. If they differ, update the project profile and slice again. This project does not claim a reserved printer or completed physical print.

Fresh inspection of the actual 3MF archive verified:

- 89 unique model instances assigned to six plates: 10, 7, 13, 13, 18 and 28 instances.
- Every new/replacement part embedded exactly once; old head cap and alarm absent.
- Embedded mesh footprints within the 256 × 256 mm bed and clear of the excluded corner.
- At least 24.0 mm nominal bed-edge margin and at least 23.98 mm between conservative part footprints.
- Maximum part height 96.93 mm, below the 250 mm profile limit.
- Source hashes and embedded process settings match the manifest and selected recipe.
- Zero machine G-code files in the archive.

These are model placement checks. The 2026-09-26 exports also include sliced supports and machine instructions for the profile above; all six native slicing runs completed without warnings. The installed club hardware and completed print fit still require physical checks.

The new head cap provides a single MicroB data-plug service window for the GPIO-powered Pi. The accepted external plug envelope remains **25 × 18 × 8 mm**. SC0727's published dimensions omit the full moulding, so measure the received plug before final closure. No Pi relocation is silently included in this queue.

Files for reproduction and verification:

- `build_print_queue.py` builds the manifest and calls installed Bambu Studio to arrange/export the editable project.
- `verify_print_queue.py` reads embedded vertices, plate assignments and presets from the exported archive; it requires the CAD runtime plus Shapely 2.1.2.
- `print-queue-verification.json` records the fresh artifact hash, plate measurements and passed checks.

The CAD runtime used here is `/tmp/microduck-cad-venv/bin/python`. Source STL files and the inherited profiles retain their original locations; all new queue outputs are confined to this redesign directory. The design uses the FIT0586 XT30 connector and a 2 m 18 AWG high-voltage power lead; neither is an additional printed object.

The electrical harness is not a printed object: use four 250 mm 22 AWG Pi leads, four 250 mm IMU leads, eight 250 mm 20 AWG motor feeds and the original motor tails. The GPIO housing plus exits must fit 7 × 52 × 15 mm; the current Pi mounting remains in place. DATA follows the physical order in `mechanical-review.md`, with the ID1-to-ID6 link extended to 400 mm and routed up/across/down the legs and torso. All lengths have fresh 1,500-pose reach checks; assembly still verifies flexible routes and bus communication.


## Head-cap revision, 2026-09-26

The missing third cap mounting boss is restored. All six native SD exports were regenerated from the corrected source and passed `printing-20260926/verify_sliced_handoff.py`. Plate1 is now approximately5h50m; all six total17h18m and384.71g. Use only the six files under `printing-20260926/SD-CARD/`. Layout remains89instances on the same6plates.
