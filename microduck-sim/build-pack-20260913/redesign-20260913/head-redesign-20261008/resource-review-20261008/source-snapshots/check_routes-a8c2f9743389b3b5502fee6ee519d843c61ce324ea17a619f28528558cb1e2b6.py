"""Independent cable-receiving candidates. No canonical geometry changes."""
from pathlib import Path
import json,base64,hashlib,io,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent;G=H.parent/'leg-guide-20261006';hashes={}
def read(p):
 b=p.read_bytes();hashes[str(p.relative_to(H.parent))]=hashlib.sha256(b).hexdigest();return b
def man(m):return mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)))
def tri(s):
 q=s.to_mesh();return trimesh.Trimesh(q.vert_properties[:,:3],q.tri_verts,process=True)
def load(p):return trimesh.load(io.BytesIO(read(p)),file_type='stl',force='mesh')
def hits(a,b):
 x=np.array(a.bounding_box()).reshape(2,3);y=np.array(b.bounding_box()).reshape(2,3)
 if np.any(x[0]>=y[1]) or np.any(y[0]>=x[1]):return 0.
 return max(0,float((a^b).volume()))
data=json.loads(read(G/'full-build-data.json'));config=json.loads(read(H/'viewer-candidate.json'));obs={};meshes={}
for p in data['parts']:
 k=p['key']
 if k in config['removedParts']:continue
 if k in config['replacementMeshes']:m=load(H/config['replacementMeshes'][k])
 else:m=trimesh.Trimesh(np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(p['indexB64']),'<u4').reshape(-1,3),process=True)
 if k in config.get('transforms',{}):m.apply_transform(config['transforms'][k])
 meshes[k]=m;obs[k]=man(m)
for p in config['additionalParts']:
 meshes[p['key']]=load(H/p['mesh']);obs[p['key']]=man(meshes[p['key']])
def tube(points,r=.75):
 ss=[]
 for p in points:ss.append(mf.Manifold.sphere(r,16).translate(p))
 for a,b in zip(points,points[1:]):ss.append(mf.Manifold.batch_hull([mf.Manifold.sphere(r,16).translate(a),mf.Manifold.sphere(r,16).translate(b)]))
 return mf.Manifold.batch_boolean(ss,mf.OpType.Add)
def check(s,exclude=()):return {k:hits(s,o) for k,o in obs.items() if k not in exclude and hits(s,o)>1e-5}
if __name__=='__main__':
 report={'obstacleCount':len(obs),'audioBounds':{k:meshes[k].bounds.tolist() for k in ['speaker','speaker_cradle','speaker_keeper','amplifier','openrb','curved_cap_hardware']},'rows':[]}
 # Pad centers read approximately from manufacturer's un-dimensioned pad drawing.
 # Receiving squares +/-.5mm cover drawing read uncertainty. Cable OD1.5mm assumed.
 pads=[[-7.77,.94,132.35],[1.77,.94,132.35]]
 for i,p in enumerate(pads):
  for rise in [3,5,8]:
   points=[p,[p[0],p[1],p[2]+rise],[15,p[1],p[2]+rise],[25,-10,138.5],[31.15+i*3.5,-13.4,138.5]]
   s=tube(points);report['rows'].append({'id':f'speaker-{i}-rise{rise}','points':points,'hits':check(s,['speaker','amplifier'])})
 for k in ['zero_w_populated_receiving','pi','camera_board','camera_retainer']:
  report.setdefault('bounds',{})[k]=meshes[k].bounds.tolist()
 report['sourceHashes']=hashes;(D/'initial-audio-probe.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
