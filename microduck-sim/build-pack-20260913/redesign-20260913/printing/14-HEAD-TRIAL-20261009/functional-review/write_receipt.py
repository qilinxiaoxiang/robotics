from pathlib import Path
import json,hashlib,zipfile
D=Path(__file__).resolve().parent;P=D.parent;src=D/'hole-readback.json';d=json.loads(src.read_text())
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def ref(p):return dict(path=str(p),sha256=sha(p))
rows=[]
for r in d['results']:
 a=Path(r['archive']);g=Path(r['gcode']);assert sha(a)==r['archiveSha256'];assert sha(g)==r['gcodeSha256']
 with zipfile.ZipFile(a)as z:
  n=next(x for x in z.namelist()if x.endswith('plate_1.gcode'));h=hashlib.sha256()
  with z.open(n)as f:
   for b in iter(lambda:f.read(1048576),b''):h.update(b)
 assert h.hexdigest()==r['gcodeSha256'];assert len(r['features'])==19 and all(f['nearbyModelSegments']>0 and f['modelCoreCount']==0 for f in r['features'])
 hits=[f for f in r['features']if f['supportCoreCount']]
 assert (len(hits)==1 and hits[0]['name']=='pi-pilot-1-1' and hits[0]['supportCoreCount']==3) if r['machine']=='Bambu' else not hits
 rows.append(dict(machine=r['machine'],archive=ref(a),gcodeSha256=r['gcodeSha256'],archiveGcodeMatchesInspectedFile=True,checkedHoles=19,holesWithoutSupportCore=18 if hits else 19,requiredOrdinaryCleanup=['Remove the single support arc at the exposed positive-Y lower Pi pilot mouth before fitting the PCB or inserting its screw. Use tweezers or fine pliers from the open cap interior; check the clear mouth by hand, do not force the screw through support.'] if hits else [],deepBoreSupportBlockageFound=False,additionalBlockerRequired=False))
report=dict(schemaVersion=1,status='PROTOTYPE_FUNCTIONAL_ACCESS_ACCEPTED_WITH_ORDINARY_SUPPORT_REMOVAL',prototypeOnly=True,wholeHeadAssemblyAccepted=False,physicalSupportRemovalVerified=False,scope='Actual native toolpaths: 4 OpenRB pilots, 4 Pi pilots, 2 amplifier pilots, 2 speaker pilots, 3 original cap-closure pilots, and 4 separate speaker-ring through-holes per machine. Root owns first-layer/bed/footprint review.',inspection=ref(src),script=ref(D/'audit_holes.py'),manifest=ref(P/'head-trial.json'),preparation=ref(P/'run/preparation.json'),results=rows,remediedFailure=dict(baselineReadback=ref(D/'hole-readback-before-blocker.json'),problem='15 sampled support core segments in positive-Y upper Pi bore',repair='One Bambu-only local non-printing support blocker; printable geometry unchanged',blocker=ref(D/'pi-positive-y-upper-hole-support-blocker-print.stl'),recheckCoreSegments=0),remainingMouthSupport=dict(machine='Bambu',feature='pi-pilot-1-1',gcodeLines=[399985],arcSubsegments=3,sourceHoleAxisRangeMm=[0.4,4.8],supportAxisRangeMm=[4.5838423035320925,4.590077686135782],depthFromOpenBoardFacingMouthMm=[0.209922313864218,0.2161576964679075],assessment='One exposed mouth-edge support arc. This is accessible before board installation, rather than a lodged deep-bore fill. Ordinary manual removal is accepted for the print-and-fit prototype; no repeated re-slicing is required.'),supportAccess='Remove cap cavity/tree supports while the cap is empty, before installing boards, speaker or wiring. The open underside permits ordinary access to board/speaker seats. Clear contact faces and hole mouths by hand; this review does not certify actual printed shrinkage, tapping quality, removal force, or unseen support adhesion.',boundary='Does not establish USB cable suitability, GPIO flexible-wire clearance, closed complete head fit, powered operation, or full assembly acceptance. No zero-support claim.')
p=D/'functional-review.json';p.write_text(json.dumps(report,indent=2)+'\n');print(str(p));print(sha(p));print([(r['machine'],r['archive']['sha256'])for r in rows])
