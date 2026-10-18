# MicroDuck Phase 1 — Build, commission, walk and pick up

Revision: 13 September 2026 · English build handbook · Problems P5/P6

**Build the complete 15-servo duck, including its moving jaw.** Use an external 5V motor supply, the existing power bank for control electronics, a borrowed Raspberry Pi Zero 2 W, and Mac keyboard control. Keep the camera, sound system and onboard battery for Phase 2.

The Phase 1 task is specific: on a level test surface, the operator walks the duck toward a prepositioned soft foam object, stops, lowers its head, closes its beak, lifts the object, holds it for three seconds and releases it. Five consecutive unassisted robot/object trials complete acceptance. The operator still controls the sequence. Camera-based object finding, arbitrary objects, autonomous navigation and carrying while walking are later work.

This is the current build route. Earlier battery/regulator purchasing lists and assembly steps are Phase 2 references. The existing camera, battery and sound mounting interfaces remain in the retained structure.

![Whole Phase 1 system and acceptance path](figures/phase1-panorama.png)

## Work in this order

1. Check out the three **Order today** carts below, and resolve the **existing-resource list** before scheduling assembly.
2. Print the six plates using the club's actual printer and plate settings; inspect the jaw's sliding fit before duplicating assembly operations.
3. Prepare the Pi and frozen software bundle in the software section. The dependency/model check does not need connected motors.
4. Prepare the unpowered fused harness and complete the source/load checks in **Build and test the power harness**. Keep unused motor outputs insulated.
5. Connect and label one motor at a time. Complete the Wizard small-motion check for IDs1–15, then assemble and test the jaw module.
6. Assemble torso, legs and head. Install the Pi, BNO085 and harness, then commission each powered branch with the body supported. Perform the sensor-only torso calibration before full-body motor enable.
7. Capture actual body/jaw poses. Pass supported pickup, standing and walking/stopping before the five complete walk-up-and-pickup trials.

Each numbered assembly stage below has its own pass criterion. The software section contains the exact commands; the power section contains the detailed wire recipe. Fill the [physical acceptance record](ACCEPTANCE-RECORD.md) as the work is performed.

## Order today

Three current carts contain the ten purchasing lines below. Merchandise is **$514.92**. This is not a delivered total: DigiKey currently estimates another **$8.30 tariff and $4.99 shipping**, while ROBOTIS/Adafruit shipping and all final sales taxes still depend on checkout. No payment or order has been made.

### ROBOTIS — $437.65

[Open the prepared cart](https://robotis.us/cart)

- **14 × Smart servo:** ROBOTIS DYNAMIXEL XL330-M288-T / 902-0163-000. $384.86. [Exact product](https://robotis.us/products/dynamixel-xl330-m288-t)
- **1 × Servo bus controller:** ROBOTIS OpenRB-150 Starter Kit / 902-0184-000. $52.79. [Exact product](https://robotis.us/products/openrb-150-starter-kit)

### Adafruit — $35.30

[Open the prepared cart](https://www.adafruit.com/shopping_cart)

- **1 × Body inertial measurement unit:** Adafruit BNO085 / 4754. $29.50. [Exact product](https://www.adafruit.com/product/4754)
- **1 × IMU four-wire adapter:** Adafruit 4397 STEMMA QT/Qwiic JST-SH4 to female sockets, 150mm. $0.95. [Exact product](https://www.adafruit.com/product/4397)
- **2 × Pi Micro-B connectors:** Adafruit 1826 USB DIY Slim MicroB plug. $1.90. [Exact product](https://www.adafruit.com/product/1826)
- **1 × OpenRB USB data cable:** Adafruit 4472 USB-A to USB-C data/sync cable, 6 inch. $2.95. [Exact product](https://www.adafruit.com/product/4472)

### DigiKey — $41.97

[Open the prepared cart](https://www.digikey.com/ordering/shoppingcart)

- **2 × Main fuse:** Littelfuse 0251010.MXL, 10A axial / DigiKey F2320-ND. $2.48. [Exact product](https://www.digikey.com/en/products/detail/littelfuse-inc/0251010-MXL/700757)
- **10 × Branch fuses:** Littelfuse 0251003.MXL, 3A axial / DigiKey F2315-ND. $9.45. [Exact product](https://www.digikey.com/en/products/detail/littelfuse-inc/0251003-MXL/700737)
- **1 × External motor power supply:** Mean Well GST60A05-P1J / DigiKey1866-2146-ND. $19.40. [Exact product](https://www.digikey.com/en/products/detail/mean-well-usa-inc/GST60A05-P1J/7703709)
- **1 × Prewired DC power socket:** Tensility10-06257 / DigiKey839-10-06257-ND. $10.64. [Exact product](https://www.digikey.com/en/products/detail/tensility-international-corp/10-06257/27685456)

The Starter Kit includes one XL330: fourteen standalone motors plus that one gives **15**, not 14. The 10A fuse order provides one installed and one spare; the ten 3A fuses provide eight installed and two spare. The two Micro-B plugs make the compact Pi power and data connections.

These three carts were read back after removing deferred parts. Ten other project carts are empty; Pololu retains one unrelated preexisting $8.49 item, excluded from this build and not a Phase 1 order. No additional items are needed to reach free shipping. The previous camera/audio/onboard-power carts should not be checked out.

**Arrival:** all four DigiKey lines show immediate availability, but DigiKey warns that processing may take an extra business day. Neither stock nor a ground-shipping menu provides a destination delivery date. Record the actual delivery dates when checking out; none is asserted here.

## Obtain from existing resources before assembly

These are required resources with purchasing holds, not claims that stock has already been found:

- Borrow a **Raspberry Pi Zero 2 W with its 40-pin header fitted**, a microSD card (16GB or larger), card reader and access to Raspberry Pi Imager. Another Pi model needs a mounting, connector and timing check before replacing this baseline.
- Use the existing **Xiaomi 5V / 3A USB-C power bank** for Pi, IMU and OpenRB logic. Borrow a suitable USB-C-to-Micro-B cable to prepare the compact power lead. Leave the power bank and its attached cable unmodified. If its automatic shutoff interrupts the 30-minute logic test, use a borrowed Pi supply and repeat.
- Borrow an intact **grounded US wall-to-IEC-C13 power cord** for the Mean Well adapter. This is the common three-contact computer-style wall cord. It is not included with this adapter; no exposed mains wiring is required.
- Use RoboClub's printer, PLA, wire, heat-shrink, solder, ties, glue and fasteners. The exact **M2.6 × 6 TAP screws for passive idler stations** must be checked in club stock; they do not come in the standalone motor packages. The assembly section identifies the other lengths. Do not substitute an ordinary machine screw because its diameter looks similar.
- Use club screwdrivers, caliper, soldering tools, multimeter and suitable power-load/current/voltage measurement equipment. A multimeter checks voltage and connections; a scope/current instrument catches short events a slow display can miss. Arrange a fall-catching support and a scale for the foam sample.

The Pi and exact idler screws are the two stock checks to settle before scheduling full assembly. Their purchasing holds remain in force. A complete shopping cart cannot itself supply borrowed items.

## Learn the connections before touching a wire

You already know plugging a USB cable into a computer. A **connector** is that physical joining part: a **plug** enters a **socket**, and small metal **contacts** touch inside it. A bare wire has conductive metal inside insulating plastic.

A **terminal** is a place where a wire joins a device. A **terminal block** holds several such places in an insulating body. A **screw terminal** uses a screw to tighten a metal clamp around the prepared wire end. Loosen, insert exposed metal into the wire hole, tighten, then gently tug. The screw belongs to the connector on the board; it never screws into a USB-C plug.

A **USB power breakout** presents power from a USB socket at wire terminals. In the example below, the USB-C cable plugs normally into the small board; two separate wires leave its other side for OpenRB. This explains the earlier power-bank suggestion. The complete Phase 1 motor route uses the Mean Well supply and prewired socket instead, so the example breakout is **not** another item to order.

![USB-C socket, wire terminals and the screw clamp](figures/usb-c-to-terminals.png)

The adapter's round **DC barrel plug** enters the matching **barrel jack/socket**. The specified supply is **center positive**: the center contact is +5V, and the outer contact is the return. **Polarity** means which connection is positive and which is return; reversing them is not a valid alternative. A meter verifies the actual connection.

A **fuse** is a sacrificial link that opens after excessive current for a sufficient time. It protects the wiring against faults; it does not make the voltage correct or clamp current to its printed number. A **wire harness** is the prepared collection of wires and connectors. In this design, a shared positive/return point splits into eight fused branches, then each motor receives its own power tail. The command wire remains shared.

**Soldering** joins metal with molten solder. **Heat-shrink tubing** is insulating plastic slipped over that joint and shrunk with heat. **Strain relief** means securing the cable to the frame so a pull reaches the frame, rather than the electrical joint. **AWG**, American Wire Gauge, specifies wire size: the lower number here means thicker copper, so 16AWG is thicker than 20AWG.

**IMU**, inertial measurement unit, is the BNO085 body-orientation sensor. It helps the controller know whether the torso is leaning. Its **I2C** sensor connection uses two signal wires plus power and return. Pi performs the balance calculation; OpenRB provides the compatible motor communication connection. The **power-source jumper** is a removable cap placed over the specified pair of pins to select a board's power path.

The learning graph now contains the terminal/connector prerequisites and records the reported gaps as unknown, not understood. [Open screw-terminal learning path](http://127.0.0.1:5063/?target=screw-terminal&dimension=intuition).

## OpenRB firmware and first communication

New OpenRB boards ship with the **usb_to_dynamixel** bridge already installed. Start by testing that bridge, instead of reflashing a working new board. It supports motor communication up to 1Mbps. [ROBOTIS firmware reference](https://emanual.robotis.com/docs/en/parts/controller/openrb-150/#dynamixel-wizard-20)

If the board has other firmware, recover the bridge in Arduino IDE: add the official board-manager URL below in Preferences; install **Arduino SAMD Boards** and **OpenRB** in Boards Manager; select OpenRB-150 and its detected USB port; open the board package's **usb_to_dynamixel** example and Upload. Disconnect motor power while uploading. Reconnect only after the bridge enumerates successfully. The connector is USB-C; the firmware supplies the USB-to-motor communication behavior.

```text
https://raw.githubusercontent.com/ROBOTIS-GIT/OpenRB-150/master/package_openrb_index.json
```

[Official board installation steps](https://emanual.robotis.com/docs/en/parts/controller/openrb-150/#install-board-manager). First prepare and verify the external power harness as described below; then assign IDs with exactly one motor connected at a time using the software section. Read that software setup before mounting the motors, since configuration precedes closing each joint.

## Phase 1 assembly and test sequence

Revision: 2026-09-13. Advances P5, economical and serviceable hardware, and P6, controlled physical deployment.

Build the complete 15-motor robot, including its moving jaw. Phase 1 uses a borrowed Pi, the torso orientation sensor and an external regulated supply; the laptop provides supervised commands. The final task is to walk toward a prepositioned lightweight object, stop, close the beak around it and lift it. Camera-based object finding, sound and untethered battery operation belong to Phase 2.

### Print and prepare

Use the [85-instance Bambu project](printing/MicroDuck-Phase1-85-instances-X1C-CoolPlate.3mf) and [exact Phase 1 print list](PRINT-LIST.md). This is 78 source/stock instances plus seven current parts. The count includes spare allowance: fourteen printed passive idlers and fourteen caps in total. It does not assert that every copy is installed.

Bambu Studio sliced all 85 instances across six plates. It predicts 372.97 g of PLA and 16 h 44 min 13 s of printing. These are slicer estimates. The saved settings are X1 Carbon, 0.4 mm nozzle, Cool Plate, PLA, 0.2 mm layers, four walls, 30% gyroid and automatic tree supports. Select the actual RoboClub printer, nozzle and plate before printing; another machine or plate needs a fresh slice. Printing materials remain RoboClub-first.

Keep these seven current parts, one of each:

- **Integrated torso/power support:** joins the original torso and motor interfaces and retains the future battery cradle and regulator shelves. The empty shelves can remain; do not cut them away or replace this structural piece with an older source print.
- **Small-regulator pocket cover:** close the empty pocket with four M2 × 12 machine screws. Remove the cover when Phase 2 needs the regulator.
- **Jaw-clearance head cap:** includes the OpenRB posts and clearance for the repaired jaw. It retains the future camera attachment.
- **Coaxial jaw motor support:** supports motor ID15 and its opposite sliding seat on the same rotation axis. It replaces source `community-24.stl`; no separate mouth bearing is required.
- **Torso IMU clamp and rear cover:** two parts that hold the BNO085 orientation sensor on the torso. The clamp grips the printed rails; it does not need a battery to be present.
- **Fuse carrier:** keeps the eight motor branch fuses and main fuse secured. Leave unused slots empty. The same branch harness can later receive power from an onboard regulator.

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

The [fuse-loading drawing](../assembly/images/11-fuse-loading.png) and [tie-path drawing](../assembly/images/12-fuse-ties.png) show how the carrier retains insulated fuse bodies. Four ties with a maximum section of 2.5 × 1.1 mm fit the checked carrier slots. Use narrow flexible loops at moving joints. Leave the last 200 mm of the Mean Well factory cord slack before its barrel-plug junction. The Tensility jack's two leads are trimmed to 100 mm from the jack exit and continue into the harness; do not add a separate 200 mm loop to those short leads. Attach strain relief at the empty battery-cradle tie passages, so movement does not pull directly on electrical contacts. **Strain relief means a clamp or tie that transfers a cable pull to the frame.** A cable hanging from its solder joints is not strain relief. Leave the barrel junction reachable and disconnect it by gripping the plug/jack bodies.

Phase 1 still requires soldering for the fused power branches, insulated wire joints, modified DATA connections and the following two compact Pi plugs. The factory-prewired supply jack avoids soldering its connector contacts. Use the club soldering station and inspect the completed harness before it goes into the robot.

![Fuse carrier loading; leave Phase 2 accessory positions empty](../assembly/images/11-fuse-loading.png)

![Fuse carrier tie passages and retention](../assembly/images/12-fuse-ties.png)

Use **two Adafruit 1826 bare MicroB plugs**, without their 26 mm plastic housings. Prepare them before putting the Pi into the head. Each completed plug, insulated solder joints and strain relief must fit the previously checked **14.5 × 9.5 × 7 mm** envelope. An arbitrary molded plug does not satisfy that check.

- **Pi data connection:** use the selected Adafruit 4472 USB-A-to-USB-C data cable. Replace only its USB-A end with one bare MicroB plug; keep the USB-C end intact for OpenRB. On the MicroB plug connect pin1 VBUS, pin2 D−, pin3 D+ and pin5 GND to their matching cable conductors. Preserve the twisted data-wire pair. Connect MicroB pin4 ID to pin5 GND; this selects the Pi's USB-host role. This cable goes into the Pi's port marked USB. It supplies OpenRB logic and carries data. It does not supply motor power. No separate OTG adapter is needed for this prepared cable.
- **Pi power connection:** source a USB-C-to-MicroB power cable from club stock, at most 500 mm long after preparation. Use 20 AWG copper power conductors, or verify that the completed wire pair has loop resistance at most 0.050 ohm, excluding connector contacts. AWG is the wire-size designation; lower numbers are thicker wires. Retain the original USB-C plug, including its USB-C power-detection circuitry, and replace only its MicroB end with the second bare plug. Connect pin1 to +5 V and pin5 to GND; leave pins2,3 and4 unconnected and insulated. Plug this into Pi PWR IN and the Xiaomi power bank's USB-C socket. Leave the power bank's integrated cable unmodified. The power bank stays on a stable raised support beside the midpoint of the 0.3 m test lane, with its USB socket near Pi head height and within 100 mm laterally of the lane. This leaves routing/slack at both ends of the lane without carrying the bank or adding its mass to the duck. Keep the cable clear of feet, check the head's full lowering motion, and retain the measured 4.75–5.25 V Pi input gate. The [power calculation](power-research.md) includes the longer logic-wire allowance.

Before plugging either cable into a board, use the connector drawing to identify all five MicroB contacts; viewing a plug from the opposite side reverses their apparent order. With all power disconnected, verify each intended end-to-end connection, verify no unintended shorts between adjacent pins, verify the data cable's ID-to-GND connection, and verify that the power cable's three unused pins remain isolated. Then measure source polarity and voltage at the completed power plug, check the insulated dimensions with calipers and perform a gentle pull test. See the [validated compact-cable wiring reference](../power/WIRING.md) and [USB envelope check](../assembly/usb-bare-plug-check.json).

The Pi supply test is 30 minutes with Wi-Fi, OpenRB and the IMU running, measuring 4.75–5.25 V at the Pi's actual 5 V/GND points with no resets or power-bank auto-off. A software status flag alone does not establish the voltage on Pi Zero. Confirm an already-soldered Pi header; otherwise fit the matching 2 × 20 header from club stock before attaching the sensor cable. BNO085 connections are Pi physical pin1/3.3 V to VIN, pin6 to GND, pin3/GPIO2 to SDA and pin5/GPIO3 to SCL. The selected STEMMA QT-to-female cable plugs into the sensor and these header pins.

With both supplies disconnected, plug the keyed four-contact end of Adafruit4397 into either BNO085 STEMMA QT socket. Connect the four individual female ends to the Pi header:

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

**Phase 1 pass:** approach by walking plus grasp/lift succeeds five consecutive times, no person supports the object or robot during the attempt, no cable assists balance, and no power/thermal protection event occurs. Keep the initial object specification and placement fixed. This is supervised task execution; automatic object detection begins in Phase 2.

### Phase 2 reintegration

The retained cap, face panel and torso support keep the attachment points for the camera cradle/tilt foot, audio carrier, selected battery and both regulator positions. Print the four deferred accessories only when their hardware is selected. An onboard supply replaces the upstream tether connection; the fused motor branches stay.

Reweigh the robot, rerun standing/walking/pickup checks and recheck the head's complete motion after each module is added. A different Pi, battery size or camera needs its own connector and mounting check. Source CAD and current digital evidence remain in the [full assembly manual](../assembly/ASSEMBLY.md); its battery-specific assembly steps are deferred for Phase 1.

### Mechanical evidence and remaining measurements

The repaired jaw support is a single watertight mesh. Its added material clears 41 head objects; 61 sampled jaw poses from 0 to 30 degrees are collision-free in the checked digital assembly. The nominal opposite support has 0.2 mm radial and 0.3 mm flange clearance. These values become actual fit only after printing. [Support design](../assembly/mouth-support/design.json), [static check](../assembly/mouth-support/static-check.json), [motion check](../assembly/mouth-motion-coaxial-conditional.json).

The Phase 1 subset reuses these exact files and preserves their mounting interfaces. No arm is present: the head/neck positions the beak, and ID15 closes it. Lip friction, lip attachment, printed sliding fit, exact original per-hole screw stack, available M2.6 TAP screws and real floor reach remain arrival-dependent checks. Each has a specific test above; no physical print, assembly, walking or grasp result has been claimed.

## Build and test the power harness

### Assemble the motor harness

A **wire harness** is the prepared set of wires and connectors. The **power star** is the shared positive/ground junction feeding separate branches. It is external to OpenRB's power circuit; the small insulated harness and fuse carrier remain inside the torso. The adapter stays outside.

### Prepare and label with all power disconnected

1. Put the adapter, power bank and USB cables aside, disconnected. Use the club soldering station, wire stripper, flux, heat-shrink, meter and helping hands. Practice a splice on spare wire first. Do not solder with a servo, Pi or source connected.
2. Mark nine installed fuses: **F0 = 10A; F1–F8 = 3A**. Leave the carrier's extra slots empty. Fuses have no direction, but their ratings matter. These are solder-in axial fuses, not screw-in fuse holders.
3. Cut red and black **16AWG copper** trunk pieces: one 30mm and two 70mm pieces of each color. Each source-to-fanout route therefore contains at most 100mm of 16AWG wire. Cut eight red and eight black **20AWG** branch wires, initially 150mm each. Shorten only after checking the actual moving-joint route; do not lengthen beyond the calculation without updating it.
4. With the jack disconnected, trim both Tensility 18AWG leads to **100mm measured from the cable exit at the jack body to the new cut end**. Leave its molded connector and internal joints untouched. Strip/tin the new distal ends. The original 305mm lead length is not the final harness length. Inspect the insulation. With the meter, verify jack center-to-red continuity, sleeve-to-black continuity, and no center-to-sleeve short. Do not infer polarity from appearance alone.
5. Lay out the existing fuse carrier. Assign F1–F4 to one fanout and F5–F8 to the other. Put F0 near the jack-lead entry, before either fanout. Tie wires to the carrier/frame so no fuse lead or solder joint supports the cable's weight.

### Make the positive and return fanouts

6. Strip about 5–6mm from an ordinary wire end, enough for the planned overlap, without cutting strands. Slide appropriately sized heat-shrink onto a wire **before** making the joint. Twist/tin stranded ends, mechanically overlap or wrap them, heat the metal joint and feed solder until it wets the strands. Allow it to cool without movement. There must be no loose strands, sharp projections or exposed conductor after insulation.
7. Positive path: jack red → F0 → 30mm red trunk → two 70mm red fanout trunks. Cut each 150mm red 20AWG branch into a 20mm fuse-input pigtail and a 130mm fuse-output lead. Each fanout trunk joins four 20mm pigtails, each going to its own fuse input. Each fuse output receives the corresponding 130mm lead. This avoids one eight-wire bundle and retains 150mm total 20AWG copper per positive branch. The pigtails fit between the fanout and the mounted fuse inputs.
8. Return path: jack black → 30mm black trunk → two 70mm black fanout trunks. Each fanout joins the matching four black branch returns. There are no fuses in ground. Keep positive and ground fanouts physically separated and individually insulated.
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
18. Secure the jack/lead separately using the empty battery-cradle tie passages. Leave approximately the last 200mm of the adapter's **factory cord before the barrel plug** slack for movement. The short 100mm jack leads run from the accessible junction into the torso; do not try to obtain 200mm of slack from them. Keep the barrel junction accessible to the operator. Do not hold it by its wires or bury it inside the duck. No new jack mounting hole is required for Phase 1.
19. The **physical motor disconnect** is pulling apart the barrel plug/jack by their bodies. This adds no switch cost. Normal sequence: stop motion, support the duck, turn torque off, then unplug motor power. For an unexpected motion, the operator can unplug immediately while keeping hands clear. A duck without motor torque can fall, so the support fixture remains necessary during commissioning. This is a supervised disconnect, not a certified emergency-stop assembly.
20. With the external adapter disconnected and OpenRB powered by USB, measure motor VDD: it must remain unpowered. An unexpected motor voltage means the modified cable still contains an unwanted positive path. Fix it before attaching the motor source. Never plug or unplug individual DYNAMIXEL motor cables live.

### Logic power and the compact Pi cable

Use the owned Xiaomi bank only for Pi, IMU and OpenRB logic in Phase 1. Its claimed 5V/3A output is a candidate source rating; it is not a measurement of this cable or its idle shutoff behavior. Keep the bank's integrated cable unmodified. The bank stays **off the robot** on a stable raised support beside the midpoint of the 0.3m test lane. Place its USB socket near Pi head height, within 100mm of the lane laterally. The midpoint-to-lane-end straight reach is then approximately 180mm before height differences, leaving useful routing/slack in a 500mm cable. Keep the loop above and clear of the feet, support its source end, and check head lowering at both ends of the lane before power. One operator can then use the Mac without carrying the bank. Its mass is not included in the Phase1 torso model. Do not strap it onto the duck without a new mass/layout check, and do not let its cable support or drag the head.

The compact cable recipe uses a genuine borrowed USB-C-to-Micro-B cable, preserves its original USB-C source plug and CC configuration, and replaces only the Micro-B end with the assembly guide's **Adafruit #1826** bare plug. Keep the power conductors at **20AWG copper or better**, with at most **500mm one-way** retained cable. At 40°C, 500mm of 20AWG copper in each direction has a calculated loop resistance of 0.03593Ω: approximately 0.036V wire drop at 1A or 0.090V at 2.5A. Connector losses and the bank's actual output are additional, so these numbers do not replace the input-voltage test. If gauge cannot be established, require a measured completed wire-pair loop resistance no greater than **0.050Ω**, excluding plug contacts, using a suitable four-wire resistance or known-current voltage-drop measurement. A normal meter's lead resistance can overwhelm this small measurement.

At the new power plug, connect Micro-B pin1 to +5V and pin5 to GND; pins2/3/4 stay unconnected. Do not add a USB PD voltage-trigger board. The separate Pi-host data lead keeps its original USB-C end at OpenRB, with Micro-B ID pin4 tied to pin5 GND at Pi. Its VBUS powers OpenRB only. Follow the assembly guide's pin-by-pin continuity and head-clearance checks before inserting either plug.

**Logic acceptance:** 4.75–5.25V measured at Pi's actual 5V/GND input during boot and a 30-minute Pi + Wi-Fi + IMU + OpenRB workload; no USB disconnects, reboot or bank auto-off. This is the project input-voltage gate. Pi Zero models lack the ordinary Raspberry Pi low-voltage detector, so `get_throttled` alone cannot establish this result. [Raspberry Pi power documentation](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-supply)

### Commissioning gates

1. **Unpowered harness:** all pin/polarity checks above pass, no exposed conductor, every cable withstands a gentle pull without moving the solder joint. Confirm the supply label says **GST60A05**, not a 12V model. Check the intact AC cord and plug before use.
2. **Source before servos:** measure positive center and voltage at the disconnected jack leads. Then use club test equipment to load the motor harness progressively at 1A, 3A and 5A. Distribute the load through branches rather than forcing 5A through one 3A group. Measure voltage at the farthest motor connector and inspect heating. If measured connector/joint losses exceed the model allowances, repair the connection first. Never create a short circuit as a “load test.”
3. **One motor at a time:** externally power one identified motor through its branch with the mechanism unloaded. Assign/read back IDs1–15. Keep normal voltage and temperature error protection enabled. A motor's factory voltage-shutdown threshold is not the allowable supply range.
4. **All motors supported:** use DYNAMIXEL Wizard's per-ID torque setting to test one unloaded motor, then one group at a time, keeping the support fixture attached. Follow with all-body holding tests while observing source current. Close Wizard before starting the exclusive Phase1 runtime; do not run both bus owners together. The runtime's arm command enables all 15 at their preloaded present positions, so its first arm is an instrumented supported test, not a claim of built-in staged enable. Log all 15 motor voltages/currents, source current and errors. Initial sampled screens are **total 5A, group 2.25A, body servo 1.3A**, with the jaw's lower configured current cap. The source is rated 6A continuous; capture short startup events with club scope/current equipment rather than relying on slow telemetry. Software stop thresholds are not instantaneous current clamps.
5. **Walking release:** after the revised 4.0V dynamics regression passes, measured servo input stays **4.0–5.5V** through the actual gait and jaw sequence, with no excursion outside the manufacturer's 3.7–6.0V operating range; source remains within 6A, sampled current screens pass, connectors and leads remain sound, and there are no resets or voltage errors. The source's overvoltage protection is not an independent 6V servo clamp. Measure stop/deceleration transients too.
6. **Task acceptance:** complete the build guide's repeated supervised walk-up and jaw pickup trials with a slack tether. Record successes, failures, object mass, current and endpoint-voltage extrema. This is the evidence required to call the Phase1 objective achieved.

A fuse opens after a current-dependent delay; a 3A fuse is not a precise 3.000A limiter. The selected main fuse remains compatible with future expansion, while the adapter's own overload response protects its output. Exact fuse opening coordination under every fault is outside this static screen. Keep the staged current-limited bench inspection and accessible physical disconnect.


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

Unplug the **external5V motor barrel connector**. Keep only the Pi and its sensor powered. The sensor tool opens the I²C device, never OpenRB, serial transport or a motor-control object. Quit every other controller and IMU reader first.

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

Keep the external5Vbarrel plug/jack within easy reach of the operator. Pull that plug to disconnect motor power. From a Mac terminal, use the client's real local path:

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

Servo bus-watchdog register 10 is set and read back before torque enable, corresponding to 200 ms without bus traffic. That firmware behavior stops commanded motion; it does not prove power disconnection or remove all holding torque. Software torque-off is still a bus request, and the launcher's final readback can report failure. The operator's accessible5Vbarrel plug/jack and support fixture remain the independent stop. Closing a laptop window is not the sole emergency stop.

The total servo-current screen is 5.0 A, with 2.25 A per fused group, matching the Phase1external 5 V / 6 A supply and separate fused distribution. Motor current bypasses OpenRB; its USB connection supplies controller logic and data. It is sampled protection, not an instantaneous electrical current limiter. Use the exact source and distribution in the Phase1power guide; the program rejects a configured screen above 5 A. A 3 A USB source is not the full-body source for this run. If using the earlier one-servo charging-bank bench, use its separate commissioning procedure; this runner expects all 15 servos.

### Verification records

`offline-results.json` reports the actual software checks. The test builds a fresh bundle and uses real community classes, actual community controller conversions over a substituted Rust transport, real Observation/UserInput/MotorCommand, and both real ONNX models. Device I/O is substituted; physical robot tests remain zero. Calibration and session logs are intentionally separate from source integrity hashes.

## Why the 6.4V video can run

The XL330 operating range is 3.7–6.0V, but its factory **Max Voltage Limit** value is 7.0V. A motor can therefore move at 6.4V without reaching that default shutdown threshold. FanGe's tutorial also removes the input-voltage shutdown trigger to avoid battery-dip interruptions. Neither changes the manufacturer's permitted operating range. The visible pack label is nominal battery voltage, not a regulated-output measurement. Our Phase 1 uses regulated 5V and retains voltage, temperature and overload protections. [ROBOTIS control table](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/), [FanGe tutorial](https://github.com/AI-FanGe/Microduck-build-tutorial).

## Verification record and next physical test

The current digital checks advance the build toward a physical MVP. They do not label absent hardware as already tested.

- **Printing:** 85 instances sliced successfully across six plates, predicted 372.97g PLA and 16h44m13s. Actual printing and fit remain arrival/club work.
- **Walking and stopping:** 33/33 simulated cases pass, including4.0V and mass changes, with sensor prediction disabled. Original20/27 baseline failures are preserved; changed controller gain and stop behavior address them. [Scope and results](simulation/README.md).
- **Hardware software path:** 50/50 offline cases pass with actual frozen controller classes and both real ONNX models. Serial transport and sensor readings are substituted; actual motor/grasp tests remain0. [Test record](runtime/offline-results.json).
- **Power:** the selected supply and stated harness assumptions calculate a4.011V worst endpoint at the5A screen. This is a narrow calculated margin, not a measured guarantee. Simulation motor-current proxies do not prove source current. The actual load/transient and task gates above are mandatory. [Calculation and exact assumptions](power-research.md).
- **Procurement:** ten buy lines across three carts total$514.92; zero held items in mapped carts after reconciliation. Club supply and Pi borrowing remain separate. [Purchasing consistency record](../procurement/english-verification.json).

Start with the unpowered harness/one-motor tests, then jaw, standing, walking/stopping and the combined task. If a stage fails, record the failure and correct that stage before continuing. Do not mark a later acceptance box from an earlier simulated or unloaded test.

## Phase 2

Add monocular camera/video and object perception, sound, and untethered battery operation after Phase 1 measurements establish actual power demand and balance. Reuse the existing jaw, OpenRB, servos, IMU, frame mounting interfaces and fused motor distribution. Reweigh and repeat walking/pickup tests whenever a module is installed. Only then select the final battery/converter capacity from measured loads.

[Exact print files](PRINT-LIST.md) · [Editable handbook](START-HERE.md) · [Frozen runtime bundle](runtime/bundle/) · [Source and calculation appendix](power-research.md)
