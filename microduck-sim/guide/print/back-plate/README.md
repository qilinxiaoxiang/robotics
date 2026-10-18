# Rear converter box, layout C revision 2 (2026-10-14)

**Superseded (2026-10-14):** release V1.10 (this layout) is replaced by V1.11, layout F (`layout-F/README.md`,
`../release-V1.11/`). Do not print or fit the V1.10 frame or lid; the files here stay as the record.

Frame: guide world, mm, x forward, y left, z up (trunk_base). The box replaces the rear pack cover and carries two XL4015
step-down boards and one Adafruit 5991 USB-C PD trigger. It has two printed parts: the frame (cover plate, box walls and
bosses) and a flat lid. It is flush with the shells (|y| 32.05), sits behind the pack (x -67.1..-45) and rises 4.5 mm
above the shell top (box top z 46.5, shell top z 42.0). Both OUT pairs stay inside the box and enter the pack channel
through a 7 x 4 passage in the front plate. Checks 1, 2, 3, 5 and 6 pass; check 7 is information for printing.

Renders: `renders/layout-C.png` (all three), `renders/layout-C-rear.png` (rear three-quarter, lid on, box top against
the shell top), `renders/layout-C-side-minus-y.png` (USB-C plug), `renders/layout-C-iso-lid-off.png` (boards and the
OUT pairs in the centre lane).

## Geometry

- **Frame** `rear_frame-world.stl`: cover plate x -47..-45 with the exact cover outline, four holes and lip (from
  `rear-pack/build_rear_pack.build_cover()`). The cover has no top notch; its top edge stays flat at z 29.5 with r1.5
  corners. Lower web x -47..-45, |y| <= 32.05, z -44..-2 joins the wall ring to the plate. Side walls |y| 30.85..32.05,
  top wall z 45.3..46.5 with no openings, bottom wall z -44..-42.8, back opening at x -65.9, inner depth 18.9.
  Volume 15652.63 mm3, one body, watertight, genus 9.
- **Lid** `rear_lid-world.stl`: 1.2 mm, x -67.1..-65.9, |y| <= 32.05, z -44..46.5, two dia 2.2 holes. Volume 6952.16 mm3.
- **XL4015 boards** `xl4015_left-world.stl` (y +17.2, 7 V) and `xl4015_right-world.stl` (y -17.2, 5 V): vertical,
  component side toward -x, PCB mid-plane x -51.03, pin face x -50.205, centre z 10.45, top edge z 41.3. IN at the
  bottom, OUT at the top.
- **5991** `pd5991-world.stl`: flat at the bottom, PCB normal along x, component side toward -x, back face x -50.0,
  27.8 edge along y centred on y 0, bottom edge 0.5 above the floor. USB-C points -y; the screw terminal faces +y.
- **Wire passage**: rounded rectangle 7 (y) x 4 (z), r 1, through the cover plate at y -3.5..3.5, z 23..27, centre
  (-46.0, 0, 25.0). Its top is the channel top z 27.0 from `pack_lib.DFR_BOX`, 0.3 under the lip (z 27.3).
- **Bosses**: eight dia 4.5 XL bosses (seat x -50.205, dia 1.6 pilots to x -45.3, 4.35 mm M2 engagement). The upper
  four (z 38.7) have 3 mm ribs at x -50.205..-47 up to the top wall, and the two at |y| 27.7 also to the side wall.
  Four dia 4.5 5991 bosses x -50..-47. Two dia 5 lid bosses x -65.9..-60.3 with pilots 5.2 deep.
- **Lid boss placement**: the top boss at (y 0, z 43.0) sits in the 8.2 mm lane between the boards, the only part of
  the top wall that is not over a board, and stays behind the OUT wire run (x -60.3 against -54.7). The bottom boss at
  (y 22, z -40.3) is in the +y corner, outside the 5991 insertion path and below its terminal wire exit.
- **USB-C opening**: -y wall x -57.5..-49.0, z -39.14..-25.14 (13 x 7.5 overmold plus 0.5 all round). No windows or vents.
- Every feature and wiring rule with its purpose: `features.json`. Parameters and coordinates: `build.json`.

## Wiring

- **OUT pairs**: each pair leaves its terminal upward (entries z 40.6, terminal end z 41.21). It bends over in the
  4.0 mm room under the top wall (z 41.3..45.3) at x about -54.7, runs inward to y 0, goes down the centre lane
  (|y| <= 4.1) to z 25, then forward through the passage into the pack channel (x -45..-37). From there 7 V (left
  board) goes to OpenRB J4 (-30, -6, 26) and 5 V (right board) to the pack front-plate notch (x -21..-19, y +-6,
  z 32.7..38.8).
- **OUT path lengths**: from each pair's entry centre (-54.705, +-17.2, 40.6) to the passage pack face (-45, 0, 25)
  along up, inward, down and forward: 47.9 mm for each board. Straight line from entry centre to passage centre: 24.8.
  Passage pack face to J4: 16.2. Passage to the notch bottom centre (-20, 0, 32.7): 26.2; to the notch centre
  (-20, 0, 35.75): 27.2.
- **IN pairs**: at each IN terminal (entries face down at z -19.7) the wire bends outward, toward its own side wall,
  within the first 2 mm. It then runs down the 5.7 mm lane behind the 5991 (x -65.9..-60.2) to the 5991 terminal. The
  15 V daisy chain between the two IN terminals runs along the floor lane behind the 5991 (x -65.9..-60.2,
  z -42.8..-37.7).
- **5991 terminal entry face**: plane y 13.70 facing +y, x -60.1..-51.6, z -35.74..-28.74. Entry centres
  (-54.1, 13.7, -30.39) and (-54.1, 13.7, -33.89).

## World coordinates

- Cover screws (frame to pack): (-47, +-16.1, 26.0) and (-47, +-16.1, -36.5).
- XL4015 screws: left (-51.03, 6.7 / 27.7, -17.8 / 38.7); right (-51.03, -27.7 / -6.7, -17.8 / 38.7).
- 5991 screws: (-50, -11.366, -24.393), (-50, -11.366, -39.633), (-50, 11.366, -24.52), (-50, 11.366, -39.76).
- Lid screws: (-67.1, 0, 43.0), (-67.1, 22, -40.3).
- XL4015 IN entries (-54.705, +-14.7 / +-19.7, -19.7). OUT entries (-54.705, +-14.7 / +-19.7, 40.6).
- XL4015 trimmer screw tops: left (-63.36, 5.63, 20.89 / 10.39); right (-63.36, -28.77, 20.89 / 10.39). They sit 2.54
  below the lid inner face, so set them with the lid off.
- 5991 USB-C socket centre about (-53.25, -15.05, -32.14).

## Checks (`checks.json`, `check_rear_plate.py`; `summary` holds the pass flags)

- **1 Manifold: pass.** Frame and lid are watertight, one body each; frame-lid overlap 0.
- **2 Fit at rest: pass, no overlaps.**
  - Frame to shells 1.40 (left) / 1.449 (right).
  - Frame to the V1.8 pack 0: the cover seats on it by design.
  - Box part (x <= -47) to the V1.8 and V1.9 packs 2.0. The lower web outside the cover outline sits 0.01 from both
    packs, in the same plane as the x -45 seat.
  - OpenRB 4.931, legs 5.313 / 5.314, hip rings 6.926 / 6.926. Lid at least 8 from everything.
- **2b Raised top at HOME** (frame and lid above z 43, every part reaching above z 30): shells 7.414 (right) / 7.502
  (left), head_bottom 56.82, nearest neck part (motor12) 63.0. The shells' rearmost point is x -46.13 (y 0, z 32.1),
  0.87 in front of the box front plane x -47; no shell vertex lies above z 43 within |y| <= 32.05.
- **3 Boards in the box: pass.**
  - XL4015 to side wall 0.55, top wall 4.0, lid 0.52, plate/web 0.52.
  - XL to XL 8.2; XL to 5991 1.58.
  - 5991 to floor 0.5, lid 5.8, plate 3.0.
  - No PCB vertices inside the frame.
- **4 Wire room.**
  - **OUT, top room**: terminal end face to the top-wall inner face 4.09; board top 4.0.
  - **OUT, wire bodies** (each pair 1.6 x 3.2; single conductors dia 1.6 at the terminal; the two pairs stacked
    3.2 x 3.2 through the passage):
    - Overlap with the frame, boards, 5991 and lid: 0.
    - The run over the boards clears the boards by 1.2 and the top wall by 1.2.
    - The lane descent clears the boards by 2.5 and the frame by 1.2.
    - Through the passage: 0.4 to the frame top and bottom, 1.9 at the sides.
    - In the channel (x -45..-37): V1.8 pack overlap 0 (gap 5.0), V1.9 pack overlap 0, OpenRB 2.277, cover lip 0.4.
  - **IN zones (accepted)**: projected (y-z) overlap with the 5991 PCB is z 3.42 and y 1.706 (left) / 1.876 (right).
    In 3D the overlap is 0 mm3 with a 0.205 gap. The routing rule above keeps the wires off the 5991 edge.
  - 5991 terminal exit room: 17.14 to the +y wall. Lane behind the 5991: 5.7 deep, clear.
  - **USB-C plug envelope** (13 x 7.5, from the socket face to 20 mm beyond the wall, y -52.05): frame 0.5, boards
    5.24. Environment: right thigh 4.7, right plate 6.547, right lower 7.753, ring2 6.744, motor2 7.723. HOME only.
- **5 Dia 5 driver lanes: pass.**
  - Cover screws with the frame alone: clear; frame gaps 1.3 / 1.007 / 1.3 / 0.937.
  - XL4015 screws: no other part in the lane; own components at least 3.452 from the axis; frame at least 0.6.
  - 5991 screws: own components at least 3.023.
  - Lid screws, including the raised top one: clear.
- **6 Assembly order frame, 5991, boards, lid: pass.**
  - Frame sliding on +x 30: min gap 1.4 (shells) with the V1.9 pack, 0.4 with the V1.8 pack.
  - 5991 +x 25: 0.5. Each XL4015 +x 25: 0.5. Lid +x 15: 0.5.
  - The upper cover screws (+-16.1, 26.0) sit behind the boards, so the frame goes on empty.
- **7 Printability.**
  - **Print pose**: frame `rear_frame-print.stl` with the bottom wall on the bed; height 90.5, bed contact
    1339.7 mm2, overhang 1613.41 mm2.
  - **Top wall**: the underside is a 61.7 x 18.9 bridge (1099.67 mm2). It needs slicer supports, which stand inside
    the box and come out through the open back.
  - **Lip**: the underside (198.0 mm2, 7.5 mm cantilever, x -45..-37.5) needs supports. They stand on the bed in front
    of the plate, outside the box, and come off from the front.
  - **Bosses**: the boss undersides are about 18 to 22 mm2 each.
  - The lip is kept.
  - **Other frame poses (information only)**: plate down with the lip, bed contact 31.7 and overhang 4164.52; plate
    down without the lip, overhang 311.72.
  - **Lid**: `rear_lid-print.stl`, outer face on the bed, no overhang.

## Mass (`mass_estimate.json`, estimate, no simulation)

- **Printed parts**: frame 16.52 g, lid 7.34 g (23.9 g in total).
- **Boards and screws**: XL4015 2 x 20 g (estimate), 5991 3.5 g, 14 new M2 x 6 2.38 g.
- **Removed**: V1.8 cover, -6.30 g.
- **Result**: net +63.4 g, from 792.6 to 856.0 g. Whole-robot COM shift (-4.27, 0.02, -1.29) mm; new COM
  (-3.70, -0.20, 20.57) in the trunk frame at HOME. Wires are not included.

## Screws

The box uses 18 x M2 x 6: 4 cover screws reused from the V1.8 cover, 8 XL4015, 4 5991 and 2 lid. 14 of them are new,
and the mass estimate counts those 14.

## Open items

- No walking-pose sweep of the legs against the box and the USB-C plug has been run; only HOME was checked.
- **XL4015 IN/OUT ends**: the ROBOTIS mesh has no silkscreen, so the ends cannot be read from it. The build assumes IN
  is at local +Y, so read the board label before mounting. The holes are symmetric, so a board with IN at the other
  end still mounts rotated 180 degrees about x, but its trimmers move to the other half of the board.
- **XL4015 mass**: 20 g each is an estimate; weigh the boards.
- **Channel**: the passage opens into the empty channel volume (`pack_lib.DFR_BOX`). If a DFR1202 is still fitted
  there, it blocks the passage.

## Files

- **Build**: `build_rear_plate.py` writes `rear_frame-world.stl`, `rear_lid-world.stl`, `rear_frame-print.stl`,
  `rear_lid-print.stl`, `xl4015_left-world.stl`, `xl4015_right-world.stl`, `pd5991-world.stl`,
  `render/xl4015_left.stl` and `render/xl4015_right.stl` (decimated for rendering), `build.json` and `features.json`.
- **Checks**: `check_rear_plate.py` writes `checks.json`.
- **Mass**: `mass_estimate.py` writes `mass_estimate.json`.
- **Renders**: `render_views.py` writes `renders/`. Run it with `~/.venvs/microduck-dyn/bin/python` under the runner
  with `--max-mib 2560`.
- **Earlier phases**: `contract_feasibility.json`, `check_contract.py`, `place_components.py`, `board_facts.json`,
  `probe_env.py/json`, `xl4015_lower-world.stl` and `xl4015_upper-world.stl` belong to the infeasible one-piece
  contract. `options-20261014/` holds layouts A and B, which were stopped.
- **Runner**: all CAD jobs and checks run through `run_bounded_cad.py --max-mib 1536 --seconds 600` with
  `/tmp/microduck-cad-venv`.
