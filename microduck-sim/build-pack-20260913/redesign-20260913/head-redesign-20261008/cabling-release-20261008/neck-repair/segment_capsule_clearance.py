"""Bound a round cable sweep with line-enclosing prism distances, one obstacle.

No neck/FK/scene dependency. Call under the project bounded CAD guard.
Each nominal centerline segment lies inside a tiny closed prism. Distance
from that prism to an obstacle is <= distance from the line segment. Thus
prism gap > radius+sagitta+numerical allowance proves separation of the
continuous round receiving sweep. A failure is INCONCLUSIVE, not necessarily
a real collision: endpoint balls conservatively extend past flat shoulders.
"""
import math,os

def check(points,radius,sagitta,obstacle,*,source_evidence,numerical_margin=.001,prism_half_width=.001,search_extra=.5,stop_on_inconclusive=False):
 assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1','Use bounded CAD launcher'
 import numpy as np,manifold3d as mf
 assert source_evidence.get('watertight') and source_evidence.get('positiveVolume') and source_evidence.get('sourceSha256'),'Caller must bind validated source/readback evidence'
 assert obstacle.status()==mf.Error.NoError and obstacle.volume()>0,'Invalid/empty obstacle'
 assert radius>0 and sagitta>=0 and numerical_margin>0 and prism_half_width>0 and search_extra>0
 p=np.asarray(points,dtype=float);assert p.ndim==2 and p.shape[1]==3 and len(p)>=2 and np.isfinite(p).all()
 p=p[np.r_[True,np.linalg.norm(np.diff(p,axis=0),axis=1)>1e-10]];assert len(p)>=2
 threshold=radius+sagitta+numerical_margin;search=threshold+search_extra;bb=np.array(obstacle.bounding_box()).reshape(2,3);rows=[];total=len(p)-1
 for i,(a,b) in enumerate(zip(p,p[1:])):
  lo=np.minimum(a,b);hi=np.maximum(a,b);sep=np.maximum(np.maximum(bb[0]-hi,lo-bb[1]),0.);lower=float(np.linalg.norm(sep));method='line-AABB lower bound'
  if lower<=threshold:
   axis=b-a;length=float(np.linalg.norm(axis));z=axis/length;basis=np.eye(3)[int(np.argmin(np.abs(z)))];x=np.cross(z,basis);x/=np.linalg.norm(x);y=np.cross(z,x)
   T=np.column_stack([x,y,z,(a+b)/2]);prism=mf.Manifold.cube([2*prism_half_width,2*prism_half_width,length+2*prism_half_width],True).transform(T)
   assert prism.status()==mf.Error.NoError and prism.volume()>0
   lower=float(prism.min_gap(obstacle,search));assert math.isfinite(lower) and 0<=lower<=search+1e-8;method='minimum gap from closed line-enclosing prism'
  clear=lower>threshold
  rows.append({'segmentIndex':i,'gapLowerBoundMm':lower,'gapMayBeSearchCapped':method.startswith('minimum') and lower>=search-1e-8,'requiredLowerBoundMm':threshold,'clear':clear,'status':'clear' if clear else 'inconclusive','method':method,'endpointSegment':i in [0,total-1]})
  if not clear and stop_on_inconclusive:break
 complete=len(rows)==total
 return {'passed':complete and all(r['clear'] for r in rows),'coverageComplete':complete,'expectedSegments':total,'completedSegments':len(rows),'nominalRadiusMm':radius,'centerlineSagittaAllowanceMm':sagitta,'numericalMarginMm':numerical_margin,'prismHalfWidthMm':prism_half_width,'searchLengthMm':search,'minimumGapLowerBoundMm':min(r['gapLowerBoundMm'] for r in rows),'inconclusiveSegmentIndices':[r['segmentIndex'] for r in rows if not r['clear']],'sourceEvidence':source_evidence,'scope':'Conservative separation of complete round receiving sweep for this polyline plus supplied centerline-error allowance against ONE validated obstacle. Caller must prove sagitta covers curve discretization and integration error. No endpoint or intended-contact exemptions. Inconclusive is not automatically actual interference.','segments':rows}
