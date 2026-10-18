"""A compact coil in the measured rear-of-motor pocket; fixed primitives, scalar length solve."""
exec(__import__('pathlib').Path('hip_core.py').read_text().split('top=json')[0])
# Override corner radii with explicit entry-only tangent arcs.
code=ast.get_source_segment(src,next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='primitives')).replace('R=(4. if ix in [3,4,5] else 2.)','R=2.');exec(code)
import sys
side=sys.argv[1]if len(sys.argv)>1 else 'right';sgn=-1 if side=='right' else 1;rid='ttl-05-04' if side=='right' else 'ttl-10-09'
top=json.loads((D/'active-topology.json').read_text());rr=next(r for r in top['routes']if r['id']==rid);fr=top['ports'][rr['fromPort']];to=top['ports'][rr['toPort']]
R=4.5;cx=-14.3;cy=-17.;turn=5.5*math.pi;delta=.8;h=5.7/(2*math.pi);drop=h*(turn-delta)
def helix(phi,z):
 phi=np.asarray(phi);u=phi-(turn-delta)
 integ=np.where(phi<delta,phi/2-delta/(2*math.pi)*np.sin(math.pi*phi/delta),np.where(phi<=turn-delta,phi-delta/2,turn-1.5*delta+u/2+delta/(2*math.pi)*np.sin(math.pi*u/delta)))
 ramp=np.where(phi<delta,(1-np.cos(math.pi*phi/delta))/2,np.where(phi<=turn-delta,1.,(1+np.cos(math.pi*u/delta))/2))
 p=np.array([cx+R*np.cos(phi),cy-R*np.sin(phi),z-h*integ]).T;v=np.array([-R*np.sin(phi),-R*np.cos(phi),-h*ramp]).T;v/=np.linalg.norm(v,axis=1)[:,None];return p,v

def bez(P,t):
 t=np.asarray(t)[:,None];p=(1-t)**3*P[0]+3*(1-t)**2*t*P[1]+3*(1-t)*t*t*P[2]+t**3*P[3];v=3*(1-t)**2*(P[1]-P[0])+6*(1-t)*t*(P[2]-P[1])+3*t*t*(P[3]-P[2]);return p,v/np.linalg.norm(v,axis=1)[:,None]
def length(points):return float(np.linalg.norm(np.diff(points,axis=0),axis=1).sum())
rows=[];solids=[]
for i,k in enumerate([-1,0,1]):
 A=np.array(fr['shoulder'])+np.array(fr['width'])*k*2.5;B=np.array(to['shoulder'])+np.array(to['width'])*k*2.5
 # Work in negative-Y canonical pocket, reflect all constructed positions for left.
 if side=='left':A[1]*=-1;B[1]*=-1
 z=-26.5+drop+k*2;Y=-8+k*1.9;YC=-18+k*2;Z=31.8+k*2
 def construct(radius):
  global R
  R=radius;P0=np.array([cx+R,cy,z]);ep,et=helix(np.array([turn]),z);end=ep[0];Q=np.array([-7.5,B[1],B[2]]);C=np.array([end,end+[2.4,0,0],Q-[2.4,0,0],Q]);hp,ht=helix(np.linspace(0,turn,1801),z);bp,bt=bez(C,np.linspace(0,1,121));tail=np.array([Q,B]);tailt=np.repeat([[1.,0,0]],2,axis=0)
  denseh,_=helix(np.linspace(0,turn,14401),z);denseb,_=bez(C,np.linspace(0,1,9601));extra=length(denseh)+length(denseb)+np.linalg.norm(B-Q)
  controls=[A,[A[0],A[1],Z],[A[0],YC,Z],[-20.,YC,Z],[-20.,YC,z],[-20.,Y,z],[cx+R,Y,z],P0]
  pr=primitives(controls);return sum(p['lengthMm']for p in pr)+extra,(pr,extra,hp,ht,bp,bt,tail,tailt,C,Q)
 value,stuff=construct(3.8);Z+=(180-value)/2
 value,(pr,extra,hp,ht,bp,bt,tail,tailt,C,Q)=construct(3.8);pp,pt=sample(pr);points=np.concatenate([pp,hp[1:],bp[1:],tail[1:]]);tans=np.concatenate([pt,ht[1:],bt[1:],tailt[1:]])
 # Prefix sample returns duplicate last tangent; here the actual final line is -Y, matching coil.
 assert np.dot(pt[-1],ht[0])>.999999 and np.dot(ht[-1],bt[0])>.999999 and np.dot(bt[-1],tailt[0])>.999999
 if side=='left':points[:,1]*=-1;tans[:,1]*=-1
 m=tube(points,tans);a=solid(m);solids.append(a);f=D/f'hip-coiled-{side}-wire-{i+1}.stl';m.export(f);checks=[]
 for p in O.glob('*.json'):
  ob=json.loads(p.read_text());bb=np.array(ob['expectedFinalBoundsMm'])
  if np.any(m.bounds[1]<bb[0])or np.any(bb[1]<m.bounds[0]):continue
  mm=trimesh.load_mesh(ob['file']);mm.apply_translation(ob.get('importTranslationMm',[0,0,0]));cut=a^solid(mm);v=cut.volume();checks.append({'key':ob['key'],'sourceSha256':ob['sha256'],'overlapMm3':v,'bounds':list(cut.bounding_box())if v>1e-7 else None})
 for j in range(1,4):
  p=D/(f'local-04-03-wire-{j}.stl'if side=='right'else f'local-08-09-wire-{j}.stl');cut=a^solid(trimesh.load_mesh(p));checks.append({'key':p.name,'sourceSha256':sha(p),'overlapMm3':cut.volume()})
 rows.append({'id':i+1,'file':str(f),'sha256':sha(f),'upperZMm':Z,'nominalLengthMm':180,'computedLengthMm':sum(p['lengthMm']for p in pr)+extra,'prefixPrimitivesCanonical':pr,'coil':{'centerXY':[cx,cy],'radiusMm':R,'pitchMm':5.7,'sweepRadians':turn,'pitchRampRadians':delta,'startZMm':z},'exitBezierCanonical':C.tolist(),'exitLineCanonical':[Q.tolist(),B.tolist()],'reflectY':side=='left','centerlineMm':points.tolist(),'checks':checks});print(i+1,'upperZ',Z,[(x['key'],round(x['overlapMm3'],6),x.get('bounds'))for x in checks if x['overlapMm3']>1e-7],flush=True)
selfs=[{'a':i+1,'b':j+1,'overlapMm3':(a^b).volume()}for i,a in enumerate(solids)for j,b in enumerate(solids)if i<j];print('self',selfs)
(D/f'hip-coiled-{side}.json').write_text(json.dumps({'status':'candidate','routeId':rid,'sourceHashes':{str(D/'active-topology.json'):sha(D/'active-topology.json')},'diameterMm':1.5,'coilAssumption':'Round conductor receiving geometry; not manufacturer minimum bend/twist certification.3 full wires each180mm; no shortened stock.','strands':rows,'wireWire':selfs,'staticPassed':all(x['overlapMm3']<1e-7 for w in rows for x in w['checks'])and all(x['overlapMm3']<1e-7 for x in selfs)},indent=2))
