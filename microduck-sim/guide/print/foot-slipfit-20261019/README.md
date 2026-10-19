# Slip-fit feet (2026-10-19)

The orange ankle bracket and the yellow foot press together so tightly that they cannot be taken apart, and every fitting loads the ankle servo (Shawn, 2026-10-19). The new feet slide onto the bracket by hand; the toe M2 x 6 TAP holds them.

## Why the stock foot is a press fit

- The bracket's lower block sits in a socket in the top of the foot. In CAD the socket walls touch the block with zero clearance, and the two parts overlap by about 0.1 mm over the contact faces: 67 mm3 of overlap in the seated pose.
- Two snap tongues, at the heel and at the toe, carry hooks of about 0.3 mm over the bracket's flange, so the block cannot go straight in.
- Printed parts add their own oversize on top of that.
- The printed feet (`community-44` left, `community-46` right) are not the guide's source foot: their socket is rolled about 4.8 deg about the front-back axis. Fitted to the real socket, the bracket sits rolled -4.84 deg (left) and +4.89 deg (right), fit rms 0.26 mm. The new feet keep that roll.

## What changed

`foot_slipfit.py` works on the foot only. The bracket is screwed to the servo horn and stays.

1. It fits the bracket's pose in the real socket by point-to-plane ICP.
2. It takes the region the bracket sweeps through as it moves straight down its own axis into that pose: everything above the bracket's lowest surface. This removes the hooks.
3. It grows that region 0.2 mm sideways and cuts it out of the foot. The faces the bracket rests on keep zero vertical clearance, so the bracket seats where it seats now.

Checks (`slipfit-check.json`):

- **Seat:** no overlap in the seated pose, either foot. The bracket rests on the seats: dropping it 0.05 mm overlaps 25 mm3.
- **Insertion path:** clear for 15 mm along the bracket axis.
- **Play:** 0.16-0.20 mm in each sideways direction in CAD. The bracket lifts off freely.
- **Sole:** unchanged below 4 mm, which covers the hot-glue cast zone to 3 mm, so the V1.21 molds fit. The nearest cut is 6.0 mm above the sole.
- **Toe screw boss:** kept. 0.9 mm3 of the CAD overlap was removed from its top; the 1.6 mm pilot is intact.

Guide and print gate: `guide/print/world/foot_left.stl` and `foot_right.stl` replace the source foot in the guide (`build_guide_data.py`, `ia_lib.WORLD_FILE`). The gate passes, and the ankle-foot pair overlap is now 0 on both legs. Release: V1.22 Yellow plate (`guide/print/release-V1.22/`, delivery `~/Downloads/zhengxia_MicroDuck_V1.22/`), together with the split ankle (`print/ankle-split-20261019/`): the same socket seats on the new base plus side with the same play (`ankle-split-check.json` footSeat). Same pose as the stock feet, so the slicer again puts support under the sole edge where it curves up off the bed (about 1,200 mm2 of overhang below 4 mm, the rest at the socket ledges). Break it off and sand the scars on the curve smooth before a hot-glue cast.

## Fitting

1. Take the old foot off once. If an M2 x 6 sits in the countersunk hole at the toe, take it out. Hold the orange bracket, not the leg or the servo, and rock the foot off. The old foot may crack.
2. Slide the new foot straight up onto the bracket by hand.
3. Drive the M2 x 6 through the bracket's toe hole into the foot boss. Tighten until the head is flush in its countersink; it is a self-tapping thread in PLA.
4. If the foot does not slide on, sand the foot's socket walls a little and try again. Never press it on or pull it on with the screw.

Regenerate:

```bash
/tmp/microduck-cad-venv/bin/python foot_slipfit.py
```

It writes the STLs, which are gitignored, and `slipfit-check.json`. It takes about 2 minutes under the bounded runner.
