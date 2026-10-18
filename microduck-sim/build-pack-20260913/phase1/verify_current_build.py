"""Compatibility entry for the context-linked current build."""
from pathlib import Path
import subprocess, sys
args=sys.argv[1:]
if 'bringup' in args:
    print('Legacy bringup scope now routes to the integrated design check; this does not prove physical operation.')
    args=[('design' if a=='bringup' else a) for a in args]
if '--scope' not in args: args=['--scope','project']+args
raise SystemExit(subprocess.call([sys.executable,str(Path(__file__).resolve().parent.parent/'redesign-20260913/verify_current_build.py'),*args]))
