# V1.9 incremental release: Black plate with the neck pitch ring and shims

One Black plate, printed instead of the V1.8 Black plate (which was not yet printed): the V1.8 eye trim and rear pack cover, unchanged in source and pose, plus the 4.9 mm neck pitch ring (`../world/neck_pitch_ring.stl`) that replaces the 4 mm ring from the 10/1 batch under the head-yaw servo ID13, and two optional shims, 1 mm and 2 mm, with the ring's bore and outside (`../neck-ring/make_shims.py`, `shims.json`). The shims stack on the shoulder under the ring when the printed stack still rattles; Shawn judged the physical gap at least 2 mm against 0.91 mm in the model. They are not drawn in the guide model, where the 4.9 mm ring already closes the gap.

The 4 mm ring sat on the pitch bracket's 18 mm shoulder with its top face 0.91 mm below the ID13 case, and no part surrounds its outside, so it floated and carried no load. The hip-yaw rings, which work, touch both faces. At 4.9 mm the ring touches the bracket and the case (`../neck-ring/thicken_ring.json`). The head-roll rings on the yaw fork stay at 4 mm: the lower head shell and the jaw support close around them.

- `manifest-V1.9.json` from `scripts/make_manifest.py`; profiles and baseline from V1.8.
- `orientation-check.json`: all three flat, rank 1 of 8; the ring as printed in the 10/1 batch.
- `run/`: native slices, review receipt, `verify-release.json` (RELEASED, 2 files). Top layer Z 4.9 mm on both machines.
- `review/`: first layer 132.5 to 132.6 mm2 per part, one island each, no support, on both machines. `superseded-run-20261012-ring-only/` is the ring-only run before the shims.
- Delivered as `~/Downloads/zhengxia_MicroDuck_V1.9_2-files.zip`. V1.8 Yellow, White and Orange stay as released. `superseded-run-20261012-ring-only/` and `superseded-run-20261012-ring-and-shims/` are the earlier V1.9 runs without the V1.8 Black parts.

Physical check: after the four M2 x 6 horn screws, the ring does not rattle up and down and ID13 still turns by hand.
