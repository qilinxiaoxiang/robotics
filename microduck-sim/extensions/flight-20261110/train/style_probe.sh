#!/bin/zsh
# Gait style (toe-out), bend and head-motion cases for UNIVERSAL-PLAN.md, run on the Mac mini through mini.sh:
#   zsh train/mini.sh push && zsh train/mini.sh run 'zsh train/style_probe.sh toe|bend|head [episodes] [workers]' && zsh train/mini.sh pull
# Output: train/eval/st_<name>.json (style_eval.py). Policies: bend_fq2 = fq2 1999 in both slots; bend_fs1 = fs1 1950
# stand slot + fw1 1250 walk slot; bend_spec = today's stand61/walk61. Each models dir also holds today's
# groundpick61.onnx and seepick61.onnx (the runtime's bend policies), so a bend runs exactly as walk_brain does it.
set -e
EP=${2:-20}
W=${3:-8}
PACK=train/manifests/flightpack-load100.json
NONE=train/manifests/flightpack-load000.json
S0="--stand-s 0"
run() {  # name models manifest case extra
  $PY train/style_eval.py --name $1 --models $2 --manifest $3 --case $4 --episodes $EP --workers $W --extra="$5" \
    --out train/eval/st_$1.json 2>&1 | tail -1
}
case "$1" in
  toe)
    run toe_fq2_pack_walk train/ckpt/bend_fq2 $PACK walk "$S0"
    run toe_fq2_pack_stand train/ckpt/bend_fq2 $PACK stand "$S0"
    run toe_spec_none_walk train/ckpt/bend_spec $NONE walk ""
    run toe_spec_none_stand train/ckpt/bend_spec $NONE stand ""
    run toe_fq2_none_walk train/ckpt/bend_fq2 $NONE walk ""
    ;;
  bend)
    # D-027 bend as the runtime does it: stand slot until 2 s, then groundpick61 to phase 0.33 (the logged pick-pose
    # phase, CURRENT-STATE head_pose_vs_chain_scan), held 4 s, rise, back to the stand slot (PICKUP.md command)
    GP="--walk-at 1 --walk-s 0 --gp-at 2 --gp-phase 0.33 --gp-hold-s 4"
    # the seeing pick (seepick61, T2) with its drawn object at the trained spot, then back to the stand slot
    SP="--walk-at 1 --walk-s 0 --sp-at 2"
    for p in fq2 fs1; do
      run bend_gp_${p}_pack train/ckpt/bend_$p $PACK stand "$S0 $GP"
      run bend_sp_${p}_pack train/ckpt/bend_$p $PACK stand "$S0 $SP"
    done
    run bend_gp_spec_none train/ckpt/bend_spec $NONE stand "$GP"
    run bend_sp_spec_none train/ckpt/bend_spec $NONE stand "$SP"
    ;;
  head)
    SCAN="--dance train/specs/head_scan_dance.json"
    for p in fq2 fs1; do
      run head_scan_${p}_pack train/ckpt/bend_$p $PACK stand "$S0 $SCAN"
      run head_quack_${p}_pack train/ckpt/bend_$p $PACK stand "$S0 --quack-at 4 8 12"
    done
    run head_walk05_fq2_pack train/ckpt/bend_fq2 $PACK walk "$S0 --head-pitch 0.5"
    run head_walk11_fq2_pack train/ckpt/bend_fq2 $PACK walk "$S0 --head-pitch 1.1"
    run head_scan_spec_none train/ckpt/bend_spec $NONE stand "$SCAN"
    run head_quack_spec_none train/ckpt/bend_spec $NONE stand "--quack-at 4 8 12"
    run head_walk05_spec_none train/ckpt/bend_spec $NONE walk "--head-pitch 0.5"
    run head_walk11_spec_none train/ckpt/bend_spec $NONE walk "--head-pitch 1.1"
    ;;
esac
