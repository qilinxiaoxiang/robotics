"""Single derived isometric roof-entry prefix; not a whole cable candidate."""
from pathlib import Path
import ast,math,hashlib
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(D/'build_reverse_nut_camera.py')
import developable_x225_dogleg as dr
trimesh=tm
src=D/'optimize_x225_u80.py';read(src)
for node in ast.parse(src.read_text()).body:
 if isinstance(node,ast.FunctionDef) and node.name=='construct':exec(compile(ast.Module(body=[node],type_ignores=[]),str(src),'exec'))
text=(D/'developable_ribbon_inner_entry.py').read_text();node=next(x for x in ast.parse(text).body if isinstance(x,ast.FunctionDef) and x.name=='family')
node.body[0]=ast.parse('L1,L2,extra,a1,a2,a3,p2,p3,p1=x').body[0]
node.body[1]=ast.parse("ops=[('S',8.4+8*abs(math.tan(p1))),('B',a1,p1,-1),('S',L1),('B',a2,p2,-1),('S',L2),('B',a3,p3,1),('S',9+extra+8*abs(math.tan(p3)))]").body[0];ast.fix_missing_locations(node);exec(compile(ast.Module(body=[node],type_ignores=[]),'<short family>','exec'),dr.__dict__)

read(D/'developable_ribbon_inner_entry.py');read(D/'positive-x225-pose.json');m=json.loads(read(O/'candidate-manifest.json'));files=m['replacementMeshes']|{q['key']:q['mesh'] for q in m['additionalParts']}
fit=json.loads(read(O/'short-oblique-connection-fits.json'))['candidates'][int(os.environ.get('FFC_CASE','0'))];x=np.array(fit['parameters']);p,t,w,L,bends,prims=dr.family(x);gap=min(b['s0']-a['s1']-8*(abs(np.tan(a['phi']))+abs(np.tan(b['phi']))) for a,b in zip(bends,bends[1:]));solid=construct(4.4,L,.35,x,16);checks=[]
base=json.loads(read(H/'viewer-candidate.json')); removed=set(base['removedParts'])|set(m['removedParts']); files=(base['replacementMeshes']|{q['key']:q['mesh'] for q in base['additionalParts']})|files
keys=sorted((set(n['P'])|set(files))-removed)

for key in keys:
 if key=='openrb':
  em=json.loads(read(H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json'))
  assert em['allSourceTrianglesCoveredExactlyOnce'] and em['componentCount']==142
  assert sum(e['sourceTriangleCount'] for e in em['components'])==em['sourceTriangleCount']==317300
  assert hashlib.sha256(read(Path(em['sourceFile']))).hexdigest()==em['sourceSha256']
  cr=[]; sb=np.array(solid.bounding_box()).reshape(2,3)
  for e in em['components']:
   ep=Path(e['mesh']); assert hashlib.sha256(read(ep)).hexdigest()==e['meshSha256']
   bb=np.array(e['bounds']); lower=float(np.linalg.norm(np.maximum(np.maximum(sb[0]-bb[1],bb[0]-sb[1]),0)))
   if lower>=2: cr.append({'component':e['index'],'overlapMm3':0.,'gapLowerBoundMm':lower,'method':'complete component bounds separation'});continue
   ob=load(ep);v,b=n['volume'](solid,ob);cr.append({'component':e['index'],'overlapMm3':v,'boundsMm':b,'minimumGapCapped2Mm':float(solid.min_gap(ob,2))});del ob;gc.collect()
  assert len(cr)==142
  checks.append({'obstacle':key,'method':'142 closed conservative source-component enclosures','expectedComponents':142,'completedComponents':len(cr),'components':cr,'overlapMm3':sum(e['overlapMm3'] for e in cr),'minimumGapCapped2Mm':min(min(2,e.get('gapLowerBoundMm',e.get('minimumGapCapped2Mm',2))) for e in cr)})
  continue
 obstacle=load(H/files[key]) if key in files else n['source'](key)
 if key=='camera_board':obstacle-=mf.Manifold.cube([.6,5,16],True).translate([75.63,9.3706236-2.5,131.1145958])
 if key=='zero_w_components':obstacle-=mf.Manifold.cube([.6,4.4,11.5],True).translate([65.8,32.4886208-2.2,131.0496]).transform(dr.T[:3])
 assert obstacle.status()==mf.Error.NoError and obstacle.volume()>0,key
 v,bb=n['volume'](solid,obstacle);checks.append({'obstacle':key,'overlapMm3':v,'boundsMm':bb,'minimumGapCapped2Mm':float(solid.min_gap(obstacle,2))});del obstacle;gc.collect()
slabs=[construct(a,min(a+2,L),1,x,8) for a in np.arange(4.4,L,2)];selfHits=[]
for i,a in enumerate(slabs):
 for j in range(i+2,len(slabs)):
  v,bb=n['volume'](a,slabs[j])
  if v>1e-5:selfHits.append({'slabs':[i,j],'overlapMm3':v,'boundsMm':bb})
prefixMesh=export(solid,'short_connection_'+str(round(L)));r={'expectedObstacles':len(keys),'completedObstacles':len(checks),'prefixMesh':prefixMesh,'integrationReady':False,'scope':'Fixed endpoints, 73/150mm three-cylinder family; nominal receiving geometry only, not wholeassembly acceptance','materialLengthMm':L,'endpointMm':p.tolist(),'endTangent':t.tolist(),'endWidthAxis':w.tolist(),'fullWidthFlatGapMm':gap,'checks':checks,'selfHits':selfHits,'sourceHashes':n['hashes']};(O/('short-connection-'+str(round(L))+'-static.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'endpoint':p.tolist(),'length':L,'gap':gap,'hits':[q for q in checks if q['overlapMm3']>1e-5],'selfHits':selfHits,'sub0p5Gap':[q for q in checks if q['minimumGapCapped2Mm']<.5],'expected':len(keys),'completed':len(checks)},indent=2))
