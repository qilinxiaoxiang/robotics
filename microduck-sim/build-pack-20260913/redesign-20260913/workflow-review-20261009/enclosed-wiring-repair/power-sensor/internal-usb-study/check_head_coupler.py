from pathlib import Path
import json,hashlib,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;W=D.parents[2];R=W.parent;HD=W/'enclosed-wiring-repair/head-layout';C=D.parent/'carrier-concept';hashes={};conservative=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):hashes[str(p)]=sha(p);return json.loads(Path(p).read_text())
def load(p):
 hashes[str(p)]=sha(p);m=trimesh.load_mesh(p)
 if not m.is_volume:
  assert Path(p).name.startswith('component_'),('Invalid receiving mesh',str(p))
  original=m;m=original.convex_hull;assert m.is_volume
  conservative.append({'file':str(p),'method':'Closed convex hull contains all original component vertices; conservative local receiving body, no deleted obstruction','originalVolumeValid':False,'hullVolumeMm3':m.volume})
 s=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError;return s

def transform(s,T):return s.transform(np.array(T)[:3])
def separated(a,b):
 x=np.array(a.bounding_box()).reshape(2,3);y=np.array(b.bounding_box()).reshape(2,3);return bool(np.any(x[1]<y[0])or np.any(y[1]<x[0]))
def check(a,b):
 if separated(a,b):return {'volumeMm3':0,'method':'bounds-separated'}
 c=a^b;assert c.status()==mf.Error.NoError;v=max(0,c.volume());return {'volumeMm3':v,'method':'valid-solid-intersection','intersectionBoundsMm':list(c.bounding_box())if v>1e-6 else None}
cfg=read(D/'candidate.json');moving={}
moving['head_coupled_receiving']=mf.Manifold.cube([20,47.9,12]).translate([-11,-24,137])
base=read(W/'original-body-converter/fusion-import-manifest.json');parts={q['key']:q for q in base['parts']};G=read(R/'leg-guide-20261006/full-build-data.json');trans={p['key']:p.get('sourceTransformWorld')for p in G['parts']};nm=read(W/'enclosed-wiring-repair/ankle-wires/native-motors/manifest.json');motorref=[q for q in nm['parts']if q['motor']==2]
retired={'power_support','regulator_insert','regulator','openrb','openrb_usb_receiving','curved_cap_hardware','head_cap','shell_left','shell_right','amplifier','speaker_cradle','imu_clamp','imu_cover','imu_board','camera_ribbon_200'}
retired.update(k for k in parts if k=='pi' or k.startswith(('zero_w_','gpio_pin_','component_','E-pi-')))
obstacles=[]
for k,p in parts.items():
 if k in retired:continue
 obstacles.append({'key':k,'file':p['file'],'translation':p.get('importTranslationMm',[0,0,0]),'motor':int(k[5:])if k.startswith('motor')and k[5:].isdigit()else None})
for k,p in [('head_cap',HD/'audio-relocation/positive-y13-native/closed-cap-Pi-audio-positive-y13-world.stl'),('amplifier',HD/'audio-relocation/amplifier-positive-y13-world.stl'),('speaker_cradle',HD/'audio-relocation/native/speaker-cradle-single-seat-adjustment.stl'),('new_carrier',C/'power-support-controller-concept-world.stl')]:obstacles.append({'key':k,'file':str(p)})
obstacles.append({'key':'community-original-cap','file':str(R/'head-redesign-20261008/curved-head/community-curved-head-world.stl')})
for side in ['left','right']:obstacles.append({'key':'original_shell_'+side+'_conservative_uncut','file':parts['shell_'+side]['file']})
refs=read(HD/'audio-relocation/native-mount-spec.json')
for q in refs['references']:
 if q['name'].startswith('REFERENCE Pi current '):obstacles.append({'key':q['name'],'file':q['file'],'transform':q.get('worldTransform')})
imu=read(D.parent/'imu-local-manifest.json')
for q in imu['parts']:
 obstacles.append({'key':q['key'],'file':str(Path(q['file']).with_suffix('.stl')),'transform':q.get('sourceToWorld')})
for q in read(C/'native-carrier.json')['pigtails']:obstacles.append({'key':q['net'],'file':q['stl']})
plug=read(HD/'body-partition/native-usb-passage/passage-spec.json')
for q in plug['plugReferences']:obstacles.append({'key':q['key'],'file':q['file'],'translation':q['worldTranslationMm']})
checks=[];missing=[]
for p in obstacles:
 if p.get('motor'):
  obs=[(p['key']+'/'+str(q['solid']),transform(load(q['file']),np.array(trans[p['key']])@np.linalg.inv(q['worldTransform'])))for q in motorref]
 else:
  if not Path(p['file']).exists():missing.append(p);continue
  raw=trimesh.load_mesh(p['file']);hashes[p['file']]=sha(p['file'])
  if p.get('transform'):raw.apply_transform(p['transform'])
  if p.get('translation'):raw.apply_translation(p['translation'])
  rb=raw.bounds
  if all(np.any(np.array(a.bounding_box()).reshape(2,3)[1]<rb[0]) or np.any(rb[1]<np.array(a.bounding_box()).reshape(2,3)[0]) for a in moving.values()):
   checks.extend({'moving':k,'fixed':p['key'],'volumeMm3':0,'method':'all-raw-vertices-bounds-separated-no-boolean-needed'} for k in moving);continue
  del raw
  b=load(p['file'])
  if p.get('transform'):b=transform(b,p['transform'])
  if p.get('translation'):b=b.translate(p['translation'])
  obs=[(p['key'],b)]
 for n,b in obs:
  for k,a in moving.items():checks.append({'moving':k,'fixed':n,**check(a,b)})
 for n,b in obs:del b
selfrows=[]
for i,(k,a)in enumerate(moving.items()):
 for n,b in list(moving.items())[i+1:]:selfrows.append({'a':k,'b':n,**check(a,b)})
out={'status':'FINITE_MANUAL_USB_INTERFACE_CHECK','passedStatic':not missing and not any(q['volumeMm3']>1e-6 for q in checks+selfrows),'checks':checks,'crossPartChecks':selfrows,'missing':missing,'retiredSources':sorted(retired),'sourceHashes':hashes|{str(Path(__file__)):sha(__file__)},'conservativeComponentSources':conservative,'bodyShellScope':'Original uncut shell solid is a conservative superset of proposed cut-only U-notch. A zero against it is sufficient; any hit requires localization against the actual notch and is not automatically a modified-shell collision.', 'wholeHarnessAccepted':False,'SC0727FlexibleLengthVerified':False,'requiredScope':'Current named rigid body/head neighbors, current Pi and controller carrier, local IMU and J4/DFR receivers; final changing FFC/audio flexible routes and articulation remain separate.'}
(D/'head-coupler-check.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'passed':out['passedStatic'],'missing':missing,'hits':[q for q in checks+selfrows if q['volumeMm3']>1e-6]},indent=2))
