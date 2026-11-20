#!/bin/zsh
# Round 3, 2026-11-20 00:20 (coordinator's arm A): the leg big-step term on the faster gain-input teacher. Modal A10,
# detached spawned call, run ts3m-b625 (app microduck-flight-ts3m-b625): from t3g_625 under universal5tgb
# (universal5tg + leg_step_over above 0.3 rad at weight -200 + the runtime's joint-range clamp on the targets),
# learning-rate cap 5e-5, 100 critic warm-up iterations, track guard 2.0, 1000 iterations, save every 25,
# --max-hours 1.0, --max-dollars 2.00. Start noise 0.10, not 0.15: the term also taxes exploration noise (the
# difference of two noise draws at 0.15 exceeds 0.3 rad on 16 % of leg-joint ticks, about 5 reward per second; at
# 0.10 about 0.3). Then its watcher: gates on every 50th save from 100 on, no gate batch once metered reads 47.00
# or more; heartbeat logs/ts3m_b625_heartbeat.txt, folders ckpt/m3s_<iter>.
#   zsh train/ts3m_b625.sh "<budget note for the heartbeat's first line>"
set -e
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
zsh $T/ts3m_launch.sh ts3m-b625 universal5tgb ts3t_t3g_625.onnx 1000 1.0 1 --save-interval 25 --max-lr 0.00005 \
  --init-std 0.10 --max-dollars 2.00
python3 $T/detach.py $T/logs/ts3m_b625_watch.out python3 $T/ts3m_watch.py hb=ts3m_b625 every=ts3m-b625:50 min=100 \
  stopusd=47 "note=$1" 2.5 ts3m-b625=m3s
