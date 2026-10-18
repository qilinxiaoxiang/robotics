# MicroDuck V1.9 release geometry: neck route and audio (released 2026-10-13)

## Current state

Released in the V1.9 Orange plate (`../release-V1.9/`, zhengxia_MicroDuck_V1.9_2-files.zip) and integrated in guide-20261013, which passed the print gate (`../../content/interference-audit/gate-receipt.json`). Six printed parts in the robot frame at q = 0, plus one envelope that is not printed. Print poses are in `manifest-ext-v19.json`; every manifest sha256 matches the STL on disk.

- The torso clip (sha 910908747a32) carries one coincident needle-face pair (two 2e-5 mm2 faces with the same normal) that `release-meshcheck-v19.json` flags; it is watertight, one body, manifold3d NoError, and was accepted as printed.
- Shawn chose to try the clips, the retainer and the amp posts as printed (2026-10-13); none has been test-fitted yet.
- The jaw limit stays in software; the clips and wires do not change it.

## Parts (colour Orange for all; Black is the alternative for the retainer and clips)

- `head_cap_v19-world.stl`. sha da655c657979c9290a1aa12d813901062baea2c38c0da31db085c986277976c2, 35303.6 mm3.
  - Replaces the V1.8 cap.
  - Print pose: the V1.8 cap pose, roof on the bed. Bed contact 104.4 mm2.
  - Tip angle 7.7 deg, so print with a 4 mm outer brim (in the manifest overrides).
  - Keeps the V1.8 Bambu support blocker for the E-pi-04 pilot.
- `speaker_retainer_v19-world.stl`. sha 1d0a76b28bf7…, 588.2 mm3. Flat on its speaker-side face, contact 367.6 mm2.
- `clip_torso_v19-world.stl`. sha addaada329c3…, 229.6 mm3. Not clean (blocker 1).
- `clip_bracket_v19-world.stl`. sha a2b796315cc0…, 192.3 mm3. Clean. Rounded mouth corners (r 2.4) and 1.5 mm end
  chamfers.
- `clip_head_v19-world.stl`. sha a800af0d8073…, 426.2 mm3. Clean.
- `clip_cap_v19-world.stl`. sha dc1973a6e640…, 251.8 mm3. Clean.
- Clip print pose: the tab's seat face on the bed, with the screw hole vertical. All rank 1 in
  `checks/orientation-ext-v19.json`.
- `resistor_envelope_v19-world.stl` (envelope only, not printed): 100 kOhm, amp underside, about 4.0 mm stack.

### Fin check (zero-volume fins and internal faces)

`scripts/meshcheck.py` runs these checks:
- watertight, consistent winding, one body;
- 0 edges shared by more than two faces, 0 boundary edges;
- 0 duplicate faces and 0 coincident faces (corners rounded to 1e-4 mm);
- for every face with inradius at least 1e-4 mm, a generalized-winding-number probe at ±1e-3 and ±1e-4 mm on both sides.
  A face that fails at both distances is a fin, an internal face or an inverted face.

The study cap had 39 such faces (6 fins, 13 internal, 20 inverted) and 1 pinched edge. The repair was manifold
`simplify(1e-4)` plus closing one 2-face crack (1 vertex merged at 1.5e-5 mm). Volume change: -0.0012 mm3.

The release cap passes every check above, with 0 separation defects among its non-needle faces. It also has 53 needle
faces with a total area of 0.0045 mm2.

## Screws (changes for content/fasteners.json)

Four rows change. Each screw becomes 2 mm longer because of the 2.0 mm clip tab, so the tip stays where it is today.
The new seat is the old centre moved 2 mm out along -axis.

- S12-horn-025: M2 x 6 → M2 x 8. New centre [20, -20.401, 32.522], axis [0, 1, 0]. Engagement 1.8, tip margin 1.2.
- S11-horn-040: M2 x 6 → M2 x 8. New centre [20, -19.5, 82.421], axis [0, 1, 0]. Engagement 2.6 (2.7 in the
  json), tip margin 0.3 (the same as V1.8).
- E-pi-04: M2 x 6 → M2 x 8. New centre [63.305, 29, 140.548], axis [-0.985, 0, 0.174]. Engagement 4.1, tip margin 1.0.
  The guide text says M2.5 x 8, which does not match.
- H-jaw_support-03: M2.5 x 6 → M2.5 x 8. New centre [42.1, -30, 115.215], axis [0, 0, -1]. Engagement 3.3, tip 5.7.

Four rows are new, all M2 x 6 self-tapping into the cap:
- H-speaker_retainer-01: [3.946, -14.585, 138.992], axis [-0.248, 0, 0.969]. Engagement 4.1, tip 0.595.
- H-speaker_retainer-02: [3.941, 14.6, 138.986], same axis. Engagement 4.1, tip 0.6.
- H-amplifier-01: [24.79, -6.35, 138.23], axis [0, 0, 1]. Engagement 4.15, tip 1.07.
- H-amplifier-02: [24.79, 6.35, 138.23], same axis. Engagement 4.15, tip 1.07.

Counts change from 75 to 79: M2 x 6 43→44, M2 x 8 8→11, M2.5 x 6 4→3, M2.5 x 8 3→4.

The unchanged screws into the V1.9 cap keep their engagement: E-pi-01/03 4.1, E-pi-02 2.15, close screws 4.95.
Nothing bottoms out (`checks/screw-engagement-v19.json`).

## Routes

Source: `route-v19.json`, 33 points, 305.7 mm, group radius 1.7. The radius is an inference: the 8 wires total
12.5 mm2, which is more than a 3.4 mm circle holds.

Proposed changes:
- `routes.json`: `bundle_neck` = points 0-9; `bundle_head` = points 9-32. Replace `head_i2s` and `head_spk` with the
  `audioWires` polylines, and add the `fanWires` polylines.
- `guide-data.json` cables `pi-trunk`, `imu` and `uart`: use `guideCables.<id>.path`.

## Connection methods in plain words (not confirmed by Shawn)

- **Cap.** One part. It uses the same three screws as V1.8. The rear notch and its zip tie are removed.
- **Speaker.** A 1 mm foam ring sits in the roof collar. The retainer frame goes on top with 2 x M2 x 6. No glue.
- **Amplifier.** It hangs on two cap posts with 2 x M2 x 6 up through its holes.
  - Clamp the speaker leads in the terminal before mounting the board.
  - The 100 kOhm GAIN-to-Vin resistor goes on the underside. The board position is unchanged.
- **Pi.** It keeps the V1.8 rails and screws. Only E-pi-04 becomes 2 mm longer.
- **Four clips.** Each is a 2.0 mm tab under an existing screw head plus a channel (4.8 x 4.8 mm, 2.4 mm slot). Press
  the 8-wire group in through the slot. Nothing else holds it. Unclip the group before removing that screw.
  - Torso clip: under S12-horn-025.
  - Bracket clip: under S11-horn-040, on the head-pitch axis.
  - Head clip: under H-jaw_support-03. The group goes down its channel and out through a side window.
  - Cap clip: under E-pi-04, over the Pi top edge.
- **Bundle at the Pi.** Dupont housings: 1x5 on pins 1, 3, 5, (7 empty), 9; 1x1 on pin 2; 1x3 on pins 6, 8, 10.
- **Bundle at the torso.** The UART pair is soldered into OpenRB J12: pad 3 RX from Pi pin 8, pad 4 TX to Pi pin 10.
- **Audio.** Five F-F jumpers from the amp header to Pi pins 4, 12, 34 (GND), 35 and 40.

## Check numbers (before the stop)

- **Cable penetration** (cables.py-equivalent, polyline and drawn spline), all with 0 penetrations:
  - bundle min 0.161 / 0.173 mm;
  - low amp-header variant 0.146 mm;
  - fan wires at least 0.364 mm, audio wires at least 0.754 mm;
  - no new finding on the unchanged guide cables.
- **Final-pose overlap.** No new overlap.
  - The cap against head_bottom is 67.5 mm3, against 63.0 in V1.8. The difference is the notch closure, an intended
    seat band.
  - Seat overlaps of the clips: 0.
  - Clearance from the S12-horn-028 head to the torso clip: 0.28 mm.
- **Cap descent and assembly path.** Excess 0, gap 0.5 mm (the same as V1.8).
- **Cap motion** (`checks/cap-motion-v19.json`): 0 new restrictions.
- **Walking frames.** No overlap for the new parts.
- **Route slack.** Policy 18.5, pickup 12.8, walking 11.4 mm. Lifting the cap needs 17 mm of extra wire.
- **Connector insertion.**
  - Amp housings: plug them before the Pi is mounted (Pi in the way after 3.5 mm).
  - Pi housings: plug them with the cap lifted, as in V1.8 (the face_panel limits them).
- **Head-fixed wires.** No jaw contact up to 40 deg.
- **Resistor.** The underside placement fits. Worst static gap 3.918 mm, worst swept gap 2.788 mm.

## Guide integration

Done in guide-20261013 (steps.py, fasteners.json, routes.json, build_guide_data.py, print/world). The handoff list that drove it is in git-free history only; this folder is now read-only release geometry.
