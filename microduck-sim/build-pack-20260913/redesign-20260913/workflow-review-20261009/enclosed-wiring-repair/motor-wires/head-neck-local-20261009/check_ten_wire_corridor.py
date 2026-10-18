from check_local import *
plan=json.loads((D/'plan.json').read_text());rows=[];probes=[]
cs=[('motor-data-1',12,1.5),('motor-data-2',13.8,1.5),('motor-data-3',15.6,1.5),('head-5V',17.9,2.5),('head-GND',20.7,2.5),('head-DATA',23,1.5),('IMU-1',24.45,.8),('IMU-2',25.55,.8),('IMU-3',26.65,.8),('IMU-4',27.75,.8)]
for key,x,d in cs:
 m=trimesh.creation.cylinder(radius=(d/2+.003)/np.cos(np.pi/32),height=33,sections=32);m.apply_translation([x,12,116.5]);f=D/(key+'-neck-corridor.stl');m.export(f);probes.append(({'key':key,'diameterMm':d,'centerXY':[x,12],'endpointsMm':[[x,12,100],[x,12,133]],'file':str(f),'sha256':sha(f)},m,solid(m)))
for o in plan['obstacles']:
 m=load(o);near=[p for p in probes if overlap(p[1].bounds,m.bounds)]
 if not near:continue
 assert m.is_volume,o['key'];b=solid(m)
 for p,_,a in near:
  c=a^b;v=c.volume();rows.append({'wire':p['key'],'obstacle':o['key'],'volumeMm3':v,'boundsMm':list(c.bounding_box())if v>1e-7 else None})
fails=[r for r in rows if r['volumeMm3']>1e-7];result={'passed':not fails,'scope':'Ten parallel local receiving cylinders only, Z100..133. Not complete routes, connectors, bending or articulated motion. Lower exit must route around neck_pitch and upper exit around audio/controller.','parts':[p for p,_,_ in probes],'exactPairs':rows,'aabbSeparatedPairs':len(probes)*len(plan['obstacles'])-len(rows),'sourceHashes':{str(D/'plan.json'):sha(D/'plan.json'),str(Path(__file__)):sha(__file__)},'failures':fails};(D/'ten-wire-corridor.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':not fails,'failures':fails,'exactPairs':len(rows)}))
