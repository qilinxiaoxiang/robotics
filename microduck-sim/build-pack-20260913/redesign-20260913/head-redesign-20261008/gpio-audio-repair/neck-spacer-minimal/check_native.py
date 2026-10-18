"""Read actual native G-code: all model extrusion segments, including G2/G3 arcs.
Full-circle radial lower bound is conservative for each native arc subset.
"""
from pathlib import Path
import json,zipfile,hashlib,re,math
D=Path(__file__).resolve().parent
p=D/'native/Neck_spacers_native.3mf'
with zipfile.ZipFile(p) as z: raw=z.read('Metadata/plate_1.gcode');cfg=json.loads(z.read('Metadata/project_settings.config'))
code=raw.decode();assert re.search(r'^M83\b',code,re.M)
positions=json.loads((D/'geometry-report.json').read_text())['positionsXYMm']
state={'X':0.,'Y':0.,'Z':0.};obj=None;kind='Custom';width=None;rows={};support=[]
for line in code.splitlines():
 if line.startswith('EXCLUDE_OBJECT_START'):
  obj=int(re.search(r'neck_spacer_(\d)',line)[1]);continue
 if line.startswith('EXCLUDE_OBJECT_END'):obj=None;continue
 if line.startswith(';TYPE:'):kind=line.split(':',1)[1];continue
 if line.startswith(';WIDTH:'):width=float(line.split(':',1)[1]);continue
 main=line.split(';')[0];tokens=main.split()
 if not tokens or tokens[0] not in ('G0','G1','G2','G3'):continue
 vals={k:float(v) for k,v in re.findall(r'\b([XYZEIJ])(-?(?:\d+(?:\.\d*)?|\.\d+))',main)}
 old=dict(state);state.update({k:vals[k] for k in ('X','Y','Z') if k in vals})
 if not obj or vals.get('E',0)<=0 or not any(k in vals for k in ('X','Y')) or kind=='Custom':continue
 assert width and abs(state['Z']-old['Z'])<1e-8
 z=round(state['Z'],5);k=(obj,z);cx,cy=positions[obj-1]
 row=rows.setdefault(k,{'object':obj,'z':z,'segments':0,'openDiameterLowerBoundMm':100.,'outerWallTravelMm':0.,'supportSegments':0})
 ax,ay=old['X']-cx,old['Y']-cy;bx,by=state['X']-cx,state['Y']-cy
 if tokens[0] in ('G2','G3'):
  ox,oy=ax+vals.get('I',0),ay+vals.get('J',0);radius=math.hypot(ax-ox,ay-oy)
  # Rounding at native arc endpoint can change radius slightly; take minimum.
  radius2=math.hypot(bx-ox,by-oy);radial=max(0,min(radius,radius2)-math.hypot(ox,oy))
  a=math.atan2(ay-oy,ax-ox);b=math.atan2(by-oy,bx-ox);sweep=(b-a)%(2*math.pi) if tokens[0]=='G3' else (a-b)%(2*math.pi)
  length=sweep*radius
 else:
  dx,dy=bx-ax,by-ay;l2=dx*dx+dy*dy;t=max(0,min(1,-(ax*dx+ay*dy)/l2)) if l2 else 0
  radial=math.hypot(ax+t*dx,ay+t*dy);length=math.sqrt(l2)
 open_diam=2*(radial-width/2-.002) # conservative 0.002 mm native decimal allowance
 row['openDiameterLowerBoundMm']=min(row['openDiameterLowerBoundMm'],open_diam);row['segments']+=1
 if kind=='Outer wall':row['outerWallTravelMm']+=length
 if 'support' in kind.lower():row['supportSegments']+=1;support.append(line)
assert len(rows)==20 and {z for _,z in rows}=={.2,.4,.6,.8,1.}
for row in rows.values():
 assert row['openDiameterLowerBoundMm']>2.0,row
 assert row['outerWallTravelMm']>18,row
 assert row['supportSegments']==0,row
assert not support
report={'passed':True,'sourceSha256':hashlib.sha256(p.read_bytes()).hexdigest(),'gcodeSha256':hashlib.sha256(raw).hexdigest(),'scriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'nativeSlicer':'OrcaSlicer 2.4.2','printerProfile':cfg['printer_settings_id'],'material':'Black PLA','quantity':4,'layerCountEach':5,'layerZMm':[.2,.4,.6,.8,1.],'minimumOpenHoleDiameterLowerBoundMm':min(r['openDiameterLowerBoundMm'] for r in rows.values()),'supportSegments':0,'rows':list(rows.values()),'method':'All positive-E G1/G2/G3 model paths checked. Native width/2 and 0.002mm numerical allowance subtracted. Full circle bound for an arc is conservative. Every layer has >18mm outer-wall extrusion and an unobstructed centered disk >2mm.','boundary':'Digital bead-width readback is not a physical tolerance or printed compression/creep test.'}
(D/'native-functional-report.json').write_text(json.dumps(report,indent=2)+'\n')
manifest={'integrationReady':True,'parts':[{'key':'neck_M2_spacer','source':str(D/'neck-M2-spacer-OD4-ID2p2-T1.stl'),'sha256':json.loads((D/'geometry-report.json').read_text())['sourceSha256'],'quantity':4,'color':'Black','printRotationMatrix':[[1,0,0],[0,1,0],[0,0,1]],'description':'OD4 / ID2.2 / thickness1 mm independent head-under spacer. Keep original neck_pitch.','fasteningStack':'Four original S13-horn-041..044 M2×6; spacer1mm + original2.89956mm seat => nominal insertion2.10044mm. Clear source0.2mm membrane in detached original bracket before assembly.','physicalBoundary':'Verify printed fit and seat flatness before tightening; no claim matching metal washer stock exists.'}],'nativeReport':str(D/'native-functional-report.json'),'nativeReportSha256':hashlib.sha256((D/'native-functional-report.json').read_bytes()).hexdigest(),'delivery':'Include four copies in final common Black plate; diagnostic four-copy plate is evidence only.'}
(D/'print-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
