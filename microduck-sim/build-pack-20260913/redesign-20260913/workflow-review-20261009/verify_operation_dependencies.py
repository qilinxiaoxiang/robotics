#!/usr/bin/env python3
"""Check process-order contracts only; never upgrades connector clearance evidence."""
from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent;R=D.parent;P=D/'operation-dependencies.json'
def validate(sequence,gates):
 errors=[]
 if len(sequence)!=len(set(sequence)): errors.append('Duplicate operation')
 pos={k:i for i,k in enumerate(sequence)}
 for g in gates:
  a,b=g['id'],g['beforeOperation']
  if a not in pos:errors.append('Missing cable gate: '+a)
  elif b not in pos:errors.append('Missing closure: '+b)
  elif pos[a]>=pos[b]:errors.append('Premature closure: '+b+' before '+a)
 return errors

def run():
 data=json.loads(P.read_text());full=json.loads((R/'leg-guide-20261006/full-build-data.json').read_text());parts={p['key'] for p in full['parts']};mods={m['id']:m for m in full['modules']}; errors=[];rows=[]
 for name,expected in data['sourceHashes'].items():
  if hashlib.sha256((R/name).read_bytes()).hexdigest()!=expected:errors.append('Stale source: '+name)
 for m in data['modules']:
  actual=mods[m['id']]['operations'];actualids=[o['id'] for o in actual]
  assert actualids==m['currentOperationIds']
  assert len(actualids)==20
  assert len(m['gates'])==8
  assert not m['currentCableGates']
  assert all(not g['closureBlockingProven'] and g['evidenceLevel']=='process' for g in m['gates'])
  for g in m['gates']:
   assert set(g['motorKeys']+g['closureCandidatePartKeys'])<=parts
  good=validate(m['reviewSequence'],m['gates']);errors.extend(good)
  current=validate(actualids,m['gates']);assert len(current)==8
  # Every motor must be covered BEFORE the source operation first adds it.
  for motor in m['motorKeys'].values():
   first=next(o['id'] for o in actual if motor in o.get('add',[]))
   assert any(motor in g['motorKeys'] and actualids.index(g['beforeOperation'])<=actualids.index(first) for g in m['gates']),motor
  negatives=[]
  for g in m['gates']:
   bad=m['reviewSequence'].copy();bad.remove(g['id']);bad.insert(bad.index(g['beforeOperation'])+1,g['id'])
   found=validate(bad,m['gates']);assert found==['Premature closure: '+g['beforeOperation']+' before '+g['id']],found
   negatives.append(g['id'])
  rows.append({'module':m['id'],'currentGuideMissingGates':len(current),'proposedSequencePassed':not good,'prematureClosureNegativeControlsRejected':len(negatives),'allFiveMotorFirstEnclosuresCovered':True})
 assert data['physicalInsertionVerified'] is False and data['integrationReady'] is False
 report={'passed':not errors,'scope':'Source-bound process-order check only. Not installed socket registration, insertion geometry, physical recovery or electrical architecture acceptance.','errors':errors,'modules':rows,'dependencySha256':hashlib.sha256(P.read_bytes()).hexdigest(),'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'physicalInsertionVerified':False,'integrationReady':False}
 (D/'operation-dependency-verification.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(run())
