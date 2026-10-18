"""Release the source-bound revision only after both real geometry gates pass."""
from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent;R=D.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads((D/p).read_text())
a=read('fastener-choice-report.json');b=read('fastener-context-report.json');p=read('fastener-patch-proposal.json')
assert a['passed'] and b['passed'] and not a['errors'] and not b['errors']
assert a['sourceDataSha256']==b['sourceDataSha256']==p['sourceDataSha256']==sha(R/'leg-guide-20261006/full-build-data.json')
for r in [a,b]:
 for f,h in r['sourceHashes'].items():
  if Path(f).resolve()!=Path(__file__).resolve():assert sha(f)==h,('stale input',f)
 # This metadata-only finalizer may evolve; geometry verifier/mesh/source hashes stay exact.
assert len(p['replacements'])==12 and len(p['guideOnlyReplacements'])==2 and len(p['geometryCandidates'])==3
for k,v in p['geometryCandidates'].items():
 for filefield,hashfield in [('worldMesh','worldMeshSha256'),('sourceFrameMesh','sourceFrameMeshSha256')]:assert sha(D/v[filefield])==v[hashfield]
p['sourceHashes']={**a['sourceHashes'],**b['sourceHashes'],str(Path(__file__).resolve()):sha(__file__)}
p['contextReportFile']='fastener-context-report.json';p['contextReportSha256']=sha(D/p['contextReportFile'])
original=json.loads((R/'leg-guide-20261006/full-build-data.json').read_text());screws={s['id']:s for s in original['screws']}
for r in p['replacements']:
 s=screws[r['id']];r.update(oldSpec=s['spec'],oldLengthMm=s['length_mm'],newLengthMm=6,newStackMm=[x+1 for x in s['stack_mm']],newPenetrationMm=r['entryMm'],newWasherMm=0,effectiveCondition='Use only with the matching revised part carrying integral 1.0 mm head seats; do not apply M2x6 to the original flat seats.')
for r in p['guideOnlyReplacements']:
 s=screws[r['id']];r.update(oldSpec=s['spec'],oldLengthMm=s['length_mm'],newStackMm={'pilot_thickness':4.0,'head_standoff_at_contact':1.8},newEngagementMm=4.0,newWasherMm=0,effectiveCondition='Pressure screw: stop when the tip bears on the rail; leave the head 1.8 mm above the holder. Do not tighten the head flush.')
for r in p['replacements']:
 if r['module'] in ['left-leg','right-leg']:
  r['currentAssembledAction']='User confirmed M2x6 already installed. Original2.8mm knee seats imply3.2mm nominal entry versus manufacturer3mm maximum; actual damage is unknown. Integral-seat lower links are validated for NEW BUILD only. Do not dismantle completed ankle/foot interfaces on this basis; their preservation during lower-link replacement is not validated.'
  r['installedUserConfirmedLengthMm']=6
p['threadFormRule']='Use ROBOTIS/compatible M2 tapping screws. M2 machine screws are not accepted as interchangeable.'
p['adoptionBoundary']='Neck replacement and IMU instruction are current fixes. Integral-seat lower/right_lower and M2x6 are validated NEW BUILD geometry. User confirmed existing knee screws are6mm. Preserve completed legs; replacing their lower links would reopen captured ankle interfaces, and a preservation sequence is not validated. Small-OD washer repair remains separate conditional review and is not adopted by this revision.'
repair=read('knee-washer-repair.json')
assert repair['passed'] and not repair['errors'] and repair['sourceDataSha256']==p['sourceDataSha256']
for f,h in repair['sourceHashes'].items():assert sha(f)==h,('stale washer evidence',f)
by_repair={r['id']:r for r in repair['rows']}
for row in a['washerAlternative']:
 row['acceptanceStatus']='Not accepted for release; original screening excluded the printed host, so empty original contacts do not establish fit.'
 if row['id'] in by_repair:
  checked=next(x for x in by_repair[row['id']]['washerAlternatives'] if x['insideDiameterMm']==2.7 and x['outsideDiameterMm']==5)
  assert checked['contacts']
  row['hostInclusiveContactsMm3']=checked['contacts'];row['acceptanceStatus']='REJECTED: OD5 washer intersects original recessed lower-link seat. Original empty contacts omitted this host and are superseded.'
a['washerAlternativeSupersededBy']={'file':'knee-washer-repair.json','sha256':sha(D/'knee-washer-repair.json'),'mainGuideWasherAdoption':False}
p['sourceHashes'][str((D/'knee-washer-repair.json').resolve())]=sha(D/'knee-washer-repair.json')
a['sourceHashes']=p['sourceHashes'];a['contextReportFile']=p['contextReportFile'];a['contextReportSha256']=p['contextReportSha256'];a['contextPassed']=b['passed'];a['contextCounts']={'torsoPaths':len(b['torsoServiceFullGeometry']['partPaths']),'torsoTools':len(b['torsoServiceFullGeometry']['driverPaths']),'curvedHeadChecks':len(b['curvedHeadFinalContext'])}
a['proposalContentNormalization']="UTF-8 json.dumps(proposal excluding only integrationReady and reportSha256, sort_keys=True, separators=(',', ':'), ensure_ascii=True)"
a['proposalContentSha256']=hashlib.sha256(json.dumps({k:v for k,v in p.items() if k not in ['integrationReady','reportSha256']},sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
(D/'fastener-choice-report.json').write_text(json.dumps(a,indent=2)+'\n');p['reportSha256']=sha(D/'fastener-choice-report.json');p['integrationReady']=True;(D/'fastener-patch-proposal.json').write_text(json.dumps(p,indent=2)+'\n')
assert p['reportSha256']==sha(D/p['reportFile'])
assert a['proposalContentSha256']==hashlib.sha256(json.dumps({k:v for k,v in p.items() if k not in ['integrationReady','reportSha256']},sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
print(json.dumps({'integrationReady':True,'passed':a['passed'],'source':p['sourceDataSha256'],'servoReplacements':12,'guideOnlyReplacements':2,'meshCandidates':3,'contextCounts':a['contextCounts'],'contentHash':a['proposalContentSha256']},indent=2))
