#!/bin/zsh
# Seeing-pick pack fine-tune (FP-R7) pre-launch work on the Mac mini, never the MacBook. Mirrors the grasp worktree
# (microduck_rl-grasp, branch cmu/grasp) beside the flight train mirror, with its own uv venv, and runs one job at a time
# behind other sessions' simulations (mini.sh's busy check), each under 10 minutes.
#   zsh train/mini_seepick.sh push                   mirror code, models, the seepick61 checkpoint, payload.py
#   zsh train/mini_seepick.sh setup                  uv sync in the mirror (first time)
#   zsh train/mini_seepick.sh test                   pytest the pack cfg and spk2 curriculum tests -> logs/seepick_pack_tests.log
#   zsh train/mini_seepick.sh check LOAD BASE CASES [ENVS] [PARTS] [TAG]   seeing_pack_check.py -> out/spk_<TAG>_<BASE>_<LOAD>.json
#        LOAD s<scale> = spk2 whole-pack scale (e.g. s0.05); env SPK_CHECK_EXTRA passes extra check arguments
#   zsh train/mini_seepick.sh smoke [ITERS] [ENVS] [WARMUP]        grasp_worker.py PPO smoke + resume -> logs/seepick_pack_smoke.log
# ssh sometimes hangs after the remote job has finished: every job writes its result file on the mini first and the
# fetch looks for that file, so a hung ssh is killed by `timeout` and the result is still copied back.
set -e
LOCAL=/Users/xiangzheng/code/robotics/microduck-sim
MIRROR=code/flight-train-mirror/robotics/microduck-sim
G=microduck_rl-grasp
T=$LOCAL/extensions/flight-20261110/train
CK=cmu/finetune/kaggle/out/sp-a-1027/runs/sp-b-1027/model_2500.pt
OVL=hardware-design-20260912/whole-robot-20260912/runtime-overlay/models
mkdir -p $T/logs $T/out
# a dead link (the MacBook slept, 2026-11-12: one ssh outlived its `timeout 700` by half an hour) is noticed by the
# keepalive within a minute; -n keeps a background ssh off the terminal
SSHO=(-n -o ServerAliveInterval=15 -o ServerAliveCountMax=4)
case "$1" in
  push)
    ssh mac-mini "mkdir -p $MIRROR/$G/$(dirname $CK) $MIRROR/$OVL $MIRROR/microduck_rl/cmu/finetune/flight $MIRROR/extensions/flight-20261110/train/ckpt/fq2_1999 $MIRROR/extensions/flight-20261110/train/manifests"
    rsync -a --exclude='.git' --exclude='.venv' --exclude='logs/' --exclude='cmu/finetune/kaggle/out/' \
      --exclude='cmu/hardware' --exclude='cmu/simulator' --exclude='cmu/real-logs' --exclude='__pycache__' \
      --exclude='output.onnx' $LOCAL/$G/ mac-mini:$MIRROR/$G/
    rsync -a $LOCAL/$G/$CK mac-mini:$MIRROR/$G/$CK
    rsync -a $LOCAL/$OVL/seepick61.onnx mac-mini:$MIRROR/$OVL/
    rsync -a $LOCAL/microduck_rl/cmu/finetune/flight/payload.py mac-mini:$MIRROR/microduck_rl/cmu/finetune/flight/
    rsync -a $T/manifests/ mac-mini:$MIRROR/extensions/flight-20261110/train/manifests/
    rsync -a $T/ckpt/fq2_1999/walk61.onnx mac-mini:$MIRROR/extensions/flight-20261110/train/ckpt/fq2_1999/
    ;;
  setup)
    timeout 900 ssh mac-mini "cd $MIRROR/$G && /opt/homebrew/bin/uv sync 2>&1 | tail -5"
    ;;
  test)
    zsh $T/mini.sh run true
    timeout -k 15 700 ssh $SSHO mac-mini "cd $MIRROR/$G && timeout 590 .venv/bin/python -m pytest -q tests/test_cmu_seeing_pick_pack_cfg.py tests/test_cmu_seeing_pick_pack_curriculum.py tests/test_cmu_seeing_pick_pack_spk3.py >/tmp/seepick_pack_tests.log 2>&1; echo exit \$? >> /tmp/seepick_pack_tests.log" || true
    timeout -k 5 90 scp -q -o ServerAliveInterval=15 mac-mini:/tmp/seepick_pack_tests.log $T/logs/seepick_pack_tests.log || true
    tail -15 $T/logs/seepick_pack_tests.log
    ;;
  check)
    # $5 envs per part, $6 parts run at once (the CPU sim is single-threaded; seeds 1..parts), $7 tag
    LD=$2; BS=$3; CS=$4; NE=${5:-64}; NP=${6:-4}; TG=${7:-start}
    OUT=spk_${TG}_${BS}_${LD}
    zsh $T/mini.sh run true
    timeout -k 15 700 ssh $SSHO mac-mini "cd $MIRROR/$G && SPK_CHECK_EXTRA='$SPK_CHECK_EXTRA' SPK_SEED0='${SPK_SEED0:-0}' zsh cmu/grasp/seeing_pack_parts.sh $LD $BS $CS $NE $NP /tmp/$OUT" || true
    timeout -k 5 90 scp -q -o ServerAliveInterval=15 mac-mini:/tmp/$OUT.log $T/logs/$OUT.log || true
    timeout -k 5 90 scp -q -o ServerAliveInterval=15 mac-mini:/tmp/$OUT.json $T/out/$OUT.json || true
    grep -E "\[pack-check\] merged|Error|Traceback|^exit|^part" $T/logs/$OUT.log | cut -c1-700
    ;;
  merge)
    # merge part files of earlier check waves left in the mini's /tmp: merge OUTSTEM STEM1 [STEM2 ...]
    #   -> out/OUTSTEM.json (e.g. two 8 x 16-env waves of one load, seeds 1-8 and 9-16)
    MO=$2; shift 2
    PS=""
    for st in "$@"; do PS="$PS /tmp/${st}_p*.json"; done
    timeout -k 15 120 ssh $SSHO mac-mini "cd $MIRROR/$G && .venv/bin/python cmu/grasp/seeing_pack_check.py --merge /tmp/$MO.json $PS > /tmp/$MO.log 2>&1; echo exit \$? >> /tmp/$MO.log" || true
    timeout -k 5 90 scp -q -o ServerAliveInterval=15 mac-mini:/tmp/$MO.log $T/logs/$MO.log || true
    timeout -k 5 90 scp -q -o ServerAliveInterval=15 mac-mini:/tmp/$MO.json $T/out/$MO.json || true
    grep -E "\[pack-check\] merged|Error|Traceback|^exit" $T/logs/$MO.log | cut -c1-700
    ;;
  spk2smoke)
    # cmu/grasp/spk2_smoke.sh: the curriculum moving s_max, a resume keeping it, a forced "no rise" stop
    zsh $T/mini.sh run true
    timeout -k 15 900 ssh $SSHO mac-mini "cd $MIRROR/$G && zsh cmu/grasp/spk2_smoke.sh" || true
    mkdir -p $T/logs/spk2_smoke
    for f in A.log B.log A_record_part1.json A_record.json B_record.json A_train.log B_train.log; do
      timeout -k 5 90 scp -q -o ServerAliveInterval=15 mac-mini:/tmp/spk2_smoke/$f $T/logs/spk2_smoke/$f || true
    done
    grep -hE "\[spk|spk-curriculum|in-run stop|exit|Traceback|Error" $T/logs/spk2_smoke/A.log $T/logs/spk2_smoke/A_train.log \
      $T/logs/spk2_smoke/B.log $T/logs/spk2_smoke/B_train.log | cut -c1-300 | head -60
    ;;
  spk3smoke)
    # cmu/grasp/spk3_smoke.sh: the floor blocking a rise (A), its floor-0 control (B), live numbered ONNX export;
    # $2 = the start checkpoint (spk2 model_best.pt), copied to the mini's /tmp/spk3/spk2_best.pt
    ssh mac-mini "mkdir -p /tmp/spk3"
    rsync -a $2 mac-mini:/tmp/spk3/spk2_best.pt
    zsh $T/mini.sh run true
    timeout -k 15 900 ssh $SSHO mac-mini "cd $MIRROR/$G && zsh cmu/grasp/spk3_smoke.sh" || true
    mkdir -p $T/logs/spk3_smoke $T/ckpt/spk3_smoke_onnx
    for f in A.log B.log A_record.json B_record.json A_train.log B_train.log; do
      timeout -k 5 90 scp -q -o ServerAliveInterval=15 mac-mini:/tmp/spk3_smoke/$f $T/logs/spk3_smoke/$f || true
    done
    timeout -k 5 90 scp -q -o ServerAliveInterval=15 "mac-mini:/tmp/spk3_smoke/*.onnx" $T/ckpt/spk3_smoke_onnx/ || true
    grep -hE "\[spk|spk-curriculum|in-run stop|exported|^exit|Traceback|Error|init" $T/logs/spk3_smoke/A.log $T/logs/spk3_smoke/A_train.log \
      $T/logs/spk3_smoke/B.log $T/logs/spk3_smoke/B_train.log | cut -c1-300 | head -80
    ;;
  smoke)
    IT=${2:-4}; NE=${3:-64}; WU=${4:-2}
    RN=spk-smoke-$(date +%m%d%H%M%S)   # a new run name: grasp_worker collects checkpoints by run name under logs/
    zsh $T/mini.sh run true
    # part 1: IT iterations as the Modal call runs them (--resume on a fresh run, --export-live); part 2: the same run
    # name again with 2 more iterations = the resume path a preempted Modal attempt takes (iteration, critic warm-up,
    # elapsed time from progress.json). No --check-iter here: the Modal smoke exercises the iteration check.
    W="SEEPICK_PACK_WARMUP=$WU timeout 290 .venv/bin/python cmu/grasp/grasp_worker.py --run-name $RN --root /tmp/spk_smoke --task Mjlab-SeeingPick-Pack-FromPick-MicroDuck-CMU-Current --num-envs $NE --save-interval 2 --max-hours 0.15 --max-dollars 1 --rate-per-hour 1 --device cpu --resume --export-live"
    timeout -k 15 700 ssh $SSHO mac-mini "cd $MIRROR/$G && rm -rf /tmp/spk_smoke && $W --max-iters $IT > /tmp/spk_smoke.log 2>&1; echo exit \$? >> /tmp/spk_smoke.log; cp /tmp/spk_smoke/$RN/run_record.json /tmp/spk_smoke/record_part1.json; $W --max-iters $((IT + 2)) >> /tmp/spk_smoke.log 2>&1; echo exit \$? >> /tmp/spk_smoke.log" || true
    timeout -k 5 90 scp -q -o ServerAliveInterval=15 mac-mini:/tmp/spk_smoke.log $T/logs/seepick_pack_smoke.log || true
    timeout -k 5 90 scp -q -o ServerAliveInterval=15 mac-mini:/tmp/spk_smoke/record_part1.json $T/out/seepick_pack_smoke_record_part1.json || true
    timeout -k 5 90 scp -q -o ServerAliveInterval=15 mac-mini:/tmp/spk_smoke/$RN/progress.json $T/out/seepick_pack_smoke_progress.json || true
    timeout -k 5 90 scp -q -o ServerAliveInterval=15 mac-mini:/tmp/spk_smoke/$RN/train.log $T/logs/seepick_pack_smoke_train.log || true
    timeout -k 5 90 scp -q -o ServerAliveInterval=15 mac-mini:/tmp/spk_smoke/$RN/run_record.json $T/out/seepick_pack_smoke_record.json || true
    mkdir -p $T/ckpt/spk_smoke
    timeout -k 5 90 scp -q -o ServerAliveInterval=15 "mac-mini:/tmp/spk_smoke/$RN/*.onnx" $T/ckpt/spk_smoke/ || true
    tail -3 $T/logs/seepick_pack_smoke.log
    ;;
esac
