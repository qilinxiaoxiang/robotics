# Side shells, next-version source

**Source only. These shells are not in the V1.9 print set and are not reprinted.** The printed V1.8 shells stay on the robot. For V1.9 the only shell work is hand-drilling the printed left shell's cross tunnel and fitting one cross screw (instruction below). The STLs here record the two shell changes for whichever later version reprints the shells.

## Files

- `shell_left_v19_source-world.stl`: 11224.6 mm³, one watertight body, genus 6, 22730 triangles. sha256 `5df6cca72f69083e82668bbe07f248ca581b00e46fe135f6bae7b724af1fc74c`.
- `shell_right_v19_source-world.stl`: 11148.72 mm³, one watertight body, genus 6, 21498 triangles. sha256 `1ce74205c81ec7438c1f57f0e3e98d4ac939a3a5961007edc6901bfa83514941`.
- `build_shells_v19_source.py` builds both from the audit solid cache (`shell_left` / `shell_right`, the printed 10/1 shells) and writes every measurement below to `shells-v19-source.json`. World (guide) frame: mm, x forward, y left, z up. Print pose and slicing are not checked; that belongs to the release that reprints the shells.

## Changes from the printed shells

1. **Left cross tunnel bored to Ø4.4** on the axis x −38.0, z 34.96, from the floor (y 2.05) to the outer mouth. An M2 pan head (Ø4.0) then reaches the floor and one M2 × 6 joins the two shells through the right shell's pilot. Removed 73.78 mm³.
2. **Horn-screw counterbores Ø4.4 × 2.0** on S12-horn-026, 027, 028 (right shell, into the ID12 idler) and 029, 030, 031, 032 (left shell, into motor12). The shell is 3.3 mm thick there, so 1.3 mm stays under each head and the head top sits 0.5 mm below the outer surface. If adopted, these seven become M2 × 4 with the same thread engagement as today's M2 × 6 (1.8 mm into the idler, 2.3 mm into motor12). S12-horn-025 keeps its flat seat, because the neck-route wire clip sits under that head. Removed 90.99 mm³ (left) and 68.19 mm³ (right).

**Tunnel wall with the Ø4.4 bore** (`wallPerAngle` in the JSON: every 10°, every 0.1 mm). The bore misses the 0.9 mm wall target in two small patches where the printed wall was thicker: 0.887 mm at the floor end (y 2.05–2.35, upper front side) and down to 0.831 mm on the upper side of the last 2 mm before the mouth (y 25.5–27.5). From y 26 outwards the printed wall is already below 0.9 mm on some side, because the tunnel breaks out through the curved outer face; the bore removes at most 0.09 mm there. Thickening the outside would put a bump on the outer face, so the bore size needs a decision when the shells are next reprinted. A Ø4.2 bore leaves at least 0.99 mm wherever it cuts, but a printed Ø4.2 hole may come out too tight for the Ø4.0 head.

## Printed V1.8 left shell: drill the cross tunnel (for the guide)

**Why.** The printed tunnel tapers from Ø4.30 at the mouth to Ø3.42 at the floor (0.035 mm per mm). The 4.0 mm head of an M2 pan-head screw jams about 16.5 mm above its seat. A 4.2 mm drill lets the head reach the floor.

**What the mesh says.**

- Floor (the head seat) at y 2.05. Below it a Ø2.12–2.28 clearance hole runs 1.95 mm to the shell's inner face (y 0.1).
- The mouth is cut by the curved outer surface, so its rim is not flat. Measured from the rim to the floor: 25.1 mm at the upper rear edge of the mouth, 28.9 mm at the lower edge.
- A Ø4.2 drill only cuts from the floor to y 23.65 (21.6 mm above the floor); the outer 3.5–7.3 mm of the tunnel is already wider and just guides the bit. It removes at most 0.39 mm per side, at the floor.
- Wall left after a Ø4.2 drill: at least 0.99 mm wherever the drill cuts (thinnest at the floor end, on the upper front side). From y 26 outwards (the last 1–5 mm before the rim, depending on the side) the printed wall is already below 0.9 mm, because the tunnel breaks out through the curved outer face; a Ø4.2 drill does not touch that part. Ø4.4 and Ø4.5 also pass the head but cut almost to the rim and leave 0.83 mm and 0.78 mm in places where the print had more than 0.9 mm, so use Ø4.2.
- Right shell pilot: Ø1.52–1.68 from y −0.8 to −5.4 (4.6 mm long). Beyond it the right shell has its own open tapered bore (Ø2.94–3.2) to its outer face, so the pilot is not blind.
- Seam between the shells at the screw: 0.9 mm.

**Tools.** 4.2 mm twist drill (standard 118° point) in a pin vise or a hand drill at its lowest speed; a strip of tape; the M2 × 6 that will be used; a screwdriver with a shaft no thicker than 3 mm and at least 30 mm long.

**Steps.**

1. Take the left shell off the robot (the reverse of the shells step: S12-horn-029 to 032 and S10-case-071). Drilling off the robot keeps chips out of the torso and makes the stop check below possible.
2. Wrap a tape flag on the drill 30.0 mm from its tip. The flag first meets the outermost point around the mouth (y 30.95 or further out), so it stops the drill with its full diameter at least 0.15 mm above the floor and its tip at least 0.85 mm short of the inner face. The flag cannot let the drill go deeper than the floor; if it stops the drill early, step 4 shows it.
3. Hold the shell so the tunnel points straight down and drill along the existing tunnel until the flag touches. Clear the chips.
4. Stop check: drop the M2 × 6 shank first into the mouth. When drilling is complete the head lands on the floor and the shank stands out of the inner face by about 4.0 mm (6 mm screw minus the 1.95 mm floor). An undrilled tunnel holds the head about 16 mm up and nothing comes out. If the shank stands out less than 3.8 mm, move the flag 0.5 mm towards the shank and drill again. If it stands out more than 4.5 mm, the floor has been cut; stop and report it.
5. Refit the shell with the same five screws. The horn screws keep their flat seats; the counterbores above are for a future reprint only.

**Fit the cross screw** (shells step, after both shells are on).

- Lay the robot on its right side, left side up. Drop the M2 × 6 shank first into the left tunnel. It falls until its tip rests on the right pilot entry.
- Drive it with the thin screwdriver until the head seats on the floor (the head top is 27.4 mm below the outermost point of the rim). A shaft of Ø3 clears the drilled tunnel by 0.6 mm; Ø4 would clear a Ø4.2 hole by only 0.1 mm.
- Result: head on the floor at y 2.05, shank crosses the 0.9 mm seam and runs 3.15 mm into the right pilot, 2.85 mm thread engagement, tip 1.45 mm short of the pilot end. No other part is within 3 mm. An M2 × 8 also fits: 4.6 mm in the pilot (the full length) and its tip ends 0.55 mm into the right shell's open bore, touching nothing.
- Nearest cable: `dxl-l10`, 2.6 mm from the screw at (−33.2, 5.4, 33.1). It runs about 1 mm outside the tunnel tube, so the tube wall (at least 0.99 mm after drilling) separates it from the drill and the driver. Earlier handoff notes gave 5.9 mm; this value is the exact surface distance from the drawn cable tube.

## No-drill option: M2 × 12 socket head in the existing taper

Rejected. A socket head cap screw (ISO 4762, head Ø3.8) stops where the printed bore narrows to its head diameter, not on a seat:

- Ø3.8 head stops at y 12.8, 10.75 mm above the floor. An M2 × 12 tip then ends at y 0.8, still inside the left shell: 0 mm engagement.
- Real heads vary. Ø3.7 stops at y 10.0 (0.9 mm engagement); Ø3.9 stops at y 15.6 (0 mm). Even an M2 × 16 would give anywhere from 0 to 4.6 mm across that range.
- The head position moves 2.85 mm for every 0.1 mm of head or bore diameter error, and the head wedges into a 1° taper. Tightening it pushes the tube wall (about 1.5 mm where the head stops) outwards and can split it.
- M2 × 12 and M2 × 16 socket heads are not in the screw stock (M2 × 4, 6, 8, 10 only).

**Recommendation: drill the printed left shell to Ø4.2 and use the M2 × 6 already in stock.**
