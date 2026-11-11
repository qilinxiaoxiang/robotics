#!/bin/zsh
# Re-render the fq2 1999 walk and landing clips with the flight pack drawn, plus the same episodes without it (proof that
# the drawn pack changes nothing), and one flight-sim take-off clip with a still. Run in the flight-20261110 folder on
# the Mac mini, one simulation at a time:  zsh sim/mini.sh run 'zsh sim/render_pack_videos.sh'
set -e
P=sim/out/pack_visual
mkdir -p $P train/video
$PY sim/pack_visual.py --manifest train/manifests/flightpack-nominal.json --out sim/out/visual/flightpack-nominal.json
# walk (as the original clip: case walk, seed 0, key frame at 10 s)
$PY train/flight_video.py --models train/ckpt/fq2_1999 --manifest train/manifests/flightpack-nominal.json --case walk \
  --seed 0 --out $P/fq2_1999_walk_nopack > $P/fq2_1999_walk_nopack.json
$PY train/flight_video.py --models train/ckpt/fq2_1999 --manifest sim/out/visual/flightpack-nominal.json --case walk \
  --seed 0 --out train/video/fq2_1999_walk_pack > $P/fq2_1999_walk_pack.json
# landing (as the original clip: case stand, landing release, key frame at 1 s)
$PY train/flight_video.py --models train/ckpt/fq2_1999 --manifest train/manifests/flightpack-nominal.json --case stand \
  --landing --key-t 1 --seed 0 --out $P/fq2_1999_landing_nopack > $P/fq2_1999_landing_nopack.json
$PY train/flight_video.py --models train/ckpt/fq2_1999 --manifest sim/out/visual/flightpack-nominal.json --case stand \
  --landing --key-t 1 --seed 0 --out train/video/fq2_1999_landing_pack > $P/fq2_1999_landing_pack.json
# flight sim take-off (ARESWEI point, calibrated trim as in the batches), camera on the duck, still at 1.0 s
$PY sim/flight.py --scenario hover --case nominal --seed 0 --fan areswei --com-est true --ground-pitch level \
  --takeoff-twr 1.6 --takeoff-ramp 0.1 --out $P/takeoff_hover.json --video $P/takeoff_hover.mp4 \
  --cam-dist 0.9 --cam-az 135 --cam-el -15 --cam-follow --still-t 1.0
echo RENDERDONE
