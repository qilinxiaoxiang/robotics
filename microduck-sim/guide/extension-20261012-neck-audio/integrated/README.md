# Integrated head: audio + Pi rails + neck bundle (extension study, V1.8 untouched)

Problems advanced: P5/P6 (serviceable MicroDuck wiring that survives the trained head motion and the beak-pickup
posture). Study date 2026-10-12. Nothing here is a print file. The 12 V1.8 world files still match
`print/world/v18-sources.json`, and git shows no change under the protected paths (`v18-unchanged.json`).

## Verdict

**The three studies fit together in one head, and the eight-wire neck bundle has a clean route through it.**

- **One cap (measured).** The integrated study cap is the notch-less V1.8 cap plus the audio roof-pair edits and the
  Pi-mount option A rails. It is one closed body. Outside the edited regions it differs from V1.8 by only 0.10 mm³:
  18 slivers of at most 0.013 mm³ each, at the grille edge.
- **+y web trimmed (measured).** The option A +y web now keeps at least 1.05 mm from jaw_support, both at rest and
  while the cap is lowered. Before the trim it was 0.50 mm at rest and 0.45 mm during descent; V1.8's Pi-to-jaw_support
  gap is 1.09 mm.
  - The trim removes 13.5 mm³ and makes the +y side about 11% weaker in the worst push case (1.284 to 1.422 MPa per N)
    and 22% weaker in the web path case (0.671 to 0.820 MPa per N). Both stay far stronger than V1.8 (9.14 MPa per N).
  - The 0.5 mm gap still reported for the +y rail zone is V1.8's own rail back face against jaw_support. The
    integration does not change it.
- **New bundle route A3 (measured).** The coordinator was right that the old route A2 ran through the space the
  amplifier now uses. Route A3 avoids it:
  1. From the -y slot, the bundle goes over the jaw-support cross wall and down to the head clip.
  2. From the head clip, it turns back up behind the Pi and passes under the amplifier's housings.
  3. It crosses the Pi top edge at y 17 to 22 and comes down the +y front edge, outboard of the pin 1 and 2 housings.
  4. At a gather point in front of the header, it fans out to pins 1, 2, 3, 5, 6, 8, 9 and 10.
- **Exact checks pass (measured).** Every new part and wire was checked against the V1.8 head and against each other.
  The checks covered the jaw sweep (0 to 40°), the head-roll sweep (±25°) and the 40 mm cap descent. There are zero
  unintended overlaps.
- **Jaw-open finding: real interference (measured).** In 24 of the 27 beak-pickup postures, opening the jaw to 40°
  drives it into the ID11 or ID12 servo case or the head-pitch bracket. Every hit is a real overlap; none is a near
  miss under 0.2 mm. At head pitch 0, the jaw opens fully when yaw is 0, and opens to 30 to 32° at full yaw.
  - This limit comes from the robot's own geometry. Wiring does not cause it, and it limits the beak-pickup goal
    either way.
- **Connectors soldered onto boards.** J12 on the OpenRB can take a JST PH 4-way top-entry header, and it fits. The
  DFR1202 needs an owner decision. It has edge pads only, so the least-bad option is a small adapter board with a
  6-way screw terminal, which needs two small rear-pack edits.
- **Additions vs V1.8.** Six new printed parts: the speaker retainer and five wire clips. Four new M2 x 6 TAP screws.
  Four existing screws become 1 mm longer. No new screw type: every length is already used in V1.8 (`counts.json`).

## Every connection method

Retention of each part:

- **Integrated cap:** one printed part. It replaces the V1.8 cap and is fastened the same way as V1.8.
- **Speaker:** clamped in a collar printed into the cap, on a 1.0 mm closed-cell foam ring. A printed retainer frame
  holds it down with 2 x M2 x 6 TAP screws into two cap bosses. No glue.
- **Amplifier:** hangs under the roof on two printed cap posts, held by 2 x M2 x 6 TAP screws through the board's
  plated holes. No glue.
- **Pi:** sits on the reinforced rails printed into the cap (option A). It is held by the four V1.8 screws:
  M2 x 6 TAP at E-pi-01 and E-pi-03, M2 x 4 TAP at E-pi-02, and M2 x 7 TAP at E-pi-04 (see the cap clip below).
- **Five bundle clips:** each is a small printed tab with one hole. It sits under the head of an existing screw, and an
  open hook holds the flat wire group. No new hole or boss is added anywhere. The screw gets 1 mm longer, so its tip
  stays where it is today. The clip shape is inference.
  - **Torso clip** under S12-horn-025: M2 x 6 becomes M2 x 7.
  - **Neck clip** under S11-case-094: stays M2 x 10. The tab is at most 1.0 mm thick, or skip this clip (neck-route).
  - **Bracket clip** under S11-horn-040: M2 x 6 becomes M2 x 7.
  - **Head clip** under H-jaw_support-03: M2.5 x 6 becomes M2.5 x 8. It sits on the lower head.
  - **Cap clip** (new in A3) under E-pi-04: M2 x 6 TAP becomes M2 x 7 TAP. It rides on the Pi, which is on the cap.
- **Grille:** holes printed into the cap. Nothing attaches to them.

Ends of each wire:

- **Eight bundle wires, Pi end:** crimped Dupont female contacts in three housings. The odd row uses one 1 x 5 housing
  (pins 1, 3, 5, empty 7, 9). The even row uses a 1 x 1 housing on pin 2 and a 1 x 3 housing on pins 6, 8 and 10.
  - Phase 1's even-row 1 x 5 (pins 2 to 10, with pin 4 left empty) is no longer usable. Its pin-4 position would
    block the amplifier's 5 V jumper on pin 4.
  - All three housings sit beside the five audio housings without overlap (`housing-blocks.json`). The housing blocks
    are built from the V1.8 1-pin housing outlines.
- **Eight bundle wires, torso end:** unchanged from V1.8 at the far end. The two pairs that V1.8 solders to boards get
  connectors (`board-connectors/README.md`):
  - **UART pair at OpenRB J12:** a JST PH contact pair in a PHR-4 housing, plugged into a B4B-PH-K-S header soldered
    into J12. Measured fit: 0.53 mm to the nearest OpenRB component and 2.55 mm to the converter.
  - **Pi supply pair at DFR1202 VOUT/GND:** clamped in a 6-way 3.5 mm screw terminal (Same Sky TB0011-350-06) on a
    small adapter board. The adapter board is soldered to the converter's edge pads. This is an owner decision; see
    "Open items".
- **Five audio jumpers:** female-to-female Duponts. One end goes on the amp's 7-pin right-angle header (soldered to the
  amp by the owner; a connector, allowed). The other end goes on Pi pins 4, 12, 34 (GND, in place of 14), 35 and 40.
  Both ends plug in.
- **Speaker leads:** clamped in the amp's screw terminal. At the speaker they are soldered to its two pads; that joint
  is on the speaker, not on a board. An optional 2-pin JST-PH inline pair lets the speaker unplug.

Wires soldered directly to any board: none, if the J12 header and the DFR1202 adapter are adopted.

## Route A3 in the head, plainly

1. The bundle enters through the Phase-1 -y slot, which is unchanged: 4.41 mm wide, the narrowest point of the whole
   route.
2. From the top of the slot, it goes 27.7 mm over the jaw-support cross wall and down to the head clip
   (H-jaw_support-03). It turns back up there, so the clip holds the bend.
3. It runs up behind the Pi at x 46 to 50, under the amplifier's housings, and crosses the Pi top edge at y 17 to 22,
   z 146 to 148. The cap clip under E-pi-04 sits on this stretch, 77.4 mm after the head clip.
4. It comes down the +y front edge, outboard of the pin 1 and 2 housings. It ends at a gather point 8.9 mm further on
   (x 77, y 27.5, z 115.5).
5. Each wire leaves its housing along the header axis and runs 5.6 to 21.7 mm to the gather point.
   - The fan stays above the head floor and out of the 40 mm column under the camera board and face panel. Those are
     lower-head parts, so it has to stay out of that column while the cap is lowered.
   - The pin 8, 9 and 10 wires cross the audio jumpers of pins 4 and 12 (figure `png/fan-closeup.png`). Wires touching
     wires is harmless. Fitting the bundle housings before the audio housings on pins 4 and 12 is the easier order
     (inference).
6. Lifting the cap: the cap clip moves up with the cap, and the head clip stays on the lower head. The stretch between
   them needs at least 12.1 mm of extra wire (a taut lower bound). Leave about 25 mm (inference). The extra lies along
   the run behind the Pi, where the corridor is about 10 mm wide.
   - Or unplug the three bundle housings and unhook the cap clip before you lift the cap.

## Numbers

Cap (`cap-build.json`, `seat-bands.json`):

- **Body and volume (measured):** one body, genus 53, 35303.6 mm³ (V1.8: 30676.3 mm³). Added vs V1.8: 5054.9 mm³.
  Removed: 427.6 mm³.
- **STL round trip (measured):** after export to STL and reload, trimesh reports 108 edges shared by more than two
  faces, out of 55,726. They are at the Ø1.7 Pi pilots (x 52.8 to 60.9, y 25.8 to 30.6). manifold3d reloads the file as
  one valid body of the same volume. The two sibling input caps already had such edges: 43 (option A) and 118 (audio).
- **Seat bands (measured, intended):** the cap overlaps head_bottom by 67.5 mm³ (V1.8: 63.0 mm³). These are the same
  two 0.2 mm seat bands along the rim. Closing the notch continues them for 4.47 mm³.

Route (`route-search.json`, `route-exact-*.json`, `route-fan.json`, `route-A3.json`):

- **Lengths (measured):** in-head length after the slot is 143.0 mm: 27.7 mm slot top to head clip, then 106.4 mm head
  clip to the front edge, then 8.9 mm to the gather point. Each fan wire adds 5.6 to 21.7 mm. The whole route is
  304.5 mm from the torso tie at q = 0.
- **Narrowest free width on the new spans (measured):** 6.79 mm over the Pi top at (60.2, 20.1, 148.0). This is the
  largest free tube radius 3.39 mm, with the group allowed to shift up to 1.5 mm sideways, checked over every jaw and
  roll pose. The passage is under 7.0 mm wide for 2.0 mm of its length and under 8.0 mm for 8.0 mm.
  - The slot-to-clip span is never narrower than 10.5 mm (radius 5.27).
  - The gather stretch has a grid radius of 3.75 mm.
  - Each fan wire's grid corridor radius is at least 1.16 mm (pin 9). A 26 AWG wire needs 0.65 mm.
- **Sections (measured, worst pose):**
  - Every section passes the 1-pin, 1 x 4 and 2 x 4 Dupont housings and a JST PH 4 housing.
  - A JST PH 8 housing (17.9 mm, nominal) fails the Pi-top section and two sections behind the Pi
    (`connector-fit-A3.json`).
  - The narrowest section still holds 13 parallel 1.7 mm wires within ±8 mm.
- **Clearances, smallest found (measured, `pairwise-scene.json`, `pairwise-pairs.json`):**
  - The group behind the Pi is 0.78 mm from the amp housings and 1.39 mm from the Pi.
  - The fan is 0.15 mm from the pin-12 jumper (wire to wire) and 0.45 mm from the pin-4 jumper.
  - The fan is 0.63 mm above head_bottom during the cap descent and 1.23 mm from the camera board.
  - The fan clears the open jaw by 3.74 mm.
  - The slot-to-clip span stays 1.26 mm from the yaw body over the full roll sweep.
  - Each fan wire is at least 0.36 mm from the other seven bundle housings (`route-A3.json`).
- **Motion, slack and pinch (measured, `checks/motion.json`, `checks/yaw-slack.json`):**
  - Below the head the route is Phase 1's A2, unchanged, so slack is the same: 21.4 mm (policy), 24.0 mm (pickup) and
    34.7 mm (full MJCF ranges). The yaw crossing needs 30.0 mm at ±80° yaw with ±25° roll.
  - The in-head A3 spans keep at least 2.47 mm from the moving yaw body, measured centreline to part surface, in every
    pose set.
  - One lower value, 1.51 mm to shell_left, occurs only at neck -90° with head pitch 90°. The head shell itself
    already overlaps the torso shells in that pose, so the robot cannot reach it.
- **Jaw against the wire spans (measured, `checks/jaw-check.json`):** in every reachable pose, the jaw stays at least
  6.11 mm from the wire group. Zero reachable poses touch it. The jaw already hits neck parts in 78 of 162 policy poses
  and 29 of 54 pickup poses.

Jaw-open pickup check (Task 4, `jaw-pickup.json`; 27 postures: neck -90/-60/-45 x head pitch 0/45/90 x yaw
-24.6/0/34, jaw 0 to 40° in 2° steps):

- **Classification:** a hit is called interference when the overlap is over 0.01 mm³ and contact when the gap is
  under 0.2 mm. At 40°, 24 postures interfere, 0 are contact only, and 3 are clear. Every hit is a real overlap.
- **Head pitch 0:**
  - Yaw 0: clear to 40°, with 1.52 mm to ID11.
  - Yaw -24.6: the jaw underside hits the head-pitch bracket from 34° (31.1 mm³, 5.5 mm deep at 40°).
  - Yaw 34: the jaw underside hits the bracket from 32° (73.8 mm³, 8.6 mm deep at 40°).
- **Head pitch 45:** the jaw underside hits the ID11 case from 32 to 38°, depending on yaw. At yaw 0 it is clear to
  36°. At 40° the overlap is 179 to 327 mm³.
- **Head pitch 90:** the jaw hits the ID12 and ID11 cases after only 4 to 8° of opening. At 40° the overlap is 2440 to
  3167 mm³. At neck -90, three postures are blocked even with the jaw shut, because the head shell overlaps both
  torso shells.
- **Consequence:** a beak pickup with the jaw opening more than about 30° needs head pitch near 0 and little yaw. Any
  of these would lift the limit:
  - a jaw-angle limit tied to head pitch in the policy;
  - a narrower jaw underside;
  - a different pickup posture.
  This is an owner decision, separate from wiring.

Counts (`counts.json`, sources listed per item):

- **New printed parts (6):** the speaker retainer, plus the torso, neck, bracket, head and cap clips.
- **Modified printed part:** the head cap.
- **Removed:** the V1.8 cap-notch zip-tie hood and its zip tie.
- **New screws (4):** M2 x 6 TAP, two for the retainer and two for the amplifier.
- **Longer screws (4):** S12-horn-025 and S11-horn-040 become M2 x 7. H-jaw_support-03 becomes M2.5 x 8. E-pi-04
  becomes M2 x 7 TAP (inference). All these lengths already exist in V1.8 `fasteners.json`.

## Open items

- **DFR1202 connector (owner decision).** There is no through-hole to solder a pin or terminal into. Choose one:
  - an adapter PCB with a TB0011-350-06 block, plus two rear-pack edits: a cover pocket of at least 0.5 mm and the
    converter feet trimmed by at least 0.2 mm each;
  - a lower clamp, which has not been found yet;
  - a converter with through-hole pins.

  Spot check: the numbers in `board-connectors/README.md` match its `fit-results.json` and `dfr-pads.json`.
  DFRobot's product page text gives 30 x 26 x 8 mm and 16 A but does not describe the pad type. The edge-pad finding
  rests on DFRobot's pin image and the repo mesh (`measure_dfr_pads.py`).
- **Jaw against the neck in pickup postures.** See above. Wiring does not cause it.
- **Clip shapes and the E-pi-04 screw length** are inference. Check the hook size on a test print. Check E-pi-04
  thread engagement: the screw grows 1 mm and the 1.0 mm tab sits under its head.
- **Cap-lift slack:** at least 12.1 mm (taut). About 25 mm is suggested (inference). Phase 1 suggested about 30 mm
  for its own route.
- **Unchanged from V1.8 and Phase 1:**
  - the 0.5 mm V1.8 +y rail-to-jaw_support gap;
  - the -y slot (4.41 mm);
  - the Phase-1 pinch notes below the head: the open jaw near the neck spans, and ID13 at yaw beyond ±150°.
- **Mesh hygiene:**
  - the 108 pinched edges at the Pi pilots after STL export;
  - the pi-mount option A "added material" STL is not closed (50 open pieces), so this study uses A minus the audio
    cap instead.
  - Any print release must rebuild the cap from source and pass the assembly-motion print gate.
- **Wires are tubes:** r 1.7 mm for the group and 0.65 mm for each fan wire. Real wires are flexible. The fan
  geometry is a grid corridor, measured exactly after it was found.

## Files and rerun

All scripts are in `scripts/` and run under the bounded runner with `/tmp/microduck-cad-venv/bin/python`. Scratch
files go to `SCRATCH` in `int_lib.py`. Run in this order:

1. `build_cap.py`
2. `jaw_pickup.py`
3. `route_occ.py`
4. `route_search.py A3-slot-to-clip A3-clip-over-top-plus-y` (or no arguments for every scenario)
5. `route_exact.py <scenario>` for the same two scenarios
6. `fan_search.py`
7. `final_route.py`
8. `pairwise.py scene` (optionally with part names), then `pairwise.py pairs`
9. `seat_bands.py`, then `housing_blocks.py`
10. `neck_checks.py motion`, `neck_checks.py jaw` and `neck_checks.py yaw`
11. `connector_fit_a3.py`
12. `counts.py`, `figures.py` and `v18_check.py`

Figures, in `png/`:

- `integrated-side.png`
- `integrated-rear.png`
- `integrated-top.png`
- `fan-closeup.png`

Study solids, in `study-solids/`:

- `head_cap-integrated-world.stl`
- `cap_added_vs_V18-world.stl`
- `web_trim_removed-world.stl`
- `A3_*-world.stl`

None of these is a print file.
