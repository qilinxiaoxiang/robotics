"""Finite envelope comparison; no production geometry or joint-limit change."""
from pathlib import Path
import json,hashlib,math
D=Path(__file__).resolve().parent;R=D.parents[1];SIM=R.parents[1]
G=R/'leg-guide-20261006';A=SIM/'hardware-design-20260912/whole-robot-20260912/assembly'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
data=json.loads((G/'full-build-data.json').read_text());parts={p['key']:p for p in data['parts']}
bankSource=R/'powerbank-trial-20261008/source-power.json';bank=json.loads(bankSource.read_text())
assert bank['dimensionsMm']==[80.9,65.9,26]
bodies=json.loads((A/'body-transforms.json').read_text())['zero_joint_body_transforms']
yaw=[bodies[k][1][3] for k in ['yaw2roll','bearing_roll']]
pitch=[bodies[k][1][3] for k in ['upper_leg_left','upper_leg_right']]
gap=parts['yaw']['bounds'][0][1]-parts['right_yaw']['bounds'][1][1]
layouts=[]
for id,title,xyz,longaxis in [('A','Wide across hips, upright',[26,65.9,80.9],2),('B','Thin across hips, upright',[65.9,26,80.9],2),('C','Thin across hips, fore-aft',[80.9,26,65.9],0)]:
    total=math.ceil(xyz[1]+2+4+2-gap);ctr=[-5,0,-6]
    bounds=[[ctr[i]-xyz[i]/2 for i in range(3)],[ctr[i]+xyz[i]/2 for i in range(3)]]
    receiving=[[bounds[0][i]-1 for i in range(3)],[bounds[1][i]+1 for i in range(3)]]
    service=[]
    for sign in [-1,1]:
        lo=bounds[0].copy();hi=bounds[1].copy()
        if sign<0:hi[longaxis]=lo[longaxis];lo[longaxis]-=25
        else:lo[longaxis]=hi[longaxis];hi[longaxis]+=25
        service.append({'end':sign,'boundsMm':[lo,hi],'status':'25mm trial service volume; not manufacturer dimension or verified clearance'})
    blockers=[]
    for key in ['torso_base','power_support','regulator','regulator_insert','fuse_carrier','shell_left','shell_right','imu_clamp']:
        b=parts[key]['bounds'];ext=[min(bounds[1][i],b[1][i])-max(bounds[0][i],b[0][i]) for i in range(3)]
        if min(ext)>0:blockers.append({'key':key,'boundsOverlapMm3':math.prod(ext),'meaning':'AABB warning only; not exact-solid intersection'})
    layouts.append({'id':id,'title':title,'bankDimensionsXYZMm':xyz,'bankBoundsMm':bounds,'bankReceivingBoundsMm':receiving,'longAxis':longaxis,'ports':service,'minimumWideningWithBankClearanceAnd2mmWallsMm':xyz[1]+6-gap,'selectedTotalWideningMm':total,'legShiftPerSideMm':total/2,'newYawAxisSpacingMm':abs(yaw[0]-yaw[1])+total,'newPitchAxisSpacingMm':abs(pitch[0]-pitch[1])+total,'nominalWallToYawLinkGapMm':(gap+total-xyz[1]-6)/2,'contextWidthIfSidewallsTranslatedMm':parts['shell_left']['bounds'][1][1]-parts['shell_right']['bounds'][0][1]+total,'oldCentralOccupancyWarnings':blockers,'mountingValidated':False,'allJointCollisionValidated':False})
report={'status':'CONCEPT ENVELOPES ONLY / NOT PRINTABLE','problemIds':['P0','P5'],'baseline':{'yawAxisCentersMm':[[6,y,-5] for y in yaw],'yawAxisSpacingMm':abs(yaw[0]-yaw[1]),'pitchAxisCentersMm':[[4,y,-17.5] for y in pitch],'pitchAxisSpacingMm':abs(pitch[0]-pitch[1]),'minimumCentralYawLinkGapMm':gap,'hipYawCaseGapMm':parts['motor10']['bounds'][0][1]-parts['motor5']['bounds'][1][1]},'assumptions':{'bankClearancePerSideMm':1,'provisionalChannelWallMm':2,'nominalMovingPartClearanceMm':1,'serviceLengthEachEndMm':25,'serviceDimensionIsManufacturerSpec':False},'layouts':layouts,'preferredNextCandidate':'C: 22mm wider, long axis fore/aft. Same lateral increase as B but lower height. Both broad end faces accessible front/rear. Requires a new central frame and converter relocation, not just leg spacing.','affectedParts':[{'key':'torso_base','sourceId':34,'color':'Black','change':'New bridge to hip yaw interfaces shifted ±11mm for B/C.'},{'key':'power_support','color':'Black','change':'Replace integrated old receiving frame; all concepts occupy the current converter region.'},{'key':'shell_left','sourceId':8,'color':'Orange','change':'Wider lower interface with neck bearing axes held at original position.'},{'key':'shell_right','sourceId':10,'color':'Orange','change':'Symmetric torso-shell interface redesign, not simply shifting the neck bearings.'},{'key':'regulator_insert','color':'Black','change':'Reposition after current power architecture decision.'},{'key':'fuse_carrier','color':'Black','change':'Old eleven-fuse architecture under review; retained only as baseline occupancy, no assumption it survives.'}],'preserved':['Intact leg mechanisms: no relative motor/link change or knee/ankle disassembly.','Original head exterior and neck axis locations.','No V1.4 production or print file modified.'],'fkChangeIfAdopted':['Translate each hip yaw motor plus its complete yaw-root subtree equally outward; move matching mounting, fastener and bearing interfaces.','Do not shift only the lower leg or change the relative hip yaw/roll/pitch geometry.','Regenerate model origins, mass/inertia and revalidate stance/policy; original walking performance does not automatically transfer.'],'remaining':['Exact receiving section preserving screw seats and load paths.','Final DFR/receiver/wire placement under reviewed electrical architecture.','Bank insertion, broad port access and natural slack.','Selected design joint sweeps and self-collision.','Mass, strength, thermal and physical commissioning.'],'sourceHashes':{str(p):sha(p) for p in [Path(__file__),G/'full-build-data.json',A/'body-transforms.json',bankSource,SIM/'microduck_rl/src/mjlab_microduck/robot/microduck/robot_allcollisions.xml']}}
(D/'layout-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1500" height="920"><rect width="1500" height="920" fill="#f7f8fa"/><g font-family="Arial,sans-serif"><text x="30" y="38" font-size="25">Central battery: three envelope concepts (NOT PRINTABLE)</text><text x="30" y="68" font-size="16">Baseline yaw spacing 35mm / pitch spacing 85mm; central gap 12mm. Grey: leg envelopes. Red: existing central structure requiring redesign.</text>']
for col,l in enumerate(layouts):
    x0=25+col*495
    svg.extend([f'<rect x="{x0}" y="94" width="475" height="796" rx="12" fill="white" stroke="#cbd5df"/>',f'<text x="{x0+15}" y="125" font-size="18">{l["id"]} · {l["title"]}</text>',f'<text x="{x0+15}" y="154" font-size="16">Total widening {l["selectedTotalWideningMm"]}mm; each leg +{l["legShiftPerSideMm"]}mm</text>'])
    for view,axes,center in [('front',(1,2),(x0+235,350)),('side',(0,2),(x0+235,650))]:
        scale=2.2 if view=='front' else 1.7
        def rect(bb,fill,opacity=1,dash=''):
            a,z=axes;xx=center[0]+scale*bb[0][a];yy=center[1]-scale*bb[1][z]
            return f'<rect x="{xx:.2f}" y="{yy:.2f}" width="{scale*(bb[1][a]-bb[0][a]):.2f}" height="{scale*(bb[1][z]-bb[0][z]):.2f}" fill="{fill}" opacity="{opacity}" stroke="#526372" stroke-width="1" stroke-dasharray="{dash}"/>'
        for key in ['motor5','motor10','motor4','motor9','hip','right_hip','thigh','right_thigh','power_support','regulator','torso_base']:
            bb=[q.copy() for q in parts[key]['bounds']]
            sign=-1 if key in ['motor5','motor4','right_hip','right_thigh'] else 1 if key in ['motor10','motor9','hip','thigh'] else 0
            for p in bb:p[1]+=sign*l['legShiftPerSideMm']
            svg.append(rect(bb,'#ccd4dd' if sign else '#e59991',.6 if sign else .35))
        svg.append(rect(l['bankBoundsMm'],'#78b8dc',.88))
        for port in l['ports']:svg.append(rect(port['boundsMm'],'#dfeef6',.45,'5 4'))
        label='FRONT: entire leg assemblies shifted laterally' if view=='front' else 'SIDE: dashed boxes = assumed 25mm end service space'
        svg.append(f'<text x="{x0+15}" y="{185 if view=="front" else 535}" font-size="14">{label}</text>')
    for y,txt in [(804,f'Battery X/Y/Z: {l["bankDimensionsXYZMm"]} mm'),(830,f'New yaw spacing {l["newYawAxisSpacingMm"]:.0f} / pitch spacing {l["newPitchAxisSpacingMm"]:.0f} mm'),(857,'Central frame, power relocation and motion checks still required')]:svg.append(f'<text x="{x0+15}" y="{y}" font-size="13">{txt}</text>')
svg.append('</g></svg>');(D/'central-battery-layouts.svg').write_text('\n'.join(svg))
print([(x['id'],x['selectedTotalWideningMm'])for x in layouts])
