#!/bin/zsh
# Round 3, 2026-11-19 23:30 (coordinator lifted "no new Modal training arms" for this one arm): the ts3-teach-k
# continuation on the faster gain-input teacher. Modal A10, detached spawned call, run ts3m-k625 (app
# microduck-flight-ts3m-k625): from t3g_625 (ts_start start, 0.19 m/s with the pack, fails only pack-walk jumps)
# under universal5tgs, learning-rate cap 5e-5, start noise 0.15, 100 critic warm-up iterations, track guard 2.0,
# 1000 iterations, save every 25, --max-hours 1.0, --max-dollars 2.00. Then its watcher: gates on every 50th save
# from 100 on, no gate batch once metered reads 47.00 or more; heartbeat logs/ts3m_k625_heartbeat.txt, ckpt/m3k_<iter>.
#   zsh train/ts3m_k625.sh "<budget note for the heartbeat's first line>"
set -e
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
zsh $T/ts3m_launch.sh ts3m-k625 universal5tgs ts3t_t3g_625.onnx 1000 1.0 1 --save-interval 25 --max-lr 0.00005 \
  --init-std 0.15 --max-dollars 2.00
python3 $T/detach.py $T/logs/ts3m_k625_watch.out python3 $T/ts3m_watch.py hb=ts3m_k625 every=ts3m-k625:50 min=100 \
  stopusd=47 "note=$1" 2.5 ts3m-k625=m3k
