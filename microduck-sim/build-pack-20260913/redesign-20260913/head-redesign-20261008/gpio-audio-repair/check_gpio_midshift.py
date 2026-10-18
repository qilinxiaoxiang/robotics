import json,gc
from pathlib import Path
import bounded_amp_check as c
import check_speaker_rewire as s
import precision_mesh as pm
D=Path(__file__).resolve().parent;O=D/'gpio-fanout';c.guarded_import();plan=json.loads((D/'speaker-rewire/scene-plan.json').read_text());obs=s.solid(plan['rows']['motor15']);rows=[];files=[]
for dx in [1.75]:
 for pin,direction in [(35,'negativeY'),(40,'positiveY')]:
  f=O/f'pin-{pin}-{direction}-R3-world.stl';files.append(f);t=pm.load(c,f).translate([dx,0,0]);v=max(0,float((t^obs).volume()));row={'pin':pin,'direction':direction,'piDeltaX':dx,'overlapMotor15Mm3':v,'passed':v<=1e-4,'minimumGapMm':t.min_gap(obs,2.0)};rows.append(row);pm.export(c,t,O/f'pin-{pin}-R3-shiftX{dx}-world.stl');del t;gc.collect()
r={'rows':rows,'inputHashes':c.fingerprint([Path(__file__),O/'motor15-R3-bends.json',plan['rows']['motor15']['dataFile']]+files),'integrationReady':False,'scope':'Only motor15; Pi shift is an independent placement candidate, not adoption.'};c.atomic_json(O/'shift175-R3-bends.json',r);print(json.dumps(rows))
