#!/bin/zsh
# Round 3, 2026-11-20: one Mamba student with the walk61 anchor, on Modal T4, detached (spawned call).
#   zsh train/ts3s_anchor_launch.sh <teacher folder under ckpt> <run> <student tag>
#   e.g. zsh train/ts3s_anchor_launch.sh m3s_450 ts3s-m3s-450-a s3a
# Without the pack the student is walk61: on rows with payload at most 0.02 kg its label is walk61's own action on
# the same 61 inputs (all 14 outputs, --anchor-w 1.0 --anchor-head all); with the pack it follows the teacher. A
# quarter of the no-pack envs is commanded like the robot walk logs (--case-share 0.25: vx 0.25, turn +-1.9 rad/s,
# head-pitch command 0 to 0.75). Everything else as the Kaggle students (160 iterations, dropped ticks to 0.08),
# except the env: universal5c = universal5 with the runtime joint-range cut the m3s teacher was trained under. --max-hours 2.0 (measured on Modal T4: 0.0259 it/s, 160 iterations in 1.72 h).
# Then the scoring follow-up (ts3_after_pair.py modal=1): waits for the app to end, downloads the saves, stages them
# as ckpt/<tag>_<iter> and scores all gates including G1, staging and batches under the gate lock. Heartbeat
# train/logs/<run with _>_heartbeat.txt.
set -e
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
RL=/Users/xiangzheng/code/robotics/microduck-sim/microduck_rl
MODAL=/Users/xiangzheng/code/robotics/omx-local/.venv/bin/modal
TE=$1; RUN=$2; TAG=$3
python3 - "$T" "$TE" <<'EOF'
import shutil, sys
from pathlib import Path
T = Path(sys.argv[1]); sys.path.insert(0, str(T))
from gate_lock import gate_lock
with gate_lock("teacher asset " + sys.argv[2]):   # train/init is inside the gate image's mount
    shutil.copyfile(T / "ckpt" / sys.argv[2] / "walk61.onnx", T / "init" / f"ts3t_{sys.argv[2]}.onnx")
EOF
cd $RL
FLIGHT_RUN=$RUN FLIGHT_HOURS=2.0 MICRODUCK_GPU=T4 $MODAL run --detach cmu/finetune/flight/flight_modal.py::run -- \
  --distill --delta universal5c --teacher-onnx /root/assets/init/ts3t_$TE.onnx \
  --manifest /root/assets/manifests/flightpack-none.json --max-iters ${TSMAXIT:-160} --max-hours 2.0 --save-interval 20 \
  --warmup-iters 2 --beta-iters 30 --bptt-steps 100 --epochs 2 --mb-envs 256 --stop-after ${TSSTOPAFTER:-100} --seed 1 \
  --drop-max 0.08 --core mamba --anchor-onnx /root/assets/walk61.onnx --anchor-w 1.0 --anchor-head all \
  --case-share 0.25 ${=TSEXTRA} > $T/logs/launch_$RUN.log 2>&1
# TSMAXIT=<last iteration>, TSSTOPAFTER=<iteration from which the task-metric stop applies>, TSEXTRA="<more worker
# flags>" (the second run: --stop-share 0.25, and --resume-pt /vol/runs/<run>/model_<it>.pt to continue a save)
grep -E "rate \\$|spawned" $T/logs/launch_$RUN.log | cut -c1-700
NAME=${RUN//-/_}
python3 $T/detach.py $T/logs/$NAME.out python3 $T/ts3_after_pair.py $RUN - - $RUN $TAG $NAME modal=1 hours=3.2
