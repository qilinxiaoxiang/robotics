# MicroDuck print release V1.41

One Orange plate: `battery_backpack_cap` and `battery_hatch`. The V1.40 frame stays on the robot and is not reprinted.

## What changed

V1.41 redoes the battery hatch latch after the V1.40 bench test (2026-11-01).

- New hatch: two solid ears in roof pockets against pull-back, the V1.40 flap against lift, a solid block over the battery, and one lead window the size of a plug, open to the rear.
- New cap: the V1.40 opening and flap slot, plus two ear pockets in the roof.
- Frame, bars, switch, DFR1202 and battery are reused unchanged.

## Bench problems and fixes

Numbers (sizes, clearances, spring travel) come from `battery-quickswap-20261101/build-v2/build.json` once the CAD is built.

1. Problem: the 6 mm lead notches could not pass the battery's XT30 male (10.2 x 5.2 mm). Fix: one 17.65 mm wide window, open to the rear, that passes the XT30 and the JST-XH balance plug straight up (checked by sweeping both plug boxes).
2. Problem: the hatch fell off: the outside flap's bump slid straight out of its slot when the leads pulled the hatch back, and the 0.8 mm front lips slipped. Fix: two solid 1.55 x 4 x 2.35 mm ear stubs on the hatch plate sit in two pockets in the cap roof and stop pull-back after 0.15 mm; the front lips engage 1.0 mm; the V1.40 flap still holds against lift.
3. Problem: the 1 x 9 mm wedge did not hold the battery. Fix: a solid 10 x 8 mm block 0.3 mm above the battery top; Shawn adds 3M foam tape if the battery still moves. No leaf springs or tongues: PLA flexures do not survive on a walking robot (Shawn).
3. Problem: _to be filled from the bench test_. Fix: one plug-size lead window in the hatch, with the cap opening widened to match.

## Known fit boundary

Battery length is taken from the listing (57 mm), not measured. The ear pockets and the block are untested on a print.

## Inputs

- STLs: `guide/print/battery-quickswap-20261101/build-v2/battery_backpack_cap-world.stl`, `battery_hatch-world.stl`, `build.json`.
- The release slices the guide-world copies in `guide/print/world/`; the guide-world JSON (`back-plate/battery-backpack-v141/guide-world.json`, else the v140 one) must name the build-v2 bytes as their source, or `make_manifest.py` stops.
- Optional `cap_cuts_mm` in build.json (robot-frame boxes of the material removed from the V1.40 cap) lets new thin regions away from the cuts pass; without it only thin regions the V1.40 cap already had pass.

## Run

```
cd ~/code/robotics/microduck-sim/guide/print/release-V1.41
zsh scripts/run_v141.sh
```

Every job runs under the bounded runner (10 minute cap); logs are in `logs/`. Output: `PARTS-SHEET-V1.41.html`, `run/delivery-folder/`, and `~/Downloads/zhengxia_MicroDuck_V1.41/` (X1C, Elegoo and H2S files plus the plate picture).
