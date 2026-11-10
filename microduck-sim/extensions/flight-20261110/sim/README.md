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
Real EDF thrust and inlet losses next to the body (vendor point 950 g at 16.2 V is the only data), ground effect and
recirculation near the floor and table, heat, real ArduPilot tuning and land detector, servo behaviour beyond the BAM
XL330 model, and MuJoCo soft-contact impact peaks (the g values depend on contact stiffness).
