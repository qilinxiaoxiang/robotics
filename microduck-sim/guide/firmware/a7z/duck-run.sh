#!/bin/bash
# start the onboard MicroDuck brain (monitor mode, torque untouched); logs persist in ~/duck-logs
# Installed to ~/duck-run.sh on the A7Z by install_teleop.sh; the app's duck-command.py runs it as ~/duck-run.sh app<MMDD-HHMMSS>.
suf=${1:?suffix}
# ~/duck-policy, written by microduck_rl cmu/deploy/deploy_policy.py, names a gated policy set; absent = walk61 (the default)
models=$(cat ~/duck-policy 2>/dev/null)
[ -n "$models" ] && [ ! -f "$models/walk61.onnx" ] && { echo "duck-run: $models has no walk61.onnx" >&2; exit 1; }
# ~/duck-supply (bench = charger pack, battery = 2S pack), written by the phone remote's backpack switch; absent = auto
supply=$(cat ~/duck-supply 2>/dev/null); case $supply in bench|battery) ;; *) supply=auto;; esac
# a running brain is stopped first; the 1 s wait (its servo bus and log closing) only when there was one
pkill -f "^/home/radxa/.venvs/duck-policy/bin/python walk_wired.py" && sleep 1
mkdir -p ~/duck-logs
echo "{\"mode\": \"monitor\"}" > /tmp/duck_cmd.json
cd ~/rt/microduck-sim/guide/firmware/mac
setsid nohup /home/radxa/.venvs/duck-policy/bin/python walk_wired.py --port /dev/ttyAS2 --baud 500000 --imu-bus 7 \
  --supply $supply ${models:+--models "$models"} --log ~/duck-logs/duck_wired_log_$suf.jsonl > ~/duck-logs/duck_wired_$suf.out 2>&1 < /dev/null &
# the head camera is not started here: approach.py starts a7z_cam.py for its run and stops it after (heat, a7z_cam.py)
