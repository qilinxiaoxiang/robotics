# Non-head assembly motion completion — 2026-10-09

Problems P5/P6. The deliverable is `assembly-motion-overlay.json`, ready for the main guide to apply after the current stock fastener selection and the verified torso-service replacement, before tutorial/wiring projection. It changes no source mesh, installed ankle/foot, cable route or printer file.

## Repairs

- Both foot-fitting/retainer operations (stable IDs 11/12) now precede the knee join (IDs 09/10). The original position let the thin driver shaft fit but put the handle through the thigh and motors. The complete ankle-foot module, eight installed screws and washer now move together during 09. A detached bench check clears the stated handle; the added foot and retained hardware also clear the fixed knee station along the existing 0.25 mm path samples.
- The two downward torso-support screws require a compact right-angle tool: Ø3 mm bit, 18 mm axial projection and Ø6 × 25 mm side arm directed toward the torso center. A long straight handle hits `power_support`. The 25 mm arm is a receiving requirement, not an assertion of owned tool stock.
- The two shell-to-yaw case screws at `neck-14` require the same short bit, with a Ø6 × 50 mm arm directed outward on the appropriate side. A straight handle hits the upper-neck parts and installed screw heads. The eight ID12 output screws keep their straight driver.
- All 90 reviewed operations receive concrete Prepare / Assemble / Check prose and source-specific motion evidence. Seven ordinary rigid-group moves now declare their retained screw IDs and the carrying part for each screw. Existing torso service moves keep their previously checked hardware groups.

## Evidence

`acceptance.json` and `overlay-verification.json` are the compact entries. Current base source is bound by byte hash; current-stock part/screw selection and every operation before overlay application are also bound. Operation hashes use Python JSON with sorted keys, compact separators, `ensure_ascii=True` and UTF-8.

- 37 fastening stations / 154 screw occurrences: stated handle against actual station parts, and shaft/handle against previously installed screw heads. Sequential screw heads within the same fastening operation are included. This supplements the earlier source-bound shaft checks.
- Seven retained-hardware group paths: moving heads against fixed parts, moving parts/heads against fixed installed heads, and both newly carried feet. Samples are spaced at most 0.25 mm. All new tested intersections are zero.
- Four integral-neck-seat delta paths: the actual added seat material is checked during the affected placements. All clear. Removed bore membrane does not introduce new interference.
- The old knee approach negative controls remain ~1,458 mm³ on each side. The corrected left path is zero; the right retains only the previously scoped 0.17147 mm³ source terminal seam contact. The original yaw-output driver blockage is reproduced at ~238.5 mm³ before the roll motor is moved to its later operation.
- The four new working-tool failures are retained under `negative-original-order/`; they are not overwritten by the positive results. `verify_overlay.py` rejects late foot fastening, a foot left behind during knee motion, a missing retained foot screw, the wrong neck tool direction, and stale source operations.
- The frozen mixed eight-cable manifest, its installation dependencies and the four-preplugged-housing station receipt are inputs. No whole-shaped flexible bundle is translated through a closed cover as an insertion demonstration.

The largest final delta worker sampled 321.422 MiB. One initial whole-data loader exceeded the 512 MiB guard; it was replaced with operation-local inputs and that result was discarded/retested. No budget was raised.

## Preserved boundaries

Leg operation 07 remains a real physical-fit checkpoint. The foot approach remains a measured stop before seating, not a passing rigid-fit claim. The user's already completed ankle/foot stays intact. The user-confirmed M2×6 knee screws through original 2.8 mm seats still imply 3.2 mm nominal entry against a 3 mm limit; this review does not approve that stack or infer damage.

The straight tool receiving envelope is a Ø3 shaft with a Ø18 × 60 mm handle beyond 45.5 mm from the head seat. The right-angle variants are explicit. These are working-space checks, not hand/grip, drive-tip, applied-torque or particular purchased-tool certification. No exact flexible deformation or walking-domain certification is asserted.

The torso source is the 28-step already-fastened-hip service branch. Its first ten removal operations apply only to hips already closed. A loose new build must not be told to tighten seven joints merely to undo them. The existing service document's loose-core entry remains distinct from a complete newly validated fresh-build sequence.

The legacy fuse-carrier `power-03/04` evidence is retained for provenance only; the separate current power revision supersedes those instructions. This overlay does not release that old electrical architecture.

## Integration

Apply each `operationPatches[].set` to its exact `expectedOperationSha256` match. Apply `moduleOrders` as full permutations of existing stable IDs. For torso, patch `service.module`, not the obsolete two-operation `DATA.modules` torso. Render `motionEvidence.caption` instead of the blanket unvalidated-path caption. Move `movingScrewIds` using the associated `movingScrewPartKeys` part displacement; leave other `priorScrewIds` at their installed position. Preserve the explicit ankle fitting and foot contact-stop behavior.

No source data, viewer, bundle or deployment was changed by this branch. Run `python3 verify_overlay.py` from this directory for the lightweight integration gate. Geometry receipts are already frozen; no broad rerun is needed for UI integration.
