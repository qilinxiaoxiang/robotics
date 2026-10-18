# Pluggable ends for the two board-soldered wire pairs (OpenRB-150 J12, DFR1202)

Problem: P5, serviceable onboard hardware. The owner's rule is that no wire is soldered straight onto a board; every
wire ends in a plug or a clamp, and soldering a connector onto a board is fine. V1.8 breaks the rule twice: the UART
pair is soldered into OpenRB-150 J12 (`guide/content/steps.py`, step `uart-wires`), and six power wires are soldered to
the DFR1202 pads (step `dfr-leads`, `guide/content/wiring/dfr1202.py`). Checked 2026-10-12. Nothing outside this folder
was changed.

## Verdict

- **J12 (UART): solder a JST PH 4-way top-entry header, B4B-PH-K-S, into J12.** The two UART wires get SPH-002T-P0.5S
  contacts in a PHR-4 housing. J12 is a through-hole row of four 2.0 mm holes with no peg holes, and the PH header
  has no pegs, so it drops in. It fits the pack in one of its two orientations: no overlap, 0.53 mm to the nearest
  OpenRB component, 2.55 mm from the plug top to the converter's back face, 2.0 mm from the pin tails to the pack
  plate. The board's drop-in path stays clear (2.0 mm). Side-entry PH does not fit (it hits OpenRB parts).
- **DFR1202 (power): no connector can be soldered onto the converter itself in a sound way.** Its VIN, GND and VOUT
  are castellated edge pads (a row of plated half-holes cut through the board edge), about 2.5, 4.5 and 3.5 mm long and
  1.8 mm deep, spaced about 10.95 and 10.56 mm apart. There is no through-hole for a pin, and no common connector
  pitch matches. The least-bad pluggable route is a small **adapter board**, soldered to the castellations the way
  such modules are meant to be mounted, carrying a **6-way 3.5 mm screw terminal block (Same Sky TB0011-350-06)**.
  It clamps all six wires, and each clamp is rated 7 A (UL). The heaviest load is the 3.25 A input. It only fits after
  two small material-removing pack edits: a pocket of at least 0.5 mm in the cover's inner face, and the two converter
  feet trimmed by at least 0.2 mm each. Without those edits it overlaps the cover (72.45 mm³) and grazes the feet
  while the converter drops in (2.86 mm³). Every other block layout checked collides with the OpenRB-150.
- **Owner decision needed for the DFR1202.** Choose one of these:
  - Accept a custom adapter PCB plus the two pack edits. The edits then have to pass the print-release gate.
  - Look for a lower clamp: at most about 7.5 mm tall and at most 20.6 mm long. That would avoid both edits, but no
    such part was sourced here.
  - Replace the converter with one that has through-hole pins. That is a new sourcing decision.

## OpenRB-150 J12: JST PH top-entry header

What J12 is (sources below):

- **Official (ROBOTIS schematic, page 3):** J12 is footprint "20010WS-04, DNP" (not populated). Pin 3 is SERIAL_RX and
  pin 4 is SERIAL_TX; pin 1 is GND and pin 2 is +3V3, as read in `guide/content/wiring/openrb.py`.
- **Official (Yeonho 20010 datasheet):** 20010WS is a 2.0 mm pitch wire-to-board wafer. It is 4.7 mm tall in the
  vertical version, wave-soldered (so through-hole), rated 2 A, and mates with a 20010HS housing.
- **Measured in the repo's placed board mesh** (`guide/print/world/openrb-board-upright.stl`, by `fit_connectors.py`):
  - J12 is one row of four holes at 2.0 mm pitch, each about 0.8 mm across.
  - Robot-frame position: y -3.7, -1.7, 0.3, 2.3 at z 6.7. The component-side copper face is at x -26.45.
  - There are no extra peg holes beside the row. The JP1 power-jumper header sits 4.1 mm towards the terminal block.
- **Pin order in the pack (inference):** pad 4 (Tx) is at y -3.7 and pad 1 (G, square) at y +2.3. This comes from
  turning the ROBOTIS product photo (USB-C up) by 180 degrees into the pack pose (USB-C down, components facing the
  rear). The guide's existing continuity check confirms it on the real board: G beeps to the terminal block −.

Proposed parts:

- **Header:** JST B4B-PH-K-S(LF)(SN). Top entry, 4 ways, 2.0 mm pitch, no pegs. JST PH datasheet: header 9.9 mm along
  the row, 4.5 mm deep with the pin row 1.7 mm from one face, 6.0 mm tall, (8) mm mated height. JST recommends a
  0.7 mm (+0.1/0) PCB hole, and the mesh hole is 0.8 mm, at the top of that tolerance. The board must be 0.8 to 1.6 mm
  thick; OpenRB is 1.65 mm in the mesh.
- **Housing:** JST PHR-4. Fit contacts only in the positions over J12 pads 3 and 4. Leave pads 1 (GND) and 2 (3.3 V)
  empty, as now.
- **Contacts:** JST SPH-002T-P0.5S, for AWG 30 to 24 and insulation 0.8 to 1.5 mm across. The guide's 26 AWG wire is
  inside that range if its insulation is at least 0.8 mm across. JST lists only machine applicators; a generic 2.0 mm
  open-barrel hand crimper or ready-crimped PH leads are the practical routes (inference, not checked).
- **Rating:** PH is rated 2 A (AWG 24) and 100 V. The UART carries milliamps at 3.3 V.
- **Far end:** unchanged. The Dupont sleeves go on Pi pins 8 and 10.

Fit results (`fit-results.json`, candidate `J12-PH-top-b`):

- **Orientation:** the header's 2.8 mm wall faces the USB-C end (-z) and its 1.7 mm wall faces JP1. Turned the other
  way (`J12-PH-top-a`), the body touches the JP1 header base: 0.019 mm³, 0.18 mm in z. With no pegs both ways go in,
  so map the two wires by the J12 silkscreen (Rx, Tx), not by the housing's position numbers.
- **Final pose:** no overlap. Header and plug to the nearest OpenRB component: 0.53 mm. Plug top (x -34.45) to the
  converter's back face (x -37.0): 2.55 mm. Pin tails (1.8 mm past the board back) to the pack plate: 2.0 mm. The step
  `jumper-tails` already trims tails to 1.5 mm or less.
- **Wire exit:** a 2.5 mm room above the plug was reserved for the two wires to turn (inference: about 2.5 times a
  1.0 mm insulation diameter). That leaves 0.05 mm to the converter. The wires must turn sideways or up straight off
  the housing. Thin-wall 26 or 28 AWG makes this easier, as long as the insulation is at least 0.8 mm across.
- **Board drop-in** (down 30 mm at x -3, then +3 onto the pads, as in `rear-pack/check_assembly.py`; shells, cover and
  converter not yet in): clear, 2.0 mm minimum, both with the header alone and with the plug and wires already fitted.
- **Pack rooms** (`pack_lib.py`: leg plugs, neck plug, terminal block, USB): all clear.
- **Cables (flexible, information only):** the ORB supply pair's current centreline passes 0.01 mm inside the plug
  envelope, and the leg links pass at 0.85 mm. These are small re-routes.
- **Assembly order:** fit the PHR-4 plug before the converter goes in. Afterwards there are only 2.55 mm between plug
  and converter.
- **Rejected:** side-entry S4B-PH-K-S. Plugging from below overlaps OpenRB components by 23.9 mm³; plugging from above
  overlaps JP1 and the terminal block by 39.5 mm³. The layout figure gives 4.8 mm tall, 7.6 mm deep, and (6.25) and
  (9.6) mm from the pin row; reading those two bracketed values as header front and plug rear is inference.
- **Not checked:** a plain 2.0 mm male pin header with a loose 2.0 mm crimp housing. It has no latch on a walking
  robot, and no sourced dimensions were found. The Yeonho 20010HS housing is the part ROBOTIS designed J12 for, but no
  current stock was found.

## DFR1202: adapter board with a 6-way screw terminal block

What the converter offers:

- **Official (DFRobot product page):**
  - Input 6 to 24 V, output 5 V ±1%, at most 16 A out, 30 × 26 × 8 mm.
  - Pins VIN, GND, VOUT, plus EN, AGND and PGOOD.
  - "A thermal pad on the back of the module allows for soldering to a large copper area."
  - No pad drawing, pitch or mounting method is published, and there is no wiki page.
- **Measured (inference, about ±0.3 mm):** a pixel measurement of DFRobot's photo by `measure_dfr_pads.py`. Results
  are in `dfr-pads.json`; DFRobot's pin image gives the same numbers within 0.2 mm.
  - VIN: 0.95 to 3.42 mm from the VIN end of the 26 mm edge.
  - GND: 10.88 to 15.37 mm.
  - VOUT: 21.95 to 25.43 mm.
  - Each pad is about 1.8 mm deep and is a row of plated half-holes, gold on both faces.
- **Why no connector goes straight on:** there are no through-holes, and the pads are 2.5 by 1.8 mm at the smallest.
  A clamp or header soldered flat on such a pad would hang its wiring force on a lap joint along the board edge. The
  pads also do not fall on a 5.0 or 5.08 mm grid. Pigtails into a lever connector would still be wires soldered to
  the board, so they break the rule.

Proposed parts:

- **Adapter board (custom, inference):**
  - 1.6 mm FR4, 2-layer, 2 oz copper, about 23 × 13.5 mm (y ±11.5, z -11.5 to +2.0).
  - It sits against the converter's bare back face (x -37.0 to -35.4) and overlaps the converter's bottom 5 mm.
  - Three lands under the castellations, extended 1 mm past the converter edge for the solder fillet.
  - Traces at least 2 mm wide to the block (inference).
  - The thermal pad stays unsoldered, as in V1.8. It sits above the overlap.
  - The board stays inside |y| 11.5, so it passes between the pack lips (|y| 11.9 and up) with 0.4 mm in the final
    pose.
- **Clamp:** Same Sky TB0011-350-06 (GR green or BE blue), soldered on the adapter's cover side.
  - Wires enter from below and the screw heads face the cover, so the screws are reachable with only the cover off.
  - Datasheet: 3.5 mm pitch, 21.0 mm long, 8.50 mm tall, 6.90 mm deep, 1.10 mm holes.
  - Rated 7 A (UL) or 10 A (IEC) per pole, 300 V or 250 V.
  - Takes 24 to 18 AWG, strip 5 to 6 mm, M2 screw at 0.2 N·m.
- **Pole order (inference):** VIN, GND | ORB +, ORB − | PI +, PI −, with each pair side by side. The adapter joins
  GND to poles 2, 4 and 6 and VOUT to poles 3 and 5. Mark + and − on the silkscreen.
- **Wires against rating** (gauges from `steps.py`; currents from the guide and `sourcing-policy.json`):
  - Input pair: 18 AWG, 3.25 A, the charger's 20 V / 65 W contract.
  - ORB pair: 20 AWG, 3 A. ROBOTIS rates all OpenRB DXL ports together at 3 A, and step `current` accepts short
    bursts above that.
  - PI pair: 22 AWG. Policy item `pi_gpio_power` asks for 1.5 A or more per contact.
  - All three gauges are inside 24 to 18 AWG and all three currents are below 7 A. The far ends are unchanged: the
    XT30 male, the OpenRB terminal block, and the Pi header sleeves.

Fit results (`fit-results.json`, candidate `DFR-adapter-TB6-rear`; block top at z -3.6, 0.6 mm under the converter's
pad edge, inside the pack's DFR pad room):

- **Adapter alone (`DFR-adapter-only`):** fits with no overlap. It sits 0.4 mm from the lips and 0.44 mm from the
  OpenRB stacking sockets. The drop-in from 35 mm above is clear, 0.41 mm from the OpenRB at the closest; the 0.0 mm
  reported against the pack is the converter's designed seat on its feet.
- **With the block, as the pack is now:**
  - The block overlaps the cover by 72.45 mm³: 0.5 mm deep over x -45.5..-45.0, y ±10.5, z -10.5..-3.6. The block is
    8.5 mm tall and only 8.0 mm lies between the converter face and the cover.
  - It overlaps the feet by 1.30 mm³ in the final pose and 2.86 mm³ during the drop-in. That is 0.2 mm per side in y,
    at |y| 10.3..10.5, x -45..-38.5, z -4.2..-3.0, because the block is 21.0 mm long and the feet start at |y| 10.3.
  - Pin tails trimmed flush to 0.3 mm leave 0.14 mm to the OpenRB stacking sockets.
  - The wire-entry room is 0.5 mm from the cover.
  - Pack rooms are clear; the nearest, the leg-plug room, is 3.25 mm away.
- **Pack edits needed** (the script's `packEditsNeeded`; both remove material only):
  - A cover inner-face pocket at least 0.5 mm deep over that area. A 1.0 mm pocket would leave 0.5 mm clearance and
    1.0 mm of cover plate (inference until rerun).
  - Trim the feet's inner edge at least 0.2 mm, from |y| 10.3 to 10.8, for 0.3 mm clearance (inference until rerun).
  - Both edits are outside this folder's scope. Under `AGENTS.md` they need the full print-release gate before any print
    file.
- **Cables (information only):** the ORB pair, the Pi trunk and the 20 V pigtail start at the old pad joints, and the
  leg links R and L loop through the bay under the converter. All of them cross the new block (down to -1.2 mm) and
  have to be redrawn from the block's wire entries at z -10.5, then checked with `interference-audit/cables.py`.
- **Rejected layouts:**
  - `DFR-adapter-TB6-rear-low` (block below the feet, top z -7.6): the cover overlap is unchanged, the drop-in still
    grazes the feet (2.86 mm³), and the wire room enters the leg-plug room (26.4 mm³).
  - `DFR-adapter-TB6-front` (block on the OpenRB side): overlaps OpenRB parts by 138.7 mm³, and by 996.7 mm³ during
    the drop-in.
  - `DFR-adapter-TB4-front-TB2-rear` (split blocks): overlaps OpenRB parts by 4.4 mm³ and the cover by 24.15 mm³, and
    by 367.8 mm³ during the drop-in.
  - JST VH: the VHR housing is 10.5 × 13.3 mm, so it cannot stand in an 8 mm channel.
  - JST PH and XH: rated 2 to 3 A and topping out at 24 or 22 AWG, below the 3.25 A input on 18 AWG.

## Sourcing (`build-pack-20260913/procurement/sourcing-policy.json` and README, read 2026-10-12)

- **No proposed part sits under an explicit hold.** None of them appears as an item, so none has a recorded purchase
  decision. The policy's principle is that engineering need does not authorise buying, and a purchase needs a recorded
  sourcing decision first.
- **RoboClub first:** the procurement README says crimp contacts, header housings, wire and consumables come from
  RoboClub first. That covers the PHR-4, the SPH-002T-P0.5S contacts and any wire.
- **New decision needed:** the B4B-PH-K-S header, the TB0011-350-06 block and the custom adapter PCB each need one.
- **Replacement converter:** this would touch `shared_regulator`, which was bought and received as the DFR1202. The
  older regulator items (`motor_reg`, `logic_reg`) are `review_hold`.
- No order was placed and no cart was touched.

## Official versus inference

- **Official:**
  - ROBOTIS e-manual and schematic: J12 part and pin names; board 25 × 66 mm.
  - Yeonho 20010 datasheet: pitch, rating, through-hole wave soldering.
  - JST PH datasheet: dimensions, hole size, rating, contact wire ranges.
  - JST VH datasheet: housing size, rating.
  - DFRobot product page: ratings, size, pin names, thermal-pad note.
  - Same Sky TB0011-350 datasheet: dimensions, rating, wire range.
- **Measured from repo geometry by the scripts:** J12 hole positions, pitch and 0.8 mm diameter (ROBOTIS-derived mesh,
  not the Gerber drill file), and every gap and overlap above.
- **Inference:**
  - Pin order of J12 in the pack.
  - The DFR1202 pad sizes, which are a photo measurement.
  - The PH side-entry reading.
  - Wire-turn room, pin-tail trims, adapter layout and pole order.
  - The pocket and trim sizes with margin.
  - Hand-crimp route and trace width.

## Open items

- **Owner decision:** adapter PCB plus the two pack edits for the DFR1202, or one of the other DFR1202 routes in the
  verdict.
- **J12 drill size:** the 0.8 mm figure comes from the 3D model. ROBOTIS Gerber download no=2167 was not opened here.
  Check it against JST's 0.7 to 0.8 mm before soldering.
- **DFR1202 pads:** measure them with calipers on the owned board before laying out the adapter. The pad lengths and
  positions here come from a photo.
- **Which PH wall is 1.7 mm:** confirm on a real B4B-PH-K-S, so the wall can face JP1 as required.
- **If the DFR route is accepted:**
  - Make the cover and feet edits in the pack source and rerun `fit_connectors.py`.
  - Rebuild the assembly guide.
  - Run the interference-audit release gate: `build_solids.py`, `pairs.py`, `steps_audit.py`, `cables.py`.
  - Redraw the torso routes.
  - Update steps `uart-wires`, `dfr-leads` and `bench-test` and the two wiring helpers. None of this was done here.
- **Purchases:** record sourcing decisions before buying the header, the block or the adapter PCB.

## Files and rerun

- `fit_connectors.py`: envelope fit, final pose plus insertion paths. It writes `fit-results.json`; its `summary`
  block holds the headline numbers per candidate, and `recommendedPairJ12vsDfrAdapter` shows the two recommended
  changes together: the J12 plug is 2.12 mm from the adapter.
- `measure_dfr_pads.py`: pad measurement from the DFRobot photo. It writes `dfr-pads.json`.
- `run-report.json`, `run-report-pads.json`: bounded-runner reports for the last runs.
- Rerun from this folder:
  `/tmp/microduck-cad-venv/bin/python ../../../../build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py --max-mib 1400 --seconds 300 --wait-lock-seconds 60 --report run-report.json -- /tmp/microduck-cad-venv/bin/python fit_connectors.py`.
  For the pad measurement, use `--max-mib 512` with `measure_dfr_pads.py`.
- Inputs: the interference-audit solid cache through `ia_lib.load_solid` (keys within 8 mm of the pack, including
  `rear_pack`, `rear_pack_cover`, `openrb_board`, `regulator`, `imu_board`, `xt30_robot`, the hip motors and shells);
  `guide/print/world/openrb-board-upright.stl`; `guide/content/routes.json`.

## Sources (all accessed 2026-10-12)

- ROBOTIS OpenRB-150 e-manual: https://emanual.robotis.com/docs/en/parts/controller/openrb-150/
- ROBOTIS OpenRB-150 schematic, download entry https://www.robotis.com/service/download.php?no=2117. Read from the
  saved copy `microduck-sim/build-pack-20260913/redesign-20260913/workflow-review-20261009/sources/openrb-150-schematic-20231130.pdf`.
- Yeonho 20010 series datasheet: http://www.yeonho.com/app/product/ca/20010-NN.pdf
- JST PH datasheet: https://www.jst-mfg.com/product/pdf/eng/ePH.pdf
- JST VH datasheet: https://www.jst-mfg.com/product/pdf/eng/eVH.pdf
- DFRobot DFR1202 product page: https://www.dfrobot.com/product-2907.html
- DFRobot DFR1202 pin and dimension image: https://dfimg.dfrobot.com/enshop/image/data/DFR1202/pin.jpg
- Same Sky TB0011-350 datasheet (rev 1.0, 10/02/2025): https://www.sameskydevices.com/product/resource/tb0011-350.pdf
- Repo: `guide/print/rear-pack/README.md` and `pack_lib.py` (pack geometry, rooms, assembly paths), `guide/content/steps.py`,
  `guide/content/wiring/dfr1202.py`, `guide/content/wiring/openrb.py`,
  `build-pack-20260913/redesign-20260913/workflow-review-20261009/power-architecture.md`.
