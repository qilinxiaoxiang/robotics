#!/bin/zsh
# spk2 diagnosis: find the training mouth actuator setting whose jaw angle over the close (phase 0.36-0.45) matches the
# runtime sim's XL330 jaw (runtime traces: 20.2, 17.4, 11.1, 3.5, -1.6 deg at 0.36, 0.38, 0.40, 0.42, 0.45), iteration-590
# ONNX, s = 0, ball, 16 envs, Mac mini CPU. The runtime jaw kp/effort (0.55 N m/rad, 0.0549 N m) with more damping.
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
S=/private/tmp/claude-501/-Users-xiangzheng-code-robotics/f1c031c9-315e-4562-8a86-dcbcac4d6fa0/scratchpad/spk2vol
zsh $T/spk2diag_mini.sh push $S/p600.onnx $S/start.onnx > /dev/null 2>&1
C=(--scale 0 --num-envs 16 --steps 150 --seed 1 --jaw-kp 0.55 --jaw-effort 0.0549)
for D in 0.03 0.06 0.10; do
  zsh $T/spk2diag_mini.sh probe jawfit_d$D --policy /tmp/spk2diag/p600.onnx --label jawfit_d$D $C --jaw-damping $D
done
echo "ALL DONE $(date +%H:%M:%S)"
