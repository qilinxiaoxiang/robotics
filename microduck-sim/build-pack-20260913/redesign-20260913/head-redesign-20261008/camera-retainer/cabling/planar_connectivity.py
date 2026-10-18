from pathlib import Path
import json,numpy as np,trimesh
from scipy.ndimage import maximum_filter,label
from collections import deque
D=Path(__file__).resolve().parent
src=(D/'build_full_ribbon.py').read_text();exec(src[:src.index('loopx=brentq')].replace('D=Path(__file__).resolve().parent','D=Path('+repr(str(D))+')'));exec(src[src.index("files={'curved_cap'"):src.index('hits={}')])
# Fixed vertical-wide strip; trace every mesh intersection through each column.
xv=np.arange(-25,85.01,1.);yv=np.arange(-43,43.01,1.);xx,yy=np.meshgrid(xv,yv,indexing='ij');orig=np.c_[xx.ravel(),yy.ravel(),np.full(xx.size,80.)];rays=np.tile([0.,0,1.],(len(orig),1));allints={}
for name,o in obs.items():
 m=tri(o-slots[name] if name in slots else o);loc,ri,_=m.ray.intersects_location(orig,rays,multiple_hits=True);arr=[[] for _ in orig]
 if len(loc):
  for i,z in zip(ri,loc[:,2]):arr[int(i)].append(float(z))
 allints[name]=[sorted(z) for z in arr]
print('RAYS_READY',flush=True)
results=[];zc=float(cam[2]);npzs={}
for width,lead,margin in [(w,l,m) for w in [16.,11.5,5.] for l,m in [(6,3),(3,1)]]:
 occ=np.zeros(len(orig),bool);reasons=[[] for _ in orig];lo=zc-width/2;hi=zc+width/2
 for name,columns in allints.items():
  for i,z in enumerate(columns):
   if not z:continue
   # Surface within interval or interval starts inside watertight solid.
   a=np.searchsorted(z,lo,side='right');b=np.searchsorted(z,hi,side='left')
   if b>a or a%2:occ[i]=True;reasons[i].append(name)
 occ=occ.reshape(xx.shape)
 # At1mm mesh spacing this1cell dilation reserves1mm lateral margin, bounding
 # the0.6mm thickness plus grid discretization. Endpoint approach is separate.
 blocked=maximum_filter(occ,size=margin);free=~blocked
 # Evaluate the end of a6mm straight lead at both sockets, not erase obstacles
 # to make a mouth-cell pass. Initial straight leads require own geometry test.
 startworld=cam+np.array([0,lead,0]);endworld=pi+np.array([0,lead,0]);start=(int(round(startworld[0]-xv[0])),int(round(startworld[1]-yv[0])));end=(int(round(endworld[0]-xv[0])),int(round(endworld[1]-yv[0])))
 labels,count=label(free);connected=bool(free[start] and free[end] and labels[start]==labels[end]);path=[]
 if connected:
  queue=deque([start]);prev={start:None}
  while queue:
   q=queue.popleft()
   if q==end:break
   for a,b in [(q[0]-1,q[1]),(q[0]+1,q[1]),(q[0],q[1]-1),(q[0],q[1]+1)]:
    nxt=(a,b)
    if 0<=a<len(xv) and 0<=b<len(yv) and free[nxt] and nxt not in prev:prev[nxt]=q;queue.append(nxt)
  q=end
  while q is not None:path.append([float(xv[q[0]]),float(yv[q[1]]),zc]);q=prev[q]
  path.reverse()
 def reasons_at(q):return reasons[q[0]*len(yv)+q[1]]
 results.append({'bodyWidthMm':width,'leadAssumptionMm':lead,'dilationCells':margin//2,'centerZMm':zc,'startAfter6mmLeadWorldMm':startworld.tolist(),'endBefore6mmLeadWorldMm':endworld.tolist(),'startFreeWithMargin':bool(free[start]),'endFreeWithMargin':bool(free[end]),'rawStartObstacles':reasons_at(start),'rawEndObstacles':reasons_at(end),'connectedInSampledPlane':connected,'shortestGridPathMm':path,'minimumRadiusEnforced':False,'200mmStorageVerified':False})
 npzs['blocked_'+str(width)+'_'+str(lead)]=blocked
np.savez_compressed(D/'planar-occupancy.npz',x=xv,y=yv,**npzs)
report={'scope':'Conservative1mm raster connectivity for a vertically wide ribbon at the actual rotated camera exit height. Uses full strip-height mesh ray interval, not a centerline-only check. One-cell dilation. No claim about unsampled3D routes.','results':results,'next':'If endpoint leads are blocked, alter geometry/pose or route vertically before searching this plane; do not smooth a path through blocked cells.'}
(D/'planar-connectivity.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
