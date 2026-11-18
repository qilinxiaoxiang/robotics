#!/bin/zsh
# Acceptance of one or more checkpoint dirs of the teacher-student round (TEACHER-STUDENT-PLAN.md section 7):
# the 36 cases (dev seeds), the score against fq2_1999 and uni_a, then the added neck/head walking case.
#   zsh train/ts_accept.sh <dir under train/ckpt> [<dir> ...]
set -e
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
cd $T/..
for M in "$@"; do
  python3 train/accept_universal.py run $M > train/logs/accept_run_$M.log 2>&1
  python3 train/accept_universal.py score $M --ref fq2_1999,uni_a > train/logs/accept_score_$M.log 2>&1 || true
  python3 train/accept_head.py run $M >> train/logs/accept_run_$M.log 2>&1
  echo "done $M $(date +%H:%M) $(grep -c '^FAIL' train/logs/accept_score_$M.log) failed lines"
done
