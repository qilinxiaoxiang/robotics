# Battery cap study: a 3S LiPo behind the layout-F rear box (2026-10-14)

Study only. Nothing here is released, sliced, gated or deployed; no release, guide, world, layout-F or PROJECT-CONTEXT
file was changed. World = guide frame, mm, x forward, y left, z up, trunk_base origin. The question: what should be
adjusted now so a later wireless (battery) version costs the least effort.

Files: `battery_cap_study.py` (geometry, hip sweep, floor, COM; writes `battery_cap_study.json` and `scene_home.pkl`,
the posed robot for the render, 17 MB, regenerable), `render_study.py` + `render_choice.json` (vtk renders through
`guide/content/render.py`, light background), `renders/tattu650-view_0.png` / `_1.png` and `renders/tattu850-view_0.png`
/ `_1.png` (rear 3/4 from the -y side; -y side view), `runner-*-report.json` (bounded runner receipts).

## Inputs and sources

- Today's power (DECISIONS.md D-007): USB-C PD -> Adafruit 5991 at 15 V -> XL4015 #1 (6.8 V) and #2 (5.0 V) in the
  layout-F box (`../layout-F/README.md`): frame x -59.1..-45 (front plate x -47..-45 on the V1.8 pack), cap x
  -67.1..-59.1 (8 mm deep), outer |y| <= 32.05, z -36.02..43, narrow tier |y| <= 15.61 below z -15.2. Shell rear face
  x -46.4 (`guide/print/world/shell_right.stl` bounds). The XL4015 #2 IN window is in the -y wall, x -65.9..-53.205,
  z -5.6..4.8.
- The empty DFR channel of the V1.9 pack (`../../rear-pack-v19/features.json`): x -45..-36.7, |y| <= 13.6, z -42.8..28.5.
- Packs (retail spec sheets read 2026-10-14; the XL4015 needs >= 8 V in, so 2S is out):
  - Tattu 3S1P 650 mAh 75C XT30: "Dimensions: 58mm (L) x 31mm (W) x 16mm (H)", "Weight: 59g (±20g)"
    (readymaderc.com); grobotronics.com adds ±5 / ±2 / ±2 mm on L / W / H. The brief's 56 x 31 x 18 / 55 g is close
    but not what the sheets say; the study uses the sheet values.
  - Tattu 3S1P 850 mAh 75C XT30: "Dimensions: 60mm (L) x 30mm (W) x 23mm (H)", "Weight: 80g" (readymaderc.com);
    adorama.com gives ±20 g; getfpv.com lists 57 mm long. No dimension tolerance published; assume the 650's.
  - Reference only: Pollen's stock NP-F550 type (2S 7.2 V) is about 70-71 x 38 x 20-23 mm and 88-110 g on third-party
    listings; it is larger than either 3S pack in every axis.
- Mass baseline: `../layout-F/mass_estimate.json` (as-built V1.9 + layout F box, boards, screws): 849.5 g, whole-robot
  COM at HOME [-3.28, -0.20, 21.04]; the official Pollen model has [0.56, -0.01, 21.75]
  (`hardware-design-20260912/whole-robot-20260912/dynamics/v19-20261014/v19-walk-summary.json`).
- COM tolerance (`hardware-design-20260912/whole-robot-20260912/dynamics/realgap-20261014/README.md`, `margins.py`,
  `volt_margins.py`): `com_x_mm` moves 50 g of trunk mass so the whole-robot COM shifts by that amount along +x
  (forward, toward the head). At 5 V: -10 to -2.5 mm walk, +2.5 mm falls. At 7.4 V: +2.5, +5, +7.5 mm walk, +10 falls;
  no backward case was run at 7.4 V. D-007's "7.5 mm" is the forward (+x) tolerance at 7.4 V.

## 1. The DFR channel cannot take either pack

Channel inner size 8.3 (x) x 27.2 (y) x 71.3 (z). Best orientation of each pack (thickness along x, width along y,
length along z) and the clearance per axis:

- Tattu 650 (16 x 31 x 58): x -7.7 mm, y -3.8 mm, z +13.3 mm. Does not fit (two axes short).
- Tattu 850 (23 x 30 x 60): x -14.7 mm, y -2.8 mm, z +11.3 mm. Does not fit.
- NP-F550 reference (20.5 x 38 x 71): x -12.2, y -10.8, z +0.3 mm. Does not fit.

The channel is 8.3 mm deep; the thinnest 3S pack is 16 mm. The channel stays what it is today: the pass-through for
the 7 V / 5 V pairs and nothing else.

## 2. Battery cap: pack behind the box

A replacement cap for the layout-F frame with a printed pocket (1.2 mm walls) that carries the pack behind the cap back
face (x -67.1). The pocket's front wall is the existing cap back wall; the cap keeps its 8 mm recess, tongues and
ears, so the frame, boards and wiring do not change. All numbers are on the pocket outer envelope (what a leg would
touch), pack at nominal size, pocket top flush with the box top z 43 ("high") unless stated.

Flat (thickness along x, length along y, width along z), pocket top at z 43:

- Tattu 650: cap depth 25.2 mm (today 8.0), rearmost x -84.3, overhang behind the shells 37.9 mm (today 20.7).
  Pocket |y| <= 30.20, z 9.6..43.0: inside the box outline and inside z -36..43. With the +5 mm length tolerance the
  pocket reaches |y| 32.7, 0.65 mm past the 32.05 rule, so measure the real pack before cutting the pocket width.
  Hip sweep minimum 30.4 mm (right upper leg, pitch -30 roll -10; today's cap 17.7 mm, frame 13.3 mm); at HOME
  47.0 mm. Lowest point above the floor: 126.9 mm standing, 84.0 mm in the SIT keyframe (today's box: 73.3 / 30.4 mm,
  the frame plate and pack bottom at z -44; the cap 81.3 / 38.4 mm). Shell gap 19.5 mm.
- Tattu 850: cap depth 32.2 mm, rearmost x -91.3, overhang 44.9 mm. Pocket |y| <= 31.20, z 10.6..43.0: inside both
  rules at nominal; with a +5 mm length tolerance |y| 33.7 (1.65 mm past the rule). Hip sweep minimum 30.5 mm; floor
  127.9 mm standing, 85.0 mm sitting.

Upright (length along z, pocket top at z 43): same cap depth, rearmost x and overhang as flat (the thickness still
points along x); pocket |y| <= 16.7 (650) / 16.2 (850), z -17.4..43 / -19.4..43, so the pocket is narrower than the
wide tier and only 1.1 / 0.6 mm wider than the narrow tier. Hip sweep 33.3 / 33.2 mm, floor in SIT 57.0 / 55.0 mm.
The pocket hangs 2.2 / 4.2 mm below the step (z -15.2) at the back.

On edge (width along x, thickness along z, pocket top at z 43): cap depth 40.2 / 39.2 mm, rearmost x -99.3 / -98.3,
overhang 52.9 / 51.9 mm; |y| as flat. Hip sweep 39.5 / 34.6 mm. Rejected on overhang: 15 mm more than flat for the
same pack.

Low placements (pocket bottom at z -36.02 + 1.2) bring the pack to 38.4 mm above the floor in SIT (the same as today's
cap) and cut the hip-sweep margin to under 6 mm by the convex-hull bound (650 flat low, right leg pitch -25; the sampled
true-surface check found no leg point within its 6 mm search box, so the real gap is between 5 and 6 mm) or 22.4 mm
(850 flat low). They lower the COM by 2.9 / 3.8 mm. Nothing argues
for them.

Choice for the renders and the COM numbers: flat, top-flush (`tattu650-flat-high`, `tattu850-flat-high`). It has the
smallest overhang, the largest floor margin, keeps the pocket width inside the wide tier and keeps the whole narrow tier
(5991, USB-C, cap ears) as it is. Upright is the alternative when a narrower back matters more than a flat one.

## 3. Centre of mass

Pack mass at the pack centre plus the extra pocket walls (printed, 1.2 mm PLA at the 0.851 slicer fill: 6.4 g for the
650 pocket, 8.1 g for the 850), on the 849.5 g / [-3.28, -0.20, 21.04] baseline. Lever arm = pack centre x minus the
baseline COM x. Sign: negative x = backward (toward the box), the opposite of the +7.5 mm forward tolerance.

- Tattu 650 flat high: 59 g + 6.4 g = 65.4 g added (914.9 g total); pack centre x -75.1 (lever arm -71.8 mm);
  COM shift [-5.13, +0.01, +0.38] mm; new COM [-8.41, -0.19, 21.42], i.e. 8.97 mm behind the official model's COM.
  With the +20 g weight tolerance the shift is -6.56 mm.
- Tattu 850 flat high: 80 g + 8.1 g = 88.1 g added (937.6 g total); pack centre x -78.6 (lever arm -75.3 mm);
  COM shift [-7.08, +0.02, +0.54] mm; new COM [-10.36, -0.18, 21.58], 10.92 mm behind the official model. With +20 g:
  -8.50 mm.

Reading against the tolerance: both shifts are backward, the direction the policy tolerated best (at 5 V it walked at
-10 mm and fell at +2.5 mm; the forward side needed 7.4 V to reach +7.5 mm). Taken alone, -5.1 mm (650) and -7.1 mm
(850) are smaller in magnitude than the 7.5 mm forward figure in D-007. But the box already moved the COM 3.85 mm back,
so the total against the official model is -9.0 mm (650) and -10.9 mm (850): the 650 stays inside the largest tested
backward offset (-10 mm, 5 V); the 850 passes it, and no run covers -10.9 mm. Before committing to the 850, run
`margins.py` style cases at com_x_mm = -10, -12.5 and -15 at 6.8 V (the 7.4 V script never ran a backward case).
The pack also raises the total mass to 915 / 938 g against the official 737 g; the mass side is not covered by the COM
sweep and is the first thing a hardware test of the battery version would show.

## 4. XT30 position

The envelope to reserve is 25 x 12 x 8 mm (an XT30 pair and the lead strain relief); wires are owned by the
outside-wires study and are not designed here. Four candidates near the XL4015 #2 IN window were checked against the
frame, cap, shells, the released wire loops (`wires_F.json`, |y| > 30.85), the hip sweep, the floor in SIT and the pack
pockets:

- **K1 (chosen): x -75.1..-67.1, y -32.05..-7.05, z -5.6..6.4.** Lies across the cap back at the window height on the -y
  half, long axis along y, so the plug is pulled out sideways toward -y with the pack above it. Hip sweep 25.4 mm (right
  upper leg, pitch -30 roll -10), shells 22.2 mm, released loops 1.6 mm, frame 8.0 mm, cap 0 (it rests on the cap
  back by design), floor 68.8 mm in SIT. Gap to the chosen pack pocket 3.2 mm (650) / 4.2 mm (850). It is inside the
  pack's own x range (-84.3 / -91.3..-67.1), so it adds no overhang. With an upright pack it would collide (-9.2 mm):
  upright needs the connector moved to the +y half or under the pocket.
- K2 (outboard of the -y wall, long axis x, y -44..-32): hip sweep 0.08 mm (right upper leg, pitch -30 roll -10) and
  it cuts through the released wire loops (-4.0 mm). Rejected.
- K3 (outboard of the -y wall, long axis z): no leg within 6 mm, but it also cuts the loops (-4.0 mm) and sits where the
  outside-wires study wants the wires. Rejected.
- K4 (behind the cap at the -y corner, long axis x, to x -92.1): the same clearances as K1 but 25 mm of overhang on its
  own, and it blocks the sideways pull. Not needed.

The 5991 lead and the battery lead both end in an XT30 at K1; the one not in use is parked (tied to the pocket).
Nothing in the released box changes for this: the IN-window wire of XL4015 #2 simply ends in an XT30 instead of at the
5991 terminal, which is the outside-wires study's call.

## 5. What to adjust now (least retrofit effort)

1. Keep the cap as the only part that changes: the frame, bosses, windows, tongue slots and ear bosses are already
   right for a battery cap, because the pocket hangs on the cap back and the cap keeps its 8 mm recess. Do not add
   anything to the frame for the battery.
2. Keep the XL4015 #2 IN wire ending outside the box near the IN window (K1 envelope) when the outside-wires study
   fixes the wire routes, so the swap is an XT30 plug and not a terminal screw.
3. Keep the narrow tier, 5991 and USB-C slot: the battery version charges through the same 5991 path (charger to the
   XT30, or the pack's own charger), so the 5991 stays.
4. Leave z 43 as the roof: every placement above fits under it; nothing needs to grow upward.
5. Measure the real pack before the pocket is cut: the 650's +5 mm length tolerance alone is enough to cross the
   |y| 32.05 outline.

## Renders

- `renders/tattu650-view_0.png`: rear 3/4 from the -y side, Tattu 650 flat high (grey box; pocket ghosted in cap
  orange; XT30 envelope red). `renders/tattu650-view_1.png`: -y side.
- `renders/tattu850-view_0.png`, `renders/tattu850-view_1.png`: the same for the Tattu 850.

Both runs went through `run_bounded_cad.py` (study 14 s, 865 MiB peak, exclusive; render 8 s, 599 MiB).
