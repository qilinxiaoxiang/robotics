# A7Z status LED window for the next head revision (note, 2026-10-15)

Problem ID: P5 (serviceable hardware): whether the head computer has power should be visible without opening the head.
Status: note only. Shawn asked on 2026-10-15 for a small window so the Radxa Cubie A7Z status light can be seen from
outside, added the next time the head cap or face panel geometry changes anyway. No print file, gate receipt or guide
page changes here. The proposal goes through the normal print gate when that revision happens.

## Result

The A7Z has one LED, a green power indicator (LED2). It sits on the component side next to the board's top edge,
between the two USB-C sockets. In the head that side faces the face panel, so the LED shines forward. The camera board
blocks the view straight ahead, but a line from the LED at about 18° to the duck's right reaches the white face panel
with nothing in the way. The proposal is a plain 3.0 mm round through-hole in the face panel at y −20.0, z 143.0 on
the face front, beside the eye at the duck's right and a little above it. The head cap needs no change.

![Front of the face with the proposed hole, and the A7Z behind the face](led-window-front.png)

## LED facts and sources (checked 2026-10-15)

- **One LED, green, power indicator.** Radxa's hardware page says the power indicator lights green when the board is
  powered normally. It names no other LED. https://docs.radxa.com/en/cubie/a7z/hardware-use/hardware-info
  (checked 2026-10-15; local copy `../print/a7z-head/sources/a7z-hardware-info.md`).
- **Schematic V1.11, page 16 "LED/KEY".** The only LED is `LED2 LED_GREEN`. Its anode is fed from `DCDC1` through
  R212 5.1 kΩ, and from the net `LED_EN` through R46 2.2 kΩ. Page 7 puts `LED_EN` on SoC pin PM2 (a GPIO). The cathode
  goes to ground. https://dl.radxa.com/cubie/a7z/docs/hw/radxa_cubie_a7z_schematic_v1.11.pdf (local copy
  `../print/a7z-head/sources/radxa_cubie_a7z_schematic_v1.11.pdf`).
- **Position, component placement map V1.11, top side ("ass-top").** LED2 sits between J16 (USB-C power) and J4
  (USB-C OTG/DP), against the port edge. R46 and R212 are next to it. Measured at 1:1 from the four mounting-hole marks
  (58 × 23 mm): centre 47.9 mm from the pin-1 end of the board, 28.1 mm from the header edge (1.9 mm in from the port
  edge). The footprint outline is about 2.8 × 1.3 mm, long side across the board. The board is 65 × 30 mm, so the LED
  is 17.1 mm from the pin-40 end. Along the board it lines up between header pins 31/32 and 33/34, on the opposite long edge.
  https://dl.radxa.com/cubie/a7z/docs/hw/radxa_cubie_a7z_components_placement_map_v1.11.pdf (local copy
  `../print/a7z-head/sources/placement-v1.11.pdf`; download page https://docs.radxa.com/en/cubie/a7z/download).
- **Photo cross-check.** Radxa's top photo (`../print/a7z-head/sources/a7z-top.png`, silkscreen "Cubie A7Z V1.10")
  shows a clear chip LED with a green die in the same place. On the 65 × 30 outline it measures s 48.1, d 27.9, within
  0.3 mm of the placement map. It looks like a top-emitting chip LED, about 1 × 2 mm.

**Inferred, not measured.** DCDC1 is the 3.3 V rail (on the same sheet set it feeds `3V3_CAM1` and `WIFI_3V3`). With a
green Vf around 2.6 to 2.8 V, the LED runs at roughly 0.1 mA from DCDC1 alone and at a few tenths of a mA when `LED_EN`
is driven high. Driving `LED_EN` low pulls the node to about 1 V and turns the LED off. So the LED is dim, and software
can switch it off, leave it dim or make it brighter. Whether Radxa's image exposes it as a Linux LED with a trigger
(heartbeat, for example) is not documented for the A7Z.

## Where the LED ends up in the head

Numbers come from `led_sightline.py` and `led_sightline.json` in this folder. They use the current robot-frame meshes:
the V1.17 A7Z cap and face, the camera model and the A7Z frame in `../print/a7z-head/checks.json`.

- **LED position (robot frame, mm, x forward, y left, z up):** (62.25, −15.4, 142.4). The A7Z hangs in the cap with its
  component side facing the face, header at the bottom, and leans 10° forward, so the LED points forward and 10° down.
  It is 15.4 mm to the duck's right of the centre line and 11 mm above the eye axis (z 131.1).
- **Shielded on two sides.** The two USB-C shells stand 3.3 mm tall, 1.7 mm (OTG, +y side) and 2.1 mm (power, −y side)
  from the LED. Light leaves only forward, up or down, and sideways within about 40° of the LED axis.
- **Straight ahead is blocked.** The camera board's −y edge is at y −16.1, 0.7 mm to the duck's right of the LED and
  14 mm in front of it. The board covers the LED's straight-ahead view.
- **Nearest printed walls.**
  - Head cap roof: 10.2 mm, the closest wall by distance. It is 60 to 80° off the LED axis, and the AC019 Wi-Fi antenna
    is taped to the roof directly above the LED (x 64 to 75.9, y ±21).
  - Face panel: 15.6 mm, at the back of the camera's lower-right corner boss. The plain 1.3 mm face plate (back at x
    80.1, front at x 81.4) is 18 to 20 mm away along every clear forward line.

## Proposed window

- **Where:** the face panel, hole centre at y −20.0, z 143.0 on the face front (x 81.4). From the front this is to
  the viewer's left of the black eye trim, 20 mm from the eye axis and 12 mm above the eye centre.
- **What:** a plain round 3.0 mm through-hole, square to the face (along x). The plate is only 1.3 mm thick, so the
  18° oblique view loses about 0.4 mm of aperture. The face prints front-down, so the hole needs no support.
- **Why there:** this is the shortest clear line from the LED to an outside surface that avoids the camera board.
  - Length 19.7 mm, 17.9° off the LED axis. A chip LED keeps about 95% of its on-axis brightness at that angle.
  - Rays from the LED through 12 points on the hole rim hit nothing but the face panel and leave into open air.
- **Margins:**
  - Line axis to the camera model: 2.59 mm; to the USB-C power shell: 1.40 mm.
  - Hole edge to the eye trim: 6.7 mm; to the nearest camera corner boss (y −14.09, z 145.11): 2.4 mm; to the head
    cap: 7.2 mm.
- **How to look:** look into the hole from in front of the duck, about 13° to its right, at head height. The view
  direction from the hole is (0.97, −0.23, 0.03). The direct-view cone is narrow, about ±6° (hole radius plus LED half
  size over 19.7 mm). Further off that line, only light scattered onto the face back is visible.
- **Nothing on the face is in the way.** The hole misses the camera bosses, the trim screw holes and the trim. It is
  a new feature with one stated purpose: seeing the power LED.

### Alternatives considered

- **A frosted window that stays closed.** This means a pocket from the face back that leaves 0.4 mm of white skin
  (two layers) in front of it. It is invisible when the LED is off and would glow from any angle. But the LED runs at
  well under 1 mA, 20 mm away (inferred above), so the glow may be too faint to see in room light. Choose it only if
  the bench check below shows a visible glow.
- **A light pipe from the LED to the face.** A pipe 2 mm in diameter running from 3 mm above the LED to the face
  would give a bright spot visible from wide angles. It is not proposed:
  - Its axis passes 1.4 mm from the USB-C power shell, leaving 0.4 mm at the pipe surface.
  - The populated cap goes on straight down from 40 mm (step `cap-on`). During that descent the Dupont plugs and
    wires on pins 31 to 40 sweep through the space the pipe would cross.
  - A pipe fixed to the face would need its own assembly-path check (`steps_audit.py`) and a holder.
  - A short frosted clear plug held only in the 1.3 mm face hole stays possible. It never enters the head cavity.
- **A window in the head cap roof.** Rejected:
  - The roof sits 60 to 80° off the LED axis.
  - The Wi-Fi antenna covers the roof directly above the LED.
  - The board comes off with the cap.

## Risks and open questions

1. **A wire crossing in front of the LED.** The guide's route for the amplifier DIN wire (header pin 40) passes over
   the board edge between the two USB-C sockets. Its centreline comes 2.2 mm from the sight line, at (66.7, −14.5,
   141.3), about 4.5 mm in front of the LED. The pin-35 LRC route comes within 5.0 mm. A real jumper can lie across
   the LED and hide it. The next revision's wiring step should keep the strip in front of the LED clear (between the
   USB-C sockets, y −14 to −18). Of the gate scripts, `cables.py` checks only penetration, not line of sight.
2. **Brightness.** The LED current is inferred from the schematic, not measured. When the board arrives (2026-10-16),
   check by eye at the bench with the board powered:
   - Look at the LED from 20 mm through a 3 mm hole in a card.
   - Hold a 1.3 mm white printed scrap and a 0.4 mm white scrap 20 mm in front of it.
   This decides between a plain hole and a closed thin window, and shows whether the hole needs to be larger.
3. **What the LED shows.** On the board, `ls /sys/class/leds` and the `trigger` file show whether Radxa's image exposes
   the LED and which trigger it uses. One Armbian forum report says it stays on and does not blink. That report is
   anecdotal and depends on the image. If the LED can be driven (`LED_EN`, SoC PM2), a heartbeat trigger would show a
   live, running system as well as power.
4. **Board revision.** The position is from placement map V1.11, checked against a V1.10 photo. Confirm on the
   delivered board before the hole is cut.
5. **The face panel's other features.** The hole is placed against the V1.17 A7Z face (`../print/face-a7z`). If the
   next revision moves the camera, its bosses or the board, rerun `led_sightline.py` with the new meshes and move the
   hole along the clear line. Any release still goes through `run_gate.py`.

## Reproduce

`/tmp/microduck-cad-venv/bin/python -I led_sightline.py` in this folder. It reads the meshes, writes
`led_sightline.json` and `led-window-front.png`, and changes no print file. It runs in a few seconds and is outside
the release gate. The hole position is the `HOLE` constant.
