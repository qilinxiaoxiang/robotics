import json
from pathlib import Path
import short_path_worker as c
c.guard()
import numpy as np,manifold3d as mf
import flat_yaw_geometry as g
D=Path(__file__).resolve().parent;O=D/'flat-ribbon-sweep';rp=O/'head_bottom.json';r=json.loads(rp.read_text());p=O/'head_bottom.npz';assert c.sha(p)==r['stateSha256'];z=np.load(p);s=mf.Manifold(mf.Mesh64(z['vertices'],z['faces']));pieces=sorted(s.decompose(),key=lambda x:x.volume(),reverse=True)
bridge=mf.Manifold.cube([4.5,2.6,4]).translate([3,10.8,110])+mf.Manifold.cube([3,2.6,24]).translate([3,10.8,110])+mf.Manifold.cube([8,2.4,2]).translate([48,11,109])+mf.Manifold.cube([3,2.4,25]).translate([53,11,109])+mf.Manifold.cube([53,3,3]).translate([3,12,131]);bonds=[(x^bridge).volume() for x in pieces[:2]];print(json.dumps({'bondsMm3':bonds}),flush=True);rows=[]
import trimesh
jp=O/'jaw_support-flat-channel-world.stl';jm=trimesh.load(jp,force='mesh');js=g.conv(jm);print(json.dumps({'jawSupportOverlapMm3':(bridge^js).volume()}),flush=True)
assert min(bonds)>0, 'Bridge must join both actual bodies before cable scan'
mesh=bridge.to_mesh64();tm=trimesh.Trimesh(mesh.vert_properties[:,:3],mesh.tri_verts,process=False);assert tm.is_watertight and tm.is_volume;tm.export(O/'arch-bridge-world.stl')
for i in r['expectedUniqueHeadRelativePoses']:
 hits=[]
 for wire in g.specs_for_pose(i):
  tube=g.tube(wire['points'],wire['receivingODMm']/2+.02);hit=bridge^tube;assert hit.status()==mf.Error.NoError
  if hit.volume()>1e-8:hits.append({'wire':wire['key'],'volumeMm3':hit.volume()})
 rows.append({'pose':i,'hits':hits})
 if hits:print(json.dumps(rows[-1]),flush=True)
out={'accepted':False,'bridgeBounds':[3,10.8,109,56,15,134],'bondVolumesMm3':bonds,'wirePoseCount':len(rows),'wireFailures':[x for x in rows if x['hits']],'sourceHashes':{str(p):c.sha(p),str(rp):c.sha(rp),str(Path(__file__)):c.sha(Path(__file__))}};c.save(O/'arch-bridge-probe.json',out);print(json.dumps(out))
