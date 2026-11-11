# Fusion Electronics from code

Shared tools for building schematics in Autodesk Fusion Electronics by generating EAGLE `.sch` files and driving Fusion through a local bridge. First used for the 18-021 Logic Display Shield (2026-11-11). Skill: `fusion-electronics` (in `~/code/claude-config/skills/`).

## The route that works

1. Keep one netlist file as the source of truth, and write a generator that emits an EAGLE `.sch` (dialect 9.7.0). Copy the needed libraries from Fusion's managed cache: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/Electron/<id>/lbr/adsk.eagle_library_*/<Lib>.lbr`. A course `.flbr` file is a zip that holds an `.lbr`.
2. Run `python3 sch_lint.py FILE.sch`, plus your own project checks (netlist, logic). Fix every failure before uploading.
3. Set `FUSION_PROJECT` and `FUSION_PATH`, then run `sh fusion.sh import /abs/FILE.sch [--replace]`. The result is PASS only when no Fusion Error window appears and the design exists. With `--replace`, the old design is renamed aside and deleted only after the new one imports.
4. Look at the result with `sh fusion.sh image NAME OUT.png`. It renders the whole sheet off-screen and needs no window in front.
5. Export Fusion's own copy (`schematic.exportManager.createEagleSchExportOptions`) and run the same checks on it. This is the real acceptance check: it tests what Fusion stored, not what you sent.

Keep `sh dialog_watch.sh` running under a Monitor for the whole session. `fx.sh` refuses to run while a dialog is open and screenshots any call that hangs for more than 10 s.

## Import rules Fusion enforces (each one failed for real)

- **No `<atts>`, `<att_values>` or `<att_sets>` library blocks.** If any are present, Fusion reports that the file "has errors and cannot be opened". Strip them when you copy libraries.
- **Groups go under schematic-level `<groups>`, before `<parts>`.** A `<schematic_group>` inside a sheet's `<plain>` is dropped without any warning.
- **Instances are smashed on import.** Write explicit `<attribute name="NAME">` and `<attribute name="VALUE">` children with positions, or no designators or values will show.
- **Set layer 93 (Pins) to `visible="no"`.** Otherwise every pin gets a direction circle.
- **Round every coordinate** to the 0.0001 mm grid you write. A pin that misses its wire end by a float error is not connected.
- **Fusion draws each group frame around its members**, including label text and smashed NAME/VALUE text. Groups placed by hand overlap, so pack them from measured bounds (see `gen_sch.py` `pack()` in the 18-021 course).
- **Put labels R0 at the left end of a stub that is long enough for the text**, with the text baseline about 1 mm above the wire. An R180 label at the free end hangs outside its frame, and text sitting on the wire hides underscores.

## Fusion API facts

- **Do not use live `Electron.run ADD ...`.**
  - A bare `ADD` opens a modal picker that blocks the bridge.
  - `ADD name@lib` raised PlacePartWorker "assetAdded" assert dialogs.
  - `Electron.importSchAndBrd` crashed Fusion.
  - Upload the file with `DataFolder.uploadFile` instead. Every upload raises an untitled "Upload Options" dialog. `fusion.sh import` confirms it with Return; this is the one keypress that takes focus.
- **Delete a design's parent first.** An electronics design is a `.fprj` with a child `.fsch` (and `.fbrd`). `DataFile.deleteMe()` on the child raises `InternalValidationError : res` while the parent exists. Close the open documents, delete the `.fprj`, then the `.fsch`. `fusion.sh delete` and `delete-folder` do this in that order and confirm that nothing is left.
- **`DataFile.name` can be set.** Renaming is how `--replace` keeps the old design until the new one has passed.
- **`app.executeTextCommand("Electron.run EXPORT IMAGE '<png>' <dpi>;")`** renders the active schematic sheet to a PNG.
- **Seeing dialogs needs System Events.** `osascript ... get name of every window` reads them. The main window's title contains "Autodesk Fusion", and docked palettes have fixed names. `osascript click` is denied (no assistive access), but `key code` works once Fusion is frontmost.

## Files

- `addin/ClaudeBridge/`: the Fusion add-in. It listens on 127.0.0.1:8777 and runs posted Python on Fusion's main thread with `app`, `ui` and `adsk` defined. The installed copy is in `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/ClaudeBridge/`; check it with `diff -r addin/ClaudeBridge "<installed path>"`.
- `fx.sh`: the bridge client. Exit codes: 2 bare ADD, 3 a dialog was already open, 4 a dialog opened during the call, 5 the call ran longer than 10 s (screenshot saved).
- `fusion.sh`: `ls`, `rename`, `delete`, `delete-folder`, `import [--replace]`, `image`, `run`.
- `jobs/*.py`: bridge job templates. `folder.py` is the prelude that resolves `FUSION_PROJECT/FUSION_PATH`; `job.py` fills `'@@KEY@@'` placeholders with `repr()`.
- `sch_lint.py`: checks format, display, geometry and layout (frames and text collisions).
- `dialog_watch.sh` and `lib.sh`: dialog detection. Screenshots go to `$FUSION_SHOT_DIR` (default `$TMPDIR/fusion-shots`).

## Known gap

Something Fusion shows briefly, an untitled window that lasts under 2 s, appears on data-changing calls. It has never been a modal: every one cleared by itself, and no screenshot showed a dialog. `fusion_dialog_names` now records each window's subrole and size, so the next one can be identified. Until then, treat an untitled window that stays longer than 4 s as a real dialog.
