# Persistent MicroDuck guide hosting

Problem P5: an assembly guide must remain accessible during physical assembly. On 2026-10-07 the prior MacBook process had exited: no listener on 127.0.0.1:8766. The user authorized Mac mini hosting.

Canonical source remains this MacBook folder. The runtime copy is `mac-mini:~/code/microduck-guide`. The current build guide (V1.6: wall power, OpenRB tray, notched head cap) is http://today.tailfc7c94.ts.net:8766/ and `/MICRODUCK-BUILD.html`; its source is `microduck-sim/guide/`, and its built `dist/MICRODUCK-BUILD.html` is copied into this folder before deployment. The leg assembly entry remains http://today.tailfc7c94.ts.net:8766/LEFT-LEG.html . The head candidate is `/HEAD-EYE-REVIEW.html`; the older ankle candidate remains `/ANKLE-REDESIGN.html`. User reaffirmed Mac mini delivery on 2026-10-08: local files and localhost previews do not satisfy handoff.

The Mini launch agent `com.shawnxiang.microduck-guide` runs `hosting/serve_remote.py` with Homebrew Python, starts at login and restarts after exit. It binds only the Mini's Tailscale address resolved from `today.tailfc7c94.ts.net`, serving the existing explicit file allowlist. Access requires the existing Tailscale connection. No extra credentials are required. This is not a public website.

The MacBook launch agent `com.xiangzheng.microduck-guide-redirect` maintains old 127.0.0.1:8766 bookmarks with a 307 redirect to the Mini. It serves no files. Both plists are in this folder; installed copies are under the respective user's `~/Library/LaunchAgents`. Logs are `~/Library/Logs/microduck-guide.{out,err}.log`.

To update, copy only `serve_guide.py`, `test_serve_guide.py`, `MICRODUCK-BUILD.html`, `PARTS-SHEET.html` (from `microduck-sim/guide/print/`), `zhengxia_MicroDuck_V1.6_8-files.zip` (the V1.6 print release), `PARTS-SHEET-V1.7.html` and `zhengxia_MicroDuck_V1.7_4-files.zip` (V1.7 reprint), `PARTS-SHEET-V1.8.html` and `zhengxia_MicroDuck_V1.8_8-files.zip` (V1.8 head and rear-pack release, from `microduck-sim/guide/print/release-V1.8/`), `EXTENSION-REVIEW.html` (neck-route + audio + Pi-mount extension review, built by `microduck-sim/guide/extension-20261012-neck-audio/page/build_page.py`), `LEFT-LEG.html`, `ANKLE-REDESIGN.html`, `HEAD-EYE-REVIEW.html`, `ANKLE-REDESIGN.zip`, the two allowlisted JSON source snapshots, and `hosting/serve_remote.py` from canonical source to matching Mini paths with rsync. Static page updates require no restart. For server changes run `ssh mac-mini 'launchctl kickstart -k gui/$(id -u)/com.shawnxiang.microduck-guide'` after copying. Do not copy unrelated source or private files into the serving directory.

Acceptance: current source bytes match remote responses; old links redirect; actual Chrome renders the assembly; original concurrency/timeout/allowlist tests pass against Mini; terminating the service process produces a new running process and HTTP 200. Receipt files are kept here. Reassess deployment if any live entry returns non-200 or mismatched bytes; appearance alone is insufficient.

Build `HEAD-EYE-REVIEW.html` in `../../head-redesign-20261008/`, then copy it into this guide directory before allowlist regression and deployment. Preserve the explicit board-identity note: its current geometry uses a first-generation Zero form-factor reference, not validated Pi 3 fit.

## Interrupted-download repair — 8 October 2026

The 3-second request-header timeout also applied to response writes. A slow reader could receive only part of the 31,912,487-byte guide, leaving the visible page indefinitely at geometry loading. A controlled 4-second pause reproduced truncation under the old timeout and a full byte-identical response under the repair. Keep the header timeout at 3 seconds and use a separate 60-second **idle write** timeout after a valid request. This is not a total-download limit. Threaded workers continue to isolate slow requests.

The same allowlisted URLs now negotiate gzip and use content-based ETags with revalidation. The first download still depends on network throughput; unchanged reloads return 304. Tests cover exact decoded bytes, quality-weighted encoding, cache validation, paused downloads, and the original truncation negative control. `main-restored-acceptance.json` binds the real Mac mini response and Chrome torso-module screenshot. Head work must not disable or replace the existing full assembly entry.

## Replacement review — 8 October 2026

`/REPRINT-PLAN.html` and `/REPRINT-PARTS.zip` are explicit allowlisted resources. Copy them from canonical source along with the full guide. The list distinguishes five primary mechanical prototypes, two optional fresh-build lower-link alternatives, and six held head/camera/audio parts. The archive contains only the seven released prototype STLs, source-bound geometry manifest and README. Conditional existing-knee washer repair is described separately; ownership of matching washers and physical fit are not established. The 26-check remote server receipt is `reprint-server-acceptance.json`.

## Stage A design review — 9 October 2026

`/DESIGN-REVIEW.html` is the English central-battery and workflow review, built from `../../workflow-review-20261009/build_review.py`. It contains dimensioned native-CAD envelope projections and explicit unfinished integration boundaries. Only this HTML and the one new literal allowlist route were deployed; native STEP concepts and print files remain local. Current live assembly/head entries remain available. See `../../workflow-review-20261009/deployment-receipt.json` for byte identity and Chrome observation. The legacy cabling tutorial remains under architecture review; the module-navigation fix is saved but not yet integrated/published.
