#!/bin/zsh
# Start train/ts3_mini_chain.sh detached ON the Mac mini and return at once (2026-11-19: background shells of a
# session, and the ssh sessions they hold, are stopped about five minutes after the session's turn ends; a chain that
# must outlive a turn cannot be their child).
#   zsh train/ts3_mini_start.sh <name> <stage> [<stage> ...]
# Prints the chain's pid and its parent pid on the Mac mini (1 = launchd) and the heartbeat path.
set -e
LOCAL=/Users/xiangzheng/code/robotics/microduck-sim
REMOTE=code/flight-train-mirror/robotics/microduck-sim
T=$LOCAL/extensions/flight-20261110/train
source $T/ssh_guard.sh
NAME=$1; shift
zsh $T/ts3_audit.sh push
rsync -a $T/ts3_mini_chain.sh mac-mini:$REMOTE/extensions/flight-20261110/train/ts3_mini_chain.sh
ssh mac-mini "mkdir -p flight-heartbeat; nohup zsh $REMOTE/extensions/flight-20261110/train/ts3_mini_chain.sh $NAME $* > flight-heartbeat/${NAME}_chain.out 2>&1 < /dev/null &"
ssh mac-mini "sleep 2; pgrep -f 'ts3_mini_chain.sh $NAME' | while read p; do ps -o pid=,ppid=,command= -p \$p | cut -c1-120; done; echo heartbeat \$HOME/flight-heartbeat/$NAME.txt; cat flight-heartbeat/$NAME.txt"
