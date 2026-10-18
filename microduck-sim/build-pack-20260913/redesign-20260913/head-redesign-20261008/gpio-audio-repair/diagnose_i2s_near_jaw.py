import json,argparse,math
from pathlib import Path
import bounded_amp_check as c
from check_speaker_rewire import tube,solid
D=Path(__file__).resolve().parent;P=D/'gpio-fanout/x225/i2s-route-proposal.json';p=argparse.ArgumentParser();p.add_argument('--pin',type=int,required=True);a=p.parse_args();c.guarded_import();route=next(r for r in json.loads(P.read_text())['routes'] if r['pin']==a.pin);points=route['centerlineMm'];ss=[0]
for x,y in zip(points,points[1:]):ss.append(ss[-1]+math.dist(x,y))
row=json.loads((D/'speaker-rewire/scene-plan.json').read_text())['rows']['jaw_support'];ob=solid(row);results=[]
for start in range(0,30,3):
 pts=[p for p,s in zip(points,ss) if start<=s<=start+3];m=tube(pts,.4);v=max(0,(m^ob).volume());results.append({'stations':[start,start+3],'gapAtMost3':m.min_gap(ob,3),'overlap':v,'start':pts[0],'end':pts[-1]})
out={'pin':a.pin,'results':results,'inputHashes':c.fingerprint([Path(__file__),P,Path(row.get('path') or row['dataFile'])])};c.atomic_json(D/f'gpio-fanout/x225/actual4397/near-jaw-{a.pin}.json',out);print(json.dumps(results))
