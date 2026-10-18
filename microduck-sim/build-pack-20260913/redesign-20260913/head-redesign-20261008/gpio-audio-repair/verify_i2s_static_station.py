"""Source-bound current station gate; excludes unopened service-path/FFC acceptance."""
import json,itertools,hashlib
from pathlib import Path
D=Path(__file__).resolve().parent;O=D/'gpio-fanout/x225/actual4397';P=O/'complete-scene-plan.json';plan=json.loads(P.read_text());inputs={};errors=[];gaps=[]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def receipt(p):
 inputs[str(p)]=sha(p);r=json.loads(p.read_text())
 for field in ['sourceHashes','inputHashes']:
  for f,h in r.get(field,{}).items():
   if sha(f)!=h:errors.append('Stale input '+str(f))
 return r
for f,h in plan['sourceHashes'].items():
 if sha(f)!=h:errors.append('Stale plan '+f)
for pin in [12,20,35,40]:
 if sha(O/f'i2s-pin{pin}-world.stl')!=plan['wireHashes'][str(pin)]:errors.append('Wire mismatch '+str(pin))
for key,r in plan['rows'].items():
 if sha(r.get('path') or r['dataFile'])!=r['sourceSha256']:errors.append('Obstacle mismatch '+key)
for p in plan['pairs']:
 if not p['exactNeeded']:continue
 pin,key=p['pin'],p['key'];r=receipt(O/'complete-pairs'/f'{pin}-{key}.json');assert r['planSha256']==sha(P)
 if key==f'gpio_pin_{pin:02d}_receiving':
  contact=receipt(O/f'exit-contact-{pin}.json')
  if not contact['passed']:errors.append('Connector exit contact '+str(pin))
 elif key=='amplifier':
  if not r['passedNoPenetration'] or r['contact']['outsideAllowedMm3']>1e-8:errors.append('Amp pad '+str(pin))
 else:
  if not r['passedNoPenetration'] or not r['preferredHalfMmMargin']:errors.append('Foreign obstacle '+str(pin)+' '+key)
  if r['minimumGapSearchCap2Mm'] is not None:gaps.append(r['minimumGapSearchCap2Mm'])
for a,b in itertools.combinations([12,20,35,40],2):
 r=receipt(O/f'wirepair-{a}-{b}.json')
 if not r['passed'] or r['minimumGapMm']<.5:errors.append('Wire pair '+str((a,b)))
 gaps.append(r['minimumGapMm'])
r={'stationStaticClearancePassed':not errors,'integrationReady':False,'errors':errors,'obstaclePairs':len(plan['pairs']),'aabbSeparatedPairs':sum(not p['exactNeeded'] for p in plan['pairs']),'exactPairs':sum(p['exactNeeded'] for p in plan['pairs']),'interwirePairs':6,'minimumExactForeignGapMm':min(gaps),'currentWireMeshes':{str(pin):{'mesh':str(O/f'i2s-pin{pin}-world.stl'),'sha256':sha(O/f'i2s-pin{pin}-world.stl')} for pin in [12,20,35,40]},'contactLimits':'Only matching female exit planes <=2 micrometres axial /0.43mm radius and four solder pad planes within local40nanometre slab. No complete component waived.','inventoryCorrection':{'owned4397Sets':1,'ownedFemaleTails':4,'usedFemaleCutoffsMm':[36,36,40,40],'minimumAvailableFemaleTailMm':40,'jstSideRetainedMm':100,'imuClubTailProposedMm':150,'solderOverlapMm':4,'resultingImuSpanBeforeOtherAllowancesMm':246,'clubTailMinimumFor250mmFinishedSpanMm':154,'note':'This corrects earlier receipt text that called100+150 a250mm finished span without subtracting splice overlap. Other8GPIO contacts are separate unconfirmed club requirements.'},'pending':['Full FFC mutual fit','Constant-length cable motion and cap closure;40mm opening is impossible with current static lengths','GAIN resistor leads/VIN branching and remaining power/IMU fanout','Body-joint motion domain with new flexible routes','Actual stock/insulation/solder/printed fit qualification'],'sourceHashes':{str(Path(__file__)):sha(Path(__file__)),str(P):sha(P),**inputs}};(O/'I2S-STATIC-STATION.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'stationStaticClearancePassed':r['stationStaticClearancePassed'],'errors':errors,'minimumExactForeignGapMm':min(gaps)}));raise SystemExit(0 if not errors else 2)
