#!/bin/zsh
# Round 3 pre-launch on the Mac mini (RUNLOG.md "Round 3"): incentive audit of the chatter-fix delta in the teacher
# env, one load per job, each under 10 minutes, CPU only, under the mirror's lock.
#   zsh train/ts3_audit.sh push                          copy the flight code, manifests and the policies used below
#   zsh train/ts3_audit.sh diag <load> <tag>             ts_start as the intended walk beside the chattering teacher
#                                                        t2a_999 (pol_chat) with the raw smoothness sums (--diag)
#   zsh train/ts3_audit.sh gate <load> <tag>             stand, shuffle, lean forward / back against the intended walk
#   zsh train/ts3_audit.sh smoke [iters] [envs]          teacher_smoke.py with delta universal5t (anchor included)
# Reward mods: train/rm_universal5.json. Results: train/out/audit_<tag>_<load>.json.
set -e
LOCAL=/Users/xiangzheng/code/robotics/microduck-sim
REMOTE=code/flight-train-mirror/robotics/microduck-sim
RL=microduck_rl
FL=extensions/flight-20261110
T=$LOCAL/$FL/train
A="\$HOME/$REMOTE/smoke-assets"
LK="\$HOME/$REMOTE/$FL/train/mini_lock.sh"
JOB=${TSJOB:-universal5t}
source $T/ssh_guard.sh
mkdir -p $T/logs $T/out
case "$1" in
  push)
    zsh $T/ts_round.sh push
    zsh $T/ts_round.sh start $T/ckpt/ts_start/walk61.onnx
    rsync -a $T/ckpt/ts2a999_teacher/teacher.onnx mac-mini:$REMOTE/smoke-assets/ts3_chat.onnx
    rsync -a $LOCAL/$RL/cmu/whole/runtime-overlay/models/walk61.onnx mac-mini:$REMOTE/smoke-assets/ts3_walk61.onnx
    rsync -a $T/rm_universal5.json mac-mini:$REMOTE/smoke-assets/rm_universal5.json
    ;;
  diag|gate)
    LD=$2; TAG=$3
    if [ "$1" = "diag" ]; then CS=pol_chat; EX="--diag --policy chat=$A/ts3_chat.onnx"; else CS=stand,shuffle,lean_fwd,lean_back; EX=""; fi
    rsync -a $T/rm_universal5.json mac-mini:$REMOTE/smoke-assets/rm_universal5.json
    ssh mac-mini "cd $REMOTE/$RL && zsh $LK run timeout 590 .venv/bin/python cmu/finetune/flight/flight_audit.py --jobs $JOB \
      --cases $CS --loads $LD --reward-mods \"\$(cat \$HOME/$REMOTE/smoke-assets/rm_universal5.json)\" --device cpu --num-envs 128 --steps ${TSSTEPS:-250} \
      --assets $A --policy start=$A/ts_start.onnx --walker start $EX --out /tmp/ts3_audit_${TAG}_$LD 2>&1" \
      > $T/logs/audit_${TAG}_$LD.log || true
    scp -q mac-mini:/tmp/ts3_audit_${TAG}_$LD/audit.json $T/out/audit_${TAG}_$LD.json || true
    grep -E "\[audit\]|\[gain\]|Traceback|Error" $T/logs/audit_${TAG}_$LD.log | cut -c1-600 | head -12
    ;;
  smoke)
    IT=${2:-3}; NE=${3:-64}
    ssh mac-mini "cd $REMOTE/$RL && FLIGHT_MANIFESTS=\$HOME/$REMOTE/$FL/train/manifests FLIGHT_ANCHOR_ONNX=$A/ts3_walk61.onnx zsh $LK run timeout 590 \
      .venv/bin/python cmu/finetune/flight/teacher_smoke.py --init $A/${TSINIT:-ts_start.onnx} --envs $NE --iters $IT --delta ${TSDELTA:-universal5t} \
      --outdir /tmp/ts3_teacher_smoke 2>&1" > $T/logs/ts3_teacher_smoke.log || true
    scp -q mac-mini:/tmp/ts3_teacher_smoke/teacher_smoke.json $T/out/ts3_teacher_smoke.json || true
    grep -E "\[smoke\]|\[teacher\]|\[anchor\]|\[gain\]|Error|Traceback" $T/logs/ts3_teacher_smoke.log | cut -c1-500 | head -40
    ;;
esac
