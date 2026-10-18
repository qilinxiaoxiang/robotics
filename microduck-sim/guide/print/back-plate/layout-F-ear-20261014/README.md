# Layout F cap: lower-corner retention without the screw tail (study, 2026-10-14)

Study only. Nothing here is released, sliced or gated; Shawn picks an option first. World = guide frame, mm, x forward,
y left, z up. Composite render: `renders/ear-options-compare.png` (rows: current, delete, hidden; columns: rear 3/4 from
+Y, +Y side, rear 3/4 from -Y, low rear view of the narrow tier, inside of the cap).

## What sticks out today

The released cap (V1.11, `../layout-F/`) is held by two top tongues with teeth plus two M2 x 6 ears:

- +Y ear at (y +23.8, z -33.6) beside the narrow tier: 10.4 mm outside the box outline. This is the tail Shawn saw.
- -Y ear at (y -23.8, z -17.4) under the step: 4.7 mm below the step underside, also outside the outline. Smaller, and
  hidden behind the 15 V terminal wires from most angles, but it is the same kind of lug.

## Recommendation

**Hidden screw** (`hidden/README.md`). It removes both lugs, so nothing leaves the outline on either side (outline check
0.0 mm, against 10.4 mm today and 4.7 mm for "delete"). The cap is still screwed at the narrow tier, the fitting path
is unchanged, no wire moves, and the screw count drops from 18 to 16. The cost is one round 4.4 mm driver hole in the
cap back beside the step and an M2 x 10 (stock).

If Shawn prefers the smallest change, **"delete"** (`delete/README.md`) answers his question: yes, the +Y screw can go.
The cap stays on and stays lifted with one screw, but the +Y lower corner then has nothing pulling it onto the rim, so
add the slot hook (no visible change). It keeps the -Y lug.

## Directions that do not work, and why

- **(a) Screw inside the narrow tier (|y| < 15.6)**: any frame boss there sits in the path of the 5991. The board slides
  in from the rim along +x and its PCB fills the narrow tier to within 0.5 mm of every wall (PCB |y| <= 13.9, z
  -34.32..-14.0; cavity |y| <= 14.41, z >= -34.82). The only frame anchors reachable from the cap inside the outline
  are the boards' own bosses, which is what the hidden-screw option uses.
- **(b) Hooks only, no screw**: the cap goes on by sliding in 1.2 mm low and then lifting. Every hook that engages on
  that lift holds the cap against pulling out and against lifting further, never against dropping back down 1.2 mm
  and sliding off. Something must stop that drop: one screw or a snap. A snap on this cap would be an arm printed
  across layers (the cap prints rear face down), or, kept in the print plane, only about 5.5 mm long, which puts
  about 3.6 % strain on PLA for a 0.8 mm catch (1.5 t d / L^2 with t 0.9, d 0.8, L 5.5). Rejected as fragile.
- **(c) Screw from below or through a side wall**: a screw up through the narrow tier floor needs its head below
  z -36.02 or a thicker floor that blocks the 5991 again. A screw along y through a side wall leaves a 1.3 to 1.6 mm
  pan head outside the wall.

## Checks (all options, `ear_options.json`)

Same checks for every row, from the released meshes edited by booleans (`ear_options.py`):

- Cap fitting path [-15,0,-1.2] -> [0,0,-1.2] -> [0,0,0] in 0.5 / 0.1 mm steps: zero overlap with the boards and with the
  frame until the final seat; the final seam overlap is 0.172 mm3 as released.
- Cap to boards: top 0.095, middle 0.288 mm as released; 5991 0.866 (delete) and 0.297 mm (hidden: column front 0.2 mm
  behind the USB-C socket).
- Wires: 0.56 mm to the frame and 0.368 mm to the cap in every option, as released.
- USB-C plug envelope: frame 0.5 mm as released; cap 0.4 mm (delete, slot hook) and 1.0 mm (hidden).
- Board insertion: the frame only loses material (ears, bosses, notches), so the board slide-in paths are unchanged.
- Each part stays one watertight body.

## Files

- `ear_options.py`, `render_options.py`: study sources (CAD venv, bounded runner, about 40 s and 2 s).
- `options/frame_<opt>-world.stl`, `options/lid_<opt>-world.stl` (opt = delete, delete_plain, hidden),
  `options/screw_hidden-world.stl`, `options/hookP-world.stl`, `options/hookM-world.stl`.
- These STLs are boolean edits of the released meshes, for renders and checks. A release would add the same features
  to `../layout-F/build_f.py`. That source needs scikit-image (`shellkit.Outline.solids` imports
  `skimage.measure.marching_cubes`), and the CAD venv no longer has it as of 2026-10-14 evening, so `build_f.py` cannot
  rerun there until it is reinstalled.
