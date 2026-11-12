#!/bin/zsh
set -x
VENV=/Users/shawnxiang/.venvs/oww
cd /Users/shawnxiang/mochi-train/oww
grep -o "section.*" setup3.log | head -2
uv pip install --python $VENV/bin/python "scipy==1.16.3"
$VENV/bin/python -c "import openwakeword, torch, torchaudio, speechbrain, audiomentations, torch_audiomentations, acoustics, pronouncing, datasets, piper_sample_generator, onnxruntime, numpy, scipy; from scipy.special import sph_harm; print('ok', torch.__version__, torchaudio.__version__, numpy.__version__, scipy.__version__, onnxruntime.__version__)"
$VENV/bin/python -c "
from piper.phonemize_espeak import EspeakPhonemizer
p = EspeakPhonemizer()
for t in ['mochee', 'mohchee', 'moh-chee', 'mow chee', 'moe chee', 'Mochi']:
    print(repr(t), p.phonemize('en-us', t))
"
uv pip freeze --python $VENV/bin/python > freeze.txt
echo SETUP4_DONE
