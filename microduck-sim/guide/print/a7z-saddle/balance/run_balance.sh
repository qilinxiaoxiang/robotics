#!/bin/zsh
# Balance runs for the saddle manifest (same protocol as a7z-slice-20261022/run_balance.sh): walk61 0.25 m/s x3 seeds, stand61 20 s, open-loop stand.
cd "$(dirname "$0")" || exit 1
PY=~/.venvs/microduck-dyn/bin/python
BSC=../../../firmware/mac/brain_sim_check.py
v=saddle; M=manifest-$v.json
for s in 0 1 2; do
  echo "== $v walk seed $s $(date +%T)"
  $PY $BSC --model asbuilt --manifest $M --volt 7.0 --drop 0.04 --vx 0.25 --walk-at 4 --walk-s 6 --seed $s > $v-walk-s$s.json 2> $v-walk-s$s.err
done
echo "== $v stand61 $(date +%T)"
$PY $BSC --model asbuilt --manifest $M --volt 7.0 --drop 0.04 --vx 0 --walk-at 1 --walk-s 20 --seed 0 > $v-stand61.json 2> $v-stand61.err
echo "== $v openloop $(date +%T)"
$PY $BSC --model asbuilt --manifest $M --volt 7.0 --drop 0.04 --vx 0 --walk-at 12 --walk-s 0.5 --seed 0 > $v-openloop.json 2> $v-openloop.err
echo "== done $(date +%T)"
