"""Single derived isometric roof-entry prefix; not a whole cable candidate."""
from pathlib import Path
import ast,math
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(D/'build_reverse_nut_camera.py')
import developable_x225_dogleg as dr
trimesh=tm
src=D/'optimize_x225_u80.py';read(src)
for node in ast.parse(src.read_text()).body:
 if isinstance(node,ast.FunctionDef) and node.name=='construct':exec(compile(ast.Module(body=[node],type_ignores=[]),str(src),'exec'))
# Isometric 180-degree oblique cylinder swaps longitudinal/transverse axes, then rises to roof.
text=(D/'developable_ribbon_inner_entry.py').read_text();node=next(x for x in ast.parse(text).body if isinstance(x,ast.FunctionDef) and x.name=='family');ops=ast.parse("ops=[('S',8.4),('B',math.pi/2,0.,-1),('S',6.),('B',math.pi/2,0.,-1),('S',9.),('B',math.pi,math.pi/4,1),('S',9.2),('B',math.pi/2,0.,-1)]").body[0];node.body[1]=ops;ast.fix_missing_locations(node);exec(compile(ast.Module(body=[node],type_ignores=[]),'<one derived roof prefix>','exec'),dr.__dict__)
read(D/'developable_ribbon_inner_entry.py');read(D/'positive-x225-pose.json');m=json.loads(read(O/'candidate-manifest.json'));files=m['replacementMeshes']|{q['key']:q['mesh'] for q in m['additionalParts']}
x=np.zeros(11);p,t,w,L,bends,prims=dr.family(x);gap=min(b['s0']-a['s1']-8*(abs(np.tan(a['phi']))+abs(np.tan(b['phi']))) for a,b in zip(bends,bends[1:]));solid=construct(4.4,L,.35,x,16);checks=[]
keys=['head_cap','pi','zero_w_components','E-pi-04_revision_screw','amplifier','camera_board','face_panel','camera_retainer','eye_trim','motor15','jaw_support','jaw_frame','upper_pad','lower_pad','head_bottom','motor14','speaker','head_yaw_link','head_roll_ring_a','head_roll_ring_b','motor13','openrb']
for key in keys:
 obstacle=load(H/files[key]) if key in files else n['source'](key)
 if key=='zero_w_components':obstacle-=mf.Manifold.cube([.6,4.4,11.5],True).translate([65.8,32.4886208-2.2,131.0496]).transform(dr.T[:3])
 v,bb=n['volume'](solid,obstacle);checks.append({'obstacle':key,'overlapMm3':v,'boundsMm':bb});del obstacle;gc.collect()
slabs=[construct(a,min(a+2,L),1,x,8) for a in np.arange(4.4,L,2)];selfHits=[]
for i,a in enumerate(slabs):
 for j in range(i+2,len(slabs)):
  v,bb=n['volume'](a,slabs[j])
  if v>1e-5:selfHits.append({'slabs':[i,j],'overlapMm3':v,'boundsMm':bb})
r={'integrationReady':False,'scope':'60mm inboard roof-entry prefix only; not200mm or camera connection','materialLengthMm':L,'endpointMm':p.tolist(),'endTangent':t.tolist(),'endWidthAxis':w.tolist(),'fullWidthFlatGapMm':gap,'checks':checks,'selfHits':selfHits,'sourceHashes':n['hashes']};(O/'roof-inboard-prefix-diagnostic.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'endpoint':p.tolist(),'length':L,'gap':gap,'hits':[q for q in checks if q['overlapMm3']>1e-5],'selfHits':selfHits},indent=2))
