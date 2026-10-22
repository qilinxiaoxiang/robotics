# A7Z back to back with the camera, Radxa Heatsink 6530B behind it (candidate, not released)

Status 2026-10-22: CAD candidate with its clearance, wall, jaw and assembly checks. Not in print/world, not through the
print gate, not printed. The 6530B envelope comes from Radxa's photos and must be re-measured on the part (arrives
2026-10-26) before release.

## What changes

- **A7Z pose**: vertical, component side (SoC, 40-pin header) facing the rear, header along the top edge, underside (CSI
  socket, microSD) facing the camera. Rear face x 68, top edge z 143.1, pin-1 end at y +32.5. The 6530B sits behind the
  board (x 56.5 to 68), fan at the pin-1 end with its inlet facing the rear.
- **Head cap** (`head_cap_b2b-world.stl`, from `../head_cap_a7z-world.stl`):
  - The two old board rails (vertical webs at each board end with the old Pi pilots) are removed. Everything of the cap
    in that zone more than 2.5 mm inside the outer hull goes; the shell stays whole.
  - Keep-out cut for the heatsink (1 mm), its two corner fin blocks (0.6 mm, plus 0.5 mm along their 2 mm assembly
    slide), the board, the header and Dupont plugs, the underside parts and solder tails (1 mm) and the fan lead (0.5 mm).
  - Three printed ears in front of the board, one at each of the two top holes and the bottom -Y hole. Board-facing side
    relieved 1.3 mm except a dia 5.8 pad round the hole; dia 2.4 clearance hole. The top ears are filled up into the
    roof; the bottom ear carries a 45 degree rib (x 72.1 to 73.6) up to the side boss column. The cap prints roof down,
    so none of the ears needs support. Ears are trimmed 0.6 mm inside the outer hull so nothing shows outside.
- **Cap wire clip (clip_cap)**: dropped. The bundle leaves the rear-facing header directly and no longer crosses the
  board's top edge. clip_head stays.
- **Fasteners**: three M2 x 8 from the front through ear and board into the 6530B's own threads (2.4 mm of thread, the
  same as Radxa's CM2x4x4 through a 1.6 mm board). The bottom +Y hole takes one Radxa CM2x4x4 from the board underside
  and has no ear: the camera socket and its ribbon sit right above it.
- **Cables**: antenna cable from the IPEX plug out of the +Y board end, up past the fan lead, over the top edge and
  forward to the antenna on the roof, 36.6 mm (cable 50 mm). The camera ribbon comes back from the camera along y +33
  and turns into the CSI socket; the spare length folds flat along the left (+Y) wall between the face and the board
  end, as on V1.17. The fan lead tucks along the +Y board end into J6, open under the heatsink end in Radxa's photos.

## Why the top edge is at z 143.1

The 6530B's corner fin blocks sit in the roof's inner corner curve. Lowering the board buys shell behind them and costs
room above the head floor (z 111.3):

- z 144.1: shell behind a 0.6 mm clearance 0.68 mm (fails 1.2); heatsink 2.72, PCIe socket 1.64 above the floor.
- z 143.6: shell 0.99 mm (fails); heatsink 2.22, PCIe socket 1.14.
- z 143.1: shell 1.32 mm; heatsink 1.72, board 1.82, PCIe socket 0.64 (the unused PCIe ribbon socket on the bottom
  edge; rigid, no relative motion to the floor).
- z 142.6: shell 1.62 mm; PCIe socket 0.14 (too close).

## Checks (`checks.json`, run `build_b2b.py` with the CAD venv, about 90 s)

- Cap: one closed solid; shell behind every cut at least 1.25 mm (no sample below 1.2); no hole through the outer
  shell; no ear material outside the outer surface.
- Nearest fixed parts: heatsink 0.63 mm to the cap (corner blocks), 1.72 to head_bottom, 4.83 to the jaw frame; fan air
  gap 1.2 mm to the jaw servo support; ribbon 1.77 to the cap; ears 0.67 to head_bottom, 5.05 to the jaw frame.
- Jaw opening 0 to 27 degrees against the board, heatsink and ears: at least 4.83 mm, growing as it opens.
- Assembly: with the cap roof down on the bench, the board + heatsink unit (kit screw in) is lowered 2 mm behind its
  final place (at least 0.5 mm to the cap all the way), then slid forward onto the ear pads (at least 0.5 mm). A straight
  driver line from each M2 x 8 head out through the face opening is free (the face panel goes on last).
- Ear strength: the top ears are solid up to the roof. The bottom ear's plate alone (2.7 x 7.4 mm section, 16.7 mm from
  the wall) with 7 N at its hole, about a 30 g knock on the 45 g board and heatsink shared by three ears, sees about
  13 MPa, a third of in-layer PLA/PETG strength; the rib adds much more. Bending stress runs along the layers.

## Open before release

1. Measure the real 6530B (outline, corner fin blocks, fan position, thread depth, the pocket over J6 and the IPEX) and
   rerun `build_b2b.py`.
2. Try the camera ribbon fold and the fan lead tuck on the parts.
3. Run the print gate (`guide/content/interference-audit/run_gate.py`), rebuild the guide with the new cap and slice.

## Touch XIAO in this head (`xiao_spots.py`, `xiao_spots.json`)

Same rules as the 2026-10-15 touch study (1 mm grid, moving parts grown 3 mm, jaw swept, the rest grown 1 mm), with
this folder's cap, board, heatsink, plugs and cables. 84.7 cm3 is free. The 22 x 18 x 5 mm board fits in these places:

- The present left-rear pocket (centre -1.9, 24.0, 123.5, leaning 60 degrees on the lower left-rear wall), 212
  centres. A 22 x 18 x 9 mm envelope also fits there (centre -1.3, 22.5, 124.4), so the board can sit on about 2 mm of
  foam tape over copper foil on that wall. No pocket of this size exists at the right rear.
- On the crown under the L1/R1 and M pads (x 34 to 54): fits, but takes pad area.
- On the roof above the A7Z top edge (63.8, 0.3, 148): under the WiFi antenna (x 64 to 76), rejected.
- Low on the left wall under L1 (39.5, 24.5, 134.5): 3 to 7 centres, a tight fit.
- Under the speaker: none.
