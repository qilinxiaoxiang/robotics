#!/bin/zsh
args=(${(s: :)1}); tag=${args[-1]}; args=(${args[1,-2]})
cd "$(dirname "$0")/.." && /usr/bin/time -p ~/.venvs/microduck-dyn/bin/python sole_thickness_sim.py "${args[@]}" --model asbuilt --volt 7.0 --drop 0.04 --walk-at 4 --walk-s 8 > "sweep/$tag.out" 2> "sweep/$tag.err"; echo "$tag exit $?" >> sweep/done.log
