"""Round 2: after `kaggle_flight.py fetch <kernel run>`, turn every saved student checkpoint of a distillation run into
a runtime models folder for ts2_pick.py and ts_accept.sh (walk61.onnx + stand61.onnx, the same stateful file, plus the
.pt for adapt_eval).

  python3 train/ts2_stage_student.py <kernel run> <run> <tag>    e.g.  ts2-mamba ts2-mamba-b s2b  ->  ckpt/s2b_<iter>/

Prints the folder names, oldest first.
"""
import shutil
import sys
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
kernel, run, tag = sys.argv[1:4]
src = TRAIN / "kaggle/out" / kernel / "runs" / run
its = sorted(int(p.stem.split("_")[1]) for p in src.glob("model_[0-9]*.onnx"))
names = []
for it in its:
    if it == 0:
        continue
    d = TRAIN / "ckpt" / f"{tag}_{it}"
    d.mkdir(parents=True, exist_ok=True)
    for name in ("walk61.onnx", "stand61.onnx"):
        shutil.copyfile(src / f"model_{it}.onnx", d / name)
    pt = src / f"model_{it}.pt"
    if pt.exists():
        shutil.copyfile(pt, d / pt.name)
    names.append(d.name)
print(" ".join(names))
