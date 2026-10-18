# Full assembly and wiring source map

Verified 7 October 2026. Problems P5 and P6. This map supports the full animated guide and the separate unpowered wiring sequence. It preserves the current body, dimensions, one-source power design and user-owned stock.

## Assembly presentation reference

The [official OMX assembly guide](https://docs.robotis.com/docs/systems/omx/quick_start_guide/assembly_guide/) uses preparation, selectable 3D assembly and videos. Its useful pattern is to identify the joint, inspect reference posture, place the frame, then inspect each connection through rotation and zoom. Apply that structure to MicroDuck’s current geometry and per-hole schedule. OMX’s shipped motor IDs and 180° posture do not establish MicroDuck motor IDs, mechanical zero or standing pose.

Use [ASSEMBLY-STEPS.md](/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/ASSEMBLY-STEPS.md) for the module sequence and [assembly-fasteners.json](/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/assembly-fasteners.json) for every scheduled screw. The machine-readable [source map](/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/leg-guide-20261006/assembly-wiring-source-map.json) binds 89 existing print-stock instances to their actual files, colors and hashes. Printed spare copies are not automatically installed parts.

## Remaining modules

### Right leg

- Source print IDs: 72, 20, 32, 64, 46, 60, 38, 50, 53, 62.
- Planned motor IDs: 1, 2, 3, 4, 5.
- Assembly reference: ASSEMBLY-STEPS.md §3; existing LEFT-LEG operations mirrored using measured right geometry.

### Torso and leg attachment

- Source print IDs: 34, 8, 10.
- Current meshes: power-support-integrated-print.stl.
- Planned motor IDs: 5, 10, 12.
- Assembly reference: ASSEMBLY-STEPS.md §3.1–3.6.

### Converter, fuse bank and input retention

- Source print IDs: current replacement mounts.
- Current meshes: regulator-open-insert-print.stl, fuse-bank-print.stl.
- Fuse carrier retained without old regulator board: 4 × M2 x 20 machine + M2 nut.
- Assembly reference: ASSEMBLY-STEPS.md §4.

### Neck pitch and head pitch

- Source print IDs: 16, 18, 28, 55, 59, 53.
- Planned motor IDs: 11, 12, 13.
- Assembly reference: ASSEMBLY-STEPS.md §5.1; per-hole assembly-fasteners.json.

### Head yaw and roll

- Source print IDs: 70, 28.
- Planned motor IDs: 13, 14.
- Assembly reference: ASSEMBLY-STEPS.md §5.1; per-hole joint audit.

### Jaw and head shell

- Source print IDs: 2, 4, 40, 42, 48, 76.
- Current meshes: motor-support-coaxial-print.stl, head-cap-usb-service-print.stl.
- Planned motor IDs: 14, 15.
- Revised motor support to bottom head shell: 4 × M2.5 x 6 TAP head<=4 diameter x1.5 high; no nuts.
- Current three-point cap to bottom head shell: 3 × M2.5 x 8 TAP head<=4 diameter x1.5 high; no nuts.
- Assembly reference: ASSEMBLY-STEPS.md §5.2–5.6.

### Pi, OpenRB and audio carriers

- Source print IDs: 76.
- Current meshes: head-cap-usb-service-print.stl, audio_carrier_print.stl.
- Pi Zero 2 W to face: 4 × M2.5 x 6 TAP Uxcell a16060200ux0367; head4 diameter x1.5 high; no nuts.
- OpenRB to current cap: 4 × M2 x 18 machine + M2 nut.
- Audio carrier to current cap: 2 × M2 x 25 machine + M2 nut.
- Assembly reference: ASSEMBLY-STEPS.md §5.5–5.7.

### Camera tilt mount and torso IMU

- Source print IDs: current replacement mounts.
- Current meshes: camera_pitch_foot.stl, camera_cradle.stl, imu_clamp_holder_print.stl, imu_rear_cover_print.stl.
- Camera PCB to cradle: 4 × M2 x 10 machine + M2 nut.
- Camera foot to cap: 2 × M3 x 10 button head + 0.5 washer + M3 nut.
- Camera cradle pitch hinge: 1 × M3 x 20 + two 0.5 washers + M3 nut.
- IMU clamp pressure screws: 2 × M2 x 5 into1.6 pilot; no nuts.
- Rear cover without removed alarm carrier: 4 × M2 x 6 into existing plastic pilot; no nuts.
- Assembly reference: ASSEMBLY-STEPS.md §6.

Right-leg links use the measured right thigh, ankle and foot. Equivalent left/right reinforcing and lower-link prints may share geometry. ID1 and ID4 rear-center screw heads each receive the specified 0.5 mm metal washer. The current full-guide builder adds the right M2×6 TAP ankle-to-foot retainer after checking actual64/46 annular rays and an empty core with surrounding material at multiple depths; it does not rely only on a mirrored point. Physical fit remains unverified.

Only neck/head pitch IDs11 and12 use separately printed idler horn/cap pairs. The other printed copies remain spares. ID11 and12 each have eight scheduled M2×6 horn screws across two faces, four case screws (two M2×8 plus two M2×10), and one M2.6×6 rear-center screw. ID13 has four M2×5 output and four M2×10 case screws; ID14 has four M2×6 output screws. ID15’s curved jaw seats use two M2×6 plus two M2×7 output screws.

Fit the jaw support with four M2.5×6 TAP screws at S1–S4; close the head with three M2.5×8 TAP screws at C1–C3. The fixed upper pad is source40, moving lower pad42, moving yellow jaw4, face76 and cosmetic eye48. The source supplies no adhesive or extra screw recipe for those trim/pad interfaces; verify their dry retention rather than inventing a connection.

## Unpowered wiring sequence

The [wiring data](/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/leg-guide-20261006/wiring-guide-data.json) provides 11 stages, 51 selectable endpoint connections, eight fused motor groups, 15 DATA links and a 40-pin header diagram with 12 used contacts. Each connection retains two endpoints, physical pins, medium, purpose and the available source references. The diagram labels describe the intended harness; they do not identify a loose physical cable from a photograph.

1. **Identify connectors with power disconnected.** Disconnect the charger, Pi and motors while making the harness. Locate physical pin 1 from the actual Pi marking. Numbers shown here are header positions, not BCM GPIO numbers. Label both ends of each lead and read actual connector polarity.
2. **Prepare the 20 V input.** Set only the 20 V switch on receiver 5991; keep ISET open. Fit the external 5 A input fuse immediately after the positive terminal, before the 2 m tether. Insulate and retain the receiver and cable joints.
3. **Connect the converter and 5 V star.** Keep the 20 V input distinguishable from all 5 V loads. Fit DFR1202 in the open insert with insulation, rear heat spreading and airflow. Make separate insulated positive and ground star joins.
4. **Assign motor, Pi and audio branches.** F0 is the 10 A motor main; F1–F8 are eight 3 A motor branches. Split into two four-branch trunks within 100 mm of the converter. F9 is the separate 3 A Pi branch; F10 is the 0.5 A audio branch. Grounds are common and unfused. Carrier slot numbers do not determine electrical assignments.
5. **Wire the eight motor groups.** Label fifteen X3P cables before modifying power conductors. The receiving servo plug keeps pin 1 GND, pin 2 VDD and pin 3 DATA. Pins 1/2 join that servo’s assigned branch. At the preceding outgoing plug remove and insulate pins 1/2, retain pin 3 DATA. OpenRB’s first plug uses the separately specified ground connection. Locate the F7 split 20 mm and F8 split 30 mm toward the torso from the pair midpoint; keep at least 30 mm tail allowance and 40 mm on the long branch before trimming.
6. **Connect the DATA chain.** At the first OpenRB outgoing plug remove VDD pin 2; retain DATA pin 3 and connect pin 1 separately to the ground star. Leave OpenRB VIN, XT60 pads and its other three motor ports unused. Follow OpenRB →15→14→13→11→12→5→4→3→2→1→6→7→8→9→10.
7. **Fit Pi power and OpenRB USB.** Use physical pins 2/4 for 5 V and 6/14 for ground. All twelve power, IMU and audio contacts share the retained 40-position housing. Keep Pi PWR IN empty and covered; set OpenRB jumper to USB/VIN 5 V while disconnected.
8. **Connect the torso IMU.** Mount BNO085 on the fixed torso with axis markings visible. Read each signal at both connector ends before placing its contact in the Pi housing.
9. **Latch the camera ribbon.** Open both latches with power disconnected. Fit the 15-contact end to Camera Module 3 Wide and 22-contact end to Pi Zero. Contacts face connector contacts; insert squarely, lock, then route a smooth loop clear of jaw and screw posts.
10. **Connect audio and speaker.** Power the amplifier through F10. Fit 100 kΩ from GAIN to VIN for 3 dB gain; retain amplifier and speaker with narrow ties. Connect both speaker outputs only to speaker pads; insulate solder joints and strain-relieve.
11. **Complete the unpowered inspection.** With electronics and source unplugged, check continuity, polarity, insulation and unintended positive-to-ground paths. Remove each fuse and confirm its positive branch is isolated. Confirm motor VDD is isolated from OpenRB VDD and USB VBUS. Move joints with torque off to check slack, rubbing and strain relief; preserve service allowance.

The route is MDY-14-ED → its original cable → [5991 receiver](https://learn.adafruit.com/adafruit-usb-type-c-power-delivery-switchable-breakout?view=all) at fixed20 V with ISET open → external5 A fuse → 2 m 18 AWG tether and XT30 → onboard [DFR1202](https://www.dfrobot.com/product-2907.html) → common5 V star. The converter input and output stay distinct. Its manufacturer current maximum does not replace the existing whole-robot load and thermal checks.

The [OpenRB manual](https://emanual.robotis.com/docs/en/parts/controller/openrb-150/) specifies TTL connector pins1 GND,2 VDD,3 DATA. This build powers motor branches externally and keeps OpenRB logic on the Pi USB path, with its jumper in USB/VIN5 V. The [XL330-M288 specification](https://emanual.robotis.com/docs/en/dxl/x/xl330-m288/) recommends5 V and allows3.7–6 V; the20 V tether terminates at the converter. The controller’s USB built-in fuse protects a different path from the external motor harness. Mechanical modules can be built before fitting the harness fuses; the current wiring retains them.

Physical Pi pins2/4 receive fused5 V and6/14 return to the star. The [BNO085](https://learn.adafruit.com/adafruit-9-dof-orientation-imu-fusion-breakout-bno085/pinouts) uses1→VIN (3.3 V),3→SDA,5→SCL,9→GND. The manufacturer explicitly documents Pi I2C wiring and a400 kHz configuration recommendation; successful operation on this actual board remains a later readback.

The [camera reference](https://www.raspberrypi.com/documentation/accessories/camera.html) supports Standard-Mini15-to-22-contact wiring for Camera Module3 and PiZero. SC1892 is the planned200 mm ribbon. Latch contact faces are read from the actual connectors, rather than guessed from the blue tabs.

For [MAX98357A](https://learn.adafruit.com/adafruit-max98357-i2s-class-d-mono-amp/pinouts), physical12→BCLK,35→LRC/LRCLK,40→DIN and20→GND. F10 supplies VIN;100 kΩ from GAIN to VIN selects3 dB. Both speaker outputs go only to the speaker pads. The8 Ω,1 W speaker requires a software volume ceiling during later commissioning.

## Source precedence and physical gaps

The user confirmed all prints, including orange, are already printed. All15 DigiKey order101587695 lines are recorded received on29 September, and the user has assembled OMX-AI. The guide should identify existing items rather than emit new purchases, stock-shortage claims or pending-delivery steps.

PROJECT-CONTEXT takes precedence over the older compute paragraph: the MacBook Pro runs control/policy; the Pi acquires and forwards sensors. The electrical Pi USB/OpenRB bridge remains the retained transport. The motor-bus owner, runtime migration and timing are not physically validated by this wiring guide.

The borrowed board photograph suggested a first-generation ZeroW, while the modeled mount and contract name Zero2W. The actual revision, installed header and connector fit need identification before board-specific fitting. Each reused motor’s type and unique ID likewise needs readback; OMX’s shipped numbering cannot be copied onto a15-motor bus.

The historical assembly manual’s battery, alarm, two regulators, old cap and several screw lengths are superseded. The source map records these contradictions explicitly. Physical cable identities, polarity, continuity, printed retention, joint slack and electrical commissioning are separate checks; no board was energized, cable modified, motor configured, print sent or purchase initiated in this source task.
