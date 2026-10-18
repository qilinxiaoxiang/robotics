"""Prewired rigid member entry into detached cap. Explicit sampled limits."""
import argparse,json,gc
from pathlib import Path
import bounded_amp_check as c
import check_speaker_rewire as s
import precision_mesh as pm
D=Path(__file__).resolve().parent;O=D/'speaker-rewire';A=D/'cap-amp16z2';p=argparse.ArgumentParser();p.add_argument('--key',choices=['speaker','amplifier','terminal-tool-negative'],required=True);a=p.parse_args();c.guarded_import();plan=json.loads((O/'scene-plan.json').read_text());capfile=A/'cap-current-audio-usb-world.stl';cap=pm.load(c,capfile);out=O/f'prewire-entry-{a.key}.json';rows=[]
if a.key=='terminal-tool-negative':
 for i in [0,1]:
  f=O/f'terminal-driver-{i}-world.stl';inter=pm.load(c,f)^cap;v=max(0,float(inter.volume()));rows.append({'tool':i,'overlapMm3':v,'boundsMm':list(inter.bounding_box()) if v>1e-5 else None})
 r={'passed':all(q['overlapMm3']>1 for q in rows),'meaning':'Negative control: these same terminal drivers collide with the fitted roof. Wire-terminal tightening must happen on the loose amplifier before mounting it in the cap.','rows':rows,'inputHashes':c.fingerprint([Path(__file__),capfile,*[O/f'terminal-driver-{i}-world.stl' for i in [0,1]]]),'integrationReady':False}
else:
 row=plan['rows'][a.key];part=s.solid(row);r={'passed':False,'integrationReady':False,'key':a.key,'benchState':'Cap detached, keeper and audio fasteners absent. Speaker+amplifier+two connected wires maintain their final relative pose on an external support while being translated up into cap. This test is one rigid member; combined group is accepted only after every member and support practicality checks.','translationWorldMm':[[0,0,-40],[0,0,0]],'sampleStepMm':.25,'rows':rows,'inputHashes':c.fingerprint([Path(__file__),capfile,O/'scene-plan.json',row.get('path') or row['dataFile']]),'continuousScope':'Sampled rigid entry only; zero sampled overlap is not continuous swept certification.'}
 for i in range(161):
  z=-40+i*.25;moved=part.translate([0,0,z]);inter=moved^cap;v=max(0,float(inter.volume()));gap=float(moved.min_gap(cap,2)) if v<1e-5 else 0;rows.append({'offsetZmm':z,'overlapMm3':v,'gapMm':gap,'boundsMm':list(inter.bounding_box()) if v>1e-5 else None});c.atomic_json(out,r)
  if v>1e-4 and not (a.key=='amplifier' and i==160):break
  del moved,inter;gc.collect()
 r['passed']=len(rows)==161 and all(x['overlapMm3']<1e-4 for x in rows);r['minimumSampleGapMm']=min(x['gapMm'] for x in rows)
 if a.key=='amplifier' and len(rows)==161 and rows[-1]['overlapMm3']>1e-4:
  contact=part^cap;posts=pm.load(c,A/'amp-new-post-0-world.stl')+pm.load(c,A/'amp-new-post-1-world.stl');outside=max(0,float((contact-posts).volume()));zmin=135.5849994;slab=c.mf.Manifold.cube([20,30,.00002]).translate([35,-40,zmin-.00001]);offslab=max(0,float((contact-slab).volume()));r['finalNominalContact']={'totalMm3':rows[-1]['overlapMm3'],'outsideTwoPostsMm3':outside,'outsideTwentyNanometreSeatSlabMm3':offslab,'seatZmm':zmin,'reason':'Original amplifier STL has float32 top face at135.585006714 while nominal post seat135.5849994; 7.314nm roundtrip surface offset. Contact limited to exactly these two seats at final endpoint.'};r['inputHashes'].update(c.fingerprint([A/'amp-new-post-0-world.stl',A/'amp-new-post-1-world.stl']));r['passed']=all(x['overlapMm3']<1e-4 for x in rows[:-1]) and outside<1e-8 and offslab<1e-8 and rows[-1]['overlapMm3']<.0002
 if r['minimumSampleGapMm']>.125:r['continuousGapLowerBoundMm']=r['minimumSampleGapMm']-.125;r['continuousScope']='All continuous translations certified by1-Lipschitz distance bound with.25mm pose spacing.'
c.atomic_json(out,r);print(json.dumps({k:v for k,v in r.items() if k not in ['rows','inputHashes']}));print(json.dumps([q for q in rows if q.get('overlapMm3',0)>1e-4]));raise SystemExit(0 if r['passed'] else 2)
