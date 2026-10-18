# Phase 1 assembly and test sequence

Revision: 2026-09-13. Advances P5, economical and serviceable hardware, and P6, controlled physical deployment.

Build the 15-motor chassis, including its moving jaw. Component bring-up uses a borrow-first Pi, the torso orientation sensor and the common regulated supply; the laptop provides supervised commands. The intermediate test is to walk toward a prepositioned lightweight object, stop, close the beak around it and lift it. Camera-based object finding and the trained jaw's real-observation interface remain required for the project goal in [PROJECT-CONTEXT.json](../../PROJECT-CONTEXT.json).

## Print and prepare

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

## Tools and fasteners

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

## 1. Check one motor before assembling the body

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

## 2. Build the jaw as an early independent module

Use the repaired jaw motor support and cap. Attach the moving jaw frame `community-4.stl` to ID15's output face. The opposite jaw boss fits into the support's integral sliding seat. A sliding seat is a smooth printed support around the opposite end of the rotating part; its axis must align with the motor shaft. It is not a rolling ball bearing.

The fixed upper lip is `community-40.stl`; the lower lip `community-42.stl` moves with the jaw. Their source names include “soft,” but the inherited print material is PLA. Do not assume those printed surfaces are rubbery. Keep the structural jaw frame rigid.

Dry-fit each lip fully onto its own matching frame. The selected Phase 1 retention method is a small amount of club-sourced **cyanoacrylate adhesive, also called CA or superglue**, at the exterior mating edges after alignment. Keep the bond out of the gripping surfaces, sliding seat and motor. Do not add a thick glue layer between the seating faces, and never glue the two opposing lips together. Cure for the actual adhesive's stated time with electronics removed from the work area. Gently pull each pad before powering; it must remain seated without shifting. This is an engineering assembly choice whose retention is accepted by the physical grip test. [Prusa's material guide supports CA for PLA](https://blog.prusa3d.com/the-great-guide-to-gluing-and-assembling-3d-prints_44908/).

![Jaw support and opening positions](../assembly/images/10-mouth-detail.png)

With power disconnected, move through a small opening, checking that the opposite support neither binds nor pulls sideways. Check that the lower pad follows only the lower jaw. The geometric scan checked 0–30 degrees in 0.5-degree steps; this is a candidate range to calibrate, not a preapproved hardware end-stop setting.

For this early module test, use Wizard with **only ID15 connected**. The full-body runtime expects all fifteen motors and is used after assembly. Support the jaw module on the bench. With Torque OFF and the output free to move gently, read Present Position at a small open position and at gentle closure; record these raw encoder values. Stay within the physical clearances and a maximum341-count span (about30 degrees); do not cross the0/4095 boundary. Set Operating Mode5, Current Limit150mA, Goal Current100mA and Profile Velocity raw5. Read back those values and retain the voltage/shutdown settings from the first-motor check. Changing mode can reset RAM settings, so set Goal Current and Profile Velocity after mode selection. Preload the actual current position as Goal Position before Torque ON. Then command only the measured open/closed values, watching for pinching, binding and current errors. Always Torque OFF before handling the mechanism. Re-capture the final jaw endpoints in the runtime calibration once all fifteen IDs are present.

Start with a measured, soft foam sample no heavier than 2 g. Use an 8 mm-thick gripping section approximately 20 mm wide. Support it at the middle of the beak so the test isolates gripping from walking and reaching. Jaw grip and attachment are physical measurements, not demonstrated by the CAD scan.

For this target, the separate [jaw-aperture check](jaw-aperture.json) samples a central 20 × 10 mm lip patch. At a modeled 20-degree opening, all nine sampled gaps exceed 14.79 mm, providing geometric room for the 8 mm gripping section. This checks the opening size; the first physical grip test still establishes whether the surfaces actually hold the foam.

**Pass:** five slow open/close cycles without binding, reset or lost ID; then five grips that retain the foam for three seconds after the object support is lowered by 10 mm. Record object mass, thickness, actual angle limits and motor current. If it slips, inspect alignment and contact first. Increasing force alone is not an accepted repair; a pad material/attachment change needs the same test again. This module test is an intermediate gate, not the final walking-and-pickup MVP.

## 3. Assemble torso, legs and neck

Assemble the torso base and integrated support around hip-yaw motors IDs5 and10. Leave the battery cradle and regulator shelves empty. Use the [leg exploded drawing](../assembly/images/09-leg-detail.png) and source-part catalog to keep mirrored parts on the correct side.

For the left leg, build from hip toward foot: ID10 → hip yaw/roll link → ID9 → hip bracket and ID8 → thigh → ID7 knee → lower-leg links → ID6 ankle → matched left community foot. Mirror that sequence for IDs5 through1 on the right. Add both thin thigh reinforcing plates.

![Leg parts and assembly order](../assembly/images/09-leg-detail.png)

Support both sides of each joint on the same rotation axis. Keep the community ankles, combined feet and printed sliding rings as a matched set. The fourteen printed idler/cap pairs are available stock; fit only the pairs required by the passive side at each station and record the leftovers as spares. The source motor mesh merges both flanges, so it does not establish a reliable installed count by itself.

Build the neck links and install ID12 neck pitch, ID11 head pitch, ID13 yaw and ID14 roll in the illustrated order. Fit the completed jaw/head module. Turn torque off while checking each joint's permitted small movement. Do not force a geared motor through resistance.

**Pass:** no scraping, cracked print, loose opposite support or wire obstruction; every actual joint location agrees with the motor-ID drawing. Record the fitted screw length for each repeated joint type in the [first-article record](../assembly/FIRST-ARTICLE.md).

## 4. Install control electronics and the fused harness

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

## 5. Establish standing and walking before attempting pickup

Fit the robot's fall-catching support so it can move without carrying the robot's normal weight. Begin on a flat surface with the tether slack. Use the runtime's calibrated standing procedure before commanding travel. Confirm the torso sensor changes correctly when the robot is tilted by hand, and verify the stop action before increasing movement.

Measure and record completed robot mass. The printed support remains, but removing a battery and head electronics changes balance. The updated controller candidate passed [33 Phase 1 mass and gait/stop cases](simulation/README.md), including 4.0 V and 5.25 V supply assumptions, with prediction disabled. It retains the walking policy during zero-translation stopping and continues heading correction. The old controller passed only 20 of 27 phase-mass cases, so use the matched Phase 1 runtime rather than silently retaining the old transition. Actual mass, printed foot friction, sensor delay and tether pull still need the physical checks below.

**Standing pass:** maintain supported-but-not-weight-carried standing for 30 seconds with no reset, drifting joint, binding or protection event. **Walking pass:** walk 0.3 m, stop and remain standing for three seconds; complete five trials with no fall and no tether pull. Retain videos and current/voltage logs. A failure returns to its last passed module test rather than proceeding to pickup.

## 6. Complete the Phase 1 pickup task

Use the same weighed foam target. Put it on a known support in the robot's reachable beak path, with the target centered and its gripping section exposed. The human places the target and commands approach from the laptop. The robot must walk, stop, lower the head to the calibrated pose, close the beak and lift the object at least 10 mm for three seconds. Complete five consecutive trials.

The target support's height is calibrated from the assembled robot's actual reach; begin at an easy beak height, then lower it only after the prior height passes. Picking directly from the floor is a stronger reach/balance test. The old browser GroundPick behavior and isolated jaw training do not establish that the community physical frame can perform the same floor motion. Record the lowest passed target height explicitly.

**Component bring-up pass:** approach by walking plus grasp/lift succeeds five consecutive times, no person supports the object or robot during the attempt, no cable assists balance, and no power/thermal protection event occurs. Keep the initial object specification and placement fixed. This test covers supervised execution; passing it does not complete camera-guided learned pickup.

## Accessory integration

The retained cap, face panel and torso support keep the attachment points for the camera cradle/tilt foot, audio carrier, selected battery and both regulator positions. Print the four deferred accessories only when their hardware is selected. An onboard supply replaces the upstream tether connection; the fused motor branches stay.

Reweigh the robot, rerun standing/walking/pickup checks and recheck the head's complete motion after each module is added. A different Pi, battery size or camera needs its own connector and mounting check. Source CAD and current digital evidence remain in the [full assembly manual](../assembly/ASSEMBLY.md); its battery-specific assembly steps are deferred for Phase 1.

## Mechanical evidence and remaining measurements

The repaired jaw support is a single watertight mesh. Its added material clears 41 head objects; 61 sampled jaw poses from 0 to 30 degrees are collision-free in the checked digital assembly. The nominal opposite support has 0.2 mm radial and 0.3 mm flange clearance. These values become actual fit only after printing. [Support design](../assembly/mouth-support/design.json), [static check](../assembly/mouth-support/static-check.json), [motion check](../assembly/mouth-motion-coaxial-conditional.json).

The Phase 1 subset reuses these exact files and preserves their mounting interfaces. No arm is present: the head/neck positions the beak, and ID15 closes it. Lip friction, lip attachment, printed sliding fit, exact original per-hole screw stack, available M2.6 TAP screws and real floor reach remain arrival-dependent checks. Each has a specific test above; no physical print, assembly, walking or grasp result has been claimed.
