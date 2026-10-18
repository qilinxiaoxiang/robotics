# External USB harness review — P5/P6

This candidate preserves the existing connection: **Pi Zero W Micro-B data → SC0727 USB-A female → Adafruit 4472 USB-A male → OpenRB USB-C**. Pi power remains on GPIO. The two external cables are unplugged before opening the cap. This is not a proposal to hide either cable or the intermediate USB-A coupling inside the head.

## Manufacturer evidence

[Adafruit 4472](https://www.adafruit.com/product/4472) specifies approximately 6 inches and a 4.5 mm cable diameter. Its linked [manufacturer drawing](https://cdn-shop.adafruit.com/product-files/4472/4472_PCM-0207_TYPE_C_M-USB2.0_A_M__.pdf), saved here, dimensions the USB-C moulding plus relief at **27 mm**, the USB-A moulding plus relief at **22.9 mm**, and the length arrow between the two metal/moulding shoulders. Reading six inches as 152.4 mm therefore leaves **102.5 mm between the flexible-cable exits**. The C-side 12 mm width is dimensioned; the inherited 7 mm thickness remains a receiving assumption. The drawing's material-list wording says “female” at C while the linked product and drawn metal tip are male; the product's male topology is retained, and the discrepancy is recorded rather than changing connector type.

The official [SC0727 product page](https://www.raspberrypi.com/products/micro-usb-male-to-usb-a-female-cable/) specifies 80 mm cable length but does not define the measurement endpoints, mould sizes or bend radius. Official Product Information Portal searches for `SC0727` and `Micro USB Male` returned no documents on 2026-10-08. This is a specific documentation gap, not evidence that the two connector mouldings are included or excluded. The candidate explicitly uses **80 mm flexible span**, a **3.5 mm cable diameter**, and a **25 × 20 × 12 mm female receiving body** as conditional assumptions. It must not be described as a measured or fully source-dimensioned SC0727 fit.

## Results and sequence

`published-usbc-verification.json` replaces the old 15 mm axial receiving box with the official 27 mm run, extending outward from the same seated shoulder. All 121 rear insertion poses are checked against the current integrated scene.

`full-harness-report.json` records both full cable centre lines and the USB-A male/female receiving bodies. The 102.5 mm A–C flexible run follows a rounded rear-side route. Both cables use an explicitly assumed 10 mm centreline bend radius; no manufacturer minimum bend radius was found. Static solid intersections, 61 intermediate USB-A mating poses and tube self-clearance are separate checks.

`harness-path-verification.json` records 229 articulated states. It preserves failed extremes of head pitch and compares them with the rigid head baseline; source joint limits are not automatically usable hardware limits. A sampled clearance result does not establish continuous motion, cable fatigue or connector load tolerance.

Install both board plugs after cap fastening while leaving the USB-A ends free. Shape the loose cables, mate USB-A without tension, then retain the route. Release restraint and unplug both board plugs before opening the cap. The published connector insertion checks describe local mating strokes; they do not imply the whole flexible harness is a rigid body during plugging.

**The optional removable guide is rejected and must not be integrated:** its arm adds IMU collisions at neck pitch50–60°, although its neutral geometry and insertion paths clear. The optional removable guide uses the existing rear cap screw and does not alter the shell. Its independent static, motion and installation receipts determine whether it may be shown. Its 4.8 mm bore receives the 4.5 mm cable but does **not** establish axial frictional strain relief. Do not issue it as a print-ready restraint or claim that cable weight is supported by a tested fixture.

## Rebuild

Use `/tmp/microduck-cad-venv/bin/python` to run, in order:

```sh
python build_harness.py
python verify_harness.py
python deliver_harness.py
```

The rejected guide scripts and their failure receipts are retained as historical diagnostics; do not rerun them into the candidate. The USB-C model is generated directly from the original local shoulder and current OpenRB transform. It never rescales the mutable legacy receiving STL, so repeating the build cannot expand an already 27 mm connector.

The current head, jaw, cheek, electronics, receiving envelopes and retained hardware are read from the integrated viewer configuration. No source shell, board or camera pose is modified. Physical cable fit, actual flex-span interpretation, strain-relief force and durability remain unaccepted. The viewer fragment marks the complete route as conditional review geometry; the published-length USB-C body has its own independent acceptance scope.
