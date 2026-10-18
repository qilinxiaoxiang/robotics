from pathlib import Path
import os,json,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
D=Path(__file__).resolve().parent;H=D.parent;p=D/'check_saved_pose.py';n={'__file__':str(p)};exec(p.read_text().split('resume=')[0],n);np=n['np'];mf=n['mf'];tm=n['trimesh'];read=n['read'];read(Path(__file__))
evidencefile=H/'cabling-release-20261008/neck-repair/zero-w-mount-clearance-evidence.json';e=json.loads(read(evidencefile));assert e['proposedComponentBoxVoidRadiusMm']==2.2 and min(r['conservativeDrawingOnlyRadiusMm'] for r in e['rows'])>3.17
for name,want in e['sourceHashes'].items():
 proof=evidencefile.parent/name;assert hashlib.sha256(read(proof)).hexdigest()==want
src=D/'zero_w_components-lowered-pose-world.stl';read(src);m=tm.load(src,force='mesh');assert m.is_watertight;old=mf.Manifold(mf.Mesh64(np.array(m.vertices,np.float64),np.array(m.faces,np.uint64)));assert old.status()==mf.Error.NoError
T=np.array(json.loads(read(D/'lowered-pose-pair-checks.json'))['worldTransform']);d=T[:3,0];u=np.cross(d,[0,0,1]);u/=np.linalg.norm(u);v=np.cross(d,u);holes=json.loads(read(D/'head-source-cache/head-screws.json'));new=old;cuts=[]
for row in holes:
 a=(T@np.r_[row['world_center_mm'],1])[:3];c=mf.Manifold.cylinder(10.1,2.2,circular_segments=64).transform(np.column_stack([u,v,d,a-d*10]));new-=c;cuts.append(c)
q=new.to_mesh64();m=tm.Trimesh(q.vert_properties[:,:3],q.tri_verts,process=True);assert m.is_watertight;out=D/'zero_w_components-mount-clearance-world.stl';m.export(out);read(out);back=tm.load(out,force='mesh');assert back.is_watertight;s=mf.Manifold(mf.Mesh64(np.array(back.vertices,np.float64),np.array(back.faces,np.uint64)));assert s.status()==mf.Error.NoError
r={'integrationReady':False,'scope':'Conservative component-envelope correction only; no material removed from real PCB, solder tails, connectors or other components.','primarySource':e['primarySourceUrl'],'voidRadiusMm':2.2,'drawingInferenceNotManufacturerKeepout':True,'minimumDrawingMarginBeyondVoidMm':min(r['remainingDrawingClearanceAfterRadius2_2Mm'] for r in e['rows']),'removedReceivingEnvelopeVolumeMm3':(old-new).volume(),'sourceVolumeMm3':old.volume(),'currentVolumeMm3':s.volume(),'watertight':bool(back.is_watertight),'allFourSourceMountIds':[r['id'] for r in holes],'sourceHashes':n['hashes']}
(D/'pi-component-mount-clearance-report.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='sourceHashes'},indent=2))
