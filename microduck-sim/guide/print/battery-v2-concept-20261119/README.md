# Battery backpack V2: concept for approval (2026-11-19)

Status: concept for Shawn's nod. Not approved, no DESIGN-CONTRACT.json, no print files. Envelopes and listing sizes
only; the CAD is drawn after the bought parts are in hand and measured. Power design: `../../../build-pack-20260913/power/power-system-20261119/README.md`
and `../../../build-pack-20260913/power/power-switch-20261119/README.md`.

Files: `concept-sheet.png` (six views), `concept_v2.py` (envelopes, checks, sheet; run with
`~/.venvs/microduck-cad/bin/python concept_v2.py`, about 5 s, 0.8 GB), `leg_check.py` (hip sweep in MuJoCo, called by
the script), `concept.json` (every number below). Frame: backpack local = guide frame = sim trunk frame, mm, x forward,
y left, z up; standing, world z = guide z + 120.

## Problems this backpack answers

1. The hard switch gets left on and drains the pack (dead Tattu cell, servos at factory settings).
2. One press turns the robot on with a light; the light goes out by itself after shutdown.
3. A software shutdown also switches the hardware off.
4. Runtime about 2 h: the Crazepony/ALIENMODEL 2S 3000 mAh pack (B08LZ8L4YD, listing 72 x 34 x 20 mm, 110 g) stays in the backpack.
5. Charging on the robot, while running, and later by sitting back onto a dock (two contacts under the tail).
6. The balance lead stays reachable for the monthly B3 balance charge.
7. The XT30 still feeds OpenRB J4 and the 5 V lead still feeds the A7Z.
8. The XIAO's USB-C stays reachable for flashing.

Constraints every feature keeps: no growth above z 43 or wider than |y| 32.05; legs 6 mm or more clear over hip pitch
+-30 and roll +-10; no conflict with the flight pack; no snaps, hooks, tongues or flexures; walls 1.5 mm or more;
screws only M2 x 4/6/8/10; nothing machined by hand.

## Layout

The 72 mm pack stands upright in the middle of the box, 20 mm deep, leads up. Today's box is 77 mm tall (z -34 to 43),
so a 72 mm pack plus walls and room for its leads does not fit. Up is forbidden, wider hits the legs and the flight
harness at |y| 32.6, and deeper behind moves the balance point back and hits the flight harness crossing behind the cap
at z 4..16. Down is free: the narrow lower tier goes from z -34 to -55. The pack sits on the floor of the lower tier;
above it is a 22 mm top bay for the leads, the XT30 joint, the balance plug and the button. The two side wings of the
upper tier carry the boards: Pololu 2813 on the left, DFR1202 low and the XIAO high on the right. A 4.45 mm heel at the
back of the lower tier holds the two charge contacts in its floor.

- Upper tier: unchanged, x -45 to -75.55, |y| <= 32.05, z -15.2 to 43. Front plate and its four fixing holes unchanged.
- Lower tier: x -45 to -80 (today -75.55), |y| <= 20.0 (today 18.6), z -55 to -15.2 (today -34). Straight step at
  z -15.2 as today.
- Box height 77 -> 98 mm; outer volume 135 -> 170 cm3; depth behind the plate 30.55 mm (upper), 35 mm (lower tier).
- Pack: x -49.3 to -69.3, |y| <= 17, z -53 to 19 (0.3 mm side play, 1 mm foam pad behind). Its front stays 2.3 mm
  behind the plate so the heads of the lower fixing screws (z -36.5) clear it.
- Mass: backpack 103 -> 196 g (+92 g); robot 960 -> 1053 g. The frame (32 g) and cap (16 g) are envelope estimates with
  solid walls (volume x 1.24 x 0.851, the repo method); windows and the CAD will make them lighter. Everything else is a
  listing mass or marked as an estimate in `concept.json`.
- Balance point of the whole robot moves 4.5 mm back and 4.4 mm down (from x -7.6, z 25.3 to x -12.0, z 21.0).
  Before any walking, the sim model gets a dated variant with these parts and the walk check (AGENTS.md model rule).

## Features (each answers a problem by number)

- **F1 Lower tier 21 mm lower, 1.4 mm wider each side, 4.45 mm heel** (4). Why: the only free direction for a 72 mm
  pack (see Layout). Simpler option: a shorter pack (the STRIX 69 mm is still too tall for 77 mm with leads). Check:
  legs 6.32 mm at the worst pose (left hip pitch +30, roll -10, lower leg), today 12.63; rule 6 mm. Round the lower
  tier's bottom outer edges in CAD to win more. Delete if a pack under about 55 mm long is chosen.
- **F2 Battery column with foam pads and two top ribs** (4). The pack is boxed by the lower-tier walls, two column
  walls in the upper tier (|y| 17.3 to 19.0, up to z 19), the floor, a 3 mm rib over the front edge of its top
  (frame) and the cap below and behind it. 1 mm 3M foam pads take up play. No bars, no screws on the pack: it is never
  swapped. Simpler option: today's two screwed bars; not needed when walls surround the pack.
- **F3 Top bay over the pack** (4, 6, 7). The three battery leads (XT30, DC5.5, XH) rise into it; the battery XT30
  meets the Pololu VIN pigtail here, the DC5.5 lead meets the charge pigtail with the Schottky diode, and the XH plug
  meets the XIAO harness socket. Balance charge: cap off (four screws), unplug the XH, plug it into the B3.
- **F4 Pololu 2813 on the left wing wall** (1, 2, 3): x -68 to -47.7, y 26.2 to 30.4, z -12 to 13.4, 3M foam tape
  against the outer wall. Its own onboard button is unused.
- **F5 DFR1202 on the right wing wall** (7): the same pocket, turned so the 8 mm thickness is along y: x -73.6 to
  -47.6, y -30.4 to -22.4, z -13.5 to 16.5, foam tape and two locating ribs (no clip lips).
- **F6 XIAO SAMD21 high on the right wing wall, USB-C window in the cap** (1, 8): x -73.3 to -52.3, z 17.5 to 35,
  USB-C end at the cap; window 13 x 7.5 mm at y -28.1, z 26.25 (USB-C plug overmould 12 x 6.5 passes).
- **F7 16 mm panel hole in the cap's upper back, left of centre** (2): centre y +17, z 30.5. Adafruit 560 (green ring)
  or 559 (red), $4.95, in stock 2026-11-19: momentary, 1 NO 1 NC, 6 V LED ring with built-in resistor. Depth behind the
  panel 20 mm with terminals, nut 19 across flats / 21.8 across corners (vendor drawing of the same 16 mm family,
  Adafruit 3350 datasheet PM161F-10E; Adafruit gives no drawing for 560, confirm on arrival). The nut sits with its
  flats top and bottom between z 21 and 40. The cap's rounded top corner starts above z 40 (today about z 37).
- **F8 Heel with two contact bores in the frame floor, held by a solid block on the cap** (5). Two spring contacts
  point down at y +9 and -9 (18 mm apart), x -76.1, tips at z -56.5 (1.5 mm below the floor). The cap's lower plate
  carries one solid block (x -78.3 to -70.4, |y| <= 12.5, z -53 to -20) that bears on both pin flanges and is the
  pack's rear stop below z -15.2. No clamp screws, no glue. Contact wires (20 AWG) rise through the 3.5 mm channel
  behind the pack to the top bay.
- **F9 Schottky 1N5822 on the charge pigtail in the top bay** (5): DO-201AD, 3 A 40 V, from RoboClub (cabinet F),
  heat-shrunk in line. Same package as the SB560 of the proposal; 2 A charge current is inside its rating.
- **F10 Lead window in the left wing's step floor** (7): about 13 x 8 mm near the front (x -50 to -63, y 21 to 29), so
  plug 3 (XT30) and plug 4 (MR30) leave at the lower left, between backpack and body, as today. Sized for the XT30
  plug (10.2 x 5.2) with its lead.
- **F11 Cap = back plate, four M2 x 8 into frame bosses** (6, 8): bosses 5 mm diameter, 6 mm long at (y, z) = (+-29,
  39) and (+-15.5, -50). Back face down on the bed, so the screw axes are vertical in print: clearance 2.5 mm in the cap,
  pilot 1.95 mm in the bosses (H2S values from print_fit.py), head seat 4.6 x 1.7.
- **F12 Third MR30 pin carries the A7Z OFF line** (3): the MR30 has three pins and today uses two.

Removed from today's backpack: the hatch (failed twice), bars, cradle, roof lead openings, plug 1 and the balance plug
on top of the box, the switch pocket and switch window.

## Assembly order (one action per line)

1. Bench: solder the XT30 pigtails to the Pololu VIN and VOUT holes, the DFR1202 VIN lead to VOUT, the XIAO harness
   (resistors, two 1N4148, XH socket, button plug), the charge pigtail (contacts, 1N5822, DC5.5 plug).
2. Screw the frame onto the OpenRB pack posts with the four M2 x 6, driver straight in from the open back (upper
   screws through the top bay, lower through the empty lower tier; lane checked clear, 0.7 mm between driver and wall).
3. Push the two contacts down into their floor bores from inside; lead their wires up the channel behind the pack.
4. Stick the Pololu on the left wing wall and the DFR1202 and the XIAO on the right wing wall; lead plugs 3 and 4 out
   through the step-floor window.
5. Slide the pack forward into the column, leads up; foam pad on its back.
6. Join the battery XT30 to the Pololu VIN pigtail, the DC5.5 lead to the charge pigtail, the XH plug to the XIAO harness.
7. Fit the button in the cap hole and tighten its nut; plug its 4-pin lead into the harness.
8. Put the cap on (its block slides into the heel behind the pack) and drive the four M2 x 8.
9. Plug 3 onto the OpenRB J4 inlet, plug 4 onto the A7Z lead.

## Contacts and the dock

Standing, the contact tips are 63.5 mm above the floor (world z 63.5) at x -76.1, facing straight down, 28.9 mm from
the nearest leg part over the hip sweep; the box bottom is the lowest point of the robot behind its feet. The sim has no sitting keyframe,
so how far the robot must lower its tail is not computed here; the dock plate height is set from a measured sit
(scan or IMU pose) when the dock is designed. Spacing 18 mm, so two dock plates 10 mm wide with a 6 mm gap catch one
pin each across about +-4 mm of sideways error; the V funnel does the rest.

## Flight pack

No conflict. Checked by mesh intersection with every part in `extensions/flight-20261110/cad/build/*-world.stl` with the
backpack 6.9 mm further back (the wing-plate centre): today's printed upper tier plus the new lower tier, 0 mm3. The
lower tier ends at z -15.2, below the harness crossing behind the cap (z 4 to 16, x -84 to -90.2 flying); the upper
tier is unchanged, so its 1.55 mm gap to that crossing is today's gap.

## Guide steps this changes (`guide/content/steps.py`)

- Chapter 12 summary (`backpack`) and all ten steps: `bp-strip`, `bp-switch` (switch pocket goes), `bp-dfr` (new
  pocket, foam tape), `bp-battery` (pack into the frame column, not the cap), `bp-bars` (goes), `bp-cap` (cap is a back
  plate with four M2 x 8), `bp-mount`, `bp-hatch` (goes), `bp-plug1` (no plug on top; button press instead),
  `bp-swap` (goes: the pack is charged on the robot; replaced by a monthly balance-charge step).
- New steps: solder the Pololu, XIAO harness and charge pigtail; flash the XIAO cutoff; fit the contacts; fit the button.
- Parts and print lists that name the V1.40 package, the switch, the DFR1202 clip and the XT30/MR30 plugs (around
  lines 384, 394-395, 426-427 and 443), and the warning that the battery reaches the robot only through plugs 3 and 4
  (line 329; still true).
- Power-up chapter: the battery guard floor moves from 6.2 to 6.4 V (`guide/firmware/pi/battery.py`, `FLOOR_AT_DV`),
  the A7Z OFF GPIO and its shutdown hook, the idle timeout.
- Weighing note (line 1890): the robot becomes about 1053 g.
- Separate stale item found on the way: step `duallock-plate` (line 1011) still has the Dual Lock back plate, while
  CURRENT-STATE `backpack_swap_plugs` says it is not fitted and the backpack screws straight onto the pack.

## Bill of materials

Owned or in RoboClub stock:
- DFRobot DFR1202 5 V buck, 1 (on the robot now).
- Seeed XIAO SAMD21, 1 (RoboClub cabinet C drawer: 3 sealed, inventory 2026-10-20).
- Schottky 1N5822, DO-201AD, 3 A 40 V, 1 (RoboClub cabinet F diodes).
- Small-signal diodes "100 V 0.2 A" (1N4148 class), 2 (RoboClub cabinet F; check the marking says 1N4148 or 1N914).
- 10 k resistor, 1 (RoboClub cabinet D lists "10K?"; check).
- JST-XH 3-pin housing and crimps (balance socket) and one 4-pin pair (button lead), RoboClub small boxes.
- Plug 3 (female XT30 on its lead) and plug 4 (female MR30 on its lead), from today's backpack.
- M2 x 6, 4 (today's fixing screws); M2 x 8, 4 (cap; stock).
- 3M foam tape (Shawn's stock).
- Heat shrink 3, 5 and 8 mm (RoboClub; not listed in INVENTORY.md, check).
- Soldering station and solder (RoboClub).

To buy:
- Crazepony/ALIENMODEL 2S 3000 mAh LiPo, Amazon B08LZ8L4YD, $22.99, 1.
- Pololu Big Pushbutton Power Switch HP #2813, $8.95, 1 (2 recommended, one spare).
- Adafruit 560 Rugged Metal Pushbutton with Green LED Ring, 16 mm momentary, $4.95, 1 (559 red also in stock).
- Spring contacts, 2 (plus spares): rated 2 A or more, barrel 4 mm or less, travel 1.5 mm or more, a flange or
  shoulder for the cap block to bear on, solder cup. Check RoboClub's pogo-pin drawer (cabinet B) first; no listing was
  verified in this pass.
- Resistors 1/4 W: 100 k x 6, 33 k x 3 (not in the RoboClub list).
- DC5.5 x 2.1 pigtail pair (male and female), 1 pack: the gender of the pack's DC5.5 lead is not on the listing.
- Amass XT30U pair, 2 (Pololu VIN joint, plus spare), unless spares are on the bench.
- Silicone wire if not in stock: 16 AWG red and black (pack XT30 to Pololu 2 x 50 mm; Pololu to plug 3 2 x 150 mm),
  20 AWG red and black (contacts to diode to DC5.5, 2 x 130 mm), 22 AWG (Pololu VOUT to DFR1202, 2 x 90 mm),
  26-28 AWG (XIAO harness, 8 x 80 mm; button lead 4 x 100 mm; OFF line from the Pololu to plug 4 100 mm and from the
  robot MR30 to the A7Z header about 250 mm).
- Not needed any more: the carted second B3 charger and Tattu 650 (already ordered 2026-11-03), the REV switch.

## Open questions for Shawn

1. The box grows 21 mm down (tail 63.5 mm above the floor standing, today 86) and the lower tier 1.4 mm wider each
   side. It is the only direction the 72 mm pack fits. Accept?
Decided by the main session 2026-11-19 (reversible, matches Shawn's stated wish "按一下亮灯，关机后自动灭灯"):
- Button to the Pololu ON pin (press = on only; off = A7Z shutdown, XIAO cutoff, or hold 2 s). A fall onto the back
  cannot switch the robot off mid-walk.
- Button on the back upper left, ring facing back, as drawn.
- Contacts: fixed brass pads on the robot, springs on the dock plates (no moving part on the walking robot, "皮实");
  the robot buys no spring contacts.
- The A7Z OFF pin is picked from the head pin map at CAD time.
- No cell-voltage report to the A7Z in v1; the XIAO acts on its own.
- Pololu 2813 current: the 16 A figure on pololu.com is at a 150 C MOSFET; the design figure stays 6 A at a 55 C rise,
  still 3 times the walking current.

Still Shawn's: question 1 (the box grows down).

## Proposal items that do not fit as written

- The 72 x 34 x 20 pack does not fit today's 77 mm-tall box with lead room; the box must grow down (F1).
- The proposal's "12 V LED version" button lit from VOUT: the in-stock 16 mm rugged buttons have a 6 V ring with a
  built-in resistor; this concept feeds it from the DFR1202 5 V, which is on exactly while the robot is on.
- Button on A/B toggles off on any press (open question 2).
- The listing text says XT60 while the photo shows XT30, and the face the leads leave from is not given; the concept
  assumes XT30 on the 34 x 20 end. An XT60 needs an adapter pigtail or a new Pololu VIN plug.
- The proposal buys an SB560; RoboClub's 1N5822 is the same package and enough for 2 A.
- Pololu 2813: 6 A continuous at a 55 C rise (16 A is the 150 C figure); 6 A stays the design figure.
