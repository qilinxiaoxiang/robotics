#!/bin/bash
# Run the onboard MicroDuck brain in the foreground. First command: DUCK_START_MODE (default monitor, torque untouched
# until a command arrives); duck-brain.service sets stand, so the robot takes the open-loop stand pose at every boot
# (the brain waits for a fresh joint and IMU sample, then turns torque on at the present positions and ramps to STAND).
# Started at boot by duck-brain.service and by ~/duck-run.sh (the app's restart, monitor); installed to ~/duck-brain.sh by
# install_teleop.sh. Logs: ~/duck-logs/duck_wired_<suffix>.out and duck_wired_log_<suffix>.jsonl.
suf=${1:-boot$(date +%m%d-%H%M%S)}
mkdir -p ~/duck-logs
echo "{\"mode\": \"${DUCK_START_MODE:-monitor}\"}" > /tmp/duck_cmd.json
cd ~/rt/microduck-sim/guide/firmware/mac || exit 1
exec /home/radxa/.venvs/duck-policy/bin/python walk_wired.py --port /dev/ttyAS2 --baud 500000 --imu-bus 7 --supply bench \
  --log ~/duck-logs/duck_wired_log_$suf.jsonl > ~/duck-logs/duck_wired_$suf.out 2>&1 < /dev/null
