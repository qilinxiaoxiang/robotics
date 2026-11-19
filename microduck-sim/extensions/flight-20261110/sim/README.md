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
- `policy_legs.py`, `fullseq_runs.sh`, `heldcheck.py`, `fullseq_falls.py`, `fullseq_trace.py`, `render_full_videos.sh`:
  the full sequence with the leg policy (next section).
- `render_hd.py`, `render_full_videos_hd.sh`, `outcome_match.py`: 1080p 60 fps presentation renders of the three full
  clips (`out/pack_visual_hd/`, studio look, caption, posters, combined cut). Drawing only: flight.py's `--video-size`,
  `--video-fps`, `--video-look`, `--video-caption`, `--cam-smooth`, `--cam-fovy`, `--cam-dz` are optional and the video
  without them is byte-identical to before; the script stops unless each run's row equals `out/pack_visual/full_*.json`.
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

## Full sequence with the leg policy (`flight.py --legs`)
The leg policy fq2 1999 (`train/policy/walk61.onnx` = `stand61.onnx`, read only) runs through the runtime's Brain with
the probe's real-condition flags (`brain_sim_check.py --volt 7.6 --drop 0.036`, sensor and action delay one tick,
policy from the first tick) inside flight.py's physics loop. The flight controller and the Brain never exchange data
except the hand-over commands below, as walk_wired.py and ArduPilot would on the robot.

- `--legs held` (default): the legs at the trimmed open-loop stand pose, KP 400, as every row before 2026-11-11.
  `heldcheck.py` reruns ARE_nominal (3 scenarios x 3 seeds) in this mode: all 45 fields of every row equal
  `out/batch` (`out/heldcheck/heldcheck.json`). This mode cannot stand once the fans stop (the hover fall at 11.5 s).
- `--legs policy`: the policy at zero command through the whole flight. Airborne it flails (actions up to 4.5 rad)
  and throws the duck: 4 of 27 airborne successes, 0 full (`out/fullseq_policy`). Not usable.
- `--legs handover` (used for the clips): policy on the ground until the estimated feet height exceeds 3 cm in the
  climb (`--takeoff-handover lift`), then Brain stand mode (2 s ramp to the Brain stand pose, KP_DEFAULT) through the
  flight, then back to the policy when the estimated feet height in the land phase drops below 3 cm
  (`--handover-h 0.03`, the landing probe's release height: policy running, released 2-3 cm up). Both switches are
  plain control-file commands; the runtime needs only the rangefinder height from the flight controller.
  Variants: `--air-pose held` (stand mode with the -4 deg ankle trim) gives the same total at nominal plus 90 %
  (15 of 18) but its failures are falls over 45 deg after the disarm (nominal 7/9, 90 % 8/9), where the default's
  are sits onto a nacelle at about 21 deg (nominal 9/9, 90 % 6/9); `--air-legs monitor` (last policy goals frozen)
  is worse (nominal 3/9, 90 % 2/9).

Success fields: `airborne_success` lift-off to first foot touchdown on the wanted surface, upright, slower than
0.8 m/s, nothing hit before it. `success` (mission) landed, disarmed and upright at the old mission end.
`full_success` airborne part ok, disarmed, then still standing 5 s after the disarm: no tilt over 45 deg at any time
(brain_sim_check's fall rule), feet on the wanted surface, no nacelle on the surface, end tilt under 25 deg. A run
with `--legs` other than held continues 6 s past the disarm. `batch.py` summaries count these as `airborne_success`,
`mission_success` and `full_success`.

## Why 80 % thrust fails here (2026-11-11, `out/t80_diag/`)
Cause: the stand-in controller's thrust model, not lack of thrust or pitch authority. `t_max_est` (flight.py) is the
vendor point scaled by bus voltage only, so at `--thrust 0.8` every commanded newton delivers 0.8 N. Held-leg trace
`base80__hover__s0` (`--log-ctl`, columns 26-36): the 1.6 x weight take-off collective delivers 1.2 to 1.3 x, lift-off at
1.0 s; then the altitude loop's feed-forward commands 1.00 to 1.05 x weight and 0.85 x arrives. The duck peaks 12 cm up
at 1.4 s and sinks back; the climb integrator (`ki_vz` 1.5, climb-rate demand only 0.29 m/s once the 0.30 m target is
reached) grows from 0.06 to 0.4 by 1.95 s against the about 1.6 it needs (1.25 x weight commanded). Back on the floor with the fans carrying the
whole weight, the unloaded feet skid backwards, the position loop leans up to 16 deg against it, and the duck tips
(3.8 s). Mixer saturation: 0.28 s in the take-off ramp, 0.04 s in the air, 1.5 s after the floor re-contact.
table_up survives only because its target keeps rising (demand clipped at 0.6 m/s), so the integrator winds twice as
fast and the sink stops 5 cm above the floor. 90 % has half the deficit and a faster lift-off.
Test (one knob, `--ctl-thrust-known`, default 1.0 = all earlier rows; default reruns of ARE_nominal seed 0, all three
scenarios, equal `out/batch` in every old field): `--thrust 0.8 --ctl-thrust-known 0.8` airborne 9 of 9 with held legs (saturation 0.35 to 0.42 s,
take-off pitch excursion 6 deg) and 9 of 9 airborne, 8 of 9 full with `--legs handover` (published row: 1 of 9 and 0).
Sweep, held legs, airborne of 9: model unknown 85 % 9, 75 % 0; model known 70 % 9, 60 % 0 (thrust-to-weight 1.21, the
take-off collective cannot be met). `--ctl-thrust-known 0.87` at 80 % (the feed-forward ArduPilot would have with its
hover throttle capped at 0.6875, `AP_MotorsMulticopter.h`) airborne 9 of 9.
Hover thrust fraction needed: 0.56 nominal, 0.65 at 90 %, 0.75 at 80 %. ArduPilot's MOT_THST_HOVER range is 0.125 to
0.6875 (parameter list, ardupilot.org/copter/docs/parameters.html), so below about 85 % of vendor thrust the learned
hover value saturates and its integrator must carry the rest.

## What the simulation cannot show
Real EDF thrust and inlet losses next to the body (one vendor point per fan is the only data), ground effect and
recirculation near the floor and table, heat, real ArduPilot tuning and land detector, servo behaviour beyond the BAM
XL330 model, and MuJoCo soft-contact impact peaks (the g values depend on contact stiffness). The leg hand-over
assumes walk_wired.py gets the flight controller's rangefinder height over MAVLink with negligible delay; that link
does not exist yet.
