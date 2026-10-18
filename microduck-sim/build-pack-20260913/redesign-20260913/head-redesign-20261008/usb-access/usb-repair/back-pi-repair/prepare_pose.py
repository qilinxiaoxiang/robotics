from pathlib import Path
import argparse,json,hashlib
D=Path(__file__).resolve().parent;H=D.parents[2]
p=argparse.ArgumentParser();p.add_argument('--report',type=Path,default=H/'camera-ribbon-repair/occupancy-layout/back-ports-1/report.json');p.add_argument('--y-shift',type=float,default=0);p.add_argument('--case',default='back-ports-1');args=p.parse_args();C=D/args.case;C.mkdir(exist_ok=True)
r=json.loads(args.report.read_text());T=[q[:] for q in r['candidate']['worldTransform']];T[1][3]+=args.y_shift
# Shoulder is the source Pi USB board edge, matching generator's25x18x8 receiving body.
original=[64.2,8.9,146.0496];shoulder=[sum(T[i][j]*original[j] for j in range(3))+T[i][3] for i in range(3)]
pose={'integrationReady':False,'worldTransform':T,'usbShoulderWorldMm':shoulder,'usbOutwardAxis':[T[i][2] for i in range(3)],'sourceReport':str(args.report.resolve()),'sourceReportSha256':hashlib.sha256(args.report.read_bytes()).hexdigest(),'additionalYTranslationMm':args.y_shift,'boardPoseFrozen':False,'sourceShoulderBeforeTransformMm':original,'boardPortsAuthority':'Matches back-ports generator USB_body bounds; reuse owned SC0727 receiving connector, do not shrink.'}
pp=C/'pose.json';pp.write_text(json.dumps(pose,indent=2)+'\n')
spec={'status':'CANDIDATE_ONLY','poseFile':str(pp),'poseSha256':hashlib.sha256(pp.read_bytes()).hexdigest(),'cutStartMm':[shoulder[i]-.5*T[i][2] for i in range(3)],'axis':[T[i][2] for i in range(3)],'widthAxis':[T[i][0] for i in range(3)],'heightAxis':[T[i][1] for i in range(3)],'cutLengthMm':55.5,'cutWidthMm':9,'cutHeightMm':19,'sourcePlugReceivingMm':[25,18,8],'clearancePerSideMm':.5,'connectorEntryTravelMm':30,'accepted':False,'scope':'One cap local service opening, no existing hole reuse or roof cowl.'}
(C/'opening-spec.json').write_text(json.dumps(spec,indent=2)+'\n');print(json.dumps({'case':args.case,'shoulder':shoulder,'axis':pose['usbOutwardAxis']}))
