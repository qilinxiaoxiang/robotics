#!/usr/bin/env bash
# After an A7Z hang or power cut, once it answers again: copy the flight recorder, the thermal log, the newest brain
# logs and brain stdout captures (*.out), the journal of the last three boots and the watchdog/lockup settings to the
# Mac, then print how each boot ended (blackbox_report.py).
#
#   bash a7z_blackbox_collect.sh [OUT]     (default OUT ~/duck-blackbox/collected/<Mac time>; A7Z_HOST=a7z)
set -euo pipefail
HOST=${A7Z_HOST:-a7z}
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${1:-$HOME/duck-blackbox/collected/$(date +%Y%m%d-%H%M%S)}
mkdir -p "$OUT/blackbox" "$OUT/brain" "$OUT/journal"
quiet() { grep -v -E "quantum|store now|upgraded" || true; }

rsync -a "$HOST:duck-logs/blackbox/" "$OUT/blackbox/" 2>&1 | quiet
rsync -a "$HOST:duck-logs/thermal.log" "$OUT/" 2>&1 | quiet || true
for f in $(ssh "$HOST" 'ls -t ~/duck-logs/duck_wired_log_*.jsonl | head -3' 2>/dev/null | quiet); do
  rsync -a "$HOST:$f" "$OUT/brain/" 2>&1 | quiet
done
for f in $(ssh "$HOST" 'ls -t ~/duck-logs/*.out ~/*.out /tmp/*.out 2>/dev/null | head -3' 2>/dev/null | quiet); do
  rsync -a "$HOST:$f" "$OUT/brain/" 2>&1 | quiet
done
ssh "$HOST" 'cat /proc/cmdline; sysctl kernel.watchdog_thresh kernel.hung_task_timeout_secs vm.dirty_expire_centisecs 2>&1;
  for w in /sys/class/watchdog/watchdog*; do echo "$w $(cat $w/identity $w/timeout 2>/dev/null | tr "\n" " ")"; done;
  systemctl show -p RuntimeWatchdogUSec' > "$OUT/journal/settings.txt" 2>/dev/null || true
ssh "$HOST" 'sudo -n journalctl --list-boots --no-pager' > "$OUT/journal/boots.txt" 2>/dev/null || true
for b in -1 -2 -3; do
  ssh "$HOST" "sudo -n journalctl -b $b -o short-monotonic --no-pager" > "$OUT/journal/boot$b.txt" 2>/dev/null || true
done
ssh "$HOST" 'sudo -n dmesg | grep -m1 -o "boot-reason: [A-Z-]*"' > "$OUT/journal/this-boot-reason.txt" 2>/dev/null || true
echo "collected into $OUT ($(du -sh "$OUT" | cut -f1)); this boot: $(cat "$OUT/journal/this-boot-reason.txt")"
python3 "$HERE/blackbox_report.py" "$OUT/blackbox" --boots 3
