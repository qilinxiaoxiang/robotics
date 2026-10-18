# Compact neutral — isolated stages only

The former all-scene entry was replaced. Do not use `check_routes` or the earlier `check_single_circle_candidate.py` / `check_segmented_candidate.py` to validate this compact revision: those historical diagnostics retain full-scene loading.

Root owns the sole CAD token. Run each stage separately through `H/run_bounded_cad.py`, with `--max-mib 512 --seconds 120` and a distinct resource report. The command after `--` is `/tmp/microduck-cad-venv/bin/python D/check_compact_neutral.py STAGE`; H is the absolute head-redesign directory and D is its `cabling-release-20261008/neck-repair` directory.

Order:

1. `plan --amp-manifest /absolute/path/to/current-audio-overlay.json`: stream-hash source data, read the complete 103-part source-cache index, apply only the canonical viewer's explicit replacements/removals/additions, and pin every input. The method agent’s `camera-ribbon-repair/local-candidate-manifest.json` is mandatory, as is an explicit current amplifier overlay. No fallback to the old amplifier. No geometry library imports.
2. `geometry`: generate only the candidate centerline and segment metadata. No scene, mesh library or Manifold imports.
3. `self`: separately check the receiving path for nonlocal self-crossing. It imports only NumPy/SciPy, queries one point neighborhood at a time, saves `compact-isolated/self-check.json`, and returns nonzero on crossing. Stop here on failure.
4. `mesh`: requires the matching successful self-check; produces the sole receiving mesh. Still loads no obstacle.
5. `obstacle --key PART`: each invocation is a fresh short process, loading exactly one obstacle from the pinned cache JSON or canonical replacement/additional STL. It refuses stale plan, path or self-check inputs. Results are independent `compact-isolated/pairs/PART.json` files. Do not combine multiple obstacles in one worker.

AABB-disjoint obstacles are recorded as clear without constructing a Manifold. Other pairs construct only the cable and that one obstacle. Cap portal contacts are reported; no contact is silently waived. The candidate is not accepted merely because a subset of pairs has passed.

`isolated-worker-static-review.json` records syntax/import/schema inspection. This file describes the execution contract. Revision 2 plan, geometry and self stages have now run under the guard; the self stage failed and stopped before mesh generation or obstacle loading. Their separate resource receipts preserve measured runtime and memory.

6. `summary`: verify every expected neutral obstacle key has a current plan/mesh/obstacle-bound receipt. Missing, stale, failed or skipped work cannot report the scene clear. Even a complete neutral pass never closes the whole harness. Six stdlib-only negative/positive coverage tests are in `test_compact_coverage.py`.

Revision2 changes only the fixed torso entry: inputY−66, frontsideR14turnaroundX38…52, then−Xapproach andR10upturn to the unchanged neck anchor. The firstY−58offset was also rejected and recorded. The originally reported entry/neckbridge pair now has minimum centerline separation10.90388mm (3.90388mm receiving surface gap), computed with exactpolyline segment distances in stdlib. This is not the fullselfcheck; the old first20reportedpairs were a truncated failure sample. Original rootreceipts remain in `compact-isolated-v1-self-failed/`. Regenerateplan/geometry/self after authorization.

Revision 3 repairs the next reported pair, yaw-to-roll bridge versus the upward head-entry strand. Only the first fixed head-entry quarter-arc grows from R16 to R24; its Y coordinate and head portal move from 16 to 24 mm, near the prior internal channel at Y23.2. The following straight shortens by 8 mm. Total constant path length is now 856.997760 mm. The exact polyline distance for this pair is 12.001198 mm, leaving 5.001198 mm between the two Ø7 receiving volumes. `compact-local-repair-v3.json` binds that limited check; it is not a full self-check or obstacle acceptance. All 953 mathematical poses retain constant length and continuous tangents. Revision 2 failure files are preserved in `compact-isolated-v2-self-failed/`.

An obstacle acceptance run must use the unified current cap and amplifier overlay. The independent plan → geometry → self stages may use a explicitly diagnostic, hash-bound current overlay, because they do not load or certify obstacle solids. The +16X/+2Z amplifier conflicts with the newer FFC; the desired +16X/+3Z position has also hit legacy amplifier posts retained in one cap branch. Neither is an accepted manufacturing layout. Do not make an obstacle-clearance claim against a casually substituted mixed scene. Root retains the CAD token until explicitly reassigned.
