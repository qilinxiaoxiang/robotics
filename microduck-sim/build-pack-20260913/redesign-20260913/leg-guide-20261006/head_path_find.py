"""Independent candidate search; reports contacts, never final-overlap clearance waiver."""
from pathlib import Path
import json,base64,hashlib,itertools,argparse
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent
args=argparse.ArgumentParser();args.add_argument('--target',choices=['jaw','upper','lower','cap','combined'],required=True);args.add_argument('--samples',type=int,default=17);a=args.parse_args()
raw=(D/'full-build-data.json').read_bytes();data=json.loads(raw);by={p['key']:p for p in data['parts']};solids={};bounds={}
def solid(k):
 if k not in solids:
  p=by[k];m=trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True);solids[k]=mf.Manifold(mf.Mesh(np.asarray(m.vertices,dtype=np.float32),np.asarray(m.faces,dtype=np.uint32)));bounds[k]=m.bounds
 return solids[k]
def ov(k,q,v):
 s=solid(k);b=solid(q);bb=bounds[k]+v
 if np.any(bb[1]<bounds[q][0]) or np.any(bounds[q][1]<bb[0]):return 0.
 return max(0.,float((s.translate(v)^b).volume()))
mod=next(m for m in data['modules'] if m['id']=='head-close');seen=set()
for m in data['modules']:
 if m['id']=='head-close':break
 for op in m['operations']:seen.update(op['add'])
key={'jaw':'jaw_frame','upper':'upper_pad','lower':'lower_pad','cap':'head_cap','combined':'head_cap'}[a.target]
for op in mod['operations']:
 seen.update(op['add'])
 if key in op['add']+op.get('moveKeys',[]):break
moving=[key]
if a.target in ['cap','combined']:moving=op['moveKeys'][:]
if a.target=='combined':moving+=['face_panel','pi','eye_trim']
if a.target=='lower':seen.add('upper_pad')
fixed=seen-set(moving)
# The face and cap are complete prerequisite subassemblies; late jaw/pads are absent.
if a.target in ['cap','combined']:fixed-={'jaw_frame','upper_pad','lower_pad'}
base={(k,q):ov(k,q,np.zeros(3)) for k in moving for q in fixed}
axes=[(0,1,0),(0,-1,0),(0,0,-1),(0,0,1),(-1,0,0),(1,0,0)]
dirs=axes+[v for v in itertools.product([-1,0,1],repeat=3) if v!=(0,0,0) and v not in axes]
results=[]
for d in dirs:
 vector=np.array(d)*32.;peaks={};worst=0
 for t in np.linspace(1,0,a.samples):
  for k in moving:
   for q in fixed:
    v=ov(k,q,vector*t)
    if v>.000001:peaks[(k,q)]=max(peaks.get((k,q),0),v)
  worst=max([v-base[p] for p,v in peaks.items()] or [0])
  if worst>100:break
 row={'vector':vector.tolist(),'peakExcessOverFinalForTriageOnly':worst,'contacts':[{'moving':p[0],'fixed':p[1],'peakMm3':v,'finalMm3':base[p]} for p,v in peaks.items()]};results.append(row)
 print(a.target,vector.tolist(),round(worst,6),flush=True)
results.sort(key=lambda r:r['peakExcessOverFinalForTriageOnly'])
out={'sourceSha256':hashlib.sha256(raw).hexdigest(),'target':a.target,'moving':moving,'fixed':sorted(fixed),'samples':a.samples,'scope':'Candidate ranking only. Explicit final contacts retained; no subtraction-based clearance acceptance. Early rejection for grossly blocked candidates.','candidates':results}
(D/'audit-20261008'/f'head-path-{a.target}.json').write_text(json.dumps(out,indent=2)+'\n')
print('BEST',json.dumps(results[:2]),flush=True)
