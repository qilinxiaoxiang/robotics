from pathlib import Path
import ast
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(D/'build_reverse_nut_camera.py')
import developable_x225_dogleg as dr
from scipy.optimize import least_squares
trimesh=tm
src=D/'optimize_x225_u80.py';read(src)
for node in ast.parse(src.read_text()).body:
 if isinstance(node,ast.FunctionDef) and node.name=='construct':exec(compile(ast.Module(body=[node],type_ignores=[]),str(src),'exec'))
read(D/'developable_x225_dogleg.py');read(D/'positive-x225-pose.json');m=json.loads(read(O/'candidate-manifest.json'));files=m['replacementMeshes']|{q['key']:q['mesh'] for q in m['additionalParts']}
x=np.array([24.,20,18,35,10,.05,0,0,0,0,0]);free=[1,2,3,6,7,8,10]
def pack(z):
 q=x.copy();q[free]=z;return q
sol=least_squares(lambda z:dr.residual(pack(z),False),x[free],bounds=([1,1,1,-.6,-1.2,-1.2,-.6],[90,90,60,.6,1.2,1.2,.6]),max_nfev=160,ftol=1e-11,gtol=1e-11,xtol=1e-11);x=pack(sol.x);p,t,w,L,bends,prims=dr.family(x);res=float(max(abs(dr.residual(x,False))));gap=min(b['s0']-a['s1']-8*(abs(np.tan(a['phi']))+abs(np.tan(b['phi']))) for a,b in zip(bends,bends[1:]));r={'accepted':False,'integrationReady':False,'candidateCount':1,'parameters':x.tolist(),'maximumEndpointResidual':res,'lengthMm':L,'minimumFullWidthFlatGapMm':gap,'checks':[],'sourceHashes':n['hashes']};out=O/'dogleg-single-candidate.json'
# Back-to-back zero-oblique opposite cylinders share a generator; zero flat gap is intentional, no material overfold.
if res>1e-4 or gap<-.00001:
 r['status']='ENDPOINT_OR_MATERIAL_BOUNDARY_REJECTED';out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));raise SystemExit()
s=construct(4.4,200,.35,x,16)
keys=['head_cap','pi','zero_w_components','E-pi-04_revision_screw','amplifier','camera_board','face_panel','camera_retainer','eye_trim','motor15','jaw_support','jaw_frame','upper_pad','lower_pad','head_bottom','motor14','speaker','head_yaw_link','head_roll_ring_a','head_roll_ring_b','motor13','openrb']
for key in keys:
 obstacle=load(H/files[key]) if key in files else n['source'](key)
 if key=='zero_w_components':obstacle-=mf.Manifold.cube([.6,4.4,11.5],True).translate([65.8,32.4886208-2.2,131.0496]).transform(dr.T[:3])
 if key=='camera_board':obstacle-=mf.Manifold.cube([.6,5,16],True).translate([75.63,9.3706236-2.5,131.1145958])
 v,bb=n['volume'](s,obstacle);r['checks'].append({'obstacle':key,'overlapMm3':v,'boundsMm':bb});out.write_text(json.dumps(r,indent=2)+'\n');del obstacle;gc.collect()
slabs=[construct(a,a+4,2,x,4) for a in np.arange(4,196,4)];selfHits=[]
for i,a in enumerate(slabs):
 for j in range(i+2,len(slabs)):
  v,bb=n['volume'](a,slabs[j])
  if v>1e-5:selfHits.append({'materialSlabIndices':[i,j],'overlapMm3':v,'boundsMm':bb})
r['coarseSelfHits']=selfHits;r['status']='SINGLE_TOPOLOGY_CHECK_COMPLETE_NOT_FINAL_ACCEPTANCE';out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'residual':res,'gap':gap,'hits':[q for q in r['checks'] if q['overlapMm3']>1e-5],'selfHits':selfHits},indent=2))
