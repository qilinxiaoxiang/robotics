# Cap-on GPIO housing check

Independent check of interference-audit finding 3 (step `cap-on`). Robot frame in mm: x forward, y left, z up. Checked 2026-10-09 against the V1.6 release.

## Conclusion

**The interference is real for the connector the guide specifies.** The guide plugs a 2x20 crimp housing with precrimped 2.54 mm leads onto the Pi header before the cap goes on (`guide/content/steps.py`, step `gpio`). When the populated cap is lowered straight down, the housing passes through `camera_clamp_screw_3`, `camera_retainer`, `camera_board` and `face_panel`. Twelve of the thirteen used pins collide; only pin 40 is clear.

**The result depends on connector length only below about 10.1 mm.** That is the limit measured from the header plastic, body plus anything rigid in front of it. Commercial 2.54 mm crimp housings are about 14 mm long, and at 14 mm the clash is certain.

**No assembly order avoids it without a part change:**
- The housing cannot be plugged after the cap is on.
- The cap cannot be lowered behind its final position and then slid forward.
- Separate 1-pin housings do not help.

**Smallest change: move the Pi seat on `head_cap` 4.6 mm toward -x.** It has three parts:
- Move both Pi rails by [-4.6, 0, 0].
- Trim only the +y rail to x >= 52.8.
- Remove the two unused former-OpenRB front bosses.

With the move, the housing clears the camera stack by 0.51 mm for the guide envelope and by 0.76 mm for a 14.0 mm housing. The Pi keeps 1.09 mm before its solder tails meet `jaw_support`.

**Three companion changes are required:**
- Screw E-pi-02 (+y lower) changes from M2x6 to M2x4. The Pi step text in `steps.py`, which drives four M2 x 6, must say three M2 x 6 and one M2 x 4 at the +y lower corner.
- The guide data must move the Pi group, the housing envelopes and fastener seats E-pi-01..04 by [-4.6, 0, 0].
- `bundle_head` must be re-routed. A route with the V1.6 clearance and length exists over the Pi's top edge.

The candidate is in `/Users/xiangzheng/code/robotics/microduck-sim/guide/print/candidates/head-cap-pi-shift/`. It is not released, sliced or zipped.

## Evidence

### Geometry of the header and housing

- **Pi board and pin axis.** The Pi Zero W stands upright. Its pin axis is (0.985, 0, -0.174), so the pins point forward and 10 degrees down.
- **Header layout.** The 2x20 header runs across the head along y, at the lower edge of the board:
  - Pins 1 and 2 are at the +y end (y 22.86 to 25.40).
  - Pins 39 and 40 are at the -y end.
  - Odd and even rows differ only in height.
  - No pin sits in front of another, so the premise that I2S pins 35/40 sit at the front end does not hold. Pin 35 is at y -20.32 to -17.78 and pin 40 at y -25.40 to -22.86.
- **Header and pin lengths.** The header plastic top is 43.23 mm along the pin axis, and the pin tips are 5.96 mm beyond it.
- **Guide housing envelope.** The guide models each used pin as a 2.54 x 2.54 mm column, 14.25 mm long from the header plastic. Its front face is at x 78.53 (odd row) and x 78.97 (even row). The envelope matches a box rebuilt from the header to within 0.055 mm³ per pin. The footprint across all 40 positions is 50.8 x 5.08 mm, which matches a real 2x20 housing.
- **Real housing length.** These figures are read from product pages; no housing was measured.
  - Harwin M20-1070200 (2+2 position female crimp housing) is listed as "5.08 x 5.10 x 14.00" with no axis labels.
  - A Maplin 8-way Dupont-style housing is listed as 14.0 x 20.32 x 2.6 mm (Length x Width x Height). There, 20.32 mm is 8 pitches along the row and 2.6 mm is one row.
  - Inference: about 14 mm is the length along the contacts.
  - The 8.5 mm figure belongs to a PCB-mount female socket, which takes no crimped leads.
- **Camera stack overhang.** The camera stack overhangs the housing front:
  - The clamp screw heads start at x 74.88 (`camera_clamp_screw_1..3`, z up to 149.2).
  - `camera_retainer` starts at x 75.48 and `camera_board` at x 75.13. Both reach z 143.6 to 150.
  - `face_panel` starts at x 77.10.
  - Because the cap comes straight down by [0, 0, 40], anything above the housing in the same xy column is in its path.

### The interference today

Each housing column was swept exactly, as hull(column, column + [0, 0, 40]). Overlap in mm³:

- **Pins 1, 2:** `face_panel` 4.4 and 5.7.
- **Pins 3, 4:** `face_panel` 4.6 and 6.7; `camera_retainer` 1.1.
- **Pins 5, 6, 8:** `camera_retainer` 15.1 to 15.5; `camera_clamp_screw_3` 12.0 to 14.9; `face_panel` 9.0 to 19.6.
- **Pins 9, 10, 12:** `camera_retainer` 9.8; `face_panel` 4.2 and 11.0 on pins 9 and 10.
- **Pin 14:** `camera_board` 142.0; `camera_retainer` 9.8.
- **Pin 35:** `camera_retainer` 30.4; `camera_clamp_screw_1` and `camera_clamp_screw_2` 15.9 each; `face_panel` 16.7.
- **Pin 40:** clear.
- **Pi group without the housing:** the board, header, components and solder tails sweep clear.

### How much rearward shift each connector length needs

The shift below is measured to the first touch, for the used columns. Connector length is measured from the header plastic.

- **Up to 9.5 mm:** no shift needed.
- **10.5 mm:** 0.39 mm.
- **11.5 mm:** 1.38 mm.
- **12.5 mm:** 2.36 mm.
- **14.0 mm:** 3.84 mm.
- **14.25 mm (guide envelope):** 4.09 mm.
- **15.25 mm:** 5.07 mm.
- **16.25 mm:** 6.06 mm.

Interpolating this curve, the threshold is about 10.1 mm. The governing obstacle is the head of `camera_clamp_screw_3` over pins 6 and 8. A full 2x20 block gives the same numbers as the used columns.

**Rear limit.** Moving the whole Pi group straight back, the solder tails first touch `jaw_support` at a 5.69 mm shift. A connector whose rigid length exceeds about 15.9 mm therefore cannot be solved by moving the Pi alone.

### Assembly orders without a part change

- **Plug the housing after the cap is on:** fails. Starting the insertion needs 14 mm of free length in front of the pin tips. Only 9.66 to 10.11 mm exists before the next part, measured along the pin axis from each used pin tip.
- **Lower the cap behind its final position, then slide it forward:** fails. The +y rail reaches `jaw_support` after 3.23 mm of rearward offset (rail at x 55.53, `jaw_support` ends at x 52.30). The housing needs 4.09 mm, or 3.84 mm for a 14.0 mm housing.
- **Separate 1-pin housings:** fails. A Dupont-style 1-pin housing is the same 14 mm long. Of the 40 header positions, only 39 and 40 have a clear column. Every used pin except 40 is blocked.
- **Fit the face and camera after the cap:** the audit reports that the face and camera unit then hits `head_bottom` (113 mm³) and `head_cap` (126 mm³), and that a tilted cap swung shut about a front axis hits the face and `jaw_support` (`findings.json`, step `cap-on`). I did not repeat those checks.

### The candidate head_cap

It is built from the released V1.6 cap (`guide/print/world/head_cap.stl`, sha256 5c22fbf6...) with exact manifold Booleans, by `scripts/build_candidate.py` (DX=4.6, X_TRIM=52.8).

- **Rails.** Both Pi side rails are removed and re-added from their source STLs, moved by [-4.6, 0, 0]. They are clipped 0.1 mm under the outer roof, as `union_cap.py` does; the roof clip is now z 147.06 instead of 147.50.
- **Trim.** The +y rail is trimmed to x >= 52.8, which removes 45.99 mm³. The -y rail needs no trim. Its swept added material is clear of everything, while the audit had trimmed both rails.
- **Bosses.** The two former OpenRB front bosses at y +-10.25 are removed.
  - `guide/content/fasteners.json` lists their holes as unassigned: "nothing mounts here".
  - Left in place, each overlaps the moved Pi PCB by 9.2 mm³.
  - Moving them back by 4.6 mm, as the audit did, is an alternative. I did not build it.
- **Volume.** V1.6 is 32118.39 mm³ and the candidate 31700.19 mm³. Removed 1221.73 mm³ (rails 433.47 and 433.44, bosses 178.23 and 177.94), added 803.53 mm³, net -418.20 mm³.
- **Everything else is unchanged.** The XOR volume outside the six edit boxes is 6e-13 mm³. The rear cable notch region XOR is 0 mm³.
- **Readback.** The mesh is watertight with consistent winding: one body, genus 6, the same as V1.6.
- **Print pose.** The candidate uses the same `sourceToPrint` as the release.
  - The bounds equal the released cap's.
  - Flat contact is 104.39 mm², the same as V1.6; the minimum is 100.
  - The new trim face sits 4.4 degrees past vertical in the print pose, so it is a wall, not an overhang.

### Side effects at 4.6 mm

**Descent and final pose:**
- **Rigid parts on the way down.** The moved Pi group and all 13 housing envelopes sweep clear of the camera stack, face, `jaw_support`, motors and `head_bottom`, with 0 mm³ overlap (exact convex sweeps).
- **Margins per pin.** Clearance to first touch is 0.51 mm on pins 6 and 8, 0.76 on 14, 0.95 on 5 and 35, 1.11 on 10 and 12, 1.56 on 9, 2.0 to 3.2 on 1 to 4, and 4.6 on 40.
- **Added cap material.** Swept at 0.25 mm steps, it overlaps nothing.
- **Final pose of the moved parts.** The moved Pi group and envelopes overlap none of 28 head parts: `jaw_support`, `motor13..15`, `jaw_frame`, the speaker parts, `amplifier`, `head_bottom`, the camera stack and the candidate cap among them.
- **Final pose of the cap.** Its contacts with the fixed and carried parts are identical to V1.6. The only ones are the existing 63.03 mm³ lap with `head_bottom` and the existing 0.21 / 4.30 mm³ contacts with the speaker keeper and screws.

**Fasteners and rails:**
- **Pi screws.** The four Pi screws are E-pi-01..04 (`fasteners.json`).
  - E-pi-01, E-pi-03 and E-pi-04 keep 4.4 mm of rail material along the screw axis, as in V1.6. Their M2x6 screws sweep clear during cap-on.
  - E-pi-02 (+y lower) keeps 2.9 to 3.24 mm of material. With the trim, an M2x6 tip leaves the rail and sweeps 10.03 mm³ into `jaw_support` during cap-on. An M2x5 sweeps 0.28 mm³.
  - An M2x4 is clear and engages 2.46 mm.
- **+y rail sections.** Areas in mm², candidate versus V1.6:
  - z 115: 8.19 versus 9.93.
  - z 117.5: 14.44 versus 22.04.
  - z 120: 15.79 versus 21.11.
  - z 122: 4.38 versus 6.50. The web there is 1.37 mm thick in x instead of 2.03 mm.
  - z 124: 5.51 versus 6.50.
  - z 126 and up: unchanged.
- **-y rail sections:** all unchanged.
- **Rails stay attached.** Both rails remain fused to the roof, with joint footprints of 9.62 and 9.70 mm² against 9.72 and 9.79 mm² in V1.6.

**Cables and access:**
- **CSI ribbon.** The straight connector-to-connector distance grows from 28.44 to 29.44 mm, so the drawn 28.87 mm route grows by about 1.0 mm. The fitted ribbon is 200 mm long (`PROJECT-CONTEXT.json`, photo-confirmed).
- **microSD slot (+y board edge).** The free gap from the board edge to the cap wall along +y is 7.40 to 9.48 mm, 0.33 mm less than V1.6 (7.74 to 9.81).
- **USB edge (top of the board).** The roof gap is 5.79 to 8.63 mm, 0.37 mm less than V1.6 (6.16 to 8.97). Inference: a micro-USB plug did not fit under the roof in V1.6 either, so USB use needs the cap off in both versions. The bundle feeds 5 V to GPIO pins 2 and 4, the Pi's 5 V pins.
- **Rear cable notch.** The notch geometry is unchanged, and the bundle centreline still passes it at 3.37 mm.
- **bundle_head.** If only the end of the drawn route moves with the Pi, the centreline passes 0.90 mm from the moved +y rail at (53.5, 31.3, 133.3). A re-route search used 0.5 mm voxels and kept the V1.6 clearances (2.91 mm to the cap and fixed parts, 1.25 mm to the Pi group) from waypoint 8 to the moved end.
  - **Around the +y board edge, as V1.6 does:** no longer possible at that clearance. The best is 2.51 mm, at the moved rail.
  - **Over the board's top edge:** possible. Exact readback gives 2.95 mm to the cap and fixed parts and 1.13 mm to the Pi group; the V1.6 route found by the same search gives 2.98 and 1.23 mm.
  - **Length.** The tail is 58.66 mm against 58.99 mm, and the whole of `bundle_head` is 128.39 mm against 128.71 (drawn V1.6: 130.0). The harness does not need to be longer.
  - The waypoints are in `measurements.json` under `bundleHeadReroute`.

## Limits

- **Housing size.** The length is not measured. The 14 mm figure comes from two product listings, one of them without axis labels. A purchased housing under about 10.1 mm, rigid parts included, would make the change unnecessary. Measure the actual housing from the build stock with calipers to settle this.
- **Leads not modelled.** Only the rigid housing is checked. The leads leave its front face with 0.5 to 3.2 mm of room before the camera stack's descent path, depending on the pin.
  - On pins 5, 6, 8, 14 and 35, the leads must be dressed sideways or down before the cap goes on, or they will brush the clamp screw heads and the retainer.
  - Inference: they are flexible enough to deflect, but they are not modelled.
  - Moving the Pi up to about 5.2 mm would add room for the leads but cut the rear margin to under 0.5 mm.
- **Rail strength.** Not computed; the following is a simple-beam inference, not FEA. At z 122, the trimmed +y web has about 0.46 of its V1.6 section modulus for forward or back loads. It sits 5 mm above the lower screw, while the unchanged web above has a 19 mm lever arm. For a load at that screw, its stress therefore stays below the upper web's.
- **Screw engagement.** The 2.46 mm engagement of the E-pi-02 M2x4 is about 1.2 screw diameters in printed plastic. Inference: it is enough to hold a 9 g board but weaker under repeated removal.
- **Moving parts not swept.** Jaw motion was not swept against the moved rails. In the closed pose nothing overlaps.
- **Not sliced.** The candidate is not sliced. Both machines need a new slice.
  - Use `pi-positive-y-upper-hole-support-blocker-shifted.stl` for Bambu, in the same frame as the V1.6 blocker.
  - The tie-slot blocker applies unchanged.
- **Guide data changed during this check.** `guide/data/guide-data.json` was regenerated: sha256 e6ebf4d9... when extracted, aafe0927... now. All 92 head parts used here are identical.
  - The camera and speaker screw meshes are now drawn from `fasteners.json`.
  - This check used the full-resolution CAD screw meshes.
  - C-camera_clamp-03 in `fasteners.json` spans the same box: x 74.88 to 80.38, y 15.91 to 19.91, z 145.2 to 149.2.
- **Sweep method.** Sweeps of convex pieces are exact. Sweeps of the non-convex cap material are sampled at 0.25 mm. The re-route search uses a voxel distance field that is conservative by up to about 0.35 mm, and its route is confirmed by exact mesh distance.

## Files

- **This summary:** `/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit/verify-cap/README.md`.
- **Measurements:** `/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit/verify-cap/measurements.json` holds every measurement, the source hashes and the run records.
- **Scripts:** `/Users/xiangzheng/code/robotics/microduck-sim/guide/content/interference-audit/verify-cap/scripts/`.
  - Run `extract.py` first; it writes the head meshes beside the scripts.
  - Then run `inspect1.py`, `inspect2.py`, `inspect3.py`, `study.py` and `DX=4.6 X_TRIM=52.8 build_candidate.py <outdir>`.
  - Then run `DX=4.6 STAGES=AB verify_candidate.py <world stl>` and the same with `STAGES=C`.
  - Then run `extra.py`, `boss_check.py`, `final_pose.py`, `reroute2.py` and `guide_drift.py`.
  - Run each job alone under `build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py --max-mib 1536`. The largest run peaked at 929 MiB.
- **Candidate folder:** `/Users/xiangzheng/code/robotics/microduck-sim/guide/print/candidates/head-cap-pi-shift/` holds four STLs and `manifest.json`. The manifest records the transforms, sha256 values, volumes and required companion changes.
  - `head_cap-pi-shift-world.stl` is in the robot frame.
  - `head_cap-pi-shift-stlframe.stl` is in the release source frame, a drop-in for `guide/print/stl/head_cap.stl`.
  - `head_cap-pi-shift-print.stl` is in the flat V1.6 print pose.
  - `pi-positive-y-upper-hole-support-blocker-shifted.stl` is the shifted Bambu support blocker.
