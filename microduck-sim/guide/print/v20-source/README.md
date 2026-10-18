# V2.0 source: side shells screwed to the rear pack, jaw without the dead pivot hole, head screws all M2

**Source only, not released.** No print pose, slicing or print gate has run on these parts. Those belong to the V2.0 release, which also rebuilds the guide from this geometry. The robot keeps the printed V1.8 shells, the V1.8 jaw frame, the V1.8 lower head shell, the V1.9 cap and the V1.9 rear pack until then.

## Why

- **Shell cross screw (Shawn, 2026-10-13).** The V1.9 cross screw at the back of the torso has to be driven 27 mm down a hand-drilled tunnel. Shawn found it too hard to drive and asked for each shell to be fixed to the rear pack instead. He chose this over external screw ears, which would show outside the body and stick out towards the legs.
- **Head screws to M2 (Shawn, 2026-10-13).** M2.5 is hard to find. The seven M2.5 head screws (four through the jaw support, three closing the cap) became ROBOTIS M2.6 in the current guide, which fit the printed holes. Shawn prefers M2 so the whole robot uses one screw size, with any print change in V2.0.
- **Jaw pivot hole (Shawn, 2026-10-13).** The passive (−Y) jaw arm turns on the mouth sliding ring and takes no screw. The Ø2.0 × 6.8 mm hole on its pivot axis was inherited from the community part, and nothing in the build uses it. Shawn asked for it to be removed.

## Parts

All three files are in the world (guide) frame: mm, x forward, y left, z up. Each is one watertight body.

- `shell_left_v20-world.stl`: 11640.74 mm³, genus 6. sha256 `4e55338ec1eb24ad5d70daccd4a7f36bdc29251b32f478339fed7a8f3dc35410`.
- `shell_right_v20-world.stl`: 11407.13 mm³, genus 6. sha256 `a718e9279c97254fe335d7064c90aa6a18d2e72065860ffad058334d1ced63a7`.
- `jaw_frame_v20-world.stl`: 27985.43 mm³, genus 10 (printed: 11). sha256 `b046fbd1be10b3e129ede274e10573b319ec82f632198f96d8d6937dbff47ec9`.
- `head_bottom_v20-world.stl` (yellow lower head shell): 27079.06 mm³, genus 7 as printed. sha256 `3b0425a503d67cf5e68c8729da2bdbc5d9fb1621daf995752fd7a7d3c0fc9433`.
- `head_cap_v20-world.stl` (orange cap): 35352.80 mm³, genus 53 as printed. sha256 `b187fc96bf5b9bf84cf3c0f82d793dd7115326572a9e660f8a9411fa5576de34`.

`build_v20_head_m2.py` builds the two head parts from the audit solid cache (the V1.8 `head_bottom` and the V1.9 `head_cap`) and writes `v20-head-m2.json`; under the bounded runner it took 250 s and 2.7 GiB.

`build_v20_source.py` builds all three from the audit solid cache: the printed shells, the V1.9 `rear_pack` and the V1.8 `jaw_frame`. It writes every measurement to `v20-source.json`. `render_v20_checks.py` draws the sections in `png/`. Run the builder under the bounded CAD runner; on 2026-10-13 it took 11 s.

## Changes, and the purpose of each feature

1. **Shell-to-pack screw, one per shell.** An M2 × 6 is driven straight down through the shell roof into the V1.9 pack's shoulder bar. Axis x −21.5, y ±20.
   - **Shell:** a Ø2.2 clearance hole and a Ø4.4 counterbore. The counterbore floor sits 1.0 mm below the highest point of its rim (left z 40.01, right z 40.10). That leaves 1.2 mm of roof under the head, and the head stands about 0.6 mm above the roof.
   - **Pack:** the print is unchanged. Bar plus plate are solid from x −23.98 to −19.02 and from z 31.6 to z 38.45 (left) or 38.43 (right). The Ø1.6 pilot is drilled through the shell's hole, which guides the drill (see below), and leaves 1.68 mm of wall in front of and behind it.
   - **Thread:** 4.1 mm of engagement in the bar on the left and 4.0 mm on the right. The tip stops 2.4 to 2.5 mm above the bar bottom.
   - The roof sits 0.36 mm (left) and 0.49 mm (right) above the bar. Drive the screw until the head touches the counterbore and no further; tightening further would bend the roof down onto the bar.
2. **Cross tunnels filled.** Both shells' tunnels at x −38, z 35 are filled: the bore, the left clearance hole and the right pilot. The cap is cut from the shell's own local convex hull, shrunk by 0.008 mm, so it follows the curve of the back. `png/tunnel-fill-sections.png` shows it flush with the printed skin, and no hole shows outside. The fill stops at each shell's inner face, so the 0.9 mm seam between the shells stays open. Material added: 360.6 mm³ (left) and 276.6 mm³ (right). The added material touches no other part.
3. **Horn-screw counterbores.** These are Shawn's next-reprint item from `../shells-v19-source`: Ø4.4 × 2.0 counterbores on S12-horn-026 to 032. With them, these seven screws become M2 × 4 with the same thread engagement as today. S12-horn-025 keeps its flat seat, because the V1.9 torso wire clip sits under its head.
4. **Jaw pivot hole filled.** The hole ran along y from −43.8 to −37.0 on the axis x 26.1, z 118.61. The fill is flush with the arm's outer face and with the boss tip (`png/jaw-hole-sections.png`). The boss outline, its tip face at y −37.0 and the sliding-ring seat are all unchanged.

5. **Head screw pilots for M2.** The four lower-shell bosses under the jaw support (H-jaw_support-01 to 04) and the three cap bosses (K-head_close-01 to 03) had 2.0 to 2.2 mm pilots for M2.5. Each pilot is filled (Ø2.4, trimmed to the part's own local convex hull) and re-cut at Ø1.6 over the same span; a blind pilot stops 0.3 mm short of its old bottom. The 2.8 mm entry chamfers stay. Nothing else changes, and the jaw support, the head wire clip and the lower-shell tabs keep their 2.65 to 2.85 mm through holes, which clear M2 by 0.65 mm or more.
   - Screws: M2 × 6 in the three bare jaw-support holes (3.3 to 4.0 mm of thread), M2 × 8 through the clip tab (3.3 mm) and M2 × 8 in the three cap closures (5.0 mm).
   - Added material: 63.5 mm³ (lower shell) and 49.5 mm³ (cap), all inside the old holes. It touches no other part and lies inside each part's old outline.
   - These two parts are a full head reprint. The M2.6 screws in the current guide work in the printed holes, so this change only makes sense once the head is reprinted for some other reason or when you want a single screw size.

## Checks (2026-10-13, `v20-source.json`)

- **Pack screws.** Neither screw nor pilot overlaps or comes within 3 mm of any final-pose part other than its own shell and the pack. Nearest cable: `dxl-n12`, 6.4 mm from the left screw; `dxl-5-4`, 10.9 mm from the right screw.
- **Driver access.** Straight above each head the first part is the lower head shell, 57.8 mm away in the final pose. At the shells step the head is not yet fitted, so the space above is open. Later maintenance needs a driver shorter than 57 mm.
- **Final-pose overlaps of the new shells.** These are the same as for the printed shells: left with motor10, 0.15 mm³, which is already present in the print. There is nothing new. The narrowest seam gap between the shells is still 0.051 mm.
- **Outside shape and assembly paths.** The outer shape is unchanged: the counterbores only remove material, and the fill is flush. The walking sweep and the shells-step approach are therefore unaffected. The full print gate still runs at release.

## Guide integration handoff (for the V2.0 release)

**fasteners.json**
- Remove the cross-screw row `X-shell_cross-01` and the two `unassignedHoles` entries at x −38, z 35. The tunnels are gone.
- Add two rows, step `shells`. Both are M2 × 6 TAP, axis [0, 0, −1], `throughParts` [`shell_left`] or [`shell_right`], `intoPart` `rear_pack`.
  - Left: center [−21.5, 20.0, 40.009], engagement 4.14 mm.
  - Right: center [−21.5, −20.0, 40.102], engagement 4.03 mm.
- S12-horn-026 to 032 become M2 × 4 TAP.

**steps.py, `shells`**
- Delete the tunnel drilling, its stop check and the cross screw.
- After both shells are on, for each shell:
  1. Put a 1.6 mm drill through the shell's roof hole, straight down, with a tape flag 7.0 mm from the tip.
  2. Drill into the pack's shoulder bar until the flag touches the counterbore floor. That puts the full drill diameter down to about z 33.5, 2 mm above the bar bottom.
  3. Blow out the chips.
  4. Drive one M2 × 6 until the head touches the counterbore.
- The prepare list loses the 4.2 mm drill and the long thin driver. It gains a 1.6 mm drill.

**Head screws (if the head parts are printed):** in fasteners.json, H-jaw_support-01/02/04 become M2 × 6, H-jaw_support-03 and K-head_close-01 to 03 become M2 × 8, all with the pilot 1.6 mm (`v20-head-m2.json` gives each engagement). In steps.py the `head-bottom`, `head-clip`, `close` and `tools` screw lists follow; the M2.6 × 6 and M2.6 × 8 head entries go away.

**steps.py, `prints`:** list both shells and the jaw frame as V2.0 prints, and the lower head shell and cap if they are printed.

If the pack is ever reprinted, model the Ø1.6 × 5 mm pilot in the bar at the same axes and drop the drilling sub-steps.
