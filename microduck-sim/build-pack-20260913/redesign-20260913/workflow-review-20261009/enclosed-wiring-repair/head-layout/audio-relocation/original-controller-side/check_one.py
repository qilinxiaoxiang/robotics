"""One evidence-directed amplifier rotation beside the fixed complete original OpenRB."""
from pathlib import Path
import os,json,math,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
Q=Path(__file__).resolve().parent;O=Q.parent
ns={'__file__':str(O/'check_one_pose.py')};exec((O/'check_one_pose.py').read_text().split('Tp=')[0],ns)
np=ns['np'];mf=ns['mf'];load=ns['load'];read=ns['read'];sha=ns['sha'];pm=ns['pm'];ctx=ns['ctx'];H=ns['H'];D=O.parent;W=ns['W'];hashes=ns['hashes']
T=np.array([[0.,-1,0,33],[1,0,0,3.5],[0,0,1,0],[0,0,0,1]])
oldamp=load(O/'amplifier-positive-y13-world.stl');amp=oldamp.transform(T[:3]);holes=[[32.3499993896,16.787000885,135.5849994],[19.6499993896,16.787000885,135.5849994]]
posts=[mf.Manifold.cylinder(23,2,circular_segments=48).translate(p) for p in holes]
checks=[]
def test(name,s,row,ob,representation):
 a=np.array(s.bounding_box()).reshape(2,3);b=np.array(ob.bounding_box()).reshape(2,3);sep=np.any(a[1]<b[0])or np.any(b[1]<a[0]);q=None if sep else s^ob;v=0 if sep else max(0,q.volume());checks.append({'moving':name,'fixed':row,'representation':representation,'volumeMm3':v,'boundsMm':list(q.bounding_box())if v>1e-6 else None})
inv=read(O/'positive-y13-native/current-rigid-inventory.json')
for row in inv['parts']:
 if row['id']=='current_amp':continue
 assert sha(row['file'])==row['sha256'];ob=load(row['file']).transform(np.array(row['worldTransform'])[:3]);test('candidate_amp',amp,row['id'],ob,'current listed rigid source')
 if row['id']!='current_cap':
  for i,post in enumerate(posts):test('proposed_post_ray_'+str(i),post,row['id'],ob,'Conservative boss ray; native roof termination still required')
 del ob;gc.collect()
em=read(H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json');assert em['allSourceTrianglesCoveredExactlyOnce'];assert sha(em['sourceFile'])==em['sourceSha256'];actual=read(D/'actual-openrb-components/micro-contact-proof.json');override={q['index']:(q['mesh'],q['meshSha256'])for q in actual['records']if q.get('mesh')};pins=read(W/'enclosed-wiring-repair/power-sensor/head-controller-study/actual-pin-components.json');override.update({q['index']:(q['file'],q['sha256']) for q in pins['records']})
openrbRows=[]
for row in em['components']:
 i=row['index'];f,h=override.get(i,(row['mesh'],row['meshSha256']));assert sha(f)==h;ob=load(f);rep='actual source component'if i in override else'component convex enclosure with full source coverage';openrbRows.append({'component':i,'file':f,'sha256':h,'representation':rep});test('candidate_amp',amp,'original_OpenRB_'+str(i),ob,rep)
 for j,post in enumerate(posts):test('proposed_post_ray_'+str(j),post,'original_OpenRB_'+str(i),ob,rep)
 if i==141:test('old_amp_negative_control',oldamp,'original_OpenRB_'+str(i),ob,rep)
 del ob;gc.collect()
reg=read(D/'native-fusion-repair-inputs.json');Tr=np.array(reg['openrb']['nativeToCurrentWorld']);port=read(D/'openrb-usbc-native-port.json');p=port['correctedAssumedMouldShoulderMm'];plugs={'original_C_mould22':mf.Manifold.cube([12,22,7]).translate([p[0]-6,p[1],p[2]-3.5]).transform(Tr[:3]),'original_C_relief5':mf.Manifold.cylinder(5,3.25/math.cos(math.pi/64),circular_segments=64).rotate([-90,0,0]).translate([p[0],p[1]+22,p[2]]).transform(Tr[:3])}
ports=read(W/'enclosed-wiring-repair/motor-wires/two-openrb-ports.json')
for i,row in enumerate(ports['ports']):
 b=np.array(row['housingLocalBounds']);plugs['original_EH_'+str(i)]=mf.Manifold.cube(b[1]-b[0]).translate(b[0]).transform(np.array(row['transform'])[:3])
for k,ob in plugs.items():
 test('candidate_amp',amp,k,ob,'Full source-bound connector receiving, not detailed mating CAD')
 for i,post in enumerate(posts):test('proposed_post_ray_'+str(i),post,k,ob,'Full source-bound connector receiving')
# The amplifier terminal faces now face -Y into the controller-side gap.
terminalMouths=[[24.3,13.703,137.785],[27.8,13.703,137.785]]
f=Q/'amplifier-quarter-turn-side-world.stl';pm.export(ctx,amp,f)
r={'status':'ONE_STATIC_CANDIDATE_NOT_ADOPTED','wholeHeadAccepted':False,'nativeOrPrintFilesChanged':False,'transformFromY13':T.tolist(),'ampBoundsMm':list(amp.bounding_box()),'holeTopCentersMm':holes,'terminalMouthsMm':terminalMouths,'terminalOutwardAxis':[0,-1,0],'sourceOpenRBComponentsExpected':142,'sourceOpenRBComponentsChecked':len(openrbRows),'openrbRepresentation':openrbRows,'sourceNativeBodies':136,'inventory':inv['parts'],'checks':checks,'hits':[x for x in checks if x['volumeMm3']>1e-6 and x['moving']!='old_amp_negative_control'],'negativeControls':[x for x in checks if x['moving']=='old_amp_negative_control'],'sourceHashes':hashes|{str(Path(__file__)):sha(__file__)},'mesh':str(f),'meshSha256':sha(f),'remaining':['Complete USB/Pi/OpenRB interfaces are owned by the coupled head study; this does not solve its other existing failures.','Speaker output wire departure, mounting access and native roof post termination not yet accepted.','Old Y13 amp posts remain in the queried cap. They must be moved through native features if this candidate is adopted.']}
r['ampStaticClear']=not any(x['moving']=='candidate_amp'for x in r['hits']);r['bossReceivingRaysClearOfOtherHardware']=not any(x['moving'].startswith('proposed_post')for x in r['hits']);(Q/'check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k]for k in ['ampBoundsMm','sourceOpenRBComponentsChecked','ampStaticClear','bossReceivingRaysClearOfOtherHardware','hits','negativeControls']},indent=2))
