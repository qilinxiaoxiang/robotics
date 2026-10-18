from check_routes import *
r=json.loads(read(D/'audio-route-candidate.json'));names={'speaker_keeper':'speaker-keeper-wire-relief-candidate-world.stl','head_cap':'cap-audio-rotation-candidate-world.stl','amplifier':'amplifier-audio-rotation-candidate-world.stl','curved_cap_hardware':'hardware-audio-rotation-candidate-world.stl'}
for k,f in names.items():obs[k]=man(load(D/f))
for i in [0,1]:obs[f'speaker_wire_{i}']=man(load(D/f'speaker-wire-{i}-candidate-world.stl'))
movingKeys=['head_cap','amplifier','curved_cap_hardware','openrb','speaker','speaker_cradle','speaker_keeper','speaker_wire_0','speaker_wire_1'];absent={p['key'] for p in config['additionalParts'] if p.get('plugEnvelope')};fixed={k:s for k,s in obs.items() if k not in movingKeys and k not in absent};rows=[];peak={}
for z in np.arange(40,-.001,-.25):
 hh={}
 for k in movingKeys:
  q=obs[k].translate([0,0,z])
  for n,s in fixed.items():
   v=hits(q,s)
   if v>1e-5:hh[k+'--'+n]=v;peak[k+'--'+n]=max(peak.get(k+'--'+n,0),v)
 rows.append({'offsetZmm':float(z),'hits':hh})
# Amp arrives under empty cap before speaker; solder and terminal screws are
# tightened before the populated amp enters the cap, so no phantom late tool access.
bench={'head_cap':obs['head_cap'],'openrb':obs['openrb']};motion=[]
for z in np.arange(30,-.001,-.25):
 hh={n:hits(obs['amplifier'].translate([0,0,-z]),s) for n,s in bench.items()};hh={n:v for n,v in hh.items() if v>1e-5};motion.append({'offsetDownMm':float(z),'hits':hh})
tools=[]
for p in r['newAmpHoleBottomMm']:
 center=np.array(p)-[0,0,1.57];tool=mf.Manifold.cylinder(45,1.5,circular_segments=48).translate(center-[0,0,46.7]);hh={n:hits(tool,s) for n,s in bench.items()};tools.append({'centerMm':center.tolist(),'hits':{n:v for n,v in hh.items() if v>1e-5}})
# A tiny source floating-point contact is not silently accepted; give exact slab.
contact=obs['head_cap']^obs['amplifier'];bb=np.array(contact.bounding_box()).reshape(2,3)
out={'closure':{'samples':len(rows),'stepMm':.25,'movingKeys':movingKeys,'fixedKeys':list(fixed),'absentAfterClosureUsb':list(absent),'peakIntersectionsMm3':peak,'rows':rows},'ampBenchInsertion':motion,'ampDrivers':tools,'ampSeatContact':{'volumeMm3':contact.volume(),'boundsMm':bb.tolist(),'zThicknessMm':float(bb[1,2]-bb[0,2]),'accepted':float(contact.volume())<2e-5 and float(bb[1,2]-bb[0,2])<2e-6},'wirePairGapMm':obs['speaker_wire_0'].min_gap(obs['speaker_wire_1'],5),'capReadbackWatertight':load(D/names['head_cap']).is_watertight,'sourceHashes':hashes,'physicalVerified':False}
(D/'audio-candidate-verification.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ['sourceHashes','ampBenchInsertion','closure']},indent=2));print('CLOSURE',peak,'BENCH',[(x['offsetDownMm'],x['hits']) for x in motion if x['hits']])
