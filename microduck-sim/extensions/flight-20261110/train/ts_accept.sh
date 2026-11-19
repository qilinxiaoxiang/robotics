#!/bin/zsh
# Acceptance of one or more checkpoint dirs of the teacher-student round (TEACHER-STUDENT-PLAN.md section 7):
# the 36 cases (dev seeds), the score against fq2_1999 and uni_a, then the added neck/head walking case.
#   zsh train/ts_accept.sh <dir under train/ckpt> [<dir> ...]
set -e
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
cd $T/..
MODAL=/Users/xiangzheng/code/robotics/omx-local/.venv/bin/modal
GPY=/Users/xiangzheng/.venvs/microduck-walk/bin/python   # numpy + onnxruntime for the action-distance line
for M in "$@"; do
  # Chatter gates first (ts3_gates.py, 2026-11-19: s2r6_4 passed every simulated fall cell and fell on the robot from
  # action chatter). A candidate that fails them gets no acceptance run and no robot checklist. GATES_TEACHER=1 for a
  # privileged teacher (no action-distance line).
  python3 train/ts3_gates.py spec acc_$M $M > train/logs/gates_$M.log 2>&1
  if ! grep -q ": 0 evals" train/logs/gates_$M.log; then
    $MODAL run train/flight_eval_modal.py --spec train/eval/spec_gate_acc_$M.json >> train/logs/gates_run_$M.log 2>&1
  fi
  if ! $GPY train/ts3_gates.py score $M ${GATES_TEACHER:+--teacher} > train/logs/gates_$M.log 2>&1; then
    echo "done $M $(date +%H:%M) GATES FAILED: $(grep -c '^FAIL' train/logs/gates_$M.log) failed gate lines (train/logs/gates_$M.log); no acceptance run"
    continue
  fi
  python3 train/accept_universal.py run $M > train/logs/accept_run_$M.log 2>&1
  python3 train/accept_universal.py score $M --ref fq2_1999,uni_a > train/logs/accept_score_$M.log 2>&1 || true
  python3 train/accept_head.py run $M >> train/logs/accept_run_$M.log 2>&1
  echo "done $M $(date +%H:%M) $(grep -c '^FAIL' train/logs/accept_score_$M.log) failed lines"
done
