#!/bin/zsh
# Full flight sequence clips with the pack drawn: leg policy standing, arm and spool, take-off, hover or table flight,
# landing, disarm, policy standing 6 s after the disarm (--legs handover, ARESWEI point, calibrated trim as in the
# batches, seed 0). Each clip gets a contact sheet (.png) and the last frame (_end.png). Run in the flight-20261110
# folder on the Mac mini, one simulation at a time:  zsh sim/mini.sh run 'zsh sim/render_full_videos.sh'
set -e
P=sim/out/pack_visual
mkdir -p $P
B=(--case nominal --seed 0 --fan areswei --com-est true --ground-pitch level --takeoff-twr 1.6 --takeoff-ramp 0.1
   --legs handover --cam-follow --cam-dist 1.6 --cam-el -14 --still-t -1)
for s in hover table_up table_down; do
  az=125; [[ $s == table_* ]] && az=55     # table scenarios: camera on the floor side, so the table never hides the duck
  timeout 600 $PY sim/flight.py --scenario $s $B --cam-az $az --out $P/full_$s.json --video $P/full_$s.mp4
done
echo RENDERDONE
