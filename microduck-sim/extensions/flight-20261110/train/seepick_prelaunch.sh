#!/bin/zsh
# Pre-launch checks of the seeing-pick pack fine-tune (FP-R7) in its training env, all on the Mac mini, one job at a
# time (mini_seepick.sh waits behind other sessions' sims), each job under 10 minutes.
#   start: seepick61 at each load, 256 episodes (8 parts x 32 envs), on the fine-tune's model (none) and on
#          sp-b-1027's training model (plugged) at no pack and full pack -> out/spk_start_<base>_<load>.json
#   audit: stand61, fq2, blind bow, carried seepick61 at each load, 128 episodes -> out/spk_audit_<case>_none_<load>.json
#   zsh train/seepick_prelaunch.sh [start|audit|all]
set -e
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
WHAT=${1:-all}
zsh $T/mini_seepick.sh push
[ $WHAT = audit ] || for spec in "none none" "nobatt none" "full none" "none plugged" "full plugged"; do
  set -- ${=spec}
  echo "== start $1 $2 $(date +%H:%M:%S)"
  zsh $T/mini_seepick.sh check $1 $2 seepick 32 8 start
done
# one case per job: 8 parts x 32 envs of one case took 510 s on 2026-11-12 (about 27 ms per env-step on one core, the
# mini's other load included), so 8 x 16 envs of one case stays near 260 s and two cases would pass the 590 s cap
[ $WHAT = start ] || for ld in none nobatt full; do
  CS=(stand61 fq2 blind)
  [ $ld != none ] && CS+=(carried)
  for c in $CS; do
    echo "== audit $ld $c $(date +%H:%M:%S)"
    zsh $T/mini_seepick.sh check $ld none $c 16 8 audit_$c
  done
done
echo "ALL DONE $(date +%H:%M:%S)"
