from pathlib import Path
import os,json
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;p=D/'repair_face_cap_clearance.py';n={'__file__':str(p)};exec(p.read_text().split('cap=load')[0],n);np=n['np'];mf=n['mf'];load=n['load'];read=n['read'];read(Path(__file__));face=load(D/'face-three-mount-cap-clearance-world.stl');base=load(D/'face-pi-camera-three-mount-world.stl');T=np.array(json.loads(read(D/'lowered-pose-pair-checks.json'))['worldTransform']);d=T[:3,0];rows=json.loads(read(D/'face-three-mount-report.json'))['fasteners'];a=np.array(rows[2]['headSeatMm'])+d*1.6;u=np.cross(d,[0,0,1]);u/=np.linalg.norm(u);vv=np.cross(d,u)
def cyl(z,l,r):return mf.Manifold.cylinder(l,r,circular_segments=48).transform(np.column_stack([u,vv,d,a+d*z]))
checks=[]
for z,l in [(0,4.4),(4.4,.3),(4.7,.3),(5,.5)]:
 core=cyl(z,l,2.25)-cyl(z-.01,l+.02,1.05);checks.append({'depthFromPrintedSeatMm':[z,z+l],'missingCurrentMm3':max(0,(core-face).volume()),'sourceDiscretizationMissingMm3':max(0,(core-base).volume())})
r={'checks':checks,'sourceHashes':n['n']['hashes']};(D/'pillar03-wall-profile.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(checks,indent=2))
