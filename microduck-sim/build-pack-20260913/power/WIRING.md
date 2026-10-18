# Power and signal wiring

**Current Phase 1 build:** use the [Phase 1 handbook](../phase1/START-HERE.html). This earlier full-feature design remains a component reference. Its onboard battery, regulators, camera and audio instructions are deferred; use the Phase 1 power recipe and 85-instance print list for the current build.

Revised 2026-09-13. **15 servos total, including jaw ID15.** This is the electrical connection definition; lengths are design ceilings, not measured flexible routes. Check joint travel and actual cable strain during assembly. The servo regulator is revised to Pololu #5671 D42V110F5; camera, OpenRB and trunk IMU are unchanged.

## Battery and the two independent 5V rails

1. Connect the GEA8502S60E2 battery EC2 to an EC2 device-side male, meaning metal pins. Purchase two GEAX6F2E2M adapters: retain the first intact for charging. With everything disconnected, cut the XT60 off the second and retain EC2 plus no more than 50mm of original lead. Verify polarity by continuity, not connector gender alone.
2. Put **F0, Littelfuse 0251010.MXL, 10A**, in positive as close as practicable to the EC2 entry. Continue to the split with red 16AWG stranded copper; battery negative returns through black 16AWG. Do not alter the battery's original 18AWG leads.
3. Feed D42V110F5 #5671 VIN/GND with 16AWG.
4. Feed S13V30F5 #4082 VIN through **F9, 0251003.MXL, 3A**, using 20AWG positive/ground. F9 belongs before VIN, avoiding an additional fuse drop on Pi's 5V output.
5. Large-board VOUT/GND goes through 16AWG, each lead preferably no longer than 100mm, to the servo distribution star. Small-board VOUT/GND splits separately to Pi and audio; audio positive passes **F10, 0251.500MXL, 0.5A**, at the branch origin. **Never connect the two VOUT rails together. Grounds are common.**

Solder directly to the designated power holes. The compact CAD does not accommodate optional tall terminal blocks. Do not carry motor power through 2.54mm headers, breadboards or loose Dupont connectors. Insulate each splice with heat-shrink and provide strain relief. Do not shrink-wrap an entire regulator.

**Main disconnection is the accessible EC2.** Pololu #1408 is only the large regulator's ENA switch: center/common to ENA, one side to GND, other side unconnected. Grounded disables; open uses the internal pull-up to enable. Its 0.3A@50VDC rating is not suitable for the motor power path. Do not connect Pi GPIO directly to the regulator's VIN-pulled-up ENA. [Switch](https://www.pololu.com/product/1408)

Leave **ENB, PFM and PG unconnected** in this build. ENB is not the shutdown connection. Identify VIN, VOUT and GND from the new board silkscreen, not the old board pad locations. [Regulator connections](https://www.pololu.com/product/5671)

The ENA switch stops the servo rail but leaves Pi powered. Support the robot before removing holding torque. At shutdown, stop motion, shut down Pi, disconnect EC2 and separately remove the balance alarm. OpenRB reset or its DXL LED does not indicate that external servo power is off. This switch is not a certified emergency-stop system.

## Eight fused groups, fifteen independent servo power tails

F1–F8 are each 0251003.MXL, 3A, on the large regulator's 5V output. Use 20AWG positive/ground feeds to each group's Y split, no longer than 150mm one way. From the split, each servo gets its own 22AWG or original ROBOTIS 21AWG positive/ground tail, no longer than 100mm one way. No first-servo connector carries the second servo's power.

- F1: ID1 right ankle; ID2 right knee.
- F2: ID3 right hip pitch; ID4 right hip roll.
- F3: ID5 right hip yaw; ID10 left hip yaw.
- F4: ID6 left ankle; ID7 left knee.
- F5: ID8 left hip pitch; ID9 left hip roll.
- F6: ID11 head pitch; ID12 neck pitch.
- F7: ID13 head yaw; ID14 head roll.
- F8: **ID15 jaw**. The existing gait model still commands only IDs1–14; assigning this ID does not implement grasp control.

Data order is independent of power groups. All servos share one DATA bus; commands and replies use that wire at different times, without active forwarding by intermediate servos. Each motor has a dedicated power-ground return via its Y split. Between successive servos, carry **DATA only**, avoiding unintended power or thin-ground bypasses.

JST EH is **2.5mm pitch**, not a 2.54mm Dupont substitute. Pin1=GND, Pin2=VDD, Pin3=DATA. Housing EHR-3; contact SEH-001T-P0.6; board header B3B-EH-A. The EH 3A rating assumes 22AWG; the standard contact accepts 30–22AWG, so do not force purchased 20AWG into it. Keep ROBOTIS's original 21AWG factory crimps intact. [ROBOTIS connector reference](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/#connector-information), [JST datasheet](https://www.jst-mfg.com/product/pdf/eng/eEH.pdf)

### Reusing the fifteen included X3P180 cables

The selected servo products each include one 180mm X3P cable. Reuse their 30 factory-crimped ends:

1. Label pins, photograph the original order, then cut each cable near its middle, making two approximately 90mm tails.
2. The downstream servo input end retains all three pins. Connect Pin1/Pin2 to that servo's group Y ground/fused 5V.
3. The upstream servo output end retains only Pin3: extract Pin1/Pin2 terminals. On the first cable's OpenRB end, extract Pin2, retain Pin3 DATA, and route Pin1 independently to the common distribution ground.
4. Rejoin the two DATA tails with a soldered, insulated, strain-relieved splice. Continue to all 15 servos.
5. Result: 15 independent powered input plugs, 14 DATA-only servo output plugs and one OpenRB plug. Label DATA-only plugs so they are not replaced with ordinary three-wire cables.

Two extra X3P180 cables can serve as spares or longer measured routes. Prefer a physically adjacent chain over long star stubs. Begin communication at 1Mbps and confirm all 15 unique IDs. Wiring-drop calculations do not establish signal integrity.

With power disconnected, open each fuse branch in turn and verify its servo VDD pins are isolated from the 5V star. With all motor fuses open, USB-powered OpenRB must not feed any servo VDD. Repeat on a current-limited bench after continuity checks. Never test a fuse by shorting a live battery.

## Pi, camera and USB

Pi Zero 2 W **PWR IN** receives small-board 5V via a custom Adafruit #1826 bare MicroB connector and 20AWG wire, preferably much shorter than the 200mm one-way ceiling. Micro Pin1=+5V, Pin5=GND; pins2/3/4 remain open. The other USB port is the OTG data/host connection to OpenRB.

Purchase #1826 quantity three: two installed, one spare. Bare connector is 14×8.5×6mm, 0.6g; the assembly check reserves 14.5×9.5×7mm after local insulation. The 26×10×7mm full plastic shell has not been cleared for the compact head. Measure finished solder/insulation and do not force the Pi socket. [Manufacturer](https://www.adafruit.com/product/1826)

Make the data lead by removing only the USB-A end of Adafruit #4472, a 152mm USB-A-to-C data cable. Retain the factory C connector and internal paired/shielded cable. Verify conductor continuity before cutting and connect:

- Original A Pin1 VBUS → Micro Pin1.
- Original A Pin2 D− → Micro Pin2.
- Original A Pin3 D+ → Micro Pin3.
- Original A Pin4 GND → Micro Pin5.
- Micro **Pin4 ID → Micro Pin5 GND**, selecting Pi host behavior.

Do not confuse USB-A Pin4 with Micro Pin4. Preserve the D+/D− pair to the connector with minimal untwisting, and preserve shield/drain continuity to the connector shell. Do not alter the C-end configuration resistors. Label the finished leads POWER and DATA HOST. USB VBUS supplies OpenRB logic only. A desktop computer and Pi must not both act as hosts on this connection; disconnect the Pi data cable before a desktop bench connection. [Cable](https://www.adafruit.com/product/4472), [Pi OTG ID behavior](https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/raspberry-pi/boot-usb.adoc)

Check pin continuity and adjacent shorts before power. Then confirm enumeration and 30 minutes of stable serial traffic with camera, Wi-Fi and audio active. The factory C shell and finished Pi-end envelope still require measurement. #1099 molded OTG adapter is not required in this build.

Camera Module 3 Wide receives power and data through CSI: **15-pin wide end at camera, 22-pin narrow end at Pi Zero**. Do not add a separate 5V camera feed. Disconnect power before touching latches and verify contact orientation against the manufacturer's instructions.

Standard Pi Zero 2 W has an unpopulated 40-pin header. Solder 2×20 pins or use a verified pre-soldered version with the same fitted direction/height; do not add a tall HAT.

## Amplifier and speaker

At small-board VOUT, put **F10, 0.5A**, before the thin audio branch. Initial continuous target after derating is 0.375A; 1W audio assumes approximately 0.217A. Verify startup pulses. Use 24AWG paired positive/ground, no longer than 250mm one way, fixed separately from motor power.

Use Adafruit **#1131 matched JST-PH two-pin cable pair**, one set. Its original leads are **26AWG, 80°C**, not 24AWG. Retain at most 50mm at each connector and splice to the 24AWG main segment. Verify and label VIN/GND polarity; this connector pair is audio-only, not Pi or servo power. [Manufacturer](https://www.adafruit.com/product/1131)

- Pi physical12 / GPIO18 → BCLK.
- Pi physical35 / GPIO19 → LRC/LRCLK.
- Pi physical40 / GPIO21 → DIN.
- VIN → the fused small-board audio 5V branch; GND → logic ground.
- GAIN → VIN through **100kΩ, 1%**, selecting 3dB. Keep SD at the module's default configuration; never feed battery voltage to a digital pin.
- Speaker leads → OUT+/OUT−. Both are bridge outputs: **neither speaker lead goes to ground**. Use a differential/isolated measurement; never clip a grounded oscilloscope lead to OUT−.

Adafruit #3006's 2024 revision includes a pre-soldered speaker terminal; its signal header still needs soldering, or use direct wires for less height. #3923 already has short speaker leads; extend with 26AWG if needed. A “3W amplifier” is not a suitable volume target for the selected 1W speaker.

## Trunk IMU and battery alarm

BNO085 uses I²C, matching the community reader. The Adafruit #4754 STEMMA QT/JST-SH four-pin-to-female lead connects:

- VIN → Pi physical1, 3.3V.
- GND → physical6.
- SDA → physical3 / GPIO2.
- SCL → physical5 / GPIO3.

3Vo is the breakout's regulated output, not VIN. Powering VIN from 3.3V keeps the I²C pull-ups at Pi logic levels. Keep flex allowance through the neck and separate the lead from motor current paths. I²C timing/clock-stretch compatibility and flexible cable motion require physical checks.

HobbyKing DL-Volt-Alarm connects to the battery's JST-XHR-3P balance connector through a separately purchased 150mm 2S JST-XH3 male/female extension. Align the connector's negative end with the alarm's marked `−` pin, then cell1 and cell2; remaining pins stay empty. Confirm each adjacent pair is approximately one cell before connection.

The manufacturer photo shows five right-angle pins at the LED-side short edge, projecting along the 38mm axis. No dimensioned pin drawing confirms whether 38mm includes them. Reserve another 12mm for the plug and 10mm for wire bending outside that edge. Do not cut keying or force a misaligned plug. The alarm has no supplied extension listed.

This alarm buzzer is separate from the duck-call speaker. It still draws from the balance connector after EC2 is removed, so disconnect both after use.

## Quantities and fabrication

- 0251010.MXL 10A: install one, spare two.
- 0251003.MXL 3A: install nine, spare three.
- 0251.500MXL 0.5A: install one, spare two. **Eleven onboard fuses total.**
- Fuse body allowance: 7.11mm length, up to 3.18mm diameter. After lead trimming, solder and heat-shrink, design to 24×5×5mm and measure the finished result. Label every rating; similar appearance is not identification.
- Obtain from RoboClub first: 16AWG red/black 0.5m each; 20AWG red/black 2m each; 24AWG red/black 0.5m each; about 1m total assorted 26AWG signal/speaker wire. Available stock is not all installed mass. Use genuine stranded copper, not copper-clad aluminum; main-wire insulation at least 105°C. The #1131 80°C factory tails are allowed only on the low-current audio branch.
- Obtain from RoboClub first: solder, flux, heat-shrink, insulation, ties and strain-relief materials. Use soldered, individually insulated copper splices; do not concentrate motor power in breadboards or Dupont headers.
- The current assembly provides removable fuse/alarm/ENA holders. Keep fuses and sharp wire ends away from the soft battery. Do not use fuse bodies as structural supports.

Direct plug-in connections are CSI, STEMMA QT, speaker terminal and the intact charging adapter. The **second onboard EC2 adapter requires cutting and soldering**, as do both Pi USB leads, ENA switch leads, motor distribution, fuses, amplifier connections and the bare Pi header. Complete all soldering, continuity and gentle pull checks before connecting a battery.
