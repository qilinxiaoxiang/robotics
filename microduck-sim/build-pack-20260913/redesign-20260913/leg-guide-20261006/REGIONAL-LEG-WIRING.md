# Regional leg wiring adapter

The old cabling tab mixed motor power tails and data edges, retained the cross-foot ID1→ID6 edge, and displayed every robot body even when the selected group was a leg. Its generic renderer rebuilt curves using Catmull–Rom interpolation and separated parallel conductors with artificial offsets. Thus a scoped menu alone did not fix the pictured geometry.

`build_leg_wiring_adapter.py` replaces only the eight in-leg rows and removes the obsolete cross-foot row. It preserves unrelated connection objects and their original steps; their electrical architecture is not reapproved. Displaced legacy separate-power rows remain under the explicit whole-machine torso/power entry. Do not rerun `build_wiring_guidance.py` or `build_wiring_spatial.py` over this result: those old producers still describe the previous architecture.

Left-leg entry: 10→9, 9→8, 8→7, 7→6. Right-leg entry: 5→4, 4→3, 3→2, 2→1. Trunk entry and the head remain separate. Previous/next never leave the chosen group.

`wiring3d.js` takes the regional route branch before the generic cable renderer. It displays five exact source meshes for the selected cable: three conductors and two receiving housings. STL triangle coordinates are retained byte-for-byte in an indexed payload, at world millimetres with identity placement. It neither interpolates nor offsets these paths. The installed view shows only the corresponding leg. Endpoint detail isolates its open motor and seated housing; it deliberately does not animate the assembled cable through a closed cover.

Each cable has English Prepare / Assemble / Check instructions. Both ports of both thigh motors must be connected before leg-01; the ankle motor before leg-05; routing is inspected before lower-link closure. `four-preplugged-delta.json` adds all eight current thigh housings along the actual shared ±Y45 approaches, with 181 samples each and no fixed-thigh intersection. Soft wire is fed freely, not treated as one rigid translating shape.

Local acceptance: `test_wiring_context.cjs` executes actual navigation and tutorial controls; `test_checked_leg_wiring.cjs` checks all source STL triangles and invokes the actual regional renderer with interpolation constructors configured to fail. `regional-leg-wiring-regression.json` binds the final source hashes. These are local tests; the parent task still owns bundle generation, Mac mini deployment and live Chrome visual acceptance. No print source changed and no physical commissioning is claimed.

The effective guide retains its integral-seat lower-link variant. `current-lower-revision-delta.json` checks all 40 cable bodies plus two case restraints against both revised links: 84 pairs covered, 14 exact tests clear. `current-guide-interface-inventory.json` records that displayed variant separately from the original printed-link inventory used by the native assembly. V1.4's actual print audit lists only the integrated neck change, not replacement knee links; no physical adoption of optional lower links is inferred.

The main Assemble page now consumes `operation-dependencies.json` through `WIRING.assemblyCablePrerequisites`. Required cable actions appear before the corresponding seating/closure text, link to that exact regional cable, and return to the same assembly operation. They are no longer instructions discoverable only after finishing the mechanical guide.


## Mixed-length and access update, 9 October

The current source is `../workflow-review-20261009/enclosed-wiring-repair/motor-wires/slack-packaging/mixed-leg-manifest.json`. Two knee links use the nominal 100 mm cable class; the other six use 180 mm. These are length classes, not a demand to reproduce a mathematical flexible shape. Six adjustable tie receiving contexts accompany the relevant route. No new printed geometry is released by this update.

Both assembly modules consume closure deadlines before the affected placement step. Their cable buttons open the exact corresponding wiring item; Return restores the original operation. The isolated motor endpoint view uses the same housing mesh and registered axis as the source-bound 16-port bench check, with play/pause and scrub along 12 mm. This does not animate a routed harness through a closed cover. Static source-envelope and bench sampling evidence do not establish physical connector fit or lifetime under motion.

Native complete-leg review and live Chrome review are retained separately from the older full-build design verifier. That verifier regenerated and passed its historical Zero-form-factor baseline on 9 October; it does not accept the current head USB package, new mount concepts or whole flexible harness.
