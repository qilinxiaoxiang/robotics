#!/bin/zsh
# Round 3, 2026-11-20 12:25: PPO on the distilled student on Modal T4, one run, detached (spawned call).
#   zsh train/ts3_rl_modal_launch.sh
# Run ts3rl-a1 -> ckpt/s3RLa_<iter>: from run AB's save 140 (train/init/s3AB_140.pt), iterations 140 to 300, save
# every 20, imitation weight annealed 0.5 -> 0.1 + PPO 0.5 (the smoke's chain a), lr 1e-4, clip 0.1, 5 critic-only
# iterations first. Env universal5 (the teacher's rewards, unchanged), teacher t3h_750, student inputs as run AB
# (gain flag in column 59, no pack flag), anchor walk61 on no-pack rows, case share 0.25, stop share 0.25.
# FLIGHT_HOURS 2.5: worst case (2.5 + 0.5) h x 0.907 USD/h = 2.72 USD; the worker stops itself at --max-hours 2.5.
# Then the watcher (ts3_rl_watch.py, detached, parent pid 1): scores every save as it lands, heartbeat
# train/logs/ts3rl_a1_heartbeat.txt.
set -e
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
RL=/Users/xiangzheng/code/robotics/microduck-sim/microduck_rl
MODAL=/Users/xiangzheng/code/robotics/omx-local/.venv/bin/modal
RUN=ts3rl-a1
python3 - "$T" <<'EOF'
import shutil, sys
from pathlib import Path
T = Path(sys.argv[1]); sys.path.insert(0, str(T))
from gate_lock import gate_lock
with gate_lock("student start asset s3AB_140"):   # train/init is inside the gate image's mount
    shutil.copyfile(T / "ckpt/s3AB_140/model_140.pt", T / "init/s3AB_140.pt")
EOF
cd $RL
FLIGHT_RUN=$RUN FLIGHT_HOURS=2.5 MICRODUCK_GPU=T4 $MODAL run --detach cmu/finetune/flight/flight_modal.py::run -- \
  --distill --delta universal5 --teacher-onnx /root/assets/init/ts3t_t3h_750.onnx \
  --manifest /root/assets/manifests/flightpack-none.json --resume-pt /root/assets/init/s3AB_140.pt \
  --max-iters 300 --max-hours 2.5 --save-interval 20 --warmup-iters 0 --beta-iters 1 --bptt-steps 100 --epochs 2 \
  --mb-envs 256 --stop-after 100 --seed 1 --drop-max 0.08 --core mamba --anchor-onnx /root/assets/walk61.onnx \
  --anchor-w 1.0 --anchor-head all --case-share 0.25 --stop-share 0.25 --gain-flag-col 59 --lr 0.0001 \
  --lr-final 0.0001 --rl-w 0.5 --bc-w 0.5 --bc-w-final 0.1 --rl-clip 0.1 --rl-std 0.1 --rl-critic-warmup 5 \
  > $T/logs/launch_$RUN.log 2>&1
grep -E "rate \\$|spawned|ap-" $T/logs/launch_$RUN.log | cut -c1-700
