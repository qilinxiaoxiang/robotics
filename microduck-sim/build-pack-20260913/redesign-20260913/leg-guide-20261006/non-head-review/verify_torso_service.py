"""Gate the exact optional finished-leg service payload, with retained hardware."""
from pathlib import Path
import json,hashlib,numpy as np,trimesh,manifold3d as mf,re
D=Path(__file__).resolve().parent;G=D.parent;p=G.parent/'head-redesign-20261008/head-fit-investigation.py';n={'__file__':str(p)};exec(p.read_text().split("report={'problemIds'")[0],n)
source=n['raw'];data=n['data'];solid=n['solid'];sample=n['samples'];payload=json.loads((D/'torso-service-steps.json').read_text());ss={s['id']:s for s in data['screws']};installed={s['id'] for s in data['screws'] if s['moduleId'] in ['left-leg','right-leg']};errors=[];paths=[];toolrows=[];accepted=[]
def cyl(a,b,r):
 a=np.array(a);b=np.array(b);T=trimesh.geometry.align_vectors([0,0,1],b-a);T[:3,3]=(a+b)/2;return n['man'](trimesh.creation.cylinder(radius=r,height=np.linalg.norm(b-a),sections=48).apply_transform(T))
def bolt(sid):
 s=ss[sid];v=np.array(s['world_axis']);a=np.array(s['world_center_mm'])+v*s.get('washer_mm',0);diam=float(re.search(r'M([0-9.]+)',s['spec'])[1]);return cyl(a-v*s['length_mm'],a,diam/2)+cyl(a,a+v*1.5,2.5)
hardware={sid:bolt(sid) for sid in installed|{s['id'] for s in data['screws'] if s['moduleId']=='torso'}}
contracts={('motor9','yaw'):(2,[-8.00101,-7.99999],.00102,.341,None),('motor4','right_yaw'):(2,[-8.00101,-7.99999],.00102,.341,None),('yaw','ring10_torso'):(2,[-5.000001,-4.99899],.00101,.0563,.00101),('right_yaw','ring5_torso'):(2,[-5.000001,-4.99899],.00101,.0563,.00101),('motor10','torso_base'):(2,[-.00000001,.00000017],.00000018,.00002,.000001),('motor5','torso_base'):(2,[-.00000001,.00000017],.00000018,.00002,.000001)}
for op in payload['module']['operations']:
 visible=set(op['isolatedPartKeys']);assert visible==set(op['visiblePartKeys']);moving=set(op.get('moveKeys',[]));moving_hw=set(op.get('movingScrewIds',[]));sids=op['screwIds']
 # Tools retain other installed screw envelopes and all declared physical parts.
 for sid in sids:
  s=ss[sid];v=np.array(s['world_axis']);a=np.array(s['world_center_mm'])+v*s.get('washer_mm',0);tool=cyl(a+v*.5,a+v*40,1.5);obs={k:solid(k) for k in visible};obs.update({'screw:'+q:hardware[q] for q in installed if q!=sid and ss[q].get('partKey') in visible})
  hits={k:float((tool^q).volume()) for k,q in obs.items() if (tool^q).volume()>.0001};row={'operation':op['id'],'screw':sid,'action':op.get('screwAction'),'contactsMm3':hits};toolrows.append(row)
  if hits:errors.append({'tool':row})
  if op.get('screwAction')=='remove':installed.discard(sid)
  else:installed.add(sid)
 if not moving:continue
 assert moving_hw<=installed,(op['id'],moving_hw-installed)
 m={k:solid(k) for k in moving};m.update({'screw:'+sid:hardware[sid] for sid in moving_hw});fixed={k:solid(k) for k in visible-moving};fixed.update({'screw:'+sid:hardware[sid] for sid in installed-moving_hw if ss[sid].get('partKey') in visible-moving})
 a,b=op['motionWaypoints']['points'];r=sample(m,fixed,a,b,step=.25)
 for entry in r['samples']:
  for pair,vol in entry['contactsMm3'].items():
   x,y=pair.split('--');contract=contracts.get((x,y));ok=False;detail=None
   if contract:
    axis,slab,depth,cap,terminal=contract;it=m[x].translate(entry['translation'])^fixed[y];bb=list(it.bounding_box());ok=vol<=cap and bb[axis]>=slab[0] and bb[axis+3]<=slab[1] and bb[axis+3]-bb[axis]<=depth and (terminal is None or np.linalg.norm(entry['translation'])<=terminal)
    detail={'pair':pair,'volumeMm3':vol,'translation':entry['translation'],'boundsMm':bb,'allowed':bool(ok)}
   if ok:accepted.append({'operation':op['id'],**detail})
   else:errors.append({'operation':op['id'],'pair':pair,'volumeMm3':vol,'translation':entry['translation']})
 paths.append({'operation':op['id'],'moving':sorted(m),'fixed':sorted(fixed),'path':r})
# Finer samples isolate the new torso-ring source contact to the final 1.01 um.
refined=[]
for x,y in [('yaw','ring10_torso'),('right_yaw','ring5_torso')]:
 c=contracts[(x,y)]
 for z in np.linspace(-.003,0,31):
  it=solid(x).translate([0,0,z])^solid(y);vol=float(it.volume())
  if vol<=1e-7:continue
  bb=list(it.bounding_box());ok=vol<=c[3] and bb[2]>=c[1][0] and bb[5]<=c[1][1] and bb[5]-bb[2]<=c[2] and abs(z)<=c[4]
  refined.append({'pair':[x,y],'zOffsetMm':float(z),'volumeMm3':vol,'boundsMm':bb,'allowed':bool(ok)})
  if not ok:errors.append({'refinedRingContact':refined[-1]})
removed=[sid for o in payload['module']['operations'] if o.get('screwAction')=='remove' for sid in o['screwIds']];reinstalled=[sid for o in payload['module']['operations'] if o.get('screwAction')=='refasten' for sid in o['screwIds']];assert len(removed)==14 and len(set(removed))==14 and set(removed)==set(reinstalled)
old=json.loads((D/'service-sequence-early-support-negative.json').read_text());negative=[t for t in old['tools'] if t['contactsMm3']];assert len(negative)==4
assert hashlib.sha256(source).hexdigest()==hashlib.sha256((G/'full-build-data.json').read_bytes()).hexdigest(),'Source data changed during run'
assert payload['sourceDataSha256']==hashlib.sha256(source).hexdigest(),'Payload must be regenerated against current source before verification'
content={k:v for k,v in payload.items() if k not in ['integrationReady','verificationSha256']}
content_hash=hashlib.sha256(json.dumps(content,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
input_hashes={name:hashlib.sha256((D/name).read_bytes()).hexdigest() for name in ['build_service_steps.py','service-sequence-early-support-negative.json']}
r={'problemIds':['P5','P6'],'passed':not errors,'errors':errors,'sourceDataSha256':hashlib.sha256(source).hexdigest(),'payloadContentSha256':content_hash,'payloadContentNormalization':"json.dumps(payload excluding only integrationReady and verificationSha256, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')",'inputHashes':input_hashes,'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'paths':paths,'tools':toolrows,'acceptedSpecificContacts':accepted,'terminalRingRefinement':refined,'temporaryRemovedIds':removed,'removedPerLeg':7,'newHardware':0,'preservedAnkleFootAndOtherFourJointFasteners':True,'negativeEarlyPowerSupport':negative,'hardwareEnvelope':{'headDiameterMm':5,'headHeightMm':1.5,'shaftDiameterFromSpec':True,'lengthFromSource':True,'washerAxialOffsetFromSource':True,'scope':'Retained screws follow their whole moving group; 5 x 1.5 mm active-guide head envelope, not measured hardware certification.'},'toolEnvelope':{'shaftDiameterMm':3,'headOffsetMm':.5,'endDistanceMm':40,'origin':'source world_center_mm plus world_axis * washer_mm, matching viewer screw head position'},'physicalFitVerified':False,'scope':'Finished-leg service branch only; fresh-build uses the checked loose torso core before yaw closure, not a claim of complete new-build validation.'}
(D/'torso-service-verification.json').write_text(json.dumps(r,indent=2)+'\n');payload['integrationReady']=not errors;payload['sourceDataSha256']=r['sourceDataSha256'];payload['verificationSha256']=hashlib.sha256((D/'torso-service-verification.json').read_bytes()).hexdigest();(D/'torso-service-steps.json').write_text(json.dumps(payload,indent=2)+'\n');print(json.dumps({'passed':not errors,'toolPaths':len(toolrows),'partPaths':len(paths),'errors':errors},indent=2));raise SystemExit(bool(errors))
