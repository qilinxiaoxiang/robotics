# MicroDuck component bring-up — one source, two suppliers

Revision: **phase1-single-source-r2** · 13 September 2026 · Problems P5/P6

**Project goal:** Build a low-cost MicroDuck for camera-guided beak pickup and reinforcement-learning experiments: perceive the target, align, grasp, lift, and assess success. Continue from the completed jaw training. Use one power source and consolidate purchases.

**Existing training:** recorded held-out results are 0/12 before training, 12/12 after training, and 12/12 for the scripted controller. The learned jaw uses simulation observations. See the [training evidence](../../microduck-simulator/rl/RESULTS.md) and [canonical project context](../../PROJECT-CONTEXT.json).

**Incomplete project handoff:** the current software package supports component bring-up. Camera capture, visual alignment and transfer of the trained jaw to real observations remain missing. The camera is required for the pickup goal. The listed order excludes camera/audio additions while their integration review is open; it is not the complete visual-pickup purchase list. The [project check](project-context-review.json) rejects that complete-project claim.

Assemble the 15-servo chassis, including ID15 jaw, using the existing Xiaomi power bank as its single source. A USB-C receiver requests 12V and one regulator supplies 5V to both motors and Pi. These source parts stay beside the test lane, with one bundled tether into the duck. Keep the borrow-first Pi Zero 2 W and RoboClub printing/fasteners/consumables route.

## Work in this order

1. Record delivery of the servo order already placed. Review the remaining DigiKey selection and required camera integration. Settle the borrowed Pi/header/microSD and club fastener, wire and test-tool resources before scheduling assembly.
2. Print the [85-instance, six-plate Phase 1 queue](PRINT-LIST.md). Check the jaw sliding fit and idler screw fit before repeating assembly. Do not print the legacy 89-instance queue.
3. Prepare the frozen software and calibrate the torso IMU before connecting motors. Prepare and test the single-source power assembly with external loads.
4. Connect one motor at a time, assign IDs1-15 and pass the Wizard small-motion checks. Assemble and test the jaw, then torso, legs and head.
5. Complete supported standing, walking/stopping and pickup component tests, then five consecutive bring-up trials. This intermediate check is operator-controlled walking 0.3m to a prepositioned soft foam object, stopping, lifting at least 10mm, holding three seconds and releasing. Passing it does not complete the visual-pickup goal.

Fill the [physical acceptance record](ACCEPTANCE-RECORD.md). Actual hardware tests remain zero. The supplied checks cannot establish actual borrowed stock or physical performance before assembly.

## Procurement record

**Recorded merchandise: $507.73.** The recorded shipping/tariff estimates add $27.97, for **$535.70 before any additional final-checkout tax**. The user reports the servo order has been placed; the ROBOTIS figures below are historical and are not a repeat-purchase instruction. DigiKey's eight recorded lines exclude the required camera addition.

- ROBOTIS: shipping $16.74; tariff estimate $0.00; displayed total $454.39.
- DigiKey: shipping $4.99; tariff estimate $6.24; displayed total $81.31.

### ROBOTIS US — $437.65 — Ordered, per user report

[Historical supplier cart](https://robotis.us/cart)

- **14 × Smart servo:** ROBOTIS DYNAMIXEL XL330-M288-T / 902-0163-000. $384.86. [Product](https://robotis.us/products/dynamixel-xl330-m288-t)
- **1 × Servo bus controller:** ROBOTIS OpenRB-150 Starter Kit / 902-0184-000. $52.79. [Product](https://robotis.us/products/openrb-150-starter-kit)

### DigiKey — $70.08 — Incomplete for visual pickup

[Open existing cart](https://www.digikey.com/ordering/shoppingcart)

- **1 × Body inertial measurement unit:** Adafruit BNO085 / 4754. $29.50. [Product](https://www.digikey.com/en/products/detail/adafruit-industries-llc/4754/13426653)
- **1 × IMU four-wire adapter:** Adafruit 4397 STEMMA QT/Qwiic JST-SH4 to female sockets, 150mm. $0.95. [Product](https://www.digikey.com/en/products/detail/adafruit-industries-llc/4397/10824270)
- **2 × Main fuse:** Littelfuse 0251010.MXL, 10A axial / DigiKey F2320-ND. $2.48. [Product](https://www.digikey.com/en/products/detail/littelfuse-inc/0251010-MXL/700757)
- **10 × Branch fuses:** Littelfuse 0251003.MXL, 3A axial / DigiKey F2315-ND. $9.45. [Product](https://www.digikey.com/en/products/detail/littelfuse-inc/0251003-MXL/700737)
- **2 × Pi Micro-B connectors:** Adafruit 1826 USB DIY Slim MicroB plug. $1.90. [Product](https://www.digikey.com/en/products/detail/adafruit-industries-llc/1826/5629443)
- **1 × OpenRB USB data cable:** Adafruit 4472 USB-A to USB-C data/sync cable, 6 inch. $2.95. [Product](https://www.digikey.com/en/products/detail/adafruit-industries-llc/4472/11587359)
- **1 × USB-C power receiver:** Adafruit 5991 HUSB238 switchable USB PD receiver. $9.95. [Product](https://www.digikey.com/en/products/detail/adafruit-industries-llc/5991/24892287)
- **1 × Common 5V regulator:** DFRobot DFR1202, 6-24V input, 5V output. $12.90. [Product](https://www.digikey.com/en/products/detail/dfrobot/DFR1202/27526972)

Fourteen standalone motors plus the motor in the Starter Kit give **15**. Ten 3A fuses supply nine installed and one spare; two 10A fuses supply one installed and one spare. Two MicroB plugs make the compact Pi power and data connections. Adafruit's four duplicate lines have been removed and its cart is empty. Other historical carts are not buying destinations; the unrelated preexisting Pololu $8.49 item is excluded.

The [actual same-parts whole-order comparison](../procurement/ORDER-COMPARISON.md) independently checks supplier consolidation: two stores total $535.70; the temporarily reconstructed three-store orders quote $541.75, both before sales tax. Consolidation alone saves $6.05. Afterwards the two-store basket was restored and Adafruit returned to zero items.

## Existing resources needed for assembly

- Borrow a Pi Zero 2 W with fitted 40-pin header, microSD (at least 16GB), card reader and access to Imager. Confirm the exact board and accessories; another Pi model changes fit and power requirements.
- Use the existing Xiaomi PB1033MI 33W bank and its intact attached cable. The receiver and regulator stay on an insulated ventilated fixture beside the lane; no new onboard mass is introduced in Phase 1.
- Use club PLA/printer, **1m per color 16AWG wire**, **2m per color 20AWG wire**, solder, heat-shrink, ties, glue and fasteners. Check the exact **M2.6 × 6 TAP** idler screws; ordinary similarly sized machine screws are not interchangeable. The assembly section lists the retained lengths and printed bearings.
- Use club soldering tools, meter, adjustable electronic load and transient/current measurement equipment, caliper, screwdrivers, marker, scale and fall-catching support. Arrange a ventilated insulating fixture for the source modules. Copper prototyping board/thermal assembly may be needed if the converter fails its initial thermal test; do not buy a second source as an unreviewed workaround.

These are requirements, not verified claims of club stock. Purchasing holds remain in force. [Detailed sourcing policy](../procurement/sourcing-policy.json).

## Connector basics and OpenRB preparation

A **terminal** is a wire connection point; the receiver's screw terminal clamps stripped wire. Its screw does not enter the USB plug. A **regulator** changes the received 12V to steady 5V. A **branch** splits that same 5V source to different loads. A **fuse** opens after sufficient overcurrent and time; it does not regulate voltage. **AWG** describes wire size: 16AWG is thicker than 20AWG. **Strain relief** transfers a cable pull to the supporting frame instead of the solder joint.

New OpenRB boards ship with the **usb_to_dynamixel** bridge. First test it; if other firmware is installed, follow the [official board-manager and firmware recovery instructions](https://emanual.robotis.com/docs/en/parts/controller/openrb-150/). Keep motors disconnected while uploading. The detailed power section establishes the USB jumper and data-only motor connection before the software's one-motor ID steps.

## Phase 1 assembly and test sequence

Revision: 2026-09-13. Advances P5, economical and serviceable hardware, and P6, controlled physical deployment.

Build the 15-motor chassis, including its moving jaw. Component bring-up uses a borrow-first Pi, the torso orientation sensor and the common regulated supply; the laptop provides supervised commands. The intermediate test is to walk toward a prepositioned lightweight object, stop, close the beak around it and lift it. Camera-based object finding and the trained jaw's real-observation interface remain required for the project goal in [PROJECT-CONTEXT.json](../../PROJECT-CONTEXT.json).

### Print and prepare

Use the [85-instance Bambu project](printing/MicroDuck-Phase1-85-instances-X1C-CoolPlate.3mf) and [exact Phase 1 print list](PRINT-LIST.md). This is 78 source/stock instances plus seven current parts. The count includes spare allowance: fourteen printed passive idlers and fourteen caps in total. It does not assert that every copy is installed.

Bambu Studio sliced all 85 instances across six plates. It predicts 372.97 g of PLA and 16 h 44 min 13 s of printing. These are slicer estimates. The saved settings are X1 Carbon, 0.4 mm nozzle, Cool Plate, PLA, 0.2 mm layers, four walls, 30% gyroid and automatic tree supports. Select the actual RoboClub printer, nozzle and plate before printing; another machine or plate needs a fresh slice. Printing materials remain RoboClub-first.

Keep these seven current parts, one of each:

- **Integrated torso/power support:** joins the original torso and motor interfaces and retains the future battery cradle and regulator shelves. The empty shelves can remain; do not cut them away or replace this structural piece with an older source print.
- **Small-regulator pocket cover:** close the empty pocket with four M2 × 12 machine screws. Remove the cover when Phase 2 needs the regulator.
- **Jaw-clearance head cap:** includes the OpenRB posts and clearance for the repaired jaw. It retains the future camera attachment.
- **Coaxial jaw motor support:** supports motor ID15 and its opposite sliding seat on the same rotation axis. It replaces source `community-24.stl`; no separate mouth bearing is required.
- **Torso IMU clamp and rear cover:** two parts that hold the BNO085 orientation sensor on the torso. The clamp grips the printed rails; it does not need a battery to be present.
- **Fuse carrier:** keeps the eight motor branch fuses secured. F0 and F9 sit at the external source; leave their carrier positions empty. The same branch harness can later receive power from an onboard regulator.

Defer the audio carrier, camera foot, camera cradle and voltage-alarm/switch carrier. Retain the face panel even before fitting a borrowed Pi: it is part of the head assembly and contains the future Pi mounting holes. The source cap, source power support and old motor support are superseded; do not mix them into this queue.

The [source part pictures](../assembly/images/07-print-catalog-1.png), [second catalog](../assembly/images/07-print-catalog-2.png) and [third catalog](../assembly/images/07-print-catalog-3.png) identify the otherwise unhelpful short source filenames. The phase print list gives every actual file and copy count.

### Tools and fasteners

Obtain the printer/material, digital caliper, small screwdrivers, side cutters, wire stripper, multimeter, soldering station, ventilation, heat-shrink tubing and general consumables from RoboClub first. A caliper measures the printed dimensions; a multimeter measures electrical voltage and checks whether two points are connected. Heat-shrink tubing is insulating plastic that shrinks around a joint when warmed.

The fifteen motor packages provide 90 M2 × 6 TAP and 150 M2 × 8 TAP screws. **TAP means a screw that forms its thread in the matching plastic hole.** Keep these apart from machine screws, which fit matching threaded metal nuts or holes.

For a 3 mm printed frame on the servo output, use the supplied M2 × 6 TAP screws. ROBOTIS warns that an M2 × 8 at that output location can enter and damage the motor case. Measure each distinct case-side printed stack before repeating it; the inventory count alone does not choose the correct screw for every hole. [ROBOTIS assembly guidance](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/#how-to-assemble)

Additional fixed Phase 1 mounting quantities are:

- OpenRB: four M2 × 18 machine screws and four M2 nuts.
- Empty regulator-pocket cover: four M2 × 12 machine screws into the existing plastic pilot holes.
- Fuse carrier: four M2 × 20 machine screws and four M2 nuts. With the regulator absent, the modeled carrier post, shelf and spacer stack is 15.5 mm. A 20 mm screw leaves 4.5 mm for the nut and exposed end; inspect the real stack before tightening. The board is not needed to support the carrier.
- IMU clamp: two M2 × 5 screws. IMU rear cover alone: four M2 × 6 screws. The older four M2 × 8 selection included the now-deferred alarm carrier.
- Borrowed Pi Zero 2 W: four M2.5 × 6 tapping screws into the face-panel pilot holes, no nuts. Verify board/thread fit before tightening.
- Passive idler/cap center screws: up to fourteen **ROBOTIS BHS M2.6 × 6 TAP**, one per installed pair. These are absent from the standalone servo package. Exact club stock must be checked; an ordinary M2.5 or M2.6 machine screw is not a verified substitute. The sourcing policy does not assume they are available.

### 1. Check one motor before assembling the body

Leave links and the beak off. Connect one unassigned motor at a time through OpenRB using the Phase 1 limited bench-power procedure. Read its model, firmware and position. Assign its ID, read the ID back, and attach a physical label.

An XL330 has a stationary case and a rotating output face. The case attaches to one side of the joint; the output attaches to the other side. Its output mounting face is already integrated. An extra set of fifteen output horns is unnecessary.

Use the [15-motor location drawing](../assembly/images/06-servo-map.png). IDs1–5 form the right leg and IDs6–10 the left leg, foot upward. IDs11–14 move the head/neck. **ID15 moves the jaw.** Slowly center each unloaded motor, turn torque off and install the link. The encoder midpoint 2048 is an electrical reference; the model's zero and the assembled standing position still need separate calibration.

![All fifteen motor locations, including the jaw](../assembly/images/06-servo-map.png)

**Pass:** every motor responds under its intended unique ID, turns in the checked direction and shows no hardware error. Record the position before and after tightening. A duplicate ID or unexpected motion is corrected on the single-motor setup before adding another motor.

### Perform the first small motion in DYNAMIXEL Wizard

Install **DYNAMIXEL Wizard 2.0** from ROBOTIS's [Mac download and installation page](https://emanual.robotis.com/docs/en/software/dynamixel/dynamixel_wizard2/#install-mac). This app lets you read and change one motor's named settings. Use the official installer; complete any macOS installation prompts yourself. Keep the external motor supply disconnected while moving USB connections. Connect OpenRB directly to the Mac with a borrowed USB-C data cable for this test; disconnect its Pi USB cable. Keep the motor supply on the external fused route described below, with OpenRB motor VDD isolated.

1. After assigning an ID with the runtime's one-motor tool, leave that motor unloaded and isolated. Close the Pi controller. In Wizard choose **Tools > Options > Scan**, select the OpenRB port, Protocol 2.0, 1,000,000 baud and that ID; then **Device > Scan**. Require one XL330-M288-T response. A factory motor that has not been assigned uses 57,600 baud; finish the ID procedure before this test.
2. Select that device and keep **Torque OFF**. Set and read back Drive Mode raw0 (normal direction, velocity-based profile, automatic torque-on disabled) and Startup Configuration raw0; confirm Operating Mode is3 for this unloaded check. Set Min Voltage Limit to3.7V, Max Voltage Limit to6.0V and Shutdown to53 (0x35); read them back. In a raw-value display the voltage values are37 and60. The final runtime later sets the jaw to mode5.
3. Set Profile Velocity to raw5 for this unloaded test. Read Present Position and copy it into Goal Position **before** enabling torque. In position mode, use its equivalent position in the 0–4095 range. Keep fingers clear of the output. Turn Torque ON and require that it holds near the starting position.
4. Change Goal Position by about 50 raw counts (4.4 degrees), keeping it within0–4095. Confirm smooth travel, then return to the starting value. Check a small motion in the opposite direction if it remains within the range. Stop immediately for unexpected travel, binding, a power-limit failure or a hardware error. Finish with Torque OFF, disconnect motor power and label the passed unit.
5. Before attaching its link, reconnect motor power and repeat steps2–3, including reapplying Profile Velocity raw5 and preloading the actual position; power cycling resets the profile setting. Then move the still-unloaded motor slowly to raw2048. Finish with Torque OFF and motor power disconnected before assembling the link against the location drawing. The later model-coordinate and physical-pose checks still apply.

After assembling and wiring a branch, support all its joints so they cannot fall when torque is off. Connect only that branch to motor power. With Torque OFF, select each individual ID, reapply/read Profile Velocity raw5 after every power cycle (it resets in RAM), verify Drive Mode0 and Startup Configuration0, preload its own current position, and turn it on one at a time; never broadcast one position value to a pair of different joints. First test holding, then only a small motion with visible clearance. Measure branch current and endpoint voltage against the power section. Turn all tested motors off before disconnecting or adding the next branch. Repeat all eight groups. These are commissioning tests; Wizard does not execute the walking policy. Quit Wizard, remove motor power and reconnect OpenRB to Pi before starting the main runtime. The runtime restores the gait settings and applies separate jaw current control.

### 2. Build the jaw as an early independent module

Use the repaired jaw motor support and cap. Attach the moving jaw frame `community-4.stl` to ID15's output face. The opposite jaw boss fits into the support's integral sliding seat. A sliding seat is a smooth printed support around the opposite end of the rotating part; its axis must align with the motor shaft. It is not a rolling ball bearing.

The fixed upper lip is `community-40.stl`; the lower lip `community-42.stl` moves with the jaw. Their source names include “soft,” but the inherited print material is PLA. Do not assume those printed surfaces are rubbery. Keep the structural jaw frame rigid.

Dry-fit each lip fully onto its own matching frame. The selected Phase 1 retention method is a small amount of club-sourced **cyanoacrylate adhesive, also called CA or superglue**, at the exterior mating edges after alignment. Keep the bond out of the gripping surfaces, sliding seat and motor. Do not add a thick glue layer between the seating faces, and never glue the two opposing lips together. Cure for the actual adhesive's stated time with electronics removed from the work area. Gently pull each pad before powering; it must remain seated without shifting. This is an engineering assembly choice whose retention is accepted by the physical grip test. [Prusa's material guide supports CA for PLA](https://blog.prusa3d.com/the-great-guide-to-gluing-and-assembling-3d-prints_44908/).

![Jaw support and opening positions](../assembly/images/10-mouth-detail.png)

With power disconnected, move through a small opening, checking that the opposite support neither binds nor pulls sideways. Check that the lower pad follows only the lower jaw. The geometric scan checked 0–30 degrees in 0.5-degree steps; this is a candidate range to calibrate, not a preapproved hardware end-stop setting.

For this early module test, use Wizard with **only ID15 connected**. The full-body runtime expects all fifteen motors and is used after assembly. Support the jaw module on the bench. With Torque OFF and the output free to move gently, read Present Position at a small open position and at gentle closure; record these raw encoder values. Stay within the physical clearances and a maximum341-count span (about30 degrees); do not cross the0/4095 boundary. Set Operating Mode5, Current Limit150mA, Goal Current100mA and Profile Velocity raw5. Read back those values and retain the voltage/shutdown settings from the first-motor check. Changing mode can reset RAM settings, so set Goal Current and Profile Velocity after mode selection. Preload the actual current position as Goal Position before Torque ON. Then command only the measured open/closed values, watching for pinching, binding and current errors. Always Torque OFF before handling the mechanism. Re-capture the final jaw endpoints in the runtime calibration once all fifteen IDs are present.

Start with a measured, soft foam sample no heavier than 2 g. Use an 8 mm-thick gripping section approximately 20 mm wide. Support it at the middle of the beak so the test isolates gripping from walking and reaching. Jaw grip and attachment are physical measurements, not demonstrated by the CAD scan.

For this target, the separate [jaw-aperture check](jaw-aperture.json) samples a central 20 × 10 mm lip patch. At a modeled 20-degree opening, all nine sampled gaps exceed 14.79 mm, providing geometric room for the 8 mm gripping section. This checks the opening size; the first physical grip test still establishes whether the surfaces actually hold the foam.

**Pass:** five slow open/close cycles without binding, reset or lost ID; then five grips that retain the foam for three seconds after the object support is lowered by 10 mm. Record object mass, thickness, actual angle limits and motor current. If it slips, inspect alignment and contact first. Increasing force alone is not an accepted repair; a pad material/attachment change needs the same test again. This module test is an intermediate gate, not the final walking-and-pickup MVP.

### 3. Assemble torso, legs and neck

Assemble the torso base and integrated support around hip-yaw motors IDs5 and10. Leave the battery cradle and regulator shelves empty. Use the [leg exploded drawing](../assembly/images/09-leg-detail.png) and source-part catalog to keep mirrored parts on the correct side.

For the left leg, build from hip toward foot: ID10 → hip yaw/roll link → ID9 → hip bracket and ID8 → thigh → ID7 knee → lower-leg links → ID6 ankle → matched left community foot. Mirror that sequence for IDs5 through1 on the right. Add both thin thigh reinforcing plates.

![Leg parts and assembly order](../assembly/images/09-leg-detail.png)

Support both sides of each joint on the same rotation axis. Keep the community ankles, combined feet and printed sliding rings as a matched set. The fourteen printed idler/cap pairs are available stock; fit only the pairs required by the passive side at each station and record the leftovers as spares. The source motor mesh merges both flanges, so it does not establish a reliable installed count by itself.

Build the neck links and install ID12 neck pitch, ID11 head pitch, ID13 yaw and ID14 roll in the illustrated order. Fit the completed jaw/head module. Turn torque off while checking each joint's permitted small movement. Do not force a geared motor through resistance.

**Pass:** no scraping, cracked print, loose opposite support or wire obstruction; every actual joint location agrees with the motor-ID drawing. Record the fitted screw length for each repeated joint type in the [first-article record](../assembly/FIRST-ARTICLE.md).

### 4. Install control electronics and the fused harness

Mount the borrowed Pi to the face panel and OpenRB to its cap posts. Mount the BNO085 firmly in the torso clamp. Run the software section's sensor-only seven-pose calibration with motor power disconnected; it measures and saves the mounting rotation. Then run its separate signed-angle check. You do not need to guess an axis mapping or type a rotation into the program.

Follow the [Phase 1 power recipe](power-research.md) for the external 5 V supply and eight fused motor groups. Each servo receives its own power input. Motor power bypasses OpenRB's 3 A onboard distribution. The shared DATA wire carries commands; the common GND wire provides the electrical reference. The motor connector pin numbers are 1 GND, 2 VDD and 3 DATA; identify pins, not just wire color. The old onboard-battery wiring figures are reference only for branch organization.

The [fuse-loading drawing](../assembly/images/11-fuse-loading.png) and [tie-path drawing](../assembly/images/12-fuse-ties.png) show how the carrier retains insulated fuse bodies. Four ties with a maximum section of 2.5 × 1.1 mm fit the checked carrier slots. Use narrow flexible loops at moving joints. Route the single motor/logic tether with slack at all joints and use the empty battery-cradle passages for strain relief. Follow the current power section for F0/F9 at the external converter and F1-F8 in this carrier. The old fuse illustration is a retention reference only. Keep the master USB-C disconnect at the external receiver accessible. **Strain relief transfers a cable pull to the frame.**

Phase 1 still requires soldering for the fused power branches, insulated wire joints, modified DATA connections and the following two compact Pi plugs. The receiver has screw terminals, while the converter power pads require soldering. Use the club soldering station and inspect the completed harness before it goes into the robot.

![Fuse carrier loading; leave Phase 2 accessory positions empty](../assembly/images/11-fuse-loading.png)

![Fuse carrier tie passages and retention](../assembly/images/12-fuse-ties.png)

Use **two Adafruit 1826 bare MicroB plugs**, without their 26 mm plastic housings. Prepare them before putting the Pi into the head. Each completed plug, insulated solder joints and strain relief must fit the previously checked **14.5 × 9.5 × 7 mm** envelope. An arbitrary molded plug does not satisfy that check.

- **Pi data connection:** use the selected Adafruit 4472 USB-A-to-USB-C data cable. Replace only its USB-A end with one bare MicroB plug; keep the USB-C end intact for OpenRB. On the MicroB plug connect pin1 VBUS, pin2 D−, pin3 D+ and pin5 GND to their matching cable conductors. Preserve the twisted data-wire pair. Connect MicroB pin4 ID to pin5 GND; this selects the Pi's USB-host role. This cable goes into the Pi's port marked USB. It supplies OpenRB logic and carries data. It does not supply motor power. No separate OTG adapter is needed for this prepared cable.
- **Pi power connection:** use a 500mm maximum 20AWG red/black pair from the common 5V converter through the external F9 fuse. Solder the second bare MicroB plug: pin1 +5V, pin5 GND, pins2/3/4 unconnected. Insert in PWR IN. The bank powers the PD receiver; it does not connect separately to Pi. Follow the current [power recipe](power-research.md) for placement, voltage drop and the 4.75–5.25V measured Pi input gate.

Before plugging either cable into a board, use the connector drawing to identify all five MicroB contacts; viewing a plug from the opposite side reverses their apparent order. With all power disconnected, verify each intended end-to-end connection, verify no unintended shorts between adjacent pins, verify the data cable's ID-to-GND connection, and verify that the power cable's three unused pins remain isolated. Then measure source polarity and voltage at the completed power plug, check the insulated dimensions with calipers and perform a gentle pull test. See the [MicroB connector product drawings](https://www.adafruit.com/product/1826) and [USB envelope check](../assembly/usb-bare-plug-check.json).

The Pi supply test is 30 minutes with Wi-Fi, OpenRB and the IMU running, measuring 4.75–5.25 V at the Pi's actual 5 V/GND points with no resets or power-bank auto-off. A software status flag alone does not establish the voltage on Pi Zero. Confirm an already-soldered Pi header; otherwise fit the matching 2 × 20 header from club stock before attaching the sensor cable. BNO085 connections are Pi physical pin1/3.3 V to VIN, pin6 to GND, pin3/GPIO2 to SDA and pin5/GPIO3 to SCL. The selected STEMMA QT-to-female cable plugs into the sensor and these header pins.

With the single source disconnected, plug the keyed four-contact end of Adafruit4397 into either BNO085 STEMMA QT socket. Connect the four individual female ends to the Pi header:

- **Red V+ → physical pin1, 3.3V.** Do not put this lead on a 5V pin.
- **Black GND → physical pin6, ground.**
- **Blue SDA → physical pin3, GPIO2**, the sensor-data signal.
- **Yellow SCL → physical pin5, GPIO3**, the sensor-clock signal.

These are physical header positions, not the GPIO numbers. Identify pin1 from the Pi's board marking and official header diagram before counting; do not guess from a rotated photograph. Verify continuity from the cable to the sensor's labeled connections before applying power. The colors follow [Adafruit's STEMMA QT specification](https://learn.adafruit.com/introducing-adafruit-stemma-qt/technical-specs); labels and measured continuity are the authority if using a different cable. Enable I2C and run the torso-axis procedure in the software section before enabling any motor torque.

**Pass before power:** correct polarity, no power-to-ground short, each removed branch fuse actually isolates its motors, no exposed conductor, and each gently pulled wire remains secured. **Pass with the robot supported:** every ID remains readable while joints are moved slowly, the Pi remains running, and loaded voltage/current meet the Phase 1 power limits.

### 5. Establish standing and walking before attempting pickup

Fit the robot's fall-catching support so it can move without carrying the robot's normal weight. Begin on a flat surface with the tether slack. Use the runtime's calibrated standing procedure before commanding travel. Confirm the torso sensor changes correctly when the robot is tilted by hand, and verify the stop action before increasing movement.

Measure and record completed robot mass. The printed support remains, but removing a battery and head electronics changes balance. The updated controller candidate passed [33 Phase 1 mass and gait/stop cases](simulation/README.md), including 4.0 V and 5.25 V supply assumptions, with prediction disabled. It retains the walking policy during zero-translation stopping and continues heading correction. The old controller passed only 20 of 27 phase-mass cases, so use the matched Phase 1 runtime rather than silently retaining the old transition. Actual mass, printed foot friction, sensor delay and tether pull still need the physical checks below.

**Standing pass:** maintain supported-but-not-weight-carried standing for 30 seconds with no reset, drifting joint, binding or protection event. **Walking pass:** walk 0.3 m, stop and remain standing for three seconds; complete five trials with no fall and no tether pull. Retain videos and current/voltage logs. A failure returns to its last passed module test rather than proceeding to pickup.

### 6. Complete the Phase 1 pickup task

Use the same weighed foam target. Put it on a known support in the robot's reachable beak path, with the target centered and its gripping section exposed. The human places the target and commands approach from the laptop. The robot must walk, stop, lower the head to the calibrated pose, close the beak and lift the object at least 10 mm for three seconds. Complete five consecutive trials.

The target support's height is calibrated from the assembled robot's actual reach; begin at an easy beak height, then lower it only after the prior height passes. Picking directly from the floor is a stronger reach/balance test. The old browser GroundPick behavior and isolated jaw training do not establish that the community physical frame can perform the same floor motion. Record the lowest passed target height explicitly.

**Component bring-up pass:** approach by walking plus grasp/lift succeeds five consecutive times, no person supports the object or robot during the attempt, no cable assists balance, and no power/thermal protection event occurs. Keep the initial object specification and placement fixed. This test covers supervised execution; passing it does not complete camera-guided learned pickup.

### Accessory integration

The retained cap, face panel and torso support keep the attachment points for the camera cradle/tilt foot, audio carrier, selected battery and both regulator positions. Print the four deferred accessories only when their hardware is selected. An onboard supply replaces the upstream tether connection; the fused motor branches stay.

Reweigh the robot, rerun standing/walking/pickup checks and recheck the head's complete motion after each module is added. A different Pi, battery size or camera needs its own connector and mounting check. Source CAD and current digital evidence remain in the [full assembly manual](../assembly/ASSEMBLY.md); its battery-specific assembly steps are deferred for Phase 1.

### Mechanical evidence and remaining measurements

The repaired jaw support is a single watertight mesh. Its added material clears 41 head objects; 61 sampled jaw poses from 0 to 30 degrees are collision-free in the checked digital assembly. The nominal opposite support has 0.2 mm radial and 0.3 mm flange clearance. These values become actual fit only after printing. [Support design](../assembly/mouth-support/design.json), [static check](../assembly/mouth-support/static-check.json), [motion check](../assembly/mouth-motion-coaxial-conditional.json).

The Phase 1 subset reuses these exact files and preserves their mounting interfaces. No arm is present: the head/neck positions the beak, and ID15 closes it. Lip friction, lip attachment, printed sliding fit, exact original per-hole screw stack, available M2.6 TAP screws and real floor reach remain arrival-dependent checks. Each has a specific test above; no physical print, assembly, walking or grasp result has been claimed.

## Build and test the power harness

### One existing power bank supplies the whole Phase 1 duck

Revision **phase1-single-source-r2**. Verified 2026-09-13; problems P5/P6. This is the current supply recipe. The before-repair adapter selection is preserved only in the audit archive.

### Selected source and two small modules

Use the existing Xiaomi 33W Power Bank 10000 (Integrated Cable), matching model **PB1033MI**. Its official single USB-C output lists **12V / 2.5A**. Use only its intact integrated USB-C cable. Do not charge another device or the bank during the test: the official simultaneous-output mode falls back to a combined 5V/3A. The bank and both modules stay outside the robot for the already selected tethered Phase 1.

Connect the bank to **Adafruit 5991**, a USB Power Delivery (PD) receiver. PD is the USB negotiation that asks for a supported voltage. With the source disconnected, set **only the 12V switch ON** and all other voltage switches OFF. Measure the negotiated output before attaching downstream equipment. This board is not a voltage regulator. Do not assume the all-OFF setting means 5V; it can request the highest available voltage.

Connect its positive terminal to **DFRobot DFR1202 VIN**, and its negative terminal to the module's power **GND**, using at most 150mm of 16AWG copper per conductor. Solder to the manufacturer's VIN/GND/VOUT power pads; use pad labels, not a guessed viewing orientation. Its **5V VOUT** and power **GND** feed both the motor and Pi branches. Leave EN, AGND and PGOOD unused; PGOOD's 5V level must not enter Pi GPIO. Secure the module on a ventilated insulating fixture, with no bare pads touching metal. At high load the manufacturer recommends transferring heat through the underside pad to a copper board; club soldering equipment and suitable copper prototyping board are required if the initial thermal test cannot pass. Do not wrap the module in foam or heat-shrink.

The two modules cost **$9.95 + $12.90 = $22.85** before tariff. The converter supports 6–24V input and 5V ±1% output; its large advertised current rating is not the bank's available current. DFR0753 costs $4.15 less but permits only 14V maximum input. The selected board tolerates the bank's possible 20V profile if the receiver is mis-set; it still requires correct 12V selection and measurement. No new battery, battery charger or wall adapter is selected.

[Official Xiaomi output profiles](https://www.mi.com/ph/product/xiaomi-33w-power-bank-10000-integrated-cable/specs/) · [Official PD support](https://www.mi.com/fr/product/xiaomi-33w-power-bank-10000-integrated-cable/specs/) · [Receiver instructions](https://learn.adafruit.com/adafruit-usb-type-c-power-delivery-switchable-breakout/pinouts) · [DFR1202 manufacturer specification and pad drawing](https://www.dfrobot.com/product-2907.html).

### Whole-system limit

The 12V/2.5A source offers **30W before conversion**, not 33W at every voltage. The commissioning screen is **5A total at 5V**, including all motors, Pi, IMU and OpenRB logic. Allocate up to 4A to motors and 1A to logic as an initial design assumption. These are not measured walking loads or physical electronic current clamps. A module labeled 16A does not make this a 16A supply.

The manufacturer reports over 90% conversion efficiency at 12V. At a deliberately lower assumed 85% efficiency and the output's 5.05V upper bound, 5A needs 29.71W before input-lead losses. That leaves little power margin in this pessimistic case. Input current must actually stay within 2.5A, measured output must stay within 5A, and the real walk/stop/pickup sequence must pass without a source reset. Do not size the robot by adding fifteen stall currents: stall is a jam/fault, not a normal walking workload. Conversely, the existing simulation's fitted winding-current proxy does not establish source-current headroom.

The [reproducible voltage-drop screen](power-screen.json) includes both wire directions, hot copper, the full tether, fuses, joints and contacts. It is a calculation under stated assumptions. Check its separate Pi and worst-motor endpoints. A shared source makes motor transients relevant to Pi stability; the physical test below therefore loads both branches simultaneously and includes stopping/regeneration.

### Assemble the motor harness

A **branch** is a separate wire path from the same power source. Two branches do not mean two batteries. The motor path bypasses OpenRB's 3A distribution and uses eight fused groups. The Pi gets its own positive/return pair from the same 5V output so motor wire losses do not also appear in the Pi lead.

### Prepare with all power disconnected

1. Source club soldering tools, flux, heat-shrink, wire stripper and a multimeter. Obtain at least **1m red + 1m black 16AWG** and **2m red + 2m black 20AWG** copper. These quantities include input wiring, tether, internal branches and preparation allowance; do not order from their historical wire suppliers.
2. Install **F0 = 10A** in the motor positive output at the external converter, before the tether; install **F9 = 3A** in the Pi positive output at the converter, before its lead. Individually insulate and secure their bodies and joints. Keep ground unfused. The order supplies one spare 10A fuse and one spare 3A fuse.
3. Prepare a paired 16AWG motor tether at most **500mm one way**. Inside the body, cut one 30mm and two 70mm pieces per color for the split trunk: each path totals at most 100mm. Prepare eight 150mm-per-color 20AWG motor branches. Do not lengthen a path without rechecking voltage drop and movement.
4. Retain the printed carrier for **F1–F8 = eight 3A motor fuses**. Its old F0 location stays empty because F0 is now at the external source. The old loading illustration demonstrates retention only, not the new fuse placement. Overall: **nine 3A fuses installed (eight motors + one Pi), one spare; one 10A installed, one spare.**
5. Fuses are supplemental fault protection. They open only after enough overcurrent for enough time. The bank's limited output may not blow a 10A fuse under every short; do not claim it will. The source and regulator also have their own electronic protection. Never intentionally short this assembly as an acceptance test.

### Make the positive and return fanouts

6. Strip about 5–6mm from an ordinary wire end, enough for the planned overlap, without cutting strands. Slide appropriately sized heat-shrink onto a wire **before** making the joint. Twist/tin stranded ends, mechanically overlap or wrap them, heat the metal joint and feed solder until it wets the strands. Allow it to cool without movement. There must be no loose strands, sharp projections or exposed conductor after insulation.
7. Positive path: motor-tether red (after the external F0) → 30mm red trunk → two 70mm red fanout trunks. Cut each 150mm red 20AWG branch into a 20mm fuse-input pigtail and a 130mm fuse-output lead. Each fanout trunk joins four 20mm pigtails, each going to its own fuse input. Each fuse output receives the corresponding 130mm lead. This avoids one eight-wire bundle and retains 150mm total 20AWG copper per positive branch. The pigtails fit between the fanout and the mounted fuse inputs.
8. Return path: motor-tether black → 30mm black trunk → two 70mm black fanout trunks. Each fanout joins the matching four black branch returns. There are no fuses in ground. Keep positive and ground fanouts physically separated and individually insulated.
9. A multiwire joint needs a heat-shrink sleeve large enough for the whole joined bundle and long enough to overlap intact insulation on both sides. Use adhesive-lined shrink from the club if needed to close gaps around multiple wires. Inspect all sides after shrinking. If a finished joint cannot be insulated securely, remake it; tape over an exposed solder bundle is not the intended construction.
10. Put each F1–F8 body in the printed carrier, with its leads insulated and strain-relieved. Keep the body-plus-insulation assembly inside the carrier's existing **24×5×5mm** allowance. Do not bend directly at the fuse body. Secure the carrier with the assembly guide's four M2×20 bolts and nuts. Keep sharp ends away from the empty future battery pocket.

### Wire eight groups into fifteen independent motor inputs

11. Route each red/black 20AWG pair together from its fuse/fanout to the assigned group, keeping its one-way copper length at or below 150mm, including the positive branch's 20mm pigtail before the fuse. Use gentle twists or adjacent ties; leave moving joints free. At the group, make a separate positive Y and ground Y. Each motor gets its own factory cable tail at or below 100mm. No motor's small power connector carries another motor's current.
12. The groups are **F1: IDs1/2; F2: IDs3/4; F3: IDs5/10; F4: IDs6/7; F5: IDs8/9; F6: IDs11/12; F7: IDs13/14; F8: ID15 jaw**. The jaw branch has only one motor.
13. Reuse the fifteen included 180mm ROBOTIS X3P cables. Label their ends before cutting each near the middle into approximately 90mm tails. The downstream input plug keeps all three contacts: **pin1 GND, pin2 VDD, pin3 DATA**. Connect its pin1 to the black group Y and pin2 to the fused red Y.
14. On the upstream output plug, release and remove **pin1 and pin2 contacts**, leaving only DATA pin3. Insulate and retain removed parts as spares. Rejoin the two DATA tails by a short soldered and insulated splice. This makes a DATA-only link between successive servos while their power comes from the separate group Ys. Verify numbered pins against the manufacturer connector drawing before cutting; wire colors are not the definition. [ROBOTIS connector information](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/#connector-information)
15. On the first cable's OpenRB end, remove **pin2 VDD**, keep pin3 DATA, and take pin1 GND separately to the common black star. Do not connect any external motor-positive wire to OpenRB. Leave its terminal VIN and XT60 pads unused. The other three OpenRB motor ports remain empty. Fit the source jumper on the **5V side used for USB/VIN**, following the manufacturer's USB jumper image. The PC/Pi USB cable powers OpenRB logic. [OpenRB power source jumper](https://emanual.robotis.com/docs/en/parts/controller/openrb-150/#power-source-jumper), [official USB jumper image](https://emanual.robotis.com/assets/images/parts/controller/openrb-150/openrb-150_power_jumper_5v.png)
16. OpenRB's motor distribution is rated 3A total and its USB path has a 0.5A fuse; the harness bypasses that distribution. Its DXL LED, FET control or reset therefore does **not** remove the external motor power. [OpenRB manual](https://emanual.robotis.com/docs/en/parts/controller/openrb-150/)

The power topology uses the retained ROBOTIS factory crimps. Do not force 20AWG wires into the small JST EH contacts, and do not substitute 2.54mm Dupont connectors for 2.5mm JST EH. The selected branch construction needs soldering; it is not a plug-only build.

### Insulation, strain relief and disconnect

17. Before final fuse-input joints are closed, verify that each group positive reaches only its assigned motor input pins2, all ground inputs reach the black star, and the DATA-only plugs have empty power positions. After closing fuse inputs, check source positive-to-all expected pins2 and source ground-to-all pins1; positive must not be shorted to ground on the disconnected harness.
18. Tie the motor tether to the empty battery-cradle passages and the logic lead near the Pi, with slack through the full head/leg range. Bind them loosely into one tether bundle; keep the bundle clear of feet. Source hardware stays on a stable insulated raised fixture beside the midpoint of the 0.3m lane, near head height and within 100mm laterally. Check reach, head lowering and slack at both lane ends before power. Do not suspend source hardware from the duck.
19. The accessible master disconnect is the bank's USB-C plug at the PD receiver. Normal sequence: stop, support the body, request Torque OFF, shut down the Pi and wait for shutdown, then unplug by the connector body. Unexpected motion: unplug immediately, catching the body with the support; this also cuts Pi power. That emergency action can interrupt storage writes. The bank's button is not assumed to be a reliable power-off switch.
20. Before connecting power, use continuity checks to establish that no motor VDD pin reaches OpenRB VDD or USB VBUS. Keep all fifteen motor input plugs disconnected for initial Pi/sensor calibration. For later recalibration, turn the source off before disconnecting these plugs and repower the logic alone. Never unplug DYNAMIXEL connectors live.

### Connect Pi power

Run a separate red/black **20AWG** pair, at most **500mm one way**, from common VOUT through F9 to the compact Adafruit1826 Micro-B plug. Connect **pin1 +5V, pin5 GND**; leave pins2/3/4 unconnected. This goes to **PWR IN**. There is no second USB-C power cable or second source. Keep the existing prepared USB data cable between the other Pi port and OpenRB, with its ID-to-GND connection as specified in the assembly section.

Measure at the actual Pi 5V/GND input, not just at the converter. The project gate is **4.75–5.25V** under boot, Wi-Fi, IMU and OpenRB load while the motor branch is simultaneously loaded. Pi Zero models lack the ordinary low-voltage detector; software status alone cannot validate this. [Raspberry Pi power documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html).

### Physical power and task acceptance

1. Unpowered: confirm no positive-to-ground short, correct pins, all intended continuity, empty OpenRB motor-positive position, insulation and strain relief. Initially keep Pi and motors disconnected.
2. Receiver only: observe negotiated 12V from the existing bank. Converter next: observe correct 5V polarity/output before any robot connection. If negotiation falls back, stop and diagnose it; never connect 12V directly to Pi or XL330.
3. Use a club electronic load/instruments to step combined output through 1A, 3A and 5A. At the upper screen distribute **4A across motor branches plus 1A through the actual Pi lead**, rather than testing each alone. Keep each motor group within its 2.25A calculated screen and each test endpoint within 1.3A. Record input current, output current and endpoint voltages. Hold the final load 30 minutes; converter case temperature must remain at or below the project's conservative 60°C criterion and stabilize over the last five minutes. This criterion is not a vendor ambient-temperature rating.
4. Enable one real servo at a time, then commission with the body supported. Retain all voltage/temperature/overload protections. Measure actual Pi voltage and the worst motor endpoint during torque enable, walking, stopping and jaw operation, including short voltage excursions with suitable instruments. Required motor task range **4.0–5.5V**; absolute XL330 operating range **3.7–6.0V**. Any reset, overheated joint, source shutdown, out-of-range excursion or failed regulator thermal check fails this stage.
5. After fit, joint calibration and supported tests pass, complete five consecutive operator-controlled trials: walk 0.3m, stop at a prepositioned soft foam piece (at most 2g, 8mm thick and 20mm wide), close jaw, lift at least 10mm, hold three seconds and release. Neither a powered-on board nor an unloaded jaw substitutes for this test. Hardware test count is currently **zero**.

If the real task exceeds the electrical envelope, first identify whether the failure is resistance, drag, controller behavior or actual source capacity. A capacity failure changes the source decision and requires a new review; it must not silently add a second power source or change the task to a single-motor demonstration.

## Phase 1 control: walk up, stop, pick up, hold and release

This foreground program connects a Mac keyboard to a borrowed Raspberry Pi Zero 2 W, trunk-mounted BNO085, OpenRB and **15 XL330-M288-T servos including jaw ID15**. One process owns the motor bus. It sends body commands from the frozen 61-input policy and jaw commands from measured calibration. It also provides a slow, calibrated pickup sequence. There is no autonomous object detection or trained real-world grasp policy in this release.

Problems advanced: P5 affordable serviceable hardware, P6 measurable first-power and fault-response acceptance. Final Phase 1 acceptance is supervised walking to a prepositioned light foam object, stopping, lowering the head, closing the jaw, lifting, holding and releasing. Supported pickup is the commissioning step before that final trial.

### What was missing and what this adds

The community controller's angle mapping contains only IDs 1–14. The old supervisor reads current and requests torque-off for ID15 but cannot move its jaw. This adapter adds ID15 only to its private controller instance, preserving body offsets and the 14-output walking model. It supplies measured open/closed jaw angles, current-based position mode for the jaw, and ready/lower/carry pickup poses. Lowering the head uses those measured poses after walking stops; it does not copy simulator-only privileged object positions into hardware software.

The camera, audio system and onboard battery are unnecessary for the directly observed first trial. Pi and BNO085 remain required for the real walking model. The Pi runs inference locally; the Mac sends keyboard commands over SSH. No public server, gamepad or automatic restarting service is installed.

### 1. Build and transfer the frozen bundle

On the Mac, this command creates a new output directory and leaves all community checkouts untouched:

```sh
cd /Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/phase1/runtime
python3 prepare.py --community /Users/xiangzheng/code/robotics/microduck-sim/Microduck-build-tutorial/microduck --overlay /Users/xiangzheng/code/robotics/microduck-sim/hardware-design-20260912/whole-robot-20260912/runtime-overlay --destination /tmp/microduck-phase1
```

The prepared `bundle/` included with this delivery is equivalent and includes both ONNX models, source hashes and upstream licenses. Install Raspberry Pi OS Lite **64-bit** using Raspberry Pi Imager. Set its hostname to **microduck**, enable SSH, and configure the same 2.4GHz Wi-Fi used by the Mac. Use a club router or private hotspot that permits devices to contact each other; client-isolated campus/guest Wi-Fi can prevent SSH. Choose the Pi username in Imager; use that username in `PI_HOST` below. If `microduck.local` does not resolve, replace it with the Pi's actual IP address from the router or Pi console. A 32-bit OS will not accept these pinned ARM64 inference wheels.

On the Mac, after the Pi boots and the chosen SSH account works:

```sh
export PI_HOST='<Pi username>@microduck.local'
ssh "$PI_HOST"
```

On the Pi:

```sh
sudo apt update
sudo apt install -y python3-venv python3-pip i2c-tools
sudo raspi-config nonint do_i2c 0
sudo usermod -aG dialout,i2c "$USER"
sudo python3 - <<'PY'
from pathlib import Path
p = Path('/boot/firmware/config.txt')
if not p.exists():
    p = Path('/boot/config.txt')
old = p.read_text()
backup = p.with_name('config.txt.before-microduck')
if not backup.exists():
    backup.write_text(old)
block = '\n[all]\n# MicroDuck BNO085: Adafruit Raspberry Pi I2C recommendation\ndtparam=i2c_arm_baudrate=400000\n'
if block not in old:
    p.write_text(old + block)
print('Configured I2C clock in', p)
PY
sudo reboot
```

Back on the Mac, transfer the prepared bundle:

```sh
scp -r /tmp/microduck-phase1 "$PI_HOST":~/microduck-phase1
ssh "$PI_HOST"
```

On the Pi:

```sh
cd ~/microduck-phase1
python3 -m venv .venv
.venv/bin/python -m pip install --only-binary=:all: -r requirements.txt
.venv/bin/python phase1.py check
cp calibration.template.json calibration.json
```

Expected output: `offline_dependency_model_check_passed`, with `stand` and `walk`. This command loads the real models and verifies driver methods without opening hardware. Python 3.11–3.13 ARM64 wheel availability was checked at package sources; actual Pi inference speed and memory remain commissioning measurements. This minimal environment does not install the unused Placo, desktop simulator or BMI088 library. The actual community BNO08x I²C driver is included.

For keyless foreground control, use an existing SSH key and `ssh-copy-id "$PI_HOST"` if the Pi does not yet trust it. `mac_control.py` uses SSH batch mode, so it fails clearly if that login has not been established. No key or password is embedded in this package.

### 1A. Measure the torso IMU axes with motor power disconnected

The rear torso clamp fixes the sensor's position but its rectangular envelope does not establish the BNO085 chip's axes. The old community mounting constant cannot be assumed correct. This procedure measures the installed board, computes the required rotation, and checks it against independent movements. It requires no guessed quaternion and no manually approved IMU flag.

Keep motor input plugs disconnected for this first calibration. For recalibration, switch the source off, disconnect all fifteen motor input plugs, then repower only Pi and its sensor. Never unplug motor connectors live. The sensor tool opens the I²C device, never OpenRB, serial transport or a motor-control object. Quit every other controller and IMU reader first.

Connect the selected Adafruit BNO085's STEMMA QT cable: **red VIN → Pi physical pin1 (3.3V); black GND → pin6; blue SDA → pin3 (GPIO2); yellow SCL → pin5 (GPIO3)**. Leave P0/P1 and DI unconnected: the default interface is I²C and default address is **0x4A**. Pulling DI high selects0x4B; do not change it for this build. The tool checks `/dev/i2c-1`, prints the responding address and requires fresh orientation plus angular-speed reports. The setup above enables I²C and sets400kHz, as recommended by Adafruit for the Pi. [Official BNO085 pinout](https://learn.adafruit.com/adafruit-9-dof-orientation-imu-fusion-breakout-bno085/pinouts), [official Pi wiring and clock setting](https://learn.adafruit.com/adafruit-9-dof-orientation-imu-fusion-breakout-bno085/python-circuitpython).

On the Pi:

```sh
cd ~/microduck-phase1
.venv/bin/python imu_calibrate.py calibrate --motor-power-disconnected
```

Use the **rigid torso**, not the feet or movable head, as the reference. At upright, keep the rear IMU clamp cover vertical and its top edge horizontal. The duck's left always means its own left when looking in the beak's direction. Support the body by hand or in a loose cradle, with motors disconnected. At each prompt, set the requested pose, let it settle, press Enter and hold still for1.5seconds:

1. **Upright:** rear cover vertical, top edge level, head raised.
2. **Forward:** tilt the entire torso about15–25° so the beak end goes down and tail end rises. Keep its left/right edges level.
3. **Left:** return upright, then lower the duck's left side15–25° and raise its right side. Do not turn it to face a different direction.
4. **Right:** return upright, then lower its right side15–25° and raise its left side.
5. **Back:** return upright, then raise the beak end15–25° and lower the tail end.
6. **Upright again:** return to the original level torso reference.
7. **Head only:** hold that torso reference fixed; gently lower only the head about20° and hold it there. The IMU reading must stay upright, because the sensor is attached to the torso. Do not force a joint.

The program fits upright/forward and checks the independent left/right/back poses. Each lean must be10–35° in the named direction with no more than5° across the other axis; upright return and head-only change must remain within3°. Each hold needs at least25 fresh reports, less than2° spread and angular speed below0.10rad/s. Stale, moving, repeated, reversed or inconsistent captures fail without overwriting the old calibration. Failure tells you which pose to repeat: fix the reference or clamp and rerun the complete command.

Successful output is **`measured_torso_axes_passed`**. It saves the computed rotation and all raw pose samples under `imu_mount` in `calibration.json`. It resets the physical gait gates because a mounting change requires renewed walking checks. Restore the head to ready, then independently check the saved mapping:

```sh
.venv/bin/python imu_calibrate.py check --motor-power-disconnected --seconds 60
```

Read the printed degrees while repeating those motions: upright near0; **beak-end down → positive `forward_deg`; beak-end up → negative**; **left-side down → positive `left_deg`; right-side down → negative**. Holding the torso still and lowering only the head should keep both readings near0. This check loads the saved rotation without fitting a new one. Repeat it after remounting, changing wiring, or before first motor enable after setup. If a sign is wrong, return to the calibration procedure; do not compensate with an invented software sign flip.

The measured rotation is applied consistently to the real Observer's body orientation, the61-input policy's gravity and angular-speed fields, and the runtime tilt stop. Missing or modified evidence blocks motor enable. The runtime requires the same I²C bus/address as calibration. The sensor adapter also tracks quaternion and gyro receipt separately: fresh acceleration packets cannot conceal an old orientation. The100ms limit is host receipt age, not measured sensor sampling latency, and leaves prediction disabled.

### 2. Configure servos while the body is supported

Follow the main assembly guide to establish the wiring and test the **factory OpenRB USB bridge first**. Flash the documented bridge sketch only if that factory check fails or the board previously ran another sketch. Assign unique servo IDs with the concrete procedure below before joining the bus. Stop any existing controller and disable its auto-start before using this entry. On a fresh Lite image there is no such service; if using the community image, stop `microduck-gamepad.service` so it cannot compete for the motor bus or turn Wi-Fi off.

Connect **exactly one physical servo** to OpenRB for ID assignment. All factory servos can start with ID1, so do not join them together first: two devices sharing an ID can be indistinguishable electrically. With the isolated servo powered from the single-servo commissioning source, run on the Pi:

```sh
cd ~/microduck-phase1
.venv/bin/python assign_id.py --list-ports
.venv/bin/python assign_id.py --new-id 1 --one-servo-connected
```

The tool scans IDs0–252 at the factory57600baud, requires one responding model1200(XL330-M288-T), verifies torque-off, sets the requested ID, sets baud-rate register3(1,000,000bps), reopens at1Mbps and verifies ID/model/rate/torque-off. The port is selected automatically only when exactly one OpenRB USB port exists; otherwise pass the exact path from `--list-ports` in `--port`.

After success, label the servo **ID1**, switch motor power off, and disconnect it. Connect the next isolated servo, power it, and run the same command with `--new-id 2`. Repeat through **ID15 for the jaw**, replacing the connected physical servo each time. Never automate these commands as a shell loop. For an already configured servo at1Mbps, add `--initial-baud 1000000`; this is also the explicit retry after an ID change succeeded but a previous baud-rate handoff was interrupted.

Join the bus only after every servo has its unique physical label. Complete the main guide's unmounted single-servo and supported branch tests before using the full-body runtime. **The runtime's `e` command enables all15 together**; it is not the earlier staged branch test.

With the robot physically supported and a commissioned external regulated 5V motor supply, on the Pi:

```sh
cd ~/microduck-phase1
.venv/bin/python phase1.py configure --supported
```

This explicit command first requests and reads back torque-off for all 15. It writes body operating mode 3, jaw operating mode 5, servo voltage limits 3.7–6.0 V, voltage/overheating/electrical-shock/overload shutdown bits0x35 enabled, and disables automatic torque-on. Jaw `Current Limit` is150 mA and `Goal Current` is100 mA initially. Every changed setting is read back; every arm also checks these voltage limits and shutdown protections. Failure exits without enabling torque. These are conservative commissioning settings, not a claim about successful grip force. The jaw's mode 5 uses the real current control function; body mode 3 remains the gait's position control.

Configuration sets **Drive Mode0**: normal direction, velocity-based profile and automatic torque-on disabled. It restores body IDs1–14 `Profile Velocity=0` and `Profile Acceleration=0`, removing the Wizard's temporary raw5 speed setting. Here zero means no servo-generated profile limit; body motion follows the50Hz controller targets and the tested gait gains. Jaw ID15 uses `Profile Velocity=10` (about0.24rad/s) and `Profile Acceleration=0`. Every arm restores and reads back these RAM profile settings after power cycles, before torque enable; wrong Drive Mode or failed profile readback blocks arming. Slow calibrated pickup interpolation remains active.

Reference: [ROBOTIS XL330 control table](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/). The source driver is pinned to [rustypot1.4.2](https://pypi.org/project/rustypot/1.4.2/); its real controller method signatures and register conversions are exercised by the offline tests.

### 3. Record actual positions

Calibration commands turn all 15 servos off. Keep the duck in its support fixture and move joints gently by hand. Never force a powered joint. Each capture asks for Enter after positioning, then reads the actual encoder positions. The body and head angles use the community coordinate mapping; jaw angles use the hardware encoder coordinate. No fabricated jaw center or assumed print tolerance is supplied.

1. Arrange the planted legs and body in the intended stable ready pose, head raised, jaw open. Capture `ready`.
2. Retain that leg pose, lower the head to the intended object height with the jaw open, and capture `lower`.
3. Retain the legs, raise the head enough to lift the selected foam object, jaw open, and capture `carry`.
4. Capture the jaw's open position and gently closed position. The allowed span is at most 30°, matching the inspected jaw geometry. Close without crushing an object or hitting a hard mechanical stop.

On the Pi, run one command for each prepared pose:

```sh
.venv/bin/python phase1.py capture --supported --name ready
.venv/bin/python phase1.py capture --supported --name lower
.venv/bin/python phase1.py capture --supported --name carry
.venv/bin/python phase1.py capture --supported --name jaw-open
.venv/bin/python phase1.py capture --supported --name jaw-closed
```

Inspect `calibration.json`. Its joint ranges start from the matching official MicroDuck model's mechanical ceilings. Narrow them wherever the assembled cable routing or prints restrict motion. The leg pose must remain within 2° across pickup poses. Record the completed physical direction, clearance, endpoint-voltage and supported-pose checks, then accept that calibration:

```sh
.venv/bin/python phase1.py accept-calibration --evidence '<completed checks and measurement/log reference>'
```

Changing poses, jaw settings, joint limits, measured IMU mounting or the current screen invalidates the saved calibration fingerprint and requires renewed acceptance. This command does not run a physical test on the operator's behalf. Its purpose is to prevent untouched placeholder calibration from enabling motion. Editing or recapturing any pose requires renewed physical checking.

### 4. Supported pickup

Keep the master USB-C plug at the external PD receiver within easy reach. Pull it to remove all robot power in an emergency; normal shutdown first stops motion, turns torque off and shuts down Pi. From a Mac terminal, use the client's real local path:

```sh
cd /Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/phase1/runtime
python3 mac_control.py --host "$PI_HOST" --supported
```

Press `e` to enable torque at the current measured positions. Then use:

- `r`: move slowly to ready.
- `n`: lower the head; `u`: lift to carry pose.
- `o` / `c`: open / close the jaw.
- `p`: ready → lower with jaw open → close gently → lift; then hold.
- `l`: open the jaw at the carry pose → return ready.
- `q`, Escape or Ctrl-C: request torque-off and end the session.

Start with an empty jaw. Next use the foam object specified by the assembly guide and place a soft receiving tray below it. Complete five observed pickup/hold/release trials before setting `physical_supported_pickup_passed` to `true` in the calibration file, with the test record retained. A current or position command is not proof the object was grasped: visually confirm lift clearance and a three-second hold.

### 5. Walking and the final combined trial

The two walking gates are separate from pickup calibration. Set `physical_supported_gait_ready` only after motor directions/zeros, the trunk IMU axes, serial timing and motor-supply tests pass. With the robot supported, `v` prepares the gait at zero command, with a1.5-second posture ramp followed by2seconds of policy settling before forward commands are applied; brief `w` commands request forward motion toward a target placed straight ahead. Backward and turning remain behind a separate directional-gait physical test gate. Each velocity request expires after250 ms; `x` sets zero velocity. Forward command is0.30 m/s, matching the tested policy input; the simulated actual speed is substantially lower. Low0.10–0.20 m/s commands are not a reliable slow-walk setting in this frozen policy. Each key request lasts at most250 ms before zero command resumes; hold/repeat only under direct observation. Backward and turning have not been accepted in the initial straight-line task.

The runner reports faults for loops slower than100 ms. Record actual50 Hz loop performance on the Pi while monitoring power; meeting the hard deadline alone does not establish gait stability. Verify the walking-to-zero-command stop before walking toward an object. Only after supported walking/stop trials pass should `physical_supported_walk_passed` become `true`.

Then launch without `--supported` for the supervised freestanding trial. Keep the same support/catch provision available, without loading it during the recorded freestanding result. Walk toward the prepositioned foam target, press `x`, wait at least one second with the robot stable, then use `r`, `p`, wait three seconds, and `l`. The calibrated pickup keeps the legs planted. Return to ready before re-entering `v`/walking. Acceptance is five complete observed repetitions with no fall, protection trip, electrical over-limit or object drop before release.

The Phase1adapter uses body position P gain 275 and retains walk61 after forward movement begins, sending zero velocity to stop. It retains heading correction at zero translation, with gain 2 and a0.8rad/s cap. It does not switch back to stand61 or blend actions. The untouched underlying61D adapter and model files remain frozen; this explicit Phase1choice is implemented in policy.py. Its compatibility tests use real ONNX execution. The optional causal predictor uses only arrived gyro/gravity/joint data. Its latency fields default to `unknown`, so it is disabled until actual sample-age evidence exists. Host receipt age alone is insufficient; a validated device timestamp or latency estimate in the 0–40 ms tested window is required. The final simulation record identifies which delayed cases used this predictor. Mass changes, the walking-to-stop transition and the pickup pose balance still require the current geometry's simulation and physical tests in the main acceptance guide. Do not mark either physical test gate true based on offline tests alone.

### Stop behavior

The Mac sends numbered heartbeats10 times/s. EOF, malformed/replayed packets,600 ms without input, invalid/stale IMU,45° tilt, failed servo reads/writes, voltage outside4.0–5.5 V, excessive measured current, a100 ms loop deadline, device watchdog fault or the session limit ends the session and requests torque-off for **all 15 including the jaw**. Re-enable is latched off until a new session. Target angles are finite and bounded before writes.

Servo bus-watchdog register 10 is set and read back before torque enable, corresponding to 200 ms without bus traffic. That firmware behavior stops commanded motion; it does not prove power disconnection or remove all holding torque. Software torque-off is still a bus request, and the launcher's final readback can report failure. The operator's accessible master USB-C disconnect and support fixture remain the independent stop. Closing a laptop window is not the sole emergency stop.

The runtime's summed servo-current screen remains 5.0A, with 2.25A per group. Those sampled winding-current readings are distinct from total supply current and are not an electronic current limiter. The current source design separately allocates 4A measured motor supply plus 1A logic, at most 5A combined. All fifteen motors are required by this runner. Physical source-current and endpoint-voltage tests in the active power guide remain mandatory.

### Verification records

`offline-results.json` reports the actual software checks. The test builds a fresh bundle and uses real community classes, actual community controller conversions over a substituted Rust transport, real Observation/UserInput/MotorCommand, and both real ONNX models. Device I/O is substituted; physical robot tests remain zero. Calibration and session logs are intentionally separate from source integrity hashes.

The active power source is the existing bank through a 12V receiver and common 5V regulator. The 5A whole-source screen includes logic; measured motor allocation initially allows 4A plus 1A logic. Runtime summed motor-current values are a separate sampled winding-current proxy, not an electronic supply limiter or a measurement of total source current. See the current power recipe for physical release.

## Verification and remaining physical acceptance

The current print route contains 85 instances on six plates. Walking/stopping simulation passes 33/33 cases; frozen-runtime offline checks pass 50/50. These are software evidence, not actual walking or power measurements. The new power screen separately checks motor and Pi endpoints; the current catalog, carts and guide are generated and checked together. [Verification record](verification.json).

Complete the physical power, joint calibration, supported walking and pickup gates above, followed by five consecutive bring-up trials. If measurements contradict the selected source or harness, record the failing condition and revise that decision before purchasing replacements. Camera integration and the learned-policy transfer remain required work toward the project goal; the component tests do not defer or remove them.

[Print files](PRINT-LIST.md) · [Editable handbook](START-HERE.md) · [Power sources and calculations](power-research.md) · [Repair audit](audit-20260913/REPAIR-AUDIT.md)
