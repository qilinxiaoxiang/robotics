"""One fixed reversible architecture probe; not an adopted mount or print revision."""
from pathlib import Path
import json,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;W=D.parents[1];O=W/'roof-wiring-stage/motor-wires/obstacles'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def solid(m):
 assert m.is_volume
 s=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError;return s
lo=np.array([-40.,-13.,-45.]);hi=np.array([-10.,13.,-37.]);m=trimesh.creation.box(hi-lo,transform=trimesh.transformations.translation_matrix((lo+hi)/2));a=solid(m);rows=[]
for p in sorted(O.glob('*.json')):
 ob=json.loads(p.read_text());assert sha(ob['file'])==ob['sha256'];b=np.array(ob['expectedFinalBoundsMm']);separation=np.maximum(np.maximum(b[0]-hi,lo-b[1]),0);gap=float(np.linalg.norm(separation));r={'key':ob['key'],'sourceSha256':ob['sha256'],'boundsMm':b.tolist(),'aabbDistanceLowerBoundMm':gap}
 if ob['key']=='regulator':r['status']='REPLACED_OLD_DFR_POSE'
 elif gap>0:r['status']='BOUNDS_SEPARATE'
 else:
  mm=trimesh.load_mesh(ob['file']);mm.apply_translation(ob.get('importTranslationMm',[0,0,0]));s=solid(mm);cut=a^s;assert cut.status()==mf.Error.NoError;r.update(status='INTERSECTION'if cut.volume()>1e-7 else'EXACT_CLEAR',intersectionMm3=cut.volume(),intersectionBoundsMm=list(cut.bounding_box())if cut.volume()>1e-7 else None,minGapClippedAt5Mm=a.min_gap(s,5))
 rows.append(r)
file=D/'dfr-below-openrb-envelope-world.stl';m.export(file)
out={'scope':'ONE fixed neutral architecture envelope only. Full present source inventory including original supports/hips/legs. Does not validate moving joints, installed retention, solder leads or source distribution. Old DFR pose replaced only; old insert/support remain tested.','candidate':{'boundsMm':[lo.tolist(),hi.tolist()],'boardPlane':'XY','receivingDimensionsMm':[30,26,8],'file':str(file),'sha256':sha(file),'lowerExtensionRelativeToOldCavityBottomMm':10,'nominalZGapToProposedOpenRBMm':2.11},'sourceHashes':{str(Path(__file__)):sha(__file__)},'expectedKeys':[r['key']for r in rows],'complete':len(rows)==len(list(O.glob('*.json'))),'checks':rows,'passedNeutralEnvelope':all(r['status']!='INTERSECTION'for r in rows),'adopted':False};f=D/'dfr-below-openrb-check.json';f.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'report':str(f),'sha256':sha(f),'passed':out['passedNeutralEnvelope'],'exact':[r for r in rows if r['status']in['INTERSECTION','EXACT_CLEAR']],'nearestBounds':sorted([r for r in rows if r['status']=='BOUNDS_SEPARATE'],key=lambda r:r['aabbDistanceLowerBoundMm'])[:6]},indent=2))
