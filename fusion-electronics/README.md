# Fusion Electronics from code

Shared tools for building schematics in Autodesk Fusion Electronics by generating EAGLE `.sch` files and driving Fusion through a local bridge. First used for the 18-021 Logic Display Shield (2026-11-11). Skill: `fusion-electronics` (in `~/code/claude-config/skills/`).

## The route that works

1. Keep one netlist file as the source of truth, and write a generator that emits an EAGLE `.sch` (dialect 9.7.0). Copy the needed libraries from Fusion's managed cache: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/Electron/<id>/lbr/adsk.eagle_library_*/<Lib>.lbr`. A course `.flbr` file is a zip that holds an `.lbr`.
2. Run `python3 sch_lint.py FILE.sch`, plus your own project checks (netlist, logic). Fix every failure before uploading.
3. Set `FUSION_PROJECT`, `FUSION_PATH` (non-empty) and optionally `FUSION_CHECK` (your project check; `{}` is the file), then run `python3 fusion.py import /abs/FILE.sch [--replace]`. PASS means all of these held:
   - Fusion showed no Error window.
   - A new `.fsch` id appeared and stayed for 5 s with no dialog.
   - Fusion's own exported copy passed `sch_lint.py` and `FUSION_CHECK`. This tests what Fusion stored, not what you sent.
   With `--replace`, the old design is renamed aside and deleted only after that acceptance. Every failure moves the new design aside as `NAME__failed_*`, restores the old one, and says so (or says loudly that it could not).
4. Look at the result with `python3 fusion.py image NAME OUT.png`. It renders the whole sheet off-screen and needs no window in front.
5. Tested on 2026-11-11 in a scratch folder:
   - Fresh import: PASS.
   - Good replace: PASS, old design deleted.
   - Bad replace: FAIL on the stored copy; old design restored, bad one moved aside.
   - Folder delete: done.
   Run `python3 tests/run_tests.py <fixture dir>` after any change to `sch_lint.py`.

Keep `sh dialog_watch.sh` running under a Monitor for the whole session. `fx.sh FILE.py` (= `fusion.py run`) sends any bridge code. It exits non-zero in each of these cases:
- Fusion raised an exception.
- A dialog was open before the call or appeared after it.
- The call ran longer than 10 s (screenshot saved).
- Fusion's windows cannot be read.
- The file has a bare ADD.

## Import rules Fusion enforces (each one failed for real)

- **No `<atts>`, `<att_values>` or `<att_sets>` library blocks.** If any are present, Fusion reports that the file "has errors and cannot be opened". Strip them when you copy libraries.
- **Groups go under schematic-level `<groups>`, before `<parts>`.** A `<schematic_group>` inside a sheet's `<plain>` is dropped without any warning.
- **Instances are smashed on import.** Write explicit `<attribute name="NAME">` and `<attribute name="VALUE">` children with positions, or no designators or values will show.
- **Set layer 93 (Pins) to `visible="no"`.** Otherwise every pin gets a direction circle.
- **Round every coordinate** to the 0.0001 mm grid you write. A pin that misses its wire end by a float error is not connected.
- **Fusion draws each group frame around its members**, including label text and smashed NAME/VALUE text. Groups placed by hand overlap, so pack them from measured bounds (see `gen_sch.py` `pack()` in the 18-021 course).
- **Put labels R0 at the left end of a stub that is long enough for the text**, with the text baseline about 1 mm above the wire. An R180 label at the free end hangs outside its frame, and text sitting on the wire hides underscores.

## Fusion API facts

- **`DataFolder.uploadFile` blocks Fusion's main thread** until its Upload Options dialog is answered. Every other bridge call waits behind it. `fusion.py import` runs the upload in a thread and confirms the dialog from outside.
- **The bridge always answers HTTP 200.** A Python exception in Fusion only shows as `"ok": false` in the JSON, and `fusion.py` turns it into a failure. Never judge a call by curl's exit code.
- **Do not use live `Electron.run ADD ...`.**
  - A bare `ADD` opens a modal picker that blocks the bridge.
  - `ADD name@lib` raised PlacePartWorker "assetAdded" assert dialogs.
  - `Electron.importSchAndBrd` crashed Fusion.
  - Upload the file with `DataFolder.uploadFile` instead. Every upload raises an untitled "Upload Options" dialog. `fusion.py import` confirms it with Return. That keypress, plus Return on the Error report of its own upload and Escape to cancel its own dialog on failure, are the only keys sent to Fusion.
- **Delete a design's parent first.** An electronics design is a `.fprj` with a child `.fsch` (and `.fbrd`). `DataFile.deleteMe()` on the child raises `InternalValidationError : res` while the parent exists. Close the open documents, delete the `.fprj`, then the `.fsch`. `fusion.py delete` and `delete-folder` do this (electronics files only; a folder with subfolders or other files is refused) in that order and confirm that nothing is left.
- **`DataFile.name` can be set.** Renaming is how `--replace` keeps the old design until the new one has passed.
- **`app.executeTextCommand("Electron.run EXPORT IMAGE '<png>' <dpi>;")`** renders the active schematic sheet to a PNG.
- **Seeing dialogs needs System Events.** `osascript ... get name of every window` reads them. The main window's title contains "Autodesk Fusion", and docked palettes have fixed names. `osascript click` is denied (no assistive access), but `key code` works once Fusion is frontmost.

## Boards: schematic to routed PCB (proven 2026-11-12, 18-021 shield)

Route that works, all through `fusion.py run` jobs on the live board (no `.brd` upload):
1. Activate the saved schematic and run `Electron.run BOARD`. Fusion opens a new unsaved BoardDocument linked to it with a default 160 x 100 mm outline.
2. Generate placement and routes in code (outline, holes, element MOVE/ROTATE, then wires and vias per net) as EAGLE command lines, and replay them one net at a time with a dialog check after each.
3. Accept with Fusion's own connectivity: `RATSNEST`, then `RUN ulp/airwires.ulp OUT.txt`. Require `TOTAL 0` and copper only on Top (1) and Bottom (304). Then export the `.brd` and compare geometry with the plan.
4. Save: `board.saveAs(name, parentDesign.dataFile.parentFolder, msg, '')` and `parentDesign.save(msg)`. Close and reopen the board (`close(False)`, then `BOARD` on the schematic) and rerun step 3 on the stored copy.
5. 3D: `commandDefinitions.itemById('Switch3dPcbDocCmd').execute()` on the board, then `saveAs` the new FusionDocument into the same folder. `app.activeViewport.saveAsImageFile(path, w, h)` renders it without bringing Fusion forward.

Traps, each seen for real:
- **Layer 16 is the inner layer `Route16`.** Bottom copper is layer 304 `Bottom`. `LAYER 16` puts wires and pours on an unconnected inner layer, every via and through-hole pad then carries a zero-length airwire (a yellow X), and the exported `.brd` still writes them as layer 16. Always write `LAYER Top` / `LAYER Bottom` by name. To repair: `DISPLAY NONE Route16; GROUP ALL; CHANGE LAYER Bottom (>1 1); DISPLAY ALL`.
- **The exported `.brd` cannot prove connectivity.** It omits zero-length airwires and maps Route16 to 16. Only the ULP (or the Inspector's Airwires count) shows them.
- `SET OBSTACLE_MODE IGNORE` before any WIRE. The default walkaround reshapes wires and raises pusher.cpp "inLocator" assert dialogs.
- `SET OPTIMIZING OFF` (else collinear segments merge and endpoint junctions turn into mid-segment touches), `SET WIRE_BEND 2` (straight segments), `GRID MM 0.001` (else HOLE and MOVE snap).
- Wires connect only at endpoints. Never end a WIRE on a point where two segments of that layer already meet, or mid-segment; draw a branch starting at the junction. Never branch at a via.
- `RIPUP;` (all) opens an UNROUTE confirmation dialog. `RIPUP net1 net2` has none but only rips copper reachable from pads on visible layers.
- Use the board's signal names (read them from an exported `.brd`): a supply symbol may name its net `+3.3V`, not `+3V3`. A wrong name silently creates a floating signal.
- `AUTO` (autorouter) does nothing through the bridge, and `AUTO LOAD` resets its parameters. `DISPLAY 16` does nothing; use layer names.
- In ULPs, iterating `S.polygons(P)` aborts the ULP silently; check pour layers through `B.layers(L)` `L.used` instead.
- Stray keypresses moved elements once; after any unexplained change, discard the unsaved board and rebuild from the schematic rather than patching.
- `RATSNEST` shows a small untitled "Info / N airwires" toast (320 x 61), only while Fusion is frontmost. The 3D workspace shows untitled browser palettes (300 x 868, 300 x 25). Neither is modal; `fusion.py` ignores the Info toast.
- Assert dialogs (420 x 265) ignore keys sent by osascript. A Quartz mouse click on OK at window x+248, y+232 closes them.
- Screenshots: capture Fusion by window id (`screencapture -l <id>`, id from `CGWindowListCopyWindowInfo`). The user has two displays and a whole-screen or rectangle capture shows whatever window is on top.

## Files

- `addin/ClaudeBridge/`: the Fusion add-in. It listens on 127.0.0.1:8777 and runs posted Python on Fusion's main thread with `app`, `ui` and `adsk` defined. The installed copy is in `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/ClaudeBridge/`; check it with `diff -r addin/ClaudeBridge "<installed path>"`.
- `fusion.py`: `ls`, `rename`, `delete`, `delete-folder`, `import [--replace] [--check CMD]`, `export`, `image`, `run`, `airwires` (foreground only: reads the RATSNEST toast).
- `ulp/airwires.ulp OUT`: writes every airwire (zero-length ones too), each wire's layer, via spans and used layers, ending with `TOTAL n ZERO m`. Run it with `Electron.run RUN "<ulp>" "<out>";` after RATSNEST. `fusion.sh` and `fx.sh` are entry points to it.
- `jobs/*.py`: bridge job templates. `folder.py` is the prelude that resolves `FUSION_PROJECT/FUSION_PATH` and refuses an empty path; `fusion.py` fills the `'@@KEY@@'` placeholders with `repr()`.
- `sch_lint.py`: checks format, display, geometry (wire ends, T-junctions, split segments, labels on their own wires, mirrored parts) and layout (frames and text collisions).
- `tests/run_tests.py FIXTURE_DIR`: runs sch_lint on a project-owned fixture set (good*.sch must pass; each mutations/m_<defect>.sch must fail with its named check). Fixtures stay in the project; the 18-021 set is in `~/Desktop/courses/18-021/.work/final/lint-fixtures`.
- `dialog_watch.sh` and `lib.sh`: dialog detection. Screenshots go to `$FUSION_SHOT_DIR` (default `$TMPDIR/fusion-shots`).

## Windows you will see

During an upload, Fusion shows two untitled AXDialog windows: Upload Options (640x314) and a full-window overlay (2056x1258). They are expected and close when the upload is confirmed. While the main thread is busy, System Events can briefly fail to read Fusion's windows. `fusion.py` retries for about 6 s; `dialog_watch.sh` prints "FUSION WINDOWS UNREADABLE" and then "readable again".
