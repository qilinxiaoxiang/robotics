# Pi-to-OpenRB UART with Dupont jumpers in the V1.8 rear pack

Problem P5/P6 (serviceable onboard wiring for the Pi-to-servo link). Study only, 2026-10-12: nothing outside this folder
was changed, and no print file was released.

## Owner decision (2026-10-13)

Shawn rejected the cover window ("背包上开个洞还是太丑了") and chose the soldered fallback: remove the 4-way header he
fitted in J12 and solder the two UART wires into J12 (pad 3 SERIAL_RX <- Pi pin 8, green; pad 4 SERIAL_TX -> Pi pin 10,
white; pads 1 GND and 2 +3V3 empty). Firmware: `firmware/openrb_uart_bridge_j12/` (Serial2; compiles, not bench-tested).
The wires follow the guide's `uart_lower` route from J12, which the cable audit already carries; the pack and cover are
unchanged. Option A below is kept as the record of the rejected alternative.

## Verdict

- **The guide hookup cannot be made to fit by cutting holes.** D13 and D14 (J7 sockets 7 and 6) sit directly behind the
  DFR1202 converter. From the socket tops to the converter's back face there are only **2.04 mm**. A straight Dupont
  plug needs 14 mm of housing plus the wire bend. Even a male pin bent flat needs about 2.9 mm. A window in the cover does
  not help, because the 8 mm thick converter fills the space in front of it. Freeing that column means raising the
  converter at least 4.65 mm, which puts its top at z 31.65, past the lowest torso-shell point over the channel (z 31.45).
  That is a new pack, a new cover and a shell change. Rejected.
- **Recommendation (option A): move the UART to the left header row, sockets 3 (A1) and 4 (A2), which sit below the
  converter.** Push two ordinary straight male Dupont plugs fully into them through **one 3.5 x 6.1 mm window cut in the
  printed cover**. The wires turn up just outside the cover, run up its back and over its top edge, then follow the
  guide's existing UART path to the plate notch.
  - What changes: the pack body stays as it is and nothing is reprinted. The window can be cut by hand in the cover you
    already printed. There are no purchases and no soldering.
  - Firmware: the bridge has to move Serial3 to these two pins. The SAMD21 can do this (same SERCOM5, other pads).
    A study sketch is in `firmware/`. It compiles (2026-10-12); it is not bench-tested yet.
  - The 20 V input lead has to drop 2.5 mm further inboard than the guide draws it (y -7.0 instead of -9.5) so it stays
    out of the plug column.
- **Ground wire:** not needed inside the robot. The Pi and the OpenRB already share the converter's GND pad through
  their 5 V pairs. On the bench, with two USB cables, plug a third jumper into J7 socket 4 (GND) as now. If you want the
  ground jumper inside the robot as well, a second 3.5 x 3.5 mm window over J7 socket 4 also fits (variant A+G, checked
  below).
- **Your J12 PH header stays unused.** It does not take Dupont: its pins are 0.5 mm square at 2.0 mm pitch, and a Dupont
  housing on it would hit the converter. It is the best fallback if you get a PHR-4 plug later (option E).

## The connection in plain words (for approval)

1. Sockets: hold the OpenRB as in the guide, component side up and USB-C at the top. Use the **left** row of black
   sockets this time, the row beside the left DYNAMIXEL port. Count down from the USB-C end. Socket 1 is AREF, 2 is A0,
   **3 is A1** and **4 is A2**.
2. Wires: the white jumper's male end goes into socket 3 (A1, the OpenRB sends) and its female end onto Pi pin 10 (RXD).
   The green jumper's male end goes into socket 4 (A2, the OpenRB listens) and its female end onto Pi pin 8 (TXD). The
   two wires still cross, TX to RX, as in the guide.
3. Cover window: cut a rectangle 3.5 mm wide and 6.1 mm tall through the cover. Look at the cover from behind the robot
   the way it sits when mounted, and cut on your **right-hand** side.
   - Horizontally: from 8.7 to 12.2 mm right of the cover's centre line. Measured from the cover's right edge (the wide
     part, 37.2 mm across), that is 6.4 to 9.9 mm in.
   - Vertically: from 31.9 to 38.0 mm above the cover's bottom edge.
   - Method: drill a 3 mm hole in the middle of each half and square the opening with a needle file or a hobby knife.
     Mark it with the cover screwed on if you can. The cover is mirror-symmetric, so it is easy to cut on the wrong
     side.
4. Plugging: with the cover screwed on, push the two male plugs straight in through the window. White goes in the lower
   socket (A1) and green in the upper one (A2). Push until each housing touches the socket top. The window only shows
   these two sockets: the holes of sockets 2 and 5 are hidden behind the window edges (0.23 mm each). The window is too
   short for a plug sitting one socket off.
5. Wires outside: each plug's tail sticks out 2.0 mm past the cover. Bend the wires straight up along the cover's back
   and hold them flat with one strip of polyimide tape. Lay them over the cover's top edge into the gap under the shell,
   then forward to the plate notch. In the notch's upper row they go between leg link R and the Pi lead.
6. Taking the cover off later: pull the two plugs out first, from outside. Then undo the four cover screws.

## Numbers

All measured on the placed ROBOTIS mesh and the release solids unless marked as inference. Frame: robot, mm, x forward,
y left, z up.

- **Socket rows.** Both rows have their socket tops at x -34.96 and a measured pitch of 2.542 mm. J7 (the guide's row)
  is at y 9.93 and J6 at y -10.43.
- **Socket centres (z):**
  - J7: socket 4 GND -7.72, socket 6 D14 -2.67, socket 7 D13 -0.12.
  - J6: socket 3 A1 -10.29, socket 4 A2 -7.74.
- **Room behind the sockets:**
  - Socket top to the cover's inside face (x -45.0): 10.04 mm for every socket.
  - Converter box: x -45..-37, |y| <= 13, z -3..27. Socket top to its back face: 2.04 mm for J7 sockets 6 to 14 and J6
    sockets 6 to 14.
  - In the J7 4/6/7 column the converter is the first thing behind D13 and D14. The J7 GND column and the J6 A1/A2
    column are clear back to the cover. The one exception is the guide's 20 V lead, 1.34 mm behind J6 sockets 1 to 4.
- **Option A window:** y -12.20..-8.66, z -12.06..-5.97, through the 2 mm cover plate (x -47..-45). That removes
  43.1 mm³. The nearest cover hole is at (-16.1, -36.5).
- **Optional GND window (A+G):** y 8.16..11.70, z -9.49..-5.95, 3.54 x 3.54 mm.
- **Over the cover top:** the cover's top edge is at z 29.5, and the pack walls and cover lip are at 28.5. The lowest
  shell point over x -48..-27, |y| <= 12 is z 31.45 (left shell) and 31.71 (right shell). The wires pass at z 30.7.
- **Wire run:** from the plug tail to the notch exit is 76 to 79 mm. The guide's run from J12 is 39.7 mm. The UART
  jumper therefore gets about 39 mm longer than the guide's 445 mm cut length (which includes 190 mm slack), so about
  485 mm. A single 40 cm male-to-female jumper is too short at the guide's slack, so two jumpers joined end to end will
  be needed. Put the joint beyond the notch, in the neck bundle.
- **Bent-pin budget (inference):** Dupont male pins stick out about 6 mm. Bending one flat leaves about 3.4 mm to go
  into the socket, against 6 mm for a straight plug.

## Exact checks (manifold3d, `options.json`)

Gap is the exact minimum distance between two solids, and overlap is the volume they share. Cables are tubes on the
`routes.json` centrelines with the guide's radii.

- **Option A, two plugs seated:**
  - Each plug's face sits on its socket top (0.05 mm, as modelled).
  - Plug A1: cover window edge 0.50 mm, re-routed 20 V lead 0.96 mm, pack 1.90 mm, leg link L 2.20 mm.
  - Plug A2: cover 0.50 mm, pack foot 0.76 mm, 20 V lead 0.96 mm, converter 3.47 mm.
  - No overlap with the board, converter, IMU, motors, shells or the pack.
- **Insertion:** each plug slides straight in along +x from 25 mm behind the cover. It clears the window by 0.50 mm all
  round, the pack by 0.76 mm or more, and the 20 V lead by 0.96 mm.
- **Wires (flexible, information):**
  - A1 wire: leg link R 0.05 mm (side by side in the notch row), cover 0.45 mm, right shell 0.48 mm.
  - A2 wire: cover 0.45 mm, shell 0.53 mm.
  - The A2 wire meets the Pi lead (0.24 mm³) only at x -18..-16, z 38.6..41.4, past the notch. There the guide merges
    all these leads into the neck bundle. The guide's own UART route touches the Pi lead at the same place.
- **20 V lead re-route** (points in `options.json`; 55.7 mm long against the guide's 57.7 mm, so the cut length still
  covers it):
  - Plugs 0.96 mm, leg link R 0.27 mm, leg-plug room 1.50 mm, pack 0.37 mm, OpenRB 1.55 mm.
  - It touches the converter only at its pad joint, 0.10 mm³. The guide route's figure there is also 0.10 mm³.
  - The guide's own route would cut through the plugs: 7.6 mm³ at A1 and 3.3 mm³ at A2. That is why it must move.
- **Option A+G (third plug in J7 socket 4):**
  - Plug: Pi lead 0.27 mm, 5 V ORB pair 0.67 mm, cover 0.50 mm, pack 1.10 mm.
  - Its wire goes through the notch's lower row beside link N (0.004 mm³ touch) and leg link R (0.01 mm). It is tight,
    which is one more reason to leave the ground jumper out inside the robot.
- **Walking sweep** of everything option A+G adds outside the pack body: the plug tails, the wires on the cover back and
  the wires over the top. The script is `sweep_added.py`, the method and frames are those of `rear-pack/pack_sweep2.py`,
  and every one of the 304 253 recorded phase-1 frames was checked.
  - Adopted frames (283 500): no leg part came within the 5.1 mm screening distance on either side. By the method's
    bound that means at least 2 mm everywhere. Hip bodies stay at least 8 mm away (the search cap).
  - Every run, including the excluded fall and blend runs: the closest is 2.41 mm on the left leg (exact, 9 flagged
    frames), and nothing on the right.

## Options, ranked

1. **A: J6 A1/A2 with straight Dupont through a cover window (recommended).**
   - Changes: one hand-cut window in the printed cover (or the same window in a cover reprint), a firmware pad change and
     the 20 V lead re-dressed. The pack body is unchanged and nothing is bought.
   - Contact: full 6 mm pin insertion (inference).
   - Cost: two plug tails 2 mm proud on the robot's back, and about 36 mm of taped wire on the cover's back face.
2. **E: your J12 PH header with a proper JST PHR-4 housing and SPH-002T-P0.5S contacts.**
   - Fits without cuts. The earlier study `../integrated/board-connectors/` gives 2.55 mm from the plug top to the
     converter and a clear board drop-in.
   - Firmware: Serial2 instead of Serial3.
   - Against it: it needs PH parts you do not have (RoboClub first, per the procurement README), so it means waiting.
     It is also not Dupont at the board end.
3. **B: J6 A1/A2 with the male pins bent flat, housings lying inside the pack.**
   - No cut. Only about 3.4 mm of pin goes into the socket (inference).
   - The housings hit leg link L (9.1 mm³) and the guide's 20 V lead (3.5 mm³), so both must be re-routed through the
     crowded bay under the converter.
   - The two jumpers stay permanently bent. Worse than A on every count except the cut.
4. **D: keep D13/D14.** Every variant collides:
   - Straight plugs: 51.6 mm³ in the converter at D13, 32.5 mm³ at D14.
   - Bent towards the centre: 29.9 mm³ and 19.0 mm³ in the converter.
   - Bent towards the +y wall: 16.9 mm³ in the side wall plus the converter, and the shell after a wall window.
   - Raising the converter by the 4.65 mm needed takes it under the shell (see Verdict). There is no room beside it
     either: it fills 26 of the channel's 27.2 mm. Rejected.
5. **C: plain Dupont female contacts on the J12 PH header.** Rejected:
   - The posts are 0.5 mm square. JST's contact name SPH-002T-**P0.5**S gives the post size, while Dupont contacts are
     made for 0.64 mm posts, so the contacts would be loose.
   - Pads 3 and 4 are 2.0 mm apart, but each housing is 2.54 mm wide: two housings overlap by 19.2 mm³.
   - A housing standing on the header top runs 51.6 mm³ into the converter and 9.4 mm³ into the cover.
6. **Fallback: solder the two UART wires onto the J12 header posts** (Serial2). It works in the space available, but it
   is the soldered-wire route you want to avoid.

## Firmware change (option A)

From the ROBOTIS schematic (repo copy `guide/data/sources/openrb-schematic.pdf`, J6 pins 3/4) and `variant.cpp`:

- A1 is PB02 = SERCOM5 PAD0, and A2 is PB03 = SERCOM5 PAD1. Serial3 already uses SERCOM5, on PB22/PB23 (D14/D13).
- The study sketch `firmware/openrb_uart_bridge_a1a2/openrb_uart_bridge_a1a2.ino` keeps the guide bridge. After
  `Serial3.begin()` it disables SERCOM5, sets TXPO = 0 (TX on A1) and RXPO = 1 (RX on A2), enables SERCOM5 again, muxes
  A1/A2 to SERCOM-ALT and releases D13/D14.
- Compile check, 2026-10-12: arduino-cli with core `OpenRB-150:samd@0.2.1` (ROBOTIS index
  `package_openrb_index.json`) and `Dynamixel2Arduino@0.8.1`, FQBN `OpenRB-150:samd:OpenRB-150`, run in a
  `debian:bookworm-slim` arm64 container because the core's macOS toolchain is x86-only. The A1/A2 sketch builds to
  12 740 bytes; the guide sketch builds to 12 632 bytes with the same setup. `firmware/compile.sh` reruns it.
- Not done: a bench test. First check: 1 Mbps loopback from the Pi with the GND jumper in J7 socket 4.

## Assembly order (option A)

1. Bench:
   - Flash the A1/A2 bridge.
   - Test with white A1 to Pi pin 10, green A2 to Pi pin 8, and black from J7 socket 4 to Pi pin 14 (separate USB
     supplies need the ground).
2. Pack, as in the guide:
   - OpenRB screws, leg links, the converter and its leads.
   - Dress the 20 V pair straight down about 1 mm behind the board at y -7, inboard of the left socket row, to the
     tether opening.
3. Jumpers:
   - Thread the female ends from the pack top through the notch's upper row (between link R and the Pi lead) into the
     neck bundle, then to the Pi.
   - Leave the male ends hanging behind the pack, over the place where the cover's top edge will sit.
4. Cover on, four screws. It can go on with the shells on or off, and the wires pass over its top edge.
5. Push white into the lower socket (A1) and green into the upper one (A2) through the window. Bend the wires up and tape
   them flat on the cover's back.

## Measurement versus inference

- **Official sources:**
  - ROBOTIS schematic and `variant.cpp`: header nets, J6/J7 order, Serial2/Serial3 pins and SERCOM pads.
  - JST PH datasheet: 2.0 mm pitch, header 6.0 mm tall, post size from the contact name P0.5.
  - The ROBOTIS e-Manual/Docs pages give the board size and Serial2, but the header order only as a drawing.
- **Measured from repo geometry:** socket positions and pitch, every gap and overlap above, the shell band, the window
  coordinates, and the walking sweep.
- **Inference:**
  - Dupont dimensions: 2.54 x 2.54 x 14 mm housing and about 6 mm of male pin (vendor listings: protosupplies 1-pin
    housing 14 x 2.54 mm, male crimp pin 18 mm long). Measure the jumpers you own.
  - Wire diameter 1.3 mm, and 3 mm of straight wire before a bend.
  - Bent-pin insertion length.
  - Whether the firmware pad move runs (it compiles).
  - Shared ground adequacy. Estimate: ORB black, 20 AWG, about 0.12 m at 3 A, drops about 12 mV, and PI black, 22 AWG,
    about 0.5 m at 0.5 A, drops about 13 mV. That is far below the roughly 1 V logic margins. Not measured.

## Open items

- **Owner approval:** the window in the printed cover changes printed geometry. Under `AGENTS.md` the connection method
  needs Shawn's confirmation before it shapes printed geometry.
- **Release gate:** if the window goes into a reprinted cover file, run the assembly-guide rebuild and the
  interference-audit gate (`build_solids.py`, `pairs.py`, `steps_audit.py`, `cables.py`) before release.
- **Guide updates (not done here):**
  - Steps `uart-wires`, `flash` and the pack/cover steps.
  - `wiring/openrb.py`, `routes.json` (`uart_lower` and `vin20`) and the firmware path.
- **Firmware:** bench-test the A1/A2 sketch (it compiles).
- **Jumpers:** measure the owned Dupont jumpers (housing length, pin length) and check the jumper length or the joint
  location.

## Files and rerun

- `scripts/run_all.sh` reruns everything under the bounded CAD runner, one exclusive job at a time, retrying while
  another CAD job holds the lock:
  - `measure_sockets.py` writes `sockets.json`.
  - `options.py` writes `options.json` and `study-solids/`.
  - `render.py` writes `png/`.
  - `sweep_added.py` writes `sweep-uart-left.json` and `sweep-uart-right.json`.
  - `summarize.py` writes `pack-uart-study.json`, the headline numbers.
- Run reports are in `run-report-*.json`. Peak memory was 195 MiB for options and 688 MiB for the sweep, and the sweep
  took 130 to 233 s.
- Study solids (not release files): `cover_with_window_A.stl`, `cover_with_windows_A+G.stl`, `plugs_A.stl`,
  `plug_GND.stl`, `wires_A.stl`, `wire_GND.stl`, `vin20_rerouted.stl`, the window cutters, and
  `added_outside_pack_A+G.stl` (the sweep target).
- PNGs:
  - `1-section-J7-why-not.png`: D13/D14 behind the converter.
  - `2-section-J6-option-A.png`: the plugs, window and wire run.
  - `3-rear-view-windows.png`: cover windows over the socket map.
  - `4-top-run-z30.7.png`: the wires over the cover top edge.

## Sources (accessed 2026-10-12)

- ROBOTIS OpenRB-150 e-Manual https://emanual.robotis.com/docs/en/parts/controller/openrb-150/ and ROBOTIS Docs
  https://docs.robotis.com/docs/parts/controller/openrb-150 (board 25 x 66 mm, MKR pinout, Serial2).
- ROBOTIS schematic, download https://www.robotis.com/service/download.php?no=2117, read from the repo copy
  `guide/data/sources/openrb-schematic.pdf` (J6/J7/J12 nets).
- OpenRB-150 `variant.cpp` / `variant.h`, repo copies in `guide/data/sources/` (A1 = PB02 SERCOM5/PAD0, A2 = PB03
  SERCOM5/PAD1, Serial3 = SERCOM5 PB22/PB23).
- JST PH datasheet https://www.jst-mfg.com/product/pdf/eng/ePH.pdf (copy in the session scratchpad).
- Dupont housing and pin listings: https://protosupplies.com/product/2-54mm-male-pins/ (vendor data, inference only).
- Repo: `guide/print/rear-pack/` (pack features, rooms, sweep method), `guide/content/steps.py` (step `uart-wires`),
  `guide/content/routes.json`, `../integrated/board-connectors/README.md` (J12 PH fit).
