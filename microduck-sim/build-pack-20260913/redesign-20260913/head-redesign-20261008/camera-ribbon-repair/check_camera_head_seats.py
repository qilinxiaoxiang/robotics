from pathlib import Path
import os,json
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;p=D/'check_saved_pose.py';n={'__file__':str(p)};exec(p.read_text().split('resume=')[0],n);np=n['np'];mf=n['mf'];tm=n['trimesh'];read=n['read'];read(Path(__file__))
def load(p):
 read(p);m=tm.load(p,force='mesh');assert m.is_watertight;s=mf.Manifold(mf.Mesh64(np.array(m.vertices,np.float64),np.array(m.faces,np.uint64)));assert s.status()==mf.Error.NoError;return s
face=load(D/'face-mounts124-cap-clearance-world.stl');eye=n['source']('eye_trim');r=json.loads(read(D/'local-camera-roll90-lowear4-pi-report.json'));checks=[]
for row in r['screws'][:4]:
 a=np.array(row['headSeatMm']);ys=np.arange(a[1]-2.2,a[1]+2.2,.25);zs=np.arange(a[2]-2.2,a[2]+2.2,.25)
 for key,solid in [('face',face),('eye',eye)]:
  q=solid.to_mesh64();mesh=tm.Trimesh(q.vert_properties[:,:3],q.tri_verts,process=True);samples=[]
  for y in ys:
   for z in zs:
    if (y-a[1])**2+(z-a[2])**2>2.3**2:continue
    hits,_,_=mesh.ray.intersects_location([[68,y,z]],[[1,0,0]],multiple_hits=True);xs=sorted(hits[:,0].tolist()) if len(hits) else []
    # Only points where source material occurs in the planned cut interval.
    if len(xs)<2 or xs[0]>=81.2:continue
    samples.append({'y':float(y),'z':float(z),'intersectionsX':xs,'forwardMaterialBoundMm':xs[-1]-81.2})
  checks.append({'screw':row['id'],'part':key,'samples':len(samples),'minimumForwardBoundMm':min([s['forwardMaterialBoundMm'] for s in samples],default=None),'under1p2Count':sum(s['forwardMaterialBoundMm']<1.2 for s in samples),'worst':min(samples,key=lambda s:s['forwardMaterialBoundMm']) if samples else None})
rep={'accepted':False,'cutEndX':81.2,'headRadiusReceivingMm':2.3,'sampleSpacingMm':.25,'checks':checks,'sourceHashes':n['hashes']};(D/'camera-head-seat-thickness.json').write_text(json.dumps(rep,indent=2)+'\n');print(json.dumps(checks,indent=2))
