#!/bin/zsh
set -x
VENV=/Users/shawnxiang/.venvs/oww
cd /Users/shawnxiang/mochi-train/oww
uv pip install --python $VENV/bin/python "numpy>=2,<2.3"
$VENV/bin/python -c "import openwakeword, torch, torchaudio, speechbrain, audiomentations, torch_audiomentations, acoustics, pronouncing, datasets, piper_sample_generator, onnxruntime, numpy, scipy; from scipy.special import sph_harm; print('ok', torch.__version__, torchaudio.__version__, numpy.__version__, scipy.__version__, onnxruntime.__version__, openwakeword.__version__ if hasattr(openwakeword,'__version__') else '')"
$VENV/bin/python -c "
from openwakeword.data import generate_adversarial_texts
for ph in ['mohchee', 'moh chee', 'mochi']:
    t = generate_adversarial_texts(input_text=ph, N=20, include_partial_phrase=1.0, include_input_words=0.2)
    print(ph, len(t), t[:12])
"
uv pip freeze --python $VENV/bin/python > freeze.txt
nohup $VENV/bin/python get_rirs_fma.py rirs > logs/rirs.log 2>&1 &
nohup $VENV/bin/python get_rirs_fma.py fma > logs/fma.log 2>&1 &
cat data/counts.json
echo SETUP5_DONE
