"""Intentional separate bearing carrier with positive L register, no discarded bearing body."""
import json
from pathlib import Path
import short_path_worker as c
c.guard()
import numpy as np,trimesh,manifold3d as mf
import flat_yaw_geometry as g
D=Path(__file__).resolve().parent;H=D.parent.parent;O=D/'flat-ribbon-sweep';sp=O/'head_bottom.npz';rp=O/'head_bottom.json';meta=json.loads(rp.read_text());assert c.sha(sp)==meta['stateSha256'];z=np.load(sp);s=mf.Manifold(mf.Mesh64(z['vertices'],z['faces']));parts=sorted(s.decompose(),key=lambda x:x.volume(),reverse=True);main,carrier=parts[:2];jp=O/'jaw_support-flat-channel-world.stl';jaw=g.conv(trimesh.load(jp,force='mesh'))
# Two perpendicular positive locating faces outside native jaw-support foot.
key=mf.Manifold.cube([2,2,1.7]).translate([45.2,4,110.5])+mf.Manifold.cube([3,4,11.8]).translate([45.2,3,99]);pocket=mf.Manifold.cube([2.4,2.4,.91]).translate([45,3.8,111.49]);original_jaw=jaw;jaw=jaw-pocket
old=carrier;carrier=carrier+key;assert carrier.status()==mf.Error.NoError
main_before=main
for delta in [[.001,0,0],[-.001,0,0],[0,.001,0],[0,-.001,0],[0,0,.001],[0,0,-.001]]:main=main-jaw.translate(delta)
contact_release=main_before.volume()-main.volume()
report={'integrationReady':False,'parts':{},'numericalInterfaceClearance':{'maxLocalOffsetMm':.001,'removedVolumeMm3':contact_release,'description':'Remove only intersection with jaw-support translated +/-0.001mm along axes, resolving final source numerical contact; no outer bbox cuts.'},'key':{'nominalRegisterEngagementMm':.6854,'minimumNominalPocketRoofMm':.8146,'keyCrossSectionMm':[2,2],'keyToCarrierUnionVolumeMm3':(old^key).volume(),'keyToJawMm3':(jaw^key).volume(),'description':'Square key positive faces bound rotation/translation about mount02; original screw retains Z and bearing half-seat remains intact.'},'scraps':[]}
report['key'].update(design='2x2 square key into underside pocket; .2mm each-side clearance; original02 thread and bearing seat preserved',keyBounds=list(key.bounding_box()),pocketBounds=list(pocket.bounding_box()),jawRemovedMm3=(original_jaw^pocket).volume())
for name,b in [('head_bottom',main),('head_roll_bearing_carrier',carrier),('jaw_support',jaw)]:
 b=b.as_original().simplify(.001);assert len(b.decompose())==1,(name,[x.volume() for x in b.decompose()])
 m=b.to_mesh64();tm=trimesh.Trimesh(m.vert_properties[:,:3],m.tri_verts,process=False);assert tm.is_watertight and tm.is_volume
 # Release an isolated sub-0.1mm numerical seam from channel Boolean at a measured location.
 if name=='head_bottom':
  seam=mf.Manifold.cube([.06,.06,.2]).translate([51.0516,-26.23283,109.50]);before=b;b=b-seam;report['numericalSeamRelease']={'bounds':list(seam.bounding_box()),'removedVolumeMm3':(before^seam).volume(),'reason':'STL readback had coincident vertical micro-edges at this channel seam; explicit local relief, no hole fill or mesh tolerance waiver.'};m=b.to_mesh64();tm=trimesh.Trimesh(m.vert_properties[:,:3],m.tri_verts,process=False);assert tm.is_watertight and tm.is_volume
 tm.vertices=np.round(tm.vertices,5);tm.merge_vertices(digits_vertex=5);tm.update_faces(tm.nondegenerate_faces(height=1e-10));tm.update_faces(tm.unique_faces());tm.remove_unreferenced_vertices();assert tm.is_volume and tm.is_watertight
 p=O/(name+'-split-channel-world.stl');p.write_text(trimesh.exchange.stl.export_stl_ascii(tm));rd=trimesh.load(p,force='mesh');assert rd.is_volume and rd.is_watertight and len(rd.split())==1
 report['parts'][name]={'worldMesh':str(p),'sha256':c.sha(p),'volumeMm3':rd.volume,'bounds':rd.bounds.tolist(),'singleConnectedClosedBody':True,'exportGridMm':.00001,'maxVertexGridDisplacementMm':.000008661}
keypath=O/'carrier-key-world.stl';km=key.to_mesh64();keypath.write_text(trimesh.exchange.stl.export_stl_ascii(trimesh.Trimesh(km.vert_properties[:,:3],km.tri_verts,process=False)))
report['key']['worldMesh']=str(keypath);report['key']['sha256']=c.sha(keypath)
data=H.parent/'leg-guide-20261006/full-build-data.json';guide=json.loads(data.read_text());original_head_path=H/'camera-ribbon-repair/positive-x225/head_bottom_x225_receiver-world.stl';original_head=g.conv(trimesh.load(original_head_path,force='mesh'));screws=[x for x in guide['screws'] if x.get('groupId')=='motor_support_frame'];report['mechanicalInterfaces']=[]
for sc in screws:
 x,y,zz=sc['world_center_mm'];zone=mf.Manifold.cylinder(8,2.6,2.6,64).translate([x,y,zz-6]);loss=(original_head^zone)-((main+carrier)^zone);report['mechanicalInterfaces'].append({'id':sc['id'],'jawLostThreadSupportMm3':((original_jaw^zone)-(jaw^zone)).volume(),'lostThreadSupportMm3':loss.volume(),'retainedBy':'head_roll_bearing_carrier' if sc['id'].endswith('02') else 'head_bottom'})
for frag in parts[2:]:
 row={'volumeMm3':frag.volume(),'bounds':list(frag.bounding_box()),'threadFeatureIntersectionsMm3':[],'bearingFeatureIntersectionsMm3':[]}
 for sc in screws:
  x,y,zz=sc['world_center_mm'];zone=mf.Manifold.cylinder(8,2.6,2.6,64).translate([x,y,zz-6]);row['threadFeatureIntersectionsMm3'].append((frag^zone).volume())
 for k in ['head_roll_ring_a','head_roll_ring_b']:
  p=next(p for p in guide['parts'] if p['key']==k);lo,hi=np.array(p['bounds']);lo-=2;hi+=2;row['bearingFeatureIntersectionsMm3'].append((frag^mf.Manifold.cube((hi-lo).tolist()).translate(lo.tolist())).volume())
 report['scraps'].append(row)
report['wireKeyChecks']=[]
for pose in meta['expectedUniqueHeadRelativePoses']:
 hits=[]
 for w in g.specs_for_pose(pose):
  vol=(key^g.tube(w['points'],w['receivingODMm']/2+.02)).volume()
  if vol>1e-8:hits.append({'wire':w['key'],'overlapMm3':vol})
 report['wireKeyChecks'].append({'pose':pose,'failures':hits})
report['sourceHashes']={str(p):c.sha(p) for p in [Path(__file__),sp,rp,jp,data,original_head_path,D/'flat_yaw_geometry.py']};c.save(O/'split-carrier-candidate.json',report);print(json.dumps({k:v for k,v in report.items() if k not in ['wireKeyChecks','sourceHashes','scraps']}));print('wire failures',sum(bool(x['failures']) for x in report['wireKeyChecks']))
