"""One exact obstacle; source binding and local solder-pad shoulder allowance only."""
import argparse,json
from pathlib import Path
import bounded_amp_check as c
import precision_mesh as pm
from check_speaker_rewire import solid
D=Path(__file__).resolve().parent;O=D/'gpio-fanout/x225/actual4397';P=O/'complete-scene-plan.json';p=argparse.ArgumentParser();p.add_argument('--pin',type=int,required=True);p.add_argument('--key',required=True);a=p.parse_args();plan=json.loads(P.read_text());row=plan['rows'][a.key];wf=O/f'i2s-pin{a.pin}-world.stl';of=Path(row.get('path') or row['dataFile']);assert c.sha(wf)==plan['wireHashes'][str(a.pin)];assert c.sha(of)==row['sourceSha256'];c.guarded_import();w=pm.load(c,wf);ob=solid(row);inter=w^ob;v=max(0,float(inter.volume()));contact=None;outside=v
if a.key=='amplifier':
 route=next(r for r in json.loads((O.parent/'i2s-route-proposal.json').read_text())['routes'] if r['pin']==a.pin);q=route['ampPadMm'];allow=c.mf.Manifold.cube([1.6,1.6,.00004],True).translate([q[0],q[1],q[2]+.00001]);outside=max(0,float((inter-allow).volume()));contact={'kind':'PCB STL pad-plane rounding','allowedXYHalfMm':.8,'allowedZIntervalMm':[q[2]-.00001,q[2]+.00003],'rawContactMm3':v,'outsideAllowedMm3':outside};assert v<.0001 or outside>1e-8
passed=outside<1e-8;gap=w.min_gap(ob,2) if passed and v<1e-8 else None;r={'pin':a.pin,'key':a.key,'passedNoPenetration':passed,'minimumGapSearchCap2Mm':gap,'preferredHalfMmMargin':gap is not None and gap>=.5,'contact':contact,'overlapMm3':v,'outsideInterfaceMm3':outside,'boundsMm':list(inter.bounding_box()) if v>1e-8 else None,'planSha256':c.sha(P),'inputHashes':c.fingerprint([Path(__file__),wf,of]),'integrationReady':False};out=O/'complete-pairs';out.mkdir(exist_ok=True);c.atomic_json(out/f'{a.pin}-{a.key}.json',r);print(json.dumps({k:v for k,v in r.items() if k not in ['inputHashes','contact']}));raise SystemExit(0 if passed else 2)
