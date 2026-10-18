# V1.8 rear electronics pack

Frame: robot frame in mm, x forward, y left, z up. Built with `/tmp/microduck-cad-venv/bin/python build_rear_pack.py`
under the bounded CAD runner; the checks below each write their JSON next to this file. Release geometry:
`../world/rear_pack.stl` and `../world/rear_pack_cover.stl` (checksums in `../world/v18-sources.json`), print poses in
`print-poses.json`.

## What it is

One orange print and one black cover that replace the integrated power support, the open regulator insert, the OpenRB
tray, the fuse bank and the IMU clamp and rear cover. The pack hangs on the four existing hip-yaw case screws
(S10-case-069/072, S05-case-074/076): its four tabs are the power support's tabs (check 2, XOR volume 0).

- Plate x -21..-19 between the hip-yaw motors and the box, |y| <= 21.3, z -40..32, with a T-shaped head (|y| <= 27.2,
  z 32..38.8) and a 12 x 6.1 mm cable notch in its top edge (y ±6, down to z 32.7). Every lead that leaves the pack
  crosses the plate through this notch into the open neck region.
- OpenRB-150 standing upright on four dia 5 pads (x -24.8..-21) with dia 1.6 pilots to x -19.6, components facing the
  rear, terminal block up, USB-C down over a floor slot (bench access only), the two centre DXL ports facing the rear low
  on the board, the +Y side port through a wall window. Four M2 x 6 from the component side (B-openrb-01..04).
- DFR1202 channel behind the board (x -45..-37), pads down: two feet at the bottom, two lips on the side walls at the
  front edge, the cover lip over its top edge. No screws.
- BNO085 on the plate front between the hip motors: shelf x -19..-14.3, y ±4.6, z 4.3..5.5 with two tie slots, two fins
  taking the board's rear edge between them.
- Side walls y ±(13.6..15.3), floor z -44..-42.8 with the USB-C opening (x -31.4..-23.9, y -7.3..6.7) and the tether
  opening (x -44.5..-39.5, y ±3); +Y wall window x -31.9..-25.2, z -29..-16.5 for the neck DXL plug. Two cover posts at the back corners with dia 1.6 x 4.8 pilots at (±16.1, 26.0) and (±16.1, -36.5).
- Cover: 2 mm plate x -47..-45, four dia 2.2 holes, lip x -45..-37.5 at z 27.3..28.5. Four M2 x 6 (C-pack_cover-01..04).

Full feature list with coordinates: `features.json`. Build summary: `build.json`.

## Checks (checks.json)

1. Fit against the torso, motors, yaw links and shells in the rest pose: pass.
2. Interface tabs identical to the power support: pass (XOR 0 mm3).
3. Electronics envelopes inside the pack without overlap: pass.
4. Cable rooms (plugs, terminal block, USB-C, tether, neck window): pass.
5. Walking sweep (`pack_sweep2.py`, all 304 253 recorded phase-1 frames, 283 500 adopted): adopted frames keep the
   left shin 3.73 mm and the right shin 5.02 mm from the pack body, hip bodies 4.94 / 4.09 mm; cover and neck plug
   room never closer than 10 mm. Run on the geometry before the two subtractive edits below; both edits remove
   material only, so the clearances can only have grown.
6. Assembly paths (`check_assembly.py`): pack in from the rear (+x 30), cover from the rear (+x 15, shells on or off),
   DFR from above (35), IMU from above (30): pass. The OpenRB cannot slide straight in
   (components meet the pads); it drops in 30 mm at x -3 and moves +3 onto the pads: pass.
7. Printability (`check_print.py`): overhangs and the two print poses: pass.

Screwdriver sweep (dia 6 x 60 shaft): the two lower OpenRB screws clear (component limit radius 6.18 mm); the two
upper ones foul the power-jumper block at dia 6 (limit radius 3.04 mm) and clear at dia 5, 4.5 and 4, so the guide
names a #0 Phillips with a shaft of 5 mm or less for them. Cover screws clear (shell gap 1.13 / 1.56 mm).

## Edits after the sweep (2026-10-12)

- Star junction J and its pocket removed: the servos take power through the OpenRB ports. The +Y wall window is back to
  z -29..-16.5 (neck plug room only), the geometry the walking sweep ran on; removing the pocket only takes material
  away, so the sweep clearances still bound this body.
- Cover post pilots deepened from 4.0 to 4.8 mm, leaving 0.8 mm past the tip of an M2 x 6 through the 2 mm cover.

Checks 1, 2, 3, 4, 6 and 7 pass on the current body. `pack_lib.openrb_mesh()` and `imu_mesh()` read the placed boards
from `../world/` (the audit's solid cache already serves them placed), and the environment in checks 4 and 6 excludes
the pack's own parts (`pack_lib.SELF_KEYS`).

## Cable layout inside the pack (guide `routes.json`, 2026-10-12)

- Leg links R and L leave the two centre ports towards the back, loop into the open −Y bay under the converter space
  (their spare length lies there, beside the tether slot), come back under the lane entrance and climb the
  lane between the board's component side and the converter at y 5..7. Risers from the converter forward: L x -34.6,
  R -32.2, ORB pair -30.2, Pi lead -29.4, UART -28.4; measured bare-point clearance to the board at least 0.8 mm. Below
  the lane only y 2..7.5 is free at z -16..-4 (a component sits at y >= 8), so the ORB pair and the Pi lead drop from the
  DFR pads into the lower +Y corner of the channel and enter the lane from below at y 5..7.
- The notch in the plate top carries two rows: upper z 37 (from −Y to +Y: R, UART pair, Pi lead, L) and lower z 34.3
  (neck link N). N comes over the +Y wall top at z 30..31 and crosses inboard behind the plate.
- The 20 V pair runs down the −Y side of the channel at y -9.5 to the tether slot. N leaves through the window and
  climbs the outside of the +Y wall at x -28.
- Checked by `../../content/interference-audit/cables.py` (zero mid-route penetration on the drawn spline and the raw
  polyline) and, before the audit, by the session's cable-to-cable screen (no two cables closer than the sum of their
  radii outside shared ends and bundles).

## Known limits

- `pack_lib.py` FIT still points at the scratch torso-fit directory used during the design; rerunning the fit checks
  needs that directory or a repointed FIT.
- The DFR1202 pad order along its 26 mm edge is not verified from the product page; the guide tells the builder to
  read the labels on the board. The pad room inside the pack covers either order.
