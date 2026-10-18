from pathlib import Path
import json,numpy as np,trimesh,manifold3d as mf,hashlib
D=Path(__file__).resolve().parent;p=D.parent.parent/'head-redesign-20261008/head-fit-investigation.py';n={'__file__':str(p)};exec(p.read_text().split("report={'problemIds'")[0],n);d=n['data'];s=n['solid'];sample=n['samples'];sc={x['id']:x for x in d['screws']};rows=[];tools=[]
def shaft(screw):
 a=np.array(screw['world_center_mm']);v=np.array(screw['world_axis']);lo=a+v*.5;hi=a+v*40;T=trimesh.geometry.align_vectors([0,0,1],hi-lo);T[:3,3]=(lo+hi)/2;return n['man'](trimesh.creation.cylinder(radius=1.5,height=np.linalg.norm(hi-lo),sections=48).apply_transform(T))
def run(name,m,f,start,stop=(0,0,0)):
 r=sample(m,f,start,stop,step=.25);rows.append({'name':name,'moving':list(m),'fixed':list(f),'path':r});print(name,r['peakContactsMm3'],flush=True)
def toolset(name,ids,obs):
 for sid in ids:
  q=shaft(sc[sid]);hits={k:float((q^v).volume()) for k,v in obs.items() if (q^v).volume()>.0001};tools.append({'phase':name,'screw':sid,'contactsMm3':hits});print('TOOL',name,sid,hits,flush=True)
for mod,roll,yaw,link in [(d['modules'][0],9,10,'yaw'),(d['modules'][1],4,5,'right_yaw')]:
 allparts={k:s(k) for k in mod['ownedPartKeys']};washer='washer'+str(roll);motor='motor'+str(yaw);caseids=[x['id'] for x in d['screws'] if x['id'].startswith(f'S{roll:02}-case-') and x['component']=='yaw2roll'];rearids=[x['id'] for x in d['screws'] if x['id'].startswith(f'S{roll:02}-rear_center-')];hornids=[x['id'] for x in d['screws'] if x['id'].startswith(f'S{yaw:02}-horn-')]
 toolset('remove-only-yaw-side-case-and-rear',caseids+rearids,allparts)
 run(mod['id']+'-washer-out',{washer:s(washer)},{k:v for k,v in allparts.items() if k!=washer},[0,0,0],[-12,0,0])
 group={k:v for k,v in allparts.items() if k not in [link,motor,washer]};run(mod['id']+'-four-joint-unit-out',group,{k:allparts[k] for k in [link,motor]},[0,0,0],[60,0,0])
 toolset('yaw-horn-with-four-joint-unit-on-other-bench',hornids,{k:allparts[k] for k in [link,motor]})
 run(mod['id']+'-yaw-motor-out',{motor:s(motor)},{link:s(link)},[0,0,0],[0,0,45])
base={'torso_base':s('torso_base')}
for k in ['ring10_torso','ring5_torso']:
 run('bench-'+k,{k:s(k)},base,[0,0,-28]);base[k]=s(k)
for k in ['motor10','motor5']:
 run('bench-'+k,{k:s(k)},base,[0,0,45]);base[k]=s(k)
# Power support is kept off until yaw-side case/rear screws are complete.
case_torso=[x['id'] for x in d['screws'] if x.get('servo_ids') and x['servo_ids'][0] in [5,10] and x['category']=='case' and x['component'] not in ['left_shell','right_shell']];toolset('stabilize-bare-torso-core',['S10-case-070','S05-case-073'],base)
for mod,roll,yaw,link in [(d['modules'][0],9,10,'yaw'),(d['modules'][1],4,5,'right_yaw')]:
 run('bench-'+link,{link:s(link)},base,[0,0,-45]);base[link]=s(link);hornids=[x['id'] for x in d['screws'] if x['id'].startswith(f'S{yaw:02}-horn-')];toolset('reattach-yaw-output-before-four-joint-leg',hornids,base)
 washer='washer'+str(roll);motor='motor'+str(yaw);group={k:s(k) for k in mod['ownedPartKeys'] if k not in [link,motor,washer]};run(mod['id']+'-whole-four-joint-unit-back',group,base,[60,0,0]);base.update(group)
 run(mod['id']+'-washer-back',{washer:s(washer)},base,[-12,0,0]);base[washer]=s(washer)
 ids=[x['id'] for x in d['screws'] if (x['id'].startswith(f'S{roll:02}-case-') and x['component']=='yaw2roll') or x['id'].startswith(f'S{roll:02}-rear_center-')];toolset('reattach-yaw-side-case-and-rear',ids,base)
run('power-support-after-leg-service',{'power_support':s('power_support')},base,[-28,0,0]);base['power_support']=s('power_support')
toolset('remaining-torso-core-screws',[x for x in case_torso if x not in ['S10-case-070','S05-case-073']],base)
r={'sourceSha256':hashlib.sha256((D.parent/'full-build-data.json').read_bytes()).hexdigest(),'rows':rows,'tools':tools,'physicalFitVerified':False};(D/'service-sequence-probe.json').write_text(json.dumps(r,indent=2)+'\n')
