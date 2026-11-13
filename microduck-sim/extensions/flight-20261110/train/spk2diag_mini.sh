#!/bin/zsh
# spk2 lateral-miss diagnosis on the Mac mini (never the MacBook): the training-env close-step probe
# (microduck_rl-grasp/cmu/grasp/spk2diag_probe.py) on CPU, one job at a time behind other sessions' sims (mini.sh).
#   zsh train/spk2diag_mini.sh push POLICY...          mirror the grasp code (mini_seepick.sh push) and copy policies
#                                                     to the mini's /tmp/spk2diag/
#   zsh train/spk2diag_mini.sh probe NAME ARGS...      spk2diag_probe.py ARGS --out /tmp/spk2diag/NAME.json, fetched
#                                                     to train/out/spk2diag/NAME.json (policy paths: /tmp/spk2diag/<file>)
set -e
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
MIRROR=code/flight-train-mirror/robotics/microduck-sim/microduck_rl-grasp
SSHO=(-n -o ServerAliveInterval=15 -o ServerAliveCountMax=4)
mkdir -p $T/out/spk2diag $T/logs
case "$1" in
  push)
    shift
    zsh $T/mini_seepick.sh push
    ssh mac-mini "mkdir -p /tmp/spk2diag"
    for f in "$@"; do rsync -a "$f" mac-mini:/tmp/spk2diag/; done
    ;;
  probe)
    NM=$2; shift 2
    zsh $T/mini.sh run true
    timeout -k 15 700 ssh $SSHO mac-mini "cd $MIRROR && timeout 600 .venv/bin/python cmu/grasp/spk2diag_probe.py $* --out /tmp/spk2diag/$NM.json > /tmp/spk2diag/$NM.log 2>&1; echo exit \$? >> /tmp/spk2diag/$NM.log" || true
    timeout -k 5 90 scp -q -o ServerAliveInterval=15 mac-mini:/tmp/spk2diag/$NM.log $T/logs/spk2diag_$NM.log || true
    timeout -k 5 90 scp -q -o ServerAliveInterval=15 mac-mini:/tmp/spk2diag/$NM.json $T/out/spk2diag/$NM.json || true
    grep -E "^\[diag\]|Error|Traceback|^exit" $T/logs/spk2diag_$NM.log | cut -c1-900
    ;;
esac
