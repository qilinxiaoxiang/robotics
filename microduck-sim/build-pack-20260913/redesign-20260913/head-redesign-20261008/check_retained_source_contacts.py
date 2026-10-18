from pathlib import Path
import json,base64,numpy as np,trimesh,manifold3d as mf
H=Path(__file__).resolve().parent;data=json.loads((H.parent/'leg-guide-20261006/full-build-data.json').read_text());c=json.loads((H/'viewer-candidate.json').read_text());parts={p['key']:p for p in data['parts']}
def raw(k):
 p=parts[k];return trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True)
def man(m):return mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)))
a=man(trimesh.load(H/c['replacementMeshes']['face_panel'],force='mesh'));old=man(raw('face_panel'));out=[]
for k in ['head_bottom','eye_trim','pi']:
 b=man(trimesh.load(H/c['replacementMeshes'][k],force='mesh')) if k in c['replacementMeshes'] else man(raw(k));q=a^b;baseline=old^man(raw(k));extra=q-baseline
 out.append({'pair':['face_panel',k],'sourceVolumeMm3':baseline.volume(),'currentVolumeMm3':q.volume(),'newContactOutsideSourceMm3':extra.volume(),'sourceBounds':baseline.bounding_box(),'currentBounds':q.bounding_box()})
(H/'retained-source-contact-analysis.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
