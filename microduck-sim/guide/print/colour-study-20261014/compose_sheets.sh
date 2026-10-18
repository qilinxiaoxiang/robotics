#!/usr/bin/env bash
# Tile and label the renders into compare sheets with ../back-plate/layout-D-20261014/compose.py.
set -euo pipefail
cd "$(dirname "$0")"
PY=/Users/xiangzheng/.venvs/microduck-dyn/bin/python; C=../back-plate/layout-D-20261014/compose.py; R=renders
caption() { case $1 in
  front34) echo "Front 3/4 at HOME. Printed PLA colours (colour_as_built.json); A is the robot today";;
  rear34) echo "Rear 3/4 at HOME; layout F converter box in orange (released V1.11, not printed yet)";;
  side) echo "Right side at HOME";; esac; }
for v in front34 rear34 side; do
  "$PY" "$C" "$R/compare-$v.png" "$(caption $v)" "A as built=$R/A-$v.png" "B white shells+thighs=$R/B-$v.png" \
    "C white shells+thighs+cap=$R/C-$v.png" "D white cap only=$R/D-$v.png" "E white shells+cap=$R/E-$v.png"
done
for k in A B C D E; do
  lbl=$(python3 -c "import json;print(json.load(open('spec-$k.json'))['label'])")
  "$PY" "$C" "$R/option-$k.png" "$lbl: front 3/4, rear 3/4, right side" "$lbl=$R/$k-front34.png" "rear 3/4=$R/$k-rear34.png" "side=$R/$k-side.png"
done
"$PY" -c "
from PIL import Image; import numpy as np
ims=[np.array(Image.open(f'$R/compare-{v}.png').convert('RGB')) for v in ('front34','rear34','side')]
Image.fromarray(np.vstack(ims)).save('$R/compare-all.png'); print('ok', '$R/compare-all.png')"
