import argparse,json,gc
from pathlib import Path
import bounded_amp_check as c
import precision_mesh as pm
from amp16_aabb_precheck import bounds,compare
D=Path(__file__).resolve().parent;H=D.parent;O=D/'speaker-rewire';p=argparse.ArgumentParser();p.add_argument('--wire',type=int,required=True);a=p.parse_args();mf=H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json';m=json.loads(mf.read_text());assert m['allSourceTrianglesCoveredExactlyOnce'] and m['componentCount']==len(m['components'])==142;assert sum(r['sourceTriangleCount'] for r in m['components'])==m['sourceTriangleCount']==317300;assert c.sha(m['sourceFile'])==m['sourceSha256'];f=O/f'speaker-wire-{a.wire}-world.stl';bb=bounds(f);c.guarded_import();target=pm.load(c,f);rows=[]
for r in m['components']:
 assert c.sha(r['mesh'])==r['meshSha256'];assert r.get('maximumHalfspaceViolationMm',0)<1e-10
 overlap=compare(bb,r['bounds'])['aabbOverlap'];v=0
 if overlap:
  obs=pm.load(c,Path(r['mesh']));v=max(0,float((target^obs).volume()));del obs;gc.collect()
 rows.append({'component':r['index'],'aabbDisjoint':not overlap,'volumeMm3':v})
report={'wire':a.wire,'passed':all(r['volumeMm3']<=1e-4 for r in rows),'rows':rows,'checkedComponents':len(rows),'allSourceTrianglesCoveredExactlyOnce':True,'sourceTriangleCount':317300,'inputHashes':c.fingerprint([Path(__file__),mf,m['sourceFile'],f]),'integrationReady':False,'scope':'Clear of all component convex enclosures proves clearance from every source triangle; cannot infer positive acceptance from a nonzero enclosure overlap.'};c.atomic_json(O/f'openrb-components-wire{a.wire}.json',report);print(json.dumps({'wire':a.wire,'passed':report['passed'],'components':len(rows),'exact':sum(not r['aabbDisjoint'] for r in rows),'failed':[r for r in rows if r['volumeMm3']>1e-4]}));raise SystemExit(0 if report['passed'] else 2)
