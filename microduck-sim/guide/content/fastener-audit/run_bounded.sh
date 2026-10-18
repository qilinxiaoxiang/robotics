#!/bin/bash
# Usage: run_bounded.sh <report.json> <seconds> -- <command...>
# Runs one CAD job under head-redesign-20261008/run_bounded_cad.py (1536 MiB, exclusive), retrying while another job holds the lock.
R=/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py
report=$1; secs=$2; shift 3
for i in $(seq 1 30); do
  out=$(python3 "$R" --max-mib 1536 --seconds "$secs" --wait-lock-seconds 60 --report "$report" -- "$@" 2>&1); code=$?
  if echo "$out" | grep -q "Another bounded CAD check is running"; then sleep 5; continue; fi
  echo "$out"; exit $code
done
echo "lock never acquired"; exit 75
