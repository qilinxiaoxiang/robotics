#!/bin/zsh
# openWakeWord "mochi" pipeline on the Mac mini. Stages: gen (piper clips), aug (augment + features), extra (our
# negatives), train. Usage: run_train.sh gen|aug|extra|train|all  (logs: ~/mochi-train/oww/logs/<stage>.log)
set -e
OWW=/Users/shawnxiang/mochi-train/oww
PY=/Users/shawnxiang/.venvs/oww/bin/python
TRAIN=$OWW/openWakeWord/openwakeword/train.py
mkdir -p $OWW/logs
cd $OWW
stage=${1:-all}
run_gen() {
  date; echo "== generate_clips"
  $PY $TRAIN --training_config $OWW/mochi.yml --generate_clips
  # real people saying "mochi" (mochi_web pos + pos_ctx of the training videos) join the synthetic positives
  cp $OWW/data/web_pos/*.wav $OWW/work/mochi/positive_train/
  ls $OWW/work/mochi/positive_train | wc -l; ls $OWW/work/mochi/negative_train | wc -l
  ls $OWW/work/mochi/positive_test | wc -l; ls $OWW/work/mochi/negative_test | wc -l
  date
}
run_aug() {
  date; echo "== augment_clips"
  $PY $TRAIN --training_config $OWW/mochi.yml --augment_clips
  # train.py keeps total_length in memory only; 16 feature frames = 32000 samples, what make_extra_features.py assumes
  $PY -c "import numpy as np; s = np.load('$OWW/work/mochi/positive_features_train.npy', mmap_mode='r').shape; print('positive_features_train', s); assert s[1] == 16, 'total_length is not 32000: rerun make_extra_features.py'"
  date
}
run_extra() {
  date; echo "== extra features"
  $PY $OWW/make_extra_features.py
  date
}
run_train() {
  date; echo "== train_model"
  $PY $OWW/train_wrap.py --training_config $OWW/mochi.yml --train_model
  ls -la $OWW/work/*.onnx $OWW/work/mochi/*.onnx 2>/dev/null || true
  date
}
case $stage in
  gen) run_gen ;;
  aug) run_aug ;;
  extra) run_extra ;;
  train) run_train ;;
  all) run_gen && run_aug && run_extra && run_train ;;
esac
echo "STAGE_DONE $stage"
