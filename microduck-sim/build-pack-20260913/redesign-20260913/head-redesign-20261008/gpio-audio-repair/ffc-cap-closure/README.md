# Complete FFC / populated-cap closure preparation

No print or native slicer work. No candidate FFC has been checked or accepted here yet.

`moving-inventory.json` contains all seven cap-owned groups: corrected cap,142 independently closed conservative OpenRB component enclosures, amplifier, speaker, cradle, keeper, and cap hardware. This is148moving entities ×161translations (`[0,0,40]` through `[0,0,0]` every0.25mm),23828entity samples. All142OpenRB components are retained, not a selected clear subset. The142enclosures jointly contain every source triangle and are conservative collision obstacles.

`prepare_inventory.py` is stdlib-only. It reads current geometry and root's43existing-obstacle receipts, records their hashes, and records the corrected-cap strict-subset proof. Those historical receipts are referenced only; changed Pi or other poses do not silently inherit them. This checker adds only the complete fixed FFC obstacle.

## Frozen FFC contract

Owner supplies `input-contract.json` after its complete200mm cable has passed its topology/self/static checks. Required fields:

- `frozen: true`, `completePath: true`, `lengthMm: 200`
- `mesh`: absolute worldSTL path, `meshSha256`: its exact hash
- `evidenceClaims`: keys `completePath`, `lengthMm`, `selfAccepted`, `staticAccepted`, `meshSha256`. Each is `{file, sha256, jsonPointer}` pointing to the actual source-bound route/self/static report value. Expected values are respectivelytrue,200,true,true,the exact meshSHA. JSONpointers use `/field/subfield` syntax.

A candidate/partial route or receipt with nonzero failures cannot satisfy this contract. Hashes alone are not treated as acceptance. Mapping existing report fields into this contract is bookkeeping; do not invent a passed receipt.

## Execution

`run_pairs.py --contract /absolute/input-contract.json --output /absolute/run-directory --jobs 2`

The runner dispatches only through `run_bounded_cad.py`:512MiB/120s per pair, two local light workers, global four-light-slot guard respected. It first verifies the fixed FFC is closed/positive/winding-consistent and valid Mesh64. Every pair then loads only that moving mesh and the FFC. Every translated mesh/intersection is discarded immediately. No transformed scene cache or all-pose scene is loaded.

Every pair writes incremental checkpoints, including all161sample rows in its completed receipt. Zero overlap certified by disjoint bounding boxes is recorded as such. Exact Boolean intersections are computed for all remaining poses. A failed/timeout/lock-rejected/incomplete/stale receipt cannot pass summary. Reuse requires exact current input/source/script hashes.

No final-contact waiver is allowed. Numerical volume tolerance is1e-7mm³. This is a0.25mm-sampled closure check, not an independent proof of continuous clearance between samples or physical tolerances. Root owns whole-head acceptance.
