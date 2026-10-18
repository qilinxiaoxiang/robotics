# C layout: native CAD review

9 October 2026. Problems P0, P5, P6. C selected by the user, A rejected; B only if a demonstrated mechanical/access advantage appears.

Open `MicroDuck-C-native-review.f3d` in Fusion. It contains the current 166 named mesh references, ten new parametric extrusion solids, and the hidden original battery envelope. `native-readback.json` binds the saved archive and confirms that it reopens with the expected geometry counts and 80.9 × 26 × 65.9 mm battery dimensions. New frame features are editable; the imported unchanged meshes are not exact BREP solids. Geometry uses millimetres externally and centimetres internally in Fusion.

The blue bank is 8 mm below the earlier C concept. Both ends are open. Each intact leg is translated 11 mm outward. The tan nine-piece skeleton is a structural route, not a complete printable bracket. Existing intersecting central references are hidden, preserved in the document. Remaining lower hip seats, neck bearing profiles, battery retention, electronics supports, fastener stacks, reachable motion and physical fit are listed in the receipt. The rear controller reference has no newly accepted attachment.

## Source and checks

- Current coordinate source and immutable mesh snapshots: `../central-cad/README.md` and `fusion-import-manifest.json`.
- Primitive source: `../central-cad/central-bridge-primitives.json`; static selected-pair check: `central-bridge-static.json`.
- Socket and left-knee access: `../leg-ports/README.md`.
- Port-face evidence: `../port-orientation/README.md`.
- The legacy project design verifier also passed on 9 October. Its baseline checks do not qualify this new skeleton, pending assembly tutorial, or physical commissioning.

## Repeatable Fusion execution

`import_current.py` imports the source-bound mesh reference. `update_native_skeleton.py` updates the active current-duck document and exports the candidate. `readback_native.py` reopens and checks the archive. Do not rerun the update on a document already containing `C lowered8`.

Use Fusion's registered Scripts and Add-ins entry or its built-in text console. During this run, the macOS accessibility radio buttons changed their reported state without switching the command interpreter. Stop retrying that UI path. The built-in `Python /?` help confirmed `Python.Run`; `Python.Run "/absolute/path/script.py"` worked in text-command mode. An absolute path must be quoted, otherwise its leading slash is parsed as an option. A standalone launcher must call `run(None)` after defining it. This route remains inside Fusion's API and saves a status receipt; a clicked Run button alone is not success evidence.

The three prior imports and original wrong-reference document were closed after the successful readback. Only the reviewed assembly remains open. Heavy source geometry checks use bounded workers; import and update each completed in approximately 15 and 11 seconds respectively.

## Delivery boundary

Native files stay local. The Mac mini `DESIGN-REVIEW.html` contains the actual Fusion screenshot and stage conclusions. It does not publish this archive or add manufacturing files. The V1.4 print archive remains unchanged.
