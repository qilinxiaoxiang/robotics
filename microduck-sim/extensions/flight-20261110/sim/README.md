# Flight-pack simulation (MicroDuck + four-EDF pack)

MuJoCo 3.10.0 on the as-built duck (official scene + battery-20261104 manifest) with the pack as rigid point masses on
`trunk_base`. All heavy runs go to the Mac mini through `sim/mini.sh` (MacBook swap was nearly full).

## Files
- `manifest.py` builds the pack parts (CAD v6 geometry, slicer grams) and writes `out/manifest_pack_<variant>.json` plus `out/mass_report.json`.
- `flight.py` flight sim: fan model (quadratic thrust, first-order lag, reaction torque, CW/CCW), two-pack battery sag,
  ArduPilot-style cascade stand-in (attitude PD+I, position/altitude loops, priority mixer), sensor noise and delay,
  MTF-01 rangefinder ray with table-edge re-basing, mission state machine, table scene, nacelle collision boxes.
  The controller is a stand-in for ArduPilot, not ArduPilot.
- `showlog.py` prints a `--log` npz. `collect.py` writes `out/results.json`.
- `hold_probe.sh` held stand pose (fans off) over hip/ankle trims. `ground_probe.sh` lift-off and touchdown variants.
- `walk_probe.sh` walk61/stand61 through `microduck_rl/cmu/mac/brain_sim_check.py` with and without the pack.
- `drift_tests.sh`, `drift_tests2.sh`, `drift_tests3.sh` take-off drift, one knob per test; `diag_com.py` true model COM vs the
  mixer's estimate; `authority.py` roll/pitch/yaw authority and margins (`out/authority.json`).
- `batch.py` airborne perturbation batch (`--air`: start hovering, trunk level) -> `out/batch*/summary.json`. `--fan areswei`
  in flight.py switches the vendor point to the ARESWEI HDS001 (980 g, 40 A at 16.8 V); default is the QX QF2611 point.
  `--lean-max` sets the position loop's lean limit (default 20 deg); `batch.py --force` reruns existing result files.
  `walk_case.py` fan currents use the QX point; multiply by about 1.18 for the ARESWEI (ratio of the two hover currents).
- `landing_tests.sh` crouch hold probe and landings with the fans carrying part of the weight while the legs settle.
- `walk_case.py` brain_sim_check plus partial thrust with an attitude loop, action scaling, crouch start, shoves, forward
  force; `walk_batch.py` the zero-training ground options; `partc.py` thrust-assisted walking (Part C).
- `pack_visual.py` the drawn pack: `visual_parts` (CAD world STLs read by path, release colours) in the visual copies
  `out/visual/<manifest>`; the loader (`cmu/model/visual.py::apply_manifest_visuals`, called by evaluate_delay.load)
  adds them as visual geoms (no mass, no contact). `flight.py` uses the visual copy; the `out/manifest_pack_*.json`
  files stay without visual_parts because copies of them load in mirrors that do not hold `cad/build`.
  `pack_visual_check.py` proves the physics unchanged and renders stand-pose stills; `render_pack_videos.sh` renders the
  fq2 clips with and without the pack and a take-off clip (`out/pack_visual/`, `train/video/*_pack*`).
- `thrust_assist_literature.md` published work on thrust-assisted walking and the ArduPilot interface questions.

## Reproduce
```
zsh sim/mini.sh setup        # once (adds pyserial too: uv pip install pyserial)
python3 sim/manifest.py      # local, seconds
zsh sim/mini.sh push
zsh sim/mini.sh run 'zsh sim/hold_probe.sh'
zsh sim/mini.sh run 'zsh sim/ground_probe.sh'
zsh sim/mini.sh run 'zsh sim/walk_probe.sh'
zsh sim/mini.sh run '$PY sim/flight.py --scenario hover --spool-down 0.6 --flare-h 0 --out sim/out/cut/hover_nominal.json --video sim/out/cut/hover_nominal.mp4'
zsh sim/mini.sh run '$PY sim/flight.py --scenario cut --cut-alt 1.0 --out sim/out/cut/cut10.json'
zsh sim/mini.sh pull
python3 sim/collect.py
```

## What the simulation cannot show
Real EDF thrust and inlet losses next to the body (one vendor point per fan is the only data), ground effect and
recirculation near the floor and table, heat, real ArduPilot tuning and land detector, servo behaviour beyond the BAM
XL330 model, and MuJoCo soft-contact impact peaks (the g values depend on contact stiffness).
