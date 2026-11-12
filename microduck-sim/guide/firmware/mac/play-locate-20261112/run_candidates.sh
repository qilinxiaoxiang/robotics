#!/bin/bash
# Mac mini: replay the gap-sweep robot commands with fine-tune candidates (models-<tag>/walk61.onnx + stand61.onnx)
# in the plain sim and the play conditions; walk61's numbers are in gap-sweep.json.
# Usage: run_candidates.sh TAG [TAG ...]
cd "$(dirname "$0")"
PY="$HOME/.venvs/microduck-dyn/bin/python"
CONDS="base head8 legplay4 footplay3 allplay4 solesoft"
for t in "$@"; do
  "$PY" gap_sweep.py --fell 36 --up 24 --jobs 5 --only $CONDS --models "models-$t" --tag "$t" > "candidate-$t.txt" 2>&1 &
done
wait
for t in "$@"; do echo "== $t"; grep -v '^[0-9]*/' "candidate-$t.txt" | tail -9; done
