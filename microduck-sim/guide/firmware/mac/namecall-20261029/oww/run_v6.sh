#!/bin/zsh
# openWakeWord "mochi" round 6 on the Mac mini: round 4's recipe (motion background at rate 5, 50000 steps) on
# prep_v6.py's data: Shawn's calls and no-call talk mined from the life log since 11-02 (mine_v6.py, accept rule
# ZC / V4MIN from mine_v6.py --validate) and every positive cut with a wider time and level spread. Then the v4 and v6
# scores side by side: score_oww.py (web / speech false wakes), score_v2.py (held-out duck calls, held-out life talk),
# score_v6.py (new held-out calls per ear at eight frame offsets). Logs logs/v6_*.log, DONE_V6 at the end.
#   ZC=5 V4MIN=0.05 nohup ./run_v6.sh > logs/v6_chain.log 2>&1 &
set -e
OWW=/Users/shawnxiang/mochi-train/oww
PY=/Users/shawnxiang/.venvs/oww/bin/python
cd $OWW
rm -f $OWW/DONE_V6
: ${ZC:?set ZC} ${V4MIN:?set V4MIN}
# every feature file mochi.yml names must exist before hours of prep (2026-11-12: dl/ was gone, train failed after
# aug and the old work/mochi.onnx was copied as v6)
for f in $($PY -c "import yaml; c = yaml.safe_load(open('$OWW/mochi.yml')); print(' '.join([c['false_positive_validation_data_path']] + [v for k, v in c['feature_data_files'].items() if 'work/mochi' not in v]))"); do
  [ -s "$f" ] || { echo "missing training input: $f"; exit 1; }
done
ls data/bg_motion/train.v4/*.wav > /dev/null || { echo "no data/bg_motion/train.v4 clips (round 4 motion set)"; exit 1; }
mkdir -p data/bg_motion_train
find data/bg_motion_train -name '*.wav' -delete
cp data/bg_motion/train.v4/*.wav data/bg_motion_train/   # round 4 motion set; round 5 walks were rejected
echo "motion clips for training: $(ls data/bg_motion_train | wc -l)"
date; echo "== prep_v6"
$PY $OWW/prep_v6.py --zc $ZC --v4min $V4MIN > logs/v6_prep.log 2>&1; tail -30 logs/v6_prep.log
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
mkdir -p work/mochi/bak_v5; mv -f work/mochi/positive_features_train.npy work/mochi/positive_features_test.npy work/mochi/negative_features_train.npy work/mochi/negative_features_test.npy work/mochi/bak_v5/ 2>/dev/null || true
date; echo "== aug";   ./run_train.sh aug   > logs/v6_aug.log 2>&1 || { echo "AUG EXIT $?"; exit 1; };   grep -v "Computing\|Trimming" logs/v6_aug.log | tail -3
grep -q "skipping" logs/v6_aug.log && { echo "AUG SKIPPED, abort"; exit 1; }
date; echo "== extra"; ./run_train.sh extra > logs/v6_extra.log 2>&1; tail -3 logs/v6_extra.log
date; echo "== train"; rm -f $OWW/work/mochi.onnx $OWW/work/mochi/mochi.onnx
./run_train.sh train > logs/v6_train.log 2>&1 || { grep -E "Error|error" logs/v6_train.log | tail -3; echo "TRAIN FAILED"; exit 1; }
grep -E "Final|STAGE" logs/v6_train.log | tail -5
if [ -s $OWW/work/mochi.onnx ]; then cp $OWW/work/mochi.onnx $OWW/models/mochi_v6.onnx
elif [ -s $OWW/work/mochi/mochi.onnx ]; then cp $OWW/work/mochi/mochi.onnx $OWW/models/mochi_v6.onnx
else echo "TRAIN WROTE NO MODEL"; exit 1; fi
ls -la $OWW/models/mochi_v6.onnx
date; echo "== score"
$PY $OWW/score_oww.py --model models/mochi_v6.onnx --out results/mochi_v6.json > logs/v6_score.log 2>&1; grep -E "thr|web" logs/v6_score.log
$PY $OWW/score_v2.py  --model models/mochi_v6.onnx --heldout data/duck_heldout_v3.json --out results/mochi_v6_extra.json >> logs/v6_score.log 2>&1; grep -E "thr" logs/v6_score.log | tail -8
$PY $OWW/score_v6.py --model models/mochi_v4.onnx --model models/mochi_v6.onnx --out results/v6_new.json > logs/v6_new.log 2>&1; grep -v Warn logs/v6_new.log | tail -4
date; echo done > $OWW/DONE_V6; echo "V6_DONE"
