# Wiring and first-power worksheet

Use physical Pi header pin numbers, not BCM GPIO numbers. Verify pin 1 against the board marking before installing the keyed/labeled 40-position housing. All power, IMU and audio contacts share this retained housing. Its housing and wire exits must fit the 7 x 52 x 15 mm envelope. Contacts must be compatible with the housing and rated at least 1.5 A. Keep the Pi PWR IN socket empty.

## W1. Make and inspect the unpowered harness

1. Keep the charger, Pi and motors disconnected. Label positive and ground at both ends of every wire. Confirm the XT30 polarity from the connector markings with a meter; do not infer polarity from the drawing viewpoint.
2. Set the Adafruit 5991 receiver for the 20 V profile only, with ISET open. Install the 5 A input fuse immediately after its positive terminal, before the 2 m tether. Enclose and insulate the receiver/fuse, and retain the tether so pulling it does not load a solder joint.
3. Connect the robot XT30 to DFR1202 input with an 18 AWG pair no longer than 100 mm. Connect its 5 V output and ground to the insulated star with a 16 AWG pair no longer than 100 mm. Keep the 20 V input unmistakably separate from 5 V loads. Provide the specified insulated heat spreading at the converter rear thermal surface and leave airflow open.
4. At the star, route the motor positive through F0 (10 A) and then eight separate 3 A branches F1-F8. F9 is the separate 3 A Pi branch; F10 is the 0.5 A audio branch. Grounds are common and unfused. The eleven onboard fuses use the carrier; the input 5 A fuse remains outside the robot.
5. Within 100 mm of the converter, divide the motor feeder into two insulated trunks, four branch fuses per trunk. Keep the ground split physically separate from positive joints. Each motor branch has its own 250 mm 20 AWG positive and return conductor, including the 20 mm positive fuse pigtail. Join each pair to individual motor tails near the motors, rather than passing a pair's power through one tiny servo connector.
6. Label the fifteen 180 mm X3P cables before modifying them. Split near their midpoints into approximately 90 mm tails. At a receiving servo keep pin 1 GND, pin 2 VDD and pin 3 DATA. Its GND and VDD wires join its own branch return and fused positive. At the preceding servo's outgoing plug remove and insulate pins 1 and 2; retain pin 3 DATA and join the data tails with an insulated splice. Keep factory 2.5 mm JST-EH crimps; do not force 20 AWG wire into them.
7. At the first OpenRB outgoing plug, remove VDD pin 2, retain DATA pin 3 and connect GND pin 1 separately to the common star. Leave OpenRB VIN, XT60 pads and its other three motor ports unused. Set the power-source jumper to USB/VIN 5 V. This retained electrical hookup does not mean the historical Pi motor-controller software implements the new Mac-control architecture.
8. Follow the exact DATA sequence in the assembly steps. Extend only ID1-to-ID6 to 400 mm using approximately 220 mm signal wire. Route up the right leg, across the torso and down the left leg. Position the F7 split 20 mm toward the torso from its pair midpoint, and F8 30 mm toward the torso. Keep at least 40 mm routing allowance on the long branch and 30 mm at each tail before trimming.
9. Use the pin checklist and cable endpoint list in this manual. The camera ribbon contacts must face the connector's contacts; latch orientation depends on the actual connector. Open latches before insertion, insert squarely, then close without force. Never connect or remove the camera ribbon while powered.
10. Install the 100 kOhm resistor between MAX98357A GAIN and VIN for 3 dB gain. Set a conservative software volume ceiling for the 8 ohm, 1 W speaker. Connect both amplifier speaker outputs only to the two speaker pads; neither output is ground. Insulate the amplifier underside and strain-relieve the wires.
11. With all electronics unplugged, check each branch positive reaches only its assigned VDD pins; each return reaches the ground star; and no motor VDD reaches OpenRB VDD or USB VBUS. Remove each fuse and confirm that its branch becomes isolated. Check for unintended positive-to-ground continuity. Never test isolation by shorting a powered branch.

## W2. First power and records

1. With the Pi and motors still disconnected, verify tether polarity and negotiated 20 V. Measure unloaded DFR1202 output; target 4.95-5.05 V. Stop and correct wiring or configuration if it fails before attaching a board.
2. Using an appropriate controlled load and measurement equipment, test 5.5 A, 8 A and 9 A, then a recorded 9.5 A pulse. Require input source current at most 3.25 A, upstream round-trip resistance at most 0.40 ohm and converter efficiency at least 85%. These are design acceptance targets, not completed measurements.
3. Run the 9 A load for 30 minutes. Record converter case, connector and wire temperatures. Require stable operation without protection cycling and accessible surfaces at most 60 C. If these conditions fail, fix the measured cause and repeat before robot operation.
4. During actual boot, motor enable, supported motion, jaw closure and release, measure transient voltage with an oscilloscope: Pi 4.75-5.25 V; motor test band 4.0-5.5 V. Measure stopping and regenerative transients. Do not assume the converter absorbs motor regeneration.
5. Verify the exact borrowed Pi boots, camera produces live images, IMU axes agree with actual tilt, audio stays within its volume limit, and all fifteen motor IDs answer individually. Keep the robot supported and set calibrated soft limits before enabling a joint. No tightening torque or actuator current setting is invented by this manual.
6. Implement the confirmed Mac control/Pi sensor-forwarding split. Define motor-bus ownership and transport, measure observation age, jitter and loop timing, and test stale-data and lost-command stopping on the actual robot. Do not launch the historical combined Pi controller as though this migration were complete.
7. Record actual fit, free motion, wiring isolation, supply measurements and stopping results. Physical fit/strength and commissioning remain distinct from the digitally checked screw schedule. Camera-guided alignment, learned grasp/lift/hold/release trials are the later task acceptance.

Record: date __________ board model __________ builder __________

Polarity / isolation __________ unloaded voltage __________ load-test log __________

Maximum temperatures __________ transient-voltage log __________ stop-test log __________

Joint or part requiring correction __________ photo / measurement reference __________
