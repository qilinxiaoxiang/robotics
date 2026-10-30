#!/bin/zsh
# openWakeWord "mochi" round 2 on the Mac mini: duck-ear positives and life-log negatives (prep_v2.py), then the
# existing stages aug -> extra -> train with 50000 steps, then both scorers. Logs in logs/v2_*.log, DONE_V2 at the end.
#   nohup ./run_v2.sh > logs/v2_chain.log 2>&1 &
set -e
OWW=/Users/shawnxiang/mochi-train/oww
PY=/Users/shawnxiang/.venvs/oww/bin/python
cd $OWW
date; echo "== prep_v2"
[ -f $OWW/data/counts_v2.json ] && [ "$SKIP_PREP" = 1 ] || $PY $OWW/prep_v2.py > logs/v2_prep.log 2>&1; tail -20 logs/v2_prep.log
sed -i '' 's/^steps: .*/steps: 50000/' $OWW/mochi.yml; grep -n "^steps" $OWW/mochi.yml
# train.py --augment_clips skips when the feature files exist (19:46: the duck clips never entered); clear them first
mkdir -p work/mochi/bak_v1; mv -f work/mochi/positive_features_train.npy work/mochi/positive_features_test.npy work/mochi/negative_features_train.npy work/mochi/negative_features_test.npy work/mochi/bak_v1/ 2>/dev/null || true
date; echo "== aug";   ./run_train.sh aug   > logs/v2_aug.log 2>&1;   grep -v "Computing\|Trimming" logs/v2_aug.log | tail -3
grep -q "skipping" logs/v2_aug.log && { echo "AUG SKIPPED, abort"; exit 1; }
date; echo "== extra"; ./run_train.sh extra > logs/v2_extra.log 2>&1; tail -3 logs/v2_extra.log
date; echo "== train"; ./run_train.sh train > logs/v2_train.log 2>&1; grep -E "Final|STAGE" logs/v2_train.log
cp $OWW/work/mochi.onnx $OWW/models/mochi_v2.onnx 2>/dev/null || cp $OWW/work/mochi/mochi.onnx $OWW/models/mochi_v2.onnx
ls -la $OWW/models/mochi_v2.onnx
date; echo "== score"
$PY $OWW/score_oww.py --model models/mochi_v2.onnx --out results/mochi_v2.json > logs/v2_score.log 2>&1; grep -E "thr|web" logs/v2_score.log
$PY $OWW/score_v2.py  --model models/mochi_v2.onnx --out results/mochi_v2_extra.json >> logs/v2_score.log 2>&1; grep -E "thr" logs/v2_score.log | tail -8
date; echo done > $OWW/DONE_V2; echo "V2_DONE"
