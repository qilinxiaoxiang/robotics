"""Accept the supported design decisions; never accept unfinished manufacturing."""
from pathlib import Path
import json,hashlib,base64,importlib.util
import numpy as np
D=Path(__file__).resolve().parent
load=lambda p:json.loads((D/p).read_text())
sha=lambda p:hashlib.sha256((D/p).read_bytes()).hexdigest()
def main():
 c=load('camera-eye-feasibility.json');h=load('head-fit-investigation.json');n=load('nut-fit-investigation.json');source=sha('../leg-guide-20261006/full-build-data.json');checks=[];source_compatibility=None
 def check(ok,label):
  checks.append({'check':label,'passed':bool(ok)})
 for r,label in [(c,'camera'),(h,'head'),(n,'nuts')]:
  bound=r['sourceDataSha256']==source
  if not bound:
   # Only these legacy head geometry receipts can inherit the pinned IMU vector
   # and fastener-source digest corrections. Every other change is rejected.
   helper=D.parent/'leg-guide-20261006/non-head-review/source_compatibility.py'
   spec=importlib.util.spec_from_file_location('imu_source_compatibility',helper);compat=importlib.util.module_from_spec(spec);spec.loader.exec_module(compat)
   if r['sourceDataSha256']==compat.OLD_SHA256:
    try:
     if source_compatibility is None:source_compatibility=compat.validated_equivalent_geometry_source(r['sourceDataSha256'])
     bound=source_compatibility['currentSha256']==source and source_compatibility['accepted']
    except compat.SourceCompatibilityError:
     bound=False
  check(bound,label+' report binds current geometry source (exact hash or two-field metadata proof)')
 check(sum(c['originalCameraIntersectionsMm3'].values())>1,'Original eye placement reproduces interference')
 check(max(c['candidateCameraIntersectionsMm3'].values())<1e-5,'Candidate static eye package has no modeled intersection')
 check(c['faceComponents']==c['eyeTrimComponents']==1,'Face and eye remain single bodies')
 check(len(c['piPilotKeepoutChecks'])==4 and all(p['removedPilotKeepoutVolumeMm3']<1e-6 for p in c['piPilotKeepoutChecks']),'All four Pi pilots preserved')
 check(max(c['optics']['intersectionsMm3'].values())<1e-5,'Modeled camera field clears existing eye outline')
 s=c['straightBenchInsertion'];check(s['PiMustBeAbsent'] and s['stepMm']==.25 and len(s['samples'])==121 and max(r['maxIntersectionMm3'] for r in s['samples'])<1e-5,'Detached-face camera entry sampled before Pi installation')
 b=c.get('boardScope',{}); config=load('viewer-candidate.json')
 check(b.get('referenceModel')=='First-generation Pi Zero outline reference' and b.get('pi3FitVerified') is False and b.get('completeZeroBoardFitVerified') is False and b.get('exactBorrowedBoardIdentified') is True,'Legacy study remains Zero outline only; exact board identified, full-board and Pi 3 fit unverified')
 p=next(p for p in load('../leg-guide-20261006/full-build-data.json')['parts'] if p['key']=='pi');v=np.frombuffer(base64.b64decode(p['positionB64']),'<f4').reshape(-1,3)
 check(b.get('referenceVerticesSha256')==hashlib.sha256(base64.b64decode(p['positionB64'])).hexdigest() and np.allclose(np.ptp(v,axis=0),[1.6,65,30],atol=.001),'Reference board measured as Zero-size PCB slab, not a populated board')
 check(config.get('boardScope')==b and 'Pi 3 fit unverified' in (D/'HEAD-EYE-REVIEW.html').read_text() and 'Pi 3 fit unverified' in (D/'render_review.py').read_text(),'Candidate webpage and rendering state the board limitation')
 browser=load('live-browser-acceptance.json') if (D/'live-browser-acceptance.json').exists() else {}
 browser_ok=bool(browser.get('accepted') and browser.get('htmlSha256')==sha('HEAD-EYE-REVIEW.html'))
 f=h['findings'];check(max(f['currentClosedSeat']['peakContactsMm3'].values())>60 and not f['originalCommunitySupport']['peakContactsMm3'],'Closed support reproduces trap absent in original open support')
 check(f['passiveBoss']['minimumOutwardReliefMmToClearClosedBoreLip']>2.7,'Force-fit decision based on captured-shaft geometry')
 check(len(f['lowerShellOrderNegativeControl']['shellFirstJawPadRoutes'])==9,'Lower-shell reorder decision retains bounded failed routes')
 r=n['recommendedCandidate'];check(r['candidateBodies']==1 and r['protectedNutPocketAndSeatRemovedVolumeMm3']==0,'Nut relief preserves original seat and one-piece cap')
 check(len(r['allFourAxialNutEntries'])==4 and all(len(p['samples'])==241 and p['maxOverlapMm3']<1e-5 for p in r['allFourAxialNutEntries']),'Four nut paths pass 0.05 mm sampling')
 check(not f['decision']['physicalForceApproved'] and not f['decision']['readyForProductionOrPrint'] and not c['physicalFitVerified'],'Physical and manufacturing boundaries preserved')
 out={'acceptedDecisionEvidence':all(x['passed'] for x in checks),'checks':checks,'sourceDataSha256':source,'evidenceSha256':{p:sha(p) for p in ['camera-eye-feasibility.json','head-fit-investigation.json','nut-fit-investigation.json']},'decision':'Legacy study supports local access and eye camera; current curved-head/retainer/jaw candidates require their integrated checks. Defer already seated ankle/foot.','manufacturingAccepted':False,'physicalFitVerified':False,'interactiveBrowserAccepted':browser_ok,'visualArtifact':'eye-camera-comparison.png'}
 out['geometrySourceCompatibility']=source_compatibility
 (D/'review-acceptance.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'acceptedDecisionEvidence':out['acceptedDecisionEvidence'],'checks':len(checks),'failed':[x['check'] for x in checks if not x['passed']]}));raise SystemExit(not out['acceptedDecisionEvidence'])
if __name__=='__main__':main()
