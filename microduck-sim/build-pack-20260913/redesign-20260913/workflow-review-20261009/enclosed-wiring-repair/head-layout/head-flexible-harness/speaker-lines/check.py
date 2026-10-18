from pathlib import Path
import os,json,hashlib,ast,types,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
D=Path(__file__).resolve().parent; NEW=D.parents[2]; R=NEW.parents[1];H=R/'head-redesign-20261008';F=NEW/'power-sensor/head-controller-study/final-integration-20261009';SRC=F/'integrated-rigid-package.json'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
base=H/'gpio-audio-repair/check_speaker_rewire.py';tree=ast.parse(base.read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='tube');ns={'c':types.SimpleNamespace(np=np,tm=tm,mf=mf)};exec(compile(ast.Module(body=[node],type_ignores=[]),str(base),'exec'),ns);tube=ns['tube']
def load(row):
 assert sha(row['file'])==row['sha256'];m=tm.load(row['file'],force='mesh');m.apply_transform(row['worldTransform']);s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)));assert s.status()==mf.Error.NoError,(row['key'],s.status());return s
def fillet(points,r=2):
 p=np.asarray(points,float);out=[p[0]]
 for i in range(1,len(p)-1):
  a=p[i]-p[i-1];b=p[i+1]-p[i];la=np.linalg.norm(a);lb=np.linalg.norm(b);a/=la;b/=lb;angle=np.arccos(np.clip(np.dot(a,b),-1,1));d=r*np.tan(angle/2);assert d<min(la if i==1 else la/2,lb if i==len(p)-2 else lb/2),(i,d,la,lb)
  start=p[i]-d*a;end=p[i]+d*b;n=b-np.dot(b,a)*a;n/=np.linalg.norm(n);center=start+r*n;out.append(start)
  for t in np.linspace(0,angle,max(5,int(angle*r/.15)))[1:]:out.append(center+r*(-n*np.cos(t)+a*np.sin(t)))
 out.append(p[-1]);return np.array(out)
routes=[]
for i,(x,y) in enumerate([(24.3,-26.27),(27.8,-16.73)]):
 p=np.array([x,14.203,136.285]);end=[36.06,y,135.35]
 rr=2.0 if i==0 else 1.2;zz=132.1 if i==0 else 133.8
 pts=[p+np.array([0,-rr*np.sin(t),-rr*(1-np.cos(t))])for t in np.linspace(0,np.pi/2,33)]
 a=pts[-1];xx=47.795 if i==0 else 50.235
 side=52.8 if i==0 else xx
 nodes=[a,[x,a[1],zz],[xx,a[1],zz]]
 if i==0:nodes += [[xx,-13.2,zz],[side,-13.2,zz]]
 nodes += [[side,y,zz],[side,y,139.0],[36.06,y,139.0],end]
 tail=fillet(nodes,1.2)
 pts=np.vstack([pts,tail[1:]]);lens=np.linalg.norm(np.diff(pts,axis=0),axis=1);arcs=np.r_[0,np.cumsum(lens)];cut=arcs[-1]-2.;j=np.searchsorted(arcs,cut)-1;mid=pts[j]+(pts[j+1]-pts[j])*(cut-arcs[j])/lens[j]
 ins=np.vstack([pts[:j+1],mid]);bare=np.vstack([mid,pts[j+1:]]);s=tube(ins,.75)+tube(bare,.175)
 routes.append({'net':'VO+'if i==0 else'VO-','start':p.tolist(),'end':end,'centerlineMm':pts.tolist(),'lengthMm':float(arcs[-1]),'insulationDiameterReceivingMm':1.5,'terminalBareLengthMm':2,'conductorDiameterReceivingMm':.35,'solid':s})
checks=[]
for row in json.loads(SRC.read_text())['parts']:
 ob=load(row)
 if row['key']=='current_amp':ob=ob.translate([0,1,-1.5])
 b=np.array(ob.bounding_box()).reshape(2,3)
 for route in routes:
  s=route['solid'];a=np.array(s.bounding_box()).reshape(2,3);v=0 if np.any(a[1]<b[0])or np.any(b[1]<a[0])else max(0,(s^ob).volume());raw=s^ob if v else None;outside=v
  if v and row['key']=='current_amp':outside=max(0,(raw-mf.Manifold.cube([2,2,2],True).translate(route['start'])).volume())
  if v and row['key']=='REFERENCE current speaker':outside=max(0,(raw-mf.Manifold.cube([3.4,3.4,2.6],True).translate(route['end'])).volume())
  checks.append({'wire':route['net'],'obstacle':row['key'],'volumeMm3':v,'outsideInterfaceMm3':outside,'bounds':list(raw.bounding_box())if v else None})
 del ob;gc.collect()
wirePairVolume=max(0,(routes[0]['solid']^routes[1]['solid']).volume())
for route in routes:
 s=route.pop('solid');m=s.to_mesh64();p=D/(route['net'].replace('+','plus').replace('-','minus')+'.stl');p.write_text(tm.exchange.stl.export_stl_ascii(tm.Trimesh(np.asarray(m.vert_properties)[:,:3],np.asarray(m.tri_verts),process=False)));route.update(file=str(p),sha256=sha(p))
r={'sourceManifest':str(SRC),'sourceSha256':sha(SRC),'scriptSha256':sha(__file__),'routes':routes,'wirePairVolumeMm3':wirePairVolume,'checks':checks,'hits':[q for q in checks if q['outsideInterfaceMm3']>1e-6],'wholeHeadAccepted':False};(D/'check.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'lengths':[q['lengthMm']for q in routes],'hits':r['hits']},indent=2))
