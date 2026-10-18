#!/usr/bin/env python3
"""Run several ext-v19 scripts one after another inside one bounded-runner slot.
Usage: batch.py "script.py arg ..." "script2.py ..."   (each quoted string is one command, split on spaces)
"""
import subprocess
import sys
import time

rc = 0
for cmd in sys.argv[1:]:
    t = time.time()
    print(f'=== {cmd}', flush=True)
    r = subprocess.run([sys.executable] + cmd.split(), check=False)
    print(f'=== {cmd} -> exit {r.returncode} in {time.time() - t:.1f}s', flush=True)
    rc = rc or r.returncode
sys.exit(rc)
