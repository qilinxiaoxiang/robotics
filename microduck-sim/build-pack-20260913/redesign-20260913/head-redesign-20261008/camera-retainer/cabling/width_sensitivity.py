from pathlib import Path
import json,numpy as np,trimesh,manifold3d as mf,hashlib
D=Path(__file__).resolve().parent
# Reuse exact source declarations without running route export/closure mutations.
src=(D/'build_full_ribbon.py').read_text();pre=src[:src.index("loopx=brentq")];exec(pre.replace('D=Path(__file__).resolve().parent', 'D=Path('+repr(str(D))+')'))
r=json.loads((D/'full-ribbon-report.json').read_text());points=np.array(r['centerlineWorldMm']);s=np.r_[0,np.cumsum(np.linalg.norm(np.diff(points,axis=0),axis=1))];L=s[-1];v=np.gradient(points,axis=0);v/=np.linalg.norm(v,axis=1)[:,None];w=np.tile([0,0,1.],(len(points),1));n=np.cross(v,w)
source=src[src.index("files={'curved_cap'"):src.index('hits={}')];exec(source)
results={}
for mid in [16,11.5,5]:
 wide=np.full(len(s),mid,float);start=np.clip((13-s)/8,0,1);end=np.clip((s-(L-12.4))/8,0,1);wide+=(16-mid)*start+(11.5-mid)*end
 verts=[]
 for p,ww,nn,wd in zip(points,w,n,wide):verts.extend([p-ww*wd/2-nn*.3,p+ww*wd/2-nn*.3,p+ww*wd/2+nn*.3,p-ww*wd/2+nn*.3])
 faces=[[0,2,1],[0,3,2]]
 for i in range(len(points)-1):
  for j in range(4):a=4*i+j;b=4*i+(j+1)%4;c=b+4;d=a+4;faces.extend([[a,b,c],[a,c,d]])
 nv=len(verts);faces.extend([[nv-4,nv-3,nv-2],[nv-4,nv-2,nv-1]]);m=trimesh.Trimesh(verts,faces,process=True);trimesh.repair.fix_normals(m);cable=man(m);hits={}
 for k,o in obs.items():
  q=cable^(o-slots[k] if k in slots else o);volume=max(0,q.volume())
  if volume>1e-5:hits[k]=volume
 results[str(mid)]={'middleWidthMm':mid,'cameraEndWidthMm':16,'miniEndWidthMm':11.5,'contactStraightLengthsMm':[5,4.4],'transitionLengthMm':8,'thicknessMm':.6,'collisionVolumesMm3':hits,'passes':not bool(hits)}
center_hits={}
for k,o in obs.items():
 m=tri(o-slots[k] if k in slots else o);inside=m.contains(points);inds=np.where(inside)[0]
 if len(inds):center_hits[k]={'insideSampleCount':len(inds),'firstArcDistanceMm':float(s[inds[0]]),'lastArcDistanceMm':float(s[inds[-1]])}
report={'date':'2026-10-08','same200mmCenterline':True,'radiusMm':6,'widths':results,'centerlinePointContainment':center_hits,'conclusion':'All tested widths fail this particular route, including centerline penetration. Unknown body width is not the sole blocker. This finite-candidate failure does not prove every routing or cable orientation impossible. Keep existing published camera orientation.','sourceRouteSha256':hashlib.sha256((D/'full-ribbon-report.json').read_bytes()).hexdigest()}
(D/'width-sensitivity.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
