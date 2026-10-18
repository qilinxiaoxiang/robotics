"""Freeze the explicit review status without changing any geometry.
Run after repair_i2s.py and the registered J4 endpoint update. This stage is not
an assembly acceptance gate; all known failures remain visible.
"""
from pathlib import Path
import json,hashlib,datetime,shutil
D=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
m=json.loads((D/'manifest.json').read_text());frozen=D/'manifest-before-status.json'
if not frozen.exists():shutil.copyfile(D/'manifest.json',frozen)
head=json.loads((D/'i2s-repair-check.json').read_text());initial=json.loads((D/'local-check.json').read_text())
for p in m['parts']:
 assert sha(p['file'])==p['sha256'],p['key']
 report=head if p['key'].startswith('i2s_') else initial
 failures=[x for x in report['records'] if x['wire']==p['key'] and x['status']=='INTERSECTION']
 p['knownStaticIntersections']=failures
 if p['key'].startswith('i2s_'):
  p['validationStatus']='FFC crossing and original jaw_support collision eliminated in the finite static screen. Not fully accepted: endpoint receiving contacts, invalid obstacle/degenerate solder-face results, inter-wire/self and articulation remain unclosed.'
  if p['key']=='i2s_pin_40':p['validationStatus']+=' KNOWN FAILURE: restored roof overlap 0.002045 mm3; retained without tolerance waiver.'
 elif p['key'].startswith(('pi_power','amp_power','openrb_power','imu_')):
  p['validationStatus']='KNOWN FAILED CANDIDATE: current static routing conflicts with listed rigid parts. Review-only red-line item; not assembly instructions. '+p['validationStatus']
  p['reviewColor']='#ef3434'
summary={'title':'Roof wiring stage — explicit partial result','frozenAt':datetime.datetime.now().astimezone().isoformat(),'integrationReady':False,'geometryFrozen':True,'renderableParts':len(m['parts']),'passedChanges':['Pi USB unused in this CAD architecture; Mac USB enters through rear OpenRB service opening','Four I2S routes no longer cross the fixed200 mm camera-ribbon mesh or original jaw_support in the bounded static screen','Actual OpenRB J4 mouth coordinates and polarity are registered; DFR-side installed pad orientation remains proposed'],'remainingFailures':['I2S pin40 touches restored roof by0.002044771 mm3; no tolerance exemption','Pi power/return and IMU candidates cross head_bottom/jaw_support','Initial power candidates cross IMU installation envelope; some also regulator_insert','Amp/OpenRB power candidate paths cross restored cap; J4 endpoint correction is not a full-route clearance claim','Speaker source wires each touch speaker_keeper by approximately0.0496 mm3 in expanded current screen; not silently waived'],'unclosedChecks':['I2S-to-I2S/self and joint articulation','Source motor/hardware open meshes and zero-thickness terminal contact results cannot substantiate zero-intersection claims','Exact DFR installed pad orientation and BNO085 connector pose','Current stock lengths, strain relief, physical fitting, power and split runtime'],'sourceBoundReports':{str(D/'i2s-repair-check.json'):sha(D/'i2s-repair-check.json'),str(D/'head-internal-check.json'):sha(D/'head-internal-check.json'),str(D/'local-check.json'):sha(D/'local-check.json')},'testedManifestSnapshot':{'file':str(frozen),'sha256':sha(frozen)},'cameraContactInterpretation':'Full ribbon intersects camera_board by23.9996 mm3, numerically matching modeled5 mm x16 mm x0.3 mm inserted section. Preserve prior source-bound connector-aware acceptance; generic whole-line intersection is not independent proof of a new collision or an exemption for arbitrary contacts.'}
m['stageSummaryFile']=str(D/'stage-summary.json');m['integrationReady']=False;m['geometryFrozen']=True
(D/'stage-summary.json').write_text(json.dumps(summary,indent=2)+'\n');(D/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(sha(D/'manifest.json'))
