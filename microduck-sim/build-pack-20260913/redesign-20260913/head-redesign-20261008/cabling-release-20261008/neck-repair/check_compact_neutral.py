"""Lightweight entrypoint for isolated compact-neutral stages.

No default CAD run and no all-scene import. Root explicitly dispatches each
worker through the single-job launcher; failed self-check blocks later stages.
"""
import runpy
from pathlib import Path
if __name__=='__main__':runpy.run_path(str(Path(__file__).with_name('compact_neutral_worker.py')),run_name='__main__')
