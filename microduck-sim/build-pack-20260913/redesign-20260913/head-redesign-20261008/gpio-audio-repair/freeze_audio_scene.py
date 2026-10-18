"""Stdlib scene extraction: never load all robot meshes in a CAD worker."""
import json
from pathlib import Path
import check_speaker_rewire as s
D=Path(__file__).resolve().parent;O=D/'speaker-rewire';cache=O/'source-cache';cache.mkdir(exist_ok=True)
idx=s.scene();originalOpenrb=idx['openrb']['path'];idx['openrb']={'key':'openrb','path':s.H/'usb-access/usb-repair/openrb-conservative-convex-obstacle.stl','conservativeEnclosureOf':str(originalOpenrb)};usb=json.loads((s.H/'usb-access/usb-repair/edge-aligned-exports/usb-receiving-geometry.json').read_text())
for case,parts in usb['cases'].items():
 for k,p in parts.items():idx['usb'+case+'_'+k]={'key':'usb'+case+'_'+k,'path':Path(p),'diagnosticVariant':case}
rows={};sources=[originalOpenrb,s.H/'usb-access/usb-repair/openrb-conservative-enclosure.json',Path(__file__),D/'check_speaker_rewire.py',s.b.core.SOURCE,s.b.core.CONFIG,s.A/'placement-overlay.json']
for k,row in idx.items():
 bb=s.b.rowbounds(row);r={k:v for k,v in row.items() if k!='data'};r['boundsMm']=bb
 if row.get('path'):r['path']=str(row['path']);sources.append(row['path'])
 else:
  f=cache/(k+'.json');f.write_text(json.dumps(row['data'],separators=(',',':')));r['dataFile']=str(f);sources.append(f)
 rows[k]=r
local=json.loads((s.b.C/'local-candidate-manifest.json').read_text());import hashlib
projection={k:local[k] for k in ['replacementMeshes','additionalParts','removedParts']}
plan={'rows':rows,'inputHashes':s.c.fingerprint(sources),'localGeometrySha256':hashlib.sha256(json.dumps(projection,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'manifestBytesSha256AtCapture':s.c.sha(s.b.C/'local-candidate-manifest.json'),'integrationReady':False};s.c.atomic_json(O/'scene-plan.json',plan)
print(json.dumps({'count':len(rows),'plan':'scene-plan.json'}))
