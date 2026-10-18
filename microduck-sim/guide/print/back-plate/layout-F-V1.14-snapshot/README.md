# Rear converter box, layout F (2026-10-14, release V1.11)

Frame: guide world, mm, x forward, y left, z up (trunk_base). Layout F replaces layout C revision 2 (V1.10, `../README.md`).
The box replaces the printed V1.8 rear pack cover and carries two ROBOTIS XL4015 step-down boards and one Adafruit 5991
USB-C PD trigger in three horizontal tiers. Two printed parts: the frame and a rounded cap. Outer envelope |y| <= 32.05,
z -36.02..43, x -67.1..-37.5. The printed V1.8 pack stays as built; its tether hole stays open and unused.
Source: `build_f.py` (`python build_f.py F` in the CAD venv under the bounded runner, about 35 s); `hip_sweep.py` (dyn
venv); `mass_estimate.py`; `write_records.py` writes `build.json`, `features.json` and `checks.json`.
Render: `renders/layout-F-final.png`.

## Handedness

The XL4015 IN terminal is at board-local -Y: the kit photo (`bringup/parts/photos/xl4015_robotis_kit_top.jpg`, component
side, trimmers at the bottom) shows OUT+ on the left and IN+ on the right with the regulator IC right of centre; the mesh
puts the regulator IC at local Y -10.94..-0.76 and the inductor at +1.74..+8.95. With local Y mapped to world +y, the IN
ends face world -y. Release geometry: IN windows in the -y wall, OUT windows in the +y wall, the 5991 turned so its
terminal faces -y and its USB-C +y, P1 at +y. `build_f.py` computes in a design frame (the y-mirror, IN at +y) and writes
every output in the world frame. Polarity: + is the lower screw on the XL4015 IN terminals and on the 5991 terminal.

## Frame and cap

- **Frame** `rear_frame-world.stl`: cover plate x -47..-45 with the exact cover outline, four cover holes and lip (from
  `rear-pack/build_rear_pack.build_cover()`); wide tier |y| <= 32.05, z -15.2..43 and narrow tier |y| <= 15.61,
  z -36.02..-15.2, wall 1.2, closed bottom. The rim is square at x -59.1 and the cross-section is constant from
  the rim to the front plate, so every board slides straight in from the rear with the cap off. Volume
  10502.4 mm3, one body (watertight).
- **Cap** `rear_lid-world.stl`: x -67.1..-59.1, 1.2 mm walls; it carries every rear-edge rounding and its
  recess holds the rear lane wires. Volume 6276.0 mm3, one body (watertight).
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
  y +-11.37, z -31.9 / -16.6).
- **Windows**: XL terminals x -65.9..-53.205 (through cap and frame), z 23.0..33.4 (top) and -5.6..4.8 (middle), IN in the
  -y wall, OUT in the +y wall. 5991 terminal x [-65.9, -53.1], z [-28.06, -20.06], -y wall. USB-C slot x
  [-65.9, -49.0], z [-31.16, -17.16], +y wall, open to the frame rim and closed by the cap.
- **Front passage P1**: x -47..-45, y 2.9..12.7, z 12.5..15.3.
- **Lower cover screws**: dia 4.4 head and driver lanes along x at (|y| 16.1, z -36.5) through the narrow tier corners.

## Cap retention

- Two tongues at the top corners of the cap (|y| 24.0..30.2, z 40.6..41.8, x
  -61.1..-53.6) run flush under the frame top wall; a 1 mm tooth on each (x
  -56.6..-54.6) sits in a slot through the top wall (x -56.8..-54.4).
- Two M2 x 6 through 1.2 mm ears (x -60.3..-59.1) into frame bosses (x -59.1..-53.5), 4.8 mm engagement: at
  (y -23.8, z -17.4) under the step (dia 5.0) and at (y +23.8, z -33.6) beside the narrow tier (dia 4.5, on a web from the
  side wall), because the USB-C plug envelope (x -57..-49.5, y 15.05..40.05, z -30.66..-17.66) fills the space under
  the step on the +y side; that boss top is z -31.35, 0.69 mm under the envelope.
- Fitting: slide the cap forward 1.2 mm low until it meets the rim, lift it 1.2 mm so the teeth enter the top-wall slots, screw the two ears. Guide approach path [[-15.0, 0.0, -1.2], [0.0, 0.0, -1.2], [0.0, 0.0, 0.0]].
- This tongue connection still needs Shawn's confirmation (robotics/AGENTS.md: connection methods are explained and
  confirmed before they shape printed geometry).

## Wiring (22 AWG, `wires_F.json`)

Every terminal wire leaves through its side window, makes one U-loop outside the wall and returns into the rear lane
(x -64.6). 7 V (top OUT) descends at y +21.0 / +18.8 and 5 V (middle OUT) rises at y +12.8 / +10.6, outboard of the
inductor; both run forward in the tier gap (z 13.9) as two ribbons with parallel 45 degree jogs to P1. The 15 V link
joins the two IN terminals. The 15 V feed runs from the middle IN terminal to the 5991 terminal, + to + (both lower
screws), so the pair crosses once: feed_q steps 2.2 mm forward (x -62.4) below the middle board. Box-internal lengths:

- `7V_a` (7V): 61.6 mm, gaps frame 0.56, cap 0.4, boards 0.3 mm
- `7V_b` (7V): 68.8 mm, gaps frame 0.658, cap 0.4, boards 0.3 mm
- `5V_a` (5V): 68.2 mm, gaps frame 0.658, cap 0.398, boards 0.3 mm
- `5V_b` (5V): 75.4 mm, gaps frame 0.658, cap 0.398, boards 0.3 mm
- `15V_link_p` (p): 67.9 mm, gaps frame 0.658, cap 0.393, boards 0.37 mm
- `15V_link_q` (q): 74.3 mm, gaps frame 0.657, cap 0.387, boards 0.356 mm
- `15V_feed_p` (p): 68.9 mm, gaps frame 0.658, cap 0.353, boards 0.376 mm
- `15V_feed_q` (q): 70.7 mm, gaps frame 0.655, cap 0.397, boards 0.35 mm

## Checks (`checks.json`)

- HOME: shells 1.04 / 1.175 mm, OpenRB
  4.931 mm, thighs 10.505 mm; USB-C plug envelope (+y)
  to the thigh 5.376 mm.
- Hip sweep (each hip pitch HOME +-30 deg in 5 deg steps with hip roll +-10 deg; no walk61 joint range is recorded):
  USB-C plug 4.28 mm (left upper leg, sampled true surfaces), frame 13.25 mm and cap
  17.66 mm (convex-hull lower bounds), window loops at least
  13.91 mm. Nothing under 2 mm.
- Insertion (`insertion_check.json`): each board along -x 0..25 mm with the cap off overlaps the frame only at its seat
  (designed contact); the cap path overlaps the boards nowhere and the frame only at the seam.
- Wires: at least 0.35 mm from boards, frame and cap.
- Print gate: `guide/content/interference-audit/gate-receipt.json` (`checks.json` printGate).

## Print poses

- Frame: rim-down, rim (x -59.1) on the bed, `rear_frame-print.stl`; 296.8 mm2 wall ring contact, 21.6 mm tall, tip
  angle 71.5 deg, no brim. Tree support inside under the front plate (12.1 mm up) and under the cover flap; the
  boss tips print on support, so clean them flat before mounting the boards. Upright touches the bed with only the
  60.8 mm2 cover strip under an 87 mm part; the side pose is 64.1 mm tall and supports the lip locating end
  (`release-V1.11/orientation-decision.json`).
- Cap: outer rear face down, tongues up, `rear_lid-print.stl`; 2643.2 mm2 contact, 13.5 mm tall; tree support under the
  rounded edges near the bed and under the ears.

- Brim: none on either part (manifest processOverrides brim_type no_brim on Bambu and Elegoo). PRINT-ORIENTATION-PRACTICE.md
  R1 adds a brim only below a 10 deg tip angle; the frame stands at 71.5 deg and the cap at 85.4 deg. The plate-wide 4 mm
  outer brim had been carried forward from the V1.9 head cap (7.7 deg), and a brim 0.1 mm off the frame's 1.2 mm wall ring
  is very hard to peel (Shawn, 2026-10-14), so the first V1.11 slice with that brim was withdrawn.

## Screws (stock M2 x 4 / 6 / 8 / 10 only)

M2 x 6: 6 for the XL4015s (4.35 mm engagement at z 38.7 and -10.9, 4.2 at z 10.1), 4 for the 5991 (4.4), 2 for the cap
ears (4.8) and the 4 reused V1.8 cover screws into the pack posts. M2 x 4: 2 for the XL4015 holes at z 17.7 (2.35 mm
engagement in the 3.2 mm boss; the tip stays inside the boss). 18 screws in all.

## Mass (`mass_estimate.json`, estimate)

Printed 17.7 g; net added 57.3 g with boards and screws; whole robot 849.9 g, COM shift
[-3.87, 0.02, -0.84] mm.
