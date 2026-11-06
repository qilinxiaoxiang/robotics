#!/usr/bin/env python3
"""MicroDuck entry point for the shared guide bundler in ~/code/robotics/guide-kit/build_guide.py.

    python3 guide/build_guide.py --data <guide-data.json> --out <file.html>

The bundler, viewer and three.js copy live in guide-kit (one editable source); this file only loads that module
and re-exports its names, so `from build_guide import load_three, ...` keeps working for MicroDuck scripts.
"""
import importlib.util
import sys
from pathlib import Path

_KIT = Path(__file__).resolve().parents[2] / 'guide-kit' / 'build_guide.py'
_spec = importlib.util.spec_from_file_location('guide_kit_build_guide', _KIT)
_mod = importlib.util.module_from_spec(_spec)
sys.modules['guide_kit_build_guide'] = _mod
_spec.loader.exec_module(_mod)
globals().update({k: v for k, v in vars(_mod).items() if not k.startswith('__')})

if __name__ == '__main__':
    sys.exit(_mod.main())
