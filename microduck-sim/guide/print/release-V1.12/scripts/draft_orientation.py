"""Draft manifest and extra poses for the V1.12 orientation check (before rows.json fixes the poses).

    /tmp/microduck-cad-venv/bin/python scripts/draft_orientation.py   -> orientation-draft-manifest.json, orientation-extra-poses.json
"""
import hashlib, json
from pathlib import Path
HERE = Path(__file__).resolve().parent; REL = HERE.parent; PRINT = REL.parent; SIM = PRINT.parents[1]
P = json.loads((HERE / 'pose-sources.json').read_text())['poses']
SRC = {'shell_left_v20': PRINT / 'v20-source/shell_left_v20-world.stl', 'shell_right_v20': PRINT / 'v20-source/shell_right_v20-world.stl',
       'head_cap_v19_white': PRINT / 'ext-v19/head_cap_v19-world.stl',
       'thigh_left': SIM / 'build-pack-20260913/assembly/print-parts/community-74.stl', 'thigh_right': SIM / 'build-pack-20260913/assembly/print-parts/community-72.stl'}
FIRST = {'shell_left_v20': 'outer face down', 'shell_right_v20': 'outer face down', 'head_cap_v19_white': 'V1.9 pose', 'thigh_left': '10/1 pose', 'thigh_right': '10/1 pose'}
parts, extra = [], {}
for k, p in SRC.items():
    parts.append(dict(key=k, color='White', quantity=1, path=str(p), sha256=hashlib.sha256(p.read_bytes()).hexdigest(),
                      sourceToPrint=P[k][FIRST[k]]['sourceToPrint'], flatContact={'minimumAreaMm2': 0.01}))
    extra[k] = [dict(name=n, sourceToPrint=v['sourceToPrint']) for n, v in P[k].items() if n != FIRST[k]]
(REL / 'orientation-draft-manifest.json').write_text(json.dumps(dict(schemaVersion=1, releaseKind='incremental', version='V1.12-draft', parts=parts), indent=1))
(REL / 'orientation-extra-poses.json').write_text(json.dumps(extra, indent=1))
