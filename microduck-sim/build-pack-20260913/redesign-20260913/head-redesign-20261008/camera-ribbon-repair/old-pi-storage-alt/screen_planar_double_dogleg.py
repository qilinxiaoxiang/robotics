from pathlib import Path
import os;assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import sys,json,math,hashlib,ast,gc
import numpy as np,trimesh,manifold3d as mf
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
D=Path(__file__).resolve().parent;C=D.parent;H=C.parent;sys.path.insert(0,str(C))
import developable_x225_dogleg as dr
cam=np.array([75.63,-9.553380023950195,131.1145988411133]);target=cam+[0,5,0];want=np.column_stack([[0,1,0],[0,0,1],[1,0,0]])
# Replace first/last U by separated quarter bends: traverse across the narrow board end before following its back face.
def family(x):
 La,L1,L2,L3,Lb,L4,R3,aa,bb,phia,phib=x
 ops=[('S',8.4),('B',math.pi/2,0,-1,3),('S',La),('B',math.pi/2,0,-1,3),('S',L1),('B',math.pi,0,1,3),('S',L2),('B',math.pi,0,1,R3),('S',L3),('B',aa,phia,-1,3),('S',Lb),('B',bb,phib,-1,3),('S',L4)]
 p,t,w=[a.copy() for a in dr.initial];s=0.;bends=[];primitives=[]
 for op in ops:
  if op[0]=='S':
   L=op[1];primitives.append({'kind':'straight','s0':s,'s1':s+L,'p':p.copy(),'t':t.copy(),'w':w.copy()});p=p+t*L;s+=L
  else:
   ang,phi,sign,R=op[1:];n=np.cross(t,w);e=w*math.cos(phi)+t*math.sin(phi);q=t*math.cos(phi)-w*math.sin(phi);L=R*ang/math.cos(phi);b={'kind':'cylindrical','s0':s,'s1':s+L,'p':p.copy(),'t':t.copy(),'w':w.copy(),'n':n,'e':e,'q':q,'angle':ang,'phi':phi,'sign':sign,'R':R};bends.append(b);primitives.append(b);p=p+e*(R*ang*math.tan(phi))+q*(R*math.sin(ang))+n*(sign*R*(1-math.cos(ang)));qp=q*math.cos(ang)+n*(sign*math.sin(ang));t=e*math.sin(phi)+qp*math.cos(phi);w=e*math.cos(phi)-qp*math.sin(phi);s+=L
 return p,t,w,s,bends,primitives
dr.family=family
node=next(x for x in ast.parse((C/'developable_ribbon_inner_entry.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='material_map');node.body[0].body.insert(0,ast.parse("R=b['R']").body[0]);ast.fix_missing_locations(node);exec(compile(ast.Module(body=[node],type_ignores=[]),'<map>','exec'),dr.__dict__)
node=next(x for x in ast.parse((C/'optimize_x225_u80.py').read_text()).body if isinstance(x,ast.FunctionDef) and x.name=='construct');exec(compile(ast.Module(body=[node],type_ignores=[]),'<construct>','exec'))
manifest=json.loads((C/'positive-x225/candidate-manifest.json').read_text());files=manifest['replacementMeshes']|{x['key']:x['mesh'] for x in manifest['additionalParts']};obstacles={};hashes={}
for key in ['head_cap','pi','zero_w_components']:
 f=H/files[key];hashes[str(f)]=hashlib.sha256(f.read_bytes()).hexdigest();m=trimesh.load(f,force='mesh');assert m.is_watertight;obstacles[key]=mf.Manifold(mf.Mesh64(np.array(m.vertices,np.float64),np.array(m.faces,np.uint64)))
# Only the true connector inserted slot is receiving space; exterior strip remains16mm throughout.
slot=mf.Manifold.cube([.6,4.4,11.5],True).translate([65.8,32.4886208-2.2,131.0496]).transform(dr.T[:3]);obstacles['zero_w_components']-=slot
lo=[1.5,35,10,25,1,9,3.32,1.,1.,-.45,-.45];hi=[9,65,50,65,14,40,4.2,2.1,2.1,.45,.45];rows=[]
for La0,L20,R30 in [(a,b,c) for a in [2.,4.,6.] for b in [20.,30.] for c in [3.4,3.8]]:
 def res(x):
  p,t,w,L,bs,_=family(x);rot=Rotation.from_matrix(want.T@np.column_stack([t,w,np.cross(t,w)])).as_rotvec()*30;gaps=[b['s0']-a['s1']-8*(abs(np.tan(a['phi']))+abs(np.tan(b['phi']))) for a,b in zip(bs,bs[1:])];lastFree=x[5]-5-8*abs(np.tan(x[-1]))
  return np.r_[p-target,rot,L-200,np.minimum(np.array(gaps)-.3,0)*10,min(lastFree-4,0)*10,(x[0]-La0)*.01,(x[2]-L20)*.01,(x[6]-R30)*.01]
 x0=[La0,48,L20,45,7,15,R30,1.6,1.6,.1,.1];fit=least_squares(res,x0,bounds=(lo,hi),max_nfev=100,ftol=1e-10,xtol=1e-10,gtol=1e-10);x=fit.x;p,t,w,L,bs,pr=family(x);err=float(max(abs(res(x)[:7])));gaps=[b['s0']-a['s1']-8*(abs(np.tan(a['phi']))+abs(np.tan(b['phi']))) for a,b in zip(bs,bs[1:])]
 row={'seed':[La0,L20,R30],'parameters':x.tolist(),'maxEndpointFrameLengthResidual':err,'length':L,'fullWidthFlatGapMin':min(gaps),'primitives':[{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in q.items()} for q in pr]}
 if err<.02 and min(gaps)>.25:
  solid=construct(4.4,200,.7,x,8);row['coarseVolumeMm3']=float(solid.volume());row['boundsMm']=list(solid.bounding_box());row['hits']={k:max(0,float((solid^v).volume())) for k,v in obstacles.items()};row['coarseGeometryOnly']=True
  del solid;gc.collect()
 rows.append(row);(D/'double-dogleg-screen.json').write_text(json.dumps({'integrationReady':False,'sourceHashes':hashes,'rows':rows,'candidateBudget':12,'sameFaceContactNormals':True,'widthMm':16,'thicknessMm':.6,'minimumBendRadiusMm':3,'scope':'Finite isometric-cylinder family with two separated quarter-turn board-edge crossings. Coarse collision screen only, no self/material/complete obstacle acceptance.'},indent=2)+'\n');print(len(rows),round(err,5),row.get('hits'),flush=True)
