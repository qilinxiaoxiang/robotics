#!/bin/zsh
set -x
VENV=/Users/shawnxiang/.venvs/oww
cd /Users/shawnxiang/mochi-train/oww
uv pip install --python $VENV/bin/python setuptools "datasets==3.6.0"
$VENV/bin/python openWakeWord/openwakeword/train.py --help 2>&1 | grep -v torchvision | head -3
$VENV/bin/python -c "import datasets, fsspec, pyarrow, numpy; print('datasets', datasets.__version__, fsspec.__version__, pyarrow.__version__, numpy.__version__)"
uv pip freeze --python $VENV/bin/python > freeze.txt
nohup $VENV/bin/python get_rirs_fma.py rirs > logs/rirs.log 2>&1 &
nohup $VENV/bin/python get_rirs_fma.py fma > logs/fma.log 2>&1 &
nohup ./run_train.sh gen > logs/gen.log 2>&1 &
sleep 90
grep -vE "^DEBUG|^INFO" logs/gen.log | tail -5 | cut -c1-300
grep -c "Batch" logs/gen.log
ls work/mochi/positive_train 2>/dev/null | wc -l
tail -2 logs/rirs.log logs/fma.log | cut -c1-200
ls data/mit_rirs | wc -l; ls data/fma 2>/dev/null | wc -l
echo SETUP6_DONE
