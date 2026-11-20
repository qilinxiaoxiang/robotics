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
  g1)
    # gain-flag student smk_g1_232 (column 59 = kp/200 - 1: 0 at 200, 0.5 at 300, 1 at 400), control smk_c0_232,
    # stop-case student smk_c1_232; then standing without the pack at gain 400 and the first 2 s with the pack
    echo "g1 gain 200 heading on"; $PY train/ts3_stop_where.py smk_g1_232 count=20 kp=200 2>&1 | tail -1
    echo "g1 gain 200 heading off"; FLIGHT_BRAIN_SET=$OFF $PY train/ts3_stop_where.py smk_g1_232 count=20 kp=200 2>&1 | tail -1
    echo "g1 gain 300 flag 0.5"; FLIGHT_OBS_SET=59:0.5 $PY train/ts3_stop_where.py smk_g1_232 count=20 kp=300 2>&1 | tail -2
    echo "g1 gain 400 flag 1.0"; FLIGHT_OBS_SET=59:1.0 $PY train/ts3_stop_where.py smk_g1_232 count=20 kp=400 2>&1 | tail -1
    echo "g1 gain 200 with the WRONG flag 1.0"; FLIGHT_OBS_SET=59:1.0 $PY train/ts3_stop_where.py smk_g1_232 count=20 kp=200 2>&1 | tail -1
    for K in 300 400; do echo "c1 gain $K"; $PY train/ts3_stop_where.py smk_c1_232 count=20 kp=$K 2>&1 | tail -1; done
    for D in smk_g1_232 s3h_160 smk_c1_232; do for S in 0 1 2; do
      echo "$D seed $S none gain 400 standing"
      FL=""; [ $D = smk_g1_232 ] && FL=59:1.0
      FLIGHT_OBS_SET=$FL TS3_SEED=$S TS3_KIND=stand $PY train/ts3_jump_where.py $D none 0 --kp-rl 400 2>&1 | grep "^{" | grep -oE '"jumps": [0-9]+|"touch_downs": [0-9]+|"fell_at": [a-z0-9.]+' | tr "\n" " "; echo
    done; done
    $PY train/ts3_first2s.py 10 smk_g1_232 smk_c0_232 2>&1 | grep -v Warning | grep nominal | cut -c1-400
    ;;
  h1)
    # A+B student smk_h1_232 (gain flag in column 59 and the pack stop case)
    for K in 200 300 400; do
      F=$(( (K - 200) / 200.0 ))
      echo "h1 gain $K flag $F heading on"; FLIGHT_OBS_SET=59:$F $PY train/ts3_stop_where.py smk_h1_232 count=20 kp=$K 2>&1 | tail -1
    done
    echo "h1 gain 200 heading off"; FLIGHT_BRAIN_SET=$OFF $PY train/ts3_stop_where.py smk_h1_232 count=20 kp=200 2>&1 | tail -1
    for S in 0 1 2; do
      echo "smk_h1_232 seed $S none gain 400 standing"
      FLIGHT_OBS_SET=59:1.0 TS3_SEED=$S TS3_KIND=stand $PY train/ts3_jump_where.py smk_h1_232 none 0 --kp-rl 400 2>&1 | grep "^{" | grep -oE '"jumps": [0-9]+|"touch_downs": [0-9]+|"fell_at": [a-z0-9.]+' | tr "\n" " "; echo
    done
    $PY train/ts3_first2s.py 10 walk61 smk_c0_232 smk_c1_232 smk_g1_232 smk_h1_232 2>&1 | grep -v Warning | grep nominal | cut -c1-400
    ;;
  first)
    $PY train/ts3_first2s.py 10 s3a_60 s3a_160 2>&1 | grep -v Warning | cut -c1-600
    ;;
esac
