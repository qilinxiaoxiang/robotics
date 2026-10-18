from pathlib import Path
import os,ast,json,math
assert os.environ.get('MICRODUCK_BOUNDED_CAD')=='1'
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
import developable_x225_dogleg as dr
D=Path(__file__).resolve().parent;O=D/'camera-quarter-rolls/90';q=json.loads((O/'report.json').read_text());dr.target=np.array(q['mouthWorldMm'])-5*np.array(q['outward']);dr.want=np.column_stack([[0,0,-1],[0,1,0],[1,0,0]])
# All bend pieces are cylinders. Two oblique 180 bends turn the ribbon width axis.
node=next(a for a in ast.parse((D/'developable_ribbon_inner_entry.py').read_text()).body if isinstance(a,ast.FunctionDef) and a.name=='family');node.body[0]=ast.parse('L1,L2,L3,L4,extra,ph1,ph2,ph3,ph4,ph5,da1,da3,da5=x').body[0]
node.body[1]=ast.parse("ops=[('S',8.4+8*abs(math.tan(ph1))),('B',math.pi/2+da1,ph1,-1),('S',L1),('B',math.pi,math.pi/4+ph2,-1),('S',L2),('B',math.pi/2+da3,ph3,1),('S',L3),('B',math.pi,-math.pi/4+ph4,-1),('S',L4),('B',math.pi/2+da5,ph5,-1),('S',9+extra+8*abs(math.tan(ph5)))]").body[0];exec(ast.unparse(node),dr.__dict__)
from scipy.ndimage import distance_transform_edt,map_coordinates
cache=np.load(O/'actual-fixed-field.npz');sdf=cache['sdf'];gridlo=np.array([-35.,-48.,75.]);del cache

def residual(x,target=None):
 p,t,w,L,b,_=dr.family(x);rot=Rotation.from_matrix(dr.want.T@np.column_stack([t,w,np.cross(t,w)])).as_rotvec()*30;gaps=[z['s0']-a['s1']-8*(abs(np.tan(a['phi']))+abs(np.tan(z['phi']))) for a,z in zip(b,b[1:])]
 base=np.r_[p-dr.target,rot,np.minimum(np.array(gaps)-.3,0)*10]
 ss=np.linspace(4.4,L,100);vv=[-8,-4,0,4,8];maps=[dr.material_map(s,v,b,(p,t,w,L)) for s in ss for v in vv];points=np.array([q+sg*.3*n for q,n in maps for sg in [-1,1]]);ds=map_coordinates(sdf,(points-gridlo).T,order=1,mode='constant',cval=-10);clear=np.minimum(ds-.5,0)*2

 return np.r_[base,clear,(L-target if target else (L-115)*.002)]
lo=[.3,.3,.3,.3,0,*([-.25]*5),*([-.6]*3)];hi=[70,70,70,70,45,*([.25]*5),*([.6]*3)];seed=np.array(json.loads((O/'upper-corridor-rise-fits.json').read_text())['candidates'][0]['parameters'])
rows=[]
for target in [200,150,115]:
 fit=least_squares(lambda x:residual(x,target),seed,bounds=(lo,hi),max_nfev=180,ftol=1e-11,xtol=1e-11,gtol=1e-11);p,t,w,L,b,pr=dr.family(fit.x);r={'integrationReady':False,'targetLength':target,'parameters':fit.x.tolist(),'lengthMm':L,'endpointErrorMm':float(np.linalg.norm(p-dr.target)),'orientationErrorRad':float(np.linalg.norm(Rotation.from_matrix(dr.want.T@np.column_stack([t,w,np.cross(t,w)])).as_rotvec())),'optimizerEvaluations':fit.nfev,'optimizerStatus':fit.status,'minimumFlatGapMm':min(z['s0']-a['s1']-8*(abs(np.tan(a['phi']))+abs(np.tan(z['phi']))) for a,z in zip(b,b[1:])),'end':p.tolist(),'target':dr.target.tolist(),'primitives':[{k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in z.items()} for z in pr]};rows.append(r);print(json.dumps({k:v for k,v in r.items() if k!='primitives'}),flush=True)
(O/'upper-corridor-actual-fits.json').write_text(json.dumps({'integrationReady':False,'bodyWidthMm':16,'bodyThicknessMm':.6,'minimumRadiusMm':3,'fixedFieldObstacleCount':184,'sourceHashes':{str(p.resolve()):__import__('hashlib').sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),O/'actual-fixed-field.npz',O/'actual-fixed-field.json',D/'positive-x225-pose.json',O/'report.json']},'candidates':rows},indent=2)+'\n')
