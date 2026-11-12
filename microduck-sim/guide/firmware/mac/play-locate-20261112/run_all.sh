#!/bin/bash
# Mac mini: tilt gap on the robot logs (2026-11-11 after the cable tidy; 2026-11-02..06 before it) and on the
# scorecard's sim replays of the 11-02..06 walks, in parallel.
cd "$(dirname "$0")"
PY="$HOME/.venvs/microduck-dyn/bin/python"
R="$HOME/duck-walks/raw"
"$PY" tilt_gap.py --out robot-1111.json "$R"/duck_wired_log_app1111-*.jsonl > robot-1111.txt 2>&1 &
"$PY" tilt_gap.py --out robot-1102-06.json "$R"/duck_wired_log_app110[2-6]-*.jsonl > robot-1102-06.txt 2>&1 &
"$PY" tilt_gap.py --out sim-1102-06.json "$HOME"/duck-walks/scorecard-auto/*-walk*.seed0.ticks.jsonl > sim-1102-06.txt 2>&1 &
wait
for f in robot-1111 robot-1102-06 sim-1102-06; do
  echo "== $f"
  grep -v Warn "$f.txt" | tail -2 | cut -c1-2500
done
