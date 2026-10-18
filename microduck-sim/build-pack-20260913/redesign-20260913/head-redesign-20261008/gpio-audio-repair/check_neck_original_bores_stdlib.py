from pathlib import Path
import zipfile,xml.etree.ElementTree as E,json,math,hashlib,base64,struct
D=Path(__file__).resolve().parent;R=D.parent.parent;SIM=R.parents[1];src=SIM/'Microduck-build-tutorial/microduck3D打印.3mf';G=R/'leg-guide-20261006/full-build-data.json';data=json.loads(G.read_text());p=next(p for p in data['parts'] if p['key']=='neck_pitch');T=p['sourceTransformWorld'];ns={'m':'http://schemas.microsoft.com/3dmanufacturing/core/2015/02'}
with zipfile.ZipFile(src) as z:
 raw=z.read('3D/Objects/object_19.model');root=E.fromstring(raw);o=next(o for o in root.findall('m:resources/m:object',ns) if o.get('id')=='27');m=o.find('m:mesh',ns);vv=[[float(v.get(k)) for k in ['x','y','z']] for v in m.findall('m:vertices/m:vertex',ns)];ff=[[int(f.get(k)) for k in ['v1','v2','v3']] for f in m.findall('m:triangles/m:triangle',ns)]
v=[[sum(T[i][k]*v[k] for k in range(3))+T[i][3] for i in range(3)] for v in vv]
def hits(x,y,vertices=v,faces=ff):
 out=[]
 for f in faces:
  a,b,c=[vertices[i] for i in f];den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
  if abs(den)<1e-12:continue
  u=((b[1]-c[1])*(x-c[0])+(c[0]-b[0])*(y-c[1]))/den;w=((c[1]-a[1])*(x-c[0])+(a[0]-c[0])*(y-c[1]))/den;t=1-u-w
  if min(u,w,t)>=-1e-8:out.append(u*a[2]+w*b[2]+t*c[2])
 out=sorted(out);return [x for i,x in enumerate(out) if not i or x-out[i-1]>1e-5]
dv=list(struct.iter_unpack('<fff',base64.b64decode(p['positionB64'])));df=list(struct.iter_unpack('<III',base64.b64decode(p['indexB64'])));rows=[]
for s in data['screws']:
 if not s['id'].startswith('S13-horn-'):continue
 x,y,z=s['world_center_mm'];rr=[]
 for dx,dy in [[.137,.223],[-.319,.197],[.241,-.293]]:
  sourcehits=hits(x+dx,y+dy);guidehits=hits(x+dx,y+dy,dv,df);rr.append({'offsetXYMm':[dx,dy],'original3mfWorldZCrossingsMm':sourcehits,'guideWorldZCrossingsMm':guidehits,'membraneThicknessMm':sourcehits[-1]-sourcehits[-2] if len(sourcehits)>=2 else None})
 faces=[]
 for radius in [1.21,1.5,1.75,1.99,2.49]:
  for i in range(48):
   ang=(i+.123)*2*math.pi/48;hh=hits(x+radius*math.cos(ang),y+radius*math.sin(ang));faces.append({'r':radius,'angle':ang,'minimumSourceWorldZMm':min(hh) if hh else None,'washerIntervalCollisionMm':sum(max(0,min(hh[j+1],z-1e-5)-max(hh[j],z-1)) for j in range(0,len(hh)-1,2))})
 rows.append({'id':s['id'],'headSeatWorldZMm':z,'sourceBoreRays':rr,'annularSeatSamples':len(faces),'annularSourceSurfaceZRangeMm':[min(r['minimumSourceWorldZMm'] for r in faces if r['minimumSourceWorldZMm'] is not None),max(r['minimumSourceWorldZMm'] for r in faces if r['minimumSourceWorldZMm'] is not None)],'spacerIntervalSampleCollisionsByRadius':{str(rad):{'count':sum(f['washerIntervalCollisionMm']>1e-5 for f in faces if f['r']==rad),'maxRayIntersectionLengthMm':max(f['washerIntervalCollisionMm'] for f in faces if f['r']==rad)} for rad in [1.21,1.5,1.75,1.99,2.49]},'missingAnnularSourceRays':sum(r['minimumSourceWorldZMm'] is None for r in faces),'M2x6EntryWith1mmSpacerMm':6-max(s['stack_mm'])-1,'M2x6EntryWith0p5mmSpacerMm':6-max(s['stack_mm'])-.5})
out={'CADExecuted':False,'method':'Direct original3MF XML triangle/vertical-line intersections using stdlib, no CAD export, meshing, booleans or source repair. Original top-levelobject28 uses object27 inobject_19.model with identitycomponenttransform. World transform is rigid from canonical guide.','originalSourceSha256':hashlib.sha256(src.read_bytes()).hexdigest(),'originalObjectXmlSha256':hashlib.sha256(raw).hexdigest(),'sourceDataSha256':hashlib.sha256(G.read_bytes()).hexdigest(),'rows':rows,'physicalFitVerified':False}
(D/'neck-original-bore-source-review.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
