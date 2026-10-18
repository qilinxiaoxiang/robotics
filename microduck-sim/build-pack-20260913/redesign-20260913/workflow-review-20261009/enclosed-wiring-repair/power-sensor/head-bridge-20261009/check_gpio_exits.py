from pathlib import Path
import sys,json,hashlib,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;F=D.parent/'head-controller-study/final-integration-20261009';I=D.parent/'integrated-harness-20261009';sys.path.insert(0,str(I));from wire_geometry import tube
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
src=F/'smt-header-package.json';portsrc=src;r=json.loads(src.read_text());ports=r['gpioHeaderProposal']['piPorts'];obs=[]
def solid(m):
 return mf.Manifold(mf.Mesh64(np.array(m.vertices,dtype=np.float64),np.array(m.faces,dtype=np.uint64)))
for p in r['parts']:
 assert sha(p['file'])==p['sha256'];m=trimesh.load_mesh(p['file']);m.apply_transform(p['worldTransform']);
 if not m.is_volume:m=m.convex_hull
 obs.append((p['key'],m.bounds,solid(m)))
rows=[]
for p in ports:
 pin=p['physicalPin']
 if pin not in [1,2,3,4,5,6,9,14]:continue
 u=np.array(p['outwardAxis']);u/=np.linalg.norm(u);a=np.array([0.,0,1]);a-=u*np.dot(u,a);a/=np.linalg.norm(a);b=np.cross(u,a);base=np.array(p['wireExitWorldMm']);od=1.5 if pin in [2,4,6,14] else .8;R=2.5 if od>1 else 2.
 for degrees in range(0,360,45):
  v=np.cos(np.radians(degrees))*a+np.sin(np.radians(degrees))*b;t=np.linspace(0,np.pi/2,45);pts=base+R*(np.sin(t)[:,None]*u+(1-np.cos(t))[:,None]*v);tans=np.cos(t)[:,None]*u+np.sin(t)[:,None]*v
  m=tube(pts,tans,od/2);s=solid(m);assert s.status()==mf.Error.NoError;hits=[]
  for key,bounds,body in obs:
   if np.any(m.bounds[1]<bounds[0]) or np.any(bounds[1]<m.bounds[0]):continue
   c=s^body;volume=max(c.volume(),0)
   if volume>1e-6:hits.append({'key':key,'volumeMm3':volume,'bounds':list(c.bounding_box())})
  row={'pin':pin,'turnDegreesAboutOutward':degrees,'diameterMm':od,'radiusMm':R,'start':base.tolist(),'end':pts[-1].tolist(),'endTangent':v.tolist(),'hits':hits,'clear':not hits};rows.append(row)
  if not hits:
   f=D/f'pin{pin:02d}-exit-turn{degrees}.stl';m.export(f);row.update(file=str(f),sha256=sha(f))
 print(pin,[(x['turnDegreesAboutOutward'],x['clear'],[(h['key'],round(h['volumeMm3'],4))for h in x['hits']])for x in rows if x['pin']==pin],flush=True)
(D/'gpio-exit-smt-check.json').write_text(json.dumps({'sourceHashes':{str(src):sha(src),str(portsrc):sha(portsrc),str(Path(__file__)):sha(__file__)},'scope':'Finite first-turn clearance for the actual female header cable exits. Not complete routing or self/cross-wire acceptance.','rows':rows},indent=2))
