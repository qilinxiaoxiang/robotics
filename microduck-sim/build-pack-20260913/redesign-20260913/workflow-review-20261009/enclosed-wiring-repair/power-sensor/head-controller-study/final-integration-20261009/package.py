from pathlib import Path
import json,hashlib,numpy as np,trimesh,manifold3d as mf
F=Path(__file__).resolve().parent;D=F.parent;W=D.parents[2];HD=W/'enclosed-wiring-repair/head-layout';H=W.parent/'head-redesign-20261008';SIM=W.parents[2]
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def row(key,file,T,group,kind='source_mesh'):
 return {'key':key,'file':str(file),'sha256':sha(file),'worldTransform':np.array(T).tolist(),'group':group,'geometryKind':kind}
I=np.eye(4);old=np.array(read(HD/'native-fusion-repair-inputs.json')['openrb']['nativeToCurrentWorld']);a=np.radians(30);p=np.radians(3);c=np.array([np.cos(a),-np.sin(a),0]);u=np.array([np.sin(a),np.cos(a),0]);T=I.copy();T[:3,:3]=np.column_stack([u,c*np.cos(p)+np.array([0,0,np.sin(p)]),c*np.sin(p)-np.array([0,0,np.cos(p)])]);T[:3,3]=[25,2,139.5]
P=I.copy();P[:3,:3]=[[0,-1,0],[0,0,-1],[1,0,0]];P[:3,3]=np.array([44,26,127])-P[:3,:3]@np.array([59,-1,131.5])
parts=[];en=read(H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json');actual={q['index']:(q['mesh'],q['meshSha256'])for q in read(HD/'actual-openrb-components/micro-contact-proof.json')['records']if q.get('mesh')};actual.update({q['index']:(q['file'],q['sha256'])for q in read(D/'actual-pin-components.json')['records']})
for q in en['components']:
 f,h=actual.get(q['index'],(q['mesh'],q['meshSha256']));assert sha(f)==h;parts.append(row('OpenRB_'+str(q['index']),f,T@np.linalg.inv(old),'controller','actual_manufacturer_component'if q['index']in actual else'conservative_component_hull'))
def boxfile(key,b,transform,group):
 m=trimesh.creation.box(extents=np.array(b[1])-b[0]);m.apply_translation(np.mean(b,axis=0));f=F/(key+'.stl');m.export(f);parts.append(row(key,f,transform,group,'receiving_assumption'))
port=read(HD/'openrb-usbc-native-port.json');s=np.array(port['correctedAssumedMouldShoulderMm']);boxfile('C22-receiving',[s+[-6,0,-3.5],s+[6,22,3.5]],T,'controller')
m=trimesh.creation.cylinder(3.25/np.cos(np.pi/64),5,sections=64);m.apply_translation([0,0,2.5]);R=trimesh.transformations.rotation_matrix(-np.pi/2,[1,0,0]);m.apply_transform(R);m.apply_translation(s+[0,22,0]);f=F/'C5-relief.stl';m.export(f);parts.append(row('C5-relief',f,T,'controller','receiving_assumption'))
for n,q in enumerate(read(W/'enclosed-wiring-repair/motor-wires/two-openrb-ports.json')['ports']):boxfile('EH'+str(n),q['housingLocalBounds'],T@np.linalg.inv(old)@q['transform'],'controller')
nm=[q for q in read(W/'enclosed-wiring-repair/ankle-wires/native-motors/manifest.json')['parts']if q['motor']==2];gt={q['key']:np.array(q.get('sourceTransformWorld',I))for q in read(W.parent/'leg-guide-20261006/full-build-data.json')['parts']}
for q in read(HD/'audio-relocation/positive-y13-native/current-rigid-inventory.json')['parts']:
 key=q['id'];f=q['file'];M=np.array(q['worldTransform']);group='fixed'
 if key=='current_cap':f=H/'curved-head/community-curved-head-world.stl';M=I
 elif key.startswith('REFERENCE Pi current'):group='pi';M=P@M
 elif key=='REFERENCE MicroB photo receiving':group='pi_interface_conditional';M=P@M
 elif key in ['REFERENCE current speaker','REFERENCE current speaker_keeper','current_cradle']:group='speaker';V=I.copy();V[1,3]=-24;M=V@M
 elif key=='current_amp':
  group='amp';m=trimesh.load_mesh(f);m.apply_transform(M);center=m.bounds.mean(axis=0);V=I.copy();V[:3,:3]=np.diag([1,-1,-1]);V[:3,3]=np.array([62,12,131])-V[:3,:3]@center;M=V@M
 elif key.split()[-1]in ['motor13','motor14','motor15']:
  for n in nm:parts.append(row(key+'/'+str(n['solid']),n['file'],gt[key.split()[-1]]@np.linalg.inv(n['worldTransform']),'fixed','actual_manufacturer_motor'))
  continue
 parts.append(row(key,f,M,group))
r={'status':'DIMENSIONED_JOINT_CANDIDATE_NOT_ACCEPTED','originalShellPreserved':True,'parts':parts,'boardNativeToWorld':T.tolist(),'piCurrentWorldDelta':P.tolist(),'speakerDeltaMm':[0,-24,0],'ampTargetCenterMm':[62,12,131],'missingRequiredInterfaces':[{'id':'USB_A_OTG_join','reason':'SC0727 is borrow-first/unconfirmed. Conditional 47.9x20x12 historical reception is not an owned part. A complete USB choice is mandatory before acceptance.'}],'microBReceiving':'Historical photo receiving only, not a manufacturer-specific verified SC0727 body. Kept visible and tested rather than silently omitted.','stage':'Static rigid packaging; no mounts, closing or assembly acceptance.'};(F/'joint-package.json').write_text(json.dumps(r,indent=2)+'\n');print(len(parts))
