# Split ankle (release 2026-10-19, V1.22)

Superseded on 2026-10-20 by the two-half ankle, `../ankle-halves-20261020/` (release V1.24): the printed base and side looked fragile and their screw posts caught the servo wire. The V1.22 black sleeves and slip-fit feet stay.

Shawn, 2026-10-19: the orange one-piece ankle bracket is hard to fit, and repeated fittings load the ankle servo. The bracket is a closed fork. The lower-leg link with its XL330 and black sleeve cannot come down into it (the sleeve catches the fork at 16.5 mm above the seated pose, `leg-guide-20261006/assembly-path-investigation.md`), and the stock sleeve is itself a 0.17 mm press fit on the 10 mm link boss. So each fitting spread the fork over the package by force.

The fix is the 2026-10-07 digital design in `build-pack-20260913/redesign-20260913/ankle-redesign-20261007/` (`DESIGN-NOTES.md`, `README.md`), which was never printed. Each ankle becomes three parts:

- **Base** (orange): the stock bracket with the passive side cut away between the two outer pillars. It keeps the four motor-output holes, the servo mating face and the foot block, so the servo screws and the foot interface are unchanged.
- **Side** (orange, "cheek" in the 10/07 files): the removable passive side, on the inner face of the ankle (towards the other leg). It closes along the shaft, away from the centre line, onto the sleeve until its two tabs meet the solid base posts, and two black M2 x 8 TAP from above (1.6 mm pilots in the base, 2.3 mm clearance holes in the side, 4 mm of thread) pull the flat faces together. The screws in their holes set it sideways and the sleeve in its pocket sets it radially; there are no tongues or slots (removed 2026-10-19: the 0.4 mm tongues and the 0.9 mm slot walls were too thin to survive handling).
- **Sleeve** (black): OD 14.6, bore 10.4, 2.8 mm wide, 0.2 mm entry chamfers. It slides onto the link boss by hand and runs free in the side's pocket (about 0.4 mm diametral clearance each side, by design; the stock sleeve was 9.65 bore, 3.0 wide).

The 10/07 geometry is used as it is. What this directory adds is the check against the robot as it is now (with the V1.22 slip-fit feet), the guide and print-gate integration, the print poses, and the release.

## Check against the current robot (`ankle_split_check.py`, `ankle-split-check.json`)

The audit solids of the current guide world (lower-leg link, XL330, 0.5 mm washer, slip-fit foot) against the 10/07 world STLs, both legs:

- **Seated:** no overlap between base, side, sleeve and the link, servo, washer or foot. The two side screws engage only the base pilots (3.93 mm3 each), nothing else. The right base keeps the 0.137 mm3, 0.001 mm thick source mating-face slab against the servo that the stock bracket has.
- **Sleeve on the link boss:** 0 mm3 (stock sleeve: 14.96 mm3 press fit).
- **Foot seat:** the slip-fit foot seats on base plus side with no overlap, rests on them (23.7 mm3 of contact on a 0.05 mm drop; stock bracket 24.8) and has the same sideways play as on the stock bracket: toe 0.18, heel 0.14, across 0.14 to 0.18 mm. Base plus side add no material outside the stock envelope where the foot sits.
- **Foot path:** the foot slides 15 mm straight down off base, side, sleeve and screws with no contact.
- **Package path, side off:** the link-servo-washer-sleeve package lifts 30 mm straight out of the base with no contact (right: the 0.137 mm3 slab only).
- **Side path, foot off:** the side slides 12 mm along the shaft towards the centre line, clear of the base and the package. With the foot on it is captured (281 mm3 of overlap with the foot at 3 mm): the foot holds the side in, so the foot comes off first when an ankle is opened.
- **Side screws:** lifted 3.5 mm they are clear of the base; they never touch the side.

It also writes the six guide/gate world files `guide/print/world/ankle_{base,cheek,sleeve}_{left,right}.stl`. The guide (`content/build_guide_data.py`, `ia_lib.WORLD_FILE`) now shows the base in place of the bracket, the new sleeve in place of the old, and the side as a new leg part; `steps.py` has the two bench steps `ankle-split` and `ankle-feet`, and the print gate (`run_gate.py`) tests their approach paths.

## Print poses

Chosen by native slicing on both machines: `poses/poses.json` and `poses/poses.md` (the bearing, sliding and register faces print clean; support is allowed on cosmetic faces only). The release manifest (`release-V1.22/scripts/make_manifest.py`) reads the poses from there.

## Fitting

On each leg, with the ankle-and-foot module off the knee (four M2 x 6 at the knee output, cup T2):

1. Old foot off: toe M2 x 6 out, hold the bracket and rock the foot off (it may crack; it is replaced). Cup A: four M2 x 4 output screws, two M2 x 10 case screws, the M2.6 x 8 rear centre with its 0.5 mm washer. Pull the link off the bracket evenly, lift the servo out, set the old bracket and sleeve aside.
2. New sleeve onto the 10 mm boss of the link by hand. Washer, rear centre and case screws back on, so link and servo are one package.
3. New base onto the servo output, horn side in; start the four M2 x 4 loosely from the outside. The package sits straight down into the base.
4. Side onto the inner face of the ankle: up from below, 8 mm inside its seat, then along the shaft away from the centre line onto the sleeve until its two tabs meet the base posts. Two M2 x 8 from above, evenly, hand snug. Tighten the four output screws.
5. New foot straight up onto base and side by hand; M2 x 6 from above through the toe of the base into the foot.

Never spread the base or press the link in; with the side off nothing needs force. To open an ankle later: foot off first (one screw), then the two M2 x 8, then slide the side off towards the centre line.

Regenerate the check and the world files:

```bash
/tmp/microduck-cad-venv/bin/python ankle_split_check.py
```

About 10 s; run it under the bounded runner.
