# Two-half ankle (release 2026-10-20, V1.24)

Shawn, 2026-10-20, on the printed V1.22 split ankle: the base and side look fragile, their supports must be removed with
care, and the two pairs of screw posts catch the servo wire. He never fitted the two M2 x 8 side screws and the ankle
worked. So each ankle is now the stock one-piece orange bracket cut in half at mid shaft, each half held by the foot. No
new screw, post, tab or slot.

- **Outer half:** the stock bracket for local z < -16.1. It is the plate on the servo horn, with the four M2 x 4 as
  before, and half of the foot block. It replaces the bracket (stock object 20/22) and the V1.22 base.
- **Inner half:** the stock bracket for local z > -15.9. It is the plate whose d15 pocket runs on the V1.22 black
  sleeve, and the other half of the foot block. It replaces the V1.22 side.
  - The sleeve lip is raised to 1.2 mm, as in V1.22.
  - The pocket and lip bore have a 45 deg teardrop roof, so the half prints on its heel chamfer with no support in the
    pocket. On the robot the roof points toward the toe, 30 deg below horizontal, and spans from 75 deg below to 15 deg
    above horizontal on the toe side; straight down, under the robot's weight, the bore stays round. The two roof flats
    are tangent to the d15 bore, so the 14.6 mm sleeve can move 0.28 mm toward the roof tip against 0.20 mm elsewhere.
- **What holds them:**
  - The V1.22 slip-fit foot slides over both foot-block halves; its end walls keep the halves from moving apart.
  - The toe M2 x 6 TAP sits on the cut (the stock toe screw axis, local x 17.5, z -16), and its countersunk head bears
    on both halves (5.5 mm2 each).
  - The cut faces are 0.2 mm apart.

The V1.22 black sleeves and yellow slip-fit feet are reused unchanged.

## Check (`make_halves.py`, `halves-check.json`, both legs, PASSED)

These checks run against the audit solids of the current guide world (lower link, XL330, washer, slip-fit foot) and the
V1.22 sleeve.

- **Seated:** no overlap. The right outer half keeps the stock bracket's 0.137 mm3, 0.001 mm source slab against the servo.
- **Envelope:** the only new material outside the stock bracket is the lip ring (40 mm3). The teardrop removes 49 mm3.
- **Foot seat:** the same as on the stock bracket.
  - Play: left 0.15/0.18 mm along x, 0.15/0.19 mm along z.
  - Drop contact: 24.78 mm3, against 24.83 mm3 on the stock bracket.
  - The foot slides 15 mm straight down off both halves.
- **Capture:** either half moved 1 mm apart overlaps the foot by 107-113 mm3. Free travel is 0.15-0.19 mm.
- **Paths:**
  - With the foot off, the inner half slides 24 mm along the shaft, clear of everything.
  - With the inner half off, the link-servo-sleeve package lifts 30 mm straight out of the outer half.
  - Seated, the inner half lifts only 0.19 mm on the sleeve.
- **Walls:** the release wall check passes on all four halves (no thin region).

The script writes `STL/{side}-{outer,inner}-{local,world}.stl` (gitignored) and the guide/gate world files
`guide/print/world/ankle_{outer,inner}_{side}.stl`. `ia_lib.WORLD_FILE` and `content/build_guide_data.py` map the guide's
`ankle` and `ankle_cheek` keys to them. `content/steps.py` step `ankle-split` fits the two halves, and the print gate
checks its approach paths.

## Print poses and release

The print poses are in `poses/poses.md` and `poses/poses.json`. `release-V1.24/scripts/make_manifest.py` reads them.
The release is one Orange plate with the four halves (`guide/print/release-V1.24/`).
