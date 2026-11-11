#!/bin/zsh
# Full flight sequence with the leg policy joined (2026-11-11). Run in the flight-20261110 folder with $PY set
# (zsh sim/mini.sh run 'zsh sim/fullseq_runs.sh <step>').
#   held      held-legs rerun of ARE_nominal, 3 scenarios x 3 seeds, compared field by field with sim/out/batch
#   policy    --legs policy   (policy from the first tick through the flight) ARE_nominal / 90 / 80 %, 3 seeds
#   handover  --legs handover (policy on the ground, Brain stand mode from lift-off 3 cm up, policy again 3 cm above the
#             surface) same cases -> sim/out/fullseq_handover
# Variants run by hand with batch.py --legs handover --flight-args ... --out-dir ...: "--air-pose held" (trimmed held
# pose in the air, sim/out/fullseq_handover_heldpose), "--air-legs monitor" (fullseq_handover_monitor), diagnostic
# "--spool-down-frac 0 --spool-down 0.02" (fans cut at the land detector, fullseq_diag_fancut). Then
# $PY sim/fullseq_falls.py <dir> for the hand-over and fall readback, $PY sim/fullseq_trace.py <row.json> for one trace.
set -e
case "$1" in
  held)
    timeout 600 $PY sim/batch.py --only ARE_nominal --seeds 3 --out-dir sim/out/heldcheck --force > sim/out/heldcheck.log 2>&1
    $PY sim/heldcheck.py sim/out/heldcheck
    ;;
  policy|handover)
    timeout 600 $PY sim/batch.py --legs $1 --only ARE_nominal,ARE_thrust90,ARE_thrust80 --seeds 3 --force
    ;;
esac
