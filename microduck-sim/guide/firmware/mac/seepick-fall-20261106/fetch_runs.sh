#!/bin/bash
# Wait for the A7Z, then copy the 2026-11-06 brain logs and seepick traces here (raw copies, nothing parsed on the A7Z).
cd "$(dirname "$0")" || exit 1
mkdir -p raw
until timeout 8 ssh -o ConnectTimeout=6 a7z true 2>/dev/null; do sleep 15; done
echo "a7z online $(date +%H:%M:%S)"
rsync -a --partial a7z:'duck-logs/duck_wired_log_app1106-*.jsonl' a7z:'duck-logs/duck_wired_app1106-*.out' \
  a7z:'duck-logs/seepick_1106*.jsonl' raw/
ls -la raw
