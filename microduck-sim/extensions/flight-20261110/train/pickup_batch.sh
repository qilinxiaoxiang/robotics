#!/bin/zsh
# Start a detached pickup-test batch on the Mac mini (mini_pickup_batch.sh) and return at once; the batch keeps
# running if this MacBook sleeps.
#   zsh pickup_batch.sh start <tag> <ckpt> <load> <d44|sd0> [<ckpt> <load> <delay> ...]
#   zsh pickup_batch.sh status <tag>       print the batch log
#   zsh pickup_batch.sh table <ckpt>...    pull results and print held / at end / falls for every load and delay
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
MIR=code/flight-train-mirror/robotics/microduck-sim/extensions/flight-20261110
case "$1" in
  start)
    shift; TAG=$1
    zsh $T/mini.sh push > /dev/null
    ssh mac-mini "cd $MIR && nohup zsh train/mini_pickup_batch.sh $* > /dev/null 2>&1 &"
    echo "started batch $TAG"
    ;;
  status)
    ssh mac-mini "cat $MIR/train/eval/batch_$2.log"
    ;;
  table)
    shift
    zsh $T/mini.sh pull > /dev/null
    cd $T && python3 pickup_table.py "$@"
    ;;
esac
