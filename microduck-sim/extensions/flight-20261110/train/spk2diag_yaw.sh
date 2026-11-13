#!/bin/zsh
# spk2 diagnosis: trunk yaw and hip yaw at the close step in the TRAINING env (s = 0, ball, 64 envs, Mac mini CPU),
# start policy against the iteration-590 trainer ONNX, to compare with the runtime traces (spk2diag_trace.sh).
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
S=/private/tmp/claude-501/-Users-xiangzheng-code-robotics/f1c031c9-315e-4562-8a86-dcbcac4d6fa0/scratchpad/spk2vol
zsh $T/spk2diag_mini.sh push $S/p600.onnx $S/start.onnx > /dev/null 2>&1
for P in start p600; do
  echo "== $P $(date +%H:%M:%S)"
  zsh $T/spk2diag_mini.sh probe yaw_s0_$P --policy /tmp/spk2diag/$P.onnx --label yaw_s0_$P --scale 0 --num-envs 64 --steps 150 --seed 1
done
echo "ALL DONE $(date +%H:%M:%S)"
