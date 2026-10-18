"""Trim only added internal pillar stock; preserve all source face material/exterior."""
from pathlib import Path
import os,json,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;H=D.parent;p=D/'check_saved_pose.py';n={'__file__':str(p)};exec(p.read_text().split('resume=')[0],n)
np=n['np'];mf=n['mf'];read=n['read'];mesh=n['mesh'];read(Path(__file__))
def load(p):
 read(p);m=n['trimesh'].load(p,force='mesh');assert m.is_watertight;s=mf.Manifold(mf.Mesh64(np.array(m.vertices,np.float64),np.array(m.faces,np.uint64)));assert s.status()==mf.Error.NoError;return s
v=lambda s:max(0,float(s.volume()))
cap=load(H/'gpio-audio-repair/cap-amp16z2/cap-current-audio-usb-world.stl');old=load(H/'face-eye-camera-clearance-world.stl');face=load(D/'face-pi-camera-mounts124-world.stl');cut=cap+cap.translate([0,.3,0]);new=face-(cut-old);removed=face-new
pose=json.loads(read(D/'lowered-pose-pair-checks.json'));T=np.array(pose['worldTransform']);normal=T[:3,0];r=json.loads(read(D/'face-mounts124-report.json'))
def cyl(a,d,l,rad):
 u=np.cross(d,[0,0,1]);u/=np.linalg.norm(u);vv=np.cross(d,u);return mf.Manifold.cylinder(l,rad,circular_segments=48).transform(np.column_stack([u,vv,d,a]))
cores=[]
for row in r['fasteners']:
 a=np.array(row['headSeatMm'])+normal*1.6
 core=cyl(a,normal,5.5,2.25)-cyl(a-normal*.01,normal,5.52,1.05)
 missing=v(core-new);cores.append({'id':row['id'],'pilotRadiusMm':1.05,'requiredRadialMaterialMm':1.2,'testedLengthMm':5.5,'missingCoreMaterialMm3':missing})
# Double precision ASCII STL preserves coplanar small source facets.
out=D/'face-mounts124-cap-clearance-world.stl';q=new.to_mesh64();m=n['trimesh'].Trimesh(q.vert_properties[:,:3],q.tri_verts,process=True);assert m.is_watertight
with out.open('w') as f:
 f.write('solid face\n')
 for tri in m.triangles:
  f.write('facet normal 0 0 0\nouter loop\n')
  for xyz in tri:f.write('vertex '+' '.join(format(float(z),'.17g') for z in xyz)+'\n')
  f.write('endloop\nendfacet\n')
 f.write('endsolid face\n')
loaded=load(out);contact=v(loaded^cap);loss=v(removed^old)
rep={'integrationReady':False,'scope':'Local face/cap repair only; assembly and full harness pending','sourceContactMm3':v(face^cap),'newContactMm3':contact,'actualRemovedVolumeMm3':v(removed),'sourceFaceMaterialRemovedMm3':loss,'candidateBodies':len(loaded.decompose()),'watertight':bool(n['trimesh'].load(out,force='mesh').is_watertight),'directionalReceivingClearanceMm':.3,'clearanceDirectionWorld':[0,1,0],'coreChecks':cores,'localGeometryPass':bool(contact<1e-5 and loss<1e-5 and len(loaded.decompose())==1 and all(x['missingCoreMaterialMm3']<.001 for x in cores)),'sourceHashes':n['hashes']}
(D/'face-mounts124-cap-clearance-report.json').write_text(json.dumps(rep,indent=2)+'\n');print(json.dumps({k:v for k,v in rep.items() if k!='sourceHashes'},indent=2))
