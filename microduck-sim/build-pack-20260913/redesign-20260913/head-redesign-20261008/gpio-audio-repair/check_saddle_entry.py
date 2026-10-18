"""Bound continuous prewired entry by sample distance and translation Lipschitz bound."""
import argparse,json
from pathlib import Path
import bounded_amp_check as c
import precision_mesh as pm
D=Path(__file__).resolve().parent;O=D/'speaker-rewire';p=argparse.ArgumentParser();p.add_argument('--wire',type=int,choices=[0,1],required=True);a=p.parse_args();c.guarded_import()
wf=O/f'speaker-wire-{a.wire}-world.stl';sf=O/'speaker-pair-roof-saddle-world.stl';w=pm.load(c,wf);s=pm.load(c,sf);step=.1;rows=[];out=O/f'saddle-entry-wire{a.wire}.json';r={'integrationReady':False,'passed':False,'inputHashes':c.fingerprint([Path(__file__),wf,sf]),'translationWorldMm':[[0,0,-40],[0,0,0]],'sampleStepMm':step,'bound':'Distance is 1-Lipschitz under translation. Each continuous pose lies within 0.05 mm of one sampled pose; min sample gap >0.05 proves positive separation over the whole motion. This tests the conservative circumscribed wire mesh.','rows':rows}
for i in range(401):
 offset=-40+i*step;m=w.translate([0,0,offset]);v=max(0,float((m^s).volume()));gap=float(m.min_gap(s,2));rows.append({'offsetMm':offset,'overlapMm3':v,'gapMm':gap});c.atomic_json(out,r)
 if v>1e-5 or gap<=step/2:break
r['minimumSampleGapMm']=min(x['gapMm'] for x in rows);r['continuousGapLowerBoundMm']=r['minimumSampleGapMm']-step/2;r['passed']=len(rows)==401 and r['continuousGapLowerBoundMm']>0;c.atomic_json(out,r);print(json.dumps({k:v for k,v in r.items() if k not in ['rows','inputHashes']}));raise SystemExit(0 if r['passed'] else 2)
