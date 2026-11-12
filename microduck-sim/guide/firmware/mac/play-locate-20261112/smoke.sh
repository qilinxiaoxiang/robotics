#!/bin/bash
# Mac mini: one recorded walk replayed with and without servo-to-link play on the leg joints.
cd "$(dirname "$0")/.."
PY="$HOME/.venvs/microduck-dyn/bin/python"
A=(--model asbuilt --volt 7.4 --drop 0.033 --stand-s 1.0 --walk-at 3.0 --until 6.63 --walk-s 0
   --manifest "$HOME/code/robotics/microduck-sim/microduck_rl/cmu/model/manifests/battery-20261104.json"
   --cmd-replay "$HOME/duck-walks/scorecard-auto/duck_wired_log_app1102-010842-1793639592.46-walk.9c28f96b.replay.json")
for jp in 0 2 4; do
  X=()
  [ "$jp" != 0 ] && X=(--joint-play "$jp")
  echo "== play $jp deg"
  "$PY" brain_sim_check.py "${A[@]}" "${X[@]}" --tick-log "/tmp/jp$jp.jsonl" 2>&1 | grep -v Warn | tail -1 > "/tmp/jp$jp.out"; python3 -c "import json,sys; d=json.loads(open(sys.argv[1]).read()); print({k: d.get(k) for k in (\"fell_at\", \"max_tilt\", \"action_jumps\", \"max_action\", \"dist_x\")})" "/tmp/jp$jp.out"
done
