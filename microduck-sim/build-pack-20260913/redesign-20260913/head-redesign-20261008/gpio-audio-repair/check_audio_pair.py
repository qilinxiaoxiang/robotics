import argparse,json
from pathlib import Path
import bounded_amp_check as c
import precision_mesh as pm
p=argparse.ArgumentParser();p.add_argument('--a',required=True);p.add_argument('--b',required=True);p.add_argument('--out',required=True);args=p.parse_args();c.guarded_import();a=pm.load(c,Path(args.a));b=pm.load(c,Path(args.b));inter=a^b;v=max(0,float(inter.volume()));r={'passed':v<=1e-4,'overlapMm3':v,'bounds':list(inter.bounding_box()) if v>1e-4 else None,'minimumGapMm':a.min_gap(b,2) if v<=1e-4 else 0,'inputHashes':c.fingerprint([Path(__file__),args.a,args.b]),'integrationReady':False};c.atomic_json(Path(args.out),r);print(json.dumps({k:v for k,v in r.items() if k!='inputHashes'}));raise SystemExit(0 if r['passed'] else 2)
