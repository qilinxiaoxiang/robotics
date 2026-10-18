"""Independent cumulative-state motion audit for the remaining main-guide sections."""
from pathlib import Path
import json,numpy as np,hashlib
D=Path(__file__).resolve().parent;G=D.parent;p=G.parent/'head-redesign-20261008/head-fit-investigation.py';ns={'__file__':str(p)};exec(p.read_text().split("report={'problemIds'")[0],ns)
data=ns['data'];parts={p['key']:p for p in data['parts']};solid=ns['solid'];samples=ns['samples'];screws={s['id']:s for s in data['screws']};wanted={'torso','power','imu','neck'};prior=set();rows=[]
def vector(op,k):
 if k in op.get('partApproachVectors',{}):return op['partApproachVectors'][k]
 if k in op.get('moveKeys',[]) and 'approachVector' in op:return op['approachVector']
 if k.startswith(('washer','nut_')):
  s=screws[parts[k]['fastenerId']];return (np.array(s['world_axis'])*(-12 if k.startswith('nut_') or 'nut side' in parts[k]['name'] else 12)).tolist()
 return op.get('approachVector',parts[k].get('approachVector',[0,35,20]))
for mod in data['modules']:
 for op in mod['operations']:
  prior.update(op['add'])
  if mod['id'] not in wanted:continue
  visible=prior&set(op.get('isolatedPartKeys',prior));moving=list(dict.fromkeys(op['add']+op.get('moveKeys',[])));fixed=visible-set(moving);grouped=bool(op.get('moveKeys'))
  groups=[moving] if grouped else [[k] for k in moving]
  for group in groups:
   group=[k for k in group if k in visible]
   if not group:continue
   v=vector(op,group[0]);stationary={k:solid(k) for k in fixed};m={k:solid(k) for k in group}
   if not np.linalg.norm(v):fixed.update(group);continue
   result=samples(m,stationary,v,step=.25)
   rows.append({'module':mod['id'],'operation':op['id'],'moving':group,'fixed':sorted(fixed),'explicitBench':bool(op.get('isolatedPartKeys')),'path':result})
   print(op['id'],group,result['peakContactsMm3'],flush=True)
   if not grouped:fixed.update(group)
r={'problemIds':['P5','P6'],'sourceSha256':hashlib.sha256((G/'full-build-data.json').read_bytes()).hexdigest(),'scope':'All prior actual source parts, not module display context; explicit off-robot stations honored. Includes prior washers/nuts. Existing completed leg fixes and ankle/foot assembly not repeated.','spacingMm':.25,'rows':rows,'physicalFitVerified':False}
(D/'remaining-motion-review.json').write_text(json.dumps(r,indent=2)+'\n')
