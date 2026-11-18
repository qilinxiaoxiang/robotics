# Sourced by train/ts_round.sh and train/mini.sh: ssh, scp and rsync to the Mac mini that cannot hang.
# 2026-11-18 (09:36 and 12:01): a remote job ended but the local ssh sat on a dead connection, 30 minutes the second
# time. Keepalives end a dead connection in about a minute (15 s x 4); a local wall-clock limit above the remote jobs'
# own `timeout 590` ends anything else; a lost connection (ssh 255) or the limit (SIGALRM, 142) is retried once, after
# the mirror's remote jobs have ended, so a retry never runs beside the first attempt.
SSH_GUARD_OPTS=(-o ServerAliveInterval=15 -o ServerAliveCountMax=4 -o ConnectTimeout=20)
SSH_GUARD_LIMIT=${SSH_GUARD_LIMIT:-640}
SSH_GUARD_JOBS='style_eval.py|flight_eval.py|flight_audit.py|_smoke.py|distill_worker.py|adapt_eval.py|bend_accept.py'

_guarded() {
  # _guarded <limit s> <command...>: run under a local alarm; one retry on a lost connection or the limit
  local lim=$1 rc try
  shift
  for try in 1 2; do
    perl -e 'alarm shift; exec @ARGV' $lim "$@"
    rc=$?
    if [ $rc -ne 255 ] && [ $rc -ne 142 ]; then return $rc; fi
    echo "[ssh_guard] $1 lost its connection or passed ${lim} s (rc $rc), attempt $try" >&2
    [ $try -eq 2 ] && break
    perl -e 'alarm shift; exec @ARGV' 660 ssh $SSH_GUARD_OPTS mac-mini \
      "for i in \$(seq 1 120); do pgrep -f '$SSH_GUARD_JOBS' > /dev/null || break; sleep 5; done" || true
  done
  return $rc
}

ssh() { _guarded $SSH_GUARD_LIMIT ssh $SSH_GUARD_OPTS "$@"; }
scp() { _guarded 300 scp $SSH_GUARD_OPTS "$@"; }
rsync() { _guarded 600 rsync -e "ssh ${SSH_GUARD_OPTS[*]}" "$@"; }
