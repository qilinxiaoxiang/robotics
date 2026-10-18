from pathlib import Path
import json,hashlib,os
assert os.environ.get('MICRODUCK_BOUNDED_CAD')
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;d=json.loads((D/'prototype-adoption.json').read_text());R=next(p for p in D.parents if p.name=='redesign-20260913')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(q):
 assert sha(q['file'])==q['sha256'];m=trimesh.load(q['file'],force='mesh');assert m.is_watertight and m.is_winding_consistent
 a=mf.Manifold(mf.Mesh64(np.array(m.vertices),np.array(m.faces,np.uint64)));assert a.status()==mf.Error.NoError;return m,a
row=d['printAssets'][0];mesh,base=load(row['baseShell']); shapes=[base]; bindings=[row['baseShell']]; additions=[]
for f in row['features']:
 m,a=load(f['worldMesh']);removed=0
 if f['key'].startswith('pi-roof-side-rail'):
  b=np.array(a.bounding_box()).reshape(2,3)
  points=m.vertices[m.vertices[:,2]>b[1,2]-.001]; xy=np.unique(points[:,:2],axis=0);ray=np.column_stack([xy,np.full(len(xy),200.)]);loc,ind,_=mesh.ray.intersects_location(ray,np.tile([0,0,-1],(len(ray),1)),multiple_hits=True);outer={}
  for q,i in zip(loc,ind):outer[int(i)]=max(outer.get(int(i),-1e10),q[2])
  assert len(outer)==len(ray);limit=min(outer.values())-.1
  below=mf.Manifold.cube([300,300,limit],False).translate([-150,-150,0]);clipped=a^below;removed=(a-clipped).volume();a=clipped

 shapes.append(a);bindings.append(f['worldMesh']);additions.append({'key':f['key'],'volumeMm3':a.volume(),'baseOverlapMm3':(a^base).volume(),'outsideRoofRemovedMm3':removed})
result=mf.Manifold.batch_boolean(shapes,mf.OpType.Add);assert result.status()==mf.Error.NoError
pieces=result.decompose();assert len(pieces)==1,('disconnected',len(pieces))
s=result.to_mesh64();out=trimesh.Trimesh(np.asarray(s.vert_properties)[:,:3],np.asarray(s.tri_verts),process=False)
world=D/'head-cap-prototype-world.stl';world.write_text(trimesh.exchange.stl.export_stl_ascii(out));back=trimesh.load(world,force='mesh');assert back.is_watertight and back.is_winding_consistent and len(back.split())==1
# Same V1.4 accepted broad side-plane print orientation; rigid translation settles the current part.
op=R/'head-redesign-20261008/gpio-audio-repair/orientation-readonly-review/flat-base-pose-candidates.json'; pose=next(x for x in json.loads(op.read_text())['parts']if x['key']=='head_cap');M=np.array(pose['worldToPrintTransform']);pm=back.copy();pm.apply_transform(M);dz=-pm.bounds[0,2];M[2,3]+=dz;pm.apply_translation([0,0,dz]);pr=D/'head-cap-prototype-print.stl';pr.write_text(trimesh.exchange.stl.export_stl_ascii(pm))
area=float(pm.area_faces[(pm.face_normals[:,2]<-.99)&(pm.triangles[:,:,2].max(axis=1)<.02)].sum())
# Original material is never subtracted. For added material outside original, inspect all vertices and edge midpoints against original roof.
added=result-base; am=added.to_mesh64();av=np.asarray(am.vert_properties)[:,:3];af=np.asarray(am.tri_verts);edges=np.unique(np.sort(np.concatenate([af[:,[0,1]],af[:,[1,2]],af[:,[2,0]]]),axis=1),axis=0); points=np.vstack([av,(av[edges[:,0]]+av[edges[:,1]])/2]); origins=points.copy();origins[:,2]=200
loc,ids,_=mesh.ray.intersects_location(origins,np.tile([0,0,-1],(len(points),1)),multiple_hits=True);roof={}
for q,i in zip(loc,ids):roof[int(i)]=max(roof.get(int(i),-1e10),q[2])
viol=[{'point':points[i].tolist(),'roof':roof.get(i)}for i in range(len(points))if i not in roof or points[i,2]>roof[i]+.005]
report={'status':'PASS_STANDARD_UNION'if not viol else'FAIL_OUTER_ROOF_VERTEX_CHECK','wholeHeadClosedAccepted':False,'physicalFitVerified':False,'sourceBindings':bindings,'scriptSha256':sha(__file__),'nativeBaseSource':str(R/'workflow-review-20261009/enclosed-wiring-repair/head-layout/sources/top-head-native.step'),'sourceNativeToWorld':[[0,-1,0,26.1],[1,0,0,0],[0,0,1,111.1146],[0,0,0,1]],'inputFeatures':additions,'worldMesh':{'file':str(world),'sha256':sha(world)},'printMesh':{'file':str(pr),'sha256':sha(pr)},'watertightReadback':bool(back.is_watertight),'connectedComponents':len(pieces),'volumeMm3':float(back.volume),'worldBoundsMm':back.bounds.tolist(),'sourceBoundsMm':mesh.bounds.tolist(),'boundsMaxDifferenceMm':float(np.max(np.abs(back.bounds-mesh.bounds))),'removedSourceVolumeMm3':(base-result).volume(),'addedVolumeMm3':added.volume(),'exteriorCheck':{'method':'All added mesh vertices and edge midpoints checked against highest original roof ray; source retained entirely','samples':len(points),'violations':viol[:20],'scope':'Checks original closed roof retained and no sampled added point exceeds original roof. Not a wall-thickness or strength certificate.'},'printTransform':M.tolist(),'orientationSource':{'file':str(op),'sha256':sha(op)},'flatBedAreaWithin002Mm':area,'printBoundsMm':pm.bounds.tolist(),'nativeCombinedBRepExported':False,'nativeSourceBoundary':'Exact source cap STEP and six native mounting STEP assets are provided; combined STL uses validated mesh Boolean union, not a fabricated native BRep.','usbBoundary':'4472 straightC receiver conflicts with closed shell; replacement finished host-compatible Micro-B to C cable remains unselected.'}
(D/'cap-union.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k in ['status','connectedComponents','volumeMm3','boundsMaxDifferenceMm','removedSourceVolumeMm3','addedVolumeMm3','flatBedAreaWithin002Mm']}));assert not viol,viol[:3]
