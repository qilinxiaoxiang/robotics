#!/bin/zsh
# Bounded CAD run with lock retry. Usage: run.sh <log-name> <script.py> [args...]
# Log: $EXT19_SCRATCH/<log-name>.log, runner report: $EXT19_SCRATCH/run-<log-name>.json
R=/Users/xiangzheng/code/robotics/microduck-sim/build-pack-20260913/redesign-20260913/head-redesign-20261008/run_bounded_cad.py
S=${EXT19_SCRATCH:-/private/tmp/claude-501/-Users-xiangzheng-code-robotics/cb2a1eef-7aa0-4728-afad-9518fb22c188/scratchpad/ext-v19}
MIB=${EXT19_MIB:-1536}
LIGHT=""
[ -n "$EXT19_LIGHT" ] && { LIGHT="--parallel-light"; MIB=512; }
name=$1; shift
cd "$(dirname "$0")"
for i in $(seq 1 60); do
  python3 $R $LIGHT --max-mib $MIB --seconds 1500 --wait-lock-seconds 60 --report $S/run-$name.json -- /tmp/microduck-cad-venv/bin/python "$@" > $S/$name.log 2>&1
  e=$?
  [ $e -ne 75 ] && break
  sleep 20
done
echo "$name exit $e"
python3 -c "import json;d=json.load(open('$S/run-$name.json'));print('rss',d.get('peakSampledTreeRssMiB'),'s',d.get('elapsedSeconds'),'guard',d.get('stoppedByGuard'))" 2>/dev/null
exit $e
