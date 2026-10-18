# Neck route for the 8-wire Pi bundle (extension study, V1.8 untouched)

Problems advanced: P5/P6 (MicroDuck wiring that survives the trained head motion and the beak-pickup posture). Study date 2026-10-12. Nothing here is a print file; V1.8 world files were re-hashed after the study and all 12 still match `print/world/v18-sources.json` (`neck-route-results.json`, `v18FilesUnchanged: true`).

## Verdict

**Feasible, with one change to how the wires are bundled.** The eight wires can run up the -y side of the neck and enter the head from below without changing any part they pass. They must go through as a loose flat group, or as single plug-ended wires. They cannot go through as the 6.7 mm round spiral-wrapped bundle. The only printed change is the head cap without the rear notch and hood. That study solid is built and is identical to the V1.8 cap outside the notch area.

- The narrowest point (measured) is a slot on the -y side of the head, between the yaw link and the jaw support. It is 4.41 mm wide (exact free radius 2.203 mm at x 16.94, y -26.73, z 129.08). In its own plane at z 129.1 it is 4.55 mm wide, and it is long enough for a 12.7 mm long plug housing laid edge-on. With the head at rest it fits 18 parallel 1.7 mm wires; the bundle has 8.
- A round 6.7 mm bundle does not pass any way into the head (measured). Even with the servo cables ignored, the widest way in is 6.30 mm. That gap is on the +y side, and the ID11-to-ID13 servo cable already runs through it.
- Compared with the external loop, the inside route needs much less spare wire (measured, taut-line model): 21.4 mm instead of 61.5 mm over the walking-policy range, and 24.0 mm instead of 79.3 mm over the beak-pickup set.
- An inline 2 x 5 plug pair below the head does not fit (measured). The Pi header itself works as the disconnect. Two 1 x 5 Dupont housings pass the slot edge-on with the head at rest, so the head can come off without cutting or desoldering anything.

## Recommended option: inside route A2 (-y side, clips beside the joint axes)

**How the wires run** (points in `route-candidates.json`, route `A2-minus-y-clips`; figure `png/route-overlay.png`, black line):

1. The wires leave the torso at the V1.8 top-rear notch, which is unchanged. They then cross the shell top to the -y shoulder ear beside the neck-pitch pivot.
2. **Torso clip** under screw S12-horn-025. This M2 x 6 screw holds the right shell to the ID12 idler, about 6 mm from the neck-pitch axis.
3. Up the outside of the -y neck link to a **neck clip** under screw S11-case-094. This M2 x 10 screw holds the link to the ID11 case.
4. Up to a **bracket clip** under screw S11-horn-040. This M2 x 6 screw holds the -y plate of the head-pitch bracket to the ID11 idler, 6 mm from the head-pitch axis.
5. Up the bracket plate, between the bracket top and the ID13 case, through the floor opening of the lower head shell, then up the -y channel. The channel runs between ID13 and the lower-shell collar and is 7.2 to 7.4 mm wide at rest.
6. Through the 4.4 mm slot, over the jaw support, to a **head clip** under jaw-support screw H-jaw_support-03 (M2.5 x 6). From there the wires go forward over the Pi top edge to the header, pins 1, 3, 5, 9, 2, 6, 8 and 10.

**How the wires are fixed, in plain words.** Each clip is a small separate printed tab with one 2.2 mm (M2) or 2.7 mm (M2.5) hole. It sits under the head of an existing screw, and an open hook on the tab holds the flat group, so no hole or boss is added to any existing part. Because each clip adds its thickness under the screw head, that screw gets 1 mm longer: M2 x 7 at S12-horn-025 and S11-horn-040, and M2.5 x 8 at H-jaw_support-03. Measured from `fasteners.json`, those holes have 1.2 mm, 0.3 mm and 5.7 mm of depth beyond the current screw tip, so the longer screw keeps today's thread engagement. S11-case-094 goes into the ID11 servo case, whose hole depth is not recorded. Keep M2 x 10 there with a clip no thicker than 1 mm (engagement 3.2 mm drops to about 2.2 mm), or skip the neck clip; see "Slack" below. Clip shape and screw lengths are inference; check them before printing.

**Plugs.** Every wire ends in a crimped Dupont female contact. On the Pi, the contacts go into two 1 x 5 housings:
- Odd row, pins 1, 3, 5, empty 7, 9: the IMU wires.
- Even row, pins 2, empty 4, 6, 8, 10: Pi power and UART. Pin 4 (5 V) stays in an empty housing position.

Single black sleeves, as in V1.8, also work and thread the slot one at a time. No wire is soldered to a board at the head end. Out of scope but relevant to the owner's new rule: in V1.8 the Pi pair is soldered to the DFR1202 VOUT and GND pads, and the UART pair to OpenRB J12 pads 3 and 4 (`steps.py`, steps `dfr-leads` and `uart-wires`). Those torso ends would need plugs too.

**Slack** (measured, `motion.json`, `yaw-slack.json`). Each span between two clips crosses only the joints between them. Leave this much extra wire in each span:
- Torso clip to neck clip (crosses neck pitch): 2.3 mm over the policy range, 6.8 mm at neck pitch -90. Because both ends are near the pivot, no loop is needed; 10 mm of extra wire is enough.
- Neck clip to bracket clip (crosses head pitch): 6.0 mm over the policy range, 6.9 mm at head pitch 90. 10 mm of extra wire is enough. Without the neck clip, this span and the one before it share about 12 mm.
- Bracket clip to head floor (crosses head yaw and roll; the only span that needs a real loop): 13.1 mm over the policy range. With head roll up to +-25 deg it needs 18.3 mm at yaw +-35, 30.0 mm at +-80 (the hand-turning limit in the V1.8 guide), 32.3 mm at +-90 and 40.4 mm at the full +-170. Leave 35 to 40 mm.

**Clearance to moving parts** (measured):
- **Jaw and beak pickup.** In every reachable pose of the policy and pickup sets, the jaw stays at least 6.1 mm from the neck-side wire group. The group is modelled as a 1.7 mm radius tube; this holds with the jaw at 0 and at 40 deg open (`jaw-check.json`). The wires do not limit the bend-forward pickup posture.

  In 78 of 162 policy-box poses and 29 of 54 pickup-box poses, the open jaw (40 deg) already comes within 0.2 mm of the ID11 or ID12 case or the bracket. That limit exists without any wiring and may come from the corner combinations in the pose boxes. It deserves its own check.
- **Bracket plate run.** Where the group runs up the bracket plate (z 82 to 95, 3 mm outboard of the plate), the lower head shell comes within 0.51 mm of the wire centreline at roll -21.4 deg. A 1.7 mm wire would just touch it. Keep the group flat against the plate, beside the screw heads.
- **Yaw crossing.** The straight span from the top of the bracket plate to the floor opening runs along the bottom edge of the ID13 case: centreline 0.06 mm from it over the policy range. In 45 of 162 policy poses the straight line passes through the bracket top edge or the ID13 case. In practice the group will rest and slide on those edges as the head turns (inference). Put a 30 mm heat-shrink or PTFE sleeve over the group there.
- **Space for the yaw loop** (`loop-space.json`, every policy pose, 1 mm grid). The always-free space within 6.5 mm of the bracket plate allows a sphere of radius 2.8 to 3.2 mm at z 80-96. It allows 5.0 to 5.7 mm at z 96-104, which is the gap under the head floor and inside the floor opening. So the loop must lie flat: an arc around the yaw axis in the gap under the head floor, or an S-fold inside the head channel. A loose round loop hanging beside the bracket would be reached by the head shell when the head rolls (inference from these numbers).
- **Inside the head** (`sections.json`). Over the policy roll range (-21.4 to 9.9 deg) the slot is narrowest at rest: 4.55 mm. It widens at other rolls: 5.65 mm at -5 deg and 7.95 mm at -21.4 deg. Head yaw does not change it, because both walls move together above the yaw joint. The channel below is never narrower than 6.49 mm (z 110, roll -10). The space over the Pi top is 8.19 to 8.55 mm with the notch-less cap.

**Assembly order** (inference):
1. Put each clip under its screw in the step where that screw goes in today: shells, neck-lower-fasten, neck-upper-join, and the jaw-support step.
2. In the bundle chapter, with the head on the neck, the cap off and the power off, roll the head about +5 to +10 deg by hand. The slot then opens beyond 20 mm.
3. Feed the crimped contacts, still without housings, up through the floor opening, the channel and the slot. Press the group into the clips, insert the contacts into the two 1 x 5 housings, and plug the housings onto the header.
4. Close the notch-less cap.

**Removing the head for service** (inference):
1. Take the cap off.
2. Unplug the two housings and lift the group out of the head clip.
3. Pull the wires down out of the head. The 1 x 5 housings pass the slot edge-on at rest (measured), and a 2 x 5 needs the head rolled at least +5 deg.
4. Remove the head as in V1.8. The torso, neck and bracket clips stay in place.

To lift the cap only, leave about 30 mm of extra wire between the head clip and the header.

**Look.** About 60 mm of flat wire group is visible on the -y side of the neck, from the shoulder ear to the head. It runs beside the servo cable that already sits there. The rear cable loop, the cap notch and its zip-tie hood are gone (inference).

## Other options considered

**Inline 8-way plug below the head (rejected, measured).** I searched every position flat against the bracket's -y plate for a mated 2 x 5 Dupont pair. The envelope was 35 x 13.7 x 6.1 mm: 28 mm mated, 3 mm wire exit at each end, 0.5 mm clearance. 81 positions are free with the robot at rest. All 8 checked positions nearest the head-pitch axis collide over the policy poses (`disconnect.json`):
- Six positions beside the plate meet the lower head shell or the jaw in 99 to 135 of 162 policy poses. These collisions include poses with the jaw closed.
- The two lowest positions, beside the neck link, overlap in 26 poses. Every recorded example has the jaw open.

The Pi header used as the disconnect does the same job and needs no extra space. If an inline plug is still wanted, place it in the head's upper compartment, not tested here. The neck-side 2 x 5 male housing then passes the slot with the head rolled at least +5 deg (measured, `connector-fit.json`).

**Route B, the +y gap behind the jaw servo (not recommended, measured).** The slack is similar: 25.0 mm over the policy range and 40.7 mm over the pickup set, with ties away from the axes. But the gap is shared with the moving ID11-to-ID13 servo cable. It is 4.55 mm at rest and 4.25 mm at roll -5. Only 1-pin and 1 x 2 Dupont housings thread it at rest.

**Keep the round 6.7 mm bundle inside (not built).** The slot would have to grow from 4.41 mm to at least about 7.2 mm. The jaw-support wall on the outer side of the slot is only about 2 mm thick (section figure), so most of the material would have to come off the head yaw link. The channel at z 106-110 would also need about 0.5 mm more. I built no study solid for this, because the flat-group form passes with no part change.

**Keep V1.8 as is (external loop).** It needs 61.5 mm of slack in the taut model over the policy range and 79.3 mm over the pickup set. The V1.8 guide uses a 130 mm loop and a 207 mm path length.

## Measurement and inference

- **Measured:** every number in this README comes from the scripts below. They use the closed interference-audit solids, the MJCF kinematics, the walking-policy trace ranges and the guide's cable paths. Existing servo cables and the camera ribbon count as obstacles at their guide radius.
- **Inference:** these are marked in the text. They include the clip shapes, screw-length choices, sleeve, loop layout, assembly and service order, look, and plug outlines other than the Dupont pitch. The path from the slot to the head clip was checked only for free space above the screw head, on the 0.5 mm grid with the head at rest. Wire diameters are 1.7 mm for 22 AWG silicone and 1.3 mm for 26 AWG. The JST outlines are nominal and must be checked against the bought part.
- **Limits:** the slack and clearance model uses straight taut spans between clip points, so it is a lower bound on wire length. Section widths come from an 18 mm window and 0.05 mm raster. The capacity counts are greedy lower bounds. The policy pose set is a 3^4 box over the trace ranges, times jaw 0 and 40 deg. Its corners may be stricter than real motion.

## Files and rerun

All files are under `microduck-sim/guide/extension-20261012-neck-audio/neck-route/`.

**Results:**
- `neck-route-results.json`: all headline numbers, the script list and the V1.8 hash check.
- Per-script JSON: `corridors.json`, `sections.json`, `motion.json`, `yaw-slack.json`, `jaw-check.json`, `connector-fit.json`, `disconnect.json`, `loop-space.json`, `kin-check.json` and `nonotch-cap.json`.

**Study solid:** `study-solids/head_cap-no-notch.stl`. Outside the notch edit box it differs from the V1.8 cap by 0.0 mm³ (XOR). It restores 166.3 mm³ of notch material and removes 199.4 mm³ of hood. It is watertight and one body. It is not a print file.

**Figures:** `png/narrowest-sections.png`, `png/route-overlay.png` and `png/channel-profile.png`.

**Scripts, in rerun order:**
1. `make_nonotch_cap.py`
2. `occ.py`, then `occ.py cables`
3. `corridor_search.py` with and without `cables`
4. `corridor.py` with and without `cables`
5. `kin_check.py`
6. `sections.py`
7. `motion.py`
8. `yaw_slack.py`
9. `jaw_check.py`
10. `connector_fit.py`
11. `disconnect.py`
12. `loop_space.py`
13. `figures.py`
14. `results.py`

Shared helpers are in `nr_lib.py`. Run the geometry jobs under `build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py --max-mib 1400`; every completed job peaked below 1.25 GB. The occupancy grids, search results and section rasters are written to the session scratch folder (`NR_SCRATCH`).
