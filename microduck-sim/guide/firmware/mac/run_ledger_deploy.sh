#!/bin/bash
# Install the run ledger on the Mac mini: copy run_ledger.py, the scorecard and the sim code it replays with, the
# change list (the Mac mini copy has no git), and a launchd job that runs `run_ledger.py tick` every 5 minutes.
# Checks that the job is loaded, one tick ran and the page is served by the phone remote at :5180/runs/.
#   ./run_ledger_deploy.sh
set -euo pipefail
cd "$(dirname "$0")"
MAC_REL=guide/firmware/mac
SIM=code/robotics/microduck-sim
URL=http://today.tailfc7c94.ts.net:5180/runs/index.html
LABEL=com.shawnxiang.microduck-runledger
python3 run_ledger.py changes
cd ../../..   # microduck-sim
rsync -aR --exclude __pycache__ --exclude 'scorecard-20261109/out' \
  ./$MAC_REL/run_ledger.py ./$MAC_REL/run-ledger-changes.json ./$MAC_REL/brain_sim_check.py ./$MAC_REL/walk_brain.py \
  ./$MAC_REL/walk_wired.py ./$MAC_REL/hold.py ./$MAC_REL/tether.py ./$MAC_REL/scorecard-20261109 \
  ./hardware-design-20260912/whole-robot-20260912/dynamics/realgap-20261014/static_gap.py \
  ./hardware-design-20260912/whole-robot-20260912/dynamics/asbuilt-20261015/asbuilt.config.json \
  "mac-mini:$SIM/"
PY=$(ssh mac-mini 'command -v python3')
ssh mac-mini "mkdir -p ~/Library/LaunchAgents ~/duck-walks && cat > ~/Library/LaunchAgents/$LABEL.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array>
    <string>$PY</string><string>/Users/shawnxiang/$SIM/$MAC_REL/run_ledger.py</string><string>tick</string>
  </array>
  <key>StartInterval</key><integer>300</integer>
  <key>RunAtLoad</key><true/>
  <key>Nice</key><integer>10</integer>
  <key>EnvironmentVariables</key><dict><key>PATH</key><string>/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin</string></dict>
  <key>StandardOutPath</key><string>/Users/shawnxiang/duck-walks/ledger-launchd.out</string>
  <key>StandardErrorPath</key><string>/Users/shawnxiang/duck-walks/ledger-launchd.err</string>
</dict></plist>
EOF
ssh mac-mini "launchctl bootout gui/\$(id -u)/$LABEL 2>/dev/null; launchctl bootstrap gui/\$(id -u) ~/Library/LaunchAgents/$LABEL.plist"
for i in $(seq 720); do
  ssh mac-mini 'test -s ~/duck-walks/ledger-runs.jsonl' && break; sleep 5
done
ssh mac-mini "launchctl print gui/\$(id -u)/$LABEL | grep -E 'state|last exit' ; tail -1 ~/duck-walks/ledger-runs.jsonl"
for i in $(seq 20); do curl -s -m 3 -o /dev/null "$URL" && break; sleep 1; done
curl -s -m 5 "$URL" | grep -q "MicroDuck 动作记录" || { echo "FAIL: page not served at $URL"; exit 1; }
echo "deployed: $URL"
