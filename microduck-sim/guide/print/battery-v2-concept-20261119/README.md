# Battery backpack V2: concept for approval (2026-11-19, rev B "sits down")

Status: concept for Shawn's nod. Not approved, no DESIGN-CONTRACT.json, no print files. Envelopes and listing sizes
only; the CAD is drawn after the bought parts are in hand and measured. Power design: `../../../build-pack-20260913/power/power-system-20261119/README.md`
and `../../../build-pack-20260913/power/power-switch-20261119/README.md`.

Rev B replaces rev A (commit 67b785de), whose lower tier reached z -55 and sat 1.7 mm above the floor when the robot
sits. Rev B keeps the box bottom at z -46: 10.9 mm above the floor seated, with no added depth behind the robot.

Files: `concept-sheet.png` (views, wiring, numbers, the layouts explored), `concept_v2.py` (envelopes, checks, layouts,
sheet), `leg_check.py` (hip sweep in MuJoCo), `sit_clearance.py` (real Brain sit; writes `sit_clearance.json`),
`concept.json` (every number below). Run on the Mac mini, in this folder:
`~/.venvs/flight-cad/bin/python concept_v2.py`, then `~/.venvs/microduck-dyn/bin/python sit_clearance.py`, then
`concept_v2.py` again to fold the seated numbers in (about 10 s, 2 s and 10 s). Frame: backpack local = guide frame =
sim trunk frame, mm, x forward, y left, z up; standing, world z = guide z + 120.

## Problems this backpack answers

1. The hard switch gets left on and drains the pack (dead Tattu cell, servos at factory settings).
2. One press turns the robot on with a light; the light goes out by itself after shutdown.
3. A software shutdown also switches the hardware off.
4. Runtime about 2 h: the Crazepony/ALIENMODEL 2S 3000 mAh pack (B08LZ8L4YD, listing 72 x 34 x 20 mm, 110 g) stays in the backpack.
5. Charging on the robot, while running, and later by sitting back onto a dock (two contacts under the tail).
6. The balance lead stays reachable for the monthly B3 balance charge.
7. The XT30 still feeds OpenRB J4 and the 5 V lead still feeds the A7Z.
8. The XIAO's USB-C stays reachable for flashing.
9. The robot can still sit down: the lowest backpack point stays 10 mm or more above the floor when seated.

Constraints every feature keeps: no growth above z 43 or wider than |y| 32.05; bottom at z -46 or higher (problem 9);
legs 6 mm or more clear over hip pitch +-30 and roll +-10; no conflict with the flight pack; no snaps, hooks, tongues
or flexures; walls 1.5 mm or more; screws only M2 x 4/6/8/10; nothing machined by hand.

## Layout

The 72 mm pack stands upright, 20 mm deep, leads up, sitting on the floor of the lower tier at z -44. With the bottom at
z -46 the box is 89 mm tall inside 85.3 mm, so 13.3 mm stay above the pack for the leads. The 16 mm button no longer
fits above the pack: its body and the 21.8 mm circle its nut sweeps when tightened need about 22 mm. The pack therefore
moves 6.3 mm to the robot's right and the button sits beside it, high on the upper left, with its body running forward
past the pack's left face. The DFR1202 moves from the right wing to the left wing under the button, next to the Pololu.
The lower tier is widened to the right to take the shifted pack, and its front-right vertical edge gets a 3.8 mm chamfer
for the right shin. The lower tier's back stays at today's x -75.55: nothing grows behind the robot.

- Upper tier: unchanged, x -45 to -75.55, |y| <= 32.05, z -15.2 to 43. Front plate and its four fixing holes unchanged.
- Lower tier: x -45 to -75.55 (as today), y -25.3 to +20 (today |y| 18.6), z -46 to -15.2 (today's box ends at z -34,
  today's front plate at z -44). 45 deg chamfer 3.8 mm on the front-right vertical edge, with a matching inner chamfer so
  the wall stays 1.7 mm.
- Box height 77 -> 89 mm (12 mm lower than today's box, 2 mm lower than today's front plate); outer volume
  135 -> 156 cm3; depth behind the plate 30.55 mm for both tiers, as today. Depth added: 0 mm.
- Pack: x -49.3 to -69.3, y -23.3 to +10.7, z -44 to 28 (0.3 mm play, 1 mm foam pad behind). Its front stays 2.3 mm
  behind the plate so the heads of the lower fixing screws (z -36.5) clear it.
- Gaps that set the layout: button body 0.6 mm beside the pack (0.3 mm after play), nut circle 0.15 mm from the left
  wing wall and 0.2 mm under the roof, lower cap bosses 0.25 mm behind the pack, lead bay 13.3 mm.
- Mass: backpack 103 -> 188 g (+85 g); robot 960 -> 1045 g. The frame (30 g) and cap (10 g) are envelope estimates with
  solid walls (volume x 1.24 x 0.851, the repo method); windows and the CAD will make them lighter. Everything else is a
  listing mass or marked as an estimate in `concept.json`.
- Balance point of the whole robot moves 4.0 mm back, 2.8 mm down and 0.5 mm right (from x -7.6, y 0.3, z 25.3 to
  x -11.6, y -0.2, z 22.6). Before any walking, the sim model gets a dated variant with these parts and the walk check
  (AGENTS.md model rule).

## Checks (concept.json)

- Seated (`sit_clearance.py`, 2026-11-19: the real Brain sit in the current as-built model battery-20261104, 7.0 V, run
  on the Mac mini): trunk 114.7 -> 59.1 mm, pitch -1.7 deg. Lowest point above the floor, standing / seated: new lower
  tier 68.9 / 10.9 mm, contact pads 69.0 / 10.9, upper tier 99.6 / 41.6; today's box 80.9 / 22.9 and today's front
  plate 70.9 / 13.7. Rule 10 mm: met with 0.9 mm to spare, in a model 85 g lighter than the new robot.
- Legs (`leg_check.py`, hip pitch +-30, roll +-10, both legs): new lower tier 7.6 mm at the worst pose (right hip pitch
  -30, roll +10, lower leg); without the chamfer it would be 5.56 mm. Upper tier 9.83 (unchanged), pads 27.8, today's
  lower tier 12.63. The chamfer is checked as a 4-step staircase outside the chamfer line, so the real value is a little
  larger.
- Flight pack: no overlap with any part in `extensions/flight-20261110/cad/build/*-world.stl`, backpack 6.9 mm further
  back (the wing-plate centre), today's printed upper tier plus the new lower tier. The lower tier ends at z -15.2,
  below the harness crossing behind the cap (z 4 to 16); the upper tier is unchanged, so its 1.55 mm gap to that
  crossing is today's gap.
- Robot trunk: no trunk mesh point inside, or within 2 mm of, the new lower tier (today's backpack contents excluded).
- Parts: no overlap between any bought part and the printed envelope, or between two bought parts. All four fixing-screw
  heads clear the pack and the button; the driver lanes from the open back are clear (0.7 mm to the left wall for the
  lower left screw, as in rev A).

## Layouts explored

Numbers from `concept.json` "options": depth added behind today's box, seated and leg clearance from the two sims, mass
and balance-point shift as estimates (shell plus parts).

- **A Upright, centred, shorter lead bay, button over the pack.** Bbox x -45..-75.55, |y| 32.05, z -46..43; depth +0;
  seated 10.9, legs 8.64; backpack about 180 g, COM 3.7 back, 2.6 down. Rejected: the button and its nut need about
  22 mm over the pack top but the bay is 13.3 mm; the nut would reach z 46.9 against a roof at 43, and the wings
  (11.4 mm inside) cannot take a 16 mm body.
- **B Upright, 6.3 mm right, button beside it, DFR1202 to the left wing, front-right chamfer (chosen).** Bbox
  x -45..-75.55, y -32.05..32.05, z -46..43; depth +0; seated 10.9, legs 7.6; backpack 188 g (detailed), COM 4.0 back,
  2.8 down, 0.5 right. Meets every constraint with the least depth.
- **C Upright, centred, button in the lower-tier back.** Lower tier grows to x -97.25; depth +21.7; seated 10.2, legs
  8.64; about 184 g, COM 4.0 back. Rejected: works, but 21.7 mm deeper than B for no gain.
- **D Pack lying lengthwise (72 along x), growing backward.** Lower tier to x -124; depth +48.5; seated 9.4, legs 9.39;
  about 188 g, COM 7.2 back, 5.8 down. Rejected: deepest, and its long tail sits 9.4 mm off the floor seated.
- **E Pack lying flat across the back (72 along y).** |y| 38; depth +0; seated 10.8, legs 0.86; overlaps the flight
  harness, wing plate and FC stack. Rejected: over the |y| 32.05 width limit and into the legs.
- **F Pack upright, turned 90 deg (34 along x).** Box back to x -86; depth +10.5; seated 10.6, legs 9.83; overlaps the
  flight harness (4777 mm3) and wing plate. Rejected: the 34 mm does not fit the unchanged upper tier (26.9 mm inside).
- Moving the DFR1202 or Pololu alone frees no height: no board sits over the pack. It helps only as part of B, where the
  right wing narrows to 5 mm and the DFR1202 (8 mm thick) has to move to the left wing.

## Features (each answers a problem by number)

- **F1 Lower tier 12 mm lower than today's box, widened to y -25.3, front-right chamfer 3.8 mm** (4, 9). Why: the
  74 mm pack (largest published length) needs 85.3 mm inside, and z -46 is the lowest bottom that keeps 10 mm seated. Simpler option: a shorter
  pack (none of the same capacity under about 60 mm was found). Check: seated 10.9 mm, legs 7.6 mm. Delete or
  shrink if a pack under about 60 mm long is chosen.
- **F2 Battery column, 6.3 mm right of centre** (4, 2). The pack is boxed by the lower tier's right wall continued up as
  a column wall (y -23.6 to -25.3, up to z 28), a 1.5 mm left rib (y 11.0 to 12.5, floor to z 20, below the button
  body), a floor strip at the front (x -49.3 to -47, z -44 to -41) as the front stop under the screw heads, two cap ribs
  through the 1 mm foam pad as the rear stop, and two 3 mm top ribs 0.3 mm over the pack top. It slides in from the
  open back under the top ribs. No bars, no screws on the pack. Simpler option: the pack centred (layout A), which
  leaves no room for the button.
- **F3 Lead bay over the pack, 11.3 mm with the 74 mm envelope (13.3 mm at the listing text's 72 mm)** (4, 6, 7). The XT30 and XH leads rise into it and bend sideways at once; the
  battery XT30 meets the Pololu VIN pigtail here, the XH plug meets the XIAO harness socket, and the 1N5822 sits here on
  the charge lead. The pack's DC5.5 lead is not used: its plug is capped and laid in the bay. Balance charge: cap off
  (four screws), unplug the XH, plug it into the B3.
- **F4 Pololu 2813 on the left wing's outer wall** (1, 2, 3): x -68 to -47.7, y 26.2 to 30.4, z -12 to 13.4, 3M foam
  tape. Its VIN pigtail and the charge lead reach the bay through the 6 mm passage in front of the button body
  (x -52.5 to -47). Its own onboard button is unused.
- **F5 DFR1202 on the left wing, against the column rib** (7): x -73.6 to -47.6, y 14.2 to 22.2, z -13.5 to 16.5,
  foam tape and two locating ribs (no clip lips). Moved from the right wing, which narrows to 5 mm in rev B.
- **F6 XIAO SAMD21 high on the right wing wall, USB-C window in the cap** (1, 8): x -73.3 to -52.3, z 17.5 to 35,
  y -30.35 to -25.85 (0.55 mm from the column wall), USB-C end at the cap; window 13 x 7.5 mm at y -28.1, z 26.25.
- **F7 16 mm panel hole in the cap's upper left** (2): centre y +19.3, z 30.2, beside the pack. Adafruit 560 (green
  ring) or 559 (red): momentary, 1 NO 1 NC, 6 V LED ring with built-in resistor. Body 20 mm behind the panel with
  terminals plus 3 mm for the solder joints; its wires leave sideways. Nut 19 across flats, 21.8 across corners (vendor
  drawing of the same 16 mm family, Adafruit 3350 datasheet PM161F-10E; Adafruit gives no drawing for 560; the CAD takes the published DigiKey 560 drawing); the box keeps the whole 21.8 mm circle clear, so the nut may stop at any angle.
- **F8 Two fixed contact pads, flush with the bottom** (5). Each pad is an L: a 6 x 8 mm face under the floor
  (x -73.85 to -65.85, at y +9 and -9, 18 mm apart) in a 0.5 mm floor pocket, and a tab up the frame's back face in a
  0.5 mm recess. The dock pushes the face up against the floor; the lower cap screw clamps the tab between the cap and
  the frame boss. No springs, no glue, nothing moving on the robot. Contact wires (20 AWG) are soldered to the tab tops
  and rise through the 3.5 mm channel behind the pack to the bay.
- **F9 Schottky 1N5822 on the charge lead in the bay** (5): DO-201AD, 3 A 40 V, from RoboClub (cabinet F), heat-shrunk
  in line. Pad + -> diode -> Pololu VIN pad (the pack node, before the switch); pad - -> Pololu GND (pack -).
- **F10 Lead slot in the left wing's step floor, open to the back** (7): 3.5 mm wide (y 22.6 to 26.1), from the back
  edge to x -60, between the DFR1202 and the Pololu. Plug 3 (XT30) and plug 4 (MR30) leads are laid in from behind and
  leave at the lower left, between backpack and body, as today; the cap's lower edge closes the slot. The plugs stay
  outside, so the slot only takes the wires.
- **F11 Cap = back plate over both tiers, four screws from behind** (6, 8): two M2 x 8 high, at (y, z) = (+29, 17) and
  (-29, 39), into 6 mm bosses; two M2 x 6 low, at (+-9, -41.5), into 3.8 mm bosses on the floor behind the pack, which
  also clamp the pad tabs (clamped 2.2 mm, 3.8 mm engaged). Bosses 5 mm diameter, pilots run through (print_fit
  pilot_depth rule). Back face down on the bed, so the screw axes are vertical in print: clearance 2.5 mm in the cap,
  pilot 1.95 mm in the bosses (H2S values from print_fit.py), head seat 4.6 x 1.7.
- **F12 Third MR30 pin carries the A7Z OFF line** (3): the MR30 has three pins and today uses two.

Removed from today's backpack: the hatch (failed twice), bars, cradle, roof lead openings, plug 1 and the balance plug
on top of the box, the switch pocket and switch window. Removed from rev A: the 4.45 mm heel, the cap block and the
spring pins.

## Assembly order (one action per line)

1. Bench: solder the XT30 pigtails to the Pololu VIN and VOUT holes, the DFR1202 VIN lead to VOUT, the XIAO harness
   (resistors, two 1N4148, XH socket, button plug), the charge lead (two pad wires, 1N5822) to the Pololu VIN and GND
   pads, and the pad wires to the two pad tabs.
2. Screw the frame onto the OpenRB pack posts with the four M2 x 6, driver straight in from the open back (upper
   screws through the empty column, lower through the empty lower tier; lane checked clear, 0.7 mm between driver and
   wall).
3. Lay the two pads into their floor pockets with the tabs up the back face; their wires go up the channel behind the
   column.
4. Lay the plug 3 and plug 4 leads into the step-floor slot from behind; stick the DFR1202 against the column rib and
   the Pololu on the left outer wall; stick the XIAO on the right wing wall.
5. Slide the pack forward into the column under the top ribs, leads up; foam pad on its back.
6. Join the battery XT30 to the Pololu VIN pigtail and the XH plug to the XIAO harness; cap the DC5.5 plug and lay it
   in the bay.
7. Fit the button in the cap hole and tighten its nut; plug its 4-pin lead into the harness.
8. Put the cap on and drive the two M2 x 8 high and the two M2 x 6 low through the pad tabs.
9. Plug 3 onto the OpenRB J4 inlet, plug 4 onto the A7Z lead.

## Contacts and the dock

Standing, the pad faces are 69 mm above the floor (sim; 74 mm from the nominal 120 mm trunk height) at x -73.85 to
-65.85, y +-9, facing straight down, 27.8 mm from the nearest leg part over the hip sweep. Seated, they are 10.9 mm
above the floor and flush with the box bottom, which is the lowest point of the backpack. So dock spring plates that
reach about 12 to 13 mm above the floor touch the pads only when the robot sits on the dock, and a standing or walking
robot passes over them with 56 mm to spare. Spacing 18 mm, pad faces 6 mm wide: two dock plates 10 mm wide with a
6 mm gap keep each pad on its own plate across about +-7 mm of sideways error, and a 6 mm pad cannot bridge the 6 mm
gap; the V funnel does the rest. Along x the pads
are 8 mm long, so the dock's back stop has to place the tail within a few mm (dock geometry is not drawn yet).

## Flight pack

No conflict (see Checks). The pack's 6.3 mm shift and the wider lower tier stay below z -15.2, under the harness.

## Guide steps this changes (`guide/content/steps.py`)

- Chapter 12 summary (`backpack`) and all ten steps: `bp-strip`, `bp-switch` (switch pocket goes), `bp-dfr` (now on
  the left wing, foam tape), `bp-battery` (pack into the frame column, not the cap), `bp-bars` (goes), `bp-cap` (cap
  is a back plate with two M2 x 8 and two M2 x 6), `bp-mount`, `bp-hatch` (goes), `bp-plug1` (no plug on top; button
  press instead), `bp-swap` (goes: the pack is charged on the robot; replaced by a monthly balance-charge step).
- New steps: solder the Pololu, XIAO harness and charge lead; flash the XIAO cutoff; fit the pads; fit the button.
- Parts and print lists that name the V1.40 package, the switch, the DFR1202 clip and the XT30/MR30 plugs (around
  lines 384, 394-395, 426-427 and 443), and the warning that the battery reaches the robot only through plugs 3 and 4
  (line 329; still true).
- Power-up chapter: the battery guard floor moves from 6.2 to 6.4 V (`guide/firmware/pi/battery.py`, `FLOOR_AT_DV`),
  the A7Z OFF GPIO and its shutdown hook, the idle timeout.
- Weighing note (line 1890): the robot becomes about 1045 g.
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
- M2 x 6, 6 (four fixing screws from today, two low cap screws); M2 x 8, 2 (cap; stock).
- 3M foam tape (Shawn's stock).
- Heat shrink 3, 5 and 8 mm (RoboClub; not listed in INVENTORY.md, check).
- Soldering station and solder (RoboClub).

To buy or to choose:
- Crazepony/ALIENMODEL 2S 3000 mAh LiPo, Amazon B08LZ8L4YD, $22.99, 1.
- Pololu Big Pushbutton Power Switch HP #2813, $8.95, 1 (2 recommended, one spare).
- Adafruit 560 Rugged Metal Pushbutton with Green LED Ring, 16 mm momentary, $4.95, 1 (559 red also in stock).
- Contact pads, 2: an L contact about 6 mm wide and 0.5 mm thick, with a face about 8 mm long and a tab about 11 mm
  tall that already has a hole for M2 (2.4 mm or more) or is narrow enough to clamp beside the screw. The flat battery
  contacts in RoboClub's battery-clips drawer have this shape; their size and tab hole are not checked. No listing was
  verified in this pass.
- Resistors 1/4 W: 100 k x 6, 33 k x 3 (not in the RoboClub list).
- Amass XT30U pair, 2 (Pololu VIN joint, plus spare), unless spares are on the bench.
- Silicone wire if not in stock: 16 AWG red and black (pack XT30 to Pololu 2 x 50 mm; Pololu to plug 3 2 x 150 mm),
  20 AWG red and black (pads to diode to Pololu VIN and GND, 2 x 130 mm), 22 AWG (Pololu VOUT to DFR1202, 2 x 90 mm),
  26-28 AWG (XIAO harness, 8 x 80 mm; button lead 4 x 100 mm; OFF line from the Pololu to plug 4 100 mm and from the
  robot MR30 to the A7Z header about 250 mm).
- Not needed any more: the DC5.5 pigtail pair and spring contacts (rev A), the carted second B3 charger and Tattu 650
  (already ordered 2026-11-03), the REV switch.

## Open questions for Shawn

1. Rev B: the box grows 12 mm down (to 2 mm below today's front plate), the lower tier 6.7 mm wider on the right and
   1.4 mm on the left, and nothing behind; the pack sits 6.3 mm right of centre and the balance point moves 0.5 mm right. Accept?
2. The pack's DC5.5 lead is left unused and capped; the dock charges through the pads into the Pololu VIN pads, the
   same pack node as the XT30. Accept, or keep the DC5.5 joint (it does not fit the 13.3 mm bay lying flat)?

Decided by the main session 2026-11-19 (reversible, matches Shawn's stated wish "按一下亮灯，关机后自动灭灯"):
- Button to the Pololu ON pin (press = on only; off = A7Z shutdown, XIAO cutoff, or hold 2 s). A fall onto the back
  cannot switch the robot off mid-walk.
- Button on the back upper left, ring facing back.
- Contacts: fixed pads on the robot, springs on the dock plates (no moving part on the walking robot, "皮实").
- The A7Z OFF pin is picked from the head pin map at CAD time.
- No cell-voltage report to the A7Z in v1; the XIAO acts on its own.
- Pololu 2813 current: the 16 A figure on pololu.com is at a 150 C MOSFET; the design figure stays 6 A at a 55 C rise,
  still 3 times the walking current.

Still open on the agent side (no decision needed from Shawn):
- Seated margin is 0.9 mm over the 10 mm rule, measured in today's model, which is 85 g lighter. The dated sim variant
  with these parts reruns `sit_clearance.py` before release.
- Several gaps are under 0.5 mm (button body to pack, nut circle to the wing wall and roof, lower bosses to the pack).
  The CAD takes each part's largest published size; no physical measurement gates the design.
- Battery envelope: 74 x 34 x 20 mm, the largest of the published sizes (listing text 72 x 34 x 20, listing drawing
  74 x 34 x 19). The listing photos show the XT30, XH and DC5.5 leads all leaving one 34 x 19 end. With 74 mm the
  lead bay is 11.3 mm and the 1N5822 sits at z 31 to 36.3; concept checks pass (concept.json, 2026-11-20).
- The pad part (see BOM) is not chosen yet.

## Proposal items that do not fit as written

- The 72 x 34 x 20 pack does not fit today's 77 mm-tall box with lead room; the box grows 12 mm down (F1) and the button
  moves beside the pack (F7).
- The proposal's "12 V LED version" button lit from VOUT: the in-stock 16 mm rugged buttons have a 6 V ring with a
  built-in resistor; this concept feeds it from the DFR1202 5 V, which is on exactly while the robot is on.
- The proposal joins the charge path to the pack's DC5.5 lead; rev B lands it on the Pololu VIN pads (same pack node)
  because the DC5.5 joint does not fit the shorter bay.
- The listing text says XT60 while the photo shows XT30, and the face the leads leave from is not given; the concept
  assumes XT30 on the 34 x 20 end. An XT60 needs an adapter pigtail or a new Pololu VIN plug.
- The proposal buys an SB560; RoboClub's 1N5822 is the same package and enough for 2 A.
- The proposal names spring contacts on the robot; the main session moved the springs to the dock.
- Pololu 2813: 6 A continuous at a 55 C rise (16 A is the 150 C figure); 6 A stays the design figure.
