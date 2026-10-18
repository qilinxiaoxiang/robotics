"""Join immutable reconstruction and incremental static evidence; no CAD changes."""
from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=D/'roof-restoration-reconstruction-only.json'
if not base.exists():base.write_bytes((D/'roof-restoration.json').read_bytes())
r=json.loads(base.read_text());p=D/'patch-static-check.json';s=json.loads(p.read_text())
assert s['passed'] and s['expectedParts']==s['completeParts']==160
for path,h in s['sourceHashes'].items():assert sha(Path(path))==h,path
assert sha(Path(r['output']))==r['outputSha256']
r['status']='ROOF_RESTORED_AND_INCREMENTAL_STATIC_CLEAR_FOR_MAC_USB_ARCHITECTURE'
r['restoredPatch']['deltaBooleanBoundsIncludingNumericalSliversMm']=r['restoredPatch']['boundsMm']
r['restoredPatch']['deltaBooleanBodiesIncludingNumericalSlivers']=r['restoredPatch'].pop('bodies')
r['restoredPatch']['boundsMm']=s['patchBoundsMm']
r['restoredPatch']['boundsMeaning']='Bounds of actual exported native reconstruction patch; excluded numerical zero-volume slivers from Boolean-difference diagnostic bounds.'
r['adoption']={'cadIntegrationReady':True,'architecture':'Mac connects directly to OpenRB through retained rear USB service opening; Pi USB socket is empty. Pi remains the sensor/camera computer.','piToOpenRBOTGCableRemoved':True,'runtimeMigrationVerified':False,'unchangedPartsPreserved':True,'incrementalStaticPassed':True,'expectedPairs':160,'completePairs':160,'exactSeparatedBounds':159,'solidIntersectionPairs':1,'intersectionVolumeMm3':0,'report':str(p),'reportSha256':sha(p),'scope':'Current seated pose; only added cap material. Not whole wired-robot motion acceptance.'}
r['remaining']='Mac/OpenRB data ownership and Pi sensor transport runtime migration plus physical commissioning remain unvalidated; head-wire installation is checked separately. No crown opening is retained for an unused Pi USB plug.'
r['finalizerSha256']=sha(Path(__file__));r['reconstructionReceiptSha256']=sha(base)
(D/'roof-restoration.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'report':str(D/'roof-restoration.json'),'sha256':sha(D/'roof-restoration.json'),'mesh':r['output'],'meshSha256':r['outputSha256']}))
