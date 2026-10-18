# MicroDuck head audio extension study (speaker + amplifier back into the V1.8 head)

Problem IDs: P5 (head integration), P6 (build and assembly). Study date 2026-10-12. This is a measurement and options study. It contains no release print files, and V1.8 is unchanged. All coordinates are in the robot frame, in mm: x forward, y left, z up.

## Verdict

The speaker and amplifier fit back into the V1.8 head if both move up under the roof. Their old positions do not work: the old speaker, cradle and keeper collide with the head-yaw link when the head rolls.

The recommended "roof pair" layout has three parts:

- **Speaker.** It lies under the rear-top roof, tilted 14.3° to follow the roof. It is held by a collar printed into the cap, a 1 mm foam ring and one printed retainer frame with 2 × M2×6 TAP screws.
- **Amplifier.** It hangs flat under the roof between the speaker and the Pi, with components facing up. It is held by 2 cap posts and 2 × M2×6 TAP screws. A right-angle 7-pin header points its Dupont housings forward, toward the Pi.
- **Grille.** A mirror-symmetric grille of 52 × Ø1.8 holes in the roof sits directly over the speaker. Nothing else on the outside changes.

The exact manifold3d checks pass with zero failures:

- no unintended overlap, statically or during head roll ±25°, jaw 0–40° or the 40 mm cap-on descent;
- no added material outside the V1.8 cap hull or in its exterior grooves;
- no material removed except the grille holes and the blind screw pilots.

Every wire ends in a plug or clamp. The only soldered wire ends are the two speaker leads, which are soldered to the speaker's own pads. No wire is soldered to any board.

Three items still need physical confirmation (see Open items):

- the terminal-block height, which is unpublished and assumed to be 10 mm;
- the foam gasket material;
- where the slack of the speaker leads and the jumpers is stowed.

## What is measurement and what is inference

- **Measured (exact geometry):** every clearance, overlap, sweep, descent, volume and bound in this README. The sources are the V1.8 audit solids and the study solids, checked with manifold3d booleans, min_gap and trimesh ray casts.
- **From datasheets (verified 2026-10-12):** part dimensions, ratings, pinout and the gain table. See Sources.
- **Assumed:** the terminal-block envelope is 7.2 × 8.0 × 10 mm (height unpublished). The foam is 1.0 mm thick, compressed to 0.6 mm. Wire tubes are r 0.7 mm for jumpers and r 0.6 mm for speaker leads.
- **Inference (not measured):** every acoustic number (resonance, "does not throttle speech"), the SD-pin mono mode and the power/clipping numbers at each gain.

## Old positions re-checked first

These are the pre-V1.8 audio parts at their old positions, checked against V1.8 (`old-positions-recheck.json`).

**Speaker side** (old position at y −31.6 to −11.4, z 131–137):

- The speaker overlaps head_yaw_link by 335 mm³ at 19° head roll.
- The cradle overlaps it by 84.9 mm³ at 15° roll.
- The keeper overlaps it by 49.3 mm³ at 25° roll.
- Static and cap-descent checks are clean.
- Conclusion: the speaker cannot go back there.

**Amplifier side** (old position at z 132.5–134.1, x 17.1–34.9, y 14.75–33.8):

- The board is clean statically and during roll, with a 6.5 mm gap.
- It sits about 0.12 mm inside the 3 mm keep-out around the head cable bundle (bundle_head).
- The roof above it leaves only 1.5–6.5 mm. A 14 mm Dupont housing standing up from the header cannot fit there.

**The four removed posts** (listed in `guide/print/cap-no-audio/remove_audio_posts.json`) are themselves clean, with a 4.97 mm roll gap. They are not reused, because the parts they carried must move.

## Where there is room (free-space map)

The source is `freespace.json` and `png/freespace-under-roof.png`: a 0.5 mm voxel screen of the space under the roof. Head roll and jaw are swept, and the CSI and bundle cables are reserved.

- **Top centre, x 15–45:** the roof's underside is at about z 149.5–153. Over |y| ≤ 10, the swept yaw body reaches up to z 135.
- **Strip at x 40–52:** about 16.5 mm free height.
- **−y side:** only about 7 mm. The yaw-body sweep rises to z 138 near y −16.5.
- **+y side over motor15:** 17–20 mm, but the head cable bundle runs there.

Placement candidates:

- **Old positions:** rejected because of the roll collision.
- **−y side under the roof:** rejected; 7 mm is not enough for the speaker plus its keeper.
- **+y side over motor15:** rejected; it competes with the bundle.
- **Roof pair (recommended):** the speaker goes under the rear roof (x −11.6 to 18.1), where the roof slopes and leaves room for a tilted 4 mm speaker. The amplifier takes the flat top-centre strip (x 22.25–41.3). The amp housings run forward into the 16.5 mm strip.

## Recommended layout, with numbers

Sources: `study-build.json` and `study-checks.json`. Sections are in `png/study-section-*.png`.

**Speaker** (Same Sky CMS-30204-18SP, 30 × 20 × 4.0 mm):

- Front-face centre [2.93, 0, 142.96], long axis along x, tilted 14.3° to match a plane fitted to the roof.
- Speaker to the cap pocket wall: 0.2 mm (a deliberate locating fit).
- Speaker to head_yaw_link at worst roll: 7.03 mm.
- Speaker to the head bundle centreline: 15.2 mm.

**Collar printed into the cap** (2,765 mm³ of added cap material, all inside the cavity):

- A ring wall (2.0 mm thick, 0.2 mm clearance around the speaker).
- A 1.5 mm lip that the foam ring presses against.
- A filler plate that leaves a 1.0 mm front gap.
- Two Ø5.2 screw bosses at ±14.6 mm across the speaker.
- Clearances: added material to head_yaw_link at worst roll 4.89 mm; collar to amplifier 1.59 mm.

**Retainer:** a 1.6 mm printed frame that presses the speaker back onto the foam.

- Retainer to head_yaw_link at worst roll: 4.66 mm.
- Retainer to amplifier: 1.80 mm.
- Retainer to the bundle centreline: 8.44 mm.

**Amplifier** (Adafruit 3006, 17.78 × 19.05 × 1.57 mm board):

- Spans x 22.25–41.3, y ±8.89; board top at z 139.8; components face up toward the roof.
- Two Ø4.0 posts come down from the roof through the board's Ø2.5 holes at (24.79, ±6.35).
- Board (including screw heads) to head_yaw_link at worst roll: 2.09 mm.
- Terminal block to the cap: 0.71 mm with the assumed 10 mm block. This is the tightest open number.

**Header and housings:**

- Right-angle 7-pin header, using the Sullins drawing: pin centreline 4.02 mm above the board, 5.84 mm mating length.
- The Dupont housings run x 42.53–56.53.
- Housing ends to the Pi: 3.47 mm. Housings to the cap: 5.71 mm.
- Housings to the yaw body: 8.0 mm or more (the screen limit).

**Pi-end housings** on pins 4, 12, 14, 35, 40:

- Each engages only its own pin; there is no overlap with any other Pi-group solid.
- Jaw sweep: 4.70 mm or more (pin 35 is closest).

**Blind screw pilots** (Ø1.7 holes, the screw holes printed into the plastic): every pilot leaves solid roof between its tip and the outside.

- Speaker bosses: 2.66 mm of roof beyond each pilot tip.
- Amp posts: 7.13 mm beyond each pilot tip.

**Exterior:**

- Added material outside the V1.8 hull: 0. Added material in exterior grooves: 0.
- Removed material: 228 mm³, which is the grille holes plus the inner ends of the screw pilots.
- Material removed outside the intended cuts: 0.
- Images: `png/study-exterior-top.png`, `png/study-exterior-rear-left.png`.

**Wires** (`wires.json`, `wire-routes.json`): a centreline screen of tubes, with the yaw body tested at five roll angles.

- All routes are clear by 0.57 mm or more.
- Cap-on descent with the wires: zero overlap.
- On the pin 14 route, the closest approaches are 0.70 mm to head_bottom and 0.78 mm to the camera board.
- Route lengths:
  - pin 4 (5 V): 48.9 mm
  - pin 35 (LRCLK): 50.7 mm
  - pin 40 (DIN): 54.6 mm
  - pin 12 (BCLK): 69.8 mm
  - pin 14 (GND): 66.2 mm
  - pin 34 (GND alternative): 54.0 mm
  - speaker leads, straight: 8.5 mm

## Space the audio occupies (for the neck-route study)

Source: `occupancy.json`. Exact bounds of every part are listed there.

**Above z 135, under the roof:** the speaker, collar, retainer, amplifier, amp housings and amp posts. Together they span x −14.5 to 56.5, y ±18.2, z 134.7–150.9. The jumpers then cross over the Pi's top edge at x 56–68, y −20 to 18, z 135–148.

**Below z 135:** only two things.

- The five Pi-end housings on the header, x 59.5–74.4. Even pins: z 115.3–120.3. Pin 35: z 112.8–117.8.
- The five jumper drops in front of the Pi, x 66.8–77.1, between the housing ends and the face plate.

**Shared lane:** the pin 12 and 14 jumpers duck under the camera at z 111.9–114.6, x 75.7–77.1, y 8.2–17.0. A bundle that arrives from below at the housing ends would have to share that lane. Using GND on pin 34 (recommended below) leaves only the pin 12 jumper in it.

**Free corridor:** the corridor from the head bottom up to the header pins is free. Audio adds nothing behind the Pi (x < 59) or anywhere below z 111.9.

**Neck-route cap:** the neck-route study's notch-less cap (`../neck-route/study-solids/head_cap-no-notch.stl`, read-only) has 0 mm³ overlap with the audio cap additions and with every audio solid.

## Amplifier header, housings and mounting

**Header direction:**

- **Straight header:** does not fit. Housings standing up from the board need 14 mm plus a wire bend. Above the board there is only about 10–13 mm (z 139.8 to the roof at about 149.5–153).
- **Right-angle header pointing +x (recommended):** fits, with the housing ends 3.47 mm short of the Pi.

**Header order** on the board (from the Adafruit .brd file): LRC, BCLK, DIN, GAIN, SD, GND, Vin. The pins that are plugged:

- LRC to Pi pin 35 (GPIO19)
- BCLK to Pi pin 12 (GPIO18)
- DIN to Pi pin 40 (GPIO21)
- GND to Pi pin 34 (recommended) or pin 14
- Vin to Pi pin 4 (5 V)

GAIN and SD stay unplugged (see Gain). The housing envelope also reserves the GAIN and SD positions.

**GND pin choice:** use pin 34, or pin 39, rather than pin 14. Pin 14 sits behind the camera board. Its jumper must duck under the housing ends with 0.70 mm to head_bottom and 0.78 mm to the camera, and it shares the lane described above. The screened pin 34 route is clear by 0.61 mm, has 4.5 mm descent margin and stays out of the camera's shadow (y −9.6 to 14.3). The pin 34 housing itself was not built as a solid. Its fit is inferred from pins 35 and 40, which bracket it and pass. BCLK has to stay on pin 12, because GPIO18 is the Pi's only PCM clock pin.

**Mounting options:**

- **Two cap posts with M2×6 TAP screws from below (recommended).** Posts are Ø4.0 with Ø1.7 pilots, and the screws go through the board's plated Ø2.5 holes. The board top seats on the post ends. The amp is removable with two screws, and no new screw type is needed.
- **Slot or clip rail printed into the cap.** No screws, but the board edges carry parts and pads, and a clip that holds through head shocks needs more space beside the 0.71 mm terminal block. Not pursued.
- **Back at its old place.** This is the only place the old posts reach, and there housings cannot fit (see above). Rejected.

## Speaker keeper options

**K1: relocated two-piece cradle and keeper** (the old design, moved under the roof).

- Pros: proven idea; the speaker sits on a flat plate.
- Cons: the roof is sloped, so the flat plates need tall posts. That is two printed parts and four M2.5×8 screws in a space where the retainer already sits only 4.66 mm from the yaw body. The old version is the one that collided during roll.
- Not built.

**K2: collar printed into the cap, foam ring and screwed retainer** (recommended; built and checked).

- The cap carries the ring wall, lip and two bosses. The speaker drops face-down into the collar onto a 1.0 mm closed-cell foam ring. The 1.6 mm retainer frame presses it in with 2 × M2×6 TAP.
- Pros: one extra printed part and two screws of an existing type. The front is sealed against the grille, so the speaker's rear wave cannot leak around to the front. No glue. It comes apart with two screws.
- Cons: the collar is printed into the cap, so changing it means reprinting the cap. The foam thickness sets the seal.

**K3: slide-in dovetail rail** (not built).

- The cap carries two 45° dovetail lips, which print without supports with the roof on the bed. A printed tray holding the speaker slides in along the speaker's long axis and stops against one M2 end-stop screw.
- Pros: one screw.
- Cons: sealing depends on sliding tolerance, so it needs a foam or wiper detail. The slide path needs about 30 mm clear at one end. The amp sits 1.6 mm from that end, and the other end runs into the curved rear roof. More fit-sensitive, with no clear gain over K2.

## Grille proposal

**Recommended grille:**

- **Location:** the rear-top roof, directly over the speaker.
- **Holes:** 52 holes, Ø1.8 mm on a 2.7 mm hex pitch, in a pattern mirrored about y = 0. They cover x −10.8 to 17.9, y ±10.0.
- **Hole direction:** each hole runs along the speaker's front normal, 10° from the print z axis.
- **Print orientation:** the cap prints roof-down, so the holes print as near-vertical round holes with no supports. The collar walls and bosses grow straight up from the roof.
- **Open area (measured):** 132.3 mm². That is 1.23× the speaker's own front-grille open area (about 108 mm², scaled from the datasheet drawing) and 33% of the chamber opening.
- **Roof thickness along the hole axes:** 4.1–5.2 mm.

**Front chamber** (measured): 634.6 mm³ of air between the speaker face and the filler plate (1.0 mm front gap). The head air behind the speaker is about 222,000 mm³ (222 cm³). The datasheet says "Enclosure Recommended"; the head cavity acts as that enclosure.

**Acoustics (inference, lumped Helmholtz model, no measurement):**

- The grille plus the front chamber resonate at about 9.9 kHz. That is just above the speaker's 10 kHz upper band edge and well above speech.
- The grille open area is larger than the speaker's own grille. Neither should throttle speech.

The variants, rerun with the same scripts (`acoustics-*.json`):

- **Front gap 2 mm:** 8.5 kHz.
- **No filler plate:** 8.3 kHz.
- **Ø1.7 holes:** 9.6 kHz.
- **Ø2.0 holes:** 8.8 kHz.

The 1 mm filler plate keeps the resonance highest, which is why it is recommended. The Ø1.8 holes balance resonance against the risk of tiny holes closing up in print.

**Alternatives considered:**

- **A side "ear" grille:** its holes would be horizontal in print, so they print poorly, and a grille on one side only looks lopsided.
- **Under the head:** crowded and muffled by the neck.
- **Behind the eyes:** crowded by the camera and face parts.

The symmetric top grille sits on the head's centreline and reads as a deliberate feature (`png/study-exterior-top.png`).

## Gain and volume (solder-free)

**Gain table** (MAX98357A datasheet; each setting ±0.6 dB):

- GAIN through 100 kΩ to GND: 15 dB
- GAIN to GND: 12 dB
- GAIN unconnected: 9 dB (the Adafruit default)
- GAIN to VDD: 6 dB
- GAIN through 100 kΩ to VDD: 3 dB

Tying GAIN straight to VDD with no resistor is a documented setting. At 5 V into 8 Ω, the datasheet gives 1.8 W at 10% THD and 1.4 W at 1% THD. The speaker is rated 1.0 W typical and 1.2 W maximum.

**Recommended: leave GAIN unconnected (9 dB) and set a software ceiling.**

- This needs no parts, no solder and no extra jumper.
- **Software ceiling** (inference from the datasheet output formula): cap the digital level at −3 dBFS. At 9 dB gain, a full-scale sine reaches 1.0 W at −2.1 dBFS and 1.2 W at −1.3 dBFS, and it starts to clip near 0 dBFS. −3 dBFS keeps a sine under 1 W with margin.
- **Implementation:** an ALSA softvol control whose maximum is set below 0 dB (its `max_dB` option), or a fixed scale in the playback code. Untested here.
- **Speech:** with ordinary speech peaks 12–15 dB above the average, the average power stays far below 1 W. Clipping is the real limit, not heating (inference).

**6 dB alternative:** tie GAIN to 5 V. A full-scale sine is then about 0.81 W, so no software ceiling is needed (inference). This cannot be a plain female-to-female jumper from GAIN to the amp's Vin pin. Vin already carries the housing from Pi pin 4, and a header pin takes only one housing. Use a 1-to-2 female "Y" Dupont jumper from Pi pin 4 to both Vin and GAIN. Pi pin 2 is the other 5 V pin, and it is already used. This needs a purchased Y jumper or one extra crimp.

**SD stays unconnected.** Adafruit's 1 MΩ pull-up on a 5 V supply puts SD at about 0.42–0.49 V. That selects the mono (left + right)/2 mode (inference from the datasheet SD thresholds 0.16 / 0.77 / 1.4 V).

## Every connection method

1. **Speaker to cap:** clamped by the K2 retainer frame with 2 × M2×6 TAP screws into the collar bosses. It sits on a 1.0 mm closed-cell foam ring, compressed to 0.6 mm. No glue.
2. **Amplifier to cap:** 2 × M2×6 TAP screws from below through the board's plated Ø2.5 holes into two Ø4.0 cap posts. No glue.
3. **Amplifier header to board:** a 7-pin right-angle male header, soldered by the owner. This is a connector soldered to the board, which is allowed.
4. **Amp to Pi (signals and power):** five female-to-female Dupont jumpers. One end of each plugs onto the amp header (LRC, BCLK, DIN, GND, Vin); the other plugs onto Pi pins 35, 12, 40, 34 (or 14) and 4. Plug-in at both ends.
5. **Speaker leads at the amp:** stripped wire ends (ferrules optional) clamped in the amp's 2-pin 3.5 mm screw terminal. This end is removable with a screwdriver.
6. **Speaker leads at the speaker:** soldered once to the speaker's two solder pads, then strain-relieved past the retainer notch. This joint is on the speaker, not on a board.
7. **Speaker leads, optional inline plug:** a 2-pin JST-PH pigtail pair between the speaker and the terminal block. One side's leads are soldered to the speaker pads; the mating side's leads are clamped in the terminal. The speaker then unplugs without a screwdriver.
8. **GAIN and SD:** not connected (recommended). The 6 dB option uses one Y Dupont jumper, as described above.
9. **Grille:** holes printed into the cap. Nothing attaches to it.

Screws: 4 more M2×6 TAP, the most-used screw type already in `fasteners.json`.

## Every solder joint

All joints are made by the owner.

- **On the amp board (connectors only):**
  - the 7 joints of the right-angle header;
  - the 2-pin terminal block: pre-soldered on Adafruit units shipped since 13 June 2024; otherwise 2 joints.
- **On the speaker (wire ends):** 2 joints, one lead to each speaker pad.
- **Wires soldered to any board:** none.

## Assembly order (bench, cap upside down)

1. Solder the header to the amp, and the terminal block if your unit needs it. Solder the two leads, about 40–60 mm long, to the speaker pads.
2. Lay the foam ring in the collar. Set the speaker face-down in the collar, with the pad end toward the amplifier. Fit the retainer and drive its 2 × M2×6 TAP screws.
3. Clamp the speaker leads in the amp's terminal block while the amp is still loose. The terminal screws face the roof, and there is no access once the amp is mounted (0.71 mm to the cap).
4. Fold the lead slack. Seat the amp on its posts and drive 2 × M2×6 TAP from below.
5. Plug the five Dupont housings onto the amp header.
6. Plug their other ends onto Pi pins 4, 12, 35, 40 and 34. Route them over the Pi's top edge and down in front of the Pi.
7. Lower the populated cap as usual. Every audio part and wire is cap-mounted and rides with it. The descent check is clean.

## Open items (need the physical parts)

- **Terminal-block height (resolved 2026-10-13).** Adafruit's 2-pin 3.5 mm terminal block (product 724) links the 4UCON drawing 19963: body 8.5 mm above the board, 7.0 mm deep, 7.8 mm wide (https://cdn-shop.adafruit.com/datasheets/19963.pdf). That the 3006 ships with this block is inference; Adafruit's 3006 CAD model (Adafruit_CAD_Parts) omits it. With 8.5 mm the gap to the roof is about 2.2 mm instead of the 0.71 mm computed for the 10 mm envelope; no owner measurement is needed.
- **Foam gasket.** Choose a 1.0 mm closed-cell, non-adhesive foam on hand, and cut it to the 30 × 20 speaker outline with a 1.5 mm wide ring.
- **Slack stowage, not screened.** The speaker leads need 40–60 mm, so they can be clamped with the amp held out of the cap. They will loop between the speaker's pad end and the amp. Stock 10 cm jumpers leave 30–50 mm of slack each over the Pi top edge; crimped jumpers of about 75 mm would avoid most of it. Confirm the loops on the real build, away from the yaw body and the head bundle.
- **Clearances to the assumed bundle.** The head bundle is modelled as 3 mm around its route centreline. The pin 12 Pi-end housing is 0.68 mm from that assumed envelope.
- **Physical fit of the K2 collar.** The 0.2 mm speaker pocket clearance needs a print test before release geometry is made.
- **Pi-side audio setup and power.** The I2S software setup and the 5 V supply headroom (a few hundred mA from 5 V at 1 W output, inference) are outside this geometry study.

## Sources (accessed 2026-10-12)

Local copies are in the scratchpad `sources/` folder of this study session.

- **Same Sky CMS-30204-18SP** product page, and datasheet `cms-30204-18x.pdf`, rev 1.0, 06/11/2026: https://www.sameskydevices.com/product/resource/cms-30204-18x.pdf. Dimensions, front grille, rear vents, pad notch, 8 Ω, 1.0 W / 1.2 W, Fo 700 Hz, 98 dB at 1 W / 10 cm, "Enclosure Recommended".
- **Adafruit 3006 product page:** https://www.adafruit.com/product/3006. Pre-soldered terminal block since 13 June 2024; header ships loose.
- **Adafruit board files:** https://github.com/adafruit/Adafruit-MAX98357-I2S-Amp-Breakout. Board outline, holes, header order and the 3.5 mm terminal footprint.
- **Analog Devices (Maxim) MAX98357A/B datasheet.** Gain table, output-level formula, power at 5 V, SD thresholds.
- **Sullins right-angle male header drawing** (xRxCzzzSxxN-M71RC): pin height and mating length.
- **Pololu 1-pin housing drawings** (0J1727 / 0J1728): housing envelope.
- **Raspberry Pi Zero W mechanical drawing:** header position.

## Files

All paths are under `/Users/xiangzheng/code/robotics/microduck-sim/guide/extension-20261012-neck-audio/audio/`.

**Results:**

- `study-build.json`: layout, parameters and build clearances.
- `study-checks.json`: exact checks, pilot skins, exterior.
- `wires.json`, `wire-routes.json`: wire screen and route polylines.
- `occupancy.json`: occupied volumes and the neck-route overlap check.
- `acoustics.json` and `acoustics-*.json`: chamber, grille and Helmholtz estimates.
- `old-positions-recheck.json`: the old positions against V1.8.
- `freespace.json`: free-space screen under the roof.
- `audio-study.json`: summary of the key numbers.

**Solids:** `study-solids/*-world.stl`, robot frame. `head_cap_extension-world.stl` is the V1.8 cap with the collar, posts and grille. `cap_added_material` and `cap_removed_material` show only the difference. These are study solids, not print files.

**Pictures:** `png/study-section-*.png`, `png/study-exterior-*.png`, `png/v18-section-*.png`, `png/freespace-under-roof.png`.

**Scripts** (`scripts/`). Rerun them with `/tmp/microduck-cad-venv/bin/python` from `scripts/`, in this order:

1. `recheck_old.py`
2. `freespace.py`
3. `build_study.py`
4. `acoustics.py`
5. `check_study.py` (about 20 min)
6. `wires.py`
7. `occupancy.py`
8. `render_study.py`

`grille_variants.sh` rebuilds each grille variant and ends by rebuilding the recommended one.
