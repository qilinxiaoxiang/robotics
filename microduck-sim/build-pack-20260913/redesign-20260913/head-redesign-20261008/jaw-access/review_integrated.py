"""Independent final-contact inspection; never changes root integration files."""
from pathlib import Path
import json,base64,numpy as np,trimesh,manifold3d as mf,hashlib
D=Path(__file__).resolve().parent.parent;G=D.parent/'leg-guide-20261006'
data=json.loads((G/'full-build-data.json').read_text());c=json.loads((D/'viewer-candidate.json').read_text());jaw=json.loads((D/'jaw-access/viewer-fragment.json').read_text());original={p['key']:p for p in data['parts']}
def man(m):
 m=m.copy();m.process();s=mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)));assert s.status()==mf.Error.NoError;return s
def source(k):
 p=original[k];return man(trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True))
c['replacementMeshes'].update(jaw['replacementMeshes']);additions={p['key']:p for p in c['additionalParts']};additions.update({p['key']:p for p in jaw['additionalParts']});solids={}
for k,p in original.items():
 if p.get('partKind')=='fastener' or k in c['removedParts']:continue
 if k in c['replacementMeshes']:solids[k]=man(trimesh.load(D/c['replacementMeshes'][k],force='mesh'))
 elif k in c.get('transforms',{}):
  pp=source(k);solids[k]=pp.transform(np.asarray(c['transforms'][k])[:3,:])
 else:solids[k]=source(k)
for k,p in additions.items():
 if 'screw' in k or p.get('geometryKind')=='fastener':continue
 solids[k]=man(trimesh.load(D/p['mesh'],force='mesh'))
rows=[];seen=set()
for k in list(jaw['replacementMeshes'])+['jaw_passive_cheek']:
 for q,f in solids.items():
  pair=tuple(sorted([k,q]))
  if k==q or pair in seen:continue
  seen.add(pair);it=solids[k]^f;v=float(it.volume())
  if v<1e-7:continue
  src=source(k)^source(q) if k in original and q in original else mf.Manifold()
  rows.append({'pair':pair,'currentMm3':v,'sourceMm3':float(src.volume()),'outsideSourceMm3':float((it-src).volume()),'boundsMm':list(it.bounding_box()),'components':[{'volumeMm3':float(s.volume()),'boundsMm':list(s.bounding_box())} for s in it.decompose()]})
retained=[]
for a,b in [('face_panel','head_bottom'),('face_panel','eye_trim'),('face_panel','pi'),('jaw_frame','motor15')]:
 it=source(a)^source(b);retained.append({'pair':[a,b],'sourceMm3':float(it.volume()),'boundsMm':list(it.bounding_box()),'components':[{'volumeMm3':float(x.volume()),'boundsMm':list(x.bounding_box())} for x in it.decompose()]})
r={'scope':'Independent hypothetical merge of current root candidate with ready jaw fragment. Read-only review of root files.','rootConfigSha256':hashlib.sha256((D/'viewer-candidate.json').read_bytes()).hexdigest(),'jawFragmentSha256':hashlib.sha256((D/'jaw-access/viewer-fragment.json').read_bytes()).hexdigest(),'contacts':rows,'sourceContactDetails':retained}
(D/'jaw-access/integrated-contact-review.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
