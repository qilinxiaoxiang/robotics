"""Bind the finite local correction and inherited prefix without new CAD work."""
from pathlib import Path
import json,hashlib,copy
D=Path(__file__).resolve().parent;H=D.parent;Q=D/'fixed-pose-local-bend';A=H/'gpio-audio-repair/ffc-terminal-adjustment'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def ref(p):return {'path':str(p),'sha256':sha(p)}
def verify_sources(d):
 for p,h in d.get('sourceHashes',{}).items():assert sha(p)==h,(p,h,sha(p))
fit=read(A/'dogleg-0.25.json');check=read(A/'dogleg-0.25-check.json');prefix=read(A/'prefix-inheritance.json');close=read(A/'final-closure/summary.json');contract=read(A/'final-closure/input-contract.json')
final=read(A/'final-geometric-acceptance.json');assert final['geometricCandidateAccepted']
for d in [fit,check,prefix,close,final]:verify_sources(d)
assert check['complete'] and check['staticClear'] and check['selfClear'] and not check['self']
assert check['expectedSelfPairs']==check['completedSelfPairs']==4221
assert prefix['exactPrimitiveEquality'] and prefix['inheritedWhollyUnchangedPairCount']+4221==4851
assert abs(fit['materialLengthMm']-200)<1e-6 and fit['maxConstraintResidual']<1e-6
assert close['diagnosticClosureClear'] and close['expectedSamples']==close['samplesCovered']==23828
assert all(e['passed'] for e in close['entities'])
mesh=Path(check['fullMesh']);assert sha(mesh)==check['fullMeshSha256']
# Independently verify exact prefix fields, not merely the inheritance boolean.
oldfit=read(Q/'spacer2-tilted-complete-fit.json')
def clipped(pr):
 return [{**x,'s1':min(x['s1'],75)} for x in pr if x['s0']<75]
assert clipped(oldfit['primitives'])==clipped(fit['primitives'])
oldpath=Q/'full-ribbon-acceptance-before-local-s.json'
if not oldpath.exists():
 current=read(Q/'full-ribbon-acceptance.json');assert not current['staticClear'];oldpath.write_bytes((Q/'full-ribbon-acceptance.json').read_bytes())
r=copy.deepcopy(read(oldpath))
r.update(schemaVersion=2,status='full_200mm_local_s_route_digital_geometry_accepted',integrationReady=True,routeGeometryAccepted=True,complete200mm=True,staticClear=True,selfClear=True,materialLengthMm=fit['materialLengthMm'],endpointFrameConstraintResidual=fit['maxConstraintResidual'],mesh=ref(mesh),physicalValidated=False,motorCommissioningAccepted=False,runtimeAccepted=False,wholeHarnessAccepted=False)
r['scope']='Digital mechanical FFC storage and populated-cap closure only. Physical bend endurance, electrical operation, other wiring circuits and final commissioning are not certified by this report.'
r.pop('outsideMesh',None)
r['selfCoverage']={'fullNonadjacentPairs':4851,'inheritedUnchangedPrefixPairs':630,'newChangedPairsExpected':4221,'newChangedPairsCompleted':4221,'nonzeroPairs':0,'scope':'2mm material pieces; adjacent seams excluded. Exact unchanged0..75mm primitive equality permits inheritance, including unchanged camera endpoint.'}
r['staticCoverage']={'unchangedMaterialMm':[0,75],'recheckedMaterialMm':[75,195.6],'modeledTerminalMatingExcludedMm':[[0,5],[195.6,200]],'changedStaticRows':len(check['static']),'changedNonzeroRows':sum(x['overlapMm3']>1e-6 for x in check['static']),'openrbConservativeComponents':142,'localComponentFootprints':13,'sourceBoxOutsideWindowRetained':True,'interpretation':'Local S avoids all actual drawn small-component footprints while retaining conservative3.8mm unknown heights. CSI receiving stays2.2mm. No contact subtraction or dropped obstacles; source former failure retained separately.'}
r['connectorStatus'].update(status='modeled_endpoints_connected_with_flat_terminal_allowance_physical_seating_not_claimed',fullWidthUnbentEndMaterialMm={'camera':8.680,'pi':fit['fullWidthFlatMm']},modeledExternalFullWidthStraightMm={'camera':3.680,'pi':fit['fullWidthFlatMm']-4.4},limitation='The local S provides6.4mm full-width straight Pi material, leaving2.0mm outside under the modeled4.4mm insertion assumption. Those are numerical receiving assumptions, not manufacturer assembly dimensions. Actual reinforced ends remain flat, fully seated and latched; no exact folding template is required.')
r['populatedCapClosureClear']=True
r['closureScope']='148 moving solids:147 proven continuously separated by swept bounds; cap checked at161 poses along Z40..0 in0.25mm increments. All23828 entity/sample positions covered. Pi2mm delta closure independently inherited because rigid geometry is unchanged.'
r['clearanceMm']={'currentRouteGlobalMinimum':'not computed; static intersection and populated closure checks passed','unchangedPrefixHistoricalScope':'Original route gap report remains bound as historical evidence; its whole-route minima are not relabeled as new full-route minima.'}
r['handlingVariation']='Use the local S as an example of ordinary flexible slack redistribution. Do not reproduce its precise curve or force sharp creases. It keeps the end reinforcement straight and lifts the former return away from conservative component receiving. Model0.3mm thickness/R1 is a receiving assumption, not a physical bend-endurance guarantee.'
r.pop('localAdjustmentEvidence',None)
r['printGeometryChangeRequired']=False
r['printGeometryDecisionScope']='This finite full-length correction needs no new printed part or changed board/camera pose. It resolves the previous component-receiving and short-Pi-end numerical example failures within the existing printed cavity. Parent delivery gate owns overall print release.'
r['assemblyOrder'][3]='Arrange middle slack in smooth loose returns around the negative edge of Pi and its component-side cavity. Near Pi, use a shallow S to keep the return off components and leave the reinforced terminal flat; no crease or exact mathematical shape is prescribed.'
r['practicalDisposition']='Retain existing body, camera clamp, Pi2mm spacers and OpenRB architecture. Full200mm modeled routing, self-clearance and populated-cap closure now pass with a local flexible end adjustment, without new print geometry. Perform ordinary connector seating and pinch checks during physical assembly.'
r['supersedes']=ref(oldpath)
paths=[A/'final-geometric-acceptance.json',A/'dogleg-0.25.json',A/'dogleg-0.25-check.json',A/'prefix-inheritance.json',A/'final-closure/summary.json',A/'final-closure/input-contract.json',A/'final-closure/head_cap.json',A/'final-closure/broadphase.json',Q/'spacer2-tilted-complete-static.json',Q/'spacer2-tilted-complete-localization.json',Q/'spacer2-tilted-complete-components-localization.json',Q/'frozen-local-occupancy-check.json',Q/'actual-cable-identification.json',Q/'pi-spacer2-pose.json',Q/'pi-spacer2-parts.json',H/'cabling-release-20261008/neck-repair/pi-local-components/local-occupancy.json',H/'gpio-audio-repair/ffc-cap-closure/diagnostic-pi-spacer2/summary.json',Path(__file__)]
r['receipts']=[ref(p)for p in paths]
(Q/'full-ribbon-acceptance.json').write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n')
print(sha(Q/'full-ribbon-acceptance.json'))
