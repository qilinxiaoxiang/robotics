import json,base64,os
from pathlib import Path
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent.parent;cache=H/'usb-access/usb-repair/robot-source-cache';idx=json.loads((cache/'index.json').read_text());d=json.loads((cache/idx['parts']['motor11']).read_text());v=np.frombuffer(base64.b64decode(d['positionB64']),'<f4').reshape(-1,3);f=np.frombuffer(base64.b64decode(d['indexB64']),'<u4').reshape(-1,3)
raw=trimesh.Trimesh(v,f,process=False);m=trimesh.Trimesh(v,f,process=True);a=mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)));assert a.status()==mf.Error.NoError
mesh=a.to_mesh();normalized=trimesh.Trimesh(mesh.vert_properties[:,:3],mesh.tri_verts,process=False)
def triangle_digest(mm):
 t=np.ascontiguousarray(mm.vertices[mm.faces],dtype=np.float32);vertices=np.sort(t.view('V12').reshape(-1,3),axis=1);triangles=np.sort(vertices.view('V36').reshape(-1));import hashlib;return hashlib.sha256(triangles.tobytes()).hexdigest()
assert triangle_digest(m)==triangle_digest(normalized)
r={'triangleSurfaceMultisetIdentical':True,'rawWatertight':bool(raw.is_watertight),'rawVolume':bool(raw.is_volume),'rawVertices':len(raw.vertices),'mergedVertices':len(m.vertices),'normalizedWatertight':bool(normalized.is_watertight),'normalizedVolume':bool(normalized.is_volume),'normalizedVertices':len(normalized.vertices),'normalizedFaces':len(normalized.faces),'volumeDelta':float(normalized.volume-m.volume),'boundsUnchanged':bool(np.array_equal(normalized.bounds,m.bounds))}
normalized.export(D/'motor11-native-topology.ply');read=trimesh.load(D/'motor11-native-topology.ply',force='mesh',process=False);r['plyReadbackWatertight']=bool(read.is_watertight);r['plyReadbackVolume']=bool(read.is_volume);r['plyReadbackBoundsSame']=bool(np.array_equal(read.bounds,m.bounds));print(json.dumps(r));(D/'motor11-topology-diagnostic.json').write_text(json.dumps(r,indent=2)+'\n')
