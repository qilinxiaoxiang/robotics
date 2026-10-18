# Rear converter box, layout F (2026-10-15: V1.16 release source with four hidden cap screws, no front passage, wire notches)

Current state: the cap pushes straight on and is held by four hidden M2 x 10, each driven from a hole in the cap back:
two through the 7 V XL4015's top corner holes into the z 38.7 frame bosses and two through the 5991's upper holes into
its standoff bosses (Shawn, 2026-10-15: screws instead of tongues and a hook). The cap ears, their frame bosses, front
passage P1, the top tongues, the tooth slots and the window hook are gone. The
released V1.14 sources are snapshotted in `../layout-F-V1.14-snapshot/`; the option study is `../layout-F-ear-20261014/`.
Every wire now runs outside the box (`wires_real_F()` in `build_f.py`): the 7 V and 5 V pairs cross the box top and
drop into the pack through two small notches in the frame (notch A in the top-wall front edge, notch B in the cover-plate
top edge, real y 3.2..12.4), hidden in the crevice between the box front and the shell rear edge. The shells are
unchanged. All `checks.json` flags pass. Design folder: `../layout-F-outside-wires-20261014/`.

Frame: guide world, mm, x forward, y left, z up (trunk_base). Layout F replaces layout C revision 2 (V1.10, `../README.md`).
The box replaces the printed V1.8 rear pack cover and carries two ROBOTIS XL4015 step-down boards and one Adafruit 5991
USB-C PD trigger in three horizontal tiers. Two printed parts: the frame and a rounded cap. Outer envelope |y| <= 32.05,
z -36.02..43, x -67.1..-37.5. The printed V1.8 pack stays as built; its tether hole stays open and unused.
Source: `build_f.py` (`python build_f.py F` in the CAD venv under the bounded runner, about 35 s); `post_build.py` (CAD
venv, about 8 s: world and print STLs, solids, print contact, outline, board and cap fitting paths, wire centreline
penetration; writes `post_build.json` and `insertion_check.json`); `hip_sweep.py` (dyn venv); `mass_estimate.py`;
`write_records.py` writes `build.json`, `features.json` and `checks.json`.
Render: `renders/layout-F-final.png`.

## Handedness

The XL4015 IN terminal is at board-local -Y: the kit photo (`bringup/parts/photos/xl4015_robotis_kit_top.jpg`, component
side, trimmers at the bottom) shows OUT+ on the left and IN+ on the right with the regulator IC right of centre; the mesh
puts the regulator IC at local Y -10.94..-0.76 and the inductor at +1.74..+8.95. With local Y mapped to world +y, the IN
ends face world -y. Release geometry: IN windows in the -y wall, OUT windows in the +y wall, the 5991 turned so its
terminal faces -y and its USB-C +y. `build_f.py` computes in a design frame (the y-mirror, IN at +y) and writes
every output in the world frame. Polarity: + is the lower screw on the XL4015 IN terminals and on the 5991 terminal.

## Frame and cap

- **Frame** `rear_frame-world.stl`: cover plate x -47..-45 with the exact cover outline, four cover holes and lip (from
  `rear-pack/build_rear_pack.build_cover()`); wide tier |y| <= 32.05, z -15.2..43 and narrow tier |y| <= 15.61,
  z -36.02..-15.2, wall 1.2, closed bottom. The rim is square at x -59.1 and the cross-section is constant from
  the rim to the front plate, so every board slides straight in from the rear with the cap off. The front plate is
  solid (no wire passage). No hook notch and no tooth slots. Wire notches (real y 3.2..12.4, 9.2 wide): A cuts the top-wall front edge back from x -47.0
  to x -49.8 through the 1.2 wall (rear corners r 1); B cuts the cover-plate top edge from z 29.5 down to z 28.5 over
  x -47..-45 (floor corners r 0.5), flush with the cover lip, which is untouched. Volume 10292.8 mm3, one watertight body.
- **Cap** `rear_lid-world.stl`: x -67.1..-59.1, 1.2 mm walls; it carries every rear-edge rounding (radii pinned to
  the V1.11 values: no wire inside the box limits them any more, a cap change is Shawn's decision) and the four screw
  columns with their driver holes (Cap retention). Volume 6404.0 mm3, one watertight body.
- **Radii** (outer; inner = outer - 1.2) and what limits each:
  - W top corners (y-z): 1.8 (top_7V:board end at the side wall at [-51.8, -30.85, 41.3])
  - W step corners (y-z, convex): 1.8 (mid_5V:board end at the side wall at [-51.8, -30.85, -13.5])
  - N bottom corners (y-z): 2.1 (pd5991:pcb at [-51.6, -13.91, -34.32])
  - step concave blend (y-z): 3.0 (cap 3.0)
  - rear vertical edges, full width: 7.4 (wire 15V_link_p at [-64.6, 24.66, 5.51])
  - rear top edge: 7.8 (top_7V:body (cap slide, 1.2 low) at [-62.3, -16.73, 40.71])
  - rear step edge (underside of the step): 4.3 (wire 15V_feed_q at [-64.6, 9.2, -12.5])
  - rear vertical edges, 5991 tier: 4.5 (wire 15V_feed_q at [-64.6, 9.2, -12.5])
  - rear bottom edge, 5991 tier: 8.0 (cap 8.0)
- **Boards**: XL4015 #1 (7 V, world key `xl4015_left`) centre z 28.2 and #2 (5 V, `xl4015_right`) centre z -0.4,
  horizontal, long axis y, component side to -x, seat x -50.205 on eight dia 4.5 bosses (holes y +-28.25, z 17.7 / 38.7
  and -10.9 / 10.1). Boss length from the seat: 5.0 at z 38.7 and -10.9, 4.2 at z 10.1 (stub to x -46.0) and 3.2 at
  z 17.7, where the torso shells stand 1.29 / 1.17 mm ahead of the front wall and any stub would close that gap. The 5991 sits in the narrow tier on four bosses with a 3.0 mm standoff (seat x -50.0, holes
  y +-11.37, z -31.9 / -16.6). Two M2 x 6 hold its lower corners; both upper holes (y +11.37, z -16.67 beside the USB-C
  socket and y -11.37, z -16.54 beside the terminal) take cap screws. The 7 V board's two upper holes (z 38.7) take
  cap screws as well; with the cap off that board hangs on its two lower M2 x 4.
- **Windows**: XL terminals x -65.9..-53.205 (through cap and frame), z 23.0..33.4 (top) and -5.6..4.8 (middle), IN in the
  -y wall, OUT in the +y wall. 5991 terminal x [-65.9, -53.1], z [-28.06, -20.06], -y wall. USB-C slot x
  [-65.9, -49.0], z [-31.16, -17.16], +y wall, open to the frame rim and closed by the cap.
- **Front plate**: solid. P1 (x -47..-45, y 2.9..12.7, z 12.5..15.3) was deleted on 2026-10-14; notch B (above) is the
  only cut in its top edge.
- **Lower cover screws**: dia 4.4 head and driver lanes along x at (|y| 16.1, z -36.5) through the narrow tier corners.

## Cap retention

Four hidden M2 x 10 (Shawn chose screws on 2026-10-14 and replaced the tongues and hook with screws on 2026-10-15).
Each runs in a dia 5.6 column from the cap back, is driven through a dia 4.4 hole in the cap back and seats its head
on a 3.0 mm column floor with a dia 2.3 clearance hole, so nothing shows from outside. The floors were 1.0 mm in V1.16/V1.17; the two low
ones tore through on the printed V1.17 cap when it was taken off (Shawn, 2026-10-15, IMG_7004). V1.19 grows each floor 2.0 mm
forward, so the seats, the M2 x 10 and the thread engagement are unchanged.

- Low pair, on the 5991 upper hole axes (y +11.367, z -16.667) and (y -11.366, z -16.54): columns to x -53.1, 1.5 mm
  behind the 5991 PCB; the +y column passes beside the USB-C socket and its underside is flattened to 0.5 mm above the
  socket top (z -19.19); seat x -56.1; the screw crosses a 1.5 mm gap and the 5991 PCB (1.6 mm) and engages 3.9 mm
  in the standoff boss pilot (tip x -46.1, pilot to x -45.3). Tightening also clamps those 5991 corners.
- Top pair, on the 7 V XL4015 top corner hole axes (y +-28.25, z 38.7): columns to x -52.6 (1.25 mm gap to the board), flattened in front of the
  rim to |y| <= 30.6 and z <= 41.55 so they slide inside the frame; seat x -55.6; the screw crosses the gap, passes the
  board's 2.5 mm hole (the board is not clamped by it) and engages 4.6 mm in the dia 5.0 frame boss (tip x -45.6).
- The gaps mean the cap always seats on the rim before the screws pull.
- Ray cast (`raycast_cap_screws.py`, `raycast_cap_screws.json`): thread ring material 3.9 / 3.9 / 4.6 / 4.6 mm in the
  frame, head envelope and driver lane clear of every part.
- Nothing sits outside the box outline (`post_build.json` outline check: 0 vertices).
- Fitting: push the cap straight forward until it meets the rim, then drive the four M2 x 10. Removal: unscrew, pull it
  straight back. Guide approach path [[-15.0, 0.0, 0.0], [0.0, 0.0, 0.0]].

## Wiring (22 AWG, `wires_F.json`, routes in `build_f.wires_real_F()`)

Every wire leaves its terminal straight out through its side window and stays outside the box (Shawn, 2026-10-14; no
U-loops, no rear lane, no front passage). Terminal entries are the V1.11 ones; + is the lower screw everywhere.

- 15 V link (-y): mid IN -> top IN outside the -y wall; `15V_link_p` at |y| 34.5 forward to x -48.5 and up,
  `15V_link_q` at |y| 36.2 straight up at x -54.7, so the pair never crosses.
- 15 V feed (-y): mid IN -> 5991 terminal; `15V_feed_q` down the outside at |y| 36.2 to z -17.6, in under the step
  and 45 degrees into the terminal window; `15V_feed_p` at |y| 34.5 back to x -60.9, down to z -20 and in.
- 7 V and 5 V (+y): up the outside of the +y wall at |y| 34.5 in four x columns (7V_a -63.3, 7V_b -60.9, 5V_a -51.4,
  5V_b -47.8), over the top edge, across the box top at z 45 in lanes y 4.4 / 6.5 / 8.6 / 10.7 (the column nearest
  the box front turns inward last, so nothing crosses), down through notch A into the box front cavity at x -47.8
  (0.95 in front of the top board's pins), forward under the shell lip through notch B at z 30 onto the cover lip.
  7 V: along the cover lip, down to OpenRB J4 (-31.5, +-1.25, 25.4) as the guide's pw-7v. 5 V: along the cover lip
  under the shell roof rib (bottom z 31.5..32), up in front of it over the 7 V to the head-notch slots (y 1.9 z 35.3
  and y 1.5 z 37.6), out through the pack plate's head notch and up to the pi-lead bundle point (-6, -14, 43.5).
- Routing order: the 7 V and 5 V pairs can only be laid over the box top and into the notches once both shells and the
  box are on; the 7 V free ends reach J4 from the pack side, the 5 V ends join the neck bundle.

Lengths (centreline, terminal to terminal / J4 / bundle point) and gaps (mm; 15V_feed_q 0.453 is the 5991 terminal mouth):

- `15V_link_p` (p): 43.5 mm, gaps frame 0.495, cap 4.32, boards 0.464 mm
- `15V_link_q` (q): 37.1 mm, gaps frame 1.003, cap 3.977, boards 1.571 mm
- `15V_feed_q` (q): 46.9 mm, gaps frame 0.6, cap 2.044, boards 0.453 mm
- `15V_feed_p` (p): 50.0 mm, gaps frame 0.6, cap 1.592, boards 0.476 mm
- `7V_a` (7V): 104.0 mm, gaps frame 0.3, cap 1.1, boards 0.456 mm
- `7V_b` (7V): 96.6 mm, gaps frame 0.6, cap 1.1, boards 0.47 mm
- `5V_a` (5V): 144.3 mm, gaps frame 0.549, cap 3.0, boards 0.471 mm
- `5V_b` (5V): 152.3 mm, gaps frame 0.451, cap 4.32, boards 0.457 mm

Cut lengths by the guide rule (longer wire of the pair + 15 per screw-terminal end, up to 5; pi lead + 15 at the
converter + 291.5 beyond the bundle point + 45 slack): 15 V feed 80, 15 V link 75, 7 V pair 135, Pi lead 505.
Wire to wire: 7V_a|7V_b 0.055, 7V_b|5V_a 0.228, 5V_a|5V_b 0.299, the 15 V pairs 0.8 or more (rule: no overlap).
Shells: the four +y wires keep 0.56..0.57 mm (over the roof rib and under the lip); pack 1.75 (5V_a); OpenRB 4.3 or more
outside the J4 clamp. Existing flexible cables (guide routes, modelled tubes): the 5 V wires overlap dxl-l10 by up to
1.7 mm and imu by 1.5 mm in the head notch and neck bundle, 7V_b overlaps dxl-l10 by 1.6 mm at J4; the current pi-lead
overlaps imu 1.7 and uart 1.6 in the same zone, so this is the existing hand-dressed bundle, not a rigid collision.

## Checks (`checks.json`)

- HOME: shells 1.04 / 1.175 mm, OpenRB
  4.931 mm, thighs 10.505 mm; USB-C plug envelope (+y)
  to the thigh 5.376 mm.
- Hip sweep (each hip pitch HOME +-30 deg in 5 deg steps with hip roll +-10 deg; no walk61 joint range is recorded):
  USB-C plug 4.28 mm (left upper leg, sampled true surfaces), frame 6.0 mm (no leg within 6 mm of the frame box) and cap
  17.66 mm (convex-hull lower bounds), wires (every segment as capsules) at least 9.25 mm (5V_b). Nothing under 2 mm.
  Rerun on this build's frame and wires (dyn venv).
- Insertion (`insertion_check.json`): each board along -x 0..25 mm with the cap off overlaps the frame only at its seat
  (top 0.583, mid 0.576, 5991 0 mm3); the straight cap path overlaps the boards and the frame nowhere (0 mm3).
  Cap to boards at rest 0.287 mm.
- Outline: no vertex of the frame or cap behind the front plate lies outside the y-z box outline.
- Wires: every wire at least 0.3 mm from frame, cap and boards (15V_feed_q 0.453 at the 5991 terminal mouth), no
  wire-to-wire overlap, no centreline inside a printed part (`post_build.py`); per-wire pack, OpenRB, shell and
  guide-cable gaps in `layout_f.json` packPerWire / shellPerWire.
- Print gate: `guide/content/interference-audit/gate-receipt.json` (`checks.json` printGate) is the last run on the
  released guide data; it has not been rerun on these parts.

## Print poses

- Frame: rim-down, rim (x -59.1) on the bed, `rear_frame-print.stl`; 252.0 mm2 wall ring contact (the ear boss ends
  are gone; the V1.15 print row asks for at least 250), 21.6 mm tall, tip
  angle 71.5 deg, no brim. Tree support inside under the front plate (12.1 mm up) and under the cover flap; the
  boss tips print on support, so clean them flat before mounting the boards. Upright touches the bed with only the
  60.8 mm2 cover strip under an 87 mm part; the side pose is 64.1 mm tall and supports the lip locating end
  (`release-V1.11/orientation-decision.json`).
- Cap: outer rear face down, open side up, `rear_lid-print.stl`; 2634.0 mm2 contact, 12.5 mm tall; tree support under the
  rounded edges near the bed. The four columns rise from the bed face, and the driver holes are vertical bores.

- Brim: none on either part (manifest processOverrides brim_type no_brim on Bambu and Elegoo). PRINT-ORIENTATION-PRACTICE.md
  R1 adds a brim only below a 10 deg tip angle; the frame stands at 71.5 deg and the cap at 85.4 deg. The plate-wide 4 mm
  outer brim had been carried forward from the V1.9 head cap (7.7 deg), and a brim 0.1 mm off the frame's 1.2 mm wall ring
  is very hard to peel (Shawn, 2026-10-14), so the first V1.11 slice with that brim was withdrawn.

## Screws (stock M2 x 4 / 6 / 8 / 10 only)

M2 x 6: 4 for the 5 V XL4015 (4.35 mm engagement at z -10.9, 4.2 at z 10.1), 2 for the 5991 lower holes (4.4) and the
4 reused V1.8 cover screws into the pack posts. M2 x 4: 2 for the 7 V XL4015 holes at z 17.7 (2.35 mm engagement in the
3.2 mm boss; the tip stays inside the boss). M2 x 10: 4 cap screws (3.9 mm in the 5991 bosses, 4.6 mm in the z 38.7
XL4015 bosses). 16 screws in all.

## Mass (`mass_estimate.json`, estimate)

Printed 17.6 g; net added 57.2 g with boards and screws; whole robot 849.8 g, COM shift
[-3.86, 0.02, -0.82] mm.
