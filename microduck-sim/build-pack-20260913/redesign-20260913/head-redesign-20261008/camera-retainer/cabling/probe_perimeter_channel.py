from pathlib import Path
import json,numpy as np,trimesh
D=Path(__file__).resolve().parent
src=(D/'build_full_ribbon.py').read_text();exec(src[:src.index('loopx=brentq')].replace('D=Path(__file__).resolve().parent','D=Path('+repr(str(D))+')'));exec(src[src.index("files={'curved_cap'"):src.index('hits={}')])
meshes={k:tri(o) for k,o in obs.items()};rows=[]
# Sample full thickness at both edge faces and midplane. Vertical ray gives exact
# mesh surface intersections at these lateral samples; this is a channel probe,
# not a continuous swept-band certification.
for side in [-1,1]:
 for yc in [30,32,34]:
  xs=np.arange(-20,75.01,2.5);ys=[side*yc-.3,side*yc,side*yc+.3];orig=np.array([[x,y,100.] for x in xs for y in ys]);directions=np.tile([0.,0,1.],(len(orig),1));surfaces=[[] for _ in orig]
  for name,m in meshes.items():
   loc,ri,_=m.ray.intersects_location(orig,directions,multiple_hits=True)
   if len(loc)==0:continue
   for i in range(len(orig)):
    zz=sorted(loc[ri==i,2]);
    for z in zz:surfaces[i].append((float(z),name))
  for zc in [123.,125.,127.]:
   centers=np.array([[x,y,zc] for x in xs for y in ys]);inside={name:m.contains(centers) for name,m in meshes.items()};section=[]
   for ix,x in enumerate(xs):
    local=[]
    for iy,y in enumerate(ys):
     idx=3*ix+iy;hits=[name for name,mask in inside.items() if mask[idx]]
     lower=[q for q in surfaces[idx] if q[0]<zc];upper=[q for q in surfaces[idx] if q[0]>zc]
     low=max(lower,default=(100.,'scan-floor'));up=min(upper,default=(165.,'scan-ceiling'))
     height=0. if hits else max(0.,2*min(zc-low[0],up[0]-zc))
     local.append({'yMm':y,'centerInside':hits,'lower':low,'upper':up,'centeredBandWidthLimitMm':height})
    lim=min(q['centeredBandWidthLimitMm'] for q in local);section.append({'xMm':float(x),'maximumCenteredVerticalBandWidthMm':lim,'lateralSamples':local})
   clear_ranges={}
   for width in [16.,11.5,5.]:
    runs=[];start=None
    for q in section+[{'xMm':float(xs[-1]+2.5),'maximumCenteredVerticalBandWidthMm':-1}]:
     if q['maximumCenteredVerticalBandWidthMm']>=width and start is None:start=q['xMm']
     elif q['maximumCenteredVerticalBandWidthMm']<width and start is not None:runs.append([start,q['xMm']-2.5]);start=None
    clear_ranges[str(width)]=runs
   rows.append({'side':side,'centerYMm':side*yc,'centerZMm':zc,'stripThicknessMm':.6,'xStepMm':2.5,'sections':section,'sampledClearXRangesMm':clear_ranges})
report={'scope':'Finite sidewall corridor cross-section probe at Y±30/32/34,Z123/125/127mm. Does not establish a connected full cable route or all-angle impossibility.','rows':rows,'sourceFullRouteReport':'full-ribbon-report.json'}
(D/'perimeter-channel-probe.json').write_text(json.dumps(report,indent=2)+'\n')
for r in rows:print(r['centerYMm'],r['centerZMm'],r['sampledClearXRangesMm'])
