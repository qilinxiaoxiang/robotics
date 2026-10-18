from pathlib import Path
import sys,json,base64,gc,itertools,argparse
D=Path(__file__).resolve().parent;N=D.parent.parent;H=N.parent.parent;sys.path.insert(0,str(N))
from short_path_worker import guard,save,sha,BODIES,ORDER
guard()
import numpy as np,trimesh,manifold3d as mf
from prepare_single_candidate import moved
ap=argparse.ArgumentParser();ap.add_argument('--body',choices=['neck','trunk_base'],required=True);args=ap.parse_args()
C=H/'usb-access/usb-repair/robot-source-cache';idx=json.loads((C/'index.json').read_text());plan=json.loads((D/'candidate.json').read_text());g=next(x for x in plan['guides'] if x['body']==args.body);domain=json.loads((H/'usb-access/usb-repair/rigid-domain.json').read_text());rows=[];count=0
# One obstacle solid and one guide part solid live at a time; transforms only cached.
def T(body,q):
 q={k:q.get(k,0) for k in ORDER[:BODIES.get(body,0)]};o=np.array(moved([0,0,0],q));R=np.array([moved(x,q,True) for x in [[1,0,0],[0,1,0],[0,0,1]]]).T;t=np.eye(4);t[:3,:3]=R;t[:3,3]=o;return t
def solid(t):
 s=mf.Manifold(mf.Mesh64(np.array(t.vertices,dtype=np.float64,order='C'),np.array(t.faces,dtype=np.uint64,order='C')));assert s.status()==mf.Error.NoError and s.volume()>0;return s
partsolids=[]
for p in g['parts']:
 t=trimesh.load(p['mesh'],force='mesh',process=False);uv,ui=np.unique(t.vertices,axis=0,return_inverse=True);t=trimesh.Trimesh(uv,ui[t.faces],process=False);partsolids.append((p,solid(t),t.bounds))
def receipt(passed,complete):
 out={'passed':passed,'coverageComplete':complete,'guideBody':args.body,'candidateHash':sha(D/'candidate.json'),'domainHash':sha(H/'usb-access/usb-repair/rigid-domain.json'),'sourceDataSha256':idx['sourceDataSha256'],'exactPairs':count,'rows':rows,'scope':'All103 canonical source parts; 229 poses; distinct relative transforms collapsed. Revised head overlays not included yet.'};save(D/f'motion-{args.body}.json',out)
for key,p in idx['parts'].items():
 data=json.loads((C/p).read_text());override=N/'flat-ribbon-sweep'/({'head_bottom':'head_bottom-split-channel-world.stl','jaw_support':'jaw_support-split-channel-world.stl'}.get(key,''));override=override if key in ['head_bottom','jaw_support'] else None
 if override:
  ot=trimesh.load(override,force='mesh');data['bounds']=ot.bounds.tolist()
 bb=np.array(data['bounds']);corners=np.array(list(itertools.product(*zip(bb[0],bb[1]))));selected={}
 for i,row in enumerate(domain['samples']):
  q=row['jointDegrees'];rel=np.linalg.inv(T(g['body'],q))@T(data['body'],q);rounded=tuple(np.round(rel.flatten(),9));pts=corners@rel[:3,:3].T+rel[:3,3];b1=np.array([pts.min(axis=0),pts.max(axis=0)])
  if any(not(np.any(b0[0]>=b1[1]) or np.any(b1[0]>=b0[1])) for _,_,b0 in partsolids):selected.setdefault(rounded,{'T':rel,'poses':[]})['poses'].append(i)
 if not selected:continue
 v=np.frombuffer(base64.b64decode(data['positionB64']),'<f4').reshape(-1,3);f=np.frombuffer(base64.b64decode(data['indexB64']),'<u4').reshape(-1,3);tm=ot if override else trimesh.Trimesh(v,f,process=True);obs=solid(tm)
 for rr in selected.values():
  b=obs.transform(rr['T'][:3]);b1=np.array(b.bounding_box()).reshape(2,3)
  for part,a,b0 in partsolids:
   if np.any(b0[0]>=b1[1]) or np.any(b1[0]>=b0[1]):continue
   hit=a^b;vol=max(0,float(hit.volume()));count+=1;row={'part':part['key'],'obstacle':key,'poses':rr['poses'],'intersectionMm3':vol,'bounds':list(hit.bounding_box()) if vol>1e-5 else None};rows.append(row)
   if vol>1e-5:
    receipt(False,False);print(json.dumps(row));sys.exit(2)
  del b
 del obs,tm;gc.collect();receipt(True,False)
receipt(True,True);print(json.dumps({'passed':True,'body':args.body,'exactPairs':count}))
