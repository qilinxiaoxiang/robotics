#!/bin/zsh
# openWakeWord training setup on the Mac mini: clones, downloads, venv packages. Logs to ~/mochi-train/oww/setup1.log
set -x
cd /Users/shawnxiang/mochi-train/oww
mkdir -p dl models
# background downloads (sizes checked: 17.3 GB features, 185 MB validation, 204 MB piper model)
nohup curl -sL --retry 3 -o dl/validation_set_features.npy https://huggingface.co/datasets/davidscripka/openwakeword_features/resolve/main/validation_set_features.npy > dl/val.log 2>&1 &
nohup curl -sL --retry 3 -o dl/en_US-libritts_r-medium.pt https://github.com/rhasspy/piper-sample-generator/releases/download/v2.0.0/en_US-libritts_r-medium.pt > dl/piper.log 2>&1 &
nohup curl -sL --retry 3 -o dl/openwakeword_features_ACAV100M_2000_hrs_16bit.npy https://huggingface.co/datasets/davidscripka/openwakeword_features/resolve/main/openwakeword_features_ACAV100M_2000_hrs_16bit.npy > dl/acav.log 2>&1 &
[ -d openWakeWord ] || git clone --depth 1 https://github.com/dscripka/openWakeWord
[ -d piper-sample-generator ] || git clone --depth 1 https://github.com/rhasspy/piper-sample-generator
git -C openWakeWord rev-parse HEAD
git -C piper-sample-generator rev-parse HEAD
ls piper-sample-generator
cat piper-sample-generator/pyproject.toml 2>/dev/null | head -60
cat piper-sample-generator/requirements.txt 2>/dev/null
ls piper-sample-generator/piper_sample_generator 2>/dev/null
grep -n "^def generate_samples" -A 30 piper-sample-generator/generate_samples.py piper-sample-generator/piper_sample_generator/*.py 2>/dev/null | head -60
grep -n "import" piper-sample-generator/generate_samples.py piper-sample-generator/piper_sample_generator/__init__.py 2>/dev/null | head -40
grep -n "FEATURE_MODELS" -A 12 openWakeWord/openwakeword/__init__.py | head -30
cat openWakeWord/examples/custom_model.yml
