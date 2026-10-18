from pathlib import Path
import os,json,zipfile,xml.etree.ElementTree as E,re,hashlib,math,sys
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm
from shapely.geometry import LineString,Point,Polygon
D=Path(__file__).resolve().parent;R=D.parents[3];P=R/'printing/12-REPAIR-V1-20261008';Q='{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
archive=D/'Black_V1_11_native.3mf';project=P/'staging-projects/MicroDuck_Elegoo_Black_ASSEMBLY_editable.3mf';ori={r['key']:r for r in json.loads((P/'orientation-preparation.json').read_text())['parts'] if r['color']=='Black'}
with zipfile.ZipFile(archive) as z:raw=z.read('Metadata/plate_1.gcode');nativecfg=json.loads(z.read('Metadata/project_settings.config'));pngs=[n for n in z.namelist() if n.endswith('.png')]
raw=(D/'Black_V1_11_GUI.gcode').read_bytes()
with zipfile.ZipFile(project)as z:model=E.fromstring(z.read('3D/3dmodel.model'));cfg=json.loads(z.read('Metadata/project_settings.config'))
meshes={};geom=[]
for obj in model.find(Q+'resources'):
 name=obj.get('name');m=obj.find(Q+'mesh');v=np.array([[float(p.get(k))for k in ('x','y','z')]for p in m.find(Q+'vertices')]);f=np.array([[int(p.get(k))for k in ('v1','v2','v3')]for p in m.find(Q+'triangles')]);r=ori[name];src=R/r['source'];assert sha(src)==r['sourceSha256'];a=tm.load(src,force='mesh').apply_transform(r['printTransform']);assert np.array_equal(f,a.faces)and np.max(abs(v-a.vertices))<1e-7
 a.apply_translation([*r['placementXYMm'],0]);meshes[name]=a;geom.append({'key':name,'sourceSha256':sha(src),'sameFacesAndVertices':True})
code=raw.decode();x=y=z=0.;kind='Custom';width=.42;height=.2;cur=None;paths={}
for line in code.splitlines():
 if line.startswith('EXCLUDE_OBJECT_START'):cur=re.search(r'NAME=(.+)_id_',line)[1]
 elif line.startswith('EXCLUDE_OBJECT_END'):cur=None
 elif line.startswith(';TYPE:'):kind=line[6:].strip()
 elif line.startswith(';WIDTH:'):width=float(line[7:])
 elif line.startswith(';HEIGHT:'):height=float(line[8:])
 if not re.match(r'^G[0123] ',line):continue
 cmd=line.split()[0];v={k:float(a)for k,a in re.findall(r'([XYZEIJ])([-+]?\d*\.?\d+)',line.split(';')[0])};xx=v.get('X',x);yy=v.get('Y',y);zz=v.get('Z',z);pts=[(x,y),(xx,yy)]
 if cmd in ('G2','G3')and('I'in v or'J'in v):
  cx=x+v.get('I',0);cy=y+v.get('J',0);rr=math.hypot(x-cx,y-cy);a=math.atan2(y-cy,x-cx);b=math.atan2(yy-cy,xx-cx);sg=1 if cmd=='G3'else-1;span=((b-a)*sg)%(2*math.pi) or 2*math.pi;n=max(1,math.ceil(span/max(.001,2*math.acos(max(-1,min(1,1-.003/max(rr,.003)))))));pts=[(cx+rr*math.cos(a+sg*span*i/n),cy+rr*math.sin(a+sg*span*i/n))for i in range(n+1)];pts[0]=(x,y);pts[-1]=(xx,yy)
 if cur and kind!='Custom'and v.get('E',0)>0 and(xx!=x or yy!=y):paths.setdefault((cur,round(zz,5)),[]).append((LineString(pts),width,kind,height))
 x,y,z=xx,yy,zz
# Source-defined closed small-hole loops, all actual printed layers. Bound every
# native bead against each hole center; keep support in larger removable cavities separate.
rows=[]
for (name,z),segments in paths.items():
 section=meshes[name].section(plane_origin=[0,0,z-segments[0][3]/2],plane_normal=[0,0,1])
 if section is None:continue
 polys=[]
 for d in section.discrete:
  if np.linalg.norm(d[0]-d[-1])>1e-5:continue
  p=Polygon(d[:,:2]);
  if p.is_valid and p.area>1e-5:polys.append(p)
 for hole in polys:
  q=hole.representative_point();depth=sum(other.area>hole.area and other.contains(q)for other in polys)
  if depth%2!=1:continue
  extent=(hole.bounds[2]-hole.bounds[0],hole.bounds[3]-hole.bounds[1]);
  if min(extent)<1 or max(extent)>6:continue
  center=hole.centroid;sourceRadius=center.distance(hole.boundary)
  vals=[(line.distance(center)-w/2-.004,kind)for line,w,kind,h in segments]
  best=min(v[0]for v in vals);support=min((v[0]for v in vals if 'support'in v[1].lower()),default=None)
  rows.append({'part':name,'layerZ':z,'centerXY':[center.x,center.y],'sourceCenteredOpenDiameter':2*sourceRadius,'nativeOpenDiameterLowerBound':2*best,'supportCoreIntrusion':support is not None and support<sourceRadius-.3})
counts={k:len([a for a,z in paths if a==k])for k in meshes};spacers=[r for r in rows if r['part'].startswith('neck_m2_spacer')];assert len(spacers)==36 and all(r['nativeOpenDiameterLowerBound']>2 for r in spacers)
ret=[r for r in rows if r['part']=='camera_retainer'];issues=[r for r in rows if r['supportCoreIntrusion'] or r['nativeOpenDiameterLowerBound']<r['sourceCenteredOpenDiameter']-.35]
audit=json.loads((D/'native-audit-GUI-stream.json').read_text());assert audit['objectCount']==11 and audit['passed']
report={'nativeSlicePassed':True,'geometrySourcePreserved':geom,'archiveSha256':sha(archive),'projectSha256':sha(project),'gcodeSha256':hashlib.sha256(raw).hexdigest(),'objectCount':len(meshes),'extrudingObjectCount':len(counts),'extrusionZPlaneCountsIncludingSupport':counts,'modelLayerCounts':{k:len([1 for (name,z),segs in paths.items() if name==k and any('support' not in seg[2].lower() for seg in segs)]) for k in meshes},'smallHoleLayerChecks':rows,'smallHoleIssues':issues,'functionalHoleScreenPassed':not issues,'spacerMinOpenDiameterMm':min(r['nativeOpenDiameterLowerBound']for r in spacers),'thumbnailPresent':bool(pngs)or'thumbnail begin'in code,'machineReady':False,'machineReadyBoundary':'Native GUI export present; digital prototype. Small vertical source-hole screen does not certify horizontal bearing support removal or full hardware fit.','sourceScope':'Source topology and all vertices preserved under recorded rigid print transforms; jaw_support_original has identity rotation.','auditSha256':sha(D/'native-audit-GUI-stream.json')}
(D/'functional-readback.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items()if k not in('smallHoleLayerChecks','geometrySourcePreserved','smallHoleIssues')},indent=2));print('hole_rows',len(rows),'issues',len(issues),'retainer_rows',len(ret));print(json.dumps(issues[:5]))
