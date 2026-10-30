#!/bin/bash
# Put namecall.py and the pet/express package it imports on the Radxa Cubie A7Z, next to the brain install_teleop.sh
# made (~/rt/microduck-sim/guide/firmware/mac/namecall.py and ~/rt/pet/express). Run on the Mac:
#
#   microduck-sim/guide/firmware/mac/namecall-20261029/install_namecall.sh      # A7Z_HOST=a7z by default
#
# Idempotent (rsync --checksum). Never moves the robot: no servo traffic, no restart of a running brain, no start of
# namecall.py. Afterwards it checks on the A7Z that the duck-policy venv imports namecall (numpy, onnxruntime,
# duck_sound, pet.express), that the sndi2s0 capture card exists and that the sounds folder has calls.
set -euo pipefail

HOST=${A7Z_HOST:-a7z}
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../../../.." && pwd)                 # .../robotics
REMOTE=${REMOTE_ROOT:-rt}                                # ~/rt on the A7Z: ~/rt/microduck-sim/..., ~/rt/pet/...
VENV=${A7Z_VENV:-/home/radxa/.venvs/duck-policy}

quiet() { grep -v -E "quantum|store now|upgraded" || true; }

cd "$ROOT"
for f in microduck-sim/guide/firmware/mac/namecall.py microduck-sim/guide/firmware/mac/duck_sound.py pet/__init__.py \
         pet/express/__init__.py pet/express/cards/duck.json; do
  [ -f "$f" ] || { echo "missing locally: $ROOT/$f" >&2; exit 1; }
done

echo "== copy"
rsync -a --checksum --relative --itemize-changes \
  microduck-sim/guide/firmware/mac/namecall.py \
  microduck-sim/guide/firmware/mac/test_namecall_detector.py \
  microduck-sim/guide/firmware/mac/test_namecall_direction.py \
  microduck-sim/guide/firmware/mac/test_namecall_chain.py \
  microduck-sim/guide/firmware/mac/test_namecall_kws.py \
  microduck-sim/guide/firmware/mac/namecall-20261029/NAMECALL.md \
  microduck-sim/guide/firmware/mac/namecall-20261029/keywords_mochi.txt \
  microduck-sim/guide/firmware/mac/facefind.py \
  microduck-sim/guide/firmware/mac/personfind.py \
  microduck-sim/guide/firmware/mac/test_personfind.py \
  microduck-sim/guide/firmware/mac/ownkws.py \
  microduck-sim/guide/firmware/mac/life_log.py \
  microduck-sim/guide/firmware/mac/namecall-20261029/models/mochi_own.npz \
  microduck-sim/guide/firmware/mac/namecall-20261029/bearing_prior.json \
  microduck-sim/guide/firmware/mac/namecall-20261029/models/oww/*.onnx \
  pet/__init__.py pet/express/*.py pet/express/cards/duck.json \
  pet/identity/__init__.py pet/identity/face.py pet/identity/models/buffalo_sc/det_500m.onnx pet/identity/models/buffalo_sc/w600k_mbf.onnx \
  pet/identity/models/yolox/yolox_tiny.onnx \
  --exclude='__pycache__' \
  "$HOST:$REMOTE/" 2>&1 | quiet

echo "== checks on $HOST"
ssh "$HOST" "cd ~/$REMOTE/microduck-sim/guide/firmware/mac && \
  for f in namecall.py duck_sound.py facefind.py personfind.py ownkws.py namecall-20261029/models/mochi_own.npz namecall-20261029/bearing_prior.json ../../../../pet/express/express.py; do sha256sum \"\$f\"; done && \
  $VENV/bin/python -c 'import namecall, numpy; print(\"namecall imports ok, numpy\", numpy.__version__); \
    print(\"policy default head\", namecall.policy_default_head())' && \
  $VENV/bin/python -c 'import ownkws; m = ownkws.OwnModel(); print(\"own name spotter:\", m.classes, \"threshold\", m.threshold)' && \
  $VENV/bin/python -c 'import facefind; from pet.identity.face import FacePipeline; FacePipeline(); print(\"face finder: SCRFD model loads\")' && \
  $VENV/bin/python -c 'import personfind; personfind.PersonDetector(); print(\"person finder: YOLOX-Tiny loads\")' && \
  ( $VENV/bin/python -c 'import sherpa_onnx, namecall; m = namecall.find_kws_model(); \
    print(\"name mode: sherpa-onnx\", sherpa_onnx.__version__, \"model\", m or \"MISSING (~/rt/models/kws/)\")' \
    2>/dev/null || echo 'name mode: NO sherpa-onnx (pip install sherpa-onnx==2.0.0 in the venv); --any-voice still works' ) && \
  ( [ -e /proc/asound/sndi2s0 ] && echo \"sndi2s0 card: \$(readlink /proc/asound/sndi2s0)\" || echo 'NO sndi2s0 card (I2S0 overlay not loaded)' ) && \
  echo \"sounds: \$(ls sounds/*.wav 2>/dev/null | wc -l) calls\" && \
  ( which arecord aplay >/dev/null && echo 'arecord/aplay present' || echo 'NO arecord/aplay (apt install alsa-utils)' )" 2>&1 | quiet
echo "== local sha256 for comparison"
shasum -a 256 microduck-sim/guide/firmware/mac/namecall.py microduck-sim/guide/firmware/mac/duck_sound.py pet/express/express.py
echo "== done: start order and the first test are in $HERE/NAMECALL.md"
