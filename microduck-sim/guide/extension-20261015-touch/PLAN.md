# MicroDuck head touch for human–pet interaction (plan, 2026-10-15)

Problem IDs: P0 (a person's touch becomes a grounded feedback signal the duck can react to and later learn from) and
P5 (the body gains a sense without new structure). Status: proposal. Nothing is bought, no print file changes, no
firmware is changed. The A7Z arrives 2026-10-16; every bench step below runs on it.

## Goal

The duck notices where a person touches its head and what kind of touch it is: a tap, a pat, a stroke along the
head (and its direction), a hold, or a push. Each kind can trigger its own reaction (a quack, leaning the head into
the hand, stopping a walk). Sensing beak grip force is a later extension (last section).

## Design: three layers, cheapest first

1. **Push and press: the existing head servos (cost $0).** neck_pitch (ID 12), head_pitch (11), head_yaw (13) and
   head_roll (14) already hold the head in position mode. A hand pressing the head raises their Present Current (XL330 address 126,
   2 bytes, 1 mA) and their position error. `guide/firmware/pi/pi_bridge.py` already Sync Reads address 128
   (velocity) and 132 (position) as one 8-byte block; reading 126..135 as one 10-byte block adds current for every
   servo in the same packet. `guide/firmware/pi/current_watch.py` already reads address 126 and can record the
   signal today.
2. **Where and how: capacitive pads inside the cap (about $15).** Copper tape with conductive adhesive on the inner
   face of the white head cap, read by the touch inputs of a Seeed XIAO ESP32-S3 (see Hardware for why not an MPR121). A finger on the outside is
   sensed through the 1.7 mm PLA wall, so the pads are invisible and the cap needs no hole. Several pads in a row
   give stroke direction: front-to-back is a sequence of pad activations.
3. **Force-sensitive resistor (FSR), only if layers 1 and 2 are not enough.** See "Where an FSR fits" below.

### Why the FSR is not the main petting sensor

- The A7Z 40-pin header has no ADC function on any pin (Radxa pin table,
  https://docs.radxa.com/en/cubie/a7z/hardware-use/pin-gpio, read 2026-10-15). An FSR needs an ADC elsewhere (an
  ADS1115 board, or the XIAO ESP32-S3 chosen below) to give a pressure value.
- An FSR measures force pressed straight into its film. Inside a rigid cap it reads almost nothing, because the
  shell carries the load to its screws; it has to sit on the outside, which means a visible film and a new slot for
  its 60 mm tail (a print change and a print-gate rerun).
- One round FSR covers a 12.7 mm disc and starts reading at about 0.3 N (Adafruit 166,
  https://www.adafruit.com/product/166). A light stroke over a 100 x 70 mm crown misses most of it.
- It wants a flat, rigid backing. The crown is curved; an 18 mm film bent over it is preloaded and drifts.

### Where an FSR fits

Published pet robots and touch-gesture studies point the same way. Sony aibo ERS-1000 uses capacitive sensors on
the head and jaw and a combined pressure/capacitive sensor on the back
(https://helpguide.sony.net/aibo/ers1000/v1/en/contents/TP0001970140.html). Flagg and MacLean (2013) recognised nine
touch gestures on a furry robot at 94% per person and 86% across 16 people by combining conductive fur with a
piezoresistive pressure fabric; they rejected FSRs because they "don't function well on curved surfaces" and are
"insensitive to light touches"
(https://www.cs.ubc.ca/labs/spin/sites/default/files/local_pdfs/2013_AffectiveTouchGestureRecognitionForFurryZoomorphicMachine.pdf).
People stroke at about 0.4 N and 3-10 cm/s (Landsman, Kao and Gerling, IEEE World Haptics 2023,
https://par.nsf.gov/biblio/10475031), and an Interlink FSR switches on at about 0.2 N, so a light stroke sits at the
edge of what it can see even when it lands on the disc.

Pressure adds intensity: a gentle pat versus a hit, or a squeeze. Layer 1 (servo current) already gives that for the
whole head. If a local force reading is still wanted after the bench tests, one flat disc goes on the crown centre M
under a small printed flat seat: an Interlink/Alpha FSR or the DFRobot SEN0294 thin-film sensor (18.3 mm, 0.4 mm
thick, triggers at 20 g, $5.00, https://www.dfrobot.com/product-1844.html), read through a spare XIAO ADC pin. That seat and its tail slot are a print change and go through the print gate.

### Ready-made flexible sensors checked (2026-10-15)

- Bela Trill Flex (EUR 18, https://eu.shop.bela.io/products/trill-flex): a capacitive flex-PCB bar on I2C (Qwiic)
  that reports touch position along its length; the sensor part detaches and its flex design is editable. A drop-in
  alternative to copper tape for one crown stroke line, front to back.
- DFRobot SEN0704 (USD 15.90, https://www.dfrobot.com/product-3120.html): a 6 x 6 piezoresistive array, 15 x 15 mm,
  20 g trigger, UART at 5 V (needs level shifting to the A7Z's 3.3 V). The small patch sags only about 0.6 mm on a
  50 mm radius, so it suits a single outside "how hard" spot better than a round FSR.
- Conformable skins for compound curves exist only as quote-only industrial products, for example PPS Conformable
  TactArray (capacitive cloth, custom-moulded for compound curvature, https://pressureprofile.com/tactarray/conformable-tactarray)
  and XELA uSkin patches (from USD 900, CAN readout).
- Yong-Lae Park's lab (SNU) publishes soft skins (liquid-metal microchannels, optical waveguides, ionic-liquid
  tomography); no product, spin-off or licence of his skins was found on 2026-10-15. Obtaining one means building
  from the papers or a research collaboration.

## Head geometry (measured from the A7Z head CAD)

`analysis/cap_zones.py` samples the A7Z cap (`guide/print/a7z-head/head_cap_a7z-world.stl`) against every head part
(A7Z envelope, speaker and retainer, amplifier, camera, face panel, eye trim, head bottom, clips, jaw frame, neck
ring) and measures wall thickness and the free space under each point of the wall. It leaves out the head servos;
the pad distances were rechecked against every gate solid, servos included, under Hardware > Pads.

- The cap wall is 1.7 mm over most of the crown and sides (thicker only at the speaker collar and the face edge).
- The A7Z WiFi antenna (AC019 FPC) lies flat under the front of the crown, x 64..76, y -21..21. Copper there would
  detune it. Pads stay at least 10 mm behind it (x <= 54).
- The speaker and its retainer sit under the rear centre of the crown and the amplifier under the middle; pads avoid
  them so the tape can be pressed flat and so the I2S wires do not run across the pads.

![Proposed pads](touch_layout.png)

Proposed pads (robot frame, mm; free space under the wall measured by `analysis/layout.py`):

- **L1 / R1**, front crown left and right: x 30..50, |y| 12..32. Free space 8.7 mm minimum, 14 mm median.
- **L2 / R2**, rear crown left and right: x 2..26, |y| 20..34. Free space 4.5 mm minimum, 13 mm median.
- **M**, crown centre between the amplifier and the antenna: x 42..54, |y| <= 8. Free space 8.0 mm minimum.

Five pads leave four spare XIAO touch inputs (cheeks, or the body back later). Each pad is two or three side-by-side
strips of the 6 mm tape, about 20 x 18 mm, the size of a fingertip contact.

## Hardware

### Space in the head (measured 2026-10-15)

`analysis/head_space.py` voxelises the head at 1 mm from the 158 closed print-gate solids (the A7Z, its header
plugs, the camera, speaker, amplifier, the jaw servo ID 15, the head roll and yaw servos ID 14 and 13, their links,
the jaw support) plus every drawn head cable. Solids are grown by 1 mm, parts that move against the cap (servos 13
and 14, the yaw link, the roll rings) by 3 mm. `analysis/oriented_fit.py` then tries each board as a box in 6 yaw x
81 roll/pitch orientations on a 15 degree grid; `analysis/verify_pose.py` checks a chosen pose exactly against the
solids and cables.

- About 108 cm3 is free, but in thin pieces between the servos, the speaker and the cap: no 33 x 19 x 4 mm box fits
  anywhere upright or flat.
- The copper pads themselves need no space (0.07 mm tape on the cap's inner face, 4 to 14 mm of air under each pad).
- Adafruit 1982 MPR121 (33 x 19 mm) fits in one pose only, leaning about 60 degrees against the inner left-rear
  wall, with 0.8 mm to the cap and 1.2 mm to the jaw support, and only with its wires soldered flat. With its
  STEMMA QT plug (41 mm long) it fits nowhere. Rejected.
- A 22 x 18 x 5 mm board fits in 52 orientations in the same left-rear pocket (centres x -10..5, y 20..28,
  z 113..131), with several millimetres of slack. Exact check of the central pose (yaw 0, pitch -15, roll -60
  degrees, centre -1.7, 24.2, 123.4; `analysis/verify_xiao.txt`): 2.6 mm to the jaw support, 3.3 mm to the cap,
  4.4 mm to the lower head shell, 4.7 mm to the servo 14-15 cable, 6.9 mm to the head-roll servo. The cap-lift path
  with the board on the cap is not yet checked; `steps_audit.py` covers it once the board is added to the guide.

### Readout board: Seeed XIAO ESP32-S3

One 21 x 17.8 mm board does both jobs (https://wiki.seeedstudio.com/xiao_esp32s3_getting_started/, USD 7.49 at
https://www.seeedstudio.com/XIAO-ESP32S3-p-5627.html, read 2026-10-15):

- Nine capacitive touch inputs (D0-D5, D8-D10 = TOUCH1-9) read the copper pads directly; no MPR121.
- The same pins have an ADC, so a later FSR or thin-film disc needs no ADS1115.
- It reports to the A7Z over I2C as a slave: XIAO D5 (SCL) to A7Z pin 29 (PB2), D4 (SDA) to pin 31 (PB3), GND to
  pin 25, and 3.3 V from pin 17 into the XIAO 3V3 pin. In the A7Z guide pins 1, 3, 5 and 9 carry the BNO085, 7 and
  11 the OpenRB UART, 2 and 6 the 5 V lead, and 4, 12, 35, 39 and 40 the amplifier. The Radxa Camera 13M 214 covers
  the edge-row (even) plug ends of pins 10 to 34, so only inner-row (odd) pins are usable there.
- No stock overlay serves these pins. The overlays Radxa marks compatible with `radxa,cubie-a7z`
  (https://github.com/radxa-pkg/radxa-overlays, read 2026-10-15) are TWI2 (27/28, 28 covered), TWI7 and UART3
  (3/5, the IMU), UART2 (7/11, the OpenRB), UART4 (16/18, covered), SPI1 (19/21/23 with CS0 on the covered 24),
  I2S0 and PWM. `sun60iw2p1-twi0` (pins 29/31 as PG8/PG9) is for the CM-A7 on the RPi CM5 IO board only. Sharing
  TWI7 with the IMU would join a cap-side wire to the torso lead, so the cap could not come off.
- Pins 29/31 are PB2/PB3, whose mux includes TWI0 SCK/SDA (Radxa pin table; A7Z schematic V1.11 page 14), with no
  pull-up on the board. The bench test writes a custom overlay: TWI0 on PB2/PB3 with `bias-pull-up`, or `i2c-gpio`
  on the same two pins as the fallback, at 100 kHz with the XIAO's internal pull-ups on as well. The wiring is the
  same for both.
- Pad wiring: L1 to D0, R1 to D1, L2 to D2, R2 to D3, M to D8 (TOUCH1, 2, 3, 4 and 7).
- Firmware: Arduino `touchRead()` on each pad at 50 Hz; the A7Z reads the five values as one I2C register block
  (`Wire.onRequest`).

A header plus Dupont housings stands about 20 mm and does not fit the pocket, so the nine wires (five pad leads, four
A7Z leads) are soldered straight to the XIAO's edge pads. Shawn approved this on 2026-10-15 as an exception like the
amplifier (2026-10-13). The board sits on 1 mm foam double-sided tape on the inner left wall of the cap; no printed
geometry changes.

### Pads

Five pads: L1, R1, L2, R2 and M. The back-of-head pad N is dropped: it sits 2.0 mm from the head-roll servo (ID 14),
which moves against the cap, so every head roll would read as a touch. Measured distances from each pad to the
nearest part: L1 8.7 mm (amplifier), R1 9.4 mm (amplifier), L2 4.7 mm (speaker retainer), R2 4.1 mm (jaw support),
M 9.9 mm (A7Z). R2 is 8.4 mm from the head-yaw link; the bench test checks it for false touches during head yaw.

### Parts and cost

- Seeed XIAO ESP32-S3, USD 7.49.
- Adafruit 1128 copper foil tape with conductive adhesive, 6 mm x 15 m, USD 5.95 (or the tape already on hand).
- Hook-up wire for five pad leads and four I2C/power leads (owned).
- Foam double-sided tape for the board, the same as the speaker mount (owned).

Borrow first from RoboClub per `build-pack-20260913/procurement/sourcing-policy.json`.

## Software

- `touch_watch.py` (to write once the board is in hand): reads the XIAO's per-pad touch values over I2C (pins 29/31) for
  the five pads at 50 Hz in its own process and prints the per-pad delta. Thresholds come from recordings, not from
  library defaults, because the 1.7 mm wall lowers the signal.
- Gesture rules, version 1: tap = one pad, under 0.3 s; pat = two or more taps within 1.5 s; stroke = two or more
  pads activating in order within 1 s (direction from the order); hold = a pad on for more than 1 s; push = head
  servo current or position error above the level recorded at rest and while walking.
- Every event is logged with a timestamp. The same log later serves as human feedback for learning (for example,
  petting as a reward signal), which is why this sits under P0.

## Bench acceptance (A7Z in hand, cap closed)

1. With the custom overlay from Hardware loaded, the A7Z sees the XIAO on pins 29/31 (`i2cdetect`) and reads 50 Hz for 10 minutes without a failed read, and the XIAO runs from pin 17 without the A7Z 3.3 V rail dropping below 3.2 V.
2. A fingertip on each pad, through the wall, gives a delta at least five times the resting noise; neighbouring
   pads do not cross-trigger.
3. No false touch with the speaker playing and the camera streaming over WiFi.
4. WiFi throughput (`iperf3`) is the same with and without the pads fitted (antenna not detuned).
5. Twenty trials of each gesture by Shawn: at least 18 of 20 recognised; zero false events in five minutes of
   walking without touch.
6. Push: present current of the four head servos recorded at rest, while walking, and under a hand press; the press
   level separates from both.

## Beak grip force (later extension)

Cheapest first: the jaw servo (ID 15) Present Current already rises when the beak closes on an object; recording
it while closing on soft and hard objects shows whether it separates "holding" from "empty" without new parts.

For a real grip-force reading the most sensitive small option is a MEMS barometer cast in degassed silicone, the
TakkTile method: noise below 0.01 N and more than 100 Hz per element with inexpensive barometer chips, read over I2C
so the A7Z needs no ADC. The ready-made TakkTile/TakkStrip product is discontinued (takktile.com is parked; Stanford
BDML notes they are no longer made, https://bdml.stanford.edu/pmwiki/pmwiki.php/Main/TakkstripDemonstrator), so this
route means building the sensor from the published method (Tenzer, Jentoft and Howe, IEEE Robotics & Automation Magazine 21(3), 2014,
https://softroboticstoolkit.com/sites/projects.iq.harvard.edu/files/sorotoolkit/files/ytenzer_ram_memssensors_2014.pdf).
It needs a pocket in the jaw pad and careful degassing, so it is a separate design step. A thin-film disc (SEN0294,
20 g trigger) on the jaw face is the simpler but coarser alternative.

## Open decisions for Shawn

- Pad set: the six head pads above, or also the body back (the shells; wires would join the neck route).
- Whether an outside FSR is still wanted after the layer 1 and 2 bench results.
