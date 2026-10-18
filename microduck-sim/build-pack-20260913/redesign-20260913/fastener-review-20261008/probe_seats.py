from pathlib import Path
import json,numpy as np,trimesh,hashlib
D=Path(__file__).resolve().parent;R=D.parent;p=R/'head-redesign-20261008/head-fit-investigation.py';n={'__file__':str(p)};exec(p.read_text().split("report={'problemIds'")[0],n)
data=n['data'];ss=data['screws'];by={p['key']:p for p in data['parts']};solid=n['solid'];man=n['man'];sample=n['samples']
def cyl(a,b,r):
 a=np.array(a);b=np.array(b);T=trimesh.geometry.align_vectors([0,0,1],b-a);T[:3,3]=(a+b)/2
 return man(trimesh.creation.cylinder(radius=r,height=np.linalg.norm(b-a),sections=96).apply_transform(T))
def tri(s):
 m=s.to_mesh();return trimesh.Trimesh(m.vert_properties[:,:3],m.tri_verts,process=True)
def collisions(s,except_keys=()):
 hits={};bb=np.array(s.bounding_box()).reshape(2,3)
 for k in by:
  if k in except_keys:continue
  q=solid(k);qb=np.array(q.bounding_box()).reshape(2,3)
  if np.any(bb[1]<qb[0]) or np.any(qb[1]<bb[0]):continue
  v=float((s^q).volume())
  if v>1e-6:hits[k]=v
 return hits
out=[]
for key,motor in [('neck_pitch',13),('lower',7),('right_lower',2)]:
 screws=[s for s in ss if s['id'].startswith(f'S{motor:02}-horn-')];base=solid(key);cand=base
 for s in screws:
  a=np.array(s['world_center_mm']);v=np.array(s['world_axis']);pad=cyl(a-v*.05,a+v,2.5)-cyl(a-v*.1,a+v*1.1,1.2);cand=cand+pad
 if key=='neck_pitch':
  for s in screws:
   a=np.array(s['world_center_mm']);v=np.array(s['world_axis']);cand=cand-cyl(a-v*(max(s['stack_mm'])+.01),a+v*1.1,1.2)
 addition=cand-base;mesh=tri(cand);mesh.export(D/(key+'-m2x6-seat-world.stl'));local=mesh.copy().apply_transform(np.linalg.inv(by[key]['sourceTransformWorld']));local.export(D/(key+'-m2x6-seat-source-frame.stl'))
 headrows=[]
 for s in screws:
  a=np.array(s['world_center_mm'])+np.array(s['world_axis']);v=np.array(s['world_axis']);head=cyl(a+v*.001,a+v*1.72,2);headrows.append({'id':s['id'],'newSeatWorldMm':a.tolist(),'newSpec':'M2 x 6 TAP','entryMm':[6-x-1 for x in reversed(s['stack_mm'])],'headContacts':collisions(head,[key]),'headVsCandidateMm3':float((head^cand).volume())})
 row={'part':key,'stockFile':by[key].get('stockFile'),'sourceMesh':by[key].get('source'),'bodyCount':len(cand.decompose()),'watertight':mesh.is_watertight,'addedVolumeMm3':float(addition.volume()),'boreCleanupRemovedMm3':float((base-cand).volume()),'newMaterialContacts':collisions(addition,[key]),'screws':headrows};out.append(row);print(json.dumps(row),flush=True)
(D/'seat-probe.json').write_text(json.dumps({'sourceDataSha256':hashlib.sha256(n['raw']).hexdigest(),'parts':out},indent=2)+'\n')
# IMU is a pressure screw: keep the same rail contact point, raising the head 1mm.
imu=[]
for s in ss:
 if s.get('groupId')!='imu_clamp':continue
 v=np.array(s['world_axis']);a=np.array(s['world_center_mm'])+v;shaft=cyl(a-v*6,a,1);head=cyl(a,a+v*1.72,2);tool=cyl(a+v*.5,a+v*40,1.5)
 # The holder pilot intentionally receives the tapping thread; rail contact is the endpoint.
 imu.append({'id':s['id'],'newSeatWorldMm':a.tolist(),'tipWorldMm':(a-v*6).tolist(),'newSpec':'M2 x 6 TAP pressure screw','shaftOtherPartsContacts':collisions(shaft,['imu_clamp']),'headContacts':collisions(head),'toolContacts':collisions(tool),'headToHolderGapMm':1.8})
(D/'imu-pressure-probe.json').write_text(json.dumps({'sourceDataSha256':hashlib.sha256(n['raw']).hexdigest(),'rows':imu},indent=2)+'\n');print('IMU',json.dumps(imu),flush=True)
