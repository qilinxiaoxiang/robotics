#!/bin/zsh
# openWakeWord "mochi" round 3 on the Mac mini: gated duck positives, tonight's calls and talk, RoboClub room noise
# (prep_v3.py), then the existing stages aug -> extra -> train with 50000 steps, then both scorers on the round-3
# held-out set. Logs in logs/v3_*.log, DONE_V3 at the end.
#   nohup ./run_v3.sh > logs/v3_chain.log 2>&1 &
set -e
OWW=/Users/shawnxiang/mochi-train/oww
PY=/Users/shawnxiang/.venvs/oww/bin/python
cd $OWW
rm -f $OWW/DONE_V3
date; echo "== prep_v3"
$PY $OWW/prep_v3.py > logs/v3_prep.log 2>&1; tail -30 logs/v3_prep.log
sed -i '' 's/^steps: .*/steps: 50000/' $OWW/mochi.yml; grep -n "^steps" $OWW/mochi.yml
# the RoboClub room chunks join the background pool (duplication rate 3: picked three times as often as their share)
grep -q bg_roboclub $OWW/mochi.yml || $PY - <<'EOF'
import re
p = "/Users/shawnxiang/mochi-train/oww/mochi.yml"
s = open(p).read()
s = s.replace('background_paths:\n  - "/Users/shawnxiang/mochi-train/oww/data/bg16k"\n',
              'background_paths:\n  - "/Users/shawnxiang/mochi-train/oww/data/bg16k"\n  - "/Users/shawnxiang/mochi-train/oww/data/bg_roboclub"\n')
s = s.replace('background_paths_duplication_rate:\n  - 1\n', 'background_paths_duplication_rate:\n  - 1\n  - 3\n')
open(p, "w").write(s)
EOF
grep -n -A3 "background_paths" $OWW/mochi.yml
# train.py --augment_clips skips when the feature files exist; clear them (round-2 features kept in bak_v2)
mkdir -p work/mochi/bak_v2; mv -f work/mochi/positive_features_train.npy work/mochi/positive_features_test.npy work/mochi/negative_features_train.npy work/mochi/negative_features_test.npy work/mochi/bak_v2/ 2>/dev/null || true
date; echo "== aug";   ./run_train.sh aug   > logs/v3_aug.log 2>&1;   grep -v "Computing\|Trimming" logs/v3_aug.log | tail -3
grep -q "skipping" logs/v3_aug.log && { echo "AUG SKIPPED, abort"; exit 1; }
date; echo "== extra"; ./run_train.sh extra > logs/v3_extra.log 2>&1; tail -3 logs/v3_extra.log
date; echo "== train"; ./run_train.sh train > logs/v3_train.log 2>&1 || true; grep -E "Final|STAGE|Error|error" logs/v3_train.log | tail -5
# train.py dies in the tflite conversion (no onnx_tf) after writing the onnx: that is fine, the onnx is the model
cp $OWW/work/mochi.onnx $OWW/models/mochi_v3.onnx 2>/dev/null || cp $OWW/work/mochi/mochi.onnx $OWW/models/mochi_v3.onnx
ls -la $OWW/models/mochi_v3.onnx
date; echo "== score"
$PY $OWW/score_oww.py --model models/mochi_v3.onnx --out results/mochi_v3.json > logs/v3_score.log 2>&1; grep -E "thr|web" logs/v3_score.log
$PY $OWW/score_v2.py  --model models/mochi_v3.onnx --heldout data/duck_heldout_v3.json --out results/mochi_v3_extra.json >> logs/v3_score.log 2>&1; grep -E "thr" logs/v3_score.log | tail -8
echo "== v2 on the same held-out set, for the comparison"
$PY $OWW/score_v2.py  --model models/mochi_v2.onnx --heldout data/duck_heldout_v3.json --out results/mochi_v2_on_v3_heldout.json > logs/v3_score_v2.log 2>&1; grep -E "thr" logs/v3_score_v2.log | tail -8
date; echo done > $OWW/DONE_V3; echo "V3_DONE"
