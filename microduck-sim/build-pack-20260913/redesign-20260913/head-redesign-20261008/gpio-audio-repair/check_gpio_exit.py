"""All twelve4mm exit probes against one obstacle per guarded process."""
import argparse,json,gc
from pathlib import Path
import bounded_amp_check as c
import check_speaker_rewire as s
import precision_mesh as pm
from amp16_aabb_precheck import bounds,compare
D=Path(__file__).resolve().parent;O=D/'gpio-fanout';p=argparse.ArgumentParser();p.add_argument('--key',required=True);a=p.parse_args();plan=json.loads((D/'speaker-rewire/scene-plan.json').read_text());idx=plan['rows'];row=idx[a.key];ex=json.loads((O/'first4mm-plan.json').read_text());pending=[];results=[]
for r in ex['rows']:
 bb=bounds(Path(r['mesh']))
 if compare(bb,row['boundsMm'])['aabbOverlap']:pending.append(r)
 else:results.append({'pin':r['pin'],'aabbDisjoint':True,'volumeMm3':0})
c.guarded_import();obs=s.solid(row)
for r in pending:
 target=pm.load(c,Path(r['mesh']));intersection=target^obs;v=max(0,float(intersection.volume()));results.append({'pin':r['pin'],'volumeMm3':v,'bounds':list(intersection.bounding_box()) if v>1e-4 else None});del target,intersection;gc.collect()
out={'key':a.key,'rows':results,'passed':all(r['volumeMm3']<=1e-4 for r in results),'integrationReady':False,'scope':'Straight first4mm only; no full fanout or flex-radius acceptance','inputHashes':c.fingerprint([Path(__file__),O/'first4mm-plan.json',D/'speaker-rewire/scene-plan.json']+[r['mesh'] for r in ex['rows']]+[row['path'] if row.get('path') else row['dataFile']])};c.atomic_json(O/(a.key+'-first4mm.json'),out);print(json.dumps({'key':a.key,'passed':out['passed'],'failed':[r for r in results if r['volumeMm3']>1e-4]}));raise SystemExit(0 if out['passed'] else 2)
