from pathlib import Path
import os,json,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent;O=D/'positive-x225';O.mkdir(exist_ok=True)
hashes={}
def read(p):
 b=p.read_bytes();hashes[str(p.resolve())]=hashlib.sha256(b).hexdigest();return b
m=json.loads(read(D/'local-candidate-manifest.json'));f=m['replacementMeshes']|{q['key']:q['mesh'] for q in m['additionalParts']};keys=['pi','zero_w_components','zero_w_gpio_solder_tails']+[q['key'] for q in json.loads(read(D/'gpio-individual-receiving-manifest.json'))['additionalParts']]
rows=[]
for k in keys:
 p=H/f[k];read(p);t=trimesh.load(p,force='mesh');assert t.is_watertight;s=mf.Manifold(mf.Mesh64(np.array(t.vertices,np.float64),np.array(t.faces,np.uint64))).translate([2.25,0,0]);assert s.status()==mf.Error.NoError and s.volume()>0;mesh=s.to_mesh64();v=np.array(mesh.vert_properties[:,:3]);faces=np.array(mesh.tri_verts);out=O/(k+'-world.stl')
 with out.open('w') as stream:
  stream.write('solid '+k+'\n')
  for row in faces:
   a,b,c=v[row];norm=np.cross(b-a,c-a);norm/=np.linalg.norm(norm);stream.write('facet normal '+' '.join(format(x,'.17g') for x in norm)+'\nouter loop\n')
   for pt in [a,b,c]:stream.write('vertex '+' '.join(format(x,'.17g') for x in pt)+'\n')
   stream.write('endloop\nendfacet\n')
  stream.write('endsolid '+k+'\n')
 q=trimesh.load(out,force='mesh');assert q.is_watertight;back=mf.Manifold(mf.Mesh64(np.array(q.vertices,np.float64),np.array(q.faces,np.uint64)));assert back.status()==mf.Error.NoError;assert abs(back.volume()-s.volume())<1e-7
 rows.append({'key':k,'mesh':str(out.relative_to(H)),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'boundsMm':q.bounds.tolist(),'watertight':True,'volumeMm3':back.volume()})
read(Path(__file__));r={'integrationReady':False,'scope':'Rigid receiving geometry only; no mounting, cable or closure acceptance','worldTransform':json.loads(read(D/'positive-x225-pose.json'))['worldTransform'],'parts':rows,'sourceHashes':hashes};(O/'pi-geometry-manifest.json').write_text(json.dumps(r,indent=2)+'\n');print('exported',len(rows),'closed components')
