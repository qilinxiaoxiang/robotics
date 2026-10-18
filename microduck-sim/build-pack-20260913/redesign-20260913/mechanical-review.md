# Mechanical integration review

Verified 2026-09-13. Problems P5 and P6: retain the existing 15-servo body while making power, perception and service access work as a complete assembly. This review preserves the camera-guided learned-pickup goal in `../../PROJECT-CONTEXT.json` and does not release procurement holds.

## Selected mechanical route

Use the wall charger and PD receiver beside the experiment area. Carry 20 V over the long two-core cable and convert to 5 V on the robot. Put the DFR1202 in the empty former battery position in the torso, using the new open insert. Keep the regulator and the downstream wiring installed when the external source changes. A future battery module plugs into the same input connection.

The new insert and supplier-size regulator box fit inside the previous battery envelope. Fresh checks found no rigid intersections against the fixed torso assembly or at 250 recorded moving poses, covering 31,500 part comparisons, including the restored camera/audio head assembly and revised USB-service cap. This approves the proposed location for a first article. Thermal performance, actual cable forces and dynamics with the received parts require assembled measurements; those claims have not been inferred from the mesh check.

## Existing battery structure and service access

The previous 85-instance print queue includes the integrated power support. It still contains the previous small battery cradle, even though the present Xiaomi bank sits offboard. The cradle was designed around a **22 × 34 × 63 mm** Gens ace GEA8502S60E2 battery, nominal **57 g**. The historical 37–77 g battery sweep was a sensitivity range, not a measured allowable payload rating.

The printed support is **69.35 × 54.50 × 96.92 mm overall**. Its four retention passages have **2.1 × 6.2 mm** openings; their center lines are at torso Y = ±18.365 mm and Z = −30.8217 / +5.8773 mm. The existing guide specifies two 4.8 mm cable ties. Removal requires disconnecting EC2, releasing or replacing the ties and sliding the battery rearward. There is no hinged battery door or spring latch. Ordinary one-way ties are inexpensive retention, not quick release.

The Xiaomi PB1033MI is **80.9 × 65.9 × 26 mm**. It does not fit this cradle in any orthogonal orientation: its sorted dimensions 26, 65.9 and 80.9 mm each exceed the corresponding 22, 34 and 63 mm battery reservation. The manufacturer dimensions were freshly checked on the [Xiaomi specification page](https://www.mi.com/global/product/xiaomi-33w-power-bank-10000-integrated-cable/specs/).

The torso IMU holder clamps onto the two upper corners of the old battery guides. Replacing the entire integrated support therefore also changes the IMU's mounting interface. A larger battery must use a separately reviewed rear carrier or a modified support that preserves these corners and the original motor mating faces; simply stretching the whole robot print is inappropriate.

## New regulator insert

The [DFR1202 manufacturer specification](https://www.dfrobot.com/product-2907.html) gives **30 × 26 × 8 mm**, with no module weight or mounting-hole drawing in the product specification. The selected orientation places the 8 mm thickness along torso X, 26 mm width across Y and 30 mm length along Z. Its center is **(−35.5, 0, −14) mm** in the existing trunk frame.

The printable open insert is **12.4 × 31 × 61 mm**, with a computed solid-PLA upper mass of **3.32 g**. Both it and the regulator box lie inside the former 22 × 34 × 63 mm battery reservation. The main rear area is open to avoid covering the module's thermal pad. The board-to-insert box intersection is zero; nominal side clearance is 0.3 mm per side and lower clearance is 0.6 mm. Use a thin insulating edge liner at the supported board edges and narrow removable retention ties, placed clear of components and solder pads after inspecting the received board. Do not wrap the converter in foam or place a tie across its inductor.

The insert uses the existing upper/lower retention positions. The source-side XT30 pair is on a short, supported flying lead; it is not held by the converter's solder pads. The power design determines connector polarity and contact assembly. The connector remains outside the moving-joint envelope and is tied to the fixed torso frame with a service loop so unplugging loads the frame instead of the PCB.

The manufacturer describes a rear thermal pad that can be soldered to a larger copper area. The advertised 16 A maximum is not a certification of this installation at that current. Keep the converter exposed to airflow during bench validation. Weigh the converter, insert, connector and added wire together, and use that actual assembly mass for the next dynamics check.

New editable/source files, all outside the canonical print queue:

- `mechanical_geometry_check.py`: construction parameters and the fresh mesh check.
- `regulator-open-insert-body.stl`: installed torso-coordinate part.
- `regulator-open-insert-print.stl`: provided print orientation, with the broad back frame on the bed.
- `dfr1202-envelope-body.stl`: inspection reference only; do not print it.
- `mechanical-geometry-verification.json`: source hashes, dimensions, sampled pose checks and exclusions.

## Camera and audio parts to restore

The previous 85-instance queue contains none of these three required/reviewed components. Add exactly one instance each:

- `../assembly/print-parts/current/camera_pitch_foot.stl`: **30 × 16 × 16 mm**.
- `../assembly/print-parts/current/camera_cradle.stl`: **30 × 41 × 9 mm**.
- `../assembly/print-parts/current/audio_carrier_print.stl`: **80.2 × 64.5 × 5.8 mm**.

The delivered `current-print-queue.3mf` contains **89 instances**: the former 85 with the head cap replaced, plus these three restored parts and the new regulator insert. It is a single editable Bambu project on six plates; the exact source/hash list is `print-manifest.json` and the passed readback is `print-queue-verification.json`. The old voltage-alarm carrier is not part of this addition. The existing jaw-clearance head cap already has the camera mounting platform, audio mounting posts, sound holes and camera-ribbon exit.

Camera Module 3 Wide uses four M2 holes on a **21 × 12.5 mm** pattern. Its cradle has 4.8 mm rear connector clearance. The tilt foot mates to the cap through two M3 holes **22 mm apart**, each **3.4 mm diameter**. The 2026-09-26 stack audit replaces the former M2×8 screws, which leave0.27mm of the nut unengaged, with four M2 × 10 camera screws, four M2 nuts, one M3 × 20 hinge screw, two M3 × 10 foot screws, three M3 nuts and four M3 washers. Existing geometry supports starting with **0–15 degrees of downward tilt**; this is a sightline starting range, followed by camera calibration on the assembled robot.

The cap's ribbon exit is **18 × 2 mm**. The **15-pin end** of the camera cable inserts into the camera's latch socket; the **22-pin end** inserts into the Pi Zero's latch socket. Both ends plug in and lock; no soldering is needed. Both devices move with the same head assembly, so this ribbon need not span an articulated neck joint. The [official connection instructions](https://www.raspberrypi.com/documentation/accessories/camera.html#install-a-raspberry-pi-camera) warn against sharp bends. No manufacturer minimum bend radius is stated there: allocate a smooth external service loop and do not claim a validated numeric minimum. The proposed 200 mm cable's excess length stays in an open loop clear of the jaw and screw posts, rather than being folded sharply into the slot.

The audio carrier's speaker reservation is **31 × 21 × 6 mm**. The proposed CMS-30204-18SP speaker's stated 30 × 20 × 4.2 mm maximum body fits that reservation; its soldered leads require insulation and an exit clear of the diaphragm. The carrier supports the rim, never the moving diaphragm. The amplifier reservation is **12 × 22 × 21 mm** in its installed orientation. Existing audio slots are 2.4 × 1.2 mm and require narrow ties; the broader battery/fuse ties do not fit them.

## USB data plug and GPIO power access

The revised electrical route supplies the Pi through its GPIO header. Its MicroB PWR IN socket remains empty. The only MicroB plug is the ready-made SC0727 OTG data adapter: the MicroB male plugs into the Pi's USB data socket, and its USB-A female receives the USB-A male end of the existing A-to-C cable. That cable's USB-C male plugs into OpenRB. These three USB connections require no soldering.

The old cap and old 14.5 × 9.5 × 7 mm bare-plug check do not certify this moulded cable. A new cap variant, `head-cap-usb-service-print.stl`, enlarges only the data cable's side opening to **20 × 10 mm**. It replaces the current head-cap print and does not add another instance. Its fastener clearances and a **25 × 18 × 8 mm external plug receiving envelope** were freshly checked. The entire plug box was conservatively treated as external to the existing connector datum; there are no intersections against the revised cap or fixed head components. The modified cap remains one watertight solid and no removed material intersects the fastener reference geometry.

A 9 mm-high receiving box was rejected because it intersected an OpenRB component; that failed check is preserved in `usb-service-window-initial-rejection.json`. The final accepted receiving height is 8 mm. These dimensions specify what the design accepts; SC0727's published information only gives the cable length, so they are not represented as a measured manufacturer envelope. Check the received moulding before closing the cap. The remaining physical claim is whether that exact received adapter lies inside this documented envelope. No amount of widening the outer shell alone resolves a taller plug that interferes with the internal controller.

A single 2 × 20 female header housing with twelve populated contacts can occupy a **7 × 52 × 15 mm** housing-and-wire-exit envelope above the existing Pi header plane. The 2026-09-26 fastener audit tightens the former54mm length to52mm so selected4mm-diameter,1.5mm-high Pi screw heads retain1mm nominal clearance. The former4.5mm head envelope fails against the54mm housing. This receiving box passes the current coaxial jaw-support, motor, controller, camera/audio, Pi screw-head and revised-cap collision check; an 18 mm tall candidate fails against the motor and support. This is a design limit for selecting club stock, not an assertion that an unspecified housing fits or has a known contact rating. Select an unshrouded housing/contact system accepting the specified wire size, with all installed insulation and wire exits inside that envelope. The individual contact ratings remain the electrical design acceptance requirement. The GPIO leads remain flexible. Connect them and test the camera preview before closing the head. Place the A-female/A-male junction outside the cap in a supported service loop, clear of moving neck joints; do not force it into the old bare-plug reservation.

## Head harness length and service routing

The independent reach check rejected the previous **100 mm Pi power wires**: regulator center to GPIO center reaches 156.91 mm across 1,500 recorded poses, before slack. The previous **150 mm IMU cable** also fails its center-to-center lower bound, reaching 152.31 mm. These failures are preserved as regression checks in `harness-reach-review.json`; short-wire voltage calculations alone are insufficient.

Use **four 250 mm finished 22 AWG Pi power wires**. The IMU harness also finishes at **250 mm per wire**: retain 100 mm of the original #4397 JST end and splice to 150 mm female-precrimp tails, individually heat-shrink each joint and stagger the joints outside the bending section. A final 250 mm length includes the splice; prepare additional raw length if stripping consumes it. Group the female contacts in the verified header housing according to the electrical pin map.

Route both harnesses through a fixed torso service anchor near **(−20, 0, 35) mm**, then a loose arc to the head. The most conservative screen uses every corner of the regulator/IMU supplier box and every corner of the full 7 × 52 × 15 mm header housing: the longest regulator route is **188.75 mm**, and the IMU route is **174.75 mm**. Adding a separate **50 mm termination/bending allowance** keeps both below 250 mm. These checks use the existing 1,500 recorded poses; they establish available length, not a flexible-wire collision simulation. Anchor the fixed portion, keep joints outside the moving arc, and manually sweep the assembled neck before enabling torque. Do not lace the flexible arc tightly to a shaft or run it through a pinch point.

## Motor power and DATA harness closure

Use **eight 250 mm one-way 20 AWG group feeds**, including the 20 mm before each fuse, plus the fifteen retained approximately 90 mm factory motor power tails. The historical 150 mm group feeds fail six of eight groups when the defined routing and service allowance are applied. The new routed calculation deducts 20 mm before the fuse and 40 mm for terminations/service, leaving **190 mm** of geometric feed reach. Individual 90 mm motor tails reserve 30 mm for their terminations and local movement, leaving 60 mm of geometric reach.

The physical fuse tray slots 2–9 carry F1–F8; slot 1 remains F0. Keep the same electrical groups:

- F1: ID1 right ankle and ID2 right knee; F2: ID3 right hip pitch and ID4 right hip roll.
- F3: ID5 right hip yaw and ID10 left hip yaw.
- F4: ID6 left ankle and ID7 left knee; F5: ID8 left hip pitch and ID9 left hip roll.
- F6: ID11 head pitch and ID12 neck pitch; F7: ID13 head yaw and ID14 head roll.
- F8: ID15 jaw alone.

For each paired group, place its Y splice near the midpoint between the two motor cases, supported by the surrounding harness and clear of shafts. Right-leg feeds leave a torso waypoint near (−20, −30, −20) mm; left-leg feeds use (−20, +30, −20) mm. The yaw pair uses (−20, 0, −20) mm. Neck/head feeds pass (−20, 0, 35) mm. Move F7's Y splice **20 mm toward that torso waypoint** from the pair midpoint; place F8's single-tail splice **30 mm toward the torso** from the jaw motor center. This avoids spending most of the available length in the main feed while leaving unused factory tail length. The final worst feed is **185.34 mm**; the worst individual tail is **51.78 mm**. All eight feeds and all fifteen tails pass their respective 190 / 60 mm geometric limits across all 1,500 poses.

Connect DATA in the following physical order, independent of motor IDs or fuse grouping:

**OpenRB → 15 → 14 → 13 → 11 → 12 → 5 → 4 → 3 → 2 → 1 → 6 → 7 → 8 → 9 → 10.**

Reuse the original fifteen X3P180 cable pairs and their factory crimped ends as specified by the electrical assembly: each destination gets its own powered input, while the upstream inter-servo plug carries DATA only. The direct connector-endpoint screen conservatively uses all motor-case corners, plus 30 mm service/splice allowance. Fourteen local links retain **180 mm finished DATA length**. For the **ID1-to-ID6 link only**, add ordinary insulated signal wire to obtain **400 mm finished DATA length**, approximately 220 mm beyond the two original tails. Route this line up the right leg, across the fixed torso and down the left leg, alongside the corresponding supported harness. Do not suspend a loose wire directly between the ankles. The routed case-to-leg-center path reaches **327.99 mm**; with the 30 mm allowance it passes 400 mm, whereas a 350 mm routed link fails. That negative result is retained.

`motor-harness-reach.json` records every group and DATA link, endpoint assumptions, fixed waypoints, retained negative checks and the final passing lengths. The electrical specialist must use 250 mm group feeds in voltage-drop calculations. These are geometric reach checks; verify cable retention through the actual joint range and all fifteen devices responding on the completed DATA bus before walking.

## Long cable and balance

The two-meter electrical tether must be supported by the test fixture for most of its length. Keep the charger and receiver stationary. Fix the stationary cable along a table edge or overhead support, then leave only a short soft service loop to the fixed torso; avoid attaching cable loads to the camera, moving head or USB socket. Start with a 0.3 m lane and position the last support near its midpoint. The USB data route, if used, is supported alongside the power pair without bundling the moving neck section rigidly.

Even **35 cm of two 18 AWG copper conductors weighs at least 5.16 g**, before insulation and any data cable, corresponding to about 0.051 N. The new check calculates this lower bound. Thus a long cable hanging from the duck can measurably disturb balance; saying the cable is long enough does not solve the mechanical load. Use a lightly supported slack loop or counterbalanced overhead guide and check the complete walking/pickup trajectory for slack, snagging and changed posture. The interface must not become taut at either end of the lane.

## Future removable power bank module

Electrical expandability is preserved by a detachable input: the external charger/receiver/cable can be replaced by a suitably rated bank, a short USB-C lead and the same PD receiver. Use a 5 A electronically marked USB-C cable for a standard USB-C connection above 3 A. The receiver itself is **29.1 × 20.3 × 10.1 mm, 3.5 g**, per the [Adafruit manufacturer page](https://www.adafruit.com/product/5991). That receiver, its plugs, wires and carrier count toward the future module's total space and mass.

A replacement that fits the existing cavity must keep its complete occupied envelope within **22 × 34 × 63 mm**, including insulation, leads and plug access. No suitable commercial 20 V / 3.25 A (65 W) power bank has been verified within that envelope in this review. The currently owned Xiaomi bank is positively rejected for that cavity. This finding does not rule out a larger exterior rear carrier.

For a larger exterior module, use two reusable straps or a screw-retained local tray and the same disconnect. Specify the exact bank first, then generate its tray from the measured outer case plus clearance. Keep the module low and centered laterally; do not place it on the head. Preserve the original hip interfaces and the IMU clamp datum. Recheck leg/neck clearance and add the measured module inertia before approving untethered operation.

Mass must be accounted for explicitly. For illustration, a 200 g rear module with its center 60 mm behind the original center of mass shifts the combined center rearward **10.9–17.1 mm** for a hypothetical 0.9–0.5 kg robot. Those are sensitivity calculations in the new evidence file, not measured robot masses. A universal claim that any correctly sized 65 W bank will preserve walking is therefore rejected. The modular power interface and locally replaceable carrier prevent that future change from requiring replacement of the servos, controller or 5 V distribution.

## Acceptance status

The proposed on-robot regulator location and new insert pass the bounded digital fit check. Camera/audio mounting geometry and their exact omitted print instances have been recovered. The single 89-instance editable print queue, header receiving envelope, Pi/IMU harness lengths and all motor power/DATA lengths also pass their bounded digital checks. No purchase, cart mutation, physical fit, thermal, tether-force or untethered validation is claimed by this review. The actionable external checks are the first printed insert/received converter edge fit, received connector strain relief, camera cable service loop, actual finished mass, and powered thermal/voltage tests under the integrated task's load.
