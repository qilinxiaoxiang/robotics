"""Bounded single-topology local search: four free parameters, max80 evaluations.
Fixed lowered Pi/current rearseat camera. Coarse geometry ranks candidates only;
no result can become accepted until independent exact self/all-obstacle checks.
"""
from pathlib import Path
import os,json,hashlib,time,gc
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np,trimesh,manifold3d as mf
from scipy.optimize import least_squares,minimize
import developable_ribbon_inner_entry as dr
D=Path(__file__).resolve().parent;H=D.parent
p=D/'check_saved_pose.py';helper={'__file__':str(p)};exec(p.read_text().split('resume=')[0],helper);read=helper['read'];read(Path(__file__))
manifest=json.loads(read(D/'local-candidate-manifest.json'));files=manifest['replacementMeshes']|{p['key']:p['mesh'] for p in manifest['additionalParts']}
dr.cam=np.array([74.83,9.3706236,131.1145958]);dr.target=dr.cam-[0,5,0]
fitfile=D/'inner-entry-ribbon-fit.json';base=np.array(json.loads(read(fitfile))['parameters']);fixed=[0,4,5,9];free=[1,2,3,6,7,8,10]
def load(p):
 read(p);m=trimesh.load(p,force='mesh');assert m.is_watertight,str(p);s=mf.Manifold(mf.Mesh64(np.array(m.vertices,np.float64),np.array(m.faces,np.uint64)));assert s.status()==mf.Error.NoError and s.volume()>0;return s
obstacles={k:load(H/files[k]) for k in ['head_cap','pi','zero_w_components','E-pi-04_revision_screw','amplifier','camera_board','face_panel']}
T=np.array(manifest['piWorldTransform']);slot=mf.Manifold.cube([.6,4.4,11.5],True).translate([65.8,32.4886208-2.2,131.0496]).transform(T[:3]);obstacles['zero_w_components']-=slot
obstacles['camera_board']-=mf.Manifold.cube([.6,5,16],True).translate([74.83,9.3706236-2.5,131.1145958])
bounds={k:np.array(s.bounding_box()).reshape(2,3) for k,s in obstacles.items()}
# Save immutable input identities before spending any candidate budget.
report={'accepted':False,'integrationReady':False,'scope':'Fixed-pose fixed-U local search, coarse ranking only','maximumCandidates':80,'fixedPiTransform':manifest['piWorldTransform'],'fixedCameraMouthMm':dr.cam.tolist(),'parameterNames':['L1','L5','phi2','phi3'],'sourceHashes':helper['hashes'],'candidates':[],'expectedFinalAcceptance':['Exact material length/orientation and reinforcement bounds','Closed full-width receiving STL','4851 exact nonadjacent self pairs','All obstacles, connector sequence, closure and articulation'],'completedFinalAcceptance':[]}
out=D/'fixed-u80-search.json';log=D/'fixed-u80-search.jsonl';log.write_text('');started=time.monotonic();best=float('inf')
def save():out.write_text(json.dumps(report,indent=2)+'\n')
save()
def construct(s0,s1,step,x,width_step=8):
 p,t,w,L,bends,_=dr.family(x);ss=np.linspace(s0,s1,max(2,int(np.ceil((s1-s0)/step))+1));vv=np.linspace(-8,8,width_step+1);coords=[];norms=[]
 for s in ss:
  for v in vv:
   q,n=dr.material_map(s,v,bends,(p,t,w,L));coords.append(q);norms.append(n)
 coords=np.array(coords);norms=np.array(norms);vertices=np.r_[coords-.3*norms,coords+.3*norms];N=len(coords);nv=len(vv);ns=len(ss);faces=[]
 for i in range(ns-1):
  for j in range(nv-1):
   a=i*nv+j;b=a+1;c=b+nv;d=a+nv;faces.extend([[a,c,b],[a,d,c],[a+N,b+N,c+N],[a+N,c+N,d+N]])
 for i in range(ns-1):
  for j in [0,nv-1]:a=i*nv+j;b=a+nv;faces.extend([[a,b,b+N],[a,b+N,a+N]])
 for i in [0,ns-1]:
  for j in range(nv-1):a=i*nv+j;b=a+1;faces.extend([[a,b,b+N],[a,b+N,a+N]])
 mesh=trimesh.Trimesh(vertices,faces,process=True);trimesh.repair.fix_normals(mesh);assert mesh.is_watertight
 solid=mf.Manifold(mf.Mesh64(np.array(mesh.vertices,np.float64),np.array(mesh.faces,np.uint64)));assert solid.status()==mf.Error.NoError
 return solid
lo=np.array([20,20,5,-.6,-1.2,-1.2,-.6]);hi=np.array([90,90,50,.6,1.2,1.2,.6])
def evaluate(z):
 global best
 if len(report['candidates'])>=80:raise RuntimeError('Candidate budget exhausted')
 x=base.copy();x[fixed]=[z[0],z[1],z[2]*.1,z[3]*.1]
 def pack(v):
  a=x.copy();a[free]=v;return a
 sol=least_squares(lambda v:dr.residual(pack(v),False),base[free],bounds=(lo,hi),max_nfev=45,ftol=1e-9,xtol=1e-9,gtol=1e-9)
 x=pack(sol.x);res=float(max(abs(dr.residual(x,False))));p,t,w,L,bends,_=dr.family(x);gap=min(b['s0']-a['s1']-8*(abs(np.tan(a['phi']))+abs(np.tan(b['phi']))) for a,b in zip(bends,bends[1:]));row={'index':len(report['candidates']),'freeParameters':list(map(float,z)),'parameters':x.tolist(),'maxEndpointLengthOrientationResidual':res,'fullWidthFlatGapMm':float(gap)}
 cost=1000+100*res+100*max(0,.3-gap)
 if res<1e-4 and gap>.3:
  # Full16mm starts at connector mouth. Mini inserted4.4mm is checked separately
  # only at final acceptance, and cannot be narrowed elsewhere to improve cost.
  solid=construct(4.4,200,.8,x);sb=np.array(solid.bounding_box()).reshape(2,3);hits={}
  for k,o in obstacles.items():
   bb=bounds[k];hits[k]=0. if np.any(sb[0]>=bb[1]) or np.any(bb[0]>=sb[1]) else max(0,float((solid^o).volume()))
  del solid
  slabs=[construct(a,a+4,2,x,4) for a in np.arange(4,196,4)];bbs=[np.array(s.bounding_box()).reshape(2,3) for s in slabs];selfvol=0.;selfpairs=0
  for i,a in enumerate(slabs):
   for j in range(i+2,len(slabs)):
    ba,bb=bbs[i],bbs[j]
    if np.any(ba[0]>=bb[1]) or np.any(bb[0]>=ba[1]):continue
    v=max(0,float((a^slabs[j]).volume()));selfvol+=v;selfpairs+=v>1e-5
  row['coarseObstacleOverlapMm3']=hits;row['coarseSelfOverlapMm3']=selfvol;row['coarseSelfOverlappingPairs']=selfpairs;cost=sum(hits.values())+selfvol*4;del slabs;gc.collect()
 row['cost']=float(cost);row['elapsedSeconds']=time.monotonic()-started;report['candidates'].append(row)
 if cost<best:best=cost;report['best']=row
 with log.open('a') as f:f.write(json.dumps(row)+'\n')
 save();print(row['index'],round(cost,5),flush=True)
 return cost
z0=np.array([base[0],base[4],base[5]*10,base[9]*10]);simplex=np.tile(z0,(5,1));simplex[1,0]-=.75;simplex[2,1]-=1.5;simplex[3,2]-=.4;simplex[4,3]-=.2
try:
 result=minimize(evaluate,z0,method='Nelder-Mead',bounds=[(1.5,10),(18,34),(-2,2),(-1.5,1.5)],options={'maxfev':80,'initial_simplex':simplex,'xatol':.015,'fatol':.01})
 report['optimizerTermination']=str(result.message)
except RuntimeError as e:report['optimizerTermination']=str(e)
report['completedCandidates']=len(report['candidates']);report['elapsedSeconds']=time.monotonic()-started;save();print(json.dumps({'completed':len(report['candidates']),'best':report.get('best')},indent=2))
