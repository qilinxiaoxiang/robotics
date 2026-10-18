from pathlib import Path
import json,math,hashlib
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).parent;OLD=D.parents[1]/'roof-wiring-stage/motor-wires';route=next(x for x in json.loads((OLD/'routes.json').read_text())['routes'] if x['id']=='ttl-04-03')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def primitives(points,R=2.):
 pts=np.array(points,dtype=float);out=[];prev=pts[0];tans=[]
 for a,b,c in zip(pts,pts[1:],pts[2:]):
  u=(b-a)/np.linalg.norm(b-a);v=(c-b)/np.linalg.norm(c-b);ang=math.acos(np.clip(np.dot(u,v),-1,1));trim=R*math.tan(ang/2)
  assert trim<min(np.linalg.norm(b-a),np.linalg.norm(c-b)),(b,trim)
  e=b-u*trim;f=b+v*trim;n=np.cross(u,v);n/=np.linalg.norm(n);cen=e+np.cross(n,u)*R
  if np.linalg.norm(e-prev)>1e-7:out.append({'kind':'line','start':prev.tolist(),'end':e.tolist(),'lengthMm':float(np.linalg.norm(e-prev))})
  h=ang/2;rv=e-cen;mid=cen+rv*math.cos(h)+np.cross(n,rv)*math.sin(h)
  out.append({'kind':'arc','start':e.tolist(),'mid':mid.tolist(),'end':f.tolist(),'center':cen.tolist(),'normal':n.tolist(),'radiusMm':R,'sweepRadians':ang,'lengthMm':R*ang});prev=f
 if np.linalg.norm(pts[-1]-prev)>1e-7:out.append({'kind':'line','start':prev.tolist(),'end':pts[-1].tolist(),'lengthMm':float(np.linalg.norm(pts[-1]-prev))})
 # check joins are forward; corner trims must not overlap
 for p in out:
  if p['kind']=='line':assert np.linalg.norm(np.array(p['end'])-p['start'])>0
 return out
def sample(pr):
 pts=[];tans=[]
 for p in pr:
  a=np.array(p['start']);b=np.array(p['end']);N=max(2,math.ceil(p['lengthMm']/.15))
  for q in np.linspace(0,1,N,endpoint=False):
   if p['kind']=='line':v=b-a;point=a+q*v;t=v/np.linalg.norm(v)
   else:
    n=np.array(p['normal']);rv=a-p['center'];ang=p['sweepRadians']*q;rad=rv*math.cos(ang)+np.cross(n,rv)*math.sin(ang);point=np.array(p['center'])+rad;t=np.cross(n,rad)/p['radiusMm']
   pts.append(point);tans.append(t)
 pts.append(b);tans.append(tans[-1]);return np.array(pts),np.array(tans)
def tube(pts,tans):
 n=24;r=(.75+.003)/math.cos(math.pi/n);frames=[];old=np.array([0.,0.,1.])
 for t in tans:
  x=old-np.dot(old,t)*t
  if np.linalg.norm(x)<.1:x=np.cross(t,[0,1,0])
  x/=np.linalg.norm(x);frames.append(x);old=x
 v=[p+r*(math.cos(q)*x+math.sin(q)*np.cross(t,x)) for p,t,x in zip(pts,tans,frames) for q in np.arange(n)*2*math.pi/n];f=[]
 for i in range(len(pts)-1):
  for j in range(n):a=i*n+j;b=i*n+(j+1)%n;f.extend([[a,b,b+n],[a,b+n,a+n]])
 v.extend([pts[0],pts[-1]]);st=len(v)-2;en=st+1
 for j in range(n):f.extend([[st,(j+1)%n,j],[en,(len(pts)-1)*n+j,(len(pts)-1)*n+(j+1)%n]])
 m=trimesh.Trimesh(v,f,process=True);m.fix_normals();assert m.is_watertight and m.is_winding_consistent;return m
def solid(m):
 a=mf.Manifold(mf.Mesh64(np.ascontiguousarray(m.vertices,dtype=np.float64),np.ascontiguousarray(m.faces,dtype=np.uint64)));assert str(a.status())=='Error.NoError' and a.volume()>0;return a
rows=[];solids=[]
for i,k in enumerate([-1,0,1]):
 A=np.array(route['from']['shoulder'])+np.array(route['from']['width'])*k*2.5;B=np.array(route['to']['shoulder'])+np.array(route['to']['width'])*k*2.5
 yy=-33+k*1.6;xx=-12+k*1.6;zz=-32.5+k*1.6
 pts=[A,[xx,A[1],A[2]],[xx,yy,A[2]],[xx,yy,zz],[B[0],yy,zz],[B[0],-67.8,zz],[B[0],-67.8,B[2]],B]
 pr=primitives(pts);p,t=sample(pr);m=tube(p,t);f=D/f'local-04-03-wire-{i+1}.stl';m.export(f);a=solid(m);solids.append(a);hits=[];checked=[]
 for o in (OLD/'obstacles').glob('*.json'):
  ob=json.loads(o.read_text());bb=np.array(ob['expectedFinalBoundsMm'])
  if np.any(m.bounds[1]<bb[0])or np.any(bb[1]<m.bounds[0]):continue
  mesh=trimesh.load_mesh(ob['file'],process=True);mesh.apply_translation(ob.get('importTranslationMm',[0,0,0]));s=solid(mesh);cut=a^s;v=cut.volume();checked.append({'key':ob['key'],'sourceSha256':ob['sha256'],'validSolid':True,'overlapMm3':v})
  if v>1e-7:hits.append({'key':ob['key'],'volumeMm3':v,'bounds':list(cut.bounding_box())})
 rows.append({'id':i+1,'file':str(f.resolve()),'sha256':sha(f),'primitives':pr,'controlPoints':np.array(pts).tolist(),'centerlineLengthMm':sum(x['lengthMm']for x in pr),'source':route['from'],'target':route['to'],'wireSlot':k,'diameterMm':1.5,'bendRadiusMm':2,'nominalStockMm':180,'spareLengthModeled':False,'meshBoundsMm':m.bounds.tolist(),'collisions':hits,'checked':checked})
 print(i+1,rows[-1]['centerlineLengthMm'],hits,flush=True)
selfs=[]
for i in range(3):
 for j in range(i):selfs.append({'a':i+1,'b':j+1,'overlapMm3':(solids[i]^solids[j]).volume()})
r={'status':'local candidate not accepted harness','route':'ttl-04-03','sourceHashes':{str(OLD/'routes.json'):sha(OLD/'routes.json')},'radiusEvidence':'R2 explicit receiving assumption, not manufacturer minimum','diameterEvidence':'1.5mm unchanged receiving assumption','strands':rows,'wireWire':selfs,'allStaticClear':not any(x['collisions']for x in rows) and not any(x['overlapMm3']>1e-7 for x in selfs)}
(D/'local-route.json').write_text(json.dumps(r,indent=2));print('wireWire',selfs)
