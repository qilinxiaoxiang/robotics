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

## Files

- `addin/ClaudeBridge/`: the Fusion add-in. It listens on 127.0.0.1:8777 and runs posted Python on Fusion's main thread with `app`, `ui` and `adsk` defined. The installed copy is in `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/ClaudeBridge/`; check it with `diff -r addin/ClaudeBridge "<installed path>"`.
- `fusion.py`: `ls`, `rename`, `delete`, `delete-folder`, `import [--replace] [--check CMD]`, `export`, `image`, `run`. `fusion.sh` and `fx.sh` are entry points to it.
- `jobs/*.py`: bridge job templates. `folder.py` is the prelude that resolves `FUSION_PROJECT/FUSION_PATH` and refuses an empty path; `fusion.py` fills the `'@@KEY@@'` placeholders with `repr()`.
- `sch_lint.py`: checks format, display, geometry (wire ends, T-junctions, split segments, labels on their own wires, mirrored parts) and layout (frames and text collisions).
- `tests/run_tests.py FIXTURE_DIR`: runs sch_lint on a project-owned fixture set (good*.sch must pass; each mutations/m_<defect>.sch must fail with its named check). Fixtures stay in the project; the 18-021 set is in `~/Desktop/courses/18-021/.work/final/lint-fixtures`.
- `dialog_watch.sh` and `lib.sh`: dialog detection. Screenshots go to `$FUSION_SHOT_DIR` (default `$TMPDIR/fusion-shots`).

## Windows you will see

During an upload, Fusion shows two untitled AXDialog windows: Upload Options (640x314) and a full-window overlay (2056x1258). They are expected and close when the upload is confirmed. While the main thread is busy, System Events can briefly fail to read Fusion's windows. `fusion.py` retries for about 6 s; `dialog_watch.sh` prints "FUSION WINDOWS UNREADABLE" and then "readable again".
