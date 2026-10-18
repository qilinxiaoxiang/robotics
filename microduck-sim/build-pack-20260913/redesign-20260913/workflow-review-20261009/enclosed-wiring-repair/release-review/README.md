# Active repair release acceptance

Problem IDs: P0, P5, P6. This entrypoint closes the gap between individually checked repairs and a complete, revision-consistent handoff. A complete populated-head/harness receipt, current guide/live readback and the matching incremental print package can change the design decision; a local body or bare-board pass cannot.

`../verify_release.py` is read-only. It hashes files, reads JSON and ZIP entries, and prints JSON to stdout. It does not generate CAD, wiring, BOMs, HTML, print files or deployment. Exit 0 means the requested scope passed; exit 1 means incomplete; invalid CLI arguments exit 2. No historical-baseline escape is supported.

From the active repair directory:

```sh
python3 -B verify_release.py --scope design
python3 -B verify_release.py --scope project
python3 -B -m unittest test_verify_release -v
```

The default input is `release-manifest.json` beside the verifier. It intentionally does not exist until the release owner supplies final evidence. `release-manifest.example.json` is an incomplete template, not a release. The current missing-input diagnostic is `known-missing-diagnostic.json` in this directory. No PROJECT-CONTEXT or dispatcher is changed by this work.

To configure the existing dispatcher, the future `activeRepair.verifier` path relative to MicroDuck is:

`build-pack-20260913/redesign-20260913/workflow-review-20261009/enclosed-wiring-repair/verify_release.py`

## Manifest contract

Required top-level fields:

- `schemaVersion: 1`, nonempty `releaseRevision`, `status: "ready"`.
- `projectContext: {path, sha256}`: exact current canonical PROJECT-CONTEXT.json.
- `artifacts`: objects with unique `id`, `role`, `path`, `sha256`.
- `gates`: six `{path, sha256}` receipt references named `mechanical`, `head`, `harness`, `guide`, `print`, `liveDeployment`.
- `projectAcceptance: {path, sha256}` only required for project acceptance.

All paths, including receipt `sourceHashes` keys, are absolute or relative to the release manifest directory. They are not resolved relative to each nested receipt. Each digest is SHA-256 of actual file bytes.

Required artifact roles are `mechanical_inventory`, `head_inventory`, `wiring_inventory`, `guide_data`, `guide_wiring`, `guide_spatial`, `guide_html`, `print_zip`, `printer_file`. Multiple HTML artifacts are allowed when the release has several entry pages. Each geometry/wiring inventory is JSON with a nonempty `sourceHashes` map covering all actual leaf geometry/route files used in that inventory. Do not supply only a report hash in place of the geometry it tested.

There is exactly one delivery ZIP. Each `printer_file` also has `color`, `machine` (`bambu` or `elegoo`) and `archiveEntry`. Every declared color needs one file for each machine. ZIP members must exactly match those declared printer files, with names starting `zhengxia_`, and their uncompressed bytes must match the declared hashes. This preserves the requested machine-only SD-card package. Native project/archive formats inside those machine files are not regenerated or reinterpreted by this checker; their slicer and functional acceptance belongs in the print receipt.

## Receipt contract

Each gate receipt must have:

```json
{
  "releaseRevision": "the same revision as the manifest",
  "passed": true,
  "complete": true,
  "unresolved": [],
  "coverage": ["the gate-specific entries below"],
  "sourceHashes": {"actual input path": "SHA-256"}
}
```

`coverage` must explicitly include the relevant fixed list from `verify_release.COVERAGE` (also listed in `receipt-contract.json`). These names specify what the producer reviewed; the verifier does not fabricate or rerun those engineering checks.

Head additionally requires `wholeHeadAccepted: true`; harness requires `wholeHarnessAccepted: true`. They must represent the complete current coupled inventory, not an isolated-board/static subsection. Body and IMU local receipts remain useful input evidence but cannot be dropped directly into these gates.

The receipt source hashes must bind:

- Mechanical: mechanical inventory.
- Head: head inventory and wiring inventory.
- Harness: wiring, mechanical and head inventories.
- Guide: all three inventories plus the final DATA, WIRING, SPATIAL and every HTML artifact.
- Print: both mechanical/head inventories, ZIP and all printer files.
- Live deployment: the exact final guide DATA/WIRING/SPATIAL/HTML. Also require `liveReadbackMatched: true`, `browserChecked: true`, actual `url` and `checkedAt`.

Include hashes of the underlying completed checks in each receipt's `sourceHashes`. Every listed source is rehashed. This is evidence aggregation, not a way to turn an incomplete result into a passed one by adding coverage labels. The release owner must derive a complete receipt from the actual source-bound checks, retaining any named intentional mating contacts and physical limitations.

## Project is a separate acceptance scope

Design success always reports zero physical tests. Project acceptance additionally requires a source-bound `projectAcceptance` receipt: `kind: "hardware_commissioning"`, positive integer `physicalTests`, all `PROJECT_COVERAGE` entries, and bindings to the current release artifacts. It includes board qualification, loaded power, connector fit, observation/control timing, stale-data and lost-command stopping.

The verifier also invokes only the read-only `review()` function of the existing `phase1/check_project_context.py`. Its training identity, implemented-capability, camera sourcing and real camera-observed visual-pickup trial gates must pass. The hardware trial contract revision must equal this release revision. No phase split, simulation result, source-only board fit, print release or successful design receipt closes those gates. The verifier does not update canonical acceptance flags or procurement holds.
