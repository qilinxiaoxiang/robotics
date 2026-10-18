from pathlib import Path
import ast
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(Path(__file__))
import developable_x225_dogleg as dr
trimesh=tm
src=D/'developable_ribbon_inner_entry.py';read(src);node=next(a for a in ast.parse(src.read_text()).body if isinstance(a,ast.FunctionDef) and a.name=='family');node.body[0]=ast.parse('sign=x[0]').body[0];node.body[1]=ast.parse("ops=[('S',4.),('B',math.pi/2,0.,sign),('S',4.)]").body[0];exec(ast.unparse(node),dr.__dict__)
for a in ast.parse((D/'optimize_x225_u80.py').read_text()).body:
 if isinstance(a,ast.FunctionDef) and a.name=='construct':exec(compile(ast.Module(body=[a],type_ignores=[]),'<mesh>','exec'))
old=D/'positive-x225';obstacles=[('native_cap',H/'curved-head/community-curved-head-world.stl'),('face',old/'face_three_screw_camera-world.stl'),('amp',H/'gpio-audio-repair/amp16z2-closed-receiving-world.stl')]
for k in ['motor13','motor14','motor15','jaw_support','jaw_frame','head_yaw_link','speaker','head_bottom','upper_pad','lower_pad']:
 if k in n['P'] or k in n['files']:obstacles.append((k,None))
pr=json.loads(read(old/'pi-geometry-manifest.json'));obstacles.extend((r['key'],H/r['mesh']) for r in pr['parts'])
for angle in [-90,90]:
 q=json.loads(read(D/'camera-quarter-rolls'/str(angle)/'report.json'));O=D/'camera-quarter-rolls'/str(angle);t=np.array(q['outward']);dr.initial=(np.array(q['mouthWorldMm']),t,np.cross([1,0,0],t));dr.R=3.
 for sign in [-1,1]:
  p,tt,w,L,b,pr=dr.family([sign]);s=construct(0,L,.25,[sign],16);mesh=export(s,'exitR3_'+str(sign));checks=[]
  for k,path in obstacles:
   o=load(path) if path else n['source'](k);v,bb=n['volume'](s,o);checks.append({'obstacle':k,'volumeMm3':v,'boundsMm':bb,'gapCapped2':float(s.min_gap(o,2))});del o
  r={'integrationReady':False,'angle':angle,'sign':sign,'receivingWidthMm':16,'straightMm':4,'R':3,'mesh':mesh,'checks':checks,'expectedPairs':len(obstacles),'completedPairs':len(checks),'sourceHashes':n['hashes']};(O/('exitR3_'+str(sign)+'.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'angle':angle,'sign':sign,'hits':[(a['obstacle'],a['volumeMm3']) for a in checks if a['volumeMm3']>1e-5]},indent=2),flush=True)
