from pathlib import Path
import os,hashlib,json,zipfile,re,base64,io,math,sys,xml.etree.ElementTree as E
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm
from PIL import Image,ImageStat
from shapely.geometry import LineString,Point
D=Path(__file__).resolve().parent;R=D.parents[2];P=R/'printing/11-ASSEMBLY-REPAIR-20261008';Q='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
f=D/'Orange_speaker.gcode';code=f.read_text();project=D/'Orange_speaker_editable.3mf'
prep=[p for p in json.loads((P/'orientation-preparation.json').read_text())['parts'] if p['color']=='Orange'];assert {p['key'] for p in prep}=={'speaker_cradle','speaker_keeper'}
with zipfile.ZipFile(project) as z:
 model=E.fromstring(z.read('3D/3dmodel.model'));cfg=json.loads(z.read('Metadata/project_settings.config'))
for p,obj in zip(prep,model.find(Q+'resources').findall(Q+'object')):
 src=R/p['source'];assert sha(src)==p['sourceSha256'];m=tm.load(src,force='mesh').apply_transform(p['printTransform']);mesh=obj.find(Q+'mesh');v=np.array([[float(a.get(k)) for k in ('x','y','z')] for a in mesh.find(Q+'vertices')]);faces=np.array([[int(a.get(k)) for k in ('v1','v2','v3')] for a in mesh.find(Q+'triangles')]);assert np.array_equal(faces,m.faces) and np.max(abs(v-m.vertices))<1e-8
thumbs=[]
for hit in re.finditer(r'^; thumbnail begin (\d+)x(\d+) (\d+)\s*\n(.*?)^; thumbnail end\s*$',code,re.M|re.S):
 encoded=''.join(l[2:].strip() for l in hit[4].splitlines());assert len(encoded)==int(hit[3]);raw=base64.b64decode(encoded,validate=True);im=Image.open(io.BytesIO(raw));im.load();assert im.format=='PNG' and im.size==(int(hit[1]),int(hit[2])) and max(ImageStat.Stat(im.convert('RGB')).var)>1
 dest=D/f'native-thumbnail-{hit[1]}x{hit[2]}.png';dest.write_bytes(raw);thumbs.append({'size':list(im.size),'sha256':sha(dest),'path':str(dest)})
assert any(t['size']==[144,144] for t in thumbs)
headers=dict(re.findall(r'^; (\w+) = (.*)$',code,re.M));expected={'curr_bed_type':'Textured PEI Plate','filament_colour':'#FF8000','filament_type':'PLA','nozzle_diameter':'0.4','print_sequence':'by layer','printer_model':'Elegoo Centauri Carbon'}
assert all(headers.get(k)==v for k,v in expected.items())
sys.path.insert(0,str(R/'printing/04-FOUR-COLOR-20260929'));from audit_spacing import parse
spacing=parse(f)[0];assert spacing['passed_nonoverlap_and_inside_bed'] and spacing['object_count']==2
sys.path.insert(0,str(R/'printing/09-REPRINT-READY-20260930'));from native_tools import first_layer_summary
first=first_layer_summary(code);assert len(first)==2 and all(r['model_area_mm2']>200 and r['support_area_mm2']==0 for r in first)
# Actual bead disk-clearance at both through-holes on every extruding layer.
ports={p['key']:[(-16+p['printTransform'][0][3]+p['placementXYMm'][0],y+p['printTransform'][1][3]+p['placementXYMm'][1]) for y in (7,17)] for p in prep}
cur=None;kind='Custom';width=.5;x=y=z=0.;rows={};all_support=0
for line in code.splitlines():
 if line.startswith('EXCLUDE_OBJECT_START'):cur=re.search(r'NAME=(speaker_\w+)_id_',line)[1];continue
 if line.startswith('EXCLUDE_OBJECT_END'):cur=None;continue
 if line.startswith(';TYPE:'):kind=line[6:].strip();continue
 if line.startswith(';WIDTH:'):width=float(line[7:]);continue
 if not re.match(r'^G[0123] ',line):continue
 cmd=line.split()[0];v={k:float(t) for k,t in re.findall(r'([XYZEIJ])([-+]?\d*\.?\d+)',line.split(';')[0])};xx=v.get('X',x);yy=v.get('Y',y);zz=v.get('Z',z);pts=[(x,y),(xx,yy)]
 if cmd in ('G2','G3') and ('I'in v or 'J'in v):
  cx=x+v.get('I',0);cy=y+v.get('J',0);rad=math.hypot(x-cx,y-cy);a=math.atan2(y-cy,x-cx);b=math.atan2(yy-cy,xx-cx);sgn=1 if cmd=='G3' else -1;span=((b-a)*sgn)%(2*math.pi);span=span if span>1e-8 else 2*math.pi;step=2*math.acos(max(-1,min(1,1-.002/max(rad,.002))));n=max(1,math.ceil(span/max(step,.001)));pts=[(cx+rad*math.cos(a+sgn*span*i/n),cy+rad*math.sin(a+sgn*span*i/n)) for i in range(n+1)];pts[0]=(x,y);pts[-1]=(xx,yy)
 if cur and v.get('E',0)>0 and kind!='Custom' and (xx!=x or yy!=y):
  k=(cur,round(zz,4));r=rows.setdefault(k,{'part':cur,'z':round(zz,4),'openHoleDiametersLowerBoundMm':[999.,999.],'supportSegments':0,'extrudingSegments':0});r['extrudingSegments']+=1
  for j,p in enumerate(ports[cur]):r['openHoleDiametersLowerBoundMm'][j]=min(r['openHoleDiametersLowerBoundMm'][j],2*(LineString(pts).distance(Point(p))-width/2-.003))
  if 'support'in kind.lower():r['supportSegments']+=1;all_support+=1
 x,y,z=xx,yy,zz
counts={key:len([r for r in rows.values() if r['part']==key]) for key in ports};assert counts=={'speaker_cradle':6,'speaker_keeper':5},counts
assert all(min(r['openHoleDiametersLowerBoundMm'])>2.5 for r in rows.values()),list(rows.values());assert all_support==0
report={'passed':True,'scope':'Two frozen speaker parts only; not a complete Orange plate handoff until head cap integration.','gcode':str(f),'gcodeSha256':sha(f),'editableProjectSha256':sha(project),'geometrySourcePreserved':True,'parts':prep,'nativeGuiObserved':'Orca Preview displayed two ring parts; Export G-code file completed with successful export notice.','nativeThumbnails':thumbs,'profileChecks':expected,'spacing':spacing,'firstLayer':first,'functionalLayers':list(rows.values()),'layerCount':counts,'supportSegments':all_support,'minimumThroughHoleDiameterLowerBoundMm':min(min(r['openHoleDiametersLowerBoundMm'])for r in rows.values()),'numericalMethod':'Actual G1/G2/G3 paths, maximum arc sagitta0.002mm, native bead width/2 plus .003mm allowance.','scriptSha256':sha(Path(__file__)),'physicalBoundary':'Native export and digital toolpath acceptance; no physical print/fit assertion.'}
(D/'native-export-acceptance.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k not in ('parts','functionalLayers','spacing','firstLayer')},indent=2))
