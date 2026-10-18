from scene import *
from itertools import product
SIM=H.parent.parents[1];FK=SIM/'hardware-design-20260912/whole-robot-20260912/assembly/assembly_fk.py';sys.path.insert(0,str(FK.parent));from assembly_fk import fk
B,_=fk();inv={k:np.linalg.inv(v) for k,v in B.items()};bodymap={p['key']:p.get('body','jaw_soft') for p in data['parts']}
cases=json.loads(read(H/'usb-access/usb-repair/rigid-domain.json'))['samples']
amp=man(load(D/'amplifier-terminal-receiving-world.stl'))
native=man(load(H/'curved-head/community-curved-head-world.stl'))
audio=json.loads(read(C/'audio-route-candidate.json'));holes=np.array(audio['newAmpHoleBottomMm'])
columns=mf.Manifold.batch_boolean([mf.Manifold.cylinder(30,2.01,circular_segments=48).translate(p) for p in holes],mf.OpType.Add)
cap=obs['head_cap']-(columns-native)
rows=[];found=[]
for delta in sorted(product([12,15,18,20],[0,-1,1],[0,1,2]),key=lambda x:sum(abs(a) for a in x)):
 s=amp.translate(delta);hh={}
 for k,o in obs.items():
  if k in ['amplifier','speaker_wire_0','speaker_wire_1','curved_cap_hardware']:continue
  if k=='head_cap':o=cap
  if(v:=hits(s,o))>1e-4:hh[k]=v
 if hh:rows.append({'deltaMm':delta,'staticHits':hh});continue
 print('STATICCLEAR',delta,flush=True)
 dyn={}
 for row in cases:
  q=row['jointDegrees'];poses,_=fk({k:np.deg2rad(v) for k,v in q.items()});Th=poses['jaw_soft']@inv['jaw_soft']
  for k,o in obs.items():
   b=bodymap.get(k,'jaw_soft')
   if b=='jaw_soft' or b not in B:continue
   other=o.transform((np.linalg.inv(Th)@poses[b]@inv[b])[:3])
   if(v:=hits(s,other))>1e-4:dyn[k]=max(dyn.get(k,0),v)
 rows.append({'deltaMm':delta,'staticHits':{},'domainHits':dyn})
 if not dyn:found.append(delta);print('FOUND',delta,flush=True)
 if len(found)>=3:break
out={'rows':rows,'clearDeltasMm':found,'sourceHashes':hashes,'bodyDomainSamples':len(cases),'capWithoutOldAmpPostsFile':'cap-without-amp-posts-world.stl'}
tri(cap).export(D/'cap-without-amp-posts-world.stl');(D/'amp-pose-search.json').write_text(json.dumps(out,indent=2)+'\n');print('complete',len(rows),found,flush=True)
