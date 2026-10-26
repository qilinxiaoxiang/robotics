#!/bin/sh
# Download model weights (gitignored) and the public InsightFace sample image.
set -eu
cd "$(dirname "$0")"
mkdir -p models samples
if [ ! -f models/buffalo_sc/w600k_mbf.onnx ]; then
  curl -fL -o models/buffalo_sc.zip https://github.com/deepinsight/insightface/releases/download/v0.7/buffalo_sc.zip
  unzip -o -q models/buffalo_sc.zip -d models/buffalo_sc && rm models/buffalo_sc.zip
fi
[ -f models/campplus_zh_en_advanced.onnx ] || curl -fL -o models/campplus_zh_en_advanced.onnx \
  https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx
[ -f samples/t1.jpg ] || curl -fL -o samples/t1.jpg \
  https://raw.githubusercontent.com/deepinsight/insightface/master/python-package/insightface/data/images/t1.jpg
shasum -a 256 -c <<'SUMS'
5e4447f50245bbd7966bd6c0fa52938c61474a04ec7def48753668a9d8b4ea3a  models/buffalo_sc/det_500m.onnx
9cc6e4a75f0e2bf0b1aed94578f144d15175f357bdc05e815e5c4a02b319eb4f  models/buffalo_sc/w600k_mbf.onnx
aa3cfc16963a10586a9393f5035d6d6b57e98d358b347f80c2a30bf4f00ceba2  models/campplus_zh_en_advanced.onnx
SUMS
