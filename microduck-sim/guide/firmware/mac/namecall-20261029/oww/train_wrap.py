"""Run openwakeword/train.py --train_model on macOS: its training DataLoader uses num_workers = cpu count with
lambda label transforms, which macOS' spawn start method cannot pickle (PicklingError, 2026-10-30). The batch
generator only reads mmaped arrays, so the loader runs in-process here (num_workers=0); nothing else changes.

  ~/.venvs/oww/bin/python train_wrap.py --training_config mochi.yml --train_model
"""
import os
import runpy
import sys

import torch
import torch.utils.data as tud

_DataLoader = tud.DataLoader


class DataLoader(_DataLoader):
    def __init__(self, *a, **k):
        k["num_workers"] = 0
        k.pop("prefetch_factor", None)
        k.pop("persistent_workers", None)
        super().__init__(*a, **k)


tud.DataLoader = DataLoader
torch.utils.data.DataLoader = DataLoader
TRAIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "openWakeWord", "openwakeword", "train.py")
sys.argv = [TRAIN] + sys.argv[1:]
runpy.run_path(TRAIN, run_name="__main__")
