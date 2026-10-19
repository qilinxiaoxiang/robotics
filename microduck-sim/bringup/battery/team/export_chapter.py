"""Export chapter 11 (battery backpack) of the MicroDuck assembly guide as its own self-contained 3D page for teammates.
    python3 export_chapter.py      -> team/backpack-3d.html (published beside the teammate page)
Reads guide/data/guide-data.json (rebuild it with guide/content/build_guide_data.py and pass the print gate first) and
bundles it with guide/build_guide.py. Keeps only the backpack chapter, its steps, the parts those steps draw and their
screws; no cables (chapter 11 highlights none)."""
import json, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
GUIDE = HERE.parents[2] / 'guide'
CH = 'backpack'
d = json.loads((GUIDE / 'data/guide-data.json').read_text())
steps = [s for s in d['steps'] if s['chapter'] == CH]
ids = {s['id'] for s in steps}
keys = set()
for s in steps:
    for f in ('show', 'add', 'context'):
        keys |= set(s.get(f) or [])
    keys |= set((s.get('approach') or {}).keys()) | set((s.get('flex') or {}).get('parts') or [])
pk = {p['key'] for p in d['parts']}
unknown = keys - pk
assert not unknown, f'step references that are not part keys: {sorted(unknown)[:10]}'
out = dict(d)
out['title'] = 'MicroDuck battery backpack: 3D build steps'
out['subtitle'] = 'Chapter 11 of the MicroDuck assembly guide: snap in the switch, clip in the DFR1202, swap the desk box for the backpack, battery in, cap on.'
out['chapters'] = [c for c in d['chapters'] if c['id'] == CH]
out['steps'] = steps
out['parts'] = [p for p in d['parts'] if p['key'] in keys]
out['cables'] = []
out['screws'] = [s for s in d['screws'] if s.get('step') in ids]
out['alternates'] = [dict(a, parts=[k for k in a['parts'] if k in keys]) for a in d.get('alternates', [])]
tmp = HERE / 'backpack-chapter-data.json'
tmp.write_text(json.dumps(out))
dst = HERE / 'backpack-3d.html'
r = subprocess.run([sys.executable, str(GUIDE / 'build_guide.py'), '--data', str(tmp), '--out', str(dst)], capture_output=True, text=True)
print(r.stdout[-1200:], r.stderr[-1500:])
tmp.unlink()
sys.exit(r.returncode)
