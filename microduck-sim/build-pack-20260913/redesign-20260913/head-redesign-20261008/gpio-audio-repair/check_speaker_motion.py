"""Conservative continuous wire sweep and explicit prewire tool geometry."""
import argparse,json,gc
from pathlib import Path
import bounded_amp_check as c
import precision_mesh as pm
import check_speaker_rewire as s
D=Path(__file__).resolve().parent;O=D/'speaker-rewire';P=D/'speaker-rewire-amp16z2p0-proposal.json'
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['build','pair','tools'],required=True);p.add_argument('--direction',choices=['insertion','closure'],default='insertion');p.add_argument('--wire',type=int,default=0);p.add_argument('--key',default='head_cap');a=p.parse_args();c.guarded_import();r=json.loads(P.read_text());route=r['routes'][a.wire];file=O/f'wire-{a.wire}-{a.direction}-continuous-receiving-world.stl';plan=json.loads((O/'scene-plan.json').read_text())
if a.phase=='build':
 pieces=[];dz=[-40,0] if a.direction=='insertion' else [0,40]
 for p,q in zip(route['centerlineMm'],route['centerlineMm'][1:]):
  lo=[min(p[k],q[k])-.76 for k in range(3)];hi=[max(p[k],q[k])+.76 for k in range(3)];lo[2]+=dz[0];hi[2]+=dz[1]
  pieces.append(c.mf.Manifold.cube([hi[k]-lo[k] for k in range(3)]).translate(lo))
 sw=c.mf.Manifold.batch_boolean(pieces,c.mf.OpType.Add);out=pm.export(c,sw,file);out.update(inputHashes=c.fingerprint([P,Path(__file__)]),meshSha256=c.sha(file),scope='Continuous Z40 translation enclosed by per-.25mm centerline chord boxes; r=.76 includes .75 wire radius plus<.003 chord sag. Conservative boxes may produce false collisions, never a true-path clearance claim from a failed box.',integrationReady=False);c.atomic_json(file.with_suffix('.json'),out);print(json.dumps({'built':str(file),'watertight':out['watertight']}))
elif a.phase=='pair':
 target=pm.load(c,file);row=plan['rows'][a.key];ob=s.solid(row);inter=target^ob;v=max(0,float(inter.volume()));out={'wire':a.wire,'direction':a.direction,'obstacle':a.key,'conservativeSweepOverlapMm3':v,'bounds':list(inter.bounding_box()) if v>1e-4 else None,'passed':v<=1e-4,'inputHashes':c.fingerprint([file,Path(__file__),O/'scene-plan.json',row['path'] if row.get('path') else row['dataFile']]),'integrationReady':False};c.atomic_json(O/f'motion-{a.direction}-{a.wire}-{a.key}.json',out);print(json.dumps(out));raise SystemExit(0 if out['passed'] else 2)
else:
 rows=[]
 # Actual staging: loose amp and prewired speaker/wires, all enclosure parts absent.
 idx={'amplifier':plan['rows']['amplifier'],'speaker':plan['rows']['speaker']}
 for i,t in enumerate(r['terminalTools']):
  xyz=t['receivingTopWorldMm'];shaft=c.mf.Manifold.cylinder(45,1.5,circular_segments=24).translate(xyz);handle=c.mf.Manifold.cylinder(60,9,circular_segments=32).translate([xyz[0],xyz[1],xyz[2]+45]);tool=shaft+handle
  for key,row in idx.items():
   v=max(0,float((tool^s.solid(row)).volume()));rows.append({'pin':t['terminalPin'],'key':key,'overlapMm3':v})
  for j in [0,1]:
   v=max(0,float((tool^pm.load(c,O/f'speaker-wire-{j}-world.stl')).volume()));rows.append({'pin':t['terminalPin'],'key':'speaker_wire_'+str(j),'overlapMm3':v})
  pm.export(c,tool,O/f'terminal-driver-{i}-world.stl')
 out={'passed':all(x['overlapMm3']<=1e-4 for x in rows),'rows':rows,'toolReceivingMm':{'shaft':[3,45],'handle':[18,60],'handleStartsAboveTerminalTop':45},'inputHashes':c.fingerprint([P,Path(__file__),O/'scene-plan.json']),'integrationReady':False,'boundary':'Bench loose-amplifier state only. Not access through installed roof; source does not dimension terminal screw recess below top.'};c.atomic_json(O/'prewire-terminal-tools.json',out);print(json.dumps(out))
