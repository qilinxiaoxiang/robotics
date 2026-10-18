# Motor-wire stage model — frozen review snapshot

This is the authorized intermediate Fusion review, not an accepted complete harness. The source robot retains original leg spacing and the existing converter. No printed part or electrical topology was changed.

Import `manifest.json` parts in millimetres with identity transforms. It contains 45 individual conductor bodies and 30 separate complete connector receiving boxes. All 75 STL exports were read back as closed, positive-volume meshes. STEP was not exported for this stage; sampled world centre lines, control points, port frames and receiving dimensions are in `routes.json` and `route-input.json`.

Four of fifteen routes have no neutral-pose static intersection in the tested scene: ID11→12, ID12→5, ID3→2 and ID7→8. Eleven remain failed and their conductor bodies are red (`#cc493d`). Original display colours are retained as `sourceColor`. Geometry, per-route check receipts and manifest hashes were checked together before this snapshot was frozen.

Registration uses the earlier official XL330 STEP shroud/pin registration and each motor source transform. The OpenRB endpoint is its actual right-angle connector, source connected component74: three square pin faces at2.5mm pitch and the +Y shroud rim. `openrb-current-source-equivalence.json` proves equality of all317300 triangle coordinates between the registered source and current Fusion OpenRB mesh. This is source-CAD alignment, not physical mating certification.

The diameter1.5mm is a receiving assumption. The mesh polygon circumscribes that diameter; it does not silently shrink the wire. In the shallow knee cavity the three wire centres converge from connector pitch2.5mm to1.6mm spacing, with original diameter retained. The curve is a locally rounded polyline; the initial free cubic overrun is no longer used. Minimum sampled bend radii are diagnostic only, not an established manufacturer bend specification.

The two knee bridge routes originally crossed the orange thigh lip. The revised routes remain in the shallow cavity and now have zero static intersections. Pre-seat the obscured knee plugs before closing this thigh subassembly. The earlier insertion evidence identifies the orange thigh lip, not the opposite black plate. Complete wire-bearing motor insertion and existing-leg recovery remain separate, unqualified operations.

## Remaining route failures

- ttl-openrb-15: head_yaw_link 5.927 mm³ maximum per conductor/receiving body, motor13 3.376 mm³ maximum per conductor/receiving body, jaw_support 3.202 mm³ maximum per conductor/receiving body, head_cap 0.527 mm³ maximum per conductor/receiving body
- ttl-15-14: speaker 33.668 mm³ maximum per conductor/receiving body, head_cap 23.564 mm³ maximum per conductor/receiving body, head_bottom 4.732 mm³ maximum per conductor/receiving body, speaker_keeper 1.295 mm³ maximum per conductor/receiving body
- ttl-14-13: jaw_support 0.470 mm³ maximum per conductor/receiving body, head_yaw_link 0.444 mm³ maximum per conductor/receiving body
- ttl-13-11: jaw_support 15.673 mm³ maximum per conductor/receiving body, head_bottom 6.967 mm³ maximum per conductor/receiving body, jaw_frame 3.097 mm³ maximum per conductor/receiving body, head_yaw_link 2.870 mm³ maximum per conductor/receiving body. Conservative OpenRB component contact also remains inconclusive.
- ttl-05-04: regulator_insert 42.730 mm³ maximum per conductor/receiving body, power_support 15.605 mm³ maximum per conductor/receiving body, regulator 1.389 mm³ maximum per conductor/receiving body
- ttl-04-03: motor3 28.359 mm³ maximum per conductor/receiving body, right_thigh 3.640 mm³ maximum per conductor/receiving body, right_plate 1.611 mm³ maximum per conductor/receiving body
- ttl-02-01: right_lower 2.304 mm³ maximum per conductor/receiving body, right_thigh 2.173 mm³ maximum per conductor/receiving body
- ttl-01-06: ankle 13.487 mm³ maximum per conductor/receiving body, right_ankle 13.483 mm³ maximum per conductor/receiving body, lower 7.264 mm³ maximum per conductor/receiving body, right_lower 7.249 mm³ maximum per conductor/receiving body, smallring 4.897 mm³ maximum per conductor/receiving body, right_smallring 4.897 mm³ maximum per conductor/receiving body
- ttl-06-07: lower 2.307 mm³ maximum per conductor/receiving body, thigh 2.173 mm³ maximum per conductor/receiving body
- ttl-08-09: motor8 28.360 mm³ maximum per conductor/receiving body, thigh 3.641 mm³ maximum per conductor/receiving body, plate 1.611 mm³ maximum per conductor/receiving body
- ttl-09-10: regulator_insert 41.607 mm³ maximum per conductor/receiving body, power_support 15.278 mm³ maximum per conductor/receiving body, regulator 2.280 mm³ maximum per conductor/receiving body

## Next dependent checks

- Resolve the remaining local paths around actual converter support, leg receiving cavities, speaker and neck surrounds. The model is not evidence that these source parts require modification.
- The motor14 lower connector receiving box overlaps the head-bottom model by1.197mm³. Its full catalog box is conservative: obtain/inspect the actual EHR housing shape before concluding that a real seated plug cannot fit.
- Model the full owned nominal180mm leads and allocate spare length. Current per-route lengths are installed-path candidates only; exact nominal versus flexible length has not been established.
- Confirm actual pin order and the active power-distribution contract. Three displayed insulated strands do not authorize bridging independently supplied VDD branches; the current DATA-only ledger remains unchanged.
- Check wire-to-wire self-contact, realistic bend/slack under joint movement, fastening restraint, and complete prewired assembly/closure. Neutral static clearance does not establish those gates.

Rebuild ownership is this directory only. Preparation is `prepare.py`, then `register_openrb.py`, then `build_routes.py`; CAD libraries must run through the shared bounded launcher. `check_route.py` checks one route against nearby source obstacles; OpenRB uses the proven source-component conservative enclosures. `finalize_stage.py` rejects stale source/model receipts and applies the staged colours. Do not run a rebuild over a displayed frozen stage without making the new snapshot explicit.
