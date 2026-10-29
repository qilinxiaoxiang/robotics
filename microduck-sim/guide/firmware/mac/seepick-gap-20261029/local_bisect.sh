#!/bin/zsh
# The single-factor runs of the gap study on the matched centre-box case, in order (one sim at a time on the MacBook).
HERE=${0:A:h}
$HERE/run_single.sh refit --bvh-refit
$HERE/run_single.sh refit_tjaw --bvh-refit --sp-jaw-current 1470 --sp-jaw-kp 400
$HERE/run_single.sh refit_mu15 --bvh-refit --sp-beak-mu 1.5
$HERE/run_single.sh refit_tjaw_mu15 --bvh-refit --sp-jaw-current 1470 --sp-jaw-kp 400 --sp-beak-mu 1.5
$HERE/run_single.sh refit_jaw150 --bvh-refit --sp-jaw-current 150
$HERE/run_single.sh refit_jaw300 --bvh-refit --sp-jaw-current 300
$HERE/run_single.sh refit_comp --bvh-refit --compensation
$HERE/run_single.sh refit_nocap --bvh-refit --sp-no-cap
$HERE/run_single.sh refit_realio --bvh-refit --drop 0.04 --sp-camera-delay 0.29 --sp-camera-drop 0.037
