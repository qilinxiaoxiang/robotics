from pathlib import Path
import hashlib,json
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;W=D.parents[2];R=W.parent;SIM=R.parents[1];O=W/'roof-wiring-stage/motor-wires/obstacles';C=SIM/'hardware-design-20260912/whole-robot-20260912/assembly/compact-battery'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
 m=trimesh.load_mesh(p);assert m.is_volume,p;s=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError;return s

def box(lo,hi):return mf.Manifold.cube(np.array(hi)-lo).translate(lo)
def export(s,p):
 a=s.to_mesh64();m=trimesh.Trimesh(a.vert_properties[:,:3],a.tri_verts,process=True);assert m.is_volume;p.write_text(m.export(file_type='stl_ascii'));rr=trimesh.load_mesh(p);assert rr.is_volume,('Export readback invalid',str(p));return {'file':str(p),'sha256':sha(p),'boundsMm':m.bounds.tolist(),'bodies':len(m.split()),'components':[{'volumeMm3':q.volume,'boundsMm':q.bounds.tolist()}for q in m.split()]} 
oldfile=C/'power-support-integrated-body.stl';origfile=C/'original-power-support-body.stl';old=load(oldfile);original=load(origfile);add=load(D/'carrier-additions-world.stl')
# Explicitly retire only the old rear tray and lower regulator shelf. Source12
# original frame above its established trim plane is restored before the new bay.
retire=box([-65,-22,-60],[-21.79,22,30]);retained=((old-retire)^box([-100,-100,-38],[100,100,100]))+(original^box([-100,-100,-38],[100,100,100]))
# New lower board window moves the old bottom crossmember to the native lower deck.
window=box([-40.6,-13.6,-50.6],[-9.4,13.6,-35.0]);controller_window=box([-38.85,-13.21,-35.39],[-19.05,13.21,32.5])
retained=retained-window-controller_window
candidate=retained+add;out=export(candidate,D/'power-support-controller-concept-world.stl');retmeta=export(retained,D/'retained-source-frame-world.stl')
nm=json.loads((D.parents[1]/'ankle-wires/native-motors/manifest.json').read_text()); motorparts=[q for q in nm['parts']if q['motor']==2];gp=R/'leg-guide-20261006/full-build-data.json';transforms={p['key']:p.get('sourceTransformWorld')for p in json.loads(gp.read_text())['parts']}
checks=[];excluded={'regulator','regulator_insert','power_support','openrb','curved_cap_hardware'}
for f in sorted(O.glob('*.json')):
 ob=json.loads(f.read_text());assert sha(ob['file'])==ob['sha256'];k=ob['key'];r={'key':k,'sourceSha256':ob['sha256']}
 if k in excluded:r['status']='REPLACED_OR_OLD_HEAD_CONTROLLER_HARDWARE';checks.append(r);continue
 bb=np.array(ob['expectedFinalBoundsMm']);a=np.array(add.bounding_box()).reshape(2,3)
 if np.any(a[1]<bb[0])or np.any(bb[1]<a[0]):r['status']='BOUNDS_SEPARATE';checks.append(r);continue
 if k.startswith('motor') and k[5:].isdigit():
  sub=[]
  for q in motorparts:
   assert sha(q['file'])==q['sha256'];s=load(q['file']).transform((np.array(transforms[k])@np.linalg.inv(q['worldTransform']))[:3]);cut=add^s;assert cut.status()==mf.Error.NoError
   if cut.volume()>1e-6:sub.append({'solid':q['solid'],'volumeMm3':cut.volume(),'boundsMm':list(cut.bounding_box())})
  r.update(status='INTERSECTION'if sub else'CLEAR',nativeMotorHits=sub);checks.append(r);continue
 s=load(ob['file']).translate(ob.get('importTranslationMm',[0,0,0]));cut=add^s;assert cut.status()==mf.Error.NoError;r.update(status='INTERSECTION'if cut.volume()>1e-6 else'CLEAR',intersectionMm3=cut.volume(),boundsMm=list(cut.bounding_box())if cut.volume()>1e-6 else None);checks.append(r)
board=box([-40,-13,-50],[-10,13,-42]);c=candidate^board;df={'intersectionMm3':c.volume(),'bounds':list(c.bounding_box())if c.volume()>1e-6 else None}
# Explicit full-component conservative OpenRB source geometry at the one chosen pose.
H=R/'head-redesign-20261008';ep=H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json';rec=json.loads(ep.read_text());regfile=W/'enclosed-wiring-repair/head-layout/native-fusion-repair-inputs.json';reg=json.loads(regfile.read_text());T=np.array([[0,0,1,-29.5],[1,0,0,0],[0,1,0,-1],[0,0,0,1]],float);delta=T@np.linalg.inv(reg['openrb']['nativeToCurrentWorld']);electronics=[];seats=[]
for q in rec['components']:
 assert sha(q['mesh'])==q['meshSha256'];s=load(q['mesh']).transform(delta[:3]);cut=candidate^s;assert cut.status()==mf.Error.NoError
 if cut.volume()>1e-6:
  entry={'component':q['index'],'volumeMm3':cut.volume(),'boundsMm':list(cut.bounding_box())}
  bb=np.array(cut.bounding_box()).reshape(2,3)
  if q['index']==141 and cut.volume()<.001 and abs(bb[1,0]+29.5)<1e-7 and bb[1,0]-bb[0,0]<.00002:seats.append(entry)
  else:electronics.append(entry)
removed=old-candidate;protected=[]
for y in [-9.5,9.5]:
 c=mf.Manifold.cylinder(40,2.5,2.5,64).translate([-16.5,y,-8]);v=(removed^c).volume();protected.append({'holeAxisXY':[-16.5,y],'radialProtectionMm':2.5,'zRange':[-8,32],'removedVolumeMm3':v})
assert all(q['removedVolumeMm3']<1e-6 for q in protected),protected
r={'originalMountProtection':protected,'status':'INDEPENDENT CARRIER CONCEPT, NOT PRINT RELEASE','sourceHashes':{str(p):sha(p)for p in [oldfile,origfile,D/'carrier-additions-world.stl',ep,regfile,Path(__file__)]},'candidate':out,'retainedOriginalMesh':retmeta,'nativeAdditionsStep':str(D/'carrier-additions-world.step'),'originalFramePolicy':'Preserve original source12 frame at/above its existing Z-38 trim except explicitly bounded lower-board window. Keep old front IMU mount; retire old rear tray and lower regulator shelf. New low shelf and outer rails carry across that window.','retiredRegionBoundsMm':[[-65,-22,-60],[-21.79,22,30]],'boardWindowBoundsMm':[[-40.6,-13.6,-50.6],[-9.4,13.6,-35.0]],'controllerWindowBoundsMm':[[-38.85,-13.21,-35.39],[-19.05,13.21,32.5]],'addedFeaturesBodyChecks':checks,'DFRReceiving':df,'OpenRBConservativeComponentHits':electronics,'namedPCBSeatingContact':{'rows':seats,'limit':'Only PCB141 at X-29.5 seating plane, thickness<0.00002 and volume<0.001 mm3; floating source tessellation straddles nominal native PCB plane. No component collision waived.'},'nativeOpenRBToWorld':T.tolist(),'manufacturingAccepted':False,'insertionAndToolAccessAccepted':False,'newStaticClear':not any(x['status']=='INTERSECTION'for x in checks)and df['intersectionMm3']<1e-6 and not electronics}
(D/'carrier-check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'bodies':out['bodies'],'hits':[q for q in checks if q['status']=='INTERSECTION'],'dfr':df,'openrb':electronics,'report':str(D/'carrier-check.json')},indent=2))
