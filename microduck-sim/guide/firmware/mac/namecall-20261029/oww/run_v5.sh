#!/bin/zsh
# openWakeWord "mochi" round 5 on the Mac mini: round 3's data (prep_v3.py) plus the duck's own motion noise
# (data/bg_motion/train: life_motion_bg.py cuts the body turns, head sweeps and walks of the 10/30 and 10/31 runs (name calls, t2b walks, long in-place turns)
# out of the always-on life log, speech masked) as background at duplication rate 5, so the spotter keeps hearing the name while the duck turns or searches. Same stages and steps
# as round 3; logs in logs/v5_*.log, DONE_V5 at the end.
#   nohup ./run_v5.sh > logs/v5_chain.log 2>&1 &
set -e
OWW=/Users/shawnxiang/mochi-train/oww
PY=/Users/shawnxiang/.venvs/oww/bin/python
cd $OWW
rm -f $OWW/DONE_V5
ls data/bg_motion/train/*.wav > /dev/null || { echo "no data/bg_motion/train clips"; exit 1; }
mkdir -p data/bg_motion_train
find data/bg_motion_train -name '*.wav' -delete
cp data/bg_motion/train/*.wav data/bg_motion_train/
echo "motion clips for training: $(ls data/bg_motion_train | wc -l)"
date; echo "== prep_v3"
$PY $OWW/prep_v3.py > logs/v5_prep.log 2>&1; tail -5 logs/v5_prep.log
sed -i '' 's/^steps: .*/steps: 50000/' $OWW/mochi.yml
grep -q bg_motion_train $OWW/mochi.yml || $PY - <<'PYEOF'
p = "/Users/shawnxiang/mochi-train/oww/mochi.yml"
s = open(p).read()
s = s.replace('  - "/Users/shawnxiang/mochi-train/oww/data/bg_roboclub"\n',
              '  - "/Users/shawnxiang/mochi-train/oww/data/bg_roboclub"\n  - "/Users/shawnxiang/mochi-train/oww/data/bg_motion_train"\n')
s = s.replace('background_paths_duplication_rate:\n  - 1\n  - 3\n', 'background_paths_duplication_rate:\n  - 1\n  - 3\n  - 5\n')
open(p, "w").write(s)
PYEOF
grep -n -A4 "background_paths" $OWW/mochi.yml
mkdir -p work/mochi/bak_v4; mv -f work/mochi/positive_features_train.npy work/mochi/positive_features_test.npy work/mochi/negative_features_train.npy work/mochi/negative_features_test.npy work/mochi/bak_v4/ 2>/dev/null || true
date; echo "== aug";   ./run_train.sh aug   > logs/v5_aug.log 2>&1 || { echo "AUG EXIT $?"; exit 1; };   grep -v "Computing\|Trimming" logs/v5_aug.log | tail -3
grep -q "skipping" logs/v5_aug.log && { echo "AUG SKIPPED, abort"; exit 1; }
date; echo "== extra"; ./run_train.sh extra > logs/v5_extra.log 2>&1; tail -3 logs/v5_extra.log
date; echo "== train"; ./run_train.sh train > logs/v5_train.log 2>&1 || true; grep -E "Final|STAGE|Error|error" logs/v5_train.log | tail -5
cp $OWW/work/mochi.onnx $OWW/models/mochi_v5.onnx 2>/dev/null || cp $OWW/work/mochi/mochi.onnx $OWW/models/mochi_v5.onnx
ls -la $OWW/models/mochi_v5.onnx
date; echo "== score"
$PY $OWW/score_oww.py --model models/mochi_v5.onnx --out results/mochi_v5.json > logs/v5_score.log 2>&1; grep -E "thr|web" logs/v5_score.log
$PY $OWW/score_v2.py  --model models/mochi_v5.onnx --heldout data/duck_heldout_v3.json --out results/mochi_v5_extra.json >> logs/v5_score.log 2>&1; grep -E "thr" logs/v5_score.log | tail -8
date; echo done > $OWW/DONE_V5; echo "V5_DONE"
