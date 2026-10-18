# White/Yellow native print decision review

Use `White_first_layer_028_editable.3mf` and its native output `native-028/White_028.gcode.3mf` for White. This changes only `initial_layer_print_height` from0.2 to0.28mm. ZIP-level comparison confirms every other member, including all source triangles and build transforms, is byte-identical. No geometry was clipped, flattened, or moved into the bed.

The original White native result is preserved in `baseline-White-rejected.gcode.3mf`. It prints only2.9333mm² atZ0.2, with no support/brim, then3075.2156mm² atZ0.4. Source face exterior has a3071.5204mm² flat face atX81.399002, already exactly facing down, but a small existing feature extends0.126350mm beyond it. At0.2 first-layer height the slicing mid-plane0.1 misses the broad face. A0.28 first layer catches that face and produces3022.4550mm² of contiguous model bed contact; second-layer area is3071.2406mm². No-brim is retained.

White native toolpaths leave all three camera clamp pilots and all three active Pi mounting pilots free of support, both at their cores and the conservatively enlarged bead edge. Native thumbnail was inspected with all bores and the camera opening visible.

Keep the existing Yellow native slice. First-layer model area1065.6332mm² and support area5060.7213mm² are separate measurements. Four motor-support pilots, three cap-through bores, and both head-roll seats have no support core or edge contacts in the actual native toolpath check. No local support blocker or new orientation is justified by this check. The open shell thumbnail was inspected.

All physical material coordinates include the configured Bambu nozzle offset[0,2]mm. Native G1/G2/G3 moves are streamed; only first two layers are retained for buffered-bead unions. These checks are about print preparation, not physical adhesion, support removal or whole-robot acceptance.

Reports: `review-summary.json`, `White028-stream.json`, `White028-features.json`, `Yellow-stream.json`, `Yellow-features.json`, `planar-faces.json`. Executable audit entrypoints are `audit_stream.py` and `check_features.py`; use the shared bounded CAD launcher. Each stream job used under60MiB; native White slicing used139MiB.
