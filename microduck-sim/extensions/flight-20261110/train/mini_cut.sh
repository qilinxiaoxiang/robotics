#!/bin/zsh
# Runs ON the Mac mini (2026-11-18 thrash: acceptance, check B and a smoke ran together). Stops this mirror's
# acceptance / style / adapt jobs and their worker processes, keeps everything whose command line carries the keep
# pattern (default: check B result files eval/bc_), then lists what is left and prints swap and load.
#   zsh train/mini_cut.sh [keep-pattern]         run with the literal word NONE to keep nothing of this mirror
KEEP=${1:-eval/bc_}
MIRROR=flight-train-mirror
kill_tree() {
  for c in $(pgrep -P $1); do kill_tree $c; done
  kill $1 2>/dev/null
}
# top-level jobs of this mirror: the zsh -c wrappers mini.sh / ts_round.sh start, and their python children
for p in $(pgrep -f "flight_eval.py|style_eval.py|adapt_eval.py|accept_|distill_worker.py|flight_worker.py"); do
  cmd=$(ps -o command= -p $p)
  cwd=$(lsof -a -d cwd -p $p -Fn 2>/dev/null | grep '^n' | cut -c2-)
  case "$cwd$cmd" in *$MIRROR*) ;; *) continue ;; esac
  case "$cmd" in *$KEEP*) continue ;; esac
  echo "stop $p $(echo $cmd | cut -c1-110)"
  kill_tree $p
done
sleep 3
# orphan multiprocessing workers (parent gone) whose working directory is this mirror
for p in $(pgrep -f "multiprocessing"); do
  [ "$(ps -o ppid= -p $p | tr -d ' ')" = "1" ] || continue
  cwd=$(lsof -a -d cwd -p $p -Fn 2>/dev/null | grep '^n' | cut -c2-)
  case "$cwd" in *$MIRROR*) echo "orphan $p stopped"; kill $p ;; esac
done
sleep 2
echo "left: $(pgrep -f 'flight-sim/bin/python|\.venv/bin/python' | wc -l | tr -d ' ') python processes"
pgrep -fl "flight_eval.py|style_eval.py|adapt_eval.py|distill_worker.py" | cut -c1-150 | grep -v "multiprocessing" | head -8
sysctl vm.swapusage
uptime
