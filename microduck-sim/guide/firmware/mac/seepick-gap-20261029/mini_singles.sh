#!/bin/zsh
H=~/sims/seepick-gap-20261027/rt/microduck-sim/guide/firmware/mac/seepick-gap-20261029
nice -n 10 $H/run_single.sh refit_sticky --bvh-refit --sp-cone elliptic --sp-impratio 10
nice -n 10 $H/run_single.sh refit_ball --bvh-refit --sp-shape ball --sp-half 0.0065 0.0065 0.0065
nice -n 10 $H/run_single.sh refit_ball_sticky --bvh-refit --sp-cone elliptic --sp-impratio 10 --sp-shape ball --sp-half 0.0065 0.0065 0.0065
nice -n 10 $H/run_single.sh refit_ball_tjaw --bvh-refit --sp-jaw-current 1470 --sp-jaw-kp 400 --sp-shape ball --sp-half 0.0065 0.0065 0.0065
nice -n 10 $H/run_single.sh refit_sticky_realio --bvh-refit --sp-cone elliptic --sp-impratio 10 --drop 0.04 --sp-camera-delay 0.29 --sp-camera-drop 0.037
nice -n 10 $H/run_single.sh refit_ball_sticky_mu035 --bvh-refit --sp-cone elliptic --sp-impratio 10 --sp-shape ball --sp-half 0.0065 0.0065 0.0065 --sp-friction 0.35
nice -n 10 $H/run_single.sh refit_sticky_mu035 --bvh-refit --sp-cone elliptic --sp-impratio 10 --sp-friction 0.35
