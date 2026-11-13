#!/bin/zsh
# spk2 diagnosis: jaw angle and lip height at phases 0.36-0.45 of the close in the TRAINING env (s = 0, ball, 32 envs,
# Mac mini CPU), to set beside the runtime traces (spk2diag_trace.sh): start policy and iteration-590 ONNX with the
# training mouth, and the iteration-590 ONNX with the runtime jaw (kp 0.55 N m/rad, 0.0549 N m).
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
S=/private/tmp/claude-501/-Users-xiangzheng-code-robotics/f1c031c9-315e-4562-8a86-dcbcac4d6fa0/scratchpad/spk2vol
zsh $T/spk2diag_mini.sh push $S/p600.onnx $S/start.onnx > /dev/null 2>&1
C=(--scale 0 --num-envs 32 --steps 150 --seed 1)
zsh $T/spk2diag_mini.sh probe jaw_s0_p600 --policy /tmp/spk2diag/p600.onnx --label jaw_s0_p600 $C
zsh $T/spk2diag_mini.sh probe jaw_s0_start --policy /tmp/spk2diag/start.onnx --label jaw_s0_start $C
zsh $T/spk2diag_mini.sh probe jaw_s0_p600_rtjaw --policy /tmp/spk2diag/p600.onnx --label jaw_s0_p600_rtjaw $C --jaw-kp 0.55 --jaw-effort 0.0549
echo "ALL DONE $(date +%H:%M:%S)"
