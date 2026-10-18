"""Shared finite-radius wire geometry; reject overlapping corner trims before meshing."""
from pathlib import Path
import ast,math
import numpy as np,trimesh,manifold3d as mf
SOURCE=Path(__file__).resolve().parents[2]/'motor-wires/local_route.py'
source=SOURCE.read_text()
for node in ast.parse(source).body:
 if isinstance(node,ast.FunctionDef) and node.name in ['primitives','sample','tube','solid']:
  code=ast.get_source_segment(source,node)
  code=code.replace('  R=(4. if ix in [3,4,5] else 2.)\n','')
  code=code.replace('def tube(pts,tans):','def tube(pts,tans,radius=.75):').replace('(.75+.003)','(radius+.003)')
  exec(code)
raw_primitives=primitives
def primitives(points,R=2.):
 v=np.diff(np.array(points,dtype=float),axis=0);length=np.linalg.norm(v,axis=1);assert min(length)>1e-8;unit=v/length[:,None]
 trims=np.r_[0,[R*math.tan(math.acos(np.clip(np.dot(a,b),-1,1))/2)for a,b in zip(unit,unit[1:])],0]
 available=length-trims[:-1]-trims[1:]
 assert min(available)>-1e-7,{'reversingFillet':available.tolist(),'points':points}
 return raw_primitives(points,R)
def self_check(pr,pts,diameter=1.5):
 lengths=[];s=0
 for a in pr:
  n=max(2,math.ceil(a['lengthMm']/.15));lengths.extend(s+np.arange(n)*a['lengthMm']/n);s+=a['lengthMm']
 lengths.append(s);arcs=np.array(lengths);exclusion=diameter+1.0
 dist=np.linalg.norm(pts[:,None,:]-pts[None,:,:],axis=2);mask=np.abs(arcs[:,None]-arcs[None,:])>=exclusion
 minimum=float(dist[mask].min());assert minimum>diameter+.32,minimum
 # .30 covers both adjacent .15 sampling intervals, .02 covers circumscribed mesh radial overbuild.
 return {'nonlocalMaterialSeparationMm':exclusion,'sampleMaximumSpacingMm':.15,'minimumSampledDistanceMm':minimum,'minimumConservativeBetweenSamplesMm':minimum-.3,'receivingDiameterMm':diameter,'meshRadialOverbuildAllowanceMm':.02,'passed':True}
