from pathlib import Path
import os,json,hashlib,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
D=Path(__file__).resolve().parent; F=D.parents[2]/'power-sensor/head-controller-study/final-integration-20261009'; SRC=F/'integrated-rigid-package.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(row):
 assert sha(row['file'])==row['sha256'];m=tm.load(row['file'],force='mesh');m.apply_transform(row['worldTransform']);s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)));assert s.status()==mf.Error.NoError;return s
rows=json.loads(SRC.read_text())['parts'];caprow=next(q for q in rows if q['key']=='current_cap');cap=load(caprow)
def cyl(x,y,z,r,h):return mf.Manifold.cylinder(h,r,r,64).translate([x,y,z])
def box(c,d):return mf.Manifold.cube(d,True).translate(c)
def export(s,key):
 m=s.to_mesh64();t=tm.Trimesh(np.asarray(m.vert_properties)[:,:3],np.asarray(m.tri_verts),process=False);p=D/(key+'.stl');p.write_text(tm.exchange.stl.export_stl_ascii(t));back=tm.load(p,force='mesh');assert back.is_watertight and back.is_winding_consistent;return {'key':key,'file':str(p),'sha256':sha(p),'worldTransform':np.eye(4).tolist(),'volumeMm3':s.volume(),'boundsMm':list(s.bounding_box())}
made={};spec=[];seat=135.5849994;depth=7.2
for i,x in enumerate([32.3499993896,19.6499993896]):
 y=16.287000885;near=cap^box([x,y,148],[4.2,4.2,40]);column=mf.Manifold.batch_boolean([near.translate([0,0,-dz])for dz in np.arange(0,31,.5)],mf.OpType.Add);p=cyl(x,y,seat,2,160-seat)^column;p-=cyl(x,y,seat,1.05,depth);assert len(p.decompose())==1
 
 if i==1:
  eh=load(next(q for q in rows if q['key']=='EH0'));hit=p^eh;print('EH contact',hit.volume(),list(hit.bounding_box()),flush=True)
  relief=eh.minkowski_sum(box([0,0,0],[1,1,1]));p-=relief;assert len(p.decompose())==1
 made['amp_roof_post_'+str(i)]=p;made['amp_screw_'+str(i)]=cyl(x,y,seat-1.57,1.25,8)+cyl(x,y,seat-1.57-1.7,2.5,1.7);made['amp_driver_'+str(i)]=cyl(x,y,seat-1.57-31.7,1.5,30)
 spec.append({'xyMm':[x,y],'seatZMm':seat,'bossDiameterMm':4,'pilotDiameterMm':2.1,'pilotDepthMm':depth,'screw':'M2.5 x 8 TAP engineering interface','pcbStackMm':1.57,'engagementMm':6.43,'tipAllowanceMm':.77,'threadStrengthPhysicallyVerified':False})
checks=[]
for row in rows:
 ob=load(row);b=np.array(ob.bounding_box()).reshape(2,3)
 for k,s in made.items():
  if k.startswith('amp_roof') and row['key']=='current_cap':continue
  if k.startswith('amp_driver') and not (row['key']=='current_cap' or 'mount' in row['key'].lower() or 'roof' in row['key'].lower()):continue
  a=np.array(s.bounding_box()).reshape(2,3);v=0. if np.any(a[1]<b[0]) or np.any(b[1]<a[0]) else max(0,(s^ob).volume());checks.append({'moving':k,'fixed':row['key'],'volumeMm3':v,'boundsMm':list((s^ob).bounding_box())if v>1e-7 else None})
 del ob;gc.collect()
# The native amp mesh has 7.4 nm seat rounding and a faceted nominal bore.
# These four exact named mating pairs retain narrow source-contact bounds.
for q in checks:
 q['sourceMatingContact']=q['fixed']=='current_amp' and q['moving'].startswith(('amp_roof_post_','amp_screw_')) and q['volumeMm3']<=.0002
 q['failed']=q['volumeMm3']>1e-6 and not q['sourceMatingContact']
sections=[]
for z in [136,138,139.25,140,142,144,146]:
 q=made['amp_roof_post_1']^box([19.6499993896,16.287000885,z],[5,5,.01]);sections.append({'zMm':z,'crossSectionAreaMm2':q.volume()/.01})
assert min(q['crossSectionAreaMm2']for q in sections)>0
print('sections',sections,flush=True)
parts=[export(s,k)for k,s in made.items()if not k.startswith('amp_driver')];hits=[q for q in checks if q['failed']];r={'status':'LOCAL_MOUNT_CHECK','integrationReady':not hits,'wholeHeadAccepted':False,'sourceManifest':str(SRC),'sourceSha256':sha(SRC),'scriptSha256':sha(__file__),'parts':parts,'mounts':spec,'leftPostEhRelief':{'clearanceMm':.5,'fullCircumferentialEngagementLowerBoundMm':3.16,'remainingUpperThread':'Locally open on the EH-facing side; not counted as full-circumference engagement.','crossSections':sections},'checks':checks,'hits':hits,'assemblyOrder':['Solder input leads and tighten the two speaker output terminal screws on the loose amplifier.','On the detached cap, mount amplifier before the controller/Pi and speaker cage obscure tool access.','Use two M2.5 x 8 screws in the existing tapping interface; check plastic-thread fit physically.'],'scope':'Separate additions only; merge posts into current cap without replacing other native board mounts. Shaft/pilot engagement is intentional only for this specified interface.'};(D/'amp-mount-fragment.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'checks':len(checks),'hits':hits,'parts':parts},indent=2))
