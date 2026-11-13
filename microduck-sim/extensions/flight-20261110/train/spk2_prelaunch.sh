#!/bin/zsh
# spk2 (seeing pick with the pack, load-scale curriculum) pre-launch checks on the Mac mini, one job at a time behind
# other sessions' sims (mini_seepick.sh / mini.sh), each under 10 minutes. LOAD s<x> = every episode at share x of the
# full pack (mass and inertia x x, make_payload_manifests.py's scaling).
# A 32-env part takes about 545 s on the shared mini (two hit the 590 s cap on 2026-11-12), so every 256-episode
# measurement is two waves of 8 parts x 16 envs (seeds 1-8, then 9-16), merged on the mini.
#   cliff   seepick61 at s = 0.05, 0.10, 0.15, 0.20 (s = 0 and 0.02 are done: out/spk_cliff_none_s0.0{0,2}.json)
#           plus a pinned no-pack control (load none, the spk1 path)               -> out/spk_cliff_none_s<x>.json
#   audit   fq2 stander and carried seepick61 at s = 0.02-0.20 (64 episodes; fq2 + seepick61 at s = 0), plus
#           seepick61, fq2 and carried at s = 0.5 and 1.0 (two 8 x 4-env waves): the fall-early audit's inputs
#                                                                                   -> out/spk_fea<TAG>_none_s<x>.json
#   zsh train/spk2_prelaunch.sh [cliff|audit|all] [TAG]   (TAG suffixes the audit files; SPK_CHECK_EXTRA passes e.g.
#                                                          "--fall-penalty 2" for the after-fix audit)
#   env SPK_CLIFF_S overrides the cliff loads (e.g. "0.10 0.15")
set -e
T=/Users/xiangzheng/code/robotics/microduck-sim/extensions/flight-20261110/train
WHAT=${1:-all}
TG=${2:-}
two_waves() {  # LOAD CASES ENVS OUTSTEM
  SPK_SEED0=0 zsh $T/mini_seepick.sh check $1 none $2 $3 8 ${4}A
  SPK_SEED0=8 zsh $T/mini_seepick.sh check $1 none $2 $3 8 ${4}B
  zsh $T/mini_seepick.sh merge spk_${4}_none_$1 spk_${4}A_none_$1 spk_${4}B_none_$1
}
zsh $T/mini_seepick.sh push
if [[ $WHAT == cliff || $WHAT == all ]]; then
  for s in ${=SPK_CLIFF_S:-0.05 0.10 0.15 0.20}; do
    echo "== cliff s$s $(date +%H:%M:%S)"
    two_waves s$s seepick 16 cliff
  done
  if [[ -z $SPK_CLIFF_S ]]; then
    echo "== cliff control load none $(date +%H:%M:%S)"
    two_waves none seepick 16 cliff
  fi
fi
if [[ $WHAT == audit || $WHAT == all ]]; then
  for s in 0.00 0.02 0.05 0.10 0.15 0.20; do
    CS=fq2,carried
    [[ $s == 0.00 ]] && CS=fq2,seepick
    echo "== audit$TG s$s $CS $(date +%H:%M:%S)"
    if [[ -n $TG ]]; then   # after a fix the start policy's own returns change too: seepick61 rerun at every s
      two_waves s$s seepick,fq2,carried 4 fea$TG
    else
      zsh $T/mini_seepick.sh check s$s none $CS 8 8 fea$TG
    fi
  done
  for s in 0.50 1.00; do
    echo "== audit$TG s$s seepick,fq2,carried $(date +%H:%M:%S)"
    two_waves s$s seepick,fq2,carried 4 fea$TG
  done
fi
echo "== done $(date +%H:%M:%S)"
