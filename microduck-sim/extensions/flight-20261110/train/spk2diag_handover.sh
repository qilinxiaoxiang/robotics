#!/bin/zsh
# spk2 diagnosis: the runtime hands seepick stand61's last action (obs 34-47 non-zero at the first tick); training
# resets it to 0. Training env, s = 0, ball, 64 envs, Mac mini CPU, start policy against the iteration-590 ONNX, with
# the runtime seed-3 handover vector (eval/pkt_trace_bend4_s3.jsonl first row) in the first observation.
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
S=/private/tmp/claude-501/-Users-xiangzheng-code-robotics/f1c031c9-315e-4562-8a86-dcbcac4d6fa0/scratchpad/spk2vol
PA="0.0013 -0.2835 -0.1459 -0.1574 0.0061 -0.0097 -0.0064 0.0409 -0.0689 0.0787 0.2391 0.106 0.2393 -0.0095"
zsh $T/spk2diag_mini.sh push $S/p600.onnx $S/start.onnx > /dev/null 2>&1
for P in p600 start; do
  echo "== $P $(date +%H:%M:%S)"
  zsh $T/spk2diag_mini.sh probe hand_s0_$P --policy /tmp/spk2diag/$P.onnx --label hand_s0_$P --scale 0 --num-envs 64 --steps 150 --seed 1 --prev-act ${=PA}
done
echo "ALL DONE $(date +%H:%M:%S)"
