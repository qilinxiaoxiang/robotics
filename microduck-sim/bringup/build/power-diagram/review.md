# power.png independent review

**2026-10-15 second text update (D-014 amendment, 9 V browned out on walking): 5991 back to switch 3 (15V, marker B at photo fraction y 0.539), charger card "15 V 档", "只开 15V 一个，改开关后重插 USB-C", 14.5-15.5 V, wire labels 15 V, Pi warning 15 V; card 4 stays #1 7.4 V (7.35-7.45, Shutdown 52). Geometry and wiring unchanged. Re-rendered the same way; checked by the author on the render (B on the 15V slider, the 5991 text box no longer overflows after shortening the replug wording); no independent re-review.**

**2026-10-15 text update (D-014): charger card "9 V 档", 5991 marker B on switch 5 (9V, photo fraction y 0.469), "只开 9V 一个", 8.6-9.4 V, card 4 = #1 7.4 V (7.35-7.45, Shutdown 52), wire labels 9 V and 7.4 V. Geometry and wiring unchanged. power.png re-rendered with headless Chrome (1600 x 1270 at 2x), power-web.jpg resized to 2000 px. Checked by the author on the render (no text overflow, B on the 9V slider); no independent re-review of this text change.**

**2026-10-14 layout F: power.html reworked (card 3 = #2 5.00 V to the Pi, card 4 = #1 6.8 V to the OpenRB, Pi and OpenRB cards swapped, USB data cable routed under the Pi card, 5991 text: USB-C enters the left-hand (+Y) window); power.png and power-web.jpg re-rendered. Independent re-review verdict: PASS. Cosmetic notes only, none affecting the wiring read. The 5 V jog sits at y 622, x = Pi card right edge - 30, clear of the zone title and border. The rounds below are for the earlier version.**

Reviewer: draw-diagrams `diagram-reviewer` agent, working from `~/.claude/skills/draw-diagrams/references/aesthetic-principles.md`.
Artifact: `power.png` (3200 x 2540, rendered from `power.html`), web copy `power-web.jpg`.

**Verdict: PASS (round 5, 2026-10-14).** No occlusion, no arrow or label collisions, no overflow, labels readable at full size.

Rounds:
- 1 to 4 FAIL: arrowheads hidden under the XL4015 photos and pills, the 6.8 V and 5 V down labels touching their arrows, wrapped set-point text breaking mid-clause, the 15 V feed crossing the link wires, card gaps too narrow for the over-the-top link. Fixed by rotating both XL4015 photos 180 degrees (IN left, OUT right), widening the card gaps, sizing arrowheads in user-space units, routing the link over the top with one hop, lifting the USB-C pill and splitting text at clause boundaries.
- 5 PASS.
- 6 PASS (2026-10-14, phase 2b): only the 5991 card text changed to "USB-C 线插进盒子右侧的开口。" (the plug enters the -Y side wall of the rear box); it wraps at the sentence boundary and nothing else regressed.

Open delivery check (D21): the rebuilt `bringup/BRINGUP.html` must embed the current `power-web.jpg` bytes, and the figure must be viewed at 1280 and 390 px.

Non-blocking notes left as they are: en dash and minus glyphs in "USB-C" and the polarity marks; empty lower halves of the OpenRB and Pi cards; on a phone the figure needs pinch zoom to read.
