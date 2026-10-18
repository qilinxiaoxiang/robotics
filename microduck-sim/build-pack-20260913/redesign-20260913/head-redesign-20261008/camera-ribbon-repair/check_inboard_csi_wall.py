"""Receiving-wall bound from exact original cap rays, one selected Pi pose."""
from pathlib import Path
import json,os,hashlib
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh
D=Path(__file__).resolve().parent;H=D.parent;capfile=H/'curved-head/curved-cap-final-candidate-world.stl';cap=trimesh.load(capfile,force='mesh');sources=[capfile];parts=[]
p=D/'pi-inboard-end-turn--1-world.stl';sources.append(p);parts.append(trimesh.load(p,force='mesh'))
# Bounds come from measured opposite-side intersections, extended0.5mm.
origins=np.array([[x,-100,z] for x in np.arange(61.5,72.251,.25) for z in np.arange(121,138.501,.25)]);dirs=np.tile([0.,1,0],(len(origins),1))
def rays(m):
 locations,indices,_=m.ray.intersects_location(origins,dirs,multiple_hits=True);out={}
 for p,i in zip(locations,indices):out.setdefault(int(i),[]).append(float(p[1]))
 return {i:sorted(set(round(v,6) for v in vals)) for i,vals in out.items()}
cr=rays(cap);pr=[rays(m) for m in parts];rows=[]
for i,origin in enumerate(origins):
 ys=[y for r in pr for y in r.get(i,[])];shell=cr.get(i,[])
 if not ys or len(shell)<2:continue
 inside,outside=shell[-2:];first=max(ys)
 if first>=inside-.3:
  rows.append({'xMm':float(origin[0]),'zMm':float(origin[2]),'outerYMm':outside,'innerYMm':inside,'candidateMinYMm':first,'existingShellYThicknessMm':outside-inside,'remainingYThicknessAfter0p3ClearanceMm':outside-first-.3,'outsideNativeOuterEnvelope':first>outside})
r={'status':'EXACT_RAY_WALL_BOUND_ONLY','accepted':False,'samplingMm':.25,'clearanceMm':.3,'requiredMinimumSkinMm':1.2,'rows':rows,'minimumRemainingYBoundMm':min(x['remainingYThicknessAfter0p3ClearanceMm'] for x in rows),'outsideNativeCount':sum(x['outsideNativeOuterEnvelope'] for x in rows),'belowMinimumCount':sum(x['remainingYThicknessAfter0p3ClearanceMm']<1.2 for x in rows),'interpretation':'Y-ray remaining wall is an upper bound on shortest3D wall thickness, so below1.2 decisively rejects relief. Above1.2 alone is not proof of shortest thickness. No new exterior opening allowed.','sourceHashes':{str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources+[Path(__file__)]}};(D/'inboard-csi-wall-bound.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:r[k] for k in ['minimumRemainingYBoundMm','outsideNativeCount','belowMinimumCount']}))
