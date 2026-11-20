#!/bin/zsh
# Round 3 pre-launch chain on the Mac mini: the incentive audit of universal5t at the three loads, the gate record,
# then the teacher smoke with the anchor from each start policy. One job at a time (ts3_audit.sh, mirror lock).
#   zsh train/ts3_prelaunch.sh <tag>
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
TAG=$1
zsh $T/ts3_audit.sh push
for LD in none full nobatt; do
  zsh $T/ts3_audit.sh gate $LD $TAG
done
python3 $T/audit_gate.py record universal5t $T/out/audit_${TAG}_full.json $T/out/audit_${TAG}_nobatt.json $T/out/audit_${TAG}_none.json || true
python3 $T/audit_gate.py record universal5 $T/out/audit_${TAG}_full.json $T/out/audit_${TAG}_nobatt.json $T/out/audit_${TAG}_none.json || true
zsh $T/ts3_audit.sh smoke 3 64
echo PRELAUNCHDONE
