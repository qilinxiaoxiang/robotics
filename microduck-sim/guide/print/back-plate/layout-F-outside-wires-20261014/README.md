# Layout F wire routing drafts (2026-10-14): over the roof (dropped) and the drop-in notch option (adopted)

**Current state (adopted, integrated into `../layout-F/build_f.py` as `wires_real_F()` and `notch_cuts()`):** Shawn chose
"侧壳顶部开孔": the 7 V and 5 V pairs cross the box top and drop into the pack through two notches in the frame, hidden in
the crevice between the box front and the shell rear edge. The shells are unchanged. `wires_F.json` here is a copy of
the integrated `../layout-F/wires_F.json` (final routes, lanes y 4.4 / 6.5 / 8.6 / 10.7, outside lanes |y| 34.5 / 36.2).
`../layout-F/checks.json` passes every flag; lengths, gaps and cut lengths are in `../layout-F/README.md`.

- Notch A, top-wall front edge: x -49.8..-47.0 (2.8 deep) through the 1.2 wall, real y 3.2..12.4, rear corners r 1.
- Notch B, cover-plate top edge: x -47..-45, z 28.5..29.5 (1.0 deep, flush with the cover lip top), same band, r 0.5.
- Draft files of the notch option in this folder: `make_frame_notch.py` -> `frame_hidden_noP1_notch-world.stl`
  (10255.0 mm3, watertight, one body, `frame_notch_check.json`), `route_notch.py` -> `routes_notch.json`
  (draft routes at |y| 34.0; the integrated routes use 34.5 and a longer 15V_feed_q approach), `hip_sweep_notch.py` ->
  `hip_sweep_notch.json` (min 9.61 mm, 5V_b), `render_notch.py` -> `renders/frame_notch_*.png`,
  `renders/notch_back_opaque_*.png` (shells opaque), `renders/notch_back_ghost_*.png` (shells see-through),
  `renders/notch_entry_*.png` (the four wires through the notches), `probe/notch_geom.py` (slot geometry).
- Why no shell notch: the only opening at the shell top is the 0.4..1.1 mm crack between the box front edge and the
  shell rear edge; under the shell lip (underside z 31.6..31.9) the cover lip (z 28.5) leaves 3.1 mm, enough for one
  1.8 mm wire layer, so the frame alone needs cutting (B) plus the top-wall bite (A) for the 3 mm bend down.

The earlier over-the-roof route below was dropped by Shawn (its wires_F is `wires_F_over_roof_superseded.json`).

---

# Layout F with outside wires and no passage P1 (design draft, 2026-10-14)

Draft only: nothing here is released or deployed. World frame = guide frame (mm, x forward, y left, z up).
Shawn's decision (2026-10-14): delete front passage P1; every wire of the 5991 and both XL4015 runs outside the box
through the existing side windows; nothing folds back into the box. The box and cap used for every check are the
"hidden screw" option Shawn chose (`../layout-F-ear-20261014/options/frame_hidden-world.stl`, `lid_hidden-world.stl`,
`screw_hidden-world.stl`) with P1 filled.

## Result in short

- The frame without P1 is one watertight body: 10303.3 mm3 (hidden-screw frame 10250.1 + 53.2 mm3 of plate), genus 18.
- **No wire can drop into the pack from the top of the side shells.** The only opening there is the crack between the
  box front edge (x -46.5) and the rear edge of the shells: 0.37 to 1.09 mm wide over |y| 0..18 (shell lip underside
  z 31.5..32.2) and 0.58 to 1.13 mm over |y| 18..28 (z 29..31). A 22 AWG wire needs 1.8 mm. The free-space search
  (0.25 mm grid, inside of the box blocked, entry only from above z 12) finds at most 0.5 mm clearance radius for any
  top entry, at (-45.75, 19.75, 31.5) between the box front and the left shell lip.
- **Best real entry: the head notch of the pack plate**, the opening every other torso cable already uses. The 7 V pair
  runs up the outside of the +y wall, across the box top, forward over the shell roof, round the roof's front edge and
  back through the notch into the pack to J4. The 5 V pair never needs the pack: it runs the same way over the roof and
  joins the neck bundle at (-6, -14, 43.5), then follows the current Pi lead route to the Pi.
- The 15 V link and feed stay on the -y side outside the wall, window to window.
- Rigid parts: every wire keeps at least 0.21 mm (5991 terminal mouth) and otherwise 0.27 mm or more. Hip sweep: at
  least 10.43 mm. Cap hook tab: 1.97 mm (feed_q) and 3.91 mm (feed_p).

## Frame without P1

- `make_frame.py` -> `frame_hidden_noP1-world.stl`: the hidden-screw frame plus the exact P1 volume (x -47..-45,
  y 2.9..12.7, z 12.5..15.3). `frame_check.json`: watertight, 1 body, 10303.3 mm3, genus 18 (P1 open: 10250.1, genus 19).
- `build_f.py` here is the V1.11 source with `PASSAGES = {}` for F: `frame_F-world.stl` 10555.5 mm3 (release 10502.4),
  one body, watertight; the cap it writes is byte-identical to the V1.11 cap.
- The main session's rebuilt `../layout-F/rear_frame-world.stl` (P1 removed, hidden cap) matches
  `frame_hidden_noP1-world.stl` within 1.7 mm3 and 1.0 mm surface deviation (`probe/compare_main.json`).

## Routes (`wires_F.json`, 22 AWG, tube dia 1.8, centreline bend radius 3.0 everywhere)

Terminal entries are the V1.11 ones. + is the lower screw on every terminal, as before.

- **15V_link_p** (mid IN lower -> top IN lower): out at z -1.9 to y -34.0, forward to x -48.5, up, back to x -54.705,
  in at z 25.7. **42.5 mm.**
- **15V_link_q** (mid IN upper -> top IN upper): out at z 3.1 to y -36.2, straight up at x -54.705, in at z 30.7. **37.1 mm.**
- **15V_feed_q** (mid IN upper -> 5991 upper screw): out to y -36.2, down to z -17.6 (under the step), in to y -20.2,
  45 degrees down into the terminal window, in at z -22.31. **46.9 mm.**
- **15V_feed_p** (mid IN lower -> 5991 lower screw): out to y -34.0, back to x -60.9, down to z -20.0, in to y -22.4,
  forward to x -54.6, 45 degrees down, in at z -25.81. **49.1 mm.** The two feed wires never cross: feed_q stays inside
  and above feed_p.
- **7V_b** (top OUT upper): out to y 34.0, up at x -54.705 to z 45.0, across the box top to y 1.2, forward over the
  shell roof at z 43.6, round the roof front edge (front of the hairpin x -17.6), back through the notch at
  (y 1.5, z 37.6), over the OpenRB to J4 at (-31.5, -1.25, 25.4). **115.7 mm.**
- **7V_a** (top OUT lower, +): out at z 25.7, forward to x -48.5, up, across the top to y 3.6, over the roof, hairpin
  front x -15.2, notch at (y 1.9, z 35.3), to J4 at (-31.5, +1.25, 25.4). **120.5 mm.**
- **5V_a** (mid OUT upper): out at z 2.1, back to x -60.9, up, across the top to y -1.2, over the roof, forward to the
  bundle point. **142.6 mm** to (-6, -14, 43.5).
- **5V_b** (mid OUT lower, +): out at z -2.9, back to x -63.3, up, across the top to y -3.6, same path. **153.3 mm.**
- Pi lead beyond the bundle point (current guide route to the Pi header): 291.5 mm.

Notch slots: 7V_b takes the slot the Pi lead leaves free (between UART and link L); 7V_a sits below it, between link N
and link L, 0.3 mm above the notch floor. The J4 wire positions (y +-1.25) are placeholders: the guide models the 7 V
pair as one centreline ending at (-31.5, 0, 25.4); which screw is + follows the board marking.

Cut lengths by the current rule (longer wire of the pair + 15 mm per screw-terminal end, rounded up to 5; Pi lead + 15
at the converter + 45 neck slack): 15 V feed **80** (was 105), 15 V link **75** (was 105), 7 V pair **155** (was 125),
Pi lead **505** (was 500).

## Clearances (`routes_outside.json`, `hip_sweep_outside.json`)

Gaps are surface to wire surface, excluding 1.6 mm inside each terminal clamp (2.0 at J4).

- Box: frame 0.27 mm (7V_a and link_p where their first bend turns along the wall at the window front edge), otherwise
  0.6; cap 1.09 or more; boards 0.79 or more; 5991 0.21 (feed_q) and 0.41 (feed_p) at the terminal mouth.
- Shells: 0.42 mm (7V_b over the left roof), 0.61 to 2.39 for the others. Pack 1.7 mm, OpenRB 1.85 mm.
- Wire to wire: 5V_a/5V_b 0.15 mm at the bundle point, 7V_a/7V_b 0.4, 7V_b/5V_a 0.6, all 15 V pairs 1.2 or more.
- Cap hook tab (x -60.3..-57.4, z -21.26..-20.06): feed_q 1.97 mm, feed_p 3.91 mm. Frame round the tab notch and
  window top edge: feed_q 1.73 mm, feed_p 4.57 mm.
- Hip sweep (each hip pitch HOME +-30 deg, roll +-10 deg, convex-hull lower bounds, `hip_sweep_outside.py` in the dyn
  venv): link_p 10.43, feed_q 10.85, feed_p 14.54, 5V_b 14.82, link_q 16.02, 5V_a 16.7, 7V_a 30.01, 7V_b 36.71 mm. Nothing
  under 2 mm.
- Existing flexible cables (modelled tube overlap, same zone): in the notch and in front of it the 7 V wires overlap
  dxl-r5 by up to 1.17 mm, imu 1.16, uart 1.05, dxl-n12 0.66; the 5 V wires overlap uart 1.33 and imu 1.27 where they
  join the bundle. The current Pi lead overlaps imu 1.7 and uart 1.59 in the same zone, so this is how the bundle is
  already modelled, not a rigid collision. These cables are dressed by hand.
- Not checked: neck motion. The 7 V hairpin round the roof edge (x -20.8..-14.3) is new geometry near the neck base;
  the 5 V run shares the existing bundle path.

## How the cap could change (not implemented)

The rear lane (wire plane x -64.6) and three rear radii were sized by the inside wires. With no wire inside
(`probe/cap_no_wires.json`, the V1.11 radius search rerun without wire points):

- Rear vertical edges, full width: 7.4 -> 7.7 (then limited by the top board body during the 1.2 mm low cap slide).
- Rear step edge (underside of the step): 4.3 -> 8.0, the cap's own 8 mm limit.
- Rear vertical edges, 5991 tier: 4.5 -> 8.0, the cap's own limit.
- Rear top edge 7.8 and the y-z corners stay: boards, not wires, limit them.
- Depth: the cap inner face (x -65.9) can move forward only 0.22 mm, to x -65.68: the inductor top of the top board
  (x -65.38) plus 0.3 sets it, not the lane. The narrow 5991 tier is different: its rearmost part is at x -60.1, so its
  rear face could come forward about 5.5 mm (inner face x -60.4). The hidden screw column in the cap sits in that tier,
  so that change belongs with the cap-fixing work.
- The cap's window notches (x -65.9..-59.1) existed only for the U-loops. Every wire now crosses the wall at x -54.7,
  so the cap side walls can be closed; the frame windows stay open to the rim (x -59.1) so each board slides in with
  its wires attached.

## Change list to adopt this (after the ear option is settled)

`layout-F/build_f.py` (the main session's copy already has `PASSAGES = {}` and the hidden cap):
1. Replace `wires()` for F with `route_outside.wires()` (same eight names and nets); drop `loop_out`, `offset_2d`, the
   ribbons, `X_W`, `XA`, `Y_T`/`Y_FAR` and the docstring lines about U-loops, the rear lane and P1.
2. Call `body_points(meshes, {})`: the outside wire points lie outside the outline and would break `search_radii`.
   Either pin the V1.11 radii or take the no-wire radii above (a cap change for Shawn to confirm).
3. Per-wire checks: keep frame, cap and board gaps; add shells, pack, OpenRB and existing cables as `route_outside.py`
   does; remove the `lane` record.
4. Optional: drop the cap window cuts (`wcut` in `build()`), see above.

`layout-F/hip_sweep.py`: capsules along every wire segment (as `hip_sweep_outside.py`), not only |y| > 30.85.
`layout-F/write_records.py` and README: wiring rule, wire lengths, the `4_wires` check note about the failing P1 wires,
the `xl_windows` and `cap_window_notches` purposes.

`layout-F/wires_F.json`: replace with this folder's file. The 7 V wires now end at J4 and the 5 V wires at the bundle
point, no longer at the pack side of P1 (x -41).

Guide cable data, `guide/content/routes.json`:
- `powerWiresF`: new source path and sha256; boxMm / beyondBoxMm / routeMm: feed_p 49.1/0/49.1, feed_q 46.9/0/46.9,
  link_p 42.5/0/42.5, link_q 37.1/0/37.1, 7V_a 120.5/0/120.5, 7V_b 115.7/0/115.7, 5V_a 142.6/291.5/434.1,
  5V_b 153.3/291.5/444.8; `cutMm` pw-15v 80, pw-15v-link 75, pw-7v 155, pi-lead 505; `_doc` text.
- `routes`: new pair centrelines for `pw-15v`, `pw-15v-link`, `pw-7v` (through the notch to J4) and the box part of
  `pi-lead` (its tail from (-6, -14, 43.5) unchanged). Then run the print gate (`cables.py` checks rigid parts only).
- `build_guide_data.py`: the notes of pw-15v (lines 472-473), pw-15v-link (477), pw-7v (480-481), the pi-lead comment
  (497-498) and the box comment that names passage P1 (353).

`guide/content/steps.py` text (line numbers as of 2026-10-14 21:05):
- 140 chapter summary and 206 overview: no "looped out and back in", no "small passage into the box"; the 7 V pair and
  Pi lead run over the shell roof between the head notch and the box.
- 324 wire-list note of the 7 V pair: its path is the notch, the shell roof and the outside of the box.
- 683 board-swap warning: no "sliding the 7 V pair and the Pi lead back through passage P1"; the pair comes out of the
  notch instead.
- 685-705 `orb-power`: after J4, lead the 7 V pair forward over the board top and out through the head notch (slot
  between UART and link L), free end left in front of the plate; not "through passage P1 later".
- 755-766 comment and `loop_text`: wires go straight out of each window and run along the outside of the wall; no U-loop,
  no rear lane.
- 777-786 `box-frame`: remove the P1 instructions and checks, and the Pi lead lay-in through the notch and channel (the
  Pi lead no longer enters the pack).
- 798-803 `box-5991`: feed leaves the bottom-tier window, runs under the step and up the outside of the right wall to
  the middle IN window.
- 818-822 `box-xl4015`: link outside the right wall; remove "lay the 7 V pair and the Pi lead in the gap from P1".
- 830-840 `box-out`: rewrite: each OUT pair leaves its left window, rises outside the left wall in its own column, crosses
  the box top and runs forward over the shell roof; 7 V round the roof edge to the notch end already in J4, Pi lead
  forward to the neck bundle.
- 851-853 `box-lid`: no wires over the components, no U-loops in the cap windows.
- Assembly order: the 7 V pair and the Pi lead can only be laid over the roof once both shells and the box are on.

## Files

- `make_frame.py`, `frame_hidden_noP1-world.stl`, `frame_check.json`: frame without P1.
- `build_f.py`, `frame_F-world.stl`, `lid_F-world.stl`, `layout_f.json`, `wires_F_inside_reference.json`: V1.11 rebuilt
  without P1 (the inside wires there only reproduce the V1.11 radii).
- `route_outside.py` -> `wires_F.json`, `routes_outside.json` (`python route_outside.py hook` adds the hook tab margins).
- `hip_sweep_outside.py` -> `hip_sweep_outside.json` (run with `~/.venvs/microduck-dyn/bin/python`).
- `probe/entry_gaps.py` -> `probe/entry_gaps.json`, `probe/entry_*.png` (free-space entry search);
  `probe/shell_gap.py` -> `probe/shell_gap.json` (exact box to shell gap); `probe/cap_no_wires.py`; `probe/sections.py`.
- `render_outside.py` -> `renders/`: `frame_noP1_0/1.png` (front plate solid) beside `frame_P1open_hidden_0/1.png`;
  `back_0/1/2.png` (robot from behind, rear-left and rear-right, wires 7 V orange, 5 V yellow, 15 V + red, - black);
  `entry_0/1/2.png` (notch close-up, shells ghosted, existing cables grey).
- Every job ran under `run_bounded_cad.py`; reports in `runs/`. `skimage` was missing from the CAD venv and was added
  (scikit-image 0.26.0 with numpy, scipy, networkx, pillow pinned).
