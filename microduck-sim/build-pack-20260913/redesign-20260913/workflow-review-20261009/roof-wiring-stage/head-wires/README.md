# Roof wiring review stage

This directory is a **renderable partial wiring study**, not an accepted harness or print release. All coordinates are current robot world millimetres. Import `manifest.json` without an extra transform. Existing robot geometry stays in `original-body-converter`; use the separately restored roof from `../roof`.

The CAD architecture uses Mac USB → OpenRB through the rear service opening. Pi USB is unused. Runtime migration is not performed. CSI carries camera power and data; there is no separate camera power line. The Pi remains the sensor endpoint for the camera, I2S and BNO085.

## Visible result

`manifest.json` contains 21 individually named/color-coded meshes. `routes.json` contains source/target nets, endpoints, centreline points, lengths and receiving assumptions. `stage-summary.json` states the specific failures. Power and IMU items have red review status; their presence in the model is not a successful-route claim.

- The source-bound 200 mm camera placement and two speaker routes are reused. A generic whole-line boolean is not interchangeable with the original connector-aware acceptance.
- The four I2S routes use the current 2 mm Pi spacer. Their original jaw-support and FFC crossings were eliminated in one finite local repair. Pin 40 still intersects the restored roof by 0.002045 mm³. This is retained as a failure, not a manufacturing allowance.
- Mac USB-C uses the published 27 mm overmould length. Its 7 mm cross dimension is still a receiving assumption. The external flexible span is an illustrative 102.5 mm route toward an unmodeled host adapter, not a validated motion tether.
- J4 VIN+/GND mouth positions come from the registered actual terminal, not the board centre. The shown wires stop at the mouth; clamp insertion depth/tool access is not accepted.
- DFR pad orientation is a proposed installation orientation derived from the manufacturer's pad image. BNO085 remains an installation envelope: its four loose ends are not fake seated sockets.
- Pi pins 2/4 supply 5 V; pins 6/14 are returns. BNO085 pins 1/3/5/9 map to 3.3 V/SDA/SCL/GND. I2S pins 12/35/40/20 map to BCLK/LRCLK/DIN/GND. Amp power-return and its signal-reference GND remain separately named conductors on one common net.

## Evidence and limits

`negative-initial-local-check.json` and `i2s-ffc-localization.json` retain the causal failures. `i2s-repair-check.json` covers the four repaired routes against 160 other scene objects plus 142 source-bound OpenRB enclosures, with explicit AABB exclusions and invalid-result records. It does not certify self-intersection, wire-to-wire clearance or articulation. `local-check.json` retains failed power/IMU paths. Open source meshes and degenerate terminal-plane results are not treated as empty intersections.

No print parts, joint limits or original robot spacing were changed. No additional wire stock is implied by a calculated route length. The former eleven-fuse array and Pi OTG route are excluded.

Primary interface evidence: ROBOTIS OpenRB-150 e-manual and current J4 registration in `../roof/j4/terminal-registration.json`; Adafruit 4472 drawing URL recorded in `mac-usb-route.json`; DFRobot DFR1202 official product/pad image. The converter and IMU endpoint assumptions remain explicit until their installed board frames are registered.
