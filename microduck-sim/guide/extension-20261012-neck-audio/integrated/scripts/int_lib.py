"""Shared paths and helpers for the integrated neck-route + audio + Pi-mount study (study only; read-only on V1.8).

Reuses the sibling studies' libraries by path: ../../audio/scripts (scene.py, check_lib.py, wires.py),
../../pi-mount/scripts (pm_lib.py, check_options.py) and ../../neck-route (nr_lib.py and its checks).
Frame: robot frame at q = 0, mm, x forward, y left, z up (same as guide/print/world and the audit solid cache).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parent                                  # .../extension-20261012-neck-audio/integrated
EXT = STUDY.parent
AUDIO = EXT / 'audio'
PIM = EXT / 'pi-mount'
NR = EXT / 'neck-route'
SOL = STUDY / 'study-solids'
SOL.mkdir(exist_ok=True)
SCRATCH = Path(os.environ.get('INT_SCRATCH', '/private/tmp/claude-501/-Users-xiangzheng-code-robotics/'
                                             'feb8343a-52e2-499e-88f6-f1b3a6b98491/scratchpad/integrated'))
SCRATCH.mkdir(parents=True, exist_ok=True)
for p in (PIM / 'scripts', AUDIO / 'scripts', NR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

INTEGRATED_CAP = SOL / 'head_cap-integrated-world.stl'


def jdump(obj, path):
    def conv(o):
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.bool_):
            return bool(o)
        if isinstance(o, Path):
            return str(o)
        raise TypeError(type(o))
    Path(path).write_text(json.dumps(obj, indent=1, default=conv))


def rnd(x, n=3):
    if isinstance(x, dict):
        return {k: rnd(v, n) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [rnd(v, n) for v in x]
    if isinstance(x, np.ndarray):
        return np.round(x, n).tolist()
    if isinstance(x, (float, np.floating)):
        return round(float(x), n)
    return x


def sha(p):
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
