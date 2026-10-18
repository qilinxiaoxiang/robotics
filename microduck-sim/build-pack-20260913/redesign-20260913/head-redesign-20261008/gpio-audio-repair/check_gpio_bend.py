"""Finite fanout-turn diagnostic. Does not reduce the18mm housing envelope."""
import argparse,json,math,gc
from pathlib import Path
import bounded_amp_check as c
import check_speaker_rewire as s
import precision_mesh as pm
D=Path(__file__).resolve().parent;O=D/'gpio-fanout';c.guarded_import();plan=json.loads((D/'speaker-rewire/scene-plan.json').read_text());obs=s.solid(plan['rows']['motor15']);ex=json.loads((O/'first4mm-plan.json').read_text());rows=[]
for r in ex['rows']:
 if r['pin'] not in [35,40]:continue
 u=c.np.array(r['direction']);start=c.np.array(r['startMm'])
 for name,v in [('negativeY',[0,-1,0]),('positiveY',[0,1,0]),('positiveZ',[0,0,1]),('negativeZ',[0,0,-1])]:
  v=c.np.array(v,dtype=float);v-=c.np.dot(v,u)*u;v/=c.np.linalg.norm(v);R=3
  points=[start+R*(math.sin(t)*u+(1-math.cos(t))*v) for t in c.np.linspace(0,math.pi/2,25)];points.append(points[-1]+4*v)
  target=s.tube(points,.75);inter=target^obs;vol=max(0,float(inter.volume()));row={'pin':r['pin'],'turn':name,'radiusMm':3,'initialStraightMm':0,'housingPcbToEndMm':18,'overlapMotor15Mm3':vol,'bounds':list(inter.bounding_box()) if vol>1e-4 else None};rows.append(row);pm.export(c,target,O/f'pin-{r["pin"]}-{name}-R3-world.stl');del target,inter;gc.collect()
r={'rows':rows,'passed':all(x['overlapMotor15Mm3']<=1e-4 for x in rows),'integrationReady':False,'scope':'Four principal R3 turns per affected pin; finite candidates, not impossibility of all routing. Tube diameter1.5 unchanged; bend immediately outside18mm receiver.','inputHashes':c.fingerprint([Path(__file__),O/'first4mm-plan.json',D/'speaker-rewire/scene-plan.json',plan['rows']['motor15']['dataFile']])};c.atomic_json(O/'motor15-R3-bends.json',r);print(json.dumps(rows))
