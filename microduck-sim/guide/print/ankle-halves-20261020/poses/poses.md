# Two-half ankle print poses (2026-10-20)

One print pose per part for the four halves made by `../make_halves.py` (left and right, outer and inner). The
machine-readable result is `poses.json`: per key the chosen `sourceToPrint` on the local STL (`../STL/*-local.stl`, sha256
recorded), bed contact, height, support per machine, the MUST faces still touched, the brim fields the release rows carry,
and the rejected poses. `decisions.json` holds the written reasons; `scripts/build_poses.py` assembles `poses.json` and
fails if a MUST face on support has no written explanation.

## Result

- **Outer halves:** the gusset end face on the bed (left local +x down, right -x down), as the V1.22 base. Bambu: every
  bearing and mating face clean. Elegoo: Orca's tree support reaches into the four d4.4 output-screw counterbores from the
  plate exterior (1.1 mm2 of the seat floors on the left, 9.7 mm2 on the right); pull the tips out with tweezers so the
  M2 x 4 heads sit flat.
- **Inner halves:** the stock heel chamfer (55 mm2) on the bed, the shaft flat. `make_halves.py` gives the d15 pocket and
  the d14 lip bore a 45 deg teardrop roof that points straight up in this pose, into the 11.7 mm thick toe-and-foot
  corner. Pocket wall, capture lip and lip bore: 0 mm2 on support and 0 mm of support inside them on both machines. The
  support stands under the foot-block arm (cosmetic). Bambu touches 0.8 mm2 of the cut face, which meets the other half
  across a 0.2 mm gap.
- **Brim:** the R1 brim (outer_only, 4 mm, gap 0.1). Outer rows carry `brimInsideHullAllowanceMm2` 5.0: Bambu loops
  2.4 mm2 of brim into the stock notch on the gusset end face (cut it out with a blade), the same notch as the V1.22
  bases. Inner rows carry `brimAlongSupportReason`: the arm's support stands on the bed beside the part and both slicers
  brim it too, so the pipeline judges only the part's own brim (2.7 mm on Bambu, trimmed by the support; 4.5 mm on Elegoo).

## Method

Each candidate was prepared and sliced alone on both machines with the V1.22 plate profiles through
`release_pipeline_v2.py` (`scripts/slice_poses.py`, every job under the bounded runner, log `logs/slice-plan.log`),
read back with the orientation study's `slice_readback.py`, and checked face by face with `scripts/face_support.py`
(a face rests on support when its centre lies within 1.0 mm in XY and 0 to 0.6 mm above a support toolpath midpoint;
support inside a cavity is toolpath length mapped back into the local cavity). The faces are named in `scripts/faces.py`:
outer MUST = motor mating face, four output seats, cut face; inner MUST = d15 pocket wall, capture lip, cut face.
`scripts/plot_layers.py` draws the first layer and the support side views.

## Rejected

- Outer, -x down (left): 7.6 mm2 of support on the motor face (Bambu), 7.8 mm2 on the output seats (Elegoo).
- Outer, +-z down: the motor face or the four seats face down onto support; -y down: no flat face under the foot block.
- Inner, +-x down (before the teardrop roof): 11-21 mm2 of the pocket wall on support and 197-766 mm of support inside the pocket.
- Inner, -z down (cut face on the bed): the plate's inner face overhangs 15 mm and its support fills the pocket (869 mm inside, the whole capture lip on support).
- Inner, exterior down: the 1.2 mm lip ring stands proud of the 7 deg exterior, so no flat face is lowest.
- Teardrop roofs on the outer half's output holes: on the hole beside the shaft the roof would point at the d5 centre
  aperture and leave 0.4 mm of wall (stock 1.3 mm).
