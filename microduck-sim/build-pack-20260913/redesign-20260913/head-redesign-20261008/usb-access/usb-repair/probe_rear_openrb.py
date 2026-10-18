"""Bounded feasibility screen: move OpenRB to the existing four rear-cover bosses."""
from pathlib import Path
import os,json,hashlib,base64,sys,types
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh as tm,manifold3d as mf
D=Path(__file__).resolve().parent;H=D.parent.parent;O=D/'rear-openrb';O.mkdir(exist_ok=True)
sys.path.insert(0,str(H/'gpio-audio-repair'));from precision_mesh import load,export
c=types.SimpleNamespace(np=np,tm=tm,mf=mf);hashes={}
def read(p):
 p=Path(p);b=p.read_bytes();hashes[str(p.resolve())]=hashlib.sha256(b).hexdigest();return b
def solid(p):
 p=Path(p);read(p)
 if p.suffix!='.json':return load(c,p)
 d=json.loads(p.read_text());m=tm.Trimesh(np.frombuffer(base64.b64decode(d['positionB64']),'<f4').reshape(-1,3),np.frombuffer(base64.b64decode(d['indexB64']),'<u4').reshape(-1,3),process=True)
 s=mf.Manifold(mf.Mesh64(np.asarray(m.vertices,np.float64),np.asarray(m.faces,np.uint64)));assert s.status()==mf.Error.NoError and s.volume()>0;return s
oldT=np.array(json.loads(read(H/'curved-head/openrb-pose-checkpoint.json'))['transformFromGuideWorld'])
T=np.eye(4);T[:3,:3]=[[0,0,1],[0,1,0],[-1,0,0]];T[:3,3]=[-215.1146,0,41.1]
delta=T@np.linalg.inv(oldT)
pieces=[solid(p).transform(delta[:3]) for p in sorted((D/'openrb-component-enclosures').glob('*.stl'))];assert len(pieces)==142
pieceBounds=np.array([s.bounding_box() for s in pieces]).reshape(-1,2,3)
bb=np.array([pieceBounds[:,0].min(axis=0),pieceBounds[:,1].max(axis=0)])
for i,s in enumerate(pieces):export(c,s,O/f'component-{i:03d}-world.stl')
scene=json.loads(read(D/'positive-x225-obstacle-plan.json'))['obstacles'];cache=D/'robot-source-cache';index=json.loads(read(cache/'index.json'))
for key in ('head_bottom','jaw_support'):
 scene[key]['source']=str(H/'cabling-release-20261008/neck-repair/flat-ribbon-sweep'/f'{key}-split-channel-world.stl')
rows=[]
for key,item in scene.items():
 if key=='openrb' or key.startswith('E-openrb'):continue
 bounds=np.array(item['bounds'])
 if not(np.all(bb[0]<bounds[1]) and np.all(bounds[0]<bb[1])):rows.append({'key':key,'separatedByBounds':True});continue
 ob=solid(item['source']);v=sum(max(0,float((s^ob).volume())) for s in pieces);rows.append({'key':key,'overlapMm3':v,'gapMm':min(s.min_gap(ob,5) for s in pieces) if v<1e-6 else 0})
report={'status':'PLACEMENT_FEASIBILITY_ONLY','transformFromGuideWorld':T.tolist(),'transformFromCurrentCurvedPose':delta.tolist(),'boardBoundsMm':bb.tolist(),'checks':rows,'hits':[r for r in rows if r.get('overlapMm3',0)>1e-5],'proposedRearCoverAnchorCenters': [[-62.6,y,z] for y in (-17.5,17.5) for z in (4,26)],'proposedAnchorStack':'Existing1.2mm cover +new2mm flange: M2x8 preserves existing4.8mm pilot engagement. No new hole in torso. Strength and assembly not established.','sourceHashes':hashes,'integrationReady':False,'remaining':['Neck/leg articulation','Four-hole OpenRB mounting and connector entry','USB host/power domain and motor cable layout','Printability and assembly access']}
(O/'placement.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'bounds':bb.tolist(),'hits':report['hits']}))
