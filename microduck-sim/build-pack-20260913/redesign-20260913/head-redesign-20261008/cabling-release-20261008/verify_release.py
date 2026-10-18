from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent;H=D.parent;B=H.parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
r=json.loads((D/'CABLING-RELEASE-REVIEW.json').read_text());a=json.loads((D/'audio-route-candidate.json').read_text());v=json.loads((D/'audio-candidate-verification.json').read_text());f=json.loads((D/'viewer-fragment.json').read_text())
checks=[]
def ck(name,condition):
 checks.append({'name':name,'passed':bool(condition)})
 if not condition:raise AssertionError(name)
for p,h in r['sourceHashes'].items():ck('source '+p,sha(B/p)==h)
for p,h in r['ownedEvidenceHashes'].items():ck('owned '+p,sha(D/p)==h)
for p,h in v['sourceHashes'].items():ck('fresh route source '+p,sha(H.parent/p)==h)
ck('fragment report binding',f['reportSha256']==sha(D/'CABLING-RELEASE-REVIEW.json'))
ck('full wiring connection inventory',len(r['connections'])==51 and len({x['id'] for x in r['connections']})==51)
ck('clear full cap closure',len(v['closure']['rows'])==161 and not v['closure']['peakIntersectionsMm3'])
ck('clear bare amp insertion',len(v['ampBenchInsertion'])==121 and not any(x['hits'] for x in v['ampBenchInsertion']))
ck('both drivers',len(v['ampDrivers'])==2 and not any(x['hits'] for x in v['ampDrivers']))
ck('speaker wires clear',not any(x['intersectionsMm3'] for x in a['speakerWires']))
ck('wire separation',a['wirePairIntersectionMm3']==0 and v['wirePairGapMm']>.45)
ck('cap and keeper topology',a['keeperWatertight'] and a['keeperBodies']==1 and v['capReadbackWatertight'] and a['capComponents']==1)
ck('no manufacturing acceptance',r['manufacturingAcceptance'] is False and r['allCableRoutesVerified'] is False and f['integrationReady'] is False)
ck('no forbidden substitute FFC',next(x for x in r['connections'] if x['id']=='camera-ribbon')['geometryStatus']=='BLOCKED_SOURCE_WIDTH_AND_END_STIFFENER_ROUTE')
gpio=json.loads((D/'gpio-candidate.json').read_text());loop=json.loads((D/'neck-loop-family.json').read_text());slot=json.loads((D/'neck-slot-closure.json').read_text())
ck('four complete static I2S lines',len(gpio['rows'])==4 and not any(x['intersectionsMm3'] for x in gpio['rows']) and not gpio['wirePairIntersectionsMm3'])
ck('neck finite negative preserved',loop['samples']==229 and loop['accepted'] is False and loop['collisionSamples']==34 and loop['lengthUnavailableSamples']==7)
ck('slot exact closure correction',slot['closedPortalNegativeControl']['collisionPoseCount']==58 and slot['lowerEdgeSlotCorrection']['sampleCount']==161 and not slot['lowerEdgeSlotCorrection']['remainingCollisionPoses'])
ck('4397 evidence and remaining facts',r['received4397ManufacturerEvidence']['wireODmm']==.8 and r['received4397ManufacturerEvidence']['flexibleLengthBetweenPlasticShouldersMm']==150 and len(r['exactPhysicalFactsToResolve'])==2)
print(json.dumps({'passed':True,'checks':len(checks),'reportSha256':sha(D/'CABLING-RELEASE-REVIEW.json'),'fragmentSha256':sha(D/'viewer-fragment.json')},indent=2))
