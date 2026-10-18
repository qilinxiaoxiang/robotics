# Rear pack V1.9

Source for the orange rear pack in the V1.9 incremental print set. It replaces the printed V1.8 pack (`../rear-pack/`). The side shells are not reprinted, so every shell gap below is measured against the printed V1.8 shells (audit solid cache `shell_left` / `shell_right`). The body is the guide's `print/world/rear_pack.stl` and the `rear_pack` row of `../release-V1.9/manifest-V1.9.json`.

## Parts

- `rear_pack-world.stl`: body, 17724.14 mm³, one watertight body, genus 9, 7040 triangles, bounds x −45..−13, y −27.6..27.6, z −44..39.2. sha256 `e2d58d22231e43690aa274925fc9c91146b4a7e7109247a269b6ffc72a9eba00`. The first V1.9 body (with the DFR lips and feet, 17910.92 mm³) was `e03112366e4af88c2cafe7604880e0ba591ceda5df1aea962b5bf1cd4c9d5091`.
- `rear_pack_cover-world.stl`: cover, unchanged from V1.8 (5569.16 mm³). sha256 `1486ae0f99ff45ad86706bf341a2cf4412742b3dc1de9af5605cc4fca04f862a`.

Both are in the world (guide) frame: mm, x forward, y left, z up. `build_rear_pack_v19.py` builds them from the V1.8 builder and writes `build.json` and `features.json` (every feature with its purpose).

## Changes from V1.8

- **BNO085 rib (Shawn, 2026-10-13).** The edge-slot fins, the shelf and its zip-tie slots are gone. A rib on the plate front face (x −19..−13, y −5.5..−2.27, 45° underside down to z 2.2) carries two Ø1.6 through pilots on the board's rear corner holes (x −15.46, z 8.04 and 28.36). Two M2 × 4 go through the board into the rib on the bench, before the pack goes in. After pack-in only about 5 mm is left on each side of the board, too little for a driver. The front holes stay empty: a rib reaching them would cross the right hip link `dxl-5-4` and overhang the torso base when the pack prints upright.
- **Shell seat (Shawn, 2026-10-13).** The T-head is grown 0.4 mm all round (ears |y| ≤ 27.6 from z 31.6, top edge z 39.2 at the notch). Two shoulder bars, 3 mm deep, sit behind the plate (x −24..−21, |y| ≥ 15.3, from z 31.6 up to the head outline lowered 0.05 mm, because the shell roof drops about 0.1 mm towards the back). The printed shells now rest their roofs 0.15 mm (left) and 0.27 mm (right) above the pack instead of 0.55 / 0.71 mm, and each shell's inner rib pair (x −24.5..−23.2 and −20.8..−19.5, tops z 30.4) sits about 1 mm under the bars. The bars stop at |y| 15.3 so the terminal room and the notch cable rows stay open. Notch, cable lanes, cover posts, DFR channel, OpenRB pads and the four hip-yaw screw tabs are unchanged.
- **OpenRB-150 from behind (Shawn, 2026-10-13).** The board used to go in only from above, 3 mm behind its pads, so it could not go in or come out with the side shells on. With the shells on, a straight slide from behind met nothing but the pack's DFR1202 stops: the two corner feet (x −45..−38.5, |y| 10.3..13.6, z −7.3..−3) from 20 mm to 4 mm out and the two front lips (x −37..−36, |y| 11.9..13.6, z −3.5..18) from 12 mm to 10 mm out, against the board edges, which reach |y| 12.4 and 13.0. The shells, pads, walls, floor, posts, USB-C slot and side window were already clear. The feet and lips are removed (186.8 mm³, exact difference with the first V1.9 body, nothing else changed). The DFR1202 is not fitted (`bringup/build/power-diagram/README.md`); the channel stays empty and open. A converter brought back later needs its own removable hold-down and must come out before the board. Board pose, pads and the four M2 × 6 are unchanged.

## Checks

All checks ran under the bounded CAD runner on 2026-10-13 against the guide audit solid cache.

**OpenRB-150 in and out from behind, shells on, cover off** (`check_v19_board_rear.py`, `check_v19_board_rear.json`; exact manifold, 0.5 mm steps, every non-retired guide part at its final pose, the BNO085 on its rib, the guide cable tubes).

- Path: straight +x from 40 mm behind the seat (board front face at x −62.4, behind the shells' rear edge x −46.4) to the seat; removal is the reverse. 81 poses, 0 collisions with the pack, the shells or any other part. Side clearance to the pack (everything but the pads) 0.6 mm (side walls, inner faces |y| 13.6, board edge at y −13.0); floor 0.8 mm; torso base 4.3 mm, BNO085 4.4 mm, hip-yaw motors 4.8 mm; both shells more than 5 mm away. The board seats on the four pads (0 mm at the seat, 0.5 mm one step before).
- Cables not ending on the board: 0 contacts along the path. Cables ending on the board cross its path: links R and L (centre ports), the supply pair (J4) and the UART pair (soldered in J12). For removal, unplug R, L and N, loosen J4 and pull the supply pair and the Pi jumpers, and lead the free ends out of the back; the UART pair moves with the board. For the first build the board goes in before these cables (step order unchanged).
- Board screws from behind with the shells on (shaft along +x to the head top at x −28.4): lower pair any shaft up to Ø6 (0.9 mm to the board's parts, 0.05 mm to the floor); upper pair up to Ø5.5 (0.06 to 0.08 mm to the board's parts), so the guide keeps Ø5 or thinner. The shells are at least 3 mm from every shaft. The heads sit 18 mm in from the shells' rear edge: any shaft 20 mm or longer.
- Access with the shells on and the cover off: J4 screws (Ø3 flat blade along +x to x −34.73, y −2.0 and 1.5, z 20.38) clear; the space above J4 is open 13.4 mm up to the shell roofs (z 38.28) and from behind up to z 31.3 (the shells' rear roof comes down to z 31.39 left, 31.66 right); the JP1 pins and the J12 pads beside them (x −70..−35, y −7.8..1.0, z 8.9..12.7) clear; the two centre-port plugs along +x from 25 mm behind: 0 collisions; the +Y side-port plug through the wall window along −y: clear for the last 20 mm (from further out it meets the left hip, motor7 and its plate, as with the shells off; the shells sit above z 0.26 and do not reach the window).

**Shell gaps** (`check_v19_seat.py`, `check_v19_seat.json`, exact manifold distances). No overlap with either shell.

- Left shell: 0.154 mm minimum, at the bar top edge (x −24, y 15.7, z 38.7). Plate top edge 0.193, ear tip 0.869, plate side beside the ribs 0.552, underside over the ribs 1.024. V1.8 was 0.548 (plate side) and 0.589 at the top edge.
- Right shell: 0.272 mm minimum, at the bar top edge. Plate top edge 0.305, underside over the ribs 1.051, plate side 1.054. V1.8 was 0.705.

**Shells step** (same file). Each shell swept along its guide approach (±40 mm in y) to its seat: 0 collisions with the V1.9 pack, as with V1.8.

**Pack swap with the shells on** (same file). The pack cannot come out or go in along −x while both shells are fitted, in V1.9 or V1.8. V1.9 with the BNO085 and its screws collides from 5.0 to 27.0 mm out (worst excess 341 mm³ left, 354 mm³ right; first contact on the roof slope at x −29..−27). V1.8 collides from 11.5 to 27.0 mm (worst 210 mm³) on a full-height shell interior feature at x −32.5..−31.3. Both shells come off for a pack swap on the assembled robot.

**BNO085 and its two M2 × 4** (`check_v19_imu.py`, `check_v19_imu.json`). Board back 0.005 mm from the rib face, no overlap. Each screw has 2.4 mm of shank in the rib and its tip ends 0.83 mm short of the rib back. No overlap with any final-pose part. Nearest parts: shell_left 0.154, shell_right 0.272, motor5 2.0, torso_base 2.144, motor10 3.144 mm. `dxl-5-4` route 0.623 mm from the rib (tube radius subtracted). Pack-in with board and screws fitted, along the guide approach until clear (30.5 mm): 0 hits. Bench driver along each screw axis (pack and board only): lower screw clear up to a Ø6 shaft (0.54 mm); upper screw needs a shaft of Ø4 or less (Ø4 clears by 0.33 mm, Ø5 touches the upper tab gusset at x −18.2..−16.5, y 11.5..12.5, z 25.5..27.1).

**Board present during torso-fasten** (`check_v19_imu_early.py`, `check_v19_imu_early.json`). Because the board now goes in with the pack, straight 70 mm drivers for the four hip-yaw case screws were checked against the board and its screws: no overlap up to Ø8 (nearest S05-case-076, 2.31 mm at Ø5 and 0.81 mm at Ø8).

**V1.8 checks rerun on the V1.9 parts** (`run_v18_check.py` runs the `../rear-pack/` scripts with their output pointed here).

- `check_fit.json`: the four hip-yaw tabs reproduce V1.8 exactly (lug-box XOR 0 mm³, hole Ø2.50, same seat faces). Wide-box XOR differs only around the IMU rib (S05-case-076 36.06 vs 27.71 mm³ in V1.8). Tab neighbour gaps unchanged: motor10 and motor5 0.224 mm, torso_base 0.0 (contact, as in V1.8). Board rooms unchanged except IMU plug top 3.89 mm (was 5.59) and socket top 2.93 mm (was 4.93). No overlaps with any guide part.
- `check_assembly.json`: pack along +x 30 passes; cover with shells off and on passes; OpenRB straight +x 20 now passes (it failed with the DFR lips and feet), the old drop-in path still passes; DFR box from above passes; upper OpenRB screws need a shaft of 5 mm or less, as before. The old "IMU from above" case still passes but no longer applies (the board is screwed on the bench).
- `check_print.json` and `orientation-check.json` (screen input `orientation-input.json`, rules in `../PRINT-ORIENTATION-PRACTICE.md`): upright on the bottom wall stays rank 1 of 11 candidates. Contact 660.6 mm², height 83.2 mm, tip angle 13.0° (13.2° with the DFR stops; V1.8 14.2°). Overhang 384.2 mm² (387.6 with the DFR stops; V1.8 327.4), of which horizontal underside 250.9 (254.3; V1.8 209.9). The two largest overhang regions are the new ear-and-bar undersides at z 31.6 (48.6 and 47.7 mm²); they need tree support like the V1.8 ear undersides, and the support sits on faces that are at least 1.02 mm clear of the shell ribs after removal. Horizontal-axis holes 10 (8 in V1.8; the two new IMU pilots).
- `check_v19_cables.py`, `check_v19_cables.json` (cables.py test against the pack body): 0 findings for V1.9 and V1.8 (10 cables near the pack in the current guide routes; rerun after removing the DFR stops, nearest clearances unchanged by it). Changed clearances: `dxl-5-4` 0.603 mm (was 1.072, at the rib), `imu` 2.872 (was 3.183), `dxl-l10` 0.909 (was 0.910). The shoulder bars change no cable; the nearest route runs at least 2.4 mm behind them.
- Walking sweep (`sweep-v19-left.json`, `sweep-v19-right.json`, 283,500 adopted frames each, run on the body with the DFR stops; not rerun after their removal: that change only takes material away from inside the bay, behind walls the legs cannot reach): identical to V1.8. Left shin 3.729 mm, left hip 4.942 mm; right shin 5.021 mm, right hip 4.672 mm.

Print gate (`guide/content/interference-audit/run_gate.py`, 2026-10-13, with this body in `print/world` and the guide step `board` sliding in from behind, approach [−25, 0, 0]): passed (solids, pairs, steps, cables). Shell gaps (`check_v19_seat.json`) and the hip-yaw tabs (`check_fit.json`: lug-box XOR 0 mm³, hole Ø2.50, tab neighbour gaps unchanged) were rerun on this body with the same results as above. Print files: `../release-V1.9/run-r2/` (Orange plate, both machines).

## Guide integration handoff

**fasteners.json, two new rows (step: the BNO085 bench mount, see steps.py below).** Both M2 × 4 TAP, `throughParts` [`imu_board`], `intoPart` `rear_pack`, axis [0, −1, 0] (driven from the board face towards −y), pilot Ø1.6 through the rib, shank in the rib 2.4 mm, engagement 2.1 mm, tip 0.83 mm short of the rib back.

- Lower: center [−15.46, −0.695, 8.04]; any driver up to Ø6.
- Upper: center [−15.46, −0.695, 28.36]; driver shaft Ø4 or less.

**fasteners.json, cross screw row (step: shells).** M2 × 6 TAP, center [−38.0, 2.05, 34.96] (head seat on the left tunnel floor), axis [0, −1, 0], `throughParts` [`shell_left`], `intoPart` `shell_right`, right pilot Ø1.52–1.68 from y −0.8 to −5.4, shank in the pilot 3.15 mm, engagement 2.85 mm, tip 1.45 mm short of the pilot end. Only after the left tunnel is hand-drilled to Ø4.2 (instruction in `../shells-v19-source/README.md`); driver shaft Ø3 or less, at least 30 mm long. This closes the two `unassignedHoles` entries at x −38, z 35.

**fasteners.json, horn screws.** No change: S12-horn-025..032 stay M2 × 6 on the printed V1.8 shells.

**steps.py.**

- `imu-board` ("Stand the BNO085 on the pack plate", today after `leg-links`): replace the shelf mounting with a bench pre-mount and move it before `pack-in`. The board's back goes flat on the rib face and two M2 × 4 go through its two rear corner holes; the front holes stay empty. The cable work (`imu-plug`) can stay where it is. The board's final position is the same as in V1.8; what changes is that it is present from `pack-in` to `leg-links`, so `steps_audit` must run with it fitted from `pack-in` on.
- `shells`: add the cross screw. Before fitting the left shell, drill its tunnel per the shell README (once, on the printed part). After both shells are on, lay the robot on its right side, drop the M2 × 6 shank first into the left tunnel and drive it until the head seats on the tunnel floor.
- Note for maintenance: a pack swap on the assembled robot needs both shells off.
- `board` (done 2026-10-13): approach [−25, 0, 0], straight in from behind; the instructions say only the cover has to be off, and a note gives the removal order with the shells on. The `shells` warning says the OpenRB-150 alone does not need the shells off. Step order is unchanged: `orb-power`, `leg-links` and `imu-plug` still need the top open.

**guide/data.** Point the rear-pack part at `rear_pack-world.stl` from this folder, rebuild the solid cache and run the full interference audit before release.
