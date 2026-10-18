"""Reject the original unsplit jaw along the candidate's entry path."""
from pathlib import Path
import json,hashlib,numpy as np,trimesh
OUT=Path(__file__).resolve().parent;p=OUT.parent/'head-fit-investigation.py';n={'__file__':str(p)};exec(p.read_text().split("report={'problemIds'")[0],n)
pivot=np.array([26.1,0,118.6146]);jaw=n['solid']('jaw_frame').translate(-pivot).rotate([0,30,0]).translate(pivot)
fixed={k:n['solid'](k) for k in ['jaw_support','head_bottom','motor15','motor14','head_yaw_link','head_roll_ring_a','head_roll_ring_b']}
cases=[]
for label in ['original-shell','candidate-shell']:
 if label=='candidate-shell':fixed['head_bottom']=n['man'](trimesh.load(OUT/'head_bottom_clearance-world.stl',force='mesh'))
 result=n['samples']({'original_jaw':jaw},fixed,[0,32,0],step=.25)
 cases.append({'case':label,'path':result,'rejected':max(result['peakContactsMm3'].values())>100})
report={'case':'Unsplit original jaw, same 30-degree output-side insertion, installed neck/shell/support obstacles','sourceDataSha256':hashlib.sha256((n['G']/'full-build-data.json').read_bytes()).hexdigest(),'cases':cases,'rejected':all(c['rejected'] for c in cases)}
(OUT/'negative-control.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({c['case']:c['path']['peakContactsMm3'] for c in cases},indent=2))
assert report['rejected']
