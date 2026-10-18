# MicroDuck current assembly sequence

This sequence applies to the 89-instance print queue, the USB-service-window head cap, one DFR1202 converter, Camera Module 3 Wide and MAX98357A audio. Use the connection-by-connection fastener schedule alongside these steps. Dimensions are millimetres. A screw specification includes its thread type as well as diameter and length; TAP means a tapping screw for its specified plastic interface.

## 1. Print, identify and prepare

**1.1.** Use the active job list in [PRINTING/README.md](PRINTING/README.md). It identifies the current machine-specific files and replacements. Do not print both an older file and its replacement. The earlier X1 Carbon SD jobs are historical; use the current Elegoo Centauri Carbon job only on its matching machine, nozzle, plate and PLA profile. Sliced G-code already contains the layer height, walls, infill and support settings. Verify the embedded preview and matching part list before starting. Colors identify this build's groups; do not infer a mechanical part from color alone.

**1.2.** Sort the prints into the two legs, torso, neck, head, camera mount and small supports. Match part names to the [print manifest](print-manifest.json). The 89 printed instances include stock allowances and retained legacy covers; the installed fastener schedule determines installation, rather than the number of printed copies. Do not install the old voltage-alarm carrier, old regulators, an onboard battery or the old head cap.

**1.3.** Remove supports and burrs without enlarging locating holes. Inspect pilot holes, shaft bores, the fuse carrier and cable slots. Use calipers, a suitable small screwdriver, tweezers, pliers and deburring tools. Prepare soldering tools, insulation and a multimeter for the separate wiring operations. Keep the source disconnected during mechanical assembly. Tighten plastic interfaces by hand.

## 2. Label and center the fifteen motors

**2.1.** **Current compute split (confirmed 29 September):** the MacBook Pro runs control and policy computation; the Pi acquires sensors and forwards observations. The combined historical Pi controller has not been migrated or validated for this split. The mechanical and electrical arrangement below retains the modeled Pi Zero header, camera and OpenRB USB interfaces. It does not select the new motor-bus owner or transport software. Do not start the historical controller assuming it implements this architecture.

**2.2.** The mounts and camera cable target the Pi Zero form factor. Identify the received/borrowed board, installed 40-pin header and camera connector before mounting. A Pi 3 or Pi 4 is not a drop-in replacement for this head mount; the photographed borrowed Zero W has not been identified or commissioned as a Zero 2 W. Complete the independent mechanical subassemblies while board-specific fit and software commissioning are resolved.

**2.3.** Right leg from the foot upward: ID1 ankle, ID2 knee, ID3 hip pitch, ID4 hip roll and ID5 hip yaw. Left leg: IDs6–10 in the same order. ID11 is head pitch, ID12 neck pitch, ID13 head yaw, ID14 head roll and ID15 jaw.

![Motor positions](../assembly/images/06-servo-map.png)

**2.4.** Connect one unassigned motor at a time to the specified current-limited commissioning supply. Read its model and firmware, set and read back its ID, and label the case. Center the unloaded motor in position-control mode, disable torque, align the associated link, and fasten it using the scheduled screws. Record its encoder zero and positive direction. The encoder midpoint of 2048 is a starting reference; the model's mechanical zero and standing pose are separate calibration values.

**2.5.** The motor case and rotating output attach to opposite sides of a joint. Fixing both to the same rigid link locks it. XL330 has an integrated output face; no additional active-output horn is installed. Use the scheduled output screw length: a longer screw can reach the stationary case even when the printed hole diameter is correct.

## 3. Assemble the torso and legs

**3.1.** Use `power-support-integrated-print.stl` in place of original torso support ID12. It retains the motor interfaces. Fit torso base `m.obj / ID34` and hip-yaw motors ID5 and ID10. Align mating faces and shaft centers before tightening.

**3.2.** Left-leg order: ID10 output → `n/o.obj` yaw-to-roll link → ID9 → `b.obj` hip bracket → ID8 and `gbgb.obj` thigh → ID7 knee → `k/l.obj` lower-leg links → ID6 ankle → left foot. Mirror the corresponding parts for ID5 → ID4 → ID3 → ID2 → ID1. The thin `f/g.obj` pieces reinforce the thighs. Match left and right from the model IDs, rather than guessing from a short filename.

**3.3.** Use the position map below at every motor. Each card has the motor ID, front/output face and rear face; match the axes and hole pattern before inserting a screw. Blue numbers specify M2 TAP output-screw length, orange numbers specify M2 TAP case-screw length, and purple numbers specify M2.6 TAP rear-center length. A “+W0.5” mark requires one washer under the screw head. The [per-hole schedule](assembly-fasteners.json) retains the source part and measured stack for each connection.

![All 118 joint screw positions, lengths and washer locations](fastener-audit/motor-fastener-locations.png)

**3.4.** Prepare these **joint-only** quantities: M2 TAP ×4: 8; ×5: 12; ×6: 46; ×7: 2; ×8: 22; ×10: 18; M2.6 TAP ×6: 8; ×8: 2. Electronics and shell screws are additional. M2 heads must fit within 4 mm diameter × 1.72 mm height. TAP screws are not interchangeable with the machine screws used with M2 nuts. Rear-center M2.6 screws require the manufacturer-matched ROBOTIS BHS rounded head profile (5.5 mm diameter, approximately 1.565 mm high); a generic cylindrical pan head can interfere with the thigh recess even at the same thread size.

**3.5.** At ankle output faces IDs1/6 use four M2×4 TAP each; at knee output faces IDs2/7 use four M2×5 TAP each. The case corners use their individually marked lengths: the motor case has a clearance collar before the pilot thread, so matching nominal case penetration alone is insufficient. At rear centers IDs1/6 use M2.6×8 with one washer each; IDs4/9 use M2.6×6 with one washer each. IDs2/3/7/8 and IDs11/12 use M2.6×6 without a washer. All four washers must be metal DIN433/ISO7092 nominal M2.5, inside diameter 2.7 mm, outside diameter 5.0 mm and thickness 0.5 mm; a larger washer can hit the retaining pocket.

**3.6.** Install only **two separately printed idler-horn/cap pairs**, at IDs11 and12. Twelve other printed pairs are spares. The other eight rear centers retain features integrated into their printed brackets. The sixteen solid locating pegs engage matching motor holes without screws; do not drill through them or count them as missing fasteners. Keep the printed sliding supports and community ankles as matched assemblies; these sliding rings do not require a second set of metal bearings.

**3.7.** Start mating screws loosely, seat the bracket evenly, then tighten by hand. Check free movement with torque disabled after each joint; do not use tightening to force a misaligned shaft into place. The map specifies the asymmetric jaw output lengths as well: two M2×6 and two M2×7 at ID15. Their curved bearing seats have different thicknesses, so do not substitute four identical screws.

![Leg components](../assembly/images/09-leg-detail.png)

## 4. Fit the converter and fuse carrier

**4.1.** The DFR1202 occupies the former battery space in `regulator-open-insert-print.stl`. Fit its edges to the insert with a thin insulating edge liner. Keep the rear thermal surface and airflow open. Retain it with the specified narrow ties clear of the inductor, components and solder joints. The insert uses the existing upper and lower retention positions. No battery is fitted in this space.

**4.2.** Mount the fuse carrier using the current stack and screw lengths in the schedule. The old large regulator is absent; its former screw allowance must not be mistaken for another installed board. Load the lower five fuse positions through the open ends, then the upper six. Retain insulated lead sections without crushing fuse bodies. Each insulated fuse assembly must fit the existing 24 × 5 × 5 reservation. The four carrier tie paths use 2.5 × 1.1 ties of suitable length.

**4.3.** The eleven onboard fuses are F0: 10 A motor main; F1–F8: eight 3 A motor groups; F9: 3 A Pi supply; F10: 0.5 A audio supply. The separate 5 A input fuse stays beside the external PD receiver before the 2 m tether. Slot position does not change the electrical branch assignment. Use the current [power and pin instructions](START-HERE.html), which specify one shared 5 V converter.

**4.4.** Support the XT30 input lead on the fixed torso, with a service loop. Plugging or unplugging must load the frame rather than converter solder pads. Do not install the old S13V30F5, D42V110F5, low-voltage alarm or ENA switch from the historical manual.

## 5. Assemble neck, jaw and head electronics

**5.1.** Install ID12 and ID11 with the neck links `d/e.obj` and `j.obj`; add ID13 with `dfbdfbbbbb1.obj`, then ID14. Follow the motor map and fastener schedule. Route flexible loops outside the moving shaft and sliding-support faces.

**5.2.** Use `motor-support-coaxial-print.stl` for the jaw motor support, replacing source ID24. Its integral 10.4 mm sliding seat shares the corrected jaw axis. The moving lower pad is `q.obj / ID42`; the fixed upper pad is `p.obj / ID40`. Do not bond the two pads together. The integral seat replaces the separate mouth ring. Before powering ID15, verify free movement, zero, soft limits and current limit; the previously scanned 0–30° geometry range is not an automatic firmware setting.

**5.3.** Fasten the revised motor support to the bottom head shell at **S1–S4** in the location image below, using **four M2.5 × 6 TAP screws, no nuts**, with heads no larger than 4 mm diameter × 1.5 mm high. Insert each screw through the support plate toward the bottom shell; the four 2.7 mm clearance holes align with the shell’s 2.2 mm pilot holes. Seat the support against the shell before tightening. The modeled stack leaves 3.6 mm of pilot engagement and at least 2.1 mm before the shortest blind end. These four screws attach the support to the shell; ID15’s motor/output connections follow their separate schedule entries.

![C1–C3 head-cap closure and S1–S4 motor-support attachment](fastener-audit/electronics-head-fastener-locations.png)

**5.4.** Fit the cap loosely while routing electronics, then close it after the camera and cable checks in Step 6. Use **three M2.5 × 8 TAP screws, no nuts**, with heads no larger than 4 mm diameter × 1.5 mm high: **C1 and C2** are the two face-end corners; **C3** is the single center hole at the neck end. Insert through the three recessed holes in the bottom shell and into the cap’s 2.1 mm pilots. Start all three before tightening evenly. The current print restores C3’s mounting boss; confirm that this boss is present before installation. The cap provides at least 5.19 mm of pilot engagement. Align the retained face-panel rim while bringing the two shells together and keep the ribbon cable outside the seam.

**5.5.** Use `head-cap-usb-service-print.stl` as the current cap. The older mouth-clearance cap is superseded by this variant. Install the Pi on the face-panel pilot holes, OpenRB on the cap posts, and the audio carrier with the scheduled screws and nuts. Pi screws have 4 mm diameter × 1.5 mm high heads; the earlier 4.5 mm maximum head is superseded. Keep the housing and wire exits within 7 × 52 × 15 mm, centered on the existing header, to retain 1 mm nominal end clearance to these heads.

**5.6.** Identify the front face panel `community-76.stl` and circular eye trim `community-48.stl` before closing the head. Dry-seat the eye trim at its matching circular opening, and locate the face panel in the head-shell rim with the Pi facing inward. The eye trim is a cosmetic ring, not the camera mount. Keep upper lip pad `community-40.stl` with the fixed shell and lower pad `community-42.stl` with the moving jaw. Check the printed mating features retain each piece through hand-operated opening and closing. The source does not specify an adhesive or extra screw for these pieces: do not add a screw into an unverified wall or bond across the moving gap. If the first print does not retain a piece, record the fit and resolve its local retention before powered jaw motion.

**5.7.** Retain MAX98357A and the CMS-30204-18SP speaker with narrow ties through the audio slots. Slots are 2.4 × 1.2, so the wider fuse ties do not fit. Insulate exposed solder joints and support the speaker rim; keep its diaphragm free. Follow the current amplifier power, gain-resistor and I²S pin map. Both speaker output terminals connect only to the speaker.

## 6. Install camera, IMU and finished data cables

**6.1.** Attach the camera PCB at its four mounting corners using M2×10 screws and four M2 nuts. The old M2×8 screws leave 0.27 mm of the nut thickness unengaged. Assemble the tilt hinge and foot using the schedule. The two foot screws are shorter than the hinge screw. Start with 0–15° downward tilt and calibrate the actual view after assembly.

**6.2.** With power disconnected, open the camera and Pi CSI latches. The 15-contact end of SC1892 goes to the camera, the 22-contact end to Pi Zero. Seat the ribbon squarely and lock both latches. Route a smooth loop through the cap slot, clear of the jaw and screw posts. Avoid sharp folds. Verify a live camera image before final closure, then check it throughout permitted head motion.

**6.3.** Clamp BNO085 to the fixed torso rails, keep its axis marking visible, and install the rear cover using the current cover-only screw length. No alarm carrier is stacked behind it. Record the IMU's orientation.

**6.4.** Pi's USB data socket takes the SC0727 OTG adapter; its USB-A socket takes the finished 4472 cable to OpenRB USB-C. Pi's PWR IN socket stays unused. The current cap accepts the documented external plug envelope of 25 × 18 × 8; check the received molded plug before closure. These are finished USB connections, with no bare USB-plug soldering step.

## 7. Route, label and check the harness

**7.1.** Use [the current handbook's connection and pin map](START-HERE.html). Pi power uses four 250 mm 22 AWG finished leads on physical pins 2/4 and 6/14. The IMU cable has four 250 mm finished leads. All twelve Pi power/IMU/audio contacts occupy the retained 40-position header housing; keep the housing plus wire exit within the checked envelope.

**7.2.** Each motor group has a 250 mm 20 AWG positive and return feed plus the original motor tails. DATA follows OpenRB → 15 → 14 → 13 → 11 → 12 → 5 → 4 → 3 → 2 → 1 → 6 → 7 → 8 → 9 → 10. The ID1-to-ID6 link is 400 mm and routes up the leg, across the torso and down the other leg. The fourteen other links remain 180 mm. Keep power groups separated at outgoing servo plugs as specified in the current electrical instructions.

**7.3.** With the source and electronics unplugged, verify polarity, insulation, each fuse's isolation, common ground and absence of a motor-power path into USB VBUS. Secure both ends of flexible runs and move joints with torque off to check slack, rubbing and strain relief. Do not trim away the documented service allowance.

## 8. Commission before unsupported motion

**8.1.** Follow the current handbook's finite power tests: unloaded polarity and negotiated voltage, converter output, controlled-load voltage drop, thermal run, transient voltage measurements, and stop behavior. Verify all fifteen IDs respond and calibrate joint zeros before supported motion. Record actual part fit and first-print tolerances alongside the design-derived screw schedule.

**8.2.** Printing and mechanical assembly do not complete the camera-guided learned-pickup task. Camera calibration, perception, policy observation transfer and real grasp/lift/release trials remain the project's commissioning steps.
