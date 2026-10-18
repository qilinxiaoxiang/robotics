from scene import *
SIM=H.parent.parents[1];FK=SIM/'hardware-design-20260912/whole-robot-20260912/assembly/assembly_fk.py'
sys.path.insert(0,str(FK.parent));from assembly_fk import fk
B,_=fk();inv={k:np.linalg.inv(v) for k,v in B.items()};bodymap={p['key']:p.get('body','jaw_soft') for p in data['parts']}
for k in obs:bodymap.setdefault(k,'jaw_soft')
bodymap={k:b if b in B else 'trunk_base' for k,b in bodymap.items()}
source=H/'usb-access/usb-repair/rigid-domain.json';cases=json.loads(read(source))['samples']
obs['amplifier']=man(load(D/'amplifier-terminal-receiving-world.stl'))
for i in [0,1]:obs[f'speaker_wire_{i}']=man(load(D/f'speaker-wire-{i}-world.stl'))
keys=['head_cap','amplifier','speaker','speaker_cradle','speaker_keeper','speaker_wire_0','speaker_wire_1','curved_cap_hardware']
rows=[];peak={}
for index,row in enumerate(cases):
 poses,_=fk({k:np.deg2rad(v) for k,v in row['jointDegrees'].items()});Th=poses['jaw_soft']@inv['jaw_soft'];hh={}
 for k,o in obs.items():
  b=bodymap[k]
  if b=='jaw_soft':continue
  relative=np.linalg.inv(Th)@poses[b]@inv[b];other=o.transform(relative[:3])
  for name in keys:
   v=hits(obs[name],other)
   if v>1e-4:hh[name+'--'+k]=v;peak[name+'--'+k]=max(peak.get(name+'--'+k,0),v)
 rows.append({'jointDegrees':row['jointDegrees'],'hits':hh})
 if index%50==0:print(index,len(cases),flush=True)
out={'sourceHashes':hashes,'samples':rows,'testedParts':keys,'sampleCount':len(rows),'failedSamples':sum(bool(r['hits']) for r in rows),'peakHitsMm3':peak,'scope':'Full source joint-domain sampled relative-body collision; no runtime range change or blanket baseline waiver.'}
(D/'audio-domain.json').write_text(json.dumps(out,indent=2)+'\n');print(peak,flush=True)
