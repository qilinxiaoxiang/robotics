"""One bounded U-return family. Each curved piece is an isometric cylinder,
including oblique bend axes; this is not a twisted rectangular sweep.
Use run_bounded_cad.py for both the numeric fit and STL export.
"""
from pathlib import Path
import os,json,math,hashlib,sys
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np
from scipy.optimize import least_squares, root
from scipy.spatial.transform import Rotation
D=Path(__file__).resolve().parent
pose=json.loads((D/'lowered-pose-pair-checks.json').read_text());T=np.array(pose['worldTransform']);mouth=np.array(pose['csiMouthWorldMm']);cam=np.array([76.03,9.3706236,131.1145958]);target=cam-[0,5,0]
R=3.;W=16.;thickness=.6
initial=(mouth-4.4*T[:3,1],T[:3,1],T[:3,2]);want=np.column_stack([[0,-1,0],[0,0,1],[-1,0,0.]])
def family(x):
 L1,L2,L3,L4,L5,L6,L7,phi2,phi6,phi3,phi5,a3,a5=x
 ops=[('S',8.4),('B',math.pi/2,0.,-1),('S',L1),('B',math.pi,phi2,-1),('S',L2),('B',math.pi/2+a3,phi3,1),('S',L3),('B',math.pi,0.,-1),('S',L4),('B',math.pi/2+a5,phi5,-1),('S',L5),('B',math.pi,phi6,-1),('S',L6),('B',math.pi/2,0.,1),('S',L7)]

 p,t,w=[a.copy() for a in initial];s=0.;bends=[];primitives=[]
 for op in ops:
  if op[0]=='S':
   L=op[1];primitives.append({'kind':'straight','s0':s,'s1':s+L,'p':p.copy(),'t':t.copy(),'w':w.copy()});p=p+t*L;s+=L
  else:
   ang,phi,sign=op[1:];n=np.cross(t,w);e=w*math.cos(phi)+t*math.sin(phi);q=t*math.cos(phi)-w*math.sin(phi);L=R*ang/math.cos(phi)
   b={'kind':'cylindrical','s0':s,'s1':s+L,'p':p.copy(),'t':t.copy(),'w':w.copy(),'n':n,'e':e,'q':q,'angle':ang,'phi':phi,'sign':sign,'R':R};bends.append(b);primitives.append(b)
   p=p+e*(R*ang*math.tan(phi))+q*(R*math.sin(ang))+n*(sign*R*(1-math.cos(ang)))
   qp=q*math.cos(ang)+n*(sign*math.sin(ang));t=e*math.sin(phi)+qp*math.cos(phi);w=e*math.cos(phi)-qp*math.sin(phi);s+=L
 return p,t,w,s,bends,primitives

def residual(x,regularize=True):
 p,t,w,L,_,_=family(x);F=np.column_stack([t,w,np.cross(t,w)]);r=np.r_[p-target,Rotation.from_matrix(want.T@F).as_rotvec()*30,L-200]
 return np.r_[r,(x[0]-9)*.05,(x[1]-10.5)*.05,(x[4]-10.5)*.05,(x[5]-9)*.05,(x[6]-16)*.05,x[9]*.05] if regularize else r

def solve():
 x0=[9,10.5,41.,41.,10.5,9,16,math.pi/4,-math.pi/4,0.,0.,0.,0.]
 lo=[8.3,8.3,20,20,8.3,8.3,9,.6,-.95,-.2,-.2,-.3,-.3];hi=[16,18,60,60,18,16,30,.95,-.6,.2,.2,.3,.3]
 fit=least_squares(residual,x0,bounds=(lo,hi),max_nfev=180,xtol=1e-11,ftol=1e-11,gtol=1e-11)
 fit=least_squares(lambda x:residual(x,False),fit.x,bounds=(lo,hi),max_nfev=100,xtol=1e-12,ftol=1e-12,gtol=1e-12)
 return fit

def material_map(s,v,bends,final):
 # Flat sheet coordinates are material arclength s and transverse v. Each
 # cylinder maps orthogonal (a,b) coordinates without stretching either.
 for b in bends:
  ds=s-b['s0'];phi=b['phi'];ac=ds*math.sin(phi)+v*math.cos(phi);bc=ds*math.cos(phi)-v*math.sin(phi)
  if bc<0:return b['p']+b['t']*ds+b['w']*v,b['n']
  if bc<=R*b['angle']:
   a=bc/R;q=b['q'];n=b['n'];sign=b['sign'];return b['p']+b['e']*ac+q*(R*math.sin(a))+n*(sign*R*(1-math.cos(a))),n*math.cos(a)-q*(sign*math.sin(a))
 p,t,w,L=final
 return p+t*(s-L)+w*v,np.cross(t,w)

def write():
 fit=solve();p,t,w,L,bends,prims=family(fit.x);res=residual(fit.x,False);gaps=[]
 for a,b in zip(bends,bends[1:]):gaps.append(b['s0']-a['s1']-W/2*(abs(math.tan(a['phi']))+abs(math.tan(b['phi']))))
 result={'status':'ONE_DEVELOPABLE_U_FAMILY_FIT','accepted':False,'parameters':fit.x.tolist(),'endpointErrorMm':float(np.linalg.norm(p-target)),'orientationErrorRadians':float(np.linalg.norm(res[3:6])/30),'intrinsicMaterialCenterLengthMm':L,'untrimmedTemplateMaterialEdgeLengthsMm':[L,L],'materialModel':'Isometric flat-to-cylinder map in orthogonal material coordinates. Oblique cylinders permit lateral displacement without a stretched/helicoid sweep. Thickness is a +/-0.3mm receiving envelope; R3 is assumed design bend radius, not manufacturer certification.','maximumAbsResidual':float(np.max(np.abs(res))),'minimumUnbentMaterialGapBetweenCylindersMm':min(gaps),'fullWidthMm':16,'miniInsertedWidthMm':11.5,'cameraInsertedLengthMm':5,'piInsertedLengthMm':4.4,'piFreeStiffenedStraightMm':4,'cameraFreeStraightMm':float(fit.x[6]-5),'sourceHashes':{str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),D/'lowered-pose-pair-checks.json']},'bends':[{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in b.items()} for b in bends],'endPointMm':p.tolist(),'targetPointMm':target.tolist(),'contactOrientationBoundary':'Width-coordinate sign and both connector contact-side/latch details require source/physical confirmation; no electrical acceptance inferred from symmetric envelope.'}
 (D/'roof-fold-ribbon-fit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['sourceHashes','bends']},indent=2),flush=True)
 result['exactEndpointFit']=bool(max(abs(res))<1e-5);result['diagnosticFitToleranceMm']=.001
 if '--mesh' not in sys.argv or max(abs(res))>.001 or min(gaps)<.3:return
 import trimesh,manifold3d as mf
 # Include analytic band transition boundaries plus 0.35mm longitudinal grid.
 ss=np.unique(np.r_[np.linspace(4.4,L,math.ceil((L-4.4)/.35)+1),*[b['s0'] for b in bends],*[b['s1'] for b in bends]])
 vv=np.unique(np.r_[np.linspace(-8,8,17),-5.75,5.75]);coords=[];normals=[]
 for s in ss:
  # Conservatively16mm everywhere outside mini mating mouth. Real revision1/2
  # transition can occupy any smaller subset, including the straight reinforcement.
  wd=16
  for v in vv:
   q,n=material_map(s,v*wd/16,bends,(p,t,w,L));coords.append(q);normals.append(n)
 coords=np.array(coords);normals=np.array(normals);verts=np.r_[coords-normals*.3,coords+normals*.3];N=len(coords);nv=len(vv);ns=len(ss);faces=[]
 for i in range(ns-1):
  for j in range(nv-1):
   a=i*nv+j;bb=a+1;c=bb+nv;d=a+nv;faces.extend([[a,c,bb],[a,d,c],[a+N,bb+N,c+N],[a+N,c+N,d+N]])
 for i in range(ns-1):
  for j in [0,nv-1]:a=i*nv+j;b=a+nv;faces.extend([[a,b,b+N],[a,b+N,a+N]])
 # The mini mating section joins a stepped body at one shared material plane.
 # The common middle face is omitted, so there is one closed shell, not two
 # coincident solids whose union can become nonmanifold at float32 precision.
 for i in [0,ns-1]:
  for j in range(nv-1):
   if i==0 and vv[j]>=-5.75 and vv[j+1]<=5.75:continue
   a=i*nv+j;b=a+1;faces.extend([[a,b,b+N],[a,b+N,a+N]])
 miniids=[j for j,v in enumerate(vv) if abs(v)<=5.75];nm=len(miniids);base=len(verts);ip,it,iw=initial;inn=np.cross(it,iw)
 mb=np.array([ip+iw*vv[j]-.3*inn for j in miniids]);mt=mb+.6*inn;verts=np.r_[verts,mb,mt]
 for j in range(nm-1):
  a=base+j;b=a+1;c=miniids[j+1];d=miniids[j]
  faces.extend([[a,c,b],[a,d,c],[a+nm,b+nm,c+N],[a+nm,c+N,d+N]])
  faces.extend([[a,b,b+nm],[a,b+nm,a+nm]])
 for j in [0,nm-1]:
  a=base+j;b=miniids[j];faces.extend([[a,b,b+N],[a,b+N,a+nm]])
 m=trimesh.Trimesh(verts,faces,process=True);trimesh.repair.fix_normals(m);assert m.is_watertight,'Export rejected: open ribbon boundary';sld=mf.Manifold(mf.Mesh(np.asarray(m.vertices,np.float32),np.asarray(m.faces,np.uint32)));assert sld.status()==mf.Error.NoError
 assert len(sld.decompose())==1,'Ribbon must be one connected material piece'
 assert 1800<sld.volume()<2000,'Ribbon receiving volume is inconsistent with200x16x0.6'
 out=D/'sc1892-roof-fold-receiving-world.stl';m.export(out)
 check=trimesh.load(out,force='mesh',process=True);assert check.is_watertight,'STL roundtrip rejected'
 center=np.array([material_map(s,0,bends,(p,t,w,L))[0] for s in ss]);(D/'roof-fold-ribbon-centerline.json').write_text(json.dumps({'intrinsicStationsMm':ss.tolist(),'centerlineWorldMm':center.tolist(),'materialEdgesMm':{'left':[material_map(s,-8,bends,(p,t,w,L))[0].tolist() for s in ss],'right':[material_map(s,8,bends,(p,t,w,L))[0].tolist() for s in ss]},'boundsMm':m.bounds.tolist()},indent=2)+'\n')
 result['meshSha256']=hashlib.sha256(out.read_bytes()).hexdigest();result['meshTriangles']=len(m.faces);result['watertight']=bool(m.is_watertight);result['boundsMm']=m.bounds.tolist();result['actualSampledCenterlineChordLengthMm']=float(np.linalg.norm(np.diff(center,axis=0),axis=1).sum());result['maximumLongitudinalSampleMm']=float(np.diff(ss).max());result['stlAccepted']=False;(D/'roof-fold-ribbon-fit.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':write()
