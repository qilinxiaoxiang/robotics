# Print files and Bambu projects

**Current Phase 1 build:** use the [Phase 1 handbook](../phase1/START-HERE.html). This earlier full-feature design remains a component reference. Its onboard battery, regulators, camera and audio instructions are deferred; use the Phase 1 power recipe and 85-instance print list for the current build.

This robot uses **15 total actuators, including one jaw actuator**. The print queue contains **64 retained source instances + 11 current parts + 14 additional idler/cap instances = 89 instances**. This is a print-stock count, not a claim that 89 parts are installed.

The source project contains 8 printed idlers and 6 caps. The full queue adds 6 idlers and 8 caps, giving **14 of each** as a maximum-one-pair-per-non-jaw-motor inventory allowance. The CAD identifies ten motor-coaxial large support-ring stations, but merges both motor-side flanges into the motor mesh. It does not establish the exact installed idler/cap count. Keep unused copies as explicit spares and record each installed pair on the first-article sheet.

Bambu Studio 2.7.1.62 predicts **390.20 g / 17 h 36 min 35 s across 6 plates** for the complete queue. The eleven changed/new parts alone predict **134.52 g / 6 h 17 min 49 s across 2 plates**. These are slicer predictions, not completed prints.

- [Complete 89-instance project](printing-full/MicroDuck-complete-89-instances-X1C-CoolPlate.3mf)
- [Eleven current parts](printing/MicroDuck-current-11-parts-X1C-CoolPlate.3mf)
- [Source catalog 1](images/07-print-catalog-1.png), [catalog 2](images/07-print-catalog-2.png), [catalog 3](images/07-print-catalog-3.png)

Both projects embed **X1 Carbon, 0.4 mm nozzle, PLA, Cool Plate, 0.2 mm layers, four walls, 30% gyroid, automatic tree supports**. Match the real machine, nozzle and plate before printing. P1S/P1P/A1, another X1 plate, and A1 mini require correct profiles and fresh arrangement/slicing. Every individual part fits inside a 180 mm cube; this does not validate an A1 mini toolpath or support layout. RoboClub machine availability is not established by these files.

The community project used P1S, Textured PEI, PLA, two walls and 15% infill. The stronger current profile changes weight. Reweigh the assembled robot before claiming the old dynamic simulation applies.

## Eleven current parts: one of each

1. **Integrated power support / PLA x 1** — 69.3 x 54.5 x 96.9 mm. Replaces a.obj / ID12. Retain the supplied orientation. Four 2 mm regulator spacers are integral; do not purchase separate spacers. Clear pocket and overhang supports.

   [power-support-integrated-print.stl](print-parts/current/power-support-integrated-print.stl)

2. **Small-regulator cover / PLA x 1** — 28.5 x 29.3 x 1.2 mm. Flat face down. Keep original scale and thickness.

   [small-regulator-cover-print.stl](print-parts/current/small-regulator-cover-print.stl)

3. **Jaw-clearance head cap / PLA x 1** — 91.8 x 122.7 x 47.2 mm. Replaces the former cap and source 5.obj / ID6. Use the registered orientation; clear cavity and hanging-post supports.

   [head-cap-mouth-clearance-print.stl](print-parts/current/head-cap-mouth-clearance-print.stl)

4. **Audio carrier / PLA x 1** — 80.2 x 64.5 x 5.8 mm. Large plane down; clear short overhangs.

   [audio_carrier_print.stl](print-parts/current/audio_carrier_print.stl)

5. **Camera tilt foot / PLA x 1** — 30.0 x 16.0 x 16.0 mm. Foot down; clear the side-ear holes.

   [camera_pitch_foot.stl](print-parts/current/camera_pitch_foot.stl)

6. **Camera cradle / PLA x 1** — 30.0 x 41.0 x 9.0 mm. Retain the supplied rear-plane-down orientation; remove all lens-hole supports.

   [camera_cradle.stl](print-parts/current/camera_cradle.stl)

7. **Torso IMU clamp / PLA x 1** — 14.5 x 42.0 x 32.9 mm. Retain the supplied side-down orientation; clean the jaws and vents.

   [imu_clamp_holder_print.stl](print-parts/current/imu_clamp_holder_print.stl)

8. **IMU rear cover / PLA x 1** — 28.7 x 39.0 x 1.2 mm. Large plane down; deburr holes.

   [imu_rear_cover_print.stl](print-parts/current/imu_rear_cover_print.stl)

9. **Eleven-fuse carrier / PLA x 1** — 44.1 x 42.6 x 19.6 mm. Base down. Clear the 6.5 mm-high lower tier through both open ends with a fine tool.

   [fuse-bank-print.stl](print-parts/current/fuse-bank-print.stl)

10. **Voltage-alarm and EN-switch carrier / PLA x 1** — 42.6 x 31.8 x 22.5 mm. Rear mounting plane down. Clear header window, tie slots, switch saddle and terminal opening.

   [voltage-alarm-carrier-print.stl](print-parts/current/voltage-alarm-carrier-print.stl)

11. **Coaxial jaw motor support / PLA x 1** — 54.2 x 73.7 x 19.2 mm. Replaces h.obj / ID24. Integral fixed sliding bushing, 10.4 mm bore centered on the jaw axis; no separate mouth bearing. Retain the source-derived orientation and clear the bore without enlarging it blindly.

   [motor-support-coaxial-print.stl](print-parts/current/motor-support-coaxial-print.stl)

## Retained source parts

Dimensions use exported print orientation. Each link is the first instance; the complete 3MF includes repeated instances. All retained parts use PLA and the source orientation. This route uses the community printed sliding supports; do not also purchase the official metal-bearing route.

The source calls p/q soft pads but assigns PLA. A later TPU pad experiment must change only those pads and validate attachment and clearance. Do not change the load-bearing jaw frame or complete combined foot to TPU without a separate design check. PLA foot traction has not been physically measured.

- **Lower head shell / 3.obj: source quantity 1 / PLA.** 91.8 x 117.1 x 20.1 mm; source IDs 2. Retain orientation and generated supports. [STL](print-parts/community-2.stl)

- **Moving jaw frame / 4.obj: source quantity 1 / PLA.** 91.4 x 69.4 x 29.0 mm; source IDs 4. Retain orientation and generated supports. [STL](print-parts/community-4.stl)

- **Do not print source 5.obj / ID6.** Replaced by a current file above.

- **Left shell / 7.obj: source quantity 1 / PLA.** 41.7 x 80.9 x 33.7 mm; source IDs 8. Retain orientation and generated supports. [STL](print-parts/community-8.stl)

- **Right shell / 8.obj: source quantity 1 / PLA.** 42.4 x 80.6 x 32.0 mm; source IDs 10. Retain orientation and generated supports. [STL](print-parts/community-10.stl)

- **Do not print source a.obj / ID12.** Replaced by a current file above.

- **Hip bracket / b.obj: source quantity 2 / PLA.** 32.5 x 19.0 x 34.5 mm; source IDs 14, 60. Retain orientation and generated supports. [STL](print-parts/community-14.stl)

- **Neck link A / d.obj: source quantity 1 / PLA.** 20.0 x 11.0 x 2.0 mm; source IDs 16. Retain orientation and generated supports. [STL](print-parts/community-16.stl)

- **Neck link B / e.obj: source quantity 1 / PLA.** 20.0 x 11.0 x 2.0 mm; source IDs 18. Retain orientation and generated supports. [STL](print-parts/community-18.stl)

- **Thigh reinforcing plate A / f.obj: source quantity 1 / PLA.** 58.1 x 45.0 x 1.0 mm; source IDs 20. Retain orientation and generated supports. [STL](print-parts/community-20.stl)

- **Thigh reinforcing plate B / g.obj: source quantity 1 / PLA.** 58.1 x 45.0 x 1.0 mm; source IDs 22. Retain orientation and generated supports. [STL](print-parts/community-22.stl)

- **Do not print source h.obj / ID24.** Replaced by a current file above.

- **Original PCB retaining strip / i.obj: source quantity 1 / PLA.** 54.0 x 6.7 x 3.8 mm; source IDs 26. Retain orientation and generated supports. [STL](print-parts/community-26.stl)

- **Neck U bracket / j.obj: source quantity 1 / PLA.** 35.0 x 18.0 x 27.7 mm; source IDs 28. Retain orientation and generated supports. [STL](print-parts/community-28.stl)

- **Lower-leg link A / k.obj: source quantity 1 / PLA.** 20.0 x 58.0 x 7.9 mm; source IDs 30. Retain orientation and generated supports. [STL](print-parts/community-30.stl)

- **Lower-leg link B / l.obj: source quantity 1 / PLA.** 20.0 x 58.0 x 7.9 mm; source IDs 32. Retain orientation and generated supports. [STL](print-parts/community-32.stl)

- **Torso base / m.obj: source quantity 1 / PLA.** 57.0 x 36.0 x 3.0 mm; source IDs 34. Retain orientation and generated supports. [STL](print-parts/community-34.stl)

- **Hip yaw/roll link A / n.obj: source quantity 1 / PLA.** 23.0 x 20.5 x 25.8 mm; source IDs 36. Retain orientation and generated supports. [STL](print-parts/community-36.stl)

- **Hip yaw/roll link B / o.obj: source quantity 1 / PLA.** 23.0 x 20.5 x 25.8 mm; source IDs 38. Retain orientation and generated supports. [STL](print-parts/community-38.stl)

- **Fixed upper lip pad / p.obj: source quantity 1 / PLA.** 87.8 x 33.3 x 3.0 mm; source IDs 40. Retain orientation and generated supports. [STL](print-parts/community-40.stl)

- **Moving lower lip pad / q.obj: source quantity 1 / PLA.** 87.7 x 32.9 x 8.6 mm; source IDs 42. Retain orientation and generated supports. [STL](print-parts/community-42.stl)

- **Community foot A, combined mesh / 111.obj: source quantity 1 / PLA.** 54.0 x 41.2 x 18.4 mm; source IDs 44. Retain orientation and generated supports. [STL](print-parts/community-44.stl)

- **Community foot B, combined mesh / 222.obj: source quantity 1 / PLA.** 54.0 x 41.2 x 18.4 mm; source IDs 46. Retain orientation and generated supports. [STL](print-parts/community-46.stl)

- **Eye outer ring / 333.obj: source quantity 1 / PLA.** 30.0 x 30.0 x 9.5 mm; source IDs 48. Retain orientation and generated supports. [STL](print-parts/community-48.stl)

- **Passive roll support / dfvdfb.obj: source quantity 2 / PLA.** 23.0 x 40.0 x 3.0 mm; source IDs 50, 51. Retain orientation and generated supports. [STL](print-parts/community-50.stl)

- **22 mm printed sliding ring / ersgtbgertgestrg.obj: source quantity 18 / PLA.** 22.0 x 22.0 x 4.0 mm; source IDs 53, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103. Retain orientation and generated supports. [STL](print-parts/community-53.stl)

- **Printed passive idler / idle_horn.stl: source quantity 8, plus 6 inventory copies / PLA.** 16.0 x 16.0 x 4.1 mm; source IDs 55, 56, 57, 77, 79, 81, 83, 85. Retain orientation and generated supports. [STL](print-parts/community-55.stl)

- **Printed idler cap / idle_cap.stl: source quantity 6, plus 8 inventory copies / PLA.** 6.8 x 6.8 x 4.6 mm; source IDs 59, 78, 80, 82, 84, 86. Retain orientation and generated supports. [STL](print-parts/community-59.stl)

- **14.6 mm printed ankle ring / rgbn.obj: source quantity 2 / PLA.** 14.6 x 14.6 x 3.0 mm; source IDs 62, 68. Retain orientation and generated supports. [STL](print-parts/community-62.stl)

- **Community right ankle / grbrgn.obj: source quantity 1 / PLA.** 36.5 x 25.5 x 39.5 mm; source IDs 64. Retain orientation and generated supports. [STL](print-parts/community-64.stl)

- **Community left ankle / thngthm.obj: source quantity 1 / PLA.** 36.5 x 25.5 x 39.5 mm; source IDs 66. Retain orientation and generated supports. [STL](print-parts/community-66.stl)

- **Head yaw/roll link / dfbdfbbbbb1.obj: source quantity 1 / PLA.** 35.9 x 34.0 x 22.5 mm; source IDs 70. Retain orientation and generated supports. [STL](print-parts/community-70.stl)

- **Right thigh / fgb.obj: source quantity 1 / PLA.** 61.0 x 47.7 x 28.0 mm; source IDs 72. Retain orientation and generated supports. [STL](print-parts/community-72.stl)

- **Left thigh / gbgb.obj: source quantity 1 / PLA.** 61.0 x 47.7 x 28.0 mm; source IDs 74. Retain orientation and generated supports. [STL](print-parts/community-74.stl)

- **Face panel and Pi mount / ghmghmghmghm.obj: source quantity 1 / PLA.** 87.7 x 44.6 x 12.5 mm; source IDs 76. Retain orientation and generated supports. [STL](print-parts/community-76.stl)

## Fixed hardware quantities for the added electronics and mounts

- M2 x 5 machine screws: 2, IMU clamp.
- M2 x 8 machine screws: 8, camera 4 and rear IMU/alarm assembly 4.
- M2 x 12 machine screws: 4, small-regulator cover.
- M2 x 18 machine screws: 4, OpenRB.
- M2 x 20 machine screws: 4, large regulator and fuse carrier; replace the old M2 x 8.
- M2 x 25 machine screws: 2, audio carrier.
- M2 nuts: 14: camera 4, OpenRB 4, audio 2, large regulator 4.
- M2.5 x 6 tapping screws: 4, Pi to face panel, no nuts; head envelope at most diameter 4.5 x 1.8 mm.
- M3 x 10 screws: 2, camera foot. M3 x 20: 1, tilt hinge.
- M3 nuts: 3. M3 washers: 4, each 0.5 mm thick.

Head M2 pan-head envelopes were checked at diameter 4 x 1.72 mm. Keep long electronics screws away from servo-case holes.

Battery retention: two Panduit PLT3S-C ties, 292 x 4.8 x 1.3 mm; trim tails and keep locks rearward. Fuse carrier: four PLT2M-C ties, 203 x 2.5 x 1.1 mm, in 2.8 x 1.6 mm slots. The lower tier is lowered 0.5 mm to leave 1.5 mm between the upper tray and lower fuse envelopes.

Short PLT.6SM-C ties, 71 x 1.8 x 0.8 mm: audio four loops of two joined ties (8), alarm two loops of three joined ties (6), EN switch one tie (1), total 15 short ties. The audio/alarm slots require the narrower width. Joined locks are physical first-article clearance checks, not verified flexible geometry. Do not substitute the 2.5 mm fuse tie through the narrow audio/alarm slots.

Battery padding needs no adhesive for retention; use closed-cell material with finished thickness at most 1 mm. If using double-coated 3M4492W, retain its battery-facing liner and measure the finished stack.

## Servo fasteners and inventory limits

Fifteen XL330 packages provide **90 M2 x 6 TAP and 150 M2 x 8 TAP** screws. The numerical inventory covers four output screws per motor (60) and up to eight case screws per motor (120). These are inventory ceilings, not a per-hole screw-length approval. Use **M2 x 6 TAP through a 3 mm output frame**: ROBOTIS warns that M2 x 8 in that location reaches the case and can damage the motor.

Each separately installed passive idler/cap uses **one M2.6 x 6 TAP center screw**, which is absent from the single-motor package. Do not substitute M2.5 or M2.6 machine screws. Source matching screws from RoboClub first; no screw-kit purchase is selected. The former two-pack FPX330-H101 option is a reference for sixteen factory screws only. If club stock lacks the required thread, length and head geometry, record that exact gap before changing the sourcing decision. Do not buy extra HNX active-output horns: this design uses the integrated XL330 output.

[ROBOTIS integrated output and idler assembly](https://emanual.robotis.com/assets/images/dxl/x/x330/xl330_assembly_integrated.png) and [output screw-length warning](https://emanual.robotis.com/assets/images/dxl/x/x330/x330_horn_screw.png), checked 2026-09-13.
