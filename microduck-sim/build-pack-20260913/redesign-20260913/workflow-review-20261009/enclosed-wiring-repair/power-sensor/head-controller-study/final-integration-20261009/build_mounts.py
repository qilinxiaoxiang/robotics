from pathlib import Path
import json,hashlib,cadquery as cq
F=Path(__file__).resolve().parent;r=json.loads((F/'custom-harness-package.json').read_text());P=r['piCurrentWorldDelta'];I=[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]];parts=[];features=[]
def move(s,M):
 return s.rotate((0,0,0),(0,1,0),100).translate(tuple(row[3] for row in M[:3]))
def cyl(p,n,R,L):return cq.Solid.makeCylinder(R,L,cq.Vector(*p),cq.Vector(*n))
def save(key,s,meta):
 assert s.isValid();p=F/(key+'.step');cq.exporters.export(s,str(p));m=F/(key+'.stl');cq.exporters.export(s,str(m),tolerance=.02,angularTolerance=.1)
 parts.append({'key':key,'file':str(m),'sha256':hashlib.sha256(m.read_bytes()).hexdigest(),'worldTransform':I,'group':'mounts','geometryKind':'native_parametric_mount','nativeStep':str(p),'nativeStepSha256':hashlib.sha256(p.read_bytes()).hexdigest()});features.append(dict(key=key,**meta))
for i,q in enumerate(json.loads((F/'mount-datum-rays.json').read_text())['controller']):
 p=q['seat'];n=q['outwardBossAxis'];L=q['capRayDistances'][0]+.7;s=cyl(p,n,2.3,L).cut(cyl(p,n,.85,4.9));save(f'controller-roof-boss-{i}',s,{'seat':p,'axis':n,'lengthMm':L,'pilotDepthMm':4.9,'fastener':'M2x6 TAP; PCB1.6mm +4.4mm nominal engagement','capUnionDepthMm':.7})
for i,q in enumerate(json.loads((F/'pi-mount-roof-rays.json').read_text())['rows']):
 y=q['sourceY']
 rail=cq.Solid.makeBox(29,3.2,2,cq.Vector(44.5,y-1.6,126.3));seatmeta=[]
 for x in [47.5,70.5]:
  rail=rail.fuse(cyl([x,y,126.3],[0,0,1],3.2,4.4));rail=rail.cut(cyl([x,y,125.9],[0,0,1],.85,4.81));seatmeta.append(q['seats'][0 if x==47.5 else 1])
 rail=move(rail,P);p=q['origin'];rail=rail.fuse(cyl(p,[0,0,1],2.4,q['roofPostLengthMm']));save(f'pi-roof-side-rail-{i}',rail,{'seats':seatmeta,'pilotDepthMm':4.8,'fastener':'2 M2x6 TAP per rail; PCB1.6 +4.4 nominal engagement','roofPostOrigin':p,'roofPostLengthMm':q['roofPostLengthMm']})
r['parts']+=parts;r['mountFeatures']=features;r['stage']='Full rigid receiving candidate with native mount additions. Cap union, assembly paths, remaining harness not accepted.';(F/'mounted-package.json').write_text(json.dumps(r,indent=2)+'\n');(F/'mount-design.json').write_text(json.dumps({'features':features,'parts':parts,'manufacturingAccepted':False},indent=2));s=(F/'check_package.py').read_text().replace("src=F/'joint-package.json'","src=F/'mounted-package.json'").replace("'joint-check-'","'mounted-check-'");(F/'check_mounted.py').write_text(s);print(json.dumps(features,indent=2))
