#!/bin/zsh
# Acceptance of the bend fine-tune (BEND-PLAN.md section 6) after its Kaggle kernel ends (fk-bend-a2 rides in the
# paired kernel fk-uni-a2). MacBook side: fetch, stage models dirs, then every simulation runs on the Mac mini, one at
# a time, each job under 10 minutes.
#   zsh train/accept_bend.sh fetch [K] [runs]  kaggle fetch K; stage ckpt/bend_a2[_best]/ (fq2 1999 in the
#                                       stand and walk slots, the fine-tuned groundpick61, the original seepick61)
#   zsh train/accept_bend.sh runtime R  style_eval bend case (PICKUP command, 20 episodes) at full / batteries out /
#                                       none for models dir ckpt/R -> eval/st_<R>_gp_<load>.json
#   zsh train/accept_bend.sh env R      bend_accept.py in the training env (mouth, pitch, p99) -> eval/bendaccept_<R>_<load>.json
#   zsh train/accept_bend.sh video R    bend clip with the pack drawn -> video/<R>_bend_pack
set -e
FLD=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110
T=$FLD/train
RL=/Users/xiangzheng/code/robotics/microduck-sim/microduck_rl
GP="--walk-at 1 --walk-s 0 --gp-at 2 --gp-phase 0.33 --gp-hold-s 4"
case "$1" in
  fetch)
    # $2 kernel (default fk-uni-a2, the paired kernel that carries fk-bend-a2), $3.. bend run names (default fk-bend-a2)
    K=${2:-fk-uni-a2}
    RUNS=(${@:3})
    [ ${#RUNS} -eq 0 ] && RUNS=(fk-bend-a2)
    (cd $RL && python3 cmu/finetune/flight/kaggle_flight.py fetch $K 2>&1 | grep -v outdated | tail -4)
    for rn in $RUNS; do
      RUN=$T/kaggle/out/$K/runs/$rn
      r=${rn#fk-}
      for v in "" _best; do
        D=$T/ckpt/${r//-/_}$v
        mkdir -p $D
        cp $T/ckpt/fq2_1999/stand61.onnx $T/ckpt/fq2_1999/walk61.onnx $T/ckpt/bend_spec/seepick61.onnx $D/
        cp $RUN/$rn$v.onnx $D/groundpick61.onnx
        print "staged $D"
      done
      python3 -c "import json,sys; r=json.load(open(sys.argv[1])); print({k: r.get(k) for k in ('final_iter','stop_reason','elapsed_s')})" $RUN/run_record.json
    done
    ;;
  runtime)
    R=$2
    zsh $T/mini.sh push > /dev/null
    for ld in load100 nobatt load000; do
      zsh $T/mini.sh run "\$PY train/style_eval.py --name ${R}_gp_$ld --models train/ckpt/$R --manifest train/manifests/flightpack-$ld.json --case stand --episodes 20 --workers 8 --extra='--stand-s 0 $GP' --out train/eval/st_${R}_gp_$ld.json 2>&1 | tail -1 | cut -c1-700" | grep -v "^busy"
    done
    zsh $T/mini.sh pull > /dev/null
    ;;
  env)
    R=$2
    cd $FLD
    for ld in full nobatt none; do
      zsh train/mini_train_smoke.sh bendaccept $ld $T/ckpt/$R/groundpick61.onnx $T/ckpt/$R/stand61.onnx $R 20 | grep -v "^busy" | cut -c1-120,250-900
    done
    ;;
  video)
    R=$2
    zsh $T/mini.sh push > /dev/null
    zsh $T/sync_pack_visual.sh
    zsh $T/mini.sh run "mkdir -p train/video && \$PY train/flight_video.py --models train/ckpt/$R --manifest sim/out/visual/flightpack-nominal.json --case stand --key-t 5 --seed 0 --extra='--stand-s 0 $GP' --out train/video/${R}_bend_pack > train/video/${R}_bend_pack.json 2>&1; tail -c 400 train/video/${R}_bend_pack.json" | grep -v "^busy"
    mkdir -p $T/video
    rsync -a "mac-mini:code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110/train/video/${R}_bend_pack*" $T/video/
    ;;
esac
