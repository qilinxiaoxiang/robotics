"""Existing side corridor; exact tangent line/arc primitives, no interpolation optimizer."""
from pathlib import Path
import json,math,hashlib,ast
import numpy as np,trimesh,manifold3d as mf
D=Path(__file__).parent;O=D.parents[1]/'roof-wiring-stage/motor-wires/obstacles'
src=(D/'local_route.py').read_text();tree=ast.parse(src)
for node in tree.body:
 if isinstance(node,ast.FunctionDef)and node.name in ['primitives','sample','tube','solid']:
  code=ast.get_source_segment(src,node)
  if node.name=='primitives':code=code.replace('R=(4. if ix in [3,4,5] else 2.)','R=(4. if ix in [4,5] else 2.)')
  exec(code)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
top=json.loads((D/'active-topology.json').read_text());r=next(r for r in top['routes']if r['id']=='ttl-05-04');fr=top['ports'][r['fromPort']];to=top['ports'][r['toPort']];rows=[];solids=[]
for i,k in enumerate([-1,0,1]):
 A=np.array(fr['shoulder'])+np.array(fr['width'])*2.5*k;B=np.array(to['shoulder'])+np.array(to['width'])*2.5*k;Y=-18.+k*2.;Z=28.+k*2.
 def controls(X):return [A,[A[0],A[1],Z],[A[0],Y,Z],[-20.,Y,Z],[-20.,Y,6.],[X,Y,6.],[X,Y,B[2]],[-17.+k*2,Y,B[2]],[-17.+k*2,B[1],B[2]],B]
 X=-40.;ps=primitives(controls(X));X-=(180-sum(p['lengthMm']for p in ps))/2;ps=primitives(controls(X));pts,tans=sample(ps);m=tube(pts,tans);a=solid(m);solids.append(a);f=D/f'hip-05-04-wire-{i+1}.stl';m.export(f);checks=[]
 for p in O.glob('*.json'):
  ob=json.loads(p.read_text());bb=np.array(ob['expectedFinalBoundsMm'])
  if np.any(m.bounds[1]<bb[0])or np.any(bb[1]<m.bounds[0]):continue
  mm=trimesh.load_mesh(ob['file']);mm.apply_translation(ob.get('importTranslationMm',[0,0,0]));cut=a^solid(mm);v=cut.volume();checks.append({'key':ob['key'],'sourceSha256':ob['sha256'],'overlapMm3':v,'bounds':list(cut.bounding_box())if v>1e-7 else None})
 for j in range(1,4):
  p=D/f'local-04-03-wire-{j}.stl';cut=a^solid(trimesh.load_mesh(p));checks.append({'key':p.name,'sourceSha256':sha(p),'overlapMm3':cut.volume()})
 rows.append({'id':i+1,'file':str(f),'sha256':sha(f),'primitives':ps,'centerlineLengthMm':sum(p['lengthMm']for p in ps),'source':fr,'target':to,'checks':checks});print(i+1,[(x['key'],x['overlapMm3'],x.get('bounds')) for x in checks if x['overlapMm3']>1e-7],flush=True)
selfs=[{'a':i+1,'b':j+1,'overlapMm3':(a^b).volume()}for i,a in enumerate(solids)for j,b in enumerate(solids)if i<j];print('self',selfs)
(D/'hip-05-04.json').write_text(json.dumps({'status':'candidate','routeId':r['id'],'sourceHashes':{str(D/'active-topology.json'):sha(D/'active-topology.json')},'radiusMm':4,'radiusEvidence':'receiving design assumption, not manufacturer flex rating','wireDiameterMm':1.5,'strands':rows,'wireWire':selfs,'staticPassed':all(x['overlapMm3']<1e-7 for w in rows for x in w['checks'])and all(x['overlapMm3']<1e-7 for x in selfs)},indent=2))
