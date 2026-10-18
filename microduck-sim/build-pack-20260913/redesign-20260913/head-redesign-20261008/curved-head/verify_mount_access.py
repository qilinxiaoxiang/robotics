"""Detached-cap installation, side-nut loading, final screw heads and driver corridors."""
exec((__import__('pathlib').Path(__file__).parent/'finalize_cap.py').read_text().split('cap=load(')[0])
cap=load(D/'curved-cap-final-candidate-world.stl');layout=json.loads((D/'curved-layout.json').read_text());T=np.array(layout['transformsFromGuideWorld']['openrb']);axis=T[:3,:3]@np.array([0,0,1.]);A=trimesh.geometry.align_vectors([0,0,1],axis)[:3,:3]
def cyl(c,r,h,axis=np.array([0,0,1.]),n=48):
 m=trimesh.creation.cylinder(radius=r,height=h,sections=n);t=trimesh.geometry.align_vectors([0,0,1],axis);t[:3,3]=c;return man(m.apply_transform(t))
nuts={};heads={};tools={};stacks=[]
for screw in [s for s in data['screws'] if s['id'].startswith('E-openrb-')]:
 c=(T@np.r_[screw['world_center_mm'],1])[:3];n=cyl(c+axis*4.1,4/np.sqrt(3),1.6,axis,6)-cyl(c+axis*4.1,1.05,2,axis);nuts[screw['id']]=n;heads[screw['id']]=cyl(c-axis*.8,2,1.6,axis);tools[screw['id']]=cyl(c-axis*(1.6+22.5),1.5,45,axis);stacks.append({'id':screw['id'],'spec':'M2 x 6 machine + M2 nut','boardMm':1.6,'nutCenterFromBoardBottomMm':4.1,'nutHeightMm':1.6,'tipBeyondNutMm':1.1})
for row in json.loads((D/'audio-mounts.json').read_text())['posts']:
 x,y=row['xyMm'];base=128.44 if row['owner']=='speaker-cage' else row['startZmm']-1.57;k=row['owner']+'-'+str(len(heads));c=np.array([x,y,base]);heads[k]=cyl(c-[0,0,.85],2.5,1.7);tools[k]=cyl(c-[0,0,24.2],1.5,45);stacks.append({'id':k,'spec':'M2.5 x 8 tapping','stackMm':row['startZmm']-base,'engagementMm':8-(row['startZmm']-base),'postLengthMm':row['postLengthMm']})
rows=[];benchSnapshots={}
bench={'head_cap':cap}
# Nuts enter through explicit side windows before board installation.
for k,s in nuts.items():
 options=[]
 for sign in [-1,1]:
  peak={}
  for d in np.arange(15,-.0001,-.25):
   q=s.translate(A[:,0]*sign*d)
   for n,o in bench.items():
    v=hits(q,o)
    if v>1e-4:peak[n]=max(v,peak.get(n,0))
  options.append({'startOffsetMm':(A[:,0]*sign*15).tolist(),'endOffsetMm':[0,0,0],'peakIntersectionsMm3':peak})
 ok=next((p for p in options if not p['peakIntersectionsMm3']),None);rows.append({'operation':'load '+k,'alternatives':options,'accepted':ok is not None});bench['nut_'+k]=s
for k,f,v in [('openrb','openrb-curved-layout-world.stl',-axis*40),('amplifier','amplifier-curved-layout-world.stl',np.array([0,0,-40])),('speaker-keeper','speaker-keeper-world.stl',np.array([0,0,-40])),('speaker','speaker-curved-layout-world.stl',np.array([0,0,-40])),('speaker-cradle','speaker-cradle-world.stl',np.array([0,0,-40]))]:
 s=load(D/f);peak={}
 for a in np.linspace(1,0,161):
  q=s.translate(v*a)
  for n,o in bench.items():
   val=hits(q,o)
   if val>1e-4:peak[n]=max(val,peak.get(n,0))
 rows.append({'operation':'seat '+k,'startOffsetMm':v.tolist(),'endOffsetMm':[0,0,0],'samples':161,'peakIntersectionsMm3':peak,'accepted':not peak});bench[k]=s;benchSnapshots[k]=dict(bench)
# Shaft corridors on the detached shell, after each respective unit is seated.
toolrows=[]
late=[]
for k,t in tools.items():
 stage=benchSnapshots['openrb'] if k.startswith('E-openrb') else benchSnapshots['amplifier'] if k.startswith('amplifier') else bench
 latehits={n:hits(t,o) for n,o in bench.items() if hits(t,o)>1e-4}
 if latehits:late.append({'id':k,'intersectionsMm3':latehits})
 h={n:hits(t,o) for n,o in stage.items() if hits(t,o)>1e-4};toolrows.append({'id':k,'diameterMm':3,'lengthMm':45,'intersectionsMm3':h,'accepted':not h})
hardware=mf.Manifold.batch_boolean(list(heads.values())+list(nuts.values()),mf.OpType.Add);tri(hardware).export(D/'cap-eight-screw-heads-four-nuts-world.stl')
report={'benchSequence':rows,'toolCorridors':toolrows,'wrongLateFasteningNegativeControl':late,'fastenerStacks':stacks,'allBenchPathsClear':all(r['accepted'] for r in rows),'allToolsClear':all(r['accepted'] for r in toolrows),'scope':'Cap is detached. Source head/motor obstacles are included in subsequent full populated-cap closure, not fictitiously present on this independent bench. Threads intentionally engage printed pilots; proof is geometric, not torque/strength.','sourceHashes':{n:hashlib.sha256((D/n).read_bytes()).hexdigest() for n in ['curved-cap-final-candidate-world.stl','audio-mounts.json','openrb-curved-layout-world.stl']},'physicalFitVerified':False}
(D/'mount-access-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
