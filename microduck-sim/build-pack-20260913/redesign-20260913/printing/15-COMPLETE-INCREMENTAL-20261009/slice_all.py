"""Serialize native slicing under the measured process-tree resource guard."""
import json, subprocess, sys
from pathlib import Path
D=Path(__file__).resolve().parent
guard=D.parent.parent/'head-redesign-20261008/run_bounded_cad.py'
pipeline=D.parent/'13-RELEASE-PIPELINE-20261009/release_pipeline.py'
prep=D/'run/preparation.json'
for row in json.loads(prep.read_text())['rows']:
    c,m=row['color'],row['machine']
    print(f'Starting {c} {m}',flush=True)
    subprocess.run([sys.executable,str(guard),'--max-mib','1536','--seconds','90',
                    '--wait-lock-seconds','30','--report',str(D/'run'/f'{c}-{m}-resource.json'),
                    '--','/tmp/microduck-cad-venv/bin/python',str(pipeline),'slice',str(prep),c,m],check=True)
    print(f'Finished {c} {m}',flush=True)
