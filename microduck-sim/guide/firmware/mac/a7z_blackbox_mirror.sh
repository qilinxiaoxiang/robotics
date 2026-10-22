#!/usr/bin/env bash
# Live off-board copy of the A7Z records while a robot test runs: the flight recorder's kmsg.log and sys.jsonl of the
# CURRENT boot (pi/blackbox.py), the newest brain log (~/duck-logs/duck_wired_log_*.jsonl) and the newest brain stdout
# capture (*.out in ~/duck-logs, ~ or /tmp), all read from the A7Z page cache as written; plus the kernel ring itself
# (`dmesg -w`, one OUT/kernel-<Mac time>.log per connection), which needs no card at all, so a card stall that stops
# the recorder still shows its hung-task lines here.
#
#   bash a7z_blackbox_mirror.sh [OUT]      (default OUT ~/duck-blackbox/live; A7Z_HOST=a7z)
#
# Each remote file is copied under its own name and a reconnect resumes at the local size, so nothing is duplicated.
# Every 2 s each stream checks that it still follows the newest file (the current boot's for the recorder) and
# switches when not. Link losses and switches go to OUT/mirror-events.log with Mac time, which bounds the moment the
# A7Z stopped answering. The Mac is kept awake (caffeinate) while it runs. Runs until Ctrl-C.
set -u
if [ -z "${MIRROR_AWAKE:-}" ]; then MIRROR_AWAKE=1 exec caffeinate -i env MIRROR_AWAKE=1 bash "$0" "$@"; fi
HOST=${A7Z_HOST:-a7z}
OUT=${1:-$HOME/duck-blackbox/live}
mkdir -p "$OUT"
ev() { echo "$(python3 -c 'import datetime; print(datetime.datetime.now().isoformat(timespec="milliseconds"))') $*" >> "$OUT/mirror-events.log"; }
# one shared connection: the 2 s checks must not log in to the A7Z under test twice a second
SSH=(ssh -o BatchMode=yes -o ConnectTimeout=4 -o ServerAliveInterval=1 -o ServerAliveCountMax=3
     -o ControlMaster=auto -o "ControlPath=$HOME/.ssh/cm-blackbox-%r@%h:%p" -o ControlPersist=30 "$HOST")
BOOT8='$(tr -d - < /proc/sys/kernel/random/boot_id | cut -c1-8)'
# remote shell expressions that print the file each stream should follow now
NEWEST_KMSG="ls ~/duck-logs/blackbox/b????-$BOOT8-kmsg.log 2>/dev/null | head -1"
NEWEST_SYS="ls ~/duck-logs/blackbox/b????-$BOOT8-sys.jsonl 2>/dev/null | head -1"
NEWEST_BRAIN="ls -t ~/duck-logs/duck_wired_log_*.jsonl 2>/dev/null | head -1"
NEWEST_OUT="ls -t ~/duck-logs/*.out ~/*.out /tmp/*.out 2>/dev/null | head -1"

newest() { "${SSH[@]}" "$1" 2>/dev/null | grep -v -E "quantum|store now|upgraded" | head -1; }

follow() {  # follow <label> <remote expression>
  local label=$1 expr=$2 path name size pid now
  while true; do
    path=$(newest "$expr")
    if [ -z "$path" ]; then sleep 2; continue; fi
    name=$(basename "$path")
    size=$(stat -f %z "$OUT/$name" 2>/dev/null || echo 0)
    ev "follow $label: $name from byte $size"
    "${SSH[@]}" "tail -c +$((size + 1)) -F '$path'" >> "$OUT/$name" 2>/dev/null &
    pid=$!
    while kill -0 $pid 2>/dev/null; do
      sleep 2
      now=$(newest "$expr")
      if [ -n "$now" ] && [ "$now" != "$path" ]; then
        ev "switch $label: $name -> $(basename "$now")"; kill $pid 2>/dev/null
        "${SSH[@]}" "pkill -f 'tail -c +[0-9]* -F $path'" >/dev/null 2>&1  # the remote tail outlives the channel
        break
      fi
    done
    wait $pid 2>/dev/null
    ev "stopped $label: $name at $(stat -f %z "$OUT/$name" 2>/dev/null) bytes"
    sleep 1
  done
}

kernel() {  # the kernel ring straight from the A7Z, a new local file per connection (each starts with the whole ring)
  local f
  while true; do
    f="$OUT/kernel-$(date +%Y%m%d-%H%M%S).log"
    ev "follow kernel ring: $(basename "$f")"
    "${SSH[@]}" 'sudo -n dmesg -w -x --time-format iso' > "$f" 2>/dev/null
    ev "stopped kernel ring: $(basename "$f") at $(stat -f %z "$f" 2>/dev/null) bytes"
    [ -s "$f" ] || rm -f "$f"
    sleep 2
  done
}

ev "mirror start host $HOST"
trap 'ev "mirror stop"; kill 0' INT TERM
follow kmsg "$NEWEST_KMSG" &
follow sys "$NEWEST_SYS" &
follow brain "$NEWEST_BRAIN" &
follow brain-out "$NEWEST_OUT" &
kernel &
echo "mirroring $HOST -> $OUT (events: $OUT/mirror-events.log); Ctrl-C stops"
wait
