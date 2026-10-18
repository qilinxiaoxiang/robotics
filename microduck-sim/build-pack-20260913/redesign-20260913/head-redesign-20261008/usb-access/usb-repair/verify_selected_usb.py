"""Reconcile conservative broad-phase coverage and current-source exact receipts."""
from pathlib import Path
import argparse,hashlib,json
D=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--plan',type=Path,default=D/'current-obstacle-plan-v2.json')
parser.add_argument('--exact',type=Path,default=D/'selected-exact-checks')
parser.add_argument('--self-results',type=Path,default=D/'current-self-checks')
parser.add_argument('--output',type=Path,default=D/'selected-usb-summary.json')
a=parser.parse_args()
hashes={}
def bind(path):
 p=Path(path)
 with p.open('rb') as f:v=hashlib.file_digest(f,'sha256').hexdigest()
 hashes[str(p.resolve())]=v;return v
def read(path):bind(path);return json.loads(Path(path).read_text())
def current(r):
 for path,expected in r.get('sourceHashes',{}).items():assert bind(path)==expected,('Stale input',path)
p=read(a.plan);current(p)
if a.plan.resolve()==(D/'current-obstacle-plan-v2.json').resolve():
 old=read(D/'current-obstacle-plan.json');assert p['selected']==old['selected'] and p['obstacles']==old['obstacles'],'Broad phase changed; selected checks must be rerun'
proxy=read(D/'openrb-conservative-enclosure.json');assert bind(proxy['sourceFile'])==proxy['sourceSha256'];assert bind(proxy['proxyFile'])==proxy['proxySha256'];assert proxy['allSourceVerticesEnclosed'] and proxy['readback']['watertight']
allReports={}
for f in a.exact.glob('span*/*.json'):
 r=read(f);current(r);assert r['coverageComplete'] and r['solidValidityChecked']
 key=f"{r['spanMm']}:{r['checks'][0]['obstacle']}";assert key not in allReports,('Duplicate',key);allReports[key]=r
assert set(allReports)==set(p['selected'])
covered=0;clearHits=[];blockedHits=[];topology=[]
for key,rows in p['selected'].items():
 r=allReports[key];part=key.split(':',1)[1];fixed=p['obstacles'][part]['body']=='jaw_soft'
 if fixed:
  assert r['requestedPoseIndices'] is None and r['requestedDomainSlice'] is None
  assert len(r['checks'])==6
 else:assert set(r['requestedPoseIndices'])=={x['poseIndex'] for x in rows}
 lookup={(c['poseIndex'],c['moving']):c for c in r['checks']}
 for row in rows:
  for component in row['components']:
   c=lookup[(-1 if fixed else row['poseIndex'],component)];covered+=1
   if c['overlapMm3']>1e-5:
    hit={'spanMm':r['spanMm'],'part':part,'component':component,'poseIndex':row['poseIndex'],'overlapMm3':c['overlapMm3']}
    (blockedHits if row['nativeRigidBlocked'] else clearHits).append(hit)
 topology.extend(r.get('contactTopologyNormalizations',[]))
assert covered==p['potentialPairs']
for span in range(25,81,5):
 r=read(a.self_results/f'span-{span}-diagnostic/self.json');current(r);assert r['allClear'] and r['coverageComplete']
report={'status':'SAMPLED_USB_FAMILY_GEOMETRY_CHECKED','broadPhasePairs':p['expectedPairs'],'aabbSeparatedPairs':p['separatedPairs'],'selectedPairsCovered':covered,'selectedJobs':len(allReports),'nativeClearPoseCount':186,'nativeBlockedPoseCount':43,'nativeClearHits':clearHits,'nativeBlockedHits':blockedHits,'nativeClearSampledGeometryClear':not clearHits,'allJointSamplesClear':not clearHits and not blockedHits,'headFixedProof':'USB and jaw_soft obstacles share one rigid transform; their relative geometry is invariant across the229 samples.','openrbBoundary':'Uses a closed conservative enclosure of every source triangle, not an invalid-solid zero result. Positive proxy collision would be inconclusive. See openrb-conservative-enclosure.json.','contactTopologyNormalizations':topology,'assemblyAccepted':False,'physicalDimensionsVerified':False,'remaining':['Continuous spans between the12 explored lengths are not certified.','USB restraints, insertion with the entire harness and shell closure remain to verify.','Future Pi pose changes invalidate this geometry result until regenerated.','Joint samples do not certify all continuous joint motion or physical limits.'],'sourceHashes':hashes}
report['remaining'].append('Receiving-mesh checks require the independent round-cable clearance proof; mesh faceting is not a continuous round-cable proof.')
bind(__file__)
a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k in ['status','broadPhasePairs','selectedJobs','nativeClearSampledGeometryClear','allJointSamplesClear']}));print(json.dumps({'nativeClearHits':len(clearHits),'nativeBlockedHits':len(blockedHits)}))
