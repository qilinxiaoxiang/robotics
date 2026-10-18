from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent;P=D.parent
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def ref(p):return dict(path=str(p),sha256=sha(p))
results=[]
for color,count in [('Yellow',7),('White',3),('Orange',19)]:
 for machine in ('Bambu','Elegoo'):
  p=D/f'{color}-{machine}-hole-readback.json';d=json.loads(p.read_text());r=d['results'][0];assert len(r['features'])==count
  assert sha(Path(r['archive']))==r['archiveSha256']
  assert d['sourceHashes'][str(P/'run/preparation.json')]==sha(P/'run/preparation.json')
  assert all(f['nearbyModelSegments']>0 and f['modelCoreCount']==0 for f in r['features'])
  hits=[f for f in r['features']if f['supportCoreCount']]
  if color=='Orange'and machine=='Bambu':
   assert len(hits)==1 and hits[0]['name']=='pi-pilot-1-1'and hits[0]['supportCoreCount']==3
   assert len(set(q['line']for q in hits[0]['supportCore']))==1
   assert all(4.58<=q['axialMm']<=4.60 for q in hits[0]['supportCore'])
  else:assert not hits
  results.append(dict(color=color,machine=machine,readback=ref(p),archive=dict(path=r['archive'],sha256=r['archiveSha256']),gcodeSha256=r['gcodeSha256'],checkedHoles=count,holesWithoutSupportCore=count-len(hits),modelCoreOcclusions=0,cleanupRequired=bool(hits),cleanup='Before installing Pi, remove the one exposed support arc about 0.21 mm inside the positive-Y lower pilot mouth with tweezers/fine pliers. Check the clear mouth by hand; do not drive the screw through support.' if hits else None,additionalBlockerRequired=False))
r=dict(schemaVersion=1,status='PROTOTYPE_FUNCTIONAL_HOLES_ACCEPTED_WITH_DECLARED_ORDINARY_CLEANUP',partsScope=['head_bottom','face_panel','head_cap','speaker_cradle','speaker_keeper'],excludedSeparateOwnerScope=['imu_clamp','imu_cover','Black parts'],checkedNativeRows=6,expectedNativeRows=6,holeChecks=58,coverageComplete=True,results=results,manifest=ref(P/'complete-incremental.json'),preparation=ref(P/'run/preparation.json'),checker=ref(D/'audit_holes.py'),practicalAssessment='Yellow seven mounting/closure bores and White three camera pilots are free of support-core and model-core obstruction in both actual sliced programs. Orange matches the reviewed head trial: one shallow exposed Pi-hole support arc in Bambu is ordinarily removable; all other inspected bores are clear. Remove cavity supports while the cap is empty, then inspect mounting seats before installing boards or the speaker.',prototypeOnly=True,physicalSupportRemovalVerified=False,fullAssemblyAccepted=False,noZeroSupportClaim=True,boundary='Actual native toolpaths were inspected with each machine nozzle offset and current placement. First layers, bed footprints and remaining parts are checked by separate owners. This receipt does not prove printed dimensional fit, screw tapping quality, USB closure, full harness or powered operation.')
p=D/'functional-review.json';p.write_text(json.dumps(r,indent=2)+'\n');print(str(p));print(sha(p))
