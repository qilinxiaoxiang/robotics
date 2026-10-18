from pathlib import Path
import ast
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(D/'build_reverse_nut_camera.py')
import developable_ribbon_inner_entry as dr
pose=json.loads(read(D/'positive-x225-pose.json'));dr.T=np.array(pose['worldTransform']);dr.mouth=np.array(pose['csiMouthWorldMm']);dr.initial=(dr.mouth-4.4*dr.T[:3,1],dr.T[:3,1],dr.T[:3,2]);dr.cam=np.array([75.63,9.3706236,131.1145958]);dr.target=dr.cam-[0,5,0]
trimesh=tm
src=D/'optimize_x225_u80.py';read(src)
for node in ast.parse(src.read_text()).body:
 if isinstance(node,ast.FunctionDef) and node.name=='construct':exec(compile(ast.Module(body=[node],type_ignores=[]),str(src),'exec'))
r=json.loads(read(O/'fixed-u80-search.json'));x=np.array(r['best']['parameters']);m=json.loads(read(O/'candidate-manifest.json'));files=m['replacementMeshes']|{q['key']:q['mesh'] for q in m['additionalParts']};p,t,w,L,bends,prims=dr.family(x);checks=[]
for i,b in enumerate(prims):
 a=max(4.4,b['s0']);z=min(200,b['s1'])
 if z-a<1e-5:continue
 solid=construct(a,z,.35,x,16)
 for k in ['head_cap','pi','zero_w_components','E-pi-04_revision_screw','face_panel','amplifier']:
  obstacle=load(H/files[k])
  if k=='zero_w_components':obstacle-=mf.Manifold.cube([.6,4.4,11.5],True).translate([65.8,32.4886208-2.2,131.0496]).transform(dr.T[:3])
  v,bb=n['volume'](solid,obstacle)
  checks.append({'primitive':i,'kind':b['kind'],'materialIntervalMm':[a,z],'obstacle':k,'overlapMm3':v,'boundsMm':bb});del obstacle;gc.collect()
rep={'accepted':False,'purpose':'Localize rejected best U route by material interval; no new optimization or acceptance','candidateIndex':r['best']['index'],'checks':checks,'sourceHashes':n['hashes']};(O/'u80-failure-classification.json').write_text(json.dumps(rep,indent=2)+'\n');print(json.dumps([q for q in checks if q['overlapMm3']>1e-5],indent=2))
