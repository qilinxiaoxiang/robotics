from pathlib import Path
import runpy,io,contextlib,math,json
D=Path(__file__).resolve().parent
with contextlib.redirect_stdout(io.StringIO()): a=runpy.run_path(str(D/'check_neck_original_bores_stdlib.py'))
v=a['v'];ff=a['ff'];data=a['data'];out=[]
def clip(poly,z,above):
 res=[]
 for p,q in zip(poly,poly[1:]+poly[:1]):
  ip=p[2]>=z if above else p[2]<=z;iq=q[2]>=z if above else q[2]<=z
  if ip:res.append(p)
  if ip!=iq:
   t=(z-p[2])/(q[2]-p[2]);res.append([p[k]+t*(q[k]-p[k]) for k in range(3)])
 return res
def edge(p,q,x,y):
 d=[q[0]-p[0],q[1]-p[1]];den=d[0]*d[0]+d[1]*d[1];t=max(0,min(1,((x-p[0])*d[0]+(y-p[1])*d[1])/den)) if den else 0
 return math.hypot(p[0]+t*d[0]-x,p[1]+t*d[1]-y)
for s in data['screws']:
 if not s['id'].startswith('S13-horn-'):continue
 x,y,z=s['world_center_mm'];best=1e9;which=None;n=0
 for i,f in enumerate(ff):
  poly=[v[k] for k in f]
  if min(p[2] for p in poly)>z-1e-5 or max(p[2] for p in poly)<z-1:continue
  poly=clip(poly,z-1,True);poly=clip(poly,z-1e-5,False) if poly else []
  if not poly:continue
  n+=1;dist=min(edge(p,q,x,y) for p,q in zip(poly,poly[1:]+poly[:1]));area=sum(p[0]*q[1]-p[1]*q[0] for p,q in zip(poly,poly[1:]+poly[:1]));crosses=[(q[0]-p[0])*(y-p[1])-(q[1]-p[1])*(x-p[0]) for p,q in zip(poly,poly[1:]+poly[:1])]
  if abs(area)>1e-9 and (all(t>=0 for t in crosses) or all(t<=0 for t in crosses)):dist=0
  if dist<best:best=dist;which=i
 out.append({'id':s['id'],'emptyDiskRadiusToOriginalMeshMm':best,'OD4CenteredRadialClearanceMm':best-2,'OD4MaxAcceptedCenterEccentricityWith0p05MarginMm':best-2-.05,'sourceFaceIndex':which,'sourceTrianglesIntersectingSpacerSlab':n,'slabWorldZMm':[z-1,z-1e-5]})
r={'method':'Direct original 3MF triangles, clipped to the full1mm spacer Z slab, exact convex-polygon projected distance to screw center.10nm seat-plane exclusion handles the canonical3.3nm rounded datum; no CAD meshing or boolean. This is a continuous empty-disk clearance, not only sampled radial rays.','rows':out,'physicalStockVerified':False,'fixtureInstalledOrPrinted':False,'scope':'Geometric receptacle for an independent washer/small spacer only; no insertion/driver or torque/creep acceptance.'};(D/'neck-spacer-original-receptacle.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
