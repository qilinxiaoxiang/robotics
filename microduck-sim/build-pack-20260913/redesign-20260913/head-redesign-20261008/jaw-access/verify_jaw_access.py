"""Additional exported-mesh verification, including bolt entry and seating."""
from pathlib import Path
import json,numpy as np,trimesh,hashlib
OUT=Path(__file__).resolve().parent;p=OUT.parent/'head-fit-investigation.py';ns={'__file__':str(p)};exec(p.read_text().split("report={'problemIds'")[0],ns)
def load(k):return ns['man'](trimesh.load(OUT/(k+'-world.stl'),force='mesh'))
P=np.array([26.1,0,118.6146])
def pose(s):return s.translate(-P).rotate([0,30,0]).translate(P)
r=json.loads((OUT/'report.json').read_text());f=json.loads((OUT/'viewer-fragment.json').read_text());fails=[]
repairs=r.get('exportTriangulationRepairs',[])
for part in r['parts']:
 path=OUT/(part['key']+'-world.stl');mesh=trimesh.load(path,force='mesh')
 if mesh.is_watertight:continue
 orig=ns['man'](mesh);clean=orig.simplify(.00001);cm=clean.to_mesh();mesh=trimesh.Trimesh(np.asarray(cm.vert_properties)[:,:3],np.asarray(cm.tri_verts),process=False);mesh.export(path);mesh.copy().apply_transform(np.linalg.inv(np.array(r['bodyFrameToWorldMm']))).export(OUT/(part['key']+'-jaw_soft.stl'))
 repairs.append({'key':part['key'],'surfaceToleranceMm':.00001,'volumeChangeMm3':float(clean.volume()-orig.volume()),'reason':'Collapse sub-float32 triangulation slivers so an STL round-trip remains watertight.'})
r['exportTriangulationRepairs']=repairs
r['candidateBeakOutsideOriginalVerticalSkinEnvelopeMm3']=r.pop('candidateBeakOutsideOriginalCombinedEnvelopeMm3',r.get('candidateBeakOutsideOriginalVerticalSkinEnvelopeMm3'))
r['beakEnvelopeMethod']='Original upper/lower external skins, with only the internal vertical gap filled in X=55..81 mm, Y=-40..-20 mm; outer limits remain unchanged. Boolean volume residual is limited to 0.0001 mm^3.'
main=load('jaw_main');arm=load('jaw_passive_cheek');pad=load('lower_pad_jaw_access')
fixed={k:ns['solid'](k) for k in ['jaw_support','motor15','motor14','head_yaw_link','head_roll_ring_a','head_roll_ring_b']};fixed['head_bottom']=load('head_bottom_clearance');fixed|={'jaw_passive_cheek':pose(arm),'lower_pad':pose(pad)}
if not r['sourceUnchangedDuringRun']:fails.append({'sourceChangedDuringBuild':True})
for c in r['acceptedContacts']:
 if c['pair']=='support--head_roll_ring_a':
  bb=np.array(c['boundsMm'])
  if not (bb[0,0]>=5.9999999 and bb[1,0]<=6.0000005):fails.append({'ringContactPlane':c})
for c in r['articulationMotorContactBounds']:
 bb=np.array(c['boundsMm'])
 if not (bb[0,1]>=39.9989 and bb[1,1]<=40.0001):fails.append({'motorContactPlane':c})
checks=[]
for i,x in enumerate([60.,76.],1):
 key=f'jaw_cheek_screw_{i}';bolt=load(key);route=ns['samples']({key:pose(bolt)},fixed,[0,-40,0],step=.25)
 if route['peakContactsMm3']:fails.append({'boltEntry':key,'contacts':route['peakContactsMm3']})
 it=bolt^main;bb=np.array(it.bounding_box()).reshape(2,3)
 # The only screw/plastic overlap must lie within the specified pilot's thread envelope.
 bmin=np.array([x-1.251,-29.901,101.249]);bmax=np.array([x+1.251,-25.999,103.751]);allowed=bool(np.all(bb[0]>=bmin) and np.all(bb[1]<=bmax) and 0<float(it.volume())<8)
 if not allowed:fails.append({'invalidThreadEngagement':key,'volumeMm3':float(it.volume()),'boundsMm':bb.tolist()})
 checks.append({'key':key,'entry':route,'threadEngagement':{'volumeMm3':float(it.volume()),'boundsMm':bb.tolist(),'allowed':allowed,'scope':'Intentional TAP engagement only, within the 2.1 mm pilot and 2.5 mm nominal shaft envelope. No material or torque qualification.'}})
# Re-run geometric motion on exported meshes, after STL float precision cleanup.
H=load('head_bottom_clearance');S=ns['solid']('jaw_support');M=ns['solid']('motor15')
neck={k:ns['solid'](k) for k in ['motor14','head_yaw_link','head_roll_ring_a','head_roll_ring_b']}
base=neck|{'jaw_support':S,'head_bottom':H,'motor15':M};export_routes={}
for name,m,obs,v in [('main_and_pad',{'jaw_main':pose(main),'pad':pose(pad)},base,[0,32,0]),('passive_cheek',{'jaw_passive_cheek':pose(arm)},base|{'jaw_main':pose(main),'pad':pose(pad)},[0,-32,0]),('pad_bench',{'pad':pad},{'jaw_main':main},[0,0,32]),('lower_shell',{'shell':H},neck,[0,0,-40]),('support_motor_group',{'support':S,'motor15':M},neck|{'shell':H},[0,0,40])]:
 result=ns['samples'](m,obs,v,step=.25);export_routes[name]=result
 for n,row in enumerate(result['samples']):
  for pair,volume in row['contactsMm3'].items():
   orig=r['routes'][name]['samples'][n]['contactsMm3'].get(pair,0)
   if volume>orig+1e-6:fails.append({'exportMotionChanged':name,'sample':n,'pair':pair,'volumeMm3':volume,'sourceMm3':orig})
static=base|{k:ns['solid'](k) for k in ['head_cap','face_panel','upper_pad','eye_trim','pi']};export_angles=[]
for angle in np.linspace(0,30,121):
 hits={}
 for key,shape in {'jaw_main':main,'jaw_passive_cheek':arm,'lower_pad':pad,'jaw_cheek_screw_1':load('jaw_cheek_screw_1'),'jaw_cheek_screw_2':load('jaw_cheek_screw_2')}.items():
  m=shape.translate(-P).rotate([0,float(angle),0]).translate(P)
  for key2,ob in static.items():
   it=m^ob;vol=float(it.volume())
   if vol<=1e-6:continue
   hits[key+'--'+key2]=vol;bb=np.array(it.bounding_box()).reshape(2,3)
   if key!='jaw_main' or key2!='motor15' or vol>.149 or bb[0,1]<39.9989 or bb[1,1]>40.0001:fails.append({'exportArticulation':float(angle),'pair':key+'--'+key2,'volumeMm3':vol})
 export_angles.append({'degrees':float(angle),'contactsMm3':hits})
r['exportedMeshRoutes']=export_routes;r['exportedMeshArticulation']=export_angles
# Match exported manufactured geometry to recorded watertight/component requirement.
mesh_checks=[]
for part in r['parts']:
 s=load(part['key']);m=trimesh.load(OUT/(part['key']+'-world.stl'),force='mesh');rec={'key':part['key'],'sha256':hashlib.sha256((OUT/(part['key']+'-world.stl')).read_bytes()).hexdigest(),'components':len(s.decompose()),'watertight':bool(m.is_watertight)};mesh_checks.append(rec)
 if rec['components']!=1 or not rec['watertight']:fails.append(rec)
r['sourceHashes']={'jaw-access/'+name:hashlib.sha256((OUT/name).read_bytes()).hexdigest() for name in ['build_jaw_access.py','verify_jaw_access.py','verify_negative.py']}
r['sourceHashes']['../leg-guide-20261006/full-build-data.json']=r['sourceSha256']
r['sourceHashes'].update({'jaw-access/'+x['key']+'-world.stl':x['sha256'] for x in mesh_checks})
r['buildScriptSha256']=hashlib.sha256((OUT/'build_jaw_access.py').read_bytes()).hexdigest();r['verificationScriptSha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();r['exportedMeshChecks']=mesh_checks;r['newScrewInsertionChecks']=checks;r['additionalDigitalFailures']=fails
passed=not r['digitalFailures'] and not fails
r['digitalAssemblyPassed']=passed;r['fullHeadAssemblyPassed']=False;r['jawAssemblySequencePassed']=passed;r['scope']='Jaw access manufacturing candidate: sampled rigid assembly and screw access only; not physical material/strength qualification'
f['integrationReady']=passed;f['acceptance']['digitalAssemblyPassed']=passed
(OUT/'report.json').write_text(json.dumps(r,indent=2)+'\n');(OUT/'viewer-fragment.json').write_text(json.dumps(f,indent=2)+'\n')
print(json.dumps({'passed':passed,'additionalFailures':fails,'meshChecks':mesh_checks},indent=2))

if not passed:raise SystemExit(1)
