#!/bin/zsh
# install training packages into ~/.venvs/oww (nothing in duck-see changes)
set -x
cd /Users/shawnxiang/mochi-train/oww
VENV=/Users/shawnxiang/.venvs/oww
uv pip install --python $VENV/bin/python torch torchaudio torchinfo torchmetrics'<1' speechbrain'<1' audiomentations==0.33.0 torch-audiomentations acoustics pyyaml pronouncing datasets deep-phonemizer==0.0.19 mutagen onnx onnxruntime webrtcvad 'numpy<2' scipy scikit-learn tqdm requests soundfile
uv pip install --python $VENV/bin/python --no-deps -e ./openWakeWord
uv pip install --python $VENV/bin/python piper-tts==1.3.0
uv pip install --python $VENV/bin/python --no-deps -e ./piper-sample-generator
$VENV/bin/python -c "import openwakeword, torch, torchaudio, speechbrain, audiomentations, torch_audiomentations, acoustics, pronouncing, datasets, piper_sample_generator, onnxruntime, numpy; print('ok', torch.__version__, numpy.__version__, onnxruntime.__version__)"
uv pip freeze --python $VENV/bin/python > freeze.txt
echo SETUP2_DONE
