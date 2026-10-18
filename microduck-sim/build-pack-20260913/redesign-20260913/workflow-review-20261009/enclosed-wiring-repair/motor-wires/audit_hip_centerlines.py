from pathlib import Path
import json,hashlib,math
import numpy as np
from scipy.spatial import cKDTree
D=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def distance(a,b,c,d):
 u=b-a;v=d-c;w=a-c;A=u@u;B=u@v;C=v@v;E=v@w;F=u@w;det=A*C-B*B
 cand=[]
 for p,x,y in [(a,c,d),(b,c,d),(c,a,b),(d,a,b)]:
  vv=y-x;t=np.clip((p-x)@vv/(vv@vv),0,1);cand.append(np.linalg.norm(p-x-t*vv))
 if det>1e-16:
  s=(B*E-C*F)/det;t=(A*E-B*F)/det
  if 0<=s<=1 and 0<=t<=1:cand.append(np.linalg.norm(w+s*u-t*v))
 return float(min(cand))
rows=[]
for side in ['right','left']:
 p=D/f'hip-coiled-{side}.json';data=json.loads(p.read_text())
 for row in data['strands']:
  pts=np.array(row['centerlineMm']);ds=np.linalg.norm(np.diff(pts,axis=0),axis=1);s=np.r_[0,np.cumsum(ds)];mid=(pts[:-1]+pts[1:])/2;maxlen=float(ds.max())
  # Every segment pair with centerline distance <=2.0 must have midpoint distance <=2+maxlen.
  pairs=cKDTree(mid).query_pairs(2+maxlen);nonlocal_pairs=[(i,j)for i,j in pairs if s[j]-s[i+1]>3.]
  vals=[(distance(pts[i],pts[i+1],pts[j],pts[j+1]),i,j)for i,j in nonlocal_pairs];low=min(vals,default=(2.,None,None))
  # Corners already use exact R2. Sampled circumcircle check covers new helix and Bezier exit.
  u=np.diff(pts,axis=0);a=u[:-1];b=u[1:];cross=np.linalg.norm(np.cross(a,b),axis=1);rad=np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1)*np.linalg.norm(a+b,axis=1)/np.maximum(2*cross,1e-30)
  out={'side':side,'wire':row['id'],'sourceSha256':sha(p),'meshSha256':sha(Path(row['file'])),'segmentCount':len(ds),'maxChordMm':maxlen,'nonlocalCandidatePairs':len(nonlocal_pairs),'minimumNonlocalCenterlineDistanceMm':low[0],'closestSegments':low[1:],'surfaceSeparationLowerBoundMm':low[0]-1.5-.006,'curvatureSampleMinimumRadiusMm':float(rad.min()),'computedMaterialLengthMm':row['computedLengthMm'],'passed':low[0]>1.506 and rad.min()>1.5 and abs(row['computedLengthMm']-180)<1e-6};rows.append(out);print(out,flush=True)
(D/'hip-centerline-audit.json').write_text(json.dumps({'passed':all(r['passed']for r in rows),'method':'Exact finite straight-segment distance after complete midpoint broadphase. Neighbour segments with arc separation <=3mm omitted as same smooth local tube; all local sampled radii checked, analytic prefix R2. Curved chord allowance .003 mm each. Not strain-life validation.','rows':rows},indent=2))
