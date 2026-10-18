from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent;H=D.parent;Q=D/'fixed-pose-local-bend'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def receipt(p):return {'path':str(p),'sha256':sha(p)}
def read(p):return json.loads(p.read_text())
fit=read(Q/'spacer2-tilted-complete-fit.json');selfr=read(Q/'spacer2-tilted-complete-localization.json');static=read(Q/'spacer2-tilted-complete-static.json');local=read(Q/'frozen-local-occupancy-check.json');closure=read(H/'gpio-audio-repair/ffc-cap-closure/diagnostic-combined-result.json')
mesh=Q/'spacer2-tilted-complete-ribbon-world.stl';assert sha(mesh)=='7ecca06a418119593bf0f665c426dd74f215670e86c3b9ea181fef0f9d2af069';assert closure['fullFFCWorldMeshSha256']==sha(mesh)
refs=[Q/x for x in ['spacer2-tilted-complete-fit.json','spacer2-tilted-complete-static.json','spacer2-tilted-complete-localization.json','spacer2-tilted-complete-components-localization.json','frozen-ribbon-clearance.json','frozen-local-occupancy-check.json','actual-cable-identification.json','pi-spacer2-pose.json','pi-spacer2-parts.json']]+[H/'cabling-release-20261008/neck-repair/pi-local-components/local-occupancy.json',H/'gpio-audio-repair/ffc-cap-closure/diagnostic-combined-result.json',Path(__file__)]
r={
 'schemaVersion':1,'status':'illustrative_route_has_unresolved_conservative_component_receiving_contact',
 'integrationReady':False,'wholeHarnessAccepted':False,'physicalValidated':False,
 'complete200mm':abs(fit['materialLengthMm']-200)<1e-8 and fit['maxConstraintResidual']<1e-8,
 'materialLengthMm':fit['materialLengthMm'],'endpointFrameConstraintResidual':fit['maxConstraintResidual'],
 'mesh':receipt(mesh),'outsideMesh':receipt(Q/'spacer2-tilted-complete-ribbon-outside-world.stl'),
 'selfClear':selfr['completedSelfPairs']==selfr['expectedSelfPairs']==4851 and not selfr['self'],
 'selfCoverage':{'expectedNonadjacentPairs':4851,'completedNonadjacentPairs':4851,'nonzeroPairs':len(selfr['self']),'scope':'2mm material pieces; adjacent seams excluded; local developable bends represented in full solid'},
 'staticClear':local['staticClear'],
 'staticCoverage':{'expectedHeadObstacles':static['expectedObstacles'],'completedHeadObstacles':static['completedObstacles'],'openrbConservativeComponents':142,'componentFootprintsExpected':13,'componentFootprintsCompleted':local['completedFootprints'],'originalComponentBoxOverlapMm3':local['originalBoxOverlapMm3'],'refinedReceivingOverlapMm3':local['refinedOverlapMm3'],'interpretation':'Remaining intersections are with unknown-height small-component receiving columns at3.8mm, not demonstrated collisions with physical components. CSI2.2mm receiving is clear; outside refinement window original box retained and clear. No geometric collision waiver applied.'},
 'connectorStatus':{'status':'standard_interface_handling_required_not_exact_seating_certified','cameraContactDirection':'toward camera PCB','piContactDirection':'toward Pi PCB; source-supported rather than inferred from connector top-contact label','modeledInsertionDepthMm':{'camera':5,'pi':4.4},'insertionDepthSource':'CAD assumptions, not manufacturer dimensions; do not treat these values as assembly instructions','fullWidthUnbentEndMaterialMm':{'camera':8.680,'pi':4.579},'modeledExternalFullWidthStraightMm':{'camera':3.680,'pi':.179},'limitation':'The frozen numerical example does not establish adequate Pi stiffener straight length under its assumed4.4mm engagement. Preserve real reinforced ends flat and seat fully in the actual ZIF socket; nearby flexible return may be adjusted. This is not evidence that printed parts need changing.','exactManufacturerConnector':'Official Zero W reduced schematic names Molex54548-2271; compatible Amphenol2mm height used only for local receiving diagnosis, not insertion-depth certification.'},
 'populatedCapClosureClear':closure['newFFCCapClosureClear'],'piSpacerDeltaCapClosureClear':closure['pi2mmDeltaCapClosureClear'],
 'closureScope':'148 moving solids;146 continuously separated by bounds,2 checked at161 poses onZ40..0. Pi spacer change22parts checked against148 moving solids. See closure receipt for sampled versus continuous evidence.',
 'clearanceMm':{'face':1.3969964462,'cap':.6736269465,'piPcb':.6094709456,'amp':.2222972030,'cameraPortBoundary':0},
 'handlingVariation':'Frozen example has0.222mm at amplifier and is not a robust mandatory routing template. Printed face/cap gaps are positive; arrange flexible slack clear of amplifier and lid edges before closing. Contact boundary at camera socket is intentional endpoint adjacency, not a separate slack corridor.',
 'localAdjustmentEvidence':{'normalToPcbLiftMm':.9,'worldVector':local['manualAdjustmentDiagnostic']['worldVector'],'minimumLocalReceivingGapMm':min(x['gapCapped2Mm'] for x in local['manualAdjustmentDiagnostic']['rows']),'sourceFootprintsClear':all(x['liftedLocalizedMaterialOverlapMm3']<1e-6 for x in local['manualAdjustmentDiagnostic']['rows']),'otherRigidObstaclesClear':all(x['overlapMm3']<1e-6 for x in local['manualAdjustmentDiagnostic']['rigidObstacleChecks']),'limitation':'ROI segment translated only to test adjacent handling space. Transition continuity, material length, self clearance and OpenRB not certified for this modified segment. Whole frozen route remains unchanged.'},
 'printGeometryChangeRequired':False,'printGeometryDecisionScope':'No additional printed geometry change is supported by the remaining conservative small-component contact or terminal straight-length assumptions. This is not a complete printing-release flag and does not supersede the parent withdrawal pending full harness acceptance.',
 'assemblyOrder':[
  'Keep cap open. Use the received orange Standard–Mini200mm cable; fully unlock both ZIF latches and keep the reinforced ends flat.',
  'Connect camera end with metal contacts toward its PCB and close the latch. Support the camera/board while inserting; do not pull against the cable.',
  'With Pi accessible on its three2mm-spaced supports, connect the22-pin end with contacts toward Pi PCB and close the latch. No modeled4.4mm insertion measurement is prescribed.',
  'Arrange the middle slack in smooth loose returns around the negative edge of Pi and its component-side cavity, leaving reinforced ends straight. Lift the final return away from components into the locally checked adjacent space; do not force a crease or reproduce the mathematical curve exactly.',
  'Before fastening cap, keep the cable away from amplifier, screw bosses and lid seam; lower the populated cap gently while watching the slack. Stop and rearrange any pinched or taut section rather than using screws to compress it.'
 ],
 'bendEndurance':{'validated':False,'minimumModeledRadiusMm':1,'thicknessReceivingMm':.3,'meaning':'Engineering receiving model; manufacturer static/fatigue bend limits not established. No recommendation to forceR1 creases or repeatedly bend at the stiffener.'},
 'practicalDisposition':'Keep existing body, camera clamp, Pi and OpenRB architecture. The full200mm storage example fits the rigid cavity and closes, with remaining uncertainty confined to a small-component receiving/terminal handling region. A finite local end adjustment is being evaluated separately; no broad route search or new printed guide is authorized by this report.',
 'receipts':[receipt(p) for p in refs]
}
(Q/'full-ribbon-acceptance.json').write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n')
print(Q/'full-ribbon-acceptance.json',sha(Q/'full-ribbon-acceptance.json'))
