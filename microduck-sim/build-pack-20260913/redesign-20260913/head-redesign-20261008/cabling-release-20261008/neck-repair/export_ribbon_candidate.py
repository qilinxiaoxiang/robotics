"""Export sampled-domain channels and verify retained mechanical interfaces."""
import argparse,json
from pathlib import Path
import short_path_worker as c
c.guard()
import numpy as np,trimesh,manifold3d as mf
import flat_yaw_geometry as g
D=Path(__file__).resolve().parent;H=D.parent.parent;O=D/'flat-ribbon-sweep';a=argparse.ArgumentParser();a.add_argument('--part',required=True);o=a.parse_args();rp=O/f'{o.part}.json';sp=O/f'{o.part}.npz';r=json.loads(rp.read_text());assert r['coverageComplete'];assert all(c.sha(p)==h for p,h in r['sourceHashes'].items());assert c.sha(sp)==r['stateSha256'];z=np.load(sp);body=mf.Manifold(mf.Mesh64(z['vertices'],z['faces']));assert body.status()==mf.Error.NoError
man=H/'camera-ribbon-repair/positive-x225/candidate-manifest.json';guidepath=H.parent/'leg-guide-20261006/full-build-data.json';guide=json.loads(guidepath.read_text());gp=next(x for x in guide['parts'] if x['key']==o.part)
if o.part=='head_bottom':src=H/json.loads(man.read_text())['replacementMeshes'][o.part];orig=trimesh.load(src,force='mesh')
else:src=H.parents[2]/gp['sourceFile'];orig=trimesh.load(src,force='mesh');orig.apply_transform(gp['sourceTransformWorld'])
base=g.conv(orig);components=sorted(body.decompose(),key=lambda x:x.volume(),reverse=True);scraps=components[1:];
if o.part=='head_bottom':
 diagnosis=json.loads((O/'head-components.json').read_text());assert diagnosis['sourceHashes'][str(sp)]==c.sha(sp);assert sum(s.volume() for s in scraps)<48;assert all(all(x['materialMm3']<1e-8 for x in row['protectedThreadMaterial']) for row in diagnosis['rows'][1:])
else:assert sum(s.volume() for s in scraps)<.5,'Substantial disconnected material: redesign required'
body=components[0].as_original().simplify(.001);m=body.to_mesh64();mesh=trimesh.Trimesh(m.vert_properties[:,:3],m.tri_verts,process=False);assert mesh.is_watertight and mesh.is_volume
world=O/f'{o.part}-flat-channel-world.stl';world.write_text(trimesh.exchange.stl.export_stl_ascii(mesh));read=trimesh.load(world,force='mesh');assert read.is_watertight and read.is_volume and len(read.split())==1
final=g.conv(read);mechanical=[]
for screw in guide['screws']:
 if screw.get('groupId')!='motor_support_frame':continue
 x,y,z=screw['world_center_mm'];guard=mf.Manifold.cylinder(8,2.6,2.6,64).translate([x,y,z-6]);old=base^guard;new=final^guard;lost=old-new;assert lost.status()==mf.Error.NoError
 mechanical.append({'id':screw['id'],'pilotDiameterMm':2.2,'radialWallTargetMm':1.5,'protectedRadiusMm':2.6,'zRangeMm':[z-6,z+2],'originalMaterialMm3':old.volume(),'remainingMaterialMm3':new.volume(),'lostMm3':lost.volume()})
for k in ['head_roll_ring_a','head_roll_ring_b']:
 p=next(p for p in guide['parts'] if p['key']==k);lo,hi=np.array(p['bounds']);lo-=2;hi+=2;guard=mf.Manifold.cube((hi-lo).tolist()).translate(lo.tolist());old=base^guard;new=final^guard;lost=old-new;mechanical.append({'id':k,'boundsExtraMm':2,'lostMm3':lost.volume()})
printpath=None;inverse=np.linalg.inv(np.array(gp['sourceTransformWorld']));shift=np.eye(4)
out={'integrationReady':False,'sampledDomainChannelCreated':True,'part':o.part,'worldMesh':str(world),'printMesh':None,'worldToPrint':(shift@inverse).tolist(),'worldSha256':c.sha(world),'printSha256':None,'singleConnectedClosedBody':True,'expectedUniqueRelativePoses':79,'completedUniqueRelativePoses':len(r['completed']),'nativeClearSourcePoses':186,'nativeBlockedSourcePosesRetained':43,'mechanicalInterfaces':mechanical,'maximumRemovedInterfaceVolumeMm3':max(x['lostMm3'] for x in mechanical),'discardedDetachedScrapVolumesMm3':[s.volume() for s in scraps],'exportSimplificationSurfaceDeviationMm':.001,'earlierSimplificationDeviationBoundMm':r.get('accumulatedSurfaceDeviationUpperBoundMm',0),'remaining':'Sampled channel shape only. Need cable clearance readback, section/bridge review and attachment-guides/other-joint segments before whole harness release. No physical fatigue or full continuous joint-domain acceptance.','sourceHashes':{str(p):c.sha(p) for p in [Path(__file__),rp,sp,src,man,guidepath,D/'flat_ribbon_geometry.py']}};c.save(O/f'{o.part}-export.json',out);print(json.dumps(out))
