#!/bin/zsh
# 2026-11-20 04:55 batch, run ON the Mac mini inside the flight-20261110 folder under mini.sh run ($PY set):
#   zsh train/mini.sh run 'zsh train/ts3_batch_s3a_f1.sh <part>'      part = f1 | stop | jump | first
# f1:    pack-flag student smk_f1_232 at the stop (gain 200, 20 seeds), flag fed, heading hold on and off; and the
#        same student without the flag fed (what the flag itself changes)
# stop:  s3a_60 at the stop, heading hold on and off; then seeds 0 and 1 traced from 15 s
# jump:  s3a_60 and the deployed walk61 in the gate's none_g400_stand cell: which joints step
# first: first-2-seconds counts for s3a_60 against s3a_160
OFF='{"HEADING_KP": 0, "HEADING_KI": 0}'
case "$1" in
  f1)
    echo "flag fed, heading hold on"
    FLIGHT_OBS_SET=60:1.0 $PY train/ts3_stop_where.py smk_f1_232 count=20 kp=200 2>&1 | tail -2
    echo "flag fed, heading hold off"
    FLIGHT_OBS_SET=60:1.0 FLIGHT_BRAIN_SET=$OFF $PY train/ts3_stop_where.py smk_f1_232 count=20 kp=200 2>&1 | tail -1
    echo "flag NOT fed (column left at 0), heading hold on"
    $PY train/ts3_stop_where.py smk_f1_232 count=20 kp=200 2>&1 | tail -1
    ;;
  stop)
    echo "heading hold on"
    $PY train/ts3_stop_where.py s3a_60 count=20 kp=200 2>&1 | tail -1
    echo "heading hold off"
    FLIGHT_BRAIN_SET=$OFF $PY train/ts3_stop_where.py s3a_60 count=20 kp=200 2>&1 | tail -1
    $PY train/ts3_stop_where.py s3a_60 0 1 kp=200 from=14 2>&1 | grep -v Warning | cut -c1-330
    ;;
  jump)
    for D in s3a_60 walk61; do
      echo "policy $D, none, gain 400, standing"
      TS3_KIND=stand $PY train/ts3_jump_where.py $D none 0 --kp-rl 400 2>&1 | grep -v Warning | cut -c1-700
    done
    ;;
  first)
    $PY train/ts3_first2s.py 10 s3a_60 s3a_160 2>&1 | grep -v Warning | cut -c1-600
    ;;
esac
