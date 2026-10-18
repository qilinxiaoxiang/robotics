from pathlib import Path
import json,hashlib,re,numpy as np,trimesh,manifold3d as mf
D=Path(__file__).resolve().parent;W=D.parents[2];R=W.parent;O=W/'roof-wiring-stage/motor-wires/obstacles';G=R/'leg-guide-20261006/full-build-data.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
inputs=set()
def load(p):
 inputs.add(str(Path(p).resolve()))
 m=trimesh.load_mesh(p);assert m.is_volume,p;s=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert s.status()==mf.Error.NoError;return s

def cyl(a,b,r):
 t=trimesh.geometry.align_vectors([0,0,1],np.array(b)-a);t[:3,3]=(np.array(a)+b)/2;m=trimesh.creation.cylinder(r,np.linalg.norm(np.array(b)-a),sections=48).apply_transform(t);return mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices),np.ascontiguousarray(m.faces,dtype=np.uint64)))
def sep(a,b):
 aa=np.array(a.bounding_box()).reshape(2,3);bb=np.array(b.bounding_box()).reshape(2,3);return np.any(aa[1]<bb[0])or np.any(bb[1]<aa[0])
def vol(a,b):
 if sep(a,b):return 0
 c=a^b;assert c.status()==mf.Error.NoError;return max(0,c.volume())
data=json.loads(G.read_text());P={p['key']:p for p in data['parts']};cfg=json.loads((D/'native-carrier.json').read_text());car=load(D/'power-support-controller-concept-world.stl');old=load(Path(json.loads((O/'power_support.json').read_text())['file']));delta_added=car-old;board=mf.Manifold.cube([30,26,8]).translate([-40,-13,-50]);reg=json.loads((W/'enclosed-wiring-repair/head-layout/native-fusion-repair-inputs.json').read_text());T=np.array(cfg['openrbNativeToWorld']);delta=T@np.linalg.inv(reg['openrb']['nativeToCurrentWorld']);ep=R/'head-redesign-20261008/usb-access/usb-repair/openrb-component-enclosures/manifest.json';er=json.loads(ep.read_text())['components'];electronics=[]
for q in er:
 assert sha(q['mesh'])==q['meshSha256'];electronics.append(('OpenRB-'+str(q['index']),load(q['mesh']).transform(delta[:3])))
# Retained controller hardware travels with the populated carrier, too.
for y in [-10.25,10.25]:
 for z in [-31.75,29.75]:
  a=np.array([-27.9,y,z]);v=np.array([1,0,0]);electronics.append(('OpenRB-M2x6-'+str(y)+'-'+str(z),cyl(a-v*6,a,1)+cyl(a,a+v*1.5,2.5)))
leads=[(q['net'],load(q['stl']))for q in cfg['pigtails']];j4=[q for q in leads if not q[0].startswith('DFR')];dfrleads=[q for q in leads if q[0].startswith('DFR')]
rows=[]
# OpenRB screws installed on the detached carrier, before robot neighbours exist.
for y in [-10.25,10.25]:
 for z in [-31.75,29.75]:
  tool=cyl([-25.9,y,z],[14.1,y,z],1.5);checks=[]
  for key,b in [('carrier',car),('DFR',board)]+electronics+leads:checks.append({'key':key,'volumeMm3':vol(tool,b)})
  rows.append({'phase':'bench-OpenRB-M2x6-driver','hole':[-29.5,y,z],'shaftDiameterMm':3,'shaftLengthMm':40,'checks':checks,'passed':all(c['volumeMm3']<1e-6 for c in checks)})
# Original body fasteners with the converter board loose, not retained in the tray.
bodyids=['S10-case-069','S10-case-072','S05-case-074','S05-case-076'];screws={s['id']:s for s in data['screws']};bodytools=[]
for sid in bodyids:
 s=screws[sid];a=np.array(s['world_center_mm']);v=np.array(s['world_axis']);tool=cyl(a+v*.5,a+v*40,1.5)
 checks=[{'key':k,'volumeMm3':vol(tool,b)}for k,b in [('new-carrier-delta',delta_added)]+electronics+j4]
 bodytools.append({'screw':sid,'checks':checks,'passed':all(c['volumeMm3']<1e-6 for c in checks),'prematureDFRInstalledNegativeMm3':vol(tool,board)})
# DFR with its three pre-soldered local leads enters the open +X end0.8mm low,
# then settles upward0.8 onto the1.1mm liner receiving allowance. No forced flex.
move=[('DFR',board)]+dfrleads;fixed=[('carrier',car)]+electronics+j4
stages=[('slide-prewired-DFR-low',[np.array([x,0,-.8])for x in np.linspace(45,0,181)]),('seat-prewired-DFR',[np.array([0,0,z])for z in np.linspace(-.8,0,9)])]
insert=[]
for label,offsets in stages:
 checks=[]
 for k,a in move:
  for n,b in fixed:
   peak=0;hits=[]
   for j,v in enumerate(offsets):
    x=vol(a.translate(v),b);peak=max(peak,x)
    if x>1e-6:hits.append({'sample':j,'offsetMm':v.tolist(),'volumeMm3':x})
   checks.append({'moving':k,'fixed':n,'samples':len(offsets),'peakMm3':peak,'hits':hits})
 insert.append({'phase':label,'checks':checks,'passed':all(c['peakMm3']<1e-6 for c in checks)})
# Complete original leg units are present, but shells/neck are not yet installed.
fixedkeys={'torso_base','ring10_torso','ring5_torso'}
for mod in data['modules']:
 if mod['id']in['left-leg','right-leg']:fixedkeys.update(mod['ownedPartKeys'])
legacy=R/'leg-guide-20261006/non-head-review/torso-service-verification.json'
legacy_data=json.loads(legacy.read_text());assert legacy_data['passed'] and legacy_data['sourceDataSha256']==sha(G)
oldpath=next(q for q in legacy_data['paths']if q['operation']=='torso-service-27')
assert fixedkeys=={k for k in oldpath['fixed']if not k.startswith('screw:')}
fixedkeys.update(k for k in oldpath['fixed']if k.startswith('screw:'))
inputs.add(str(legacy))
nm=json.loads((D.parents[1]/'ankle-wires/native-motors/manifest.json').read_text());source_motors=[q for q in nm['parts']if q['motor']==2]
def source(k):
 if k.startswith('screw:'):
  s=screws[k[6:]];v=np.array(s['world_axis']);a=np.array(s['world_center_mm'])+v*s.get('washer_mm',0);diam=float(re.search(r'M([0-9.]+)',s['spec'])[1]);yield k,cyl(a-v*s['length_mm'],a,diam/2)+cyl(a,a+v*1.5,2.5)
 elif k.startswith('motor')and k[5:].isdigit():
  for q in source_motors:yield k+'/'+str(q['solid']),load(q['file']).transform((np.array(P[k]['sourceTransformWorld'])@np.linalg.inv(q['worldTransform']))[:3])
 else:
  inputs.add(str(O/(k+'.json')));ob=json.loads((O/(k+'.json')).read_text());assert sha(ob['file'])==ob['sha256'];yield k,load(ob['file']).translate(ob.get('importTranslationMm',[0,0,0]))
moving=[('new-carrier-delta',delta_added)]+electronics+j4;path=[];offsets=[np.array([x,0,0])for x in np.linspace(-28,0,113)]
for key in sorted(fixedkeys):
 for n,b in source(key):
  for k,a in moving:
   aa=np.array(a.bounding_box()).reshape(2,3);aa[0,0]-=28;bb=np.array(b.bounding_box()).reshape(2,3)
   if np.any(aa[1]<bb[0])or np.any(bb[1]<aa[0]):path.append({'moving':k,'fixed':n,'samples':113,'method':'whole-path-bounds','peakMm3':0});continue
   peak=0;hits=[]
   for j,v in enumerate(offsets):
    x=vol(a.translate(v),b);peak=max(peak,x)
    if x>1e-6:hits.append({'sample':j,'offsetMm':v.tolist(),'volumeMm3':x})
   path.append({'moving':k,'fixed':n,'samples':113,'method':'exact-sampled','peakMm3':peak,'hits':hits})
# Repeat only the DFR assembly change against the now-present original leg/body station.
dfr_body=[]
for key in sorted(fixedkeys|{'screw:'+sid for sid in bodyids}):
 for n,b in source(key):
  for label,offsets in stages:
   for k,a in move:
    aa=np.array(a.bounding_box()).reshape(2,3);alloffset=np.array(offsets);aa[0]+=alloffset.min(axis=0);aa[1]+=alloffset.max(axis=0);bb=np.array(b.bounding_box()).reshape(2,3)
    if np.any(aa[1]<bb[0])or np.any(bb[1]<aa[0]):dfr_body.append({'phase':label,'moving':k,'fixed':n,'samples':len(offsets),'method':'whole-path-bounds','peakMm3':0});continue
    peak=0;hits=[]
    for index,v in enumerate(offsets):
     value=vol(a.translate(v),b);peak=max(peak,value)
     if value>1e-6:hits.append({'sample':index,'offsetMm':v.tolist(),'volumeMm3':value})
    dfr_body.append({'phase':label,'moving':k,'fixed':n,'samples':len(offsets),'peakMm3':peak,'hits':hits})
# Two narrow insulating strips are added after the board is seated; their free
# ends pass between the three solder pad leads. Holding the loose board for this
# step is intentional; no rigid 1.1mm liner is falsely present in the low slide.
liner=[]
for y in [-7,7]:
 strip=mf.Manifold.cube([26,2,1.0]).translate([-39,y-1,-51.05]);checks=[]
 for name,b in [('carrier',car),('DFR',board)]+electronics+leads:
  peak=0
  for x in np.linspace(45,0,181):peak=max(peak,vol(strip.translate([x,0,0]),b))
  checks.append({'fixed':name,'samples':181,'peakMm3':peak})
 for key in sorted(fixedkeys|{'screw:'+sid for sid in bodyids}):
  for name,b in source(key):
   peak=0
   for x in np.linspace(45,0,181):peak=max(peak,vol(strip.translate([x,0,0]),b))
   checks.append({'fixed':name,'samples':181,'peakMm3':peak})
 liner.append({'finalBoundsMm':[[-39,y-1,-51.05],[-13,y+1,-50.05]],'material':'Insulating strip receiving allowance; thickness1.0mm, cut26x2mm','approachMm':[45,0,0],'checks':checks,'passed':all(q['peakMm3']<1e-6 for q in checks)})
tie_passages=[]
for x in [-34,-16]:
 for sign in [-1,1]:
  lo=[x-2.4,min(sign*22,sign*13.6),-46.6];hi=[x+2.4,max(sign*22,sign*13.6),-45.4];strip=mf.Manifold.cube(np.array(hi)-lo).translate(lo)
  checks=[{'key':k,'volumeMm3':vol(strip,b)}for k,b in [('carrier',car),('DFR',board)]+electronics+leads]
  tie_passages.append({'slot':[x,sign*14.8,-46],'receivingWidthThicknessMm':[4.8,1.2],'checks':checks,'passed':all(c['volumeMm3']<1e-6 for c in checks)})
out={'insulatingStripInsertion':liner,'DFRAfterBodyInsertion':{'checks':dfr_body,'passed':all(c['peakMm3']<1e-6 for c in dfr_body)},'tieEndThreadingPassages':tie_passages,'scope':'Local assembly at original torso service station: completed legs/base/rings present, side shells/neck absent. Reuses original power_support material/path; checks all added material/electronics/short J4 receivers. DFR and its pre-soldered leads are deliberately loose until four body screws close. Not whole flexible wiring or physical strength acceptance.','sourceHashes':{str(p):sha(p)for p in [G,D/'native-output-readback.json',D/'power-support-controller-concept-world.stl',D/'native-carrier.json',ep,Path(__file__)]},'controllerBenchTools':rows,'originalBodyToolDelta':bodytools,'DFRBenchInsertion':insert,'populatedCarrierApproach':{'vectorMm':[-28,0,0],'fixedPartKeys':sorted(fixedkeys),'movingPartKeys':[k for k,s in moving],'checks':path,'passed':all(x['peakMm3']<1e-6 for x in path)},'passed':all(r['passed']for r in rows+bodytools+insert+tie_passages+liner)and all(x['peakMm3']<1e-6 for x in path+dfr_body)}
# Compare explicit expected inventories with completed pair keys; missing work cannot pass.
fixednames=[]
for key in sorted(fixedkeys):
 fixednames.extend([key+'/'+str(q['solid'])for q in source_motors] if key.startswith('motor')and key[5:].isdigit() else [key])
expected_path={(k,n)for k,a in moving for n in fixednames}
expected_dfr={(label,k,n)for label,offsets in stages for k,a in move for n in fixednames+['screw:'+sid for sid in bodyids]}
actual_path={(q['moving'],q['fixed'])for q in path}
actual_dfr={(q['phase'],q['moving'],q['fixed'])for q in dfr_body}
assert expected_path==actual_path and len(path)==len(expected_path)
assert expected_dfr==actual_dfr and len(dfr_body)==len(expected_dfr)
assert len(rows)==4 and all(len(q['checks'])==153 for q in rows)
assert len(bodytools)==4 and all(len(q['checks'])==149 for q in bodytools)
assert len(insert)==2 and all(len(q['checks'])==596 for q in insert)
assert len(tie_passages)==4 and all(len(q['checks'])==153 for q in tie_passages)
assert set(oldpath['fixed'])==fixedkeys and oldpath['path']['start']==[-28,0,0] and oldpath['path']['stop']==[0,0,0] and not oldpath['path']['peakContactsMm3']
assert legacy_data['sourceDataSha256']==sha(G)
out['inheritedOriginalMaterialPath']={'file':str(legacy),'sha256':sha(legacy),'row':'torso-service-27','unchangedFixedKeys':True,'meaning':'Retained source material is a subset of the previously checked support; all newly added material and populated controller checked separately here.'}
out['coverage']={'expectedFixedBodies':fixednames,'expectedCarrierPairs':len(expected_path),'completedCarrierPairs':len(path),'expectedDFRBodyPairs':len(expected_dfr),'completedDFRBodyPairs':len(dfr_body),'controllerToolPairs':4*153,'originalToolDeltaPairs':4*149,'DFRBenchStagePairs':2*596,'tiePassagePairs':4*153,'complete':True}
inputs.update(str(p)for p in [legacy,O/'power_support.json',D.parents[1]/'ankle-wires/native-motors/manifest.json',W/'enclosed-wiring-repair/head-layout/native-fusion-repair-inputs.json'])
out['sourceHashes'].update({p:sha(p)for p in sorted(inputs)})
assert len(liner)==2 and all(len(q['checks'])==153+len(fixednames)+4 for q in liner)
out['coverage']['linerStripPairs']=sum(len(q['checks'])for q in liner)
out['complete']=out['coverage']['complete']
f=D/'local-assembly-check.json';f.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'passed':out['passed'],'controllerToolsPassed':all(r['passed']for r in rows),'bodyToolPrematureDFR':[{'screw':r['screw'],'volumeMm3':r['prematureDFRInstalledNegativeMm3']}for r in bodytools],'carrierHits':[x for x in path if x['peakMm3']>1e-6],'DFRBodyHits':[{k:v for k,v in x.items()if k!='hits'} for x in dfr_body if x['peakMm3']>1e-6],'tiePassed':all(r['passed']for r in tie_passages)},indent=2))
