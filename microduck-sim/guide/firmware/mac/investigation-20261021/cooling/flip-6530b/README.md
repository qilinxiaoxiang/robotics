# A7Z flipped, Radxa Heatsink 6530B behind the board: fit check (2026-10-21)

Read-only check on the current guide CAD (`guide/data/guide-data.json` final poses, board frame `guide/print/a7z-head/checks.json`). No part was changed.

- Assumed 6530B envelope: 65 x 30 x 11.5 mm (Radxa page), 13 mm from the component face with the pad, 16 mm with a 3 mm fan inlet gap; it leaves the header strip (d < 6 mm) open, as in Radxa's photo.
- Result (`free.json`, `flip-6530b.png`): with the board flipped in place, 68 % of the heatsink footprint has 13 mm behind it (60 % has 16 mm). The upper part (d 13-30) has 13-50 mm. The lower band d 6-13 along the whole board has 4-10 mm: `jaw_support` (and `motor15`, the jaw servo, at the pin-1 end). Both board ends meet the cap's mounting pads (1.6-2.4 mm), which a flip would redesign anyway.
- Moving the board up does not free the band: the cap roof is 5-8 mm above the board's top edge (median) and near 0 at the ends (`up.py`).
- So the 6530B fits behind a flipped board only if the jaw support and jaw servo drop or move by about 3-9 mm, or the head grows; both change the jaw mechanism or the head shape (jaw geometry change reruns the jaw pose-cap study).

Run: `/tmp/microduck-cad-venv/bin/python -I rear_free.py free`, then `up.py`, `fig.py` in this folder.

## Back to back with the camera (header on top, board 8 mm forward)

Board turned 180° about its long axis (component side, SoC and header face the rear, header along the top edge) and moved 8 mm forward along the board normal, so its underside parts (CSI socket 3.9 mm) sit about 5 mm behind the camera board (front free in the current CAD is at least 12.9 mm to the camera over s 5-60). Rear depth then grows by 8 mm everywhere (`fig2.py`, `back-to-back.png`):
- 6530B footprint (lower 24 mm): 91 % has 13 mm, 80 % has 16 mm. The shortfall (0-3.4 mm) is the lower corner at the pin-1 end (s 5-20, `motor15` and `jaw_support`) and two small spots near s 50-58 (`clip_head`); the middle of the bottom edge has 16-20 mm.
- Header strip (top 6 mm): 95 % has 17 mm for Dupont plugs pointing rearward.
- Both board ends (s < 5, s > 60) are the cap's mounting rails and are redesigned in any flip.

## Change sketch for the back-to-back layout (proposal, nothing built)

`fig3.py` -> `change-sketch.png`. Board parts are the measured TOP/BOTTOM boxes from `guide/print/a7z-head/build_a7z_head.py`; the new pose is `(s, d, h) -> w(s, 30 - d, 1.6 - h + 8)` in that file's board frame.

Printed parts that change:
1. `head_cap`: the four hole pads move about 8 mm forward to meet the board's rear (component) face; the +Y slot no longer needs the ribbon fold room; the -Y microSD slot moves forward with the card (now on the front face); optional roof vent band A above the SoC.
2. `clip_cap`: the board's top edge moves into its space (1.9 mm free today); it is redesigned at the rear or dropped, since the plugs now face the rear.
3. `clip_head`: the bundle now runs down behind the board; the clip moves with it (it is also one of the small 6530B blockers).

Unchanged: face panel, eye trim, camera and its bosses, speaker, amplifier, touch pads and XIAO, jaw and neck parts.

Other consequences: camera FPC becomes a short U-turn in a 5 mm gap (the owned cable length has to be checked on the part); the IPEX socket is on the rear face, so the coax goes over the top edge to the roof antenna (current 36 mm, limit 50 mm); the board's top edge sits under the antenna's rear half (Wi-Fi to recheck); J16 USB-C points down, so the unprinted roof USB service opening no longer applies; plugs face the rear, so the inner-row restriction from the camera covering the edge row goes away. Board mounting method is open: it must be confirmed with Shawn before it shapes printed geometry.

## Vertical instead of 10° lean (estimate)

The 10° lean is inherited from the Pi Zero W pose in the source cap (`guide/print/a7z-head/pi-frame-raw.json`, derived from the guide's header pins); no design reason for it is recorded. The camera sits on the vertical face, so the tilted board is 12.9 mm from the camera at its top edge and about 18 mm at its bottom. Standing the back-to-back board vertical (pivot at the top edge) moves its bottom about 30·sin 10° = 5.2 mm further forward. Estimate from the same depth map (rear + 8 + (30 - d)·sin 10°, ignoring the 1.5 % change in ray direction): the 6530B footprint then has 13 mm everywhere and 16 mm over 97 %; the front gap is at least 4.9 mm (top) and 6.5 mm (bottom 6 mm). Needs a real recast before any CAD.
