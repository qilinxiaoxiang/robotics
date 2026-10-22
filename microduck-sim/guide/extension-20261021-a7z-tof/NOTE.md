# VL53L8CX depth sensor behind the A7Z face (placement study, 2026-10-21)

Problem: final goal step 1/4 (find the item, pick it up with the beak). Pollen's official MicroDuck head carries an
8×8 ToF sensor (VL53L8CX, or VL53L5CX) behind a small window beside the eye (pollen-robotics/microduck 942e58e,
`tof/`, `deploy/robotd.toml` [theremin]). This note answers where the same sensor fits in our A7Z head.
Status: study only. No print file, gate receipt or guide page changed.

![Front view and sections](tof-placement.png)

## Result

- **Spot:** the Pololu 3419 carrier stands upright (22.9 mm tall) flat on the face back, centre y −23.0, z 130.0,
  components facing forward. The sensor is at the board centre, 22.9 mm to the duck's right of the camera axis.
- **Room:** at least 15.2 mm of free depth behind the face over the whole footprint plus 0.5 mm margin; the
  envelope used is 6.5 mm (0.3 air, 1.8 parts, 1.02 PCB, about 3.4 solder joints and wire bends).
- **Field of view:** the full 45° × 45° pyramid is clear of the eye trim, cap overhang, jaw frame and lower shell
  out to 1 m.
- **Other fitting centres:** y −28.5 to −23.0, z 123 to 131 (171 of the 241 fitting centres). Centres above z 131
  block the sightline from the A7Z green LED (world 62.1, −15.4, 142.4) to the planned LED hole at y −20, z 143.
- **What does not fit:** any landscape board, and anything on the duck's left: the camera ribbon (z 125 to 137, to
  y 33) and the cap walls take that side.

## Needed before it works

- A window in the face panel. The sensor cannot range through 1.3 mm of white PLA. Estimate: about 8 × 4.6 mm,
  the VL53L8CX package (6.4 × 3.0 mm) plus the 45° cone over the 1.6 mm from the sensor top to the face front.
  ST's cover-window guidance has not been checked yet. This is a face change and goes through the print gate.
- Mounting: double-sided foam tape on the face back, or two M2 bosses for the carrier's holes in the same reprint.
- Wiring: VIN (3.2 to 5.5 V), GND, SDA, SCL. Default 7-bit address 0x29 does not clash with the BNO085 (0x4A,
  TWI7) or the touch XIAO (0x2A, TWI0). Pololu: about 100 mA typical while ranging, 150 mA peak.

## Sources

- Pololu 3419 page, specs and dimension drawing (checked 2026-10-21): https://www.pololu.com/product/3419,
  https://www.pololu.com/file/0J2032/vl53l8cx-carrier-dimensions.pdf (12.7 × 22.9 mm, PCB 1.02 mm, parts 1.8 mm,
  sensor 6.3 mm from the left and 11.4 mm from the bottom edge, 65° diagonal / 45° FoV, 20 mm minimum range).
- Head meshes: `../print/face-a7z/`, `../print/a7z-head/`, `../print/world/`. Face back plane x 80.1, front 81.4.

## Reproduce

`/tmp/microduck-cad-venv/bin/python -I tof_place.py <dir>` (about 40 s), then `tof_render.py <dir>`.
