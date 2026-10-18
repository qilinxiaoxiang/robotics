from pathlib import Path
import ast
D=Path(__file__).resolve().parent
exec((D/'build_reverse_nut_camera.py').read_text().split('cam=load')[0]);read(Path(__file__))
from scipy.optimize import root
import developable_x225_dogleg as dr
trimesh=tm
pr=json.loads(read(D/'occupancy-layout/frontFlip-full-usb-unused-0-shift-1.0,0.0,0.0/report.json'));T=np.array(pr['candidate']['worldTransform']);mouth=(T@np.array([65.8,32.4886208,131.0496,1]))[:3];dr.initial=(mouth-4.4*T[:3,1],T[:3,1],T[:3,2]);dr.target=np.array([75.63,4.3706236,131.1145958]);O=D/'occupancy-layout/frontFlip-ribbon';O.mkdir(exist_ok=True)
src=D/'developable_ribbon_inner_entry.py';read(src);node=next(a for a in ast.parse(src.read_text()).body if isinstance(a,ast.FunctionDef) and a.name=='family');node.body[0]=ast.parse('R2,Lmid,extra,phi=x').body[0];node.body[1]=ast.parse("ops=[('S',8.4+8*abs(math.tan(phi))),('B',math.pi,phi,-1,3.),('S',Lmid),('B',math.pi,phi,-1,R2),('S',9+extra+8*abs(math.tan(phi)))]").body[0]
source=ast.unparse(node).replace('ang, phi, sign = op[1:]','ang, phi, sign, R = op[1:]');exec(source,dr.__dict__)
node=next(a for a in ast.parse(src.read_text()).body if isinstance(a,ast.FunctionDef) and a.name=='material_map');source=ast.unparse(node).replace('for b in bends:',"for b in bends:\n        R=b['R']");exec(source,dr.__dict__)
for a in ast.parse((D/'optimize_x225_u80.py').read_text()).body:
 if isinstance(a,ast.FunctionDef) and a.name=='construct':exec(compile(ast.Module(body=[a],type_ignores=[]),'<mesh>','exec'))
read(D/'optimize_x225_u80.py')
for desired in [None,100.,150.,200.]:
 if desired:
  def residual(x):
   p,t,w,L,*_=dr.family(x);return np.r_[p-dr.target,L-desired]
  fit=root(residual,[6,55+(desired-90)/2,(desired-90)/2,-.04]);x=fit.x
 else:
  def residual(v):return dr.family([v[0],v[1],0,v[2]])[0]-dr.target
  fit=root(residual,[6,55,-.04]);x=np.array([fit.x[0],fit.x[1],0,fit.x[2]])
 p,t,w,L,bends,ops=dr.family(x);solid=construct(4.4,L,.3,x,16);name='twoU_'+('minimum' if desired is None else str(int(desired)));path=export(solid,name);checks=[]
 obstacles=[('native_cap',H/'curved-head/community-curved-head-world.stl'),('camera',D/'positive-x225/camera_board_clamped-world.stl'),('amp',H/'gpio-audio-repair/amp16z2-closed-receiving-world.stl'),('face',D/'positive-x225/face_three_screw_camera-world.stl'),('clamp',D/'positive-x225/camera_three_screw_clamp-world.stl')]+[(r['key'],H/r['mesh']) for r in pr['parts'] if r['key']!='CSI_free4']
 for k in ['motor13','motor14','motor15','jaw_support','jaw_frame','head_yaw_link','speaker','head_bottom','upper_pad','lower_pad']:
  if k in n['P'] or k in n['files']:obstacles.append((k,None))
 rb=json.loads(read(H/'usb-access/usb-repair/openrb-component-enclosures/manifest.json'));obstacles += [('OpenRB_'+str(r['index']),Path(r['mesh'])) for r in rb['components']]
 for k,path2 in obstacles:
  o=load(path2) if path2 else n['source'](k)
  if k=='camera':o-=mf.Manifold.cube([.6,5,16],True).translate([75.63,6.8706236,131.1145958])
  v,bb=n['volume'](solid,o);checks.append({'obstacle':k,'overlapMm3':v,'boundsMm':bb,'gapCapped2':float(solid.min_gap(o,2))});del o
 slabs=[construct(a,min(a+2,L),.5,x,16) for a in np.arange(4.4,L,2)];selfhits=[]
 for i,a in enumerate(slabs):
  for j in range(i+2,len(slabs)):
   v,bb=n['volume'](a,slabs[j])
   if v>1e-5:selfhits.append({'slabs':[i,j],'overlapMm3':v})
 del slabs;gc.collect();r={'integrationReady':False,'targetLength':desired,'materialLengthMm':float(L),'radii':[3,float(x[0])],'width':16,'parameters':x.tolist(),'endpointErrorMm':float(np.linalg.norm(p-dr.target)),'tangent':t.tolist(),'widthAxis':w.tolist(),'mesh':path,'boundsMm':list(solid.bounding_box()),'checks':checks,'selfHits':selfhits,'expectedObstacles':len(obstacles),'completedObstacles':len(checks),'sourceHashes':n['hashes'],'miniInserted4p4NotYetExported':True,'contactNormalStart':np.cross(dr.initial[1],dr.initial[2]).tolist(),'contactNormalEnd':np.cross(t,w).tolist()};(O/(name+'.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'name':name,'length':L,'radii':r['radii'],'parameters':x.tolist(),'hits':[(a['obstacle'],a['overlapMm3']) for a in checks if a['overlapMm3']>1e-5],'selfHits':selfhits,'bounds':r['boundsMm']},indent=2),flush=True)
