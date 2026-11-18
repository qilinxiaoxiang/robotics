#!/bin/zsh
# Runs ON the Mac mini. One simulation job of this mirror at a time, and none on a loaded machine (2026-11-18: an
# acceptance batch, check B and a smoke ran together, 33 workers on 16 GB RAM filled 21 GB of swap and the machine
# kernel-panicked at 18:10).
#   zsh mini_lock.sh acquire <holder pid>     wait for the lock (up to 90 min), take it, then the pre-flight
#   zsh mini_lock.sh release <holder pid>     give the lock back (only its holder's)
#   zsh mini_lock.sh run <command ...>        acquire, run the command, release; the command's exit code
# Lock: ~/.flight-mirror-sim.lock holding the holder's pid; a lock whose pid is gone is stale and is cleared.
# Pre-flight (after the lock is held): refuses, exit 4, when swap used is over 4096 MB or more than 10 simulation
# python processes (flight-sim venv or a .venv python) already run. It looks six times, 30 s apart, before refusing.
# MINI_LOCK_TEST_SWAP_MB / MINI_LOCK_TEST_PROCS force the readings (refusal test).
LOCK=$HOME/.flight-mirror-sim.lock
SWAP_MAX_MB=4096
PROC_MAX=10

swap_mb() {
  [ -n "$MINI_LOCK_TEST_SWAP_MB" ] && { echo $MINI_LOCK_TEST_SWAP_MB; return; }
  sysctl -n vm.swapusage | sed -E 's/.*used = ([0-9.]+)M.*/\1/' | cut -d. -f1
}
procs() {
  [ -n "$MINI_LOCK_TEST_PROCS" ] && { echo $MINI_LOCK_TEST_PROCS; return; }
  pgrep -f "venvs/flight-sim/bin/python|\.venv/bin/python" | wc -l | tr -d ' '
}
acquire() {
  local me=$1 i h
  for i in $(seq 1 540); do
    if ( set -o noclobber; echo $me > $LOCK ) 2>/dev/null; then
      break
    fi
    h=$(cat $LOCK 2>/dev/null)
    if [ -z "$h" ] || ! kill -0 $h 2>/dev/null; then
      echo "[mini_lock] stale lock of pid ${h:-?} cleared" >&2
      rm -f $HOME/.flight-mirror-sim.lock
      continue
    fi
    [ $i -eq 540 ] && { echo "[mini_lock] still held by pid $h after 90 min" >&2; return 3; }
    sleep 10
  done
  for i in 1 2 3 4 5 6; do
    local s=$(swap_mb) p=$(procs)
    if [ "$s" -le $SWAP_MAX_MB ] && [ "$p" -le $PROC_MAX ]; then
      return 0
    fi
    echo "[mini_lock] pre-flight: swap used $s MB (limit $SWAP_MAX_MB), simulation pythons $p (limit $PROC_MAX), look $i of 6" >&2
    [ $i -lt 6 ] && sleep 30
  done
  release $me
  echo "[mini_lock] REFUSED: the machine is loaded; nothing was started" >&2
  return 4
}
release() {
  [ "$(cat $LOCK 2>/dev/null)" = "$1" ] && rm -f $HOME/.flight-mirror-sim.lock
  return 0
}
case "$1" in
  acquire) acquire $2 ;;
  release) release $2 ;;
  run)
    shift
    acquire $$ || exit $?
    "$@"
    rc=$?
    release $$
    exit $rc
    ;;
esac
