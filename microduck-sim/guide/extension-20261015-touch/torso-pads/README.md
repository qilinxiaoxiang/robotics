# Torso-shell touch pads (geometry study, 2026-10-20)

Problem IDs: P0 and P5, as in `../PLAN.md`. Status: dropped by Shawn on 2026-10-20 before soldering; kept as a record. No print file, guide data or firmware changes.

Two 18 x 18 mm copper pads (four 5 mm strips each) on the inner face of the white torso shells, read by the XIAO
ESP32-S3 in the head cap on its two spare touch inputs D9 (left) and D10 (right). The second option is a separate
reader in the torso.

## Files

- `torso_pads.py`: the pad search, clearances, wire routes, plug spaces and torso board fit. Writes `results.json`.
- `render_pads.py`: writes `pad_shell_left.png` and `pad_shell_right.png` (inner face, pad, lead, nearest parts).
- `results.json`: every number below, plus `signal_estimate`, `seams` and `plan_contradictions`.

Run both with the bounded runner and the cad venv:
`run_bounded_cad.py --max-mib 1800 --report <file> -- /tmp/microduck-cad-venv/bin/python torso_pads.py` (about 50 s,
1.5 GB peak), then the same for `render_pads.py`.

## Method

The inputs are the print-gate solids in the final pose (the `ia_lib` cache), plus the guide cables and screws. Each
shell's inner face is sampled on a 1 mm grid by rays along y. Every 18 x 18 window is then tested against five
conditions:

- most nodes on the wall (at least 97 %);
- no rib or boss inside the window;
- the inner face varies by 3 mm or less;
- the wall is 4 mm thick or less;
- Shawn's limits: at least 4 mm from moving parts and at least 3 mm from metal, boards and servo cases.

Moving parts are the ID12 neck group, swept over its collision-free pitch range clipped to the model range
(-66..90 degrees). The leg parts are swept one full turn about the hip-yaw axis. Distances are measured against point
clouds of the surfaces, with samples about 0.4 mm apart. Wire routes use A* search on 1 mm grids. In the head, the
search reuses `../analysis/head_space.npz`, and the wire stays above the cap rim. In the torso, the wire stays 4.65 mm
from the swept ID12 body. Along the neck, the lead follows the drawn 8-wire bundle.

## Results (measured from the CAD unless marked)

- **Pads.** Left: x -42..-24, z 12..30 (centre -33, 29.0, 21). Right: x -41..-23, z 13..31 (centre -32, -29.6, 22).
  - Both sit on the rear flank, the only flat panel that passes the limits. It runs between the rear curve of the
    shell and a rib at x -24..-19.
  - The wall there is 2.2 mm. Behind the wall is 8 to 13 mm of air on the left and 9.5 to 14 mm on the right.
  - Placement tolerance is small. The left pad has only two passing positions (about ±0.5 mm). The right pad's centre
    may move over x -33..-30 and z 15..22.
- **Nearest parts.** Neither pad is near a moving part, and no other part breaks a limit.

  - Rear pack wall (printed): 3.1 mm left, 2.8 mm right.
  - Nearest rear-box XL4015 screw (M2 × 6): 3.5 mm left, 4.6 mm right.
  - XL4015 top board: 5.6 mm left, 6.6 mm right.
  - Hip-yaw servo case (ID10 left, ID5 right): 5.9 mm left, 4.9 mm right.
  - OpenRB-150 and BNO085: more than 14 mm on both sides.
  - Swept ID12 group (moving): 16 mm left, 17 mm right.
  - Nearest cable: pi-lead 7.8 mm (left), 15 V link 8.3 mm (right).

  The left pad is also 10.4 mm from the DXL link N. The middle of the flank fails: it is 1.2 mm from the ID10 case
  (left) and 1.7 mm from the ID5 case (right).
- **Wire length.** Each lead is about 325 mm in total, so cut 340 mm.

  - XIAO to the cap plug: 82 mm (left, D9), 83 mm (right, D10).
  - In the bundle, cap plug to torso top: 206 mm (left), 199 mm (right).
  - Torso top to pad: 37 mm (left), 42 mm (right).

  The right torso route only fits with 1.25 mm of grid clearance.
- **Seams.** The lead needs two plugs and none in the neck.
  - Torso top: one 2-pin plug for both pad leads, beside the bundle at the pack notch. Each shell then comes off with
    its own 37 to 42 mm lead. The space there fits a ZH 2-pin pair with 5.4 mm to spare, an XH pair with 2.3 mm and a
    mated DuPont 1x2 with 1.4 mm. All three stay at least 6.2 mm from the swept ID12 group.
  - Head cap: one 2-pin plug in the bundle stretch behind the A7Z. It is unplugged together with the eight header
    plugs. The space there fits a DuPont 1x2 with 2.9 mm to spare, a ZH pair with 2.7 mm and an XH pair with 0.6 mm.
  - Neck: no plug. The two wires ride in the bundle through the three clips. Inference: ten 1.3 mm wires need at least
    4.4 mm in the 4.8 mm channel.
  - The connector envelopes are typical sizes, not measured parts. JST ZH has no official wire-to-wire housing.
- **Signal** (inference, analytic):
  - The lead's parasitic capacitance is about 24 pF (range 15 to 35), mostly from 206 mm running alongside the bundle
    wires. A head pad's lead is about 3 to 5 pF.
  - A fingertip through the 2.2 mm wall adds about 1.2 pF, and a palm over the whole pad about 3.9 pF. That is a 5 % or
    16 % change, against about 39 % for a head pad.
  - The lead runs 206 mm alongside the UART and I2C wires, and Espressif advises against running touch traces parallel
    to digital lines. It passes 1.3 mm from the ID13 case and 1.2 mm from the head-yaw link between the bracket clip
    and the head clip.
  - Head yaw, pitch and roll and neck pitch move the bundle. 20 mm of lead moving from 2 to 5 mm off a servo case
    changes it by about 0.13 pF, about a tenth of a fingertip.
- **Torso reader option** (XIAO SAMD21):
  - Leads would be about 40 mm, about 3 pF, so about 40 % change and no neck motion in the lead.
  - No 21 x 18 x 5 mm space exists in the torso (measured). The largest 5 mm-thick free boxes are 14 x 23 mm in each
    flank pocket, 12 x 23 mm between the hip motors and 24 x 11 mm lying flat.
  - The BNO085's lower STEMMA QT socket is 3.5 mm above the base plate, too little for a plug (inference: a JST SH plug
    and its wire bend need about 7 mm).
  - The one free bus is the unused -Y DXL port of the OpenRB-150. `openrb_dual_host` forwards every DYNAMIXEL packet,
    so a Protocol 2.0 device needs no OpenRB flash. It does need a regulator from the 7.0 to 8.4 V rail and a check of
    the DXL data level against the SAMD21's 3.3 V pins.

## Open items

- Placement assumes the rear converter box. With the battery backpack the XL4015 screws are absent, and the nearest
  backpack part is its frame at 5.8 mm on the left and 6.3 mm on the right (printed).
- Bench checks the CAD cannot answer: the real lead capacitance, noise from the UART and I2C lines during walking, and
  whether the tape on hand has conductive adhesive (if not, solder the strip overlaps).
