# Head mounting trial — 9 October 2026

Print one Orange plate on either machine. The SD ZIP contains two alternatives: a Bambu X1C `.gcode.3mf` and an Elegoo Centauri Carbon `.gcode`. Use the file matching the available printer; both produce the same three pieces. The files use a 0.4 mm nozzle and PLA. The Bambu file is configured for the Cool Plate; the Elegoo file uses the textured PEI plate.

The three pieces are the curved head cap with integral electronics mounts, the speaker cradle and the speaker retaining ring. The cap replaces the original cap (stock item 4), including the earlier V1.4 cap. The speaker pieces replace their V1.4 versions if those have already been printed. This is an incremental head trial; it does not repeat the complete robot or include other unprinted V1.4 parts.

## Fit the parts

1. Remove accessible printing supports while the cap is empty. On the Bambu print, remove the small support strand at the mouth of the lower screw hole on one Pi rail before inserting its screw. The strand sits about 0.21 mm inside the exposed opening. Clear the mounting holes gently; preserve the small posts.
2. Assemble the speaker between its cradle and retaining ring, connect its wires and attach it with two M2.5×8 self-tapping screws.
3. Connect the amplifier leads while accessible and attach the amplifier with two M2.5×8 self-tapping screws.
4. Connect the OpenRB cables before mounting the board with four M2×6 self-tapping screws.
5. Mount the Pi Zero W on its integral rails with four M2×6 self-tapping screws. Keep its existing 40-pin header. Connect the female leads before placing the face assembly.
6. Lay the flexible wires through the available spaces with slack near each plug. Keep the camera ribbon clear of the shell seam. Bring the face and cap together gently and inspect for pressure on plugs or wires.

These new mounting features use eight M2×6 and four M2.5×8 self-tapping screws. Original shell fasteners remain in use. No M2×5 or separate neck washers are added by this trial set.

## What this trial establishes

The trial checks the cap, mounting posts, boards and speaker against the actual hardware. It also checks how the existing female GPIO leads sit under the face. Natural flexible-wire shapes are set by hand during fitting.

The owned straight USB-C plug housing still conflicts with the closed cap in this board arrangement. A suitable short internal Pi-to-OpenRB lead remains unresolved. Do not force the cap closed against that plug. The trial set does not establish a complete closed, powered head.

Once a fitting lead is established, repeat the gentle closure check and verify the Pi can enumerate the OpenRB over USB before final assembly.
