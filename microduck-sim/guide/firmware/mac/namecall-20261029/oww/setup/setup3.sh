#!/bin/zsh
# pin scipy (acoustics needs scipy.special.sph_harm, removed in 1.17) and torch/torchaudio 2.5.1 (torchaudio>=2.9 needs torchcodec/ffmpeg for load)
set -x
VENV=/Users/shawnxiang/.venvs/oww
cd /Users/shawnxiang/mochi-train/oww
uv pip install --python $VENV/bin/python "scipy==1.15.3" "torch==2.5.1" "torchaudio==2.5.1"
$VENV/bin/python -c "import openwakeword, torch, torchaudio, speechbrain, audiomentations, torch_audiomentations, acoustics, pronouncing, datasets, piper_sample_generator, onnxruntime, numpy, scipy; print('ok', torch.__version__, torchaudio.__version__, numpy.__version__, scipy.__version__, onnxruntime.__version__)"
$VENV/bin/python -c "
import sys; sys.path.insert(0, '/Users/shawnxiang/mochi-train/oww/psg_shim')
import generate_samples; print('shim ok')
from piper.phonemize_espeak import EspeakPhonemizer
p = EspeakPhonemizer()
for t in ['mochi', 'mochi.', 'moh chee', 'mo chee', 'mocha', 'moshi']:
    print(repr(t), p.phonemize('en-us', t))
"
uv pip freeze --python $VENV/bin/python > freeze.txt
grep -iE "piper|torch|scipy|numpy|onnx|openwake" freeze.txt
echo SETUP3_DONE
