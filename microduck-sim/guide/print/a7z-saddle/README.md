# A7Z roof saddle (D-022, 2026-10-22)

The Radxa Cubie A7Z leaves the head (closed-head soak: 85 C in 5 min, both clusters at 416 MHz, resets) and sits in a
printed saddle on the torso roof over the V1.9 rear pack, with a 15 x 15 x 5 mm copper heatsink on the A733 and a
30 x 30 x 8 mm 5 V fan in the lid. Concept comparison, balance sweep and the first head sweep: `../a7z-slice-20261022/`.

## Files
- `build_saddle.py`: the geometry (every number in its docstring); run under the bounded runner:
  `python3 build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py --seconds 500 --max-mib 2048 --report guide/print/a7z-saddle/build/bounded-report.json -- /tmp/microduck-cad-venv/bin/python guide/print/a7z-saddle/build_saddle.py`
  (about 2 s). Writes `build/saddle_body-world.stl`, `build/saddle_lid-world.stl`, the bought parts in the saddle pose
  (`build/<name>-world.stl`, remapped from `../a7z-head/a7z_parts/` through the board frame), `build/build.json`
  (parameters, part bounds, fit checks, screws, wall allowances) and `build/pins.json` (header pin tops for the routes).
- `to_guide_world.py`: copies the parts into `guide/print/world/` (`saddle_body.stl`, `saddle_lid.stl`, `sd_*.stl`) and
  records their sha256 in `guide-world.json`.
- `render_views.py` (`~/.venvs/microduck-dyn/bin/python`): `renders/saddle.png`, four views on the as-built model at HOME.
- `head_sweep.py` (microduck-dyn): neck/head joint sweep of the head meshes against the saddle outline; `head_sweep_final.out`
  is the run on the released outline (`-45 -34.4 42 -5 34.4 74`): HOME clearance 25.1 mm, 105 of the 633 trained-range poses
  that clear the existing parts hit the saddle (neck forward, head pitched up) — a software keep-out in walk_brain when fitted.
- `stl_clean.py`: makes the manifold3d exports trimesh-watertight (sliver triangles removed with the neighbour split at the
  T-vertex, pinch edges split at the vertex fans); `build_saddle.py` runs it on the two prints before export, the release
  pipeline's load_mesh needs it.
- `route_check_saddle.py`: the saddle-era cable routes in `guide/content/routes.json` (torso and head wires to the header
  pins, fan lead, camera USB, antenna pigtail) checked at 0.25 mm against the guide solids; `--write` regenerates the
  pin tails from `build/pins.json` (not idempotent on pi-lead's anchor; after a board move, shift the drop columns by hand).
- `balance/`: `make_manifest.py` (saddle manifest from the as-built mass manifest), `run_balance.sh` (walk x3, stand61,
  open-loop stand with `firmware/mac/brain_sim_check.py`), results `balance/saddle-*.json`.
- `build/wall_check.out`: `wall_check.py` on both prints. The lid passes. The body's only thin regions are the wall feet,
  wedges where the vertical outer face meets the shell's sloping roof seat; they are listed as `thinWallAllowances` in
  `build.json` for the release rows.

## Board position
Header edge x -42.8 (0.6 off the rear wall inner face), pin-1 end at -y, USB-C/HDMI edge x -12.8. Moved 0.3 mm forward
on 2026-10-22 after the route check: the AC019 strip on the rear wall ends at |y| 21 inside the Dupont housing span, so
its 1.13 mm pigtail runs between the wall and the housings (1.56 mm, 1.26 over the strip) to |y| 25.4 and on to the IPEX
socket. The floor passage (x -21..-5, |y| <= 16) runs out under the front wall as a 32 x 4.5 mm slot: the neck bundle
leaves the roof opening forward to the neck through it (the wall above is a bridge printed on support).

## Release and gate
`../release-V1.29/` (scripts/run_v129.sh: manifest, prepare, both slices, reviews, native review, package, verify, parts
sheet, delivery folder). Body upright with the domed floor on tree support (2.3 mm2 own contact, no_brim), lid upside
down on its plate; X1C 1h34m 29.9 g, Elegoo 1h41m 30.4 g. Print gate 2026-10-22 passed with chapter 7 of the guide
(`guide/content/interference-audit/gate-receipt.json`); the card goes in through the +Y wall slot after the board, the
USB-C plug drops into the 10 mm gap before the neck and goes back through the notch, the lid comes in from behind
under the head.

## Fit checks (build.json `checks`)
Zero overlap between the body and the shells, rear pack, rear box frame and lid, IMU board, OpenRB, torso clip, neck ring
and the head parts at HOME; zero between the body/lid and the board, its components, the copper, fan, housings, antenna
and the USB-C plug. Fan to copper 8.7 mm, fan to Dupont housings 1.3 mm (the fan is in front of the housings, so the
wires leave upward behind it), roof-screw heads 0.65 mm under the microSD socket.
