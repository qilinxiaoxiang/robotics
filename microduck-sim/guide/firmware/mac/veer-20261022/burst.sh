#!/bin/bash
# One veer test burst from the Mac: walk forward at vx 0.25 for 2 s on the A7Z brain, then print that burst's yaw.
#   bash burst.sh            one burst (robot must already be in walk at zero command, i.e. stand61, on the start mark)
#   bash burst.sh report N   yaw of the newest N bursts and the stance split over them, no motion
# Copies veer_check.py to ~/duck/ on the A7Z when it differs. Writes the command file atomically like the app bridge.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
VX=${VX:-0.25}
SECS=${SECS:-2}
rsync -a --checksum "$HERE/veer_check.py" a7z:duck/veer_check.py
if [ "${1:-}" != report ]; then
  pgrep_out=$(ssh a7z 'pgrep -f "python walk_wired.py" || true')
  [ -n "$pgrep_out" ] || { echo "walk_wired.py is not running on the A7Z: start it first (step 0)"; exit 1; }
  ssh a7z "echo '{\"mode\": \"walk\", \"vx\": $VX, \"vy\": 0, \"vtheta\": 0, \"for_s\": $SECS}' > /tmp/duck_cmd.json.t && mv /tmp/duck_cmd.json.t /tmp/duck_cmd.json"
  echo "burst sent: vx $VX for $SECS s"
  sleep $((SECS + 3))
fi
ssh a7z "python3 ~/duck/veer_check.py \$(ls -t ~/duck-logs/duck_wired_log_*.jsonl | head -1) --last ${2:-1}"
