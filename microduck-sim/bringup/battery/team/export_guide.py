"""Export the whole MicroDuck assembly guide (all chapters) for the teammate page.
    python3 export_guide.py   -> team/microduck-build.html + team/microduck-build-geometry-N.js (published beside the teammate page)
The bundle is 18 MB, above the 16 MB per-file limit of the page host, so the geometry block goes into scripts of at most 4 MB each.
Reads guide/data/guide-data.json; rebuild it with guide/content/build_guide_data.py and pass the print gate first."""
import subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
GUIDE = HERE.parents[2] / 'guide'
r = subprocess.run([sys.executable, str(GUIDE / 'build_guide.py'), '--data', str(GUIDE / 'data/guide-data.json'),
                    '--out', str(HERE / 'microduck-build.html'), '--geometry-script', 'microduck-build-geometry.js'],
                   capture_output=True, text=True)
print(r.stdout[-1200:], r.stderr[-600:] if r.returncode else '')
sys.exit(r.returncode)
